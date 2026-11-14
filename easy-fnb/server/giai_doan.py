"""Giai đoạn bữa ăn của từng bàn đang có khách, và lời nhắc khi một giai đoạn kéo quá lâu.

    seated (khách mới ngồi) -> greeted (đã có nhân viên tới) -> served (đã có đồ ăn/uống) -> finished (ăn xong,
    đĩa trống) -> left (khách rời)

AI chỉ trả lời câu hỏi có/không về ảnh bàn; mọi việc tính giờ và quyết định nằm ở đây.
- seated, left: từ trạng thái bàn camera gửi (POST /api/edge/tables) và sự kiện khách rời.
- greeted: camera thấy nhân viên tới bàn, hoặc nhân viên bấm Xong việc gọi/khách mới của bàn đó.
- served, finished: Gemini Decision xem ảnh bàn camera gửi định kỳ (POST /api/edge/table-snap). Phải HAI lần đọc
  liên tiếp cùng nói vậy mới chuyển (một khung bị che không được làm đổi giai đoạn). Có đồ ăn thì coi như đã có
  nhân viên tới. Decision tắt hoặc lỗi thì bàn vẫn đi seated -> greeted -> left theo tín hiệu camera.
- Trong một lượt khách giai đoạn chỉ đi tới. Lượt mới (bàn có khách lại sau khi rời) bắt đầu lại từ seated.
- Bàn theo tên, không theo camera: hai camera cùng thấy một bàn thì vẫn là một lượt khách.
- Giờ tính bằng đồng hồ của máy chủ (hub.clock), không dùng giờ camera gửi: đồng hồ camera lệch hay chạy lùi
  không ảnh hưởng. Máy chủ khởi động lại giữa bữa thì bàn bắt đầu lại từ seated.

Lời nhắc (mỗi loại một lần cho mỗi lượt khách), hiện như tín hiệu mềm "khách nhìn quanh": một dòng nhật ký,
đánh dấu trên bàn, không đọc cho nhân viên. Riêng "chưa ai ra tiếp" tạo thêm việc khách mới nếu bàn chưa có
việc nào đang mở.
"""
import asyncio
import time
from collections import deque

from .gemini import P_NO, P_YES

STAGES = ('seated', 'greeted', 'served', 'finished', 'left')
ACTIVE = STAGES[:4]                     # đang có khách
CHECKED = ('seated', 'greeted', 'served')   # còn cần xem ảnh (ăn xong rồi thì thôi)
STAGE_VI = {'seated': 'khách mới ngồi', 'greeted': 'đã có nhân viên tới', 'served': 'đã có món',
            'finished': 'đã ăn xong', 'left': 'khách đã rời'}
NUDGE_VI = {'greet': 'ngồi khá lâu mà chưa ai ra tiếp', 'food': 'chờ khá lâu mà chưa thấy món lên',
            'bill': 'đã ăn xong khá lâu, có thể đang chờ tính tiền'}
NUDGE_SETTING = {'greet': 'wait_greet_s', 'food': 'wait_food_s', 'bill': 'wait_bill_s'}
LEFT_GRACE_S = 20.0         # camera báo bàn trống hay khách rời thoáng qua (người che, đứng lên lấy đồ): chờ chừng này giây mới coi là khách rời
CLEAR_MIN = 0.2             # ảnh bàn cắt từ camera thường nhỏ và mờ, Gemini hay chấm 'rõ' thấp: chỉ bỏ ảnh thật sự không xem được
FIRST_CHECK_S = 10.0        # xem ảnh lần đầu sau khi khách ngồi chừng này giây
STAFF_CHECK_S = 20.0        # nhân viên vừa tới: xem lại sớm (có thể vừa mang món ra)
RECHECK_S = 15.0            # lần đọc đầu nói "có": xem lại sớm để có lần thứ hai
NEED = 2                    # số lần đọc liên tiếp cùng kết quả mới đổi giai đoạn
MAX_PER_MIN = 30            # trần số lần hỏi Gemini mỗi phút cho mọi bàn (gói miễn phí: 200 lần/phút)
CHECK_TIMEOUT_S = 6.0
HOLD_S = 600.0              # khách để đồ lại rồi rời bàn (đi vệ sinh, ra ngoài nghe máy): chờ chừng này mới coi là đã về
SNAP_MAX = 1_000_000
CLOSED = ('done', 'cancelled')


def now_ms():
    return int(time.time() * 1000)


def safe_name(s):
    return ''.join(ch for ch in str(s) if ch.isalnum() or ch in '_-')


class GiaiDoan:
    def __init__(self, hub, breaker):
        self.hub = hub
        self.breaker = breaker          # ngắt mạch riêng: ảnh bàn lỗi không làm ngừng việc kiểm tra cảnh báo
        self.dir = hub.data / 'snaps'
        self.st = {}                    # tên bàn -> trạng thái lượt khách hiện tại (hoặc vừa rời)
        self.snap_at = {}               # (camera, bàn) -> lúc nhận ảnh bàn gần nhất (ms)
        self.calls = deque()            # lúc hỏi Gemini trong 60 giây gần nhất
        self.tasks = set()
        self.timeout_s = CHECK_TIMEOUT_S
        self._seat = 0
        self._warned = False

    # ------------------------------------------------------------ tiện ích
    def _err(self, e):
        if not self._warned:
            self._warned = True
            print(f'giai đoạn bàn lỗi (bỏ qua): {type(e).__name__}: {e}')

    def _entries(self, name):
        return [tb for tb in self.hub.tables.values() if tb['id'] == name]

    def decorate(self, tb):
        """Điền stage, stage_since, nudge, snap_at vào một TableState."""
        s = self.st.get(tb['id'])
        tb['stage'] = s['stage'] if s else None
        tb['stage_since'] = s['since'] if s else None
        tb['nudge'] = s['nudge'] if s else None
        tb['nudge_at'] = s['nudge_at'] if s else None
        tb['snap_at'] = self.snap_at.get((tb['camera'], tb['id']))
        tb['away'] = bool(s and s['stage'] in ACTIVE and s.get('hold_until'))   # khách tạm rời, còn đồ ở bàn
        return tb

    def _sync(self, name, skip_cam=None):
        for tb in self._entries(name):
            if tb['camera'] != skip_cam:
                self.hub.publish('table', self.decorate(tb))

    def _set(self, name, stage, via, skip_cam=None, **extra):
        """Chuyển giai đoạn (chỉ đi tới). Ghi dòng thời gian và phát lại trạng thái bàn."""
        s = self.st[name]
        if STAGES.index(stage) <= STAGES.index(s['stage']):
            return False
        now = self.hub.clock()
        prev, prev_s = s['stage'], round(now - s['t0'], 1)
        s.update(stage=stage, since=now_ms(), t0=now, n_food=0, n_empty=0, nudge=None, nudge_at=None)
        self.hub.timeline.add('stage', table=name, camera=s['camera'], stage=stage, prev=prev, via=via,
                              seat=s['seat'], prev_s=prev_s, **extra)
        self._sync(name, skip_cam)
        return True

    def _start(self, name, cam, skip_cam=None):
        self._seat += 1
        now = self.hub.clock()
        old = self.st.get(name)
        self.st[name] = dict(stage='seated', since=now_ms(), t0=now, seat=self._seat, camera=cam, staff_t=None,
                             away_t=None, n_food=0, n_empty=0, nudged=set(), nudge=None, nudge_at=None,
                             due=now + FIRST_CHECK_S, pulled=-1e9, busy=False, clear_t=None, food=None)
        self.hub.timeline.add('stage', table=name, camera=cam, stage='seated', prev=old['stage'] if old else None,
                              via='camera', seat=self._seat)
        self._sync(name, skip_cam)

    # ------------------------------------------------------------ tín hiệu từ Hub
    def on_table(self, tb):
        """Hub gọi khi một camera báo bàn đổi trạng thái, TRƯỚC khi lưu và phát `tb`."""
        try:
            name, cam = tb['id'], tb['camera']
            states = [e['state'] for e in self._entries(name) if e['camera'] != cam] + [tb['state']]
            s = self.st.get(name)
            if 'occupied' in states:
                if s is None or s['stage'] == 'left':
                    self._start(name, cam, skip_cam=cam)
                else:
                    s['away_t'] = None          # chỉ là trống thoáng qua
                    s['hold_until'] = None      # khách để đồ đã quay lại: vẫn là lượt cũ
            elif s and s['stage'] in ACTIVE and not s.get('hold_until'):
                # chưa kết luận ngay cả khi camera báo cần dọn: chờ LEFT_GRACE_S để Gemini kịp xem ảnh
                # (thấy đồ cá nhân thì giữ bàn, xem hold)
                if any(x != 'unknown' for x in states) and s['away_t'] is None:
                    s['away_t'] = self.hub.clock()
            self.decorate(tb)
        except Exception as e:
            self._err(e)

    def on_staff(self, name, via='staff_arrived'):
        """Có nhân viên ở bàn (camera thấy, hoặc nhân viên bấm Xong việc của bàn)."""
        try:
            s = self.st.get(name)
            if not s or s['stage'] not in ACTIVE:
                return
            now = self.hub.clock()
            s['staff_t'] = now
            if s['stage'] == 'seated':
                self._set(name, 'greeted', via)
            if now - s['pulled'] > 60:          # camera gửi lại mỗi 5 giây khi nhân viên còn đứng đó: chỉ kéo một lần
                s['pulled'] = now
                s['due'] = min(s['due'], now + STAFF_CHECK_S)
        except Exception as e:
            self._err(e)

    def on_left(self, name):
        try:
            s = self.st.get(name)
            if s and s['stage'] in ACTIVE and s['away_t'] is None:
                s['away_t'] = self.hub.clock()      # chưa kết luận ngay: khách ngồi lại trong lúc chờ thì vẫn là lượt cũ
        except Exception as e:
            self._err(e)

    def hold(self, name):
        """Gemini thấy đồ cá nhân còn ở bàn lúc camera báo cần dọn: khách chỉ tạm rời. Giữ lượt khách HOLD_S.
        Trả False khi không giữ được (bàn không có lượt khách đang mở, hoặc lượt này đã giữ một lần rồi)."""
        try:
            s = self.st.get(name)
            if not s or s['stage'] not in ACTIVE or s.get('held'):
                return False
            s.update(hold_until=self.hub.clock() + float(self.hub.settings.get('hold_s') or HOLD_S), held=True,
                     away_t=None)   # chỉnh được trong Cài đặt (demo đặt ngắn)
            text = f'Bàn {name}: khách tạm rời, còn để đồ. Chưa cần dọn'
            self.hub.add_log('system', text, name, s['camera'])
            self.hub.timeline.add('table', table=name, camera=s['camera'], text=text, away=True, seat=s['seat'])
            self._sync(name)
            return True
        except Exception as e:
            self._err(e)
            return False

    def reset(self):
        """Bắt đầu ca mới: quên hết. Lần hỏi Gemini đang dở sẽ bị bỏ kết quả (bàn không còn lượt khách đó)."""
        self.st.clear()
        self.snap_at.clear()
        try:
            for f in self.dir.glob('*.jpg'):
                f.unlink()
        except OSError as e:
            self._err(e)

    def tick(self):
        try:
            now = self.hub.clock()
            for name, s in list(self.st.items()):
                if not self._entries(name):     # bàn đã bị xoá khỏi vùng vẽ
                    del self.st[name]
                elif s['stage'] in ACTIVE:
                    if s.get('hold_until') and now >= s['hold_until']:
                        # hết thời gian giữ mà khách chưa quay lại: coi là đã về, báo dọn (lần này không giữ nữa)
                        s['hold_until'] = None
                        self._set(name, 'left', 'hold_expired')
                        self.hub.edge_event(dict(kind='can_don', camera=s['camera'], table=name,
                                                 detail='Khách để đồ lại khá lâu chưa quay lại'))
                    elif s.get('hold_until'):
                        pass
                    elif s['away_t'] is not None and now - s['away_t'] >= LEFT_GRACE_S:
                        self._set(name, 'left', 'camera')
                    else:
                        self._nudges(name, s, now)
        except Exception as e:
            self._err(e)

    # ------------------------------------------------------------ lời nhắc
    def _nudges(self, name, s, now):
        which = {'seated': 'greet', 'greeted': 'food', 'finished': 'bill'}.get(s['stage'])
        if which is None or which in s['nudged']:
            return
        try:
            limit = float(self.hub.settings.get(NUDGE_SETTING[which]) or 0)
        except (TypeError, ValueError):
            limit = 0
        if limit <= 0 or now - s['t0'] < limit:
            return
        # "chưa thấy món": chỉ nhắc khi AI thật sự đã xem ảnh từ lúc nhân viên tới và không thấy đồ ăn
        # (Decision tắt thì không biết có món hay chưa, nhắc sẽ thành báo nhầm ở mọi bàn)
        if which == 'food' and (s['clear_t'] is None or s['clear_t'] < s['t0'] or s['food'] is None
                                or s['food'] >= P_YES):
            return
        # "chờ tính tiền": đã có nhân viên tới sau khi ăn xong thì thôi
        if which == 'bill' and s['staff_t'] is not None and s['staff_t'] >= s['t0']:
            return
        s['nudged'].add(which)
        s['nudge'], s['nudge_at'] = which, now_ms()
        text = f'Bàn {name} {NUDGE_VI[which]}'
        self.hub.add_log('nudge', text, name, s['camera'])
        self.hub.timeline.add('nudge', table=name, camera=s['camera'], text=text, nudge=which, stage=s['stage'],
                              seat=s['seat'], waited_s=round(now - s['t0']))
        self._sync(name)
        if which == 'greet' and not any(a['table'] == name and a['status'] not in CLOSED
                                        for a in self.hub.alerts.values()):
            # chưa có việc nào đang mở cho bàn này: tạo việc "khách mới" như camera báo (đi qua luật gộp trùng)
            self.hub.edge_event(dict(kind='khach_moi', camera=s['camera'], table=name,
                                     detail='Khách ngồi khá lâu mà chưa ai ra tiếp'))

    # ------------------------------------------------------------ ảnh bàn định kỳ từ camera
    def snap_path(self, cam, name):
        return self.dir / f'{safe_name(cam)}_{safe_name(name)}.jpg'

    def snap_file(self, name, cam=None):
        """Tệp ảnh bàn mới nhất (của camera `cam`, hoặc camera gửi gần nhất). None nếu chưa có."""
        got = [(at, c) for (c, n), at in self.snap_at.items() if n == name and cam in (None, c)]
        if not got:
            return None
        f = self.snap_path(max(got)[1], name)
        return f if f.exists() else None

    def snap(self, cam, name, jpeg, ts=None):
        """Nhận một ảnh bàn. Trả dict(ok, check): check nói có hỏi Gemini không và vì sao không.
        `ts` của camera chỉ để tham khảo: mọi mốc giờ dùng đồng hồ máy chủ."""
        tb = self.hub.tables.get(f'{cam}/{name}')
        if tb is None:              # bàn không có trong vùng vẽ, hoặc camera chưa báo trạng thái bàn này
            return dict(ok=False, reason='unknown_table')
        if jpeg[:2] != b'\xff\xd8' or len(jpeg) > SNAP_MAX:
            raise ValueError('cần ảnh JPEG dưới 1 MB')
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            self.snap_path(cam, name).write_bytes(jpeg)
            self.snap_at[(cam, name)] = now_ms()
            self.hub.publish('table', self.decorate(tb))
        except OSError as e:        # ổ đĩa lỗi: vẫn xem ảnh được
            self._err(e)
        try:
            return dict(ok=True, check=self._maybe_check(name, jpeg))
        except Exception as e:
            self._err(e)
            return dict(ok=True, check='error')

    def _maybe_check(self, name, jpeg):
        s = self.st.get(name)
        if not s or s['stage'] not in CHECKED:
            return 'not_needed'
        g = self.hub.gemini
        try:
            every = float(self.hub.settings.get('table_check_s') or 0)
        except (TypeError, ValueError):
            every = 0
        if every <= 0 or not (g.enabled and getattr(g, 'decision', False) and hasattr(g, 'table_check')):
            return 'off'
        if s['busy']:
            return 'busy'           # mỗi bàn chỉ một lần hỏi đang chạy
        now = self.hub.clock()
        if now < s['due']:
            return 'not_due'
        while self.calls and now - self.calls[0] >= 60:
            self.calls.popleft()
        if len(self.calls) >= MAX_PER_MIN:
            return 'rate_limited'
        s['due'] = now + every
        if self.hub.breaker.state == 'open' or not self.breaker.allow():
            return 'breaker_open'   # Gemini đang lỗi: không hỏi thêm, chờ lượt sau
        s['busy'] = True
        self.calls.append(now)
        t = asyncio.get_running_loop().create_task(self._check(name, s, jpeg))
        self.tasks.add(t)
        t.add_done_callback(self.tasks.discard)
        return 'started'

    async def _check(self, name, s, jpeg):
        try:
            r = await asyncio.wait_for(self.hub.gemini.table_check(jpeg, name), self.timeout_s)
        except Exception as e:      # 429, quá hạn, ảnh bị từ chối, lỗi mạng: bỏ lần đọc này
            self.breaker.failure()
            self.hub.timeline.add('table_check', table=name, camera=s['camera'], error=f'{type(e).__name__}: {e}'[:160])
            return
        finally:
            s['busy'] = False
        self.breaker.success()
        try:
            probs = {k: round(float(v), 3) for k, v in (r.get('probs') or {}).items()}
            if self.st.get(name) is not s or s['stage'] not in CHECKED:
                return              # khách đã rời hoặc ca mới bắt đầu trong lúc hỏi: bỏ kết quả
            used = self._reading(name, s, probs)
            self.hub.timeline.add('table_check', table=name, camera=s['camera'], used=used, ms=r.get('ms'),
                                  stage=s['stage'], **probs)
        except Exception as e:
            self._err(e)

    def _reading(self, name, s, p):
        """Một lần đọc ảnh bàn (xác suất "có" từng câu). Trả 'ok' hoặc lý do bỏ qua lần đọc."""
        if p.get('image_clear', 1.0) < CLEAR_MIN:
            return 'unclear'
        if p.get('people_at_table', 1.0) <= P_NO:
            return 'no_people'      # không thấy ai ngồi: khung bị che hoặc khách vừa đứng lên; khách rời do camera lo
        now = self.hub.clock()
        s['clear_t'] = now
        food, empty, menu = p.get('food_or_drink_on_table'), p.get('plates_mostly_empty'), p.get('menu_in_hand', 0.0)
        if food is not None:
            s['food'] = food
        if s['stage'] in ('seated', 'greeted'):
            key, yes, no = 'n_food', food is not None and food >= P_YES, food is not None and food <= P_NO
            nxt = 'served'
        else:                       # served: đĩa gần trống và không ai đang xem thực đơn (gọi thêm món)
            key, yes = 'n_empty', empty is not None and empty >= P_YES and menu < P_YES
            no = (empty is not None and empty <= P_NO) or menu >= P_YES
            nxt = 'finished'
        if yes:
            s[key] += 1
        elif no:
            s[key] = 0              # lưng chừng thì giữ nguyên, không tính cũng không xoá
        if s[key] >= NEED:
            self._set(name, nxt, 'snapshot', probs=p)
        elif yes:
            s['due'] = min(s['due'], now + RECHECK_S)
        return 'ok'

import type { ReactNode } from 'react';
import { Volume2, VolumeX } from 'lucide-react';
import { StaffApp } from '../components/StaffApp';
import { STAFF } from '../sim/model';
import { useSim } from '../sim/store';
import { SYSTEM, setLang, setListenAll, textFor, useVoice } from '../sim/voice';

/** Trang cho quản lý: xem app của từng nhân viên và nghe đúng kênh tai nghe của họ */
export default function StaffChannels() {
  const e = useSim();
  const v = useVoice();
  const all = v.listening.length === STAFF.length;
  const channels = v.listening.map((id) => e.staffName(id)).join(', ');

  let voiceNote: ReactNode;
  if (!v.supported) {
    voiceNote = 'Trình duyệt này không đọc được giọng nói; vẫn có tiếng chuông và chữ trên từng app.';
  } else if (!v.hasVoice) {
    voiceNote =
      v.lang === 'vi' ? (
        <>
          Máy này chưa có giọng tiếng Việt nên câu đọc sẽ sai dấu.{' '}
          <button type="button" className="link-btn" onClick={() => setLang('en')}>
            Chuyển sang English
          </button>{' '}
          hoặc mở bằng Microsoft Edge (có giọng HoaiMy).
        </>
      ) : (
        'Máy này chưa có giọng tiếng Anh, trình duyệt sẽ dùng giọng mặc định.'
      );
  } else {
    voiceNote = `Giọng ${v.voiceName}. Mỗi kênh một giọng hoặc cao độ riêng để nghe là biết của ai; việc gấp có hai tiếng chuông.`;
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>App nhân viên</h1>
          <p>Mỗi người chỉ nhận việc của mình, đọc thẳng vào tai nghe Bluetooth. Bật kênh của ai thì nghe đúng những gì người đó đang nghe.</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <div className="seg" role="group" aria-label="Ngôn ngữ giọng đọc">
            <button type="button" aria-pressed={v.lang === 'vi'} onClick={() => setLang('vi')}>
              Tiếng Việt
            </button>
            <button type="button" aria-pressed={v.lang === 'en'} onClick={() => setLang('en')}>
              English
            </button>
          </div>
          <button type="button" className="btn" aria-pressed={all} onClick={() => setListenAll(!all)}>
            {all ? <VolumeX size={16} aria-hidden="true" /> : <Volume2 size={16} aria-hidden="true" />}
            {all ? 'Tắt tất cả kênh' : 'Nghe tất cả kênh'}
          </button>
        </div>
      </div>

      <section className="panel onair" aria-labelledby="onair-title">
        <h2 id="onair-title" className="visually-hidden">
          Đang phát
        </h2>
        <div className="onair-now" aria-live="polite">
          {v.speaking ? (
            <>
              <span className="chip chip--p2">
                <Volume2 size={13} aria-hidden="true" />
                {v.speaking.staff === SYSTEM ? 'Hệ thống' : `Đang đọc cho ${e.staffName(v.speaking.staff)}`}
              </span>
              <span className="onair-line">“{textFor(v.speaking, v.lang)}”</span>
            </>
          ) : v.listening.length ? (
            <span className="ink2">Đang chờ việc mới trên kênh của {channels}.</span>
          ) : (
            <span className="ink2">Chưa bật kênh nào. Bấm “Nghe kênh này” ở một nhân viên bên dưới.</span>
          )}
        </div>
        <p className="small muted">{voiceNote}</p>
      </section>

      <div className="sapps">
        {STAFF.map((s) => (
          <StaffApp key={s.id} id={s.id} />
        ))}
      </div>
    </div>
  );
}

import { ROLE_LABEL, TASK_INFO, type Role, type TaskKind } from './model';
import type { Lang } from './voice';

const TASK_EN: Record<TaskKind, string> = {
  call: 'Calling for service',
  broken: 'Broken dish',
  greet: 'New guests seated',
  bill: 'Asking for the bill',
  clear: 'Needs clearing',
  food_late: 'Food running late',
  refill: 'Needs a water refill',
  plates: 'Out of food',
};

const ROLE_EN: Record<Role, string> = { serve: 'Server', cashier: 'Cashier', clean: 'Busser' };

/** Chữ trên app nhân viên, theo ngôn ngữ đang chọn */
export const STAFF_TEXT = {
  vi: {
    task: (k: TaskKind) => {
      const s = TASK_INFO[k].label;
      return s.charAt(0).toUpperCase() + s.slice(1);
    },
    role: (r: Role, zone?: string) => `${ROLE_LABEL[r]}${zone ? `, khu ${zone}` : ''}`,
    table: 'Bàn',
    assignedAt: 'Giao lúc',
    autoConfirm: 'Không cần bấm gì: camera tự xác nhận khi bạn tới bàn.',
    confirmed: 'Camera đã xác nhận bạn đang ở bàn.',
    free: 'Đang rảnh',
    onBreak: 'Đang nghỉ giải lao',
    nextHint: 'Việc tiếp theo sẽ được đọc thẳng vào tai nghe.',
    heard: 'Đã nghe trong tai nghe',
    empty: 'Chưa có thông báo nào trong ca.',
    listen: 'Nghe kênh này',
    listening: 'Đang nghe',
    talking: 'Đang đọc',
    replay: (text: string) => `Phát lại: ${text}`,
    openPhone: (name: string) => `Mở app của ${name} như trên điện thoại`,
    status: {
      departing: (n: number) => `Vừa nhận bàn ${n}`,
      enroute: (n: number) => `Đang tới bàn ${n}`,
      serving: (n: number) => `Ở bàn ${n}`,
      idle: 'Rảnh',
      break: 'Nghỉ',
    },
    soundTitle: 'Bật âm thanh để nhận việc',
    soundBody: 'Đeo tai nghe Bluetooth rồi bấm nút dưới. Mỗi việc mới có tiếng chuông và câu đọc, việc gấp có hai tiếng chuông và rung.',
    soundOn: 'Bật âm thanh',
    soundOff: 'Tắt âm thanh',
    who: 'Bạn là ai?',
    whoHint: 'Chọn tên để nhận đúng việc của mình.',
    switchStaff: 'Đổi nhân viên',
    back: 'Về bảng quản lý',
    sim: 'Dữ liệu mô phỏng, chưa nối camera thật.',
  },
  en: {
    task: (k: TaskKind) => TASK_EN[k],
    role: (r: Role, zone?: string) => `${ROLE_EN[r]}${zone ? `, zone ${zone}` : ''}`,
    table: 'Table',
    assignedAt: 'Assigned',
    autoConfirm: 'No need to tap anything: the camera confirms when you reach the table.',
    confirmed: 'The camera confirmed you are at the table.',
    free: 'Free',
    onBreak: 'On break',
    nextHint: 'Your next task will be read straight into your earbud.',
    heard: 'Heard in the earbud',
    empty: 'No announcements yet this shift.',
    listen: 'Listen in',
    listening: 'Listening',
    talking: 'Speaking',
    replay: (text: string) => `Replay: ${text}`,
    openPhone: (name: string) => `Open ${name}'s app as on a phone`,
    status: {
      departing: (n: number) => `Just got table ${n}`,
      enroute: (n: number) => `Heading to table ${n}`,
      serving: (n: number) => `At table ${n}`,
      idle: 'Free',
      break: 'Break',
    },
    soundTitle: 'Turn on sound to get tasks',
    soundBody: 'Put on your Bluetooth earbud and tap the button below. Every new task plays a chime and a spoken line; urgent ones chime twice and vibrate.',
    soundOn: 'Turn on sound',
    soundOff: 'Turn off sound',
    who: 'Who are you?',
    whoHint: 'Pick your name to get only your own tasks.',
    switchStaff: 'Switch staff',
    back: 'Back to the manager dashboard',
    sim: 'Simulated data, no real cameras connected.',
  },
} satisfies Record<Lang, unknown>;

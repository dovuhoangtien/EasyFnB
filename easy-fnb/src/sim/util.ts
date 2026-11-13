export const hms = (h: number, m: number, s = 0) => h * 3600 + m * 60 + s;

const pad = (n: number) => String(n).padStart(2, '0');

/** Giờ trong ngày, ví dụ 19:24:05 */
export function clock(t: number, withSeconds = true) {
  const s = Math.floor(t) % 86400;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return withSeconds ? `${pad(h)}:${pad(m)}:${pad(s % 60)}` : `${pad(h)}:${pad(m)}`;
}

/** Thời lượng dạng đồng hồ, ví dụ 1:05 */
export function mmss(sec: number) {
  const v = Math.max(0, Math.floor(sec));
  return `${Math.floor(v / 60)}:${pad(v % 60)}`;
}

/** Thời lượng dạng chữ, ví dụ "1 phút 5 giây" */
export function durText(sec: number) {
  const v = Math.max(0, Math.round(sec));
  if (v < 60) return `${v} giây`;
  const m = Math.floor(v / 60);
  const s = v % 60;
  return s ? `${m} phút ${s} giây` : `${m} phút`;
}

/** Số thập phân kiểu Việt Nam: 1,5 */
export const dec = (n: number, digits = 1) => n.toFixed(digits).replace('.', ',');

export function median(values: number[]) {
  if (!values.length) return NaN;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/** Bỏ dấu nhưng giữ chữ hoa, để giọng tiếng Anh đọc tên cho đúng */
export function plain(s: string) {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D");
}

/** Bỏ dấu tiếng Việt để so khớp câu hỏi */
export function fold(s: string) {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase();
}

export function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

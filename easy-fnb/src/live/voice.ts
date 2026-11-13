/**
 * Âm báo cho app nhân viên chạy thật: tiếng chuông WebAudio, rung, và đọc tiếng Việt.
 * Cùng cách làm với src/sim/voice.ts nhưng không dính tới bộ mô phỏng.
 * Trình duyệt chặn âm thanh tự phát, nên phải gọi unlockAudio() trong một lần bấm.
 */

import { apiUrl } from './api';

const synth = typeof window !== 'undefined' && 'speechSynthesis' in window ? window.speechSynthesis : null;
let audio: AudioContext | null = null;
let viVoice: SpeechSynthesisVoice | null = null;

function quality(v: SpeechSynthesisVoice) {
  let q = 0;
  if (/natural|online|neural/i.test(v.name)) q += 4;
  if (/google/i.test(v.name)) q += 2;
  return q;
}

function pickVoice() {
  if (!synth) return;
  const vi = synth
    .getVoices()
    .filter((v) => v.lang.toLowerCase().replace('_', '-').startsWith('vi'))
    .sort((a, b) => quality(b) - quality(a));
  viVoice = vi[0] ?? null;
}

if (synth) {
  pickVoice();
  synth.addEventListener('voiceschanged', pickVoice);
}

export const speechSupported = () => !!synth;
/** Máy chủ có giọng đọc Việt (VieNeu, hoặc Piper dự phòng): luôn dùng khi có */
let serverVoice = false;
if (typeof window !== 'undefined') {
  fetch(apiUrl('/api/tts/status'))
    .then((r) => r.json())
    .then((j: { enabled?: boolean }) => {
      serverVoice = !!j.enabled;
    })
    .catch(() => {});
}
/** Nhịp đọc kiểu loa báo nhận tiền: chậm hơn giọng gốc, mỗi cụm một hơi, có khoảng lặng ở giữa */
const RATE = 0.88;
const PAUSE_COMMA_MS = 380;
const PAUSE_STOP_MS = 600;

interface Clip {
  text: string;
  /** khoảng lặng sau cụm này */
  pause: number;
}

/** "Gấp. Bàn B2, gọi phục vụ" -> ba cụm đọc riêng. Cụm ngắn còn được máy chủ giữ sẵn nên phát ngay. */
function clips(text: string): Clip[] {
  const out: Clip[] = [];
  for (const m of text.matchAll(/([^.,;!?]+)([.,;!?]?)/g)) {
    const t = m[1].trim();
    if (t) out.push({ text: t, pause: m[2] === ',' || m[2] === ';' ? PAUSE_COMMA_MS : PAUSE_STOP_MS });
  }
  return out;
}

const ttsUrl = (text: string) => apiUrl(`/api/tts?text=${encodeURIComponent(text)}`);

const player = typeof Audio !== 'undefined' ? new Audio() : null;
if (player) {
  player.defaultPlaybackRate = RATE;
  player.preservesPitch = true;
}
const queue: Clip[] = [];
let busy = false;
function playNext() {
  if (!player || busy) return;
  const next = queue.shift();
  if (!next) return;
  busy = true;
  let over = false;
  const after = () => {
    if (over) return;
    over = true;
    window.setTimeout(() => {
      busy = false;
      playNext();
    }, next.pause);
  };
  player.onended = after;
  player.onerror = after;
  player.src = ttsUrl(next.text);
  player.playbackRate = RATE;
  void player.play().catch(after);
}

export const hasVietnameseVoice = () => !!viVoice || serverVoice;

/** Gọi trong sự kiện bấm nút: mở khoá loa và giọng đọc cho cả ca */
export function unlockAudio() {
  try {
    audio ??= new AudioContext();
    if (audio.state === 'suspended') void audio.resume();
  } catch {
    audio = null;
  }
  if (player) {
    // mở khoá phát file âm thanh (giọng từ máy chủ) trong lần bấm này
    player.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
    void player.play().catch(() => {});
  }
  if (synth) {
    // iOS chỉ cho đọc sau khi đã đọc một lần trong thao tác của người dùng
    const u = new SpeechSynthesisUtterance(' ');
    u.volume = 0;
    synth.speak(u);
    pickVoice();
  }
}

/** Tiếng chuông: việc gấp kêu hai nốt cao, việc thường một nốt, huỷ thì một nốt trầm */
export function beep(kind: 'urgent' | 'normal' | 'cancel' = 'normal') {
  if (!audio) return;
  if (audio.state === 'suspended') void audio.resume();
  const notes = kind === 'urgent' ? [988, 1319, 988, 1319] : kind === 'normal' ? [880, 1175] : [523];
  const t0 = audio.currentTime + 0.02;
  notes.forEach((freq, i) => {
    const osc = audio!.createOscillator();
    const gain = audio!.createGain();
    const t = t0 + i * 0.16;
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.22, t + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.15);
    osc.connect(gain).connect(audio!.destination);
    osc.start(t);
    osc.stop(t + 0.17);
  });
}

export function vibrate(pattern: number | number[]) {
  try {
    navigator.vibrate?.(pattern);
  } catch {
    // máy không hỗ trợ rung
  }
}

/** Đọc một câu tiếng Việt; câu mới không cắt câu đang đọc.
 * Ưu tiên giọng của máy chủ (VieNeu, nghe tự nhiên hơn giọng có sẵn của điện thoại/Windows);
 * máy chủ không có giọng thì mới dùng giọng Việt của trình duyệt. */
export function speak(text: string) {
  const parts = clips(text);
  if (serverVoice && player) {
    // gọi trước cả câu để máy chủ làm sẵn các cụm, tới lượt là phát ngay
    for (const c of parts.slice(1)) void fetch(ttsUrl(c.text)).catch(() => {});
    queue.push(...parts);
    playNext();
    return;
  }
  // không có giọng Việt thì im: giọng tiếng Anh đọc chữ Việt nghe sai và gây khó chịu
  if (!synth || !viVoice) return;
  for (const c of parts) {
    const u = new SpeechSynthesisUtterance(c.text);
    u.lang = 'vi-VN';
    u.voice = viVoice;
    u.rate = RATE;
    synth.speak(u);
  }
}

/** Chuông, rung rồi đọc: dùng khi có việc mới */
export function announce(text: string, urgent: boolean) {
  beep(urgent ? 'urgent' : 'normal');
  vibrate(urgent ? [120, 70, 120, 70, 120] : [90, 60, 90]);
  window.setTimeout(() => speak(text), urgent ? 950 : 650);
}

export function stopSpeaking() {
  synth?.cancel();
  queue.length = 0;
  busy = false;
  player?.pause();
}

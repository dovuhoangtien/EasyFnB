import { useSyncExternalStore } from 'react';
import type { Spoken } from './engine';
import { STAFF, staffDef } from './model';
import { engine } from './store';
import { plain } from './util';

/**
 * Tai nghe nhân viên. Mỗi nhân viên là một kênh riêng: chỉ nghe việc giao cho mình.
 * Người quản lý bật kênh nào thì nghe đúng những gì người đó nghe.
 * Bản demo dùng Web Speech API của trình duyệt; bản thật phát câu tạo sẵn
 * bằng Google Chirp 3 HD trên app Android, qua tai nghe Bluetooth.
 */

export type Lang = 'vi' | 'en';

/** Một câu cần đọc: thông báo thật của ca, hoặc câu xác nhận khi bật kênh */
export interface Line {
  id: number;
  staff: string;
  priority: 1 | 2 | 3;
  text: string;
  textEn: string;
}

export interface VoiceState {
  lang: Lang;
  listening: string[];
  speaking: Line | null;
  supported: boolean;
  hasVoice: boolean;
  voiceName?: string;
}

const synth = typeof window !== 'undefined' && 'speechSynthesis' in window ? window.speechSynthesis : null;
const MAX_QUEUE = 4;
const PITCH = [1, 0.88, 1.12, 0.95, 1.06];
const GENDER: Record<string, 'f' | 'm'> = { lan: 'f', thao: 'f', minh: 'm', hung: 'm', tu: 'm' };
const FEMALE = /zira|aria|jenny|hoaimy|samantha|female|ava|emma|michelle|sonia|libby|susan|hazel|linh/i;

/** Câu của hệ thống, không thuộc kênh nhân viên nào */
export const SYSTEM = 'he-thong';

let lang: Lang = 'vi';
let langChosen = false;
const listen = new Set<string>();
const voices: Record<Lang, SpeechSynthesisVoice[]> = { vi: [], en: [] };
const queue: Line[] = [];
let speaking: Line | null = null;
let busy = false;
let audio: AudioContext | null = null;
let localId = -1;

const listeners = new Set<() => void>();
let snapshot = makeSnapshot();

function makeSnapshot(): VoiceState {
  return {
    lang,
    listening: [...listen],
    speaking,
    supported: !!synth,
    hasVoice: voices[lang].length > 0,
    voiceName: voices[lang][0]?.name,
  };
}

function changed() {
  snapshot = makeSnapshot();
  listeners.forEach((fn) => fn());
}

// ---------- chọn giọng ----------
function quality(v: SpeechSynthesisVoice) {
  let q = 0;
  if (/natural|online|neural/i.test(v.name)) q += 4;
  if (/google/i.test(v.name)) q += 2;
  if (/en-us/i.test(v.lang)) q += 1;
  return q;
}

function pickVoices() {
  if (!synth) return;
  const all = synth.getVoices();
  const sorted = (list: SpeechSynthesisVoice[]) => [...list].sort((a, b) => quality(b) - quality(a));
  voices.vi = sorted(all.filter((v) => v.lang.toLowerCase().startsWith('vi')));
  voices.en = sorted(all.filter((v) => v.lang.toLowerCase().startsWith('en')));
  // Máy không có giọng tiếng Việt thì mặc định đọc tiếng Anh cho rõ, trừ khi người dùng đã tự chọn
  if (!langChosen && all.length) lang = voices.vi.length || !voices.en.length ? 'vi' : 'en';
  changed();
}

if (synth) {
  pickVoices();
  synth.addEventListener('voiceschanged', pickVoices);
}

/** Mỗi kênh một giọng (nếu máy có nhiều giọng tốt) hoặc một cao độ, để nghe là biết của ai */
function voiceFor(staff: string) {
  const list = voices[lang];
  const idx = Math.max(0, STAFF.findIndex((s) => s.id === staff));
  if (!list.length) return { voice: null, pitch: PITCH[idx] ?? 1 };
  const best = quality(list[0]);
  const pool = list.filter((v) => quality(v) >= best - 1);
  // Nữ đọc giọng nữ, nam giọng nam nếu máy có; trùng giọng thì đổi cao độ
  const g = GENDER[staff] ?? 'm';
  const female = pool.filter((v) => FEMALE.test(v.name));
  const male = pool.filter((v) => !FEMALE.test(v.name));
  const side = g === 'f' ? (female.length ? female : pool) : male.length ? male : pool;
  const k = Math.max(0, STAFF.filter((s) => (GENDER[s.id] ?? 'm') === g).findIndex((s) => s.id === staff));
  const reuse = Math.floor(k / side.length);
  return { voice: side[k % side.length], pitch: reuse ? (k % 2 ? 0.9 : 1.1) : 1 };
}

// ---------- chuông báo trước mỗi câu ----------
function unlockAudio() {
  try {
    audio ??= new AudioContext();
    if (audio.state === 'suspended') void audio.resume();
  } catch {
    audio = null;
  }
}

function chime(priority: 1 | 2 | 3) {
  if (!audio) return;
  const notes = priority === 1 ? [988, 1319] : priority === 2 ? [880] : [659];
  const t0 = audio.currentTime + 0.02;
  notes.forEach((freq, i) => {
    const osc = audio!.createOscillator();
    const gain = audio!.createGain();
    const t = t0 + i * 0.17;
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.16, t + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.16);
    osc.connect(gain).connect(audio!.destination);
    osc.start(t);
    osc.stop(t + 0.18);
  });
}

// ---------- hàng đợi đọc ----------
export const textFor = (line: Pick<Line, 'text' | 'textEn'>, l: Lang) => (l === 'en' ? line.textEn : line.text);

function enqueue(line: Line) {
  if (queue.length >= MAX_QUEUE) {
    // Dồn quá nhiều thì bỏ câu ít gấp nhất, cũ nhất
    const low = queue.findIndex((q) => q.priority === 3);
    queue.splice(low >= 0 ? low : 0, 1);
  }
  if (line.priority === 1) {
    const at = queue.findIndex((q) => q.priority !== 1);
    queue.splice(at < 0 ? queue.length : at, 0, line);
  } else {
    queue.push(line);
  }
  pump();
}

function pump() {
  if (busy) return;
  const line = queue.shift();
  if (!line) return;
  busy = true;
  speaking = line;
  changed();
  chime(line.priority);
  window.setTimeout(() => say(line), line.priority === 1 ? 420 : 280);
}

function say(line: Line) {
  let finished = false;
  const done = () => {
    if (finished) return;
    finished = true;
    busy = false;
    speaking = null;
    changed();
    window.setTimeout(pump, 220);
  };
  if (!synth) {
    window.setTimeout(done, 1600);
    return;
  }
  const u = new SpeechSynthesisUtterance(lang === 'en' ? plain(line.textEn) : line.text);
  const { voice, pitch } = voiceFor(line.staff);
  u.lang = lang === 'en' ? 'en-US' : 'vi-VN';
  if (voice) u.voice = voice;
  u.pitch = pitch;
  u.rate = lang === 'en' ? 1.04 : 1.02;
  u.onend = done;
  u.onerror = done;
  synth.speak(u);
  window.setTimeout(done, 9000); // phòng khi trình duyệt không báo đọc xong
}

function stopStaff(id?: string) {
  for (let i = queue.length - 1; i >= 0; i--) if (!id || queue[i].staff === id) queue.splice(i, 1);
  if (speaking && (!id || speaking.staff === id)) synth?.cancel();
}

engine.onSpeak = (s: Spoken) => {
  if (listen.has(s.staff)) enqueue(s);
};

// ---------- điều khiển ----------
export function setLang(l: Lang) {
  langChosen = true;
  if (l === lang) return;
  lang = l;
  stopStaff();
  changed();
}

function confirmLine(id: string): Line {
  const name = staffDef(id).name;
  return {
    id: localId--,
    staff: id,
    priority: 3,
    text: `Đang nghe kênh của ${name}`,
    textEn: `Now listening to ${name}'s channel`,
  };
}

export function setListen(id: string, on: boolean) {
  unlockAudio();
  if (on) {
    listen.add(id);
    enqueue(confirmLine(id));
  } else {
    listen.delete(id);
    stopStaff(id);
  }
  changed();
}

/** Chỉ nghe đúng một kênh, dùng cho app trên điện thoại của nhân viên */
export function listenOnly(id: string) {
  unlockAudio();
  for (const other of [...listen]) if (other !== id) setListen(other, false);
  if (!listen.has(id)) setListen(id, true);
}

export function setListenAll(on: boolean) {
  unlockAudio();
  if (on) {
    STAFF.forEach((s) => listen.add(s.id));
    enqueue({ id: localId--, staff: SYSTEM, priority: 3, text: 'Đang nghe tất cả các kênh', textEn: 'Listening to all channels' });
  } else {
    listen.clear();
    stopStaff();
  }
  changed();
}

/** Phát lại một câu nhân viên đã nghe */
export function replay(line: Line) {
  unlockAudio();
  enqueue({ ...line, id: localId-- });
}

export function useVoice() {
  return useSyncExternalStore(
    (fn) => {
      listeners.add(fn);
      return () => {
        listeners.delete(fn);
      };
    },
    () => snapshot,
  );
}

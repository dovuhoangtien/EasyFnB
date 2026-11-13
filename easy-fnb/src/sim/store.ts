import { useSyncExternalStore } from 'react';
import { Engine } from './engine';

export const engine = new Engine();

// Chỉ khi chạy dev: cho phép soi bộ mô phỏng từ console
if (import.meta.env.DEV) Object.assign(window, { __engine: engine });

let last = performance.now();
let lastNotify = 0;

function frame(now: number) {
  engine.wall = now;
  const real = Math.min(0.25, (now - last) / 1000);
  last = now;
  if (engine.running) {
    let sim = real * engine.speed;
    while (sim > 0) {
      const d = Math.min(sim, 1);
      engine.step(d);
      sim -= d;
    }
  }
  if (now - lastNotify > 66) {
    lastNotify = now;
    engine.notify();
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

/** Đăng ký component với bộ mô phỏng, render lại khoảng 15 lần mỗi giây */
export function useSim() {
  useSyncExternalStore(engine.subscribe, () => engine.version);
  return engine;
}

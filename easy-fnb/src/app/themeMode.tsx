import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { Theme } from '@astryxdesign/core/theme';
import { easyTheme } from '../theme';

export type ThemeChoice = 'light' | 'dark' | 'system';
const KEY = 'ez-theme';

function saved(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY);
    return v === 'light' || v === 'dark' ? v : 'system';
  } catch {
    return 'system';
  }
}

const Ctx = createContext<{ choice: ThemeChoice; setChoice: (c: ThemeChoice) => void }>({ choice: 'system', setChoice: () => {} });

/** Giao diện sáng hoặc tối: mặc định theo máy, người dùng chọn thì nhớ trên máy đó */
export function ThemeMode({ children }: { children: ReactNode }) {
  const [choice, set] = useState<ThemeChoice>(saved);
  const setChoice = useCallback((c: ThemeChoice) => {
    set(c);
    try {
      if (c === 'system') localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, c);
    } catch {
      /* chế độ riêng tư: chỉ đổi trong lần mở này */
    }
  }, []);
  return (
    <Ctx.Provider value={{ choice, setChoice }}>
      <Theme theme={easyTheme} mode={choice}>
        {children}
      </Theme>
    </Ctx.Provider>
  );
}

export const useThemeChoice = () => useContext(Ctx);

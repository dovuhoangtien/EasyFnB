import { StrictMode, type ComponentProps } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link as RouterLink } from 'react-router';
import { LinkProvider } from '@astryxdesign/core/Link';
import { ToastViewport } from '@astryxdesign/core/Toast';
import './index.css';
import App from './App.tsx';
import { ThemeMode } from './app/themeMode';

/** Link của Astryx đi qua react-router; link ra ngoài vẫn là thẻ a thường */
function AppLink({ href, ...rest }: ComponentProps<'a'>) {
  if (!href || /^(https?:|mailto:|tel:|#)/.test(href)) return <a href={href} {...rest} />;
  return <RouterLink to={href} {...rest} />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeMode>
      <BrowserRouter>
        <LinkProvider component={AppLink}>
          <ToastViewport>
            <App />
          </ToastViewport>
        </LinkProvider>
      </BrowserRouter>
    </ThemeMode>
  </StrictMode>,
);

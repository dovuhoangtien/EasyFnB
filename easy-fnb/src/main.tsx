import { StrictMode, type ComponentProps } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link as RouterLink } from 'react-router';
import { Theme } from '@astryxdesign/core/theme';
import { LinkProvider } from '@astryxdesign/core/Link';
import { ToastViewport } from '@astryxdesign/core/Toast';
import './index.css';
import App from './App.tsx';
import { easyTheme } from './theme';

/** Link của Astryx đi qua react-router; link ra ngoài vẫn là thẻ a thường */
function AppLink({ href, ...rest }: ComponentProps<'a'>) {
  if (!href || /^(https?:|mailto:|tel:|#)/.test(href)) return <a href={href} {...rest} />;
  return <RouterLink to={href} {...rest} />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Theme theme={easyTheme} mode="system">
      <BrowserRouter>
        <LinkProvider component={AppLink}>
          <ToastViewport>
            <App />
          </ToastViewport>
        </LinkProvider>
      </BrowserRouter>
    </Theme>
  </StrictMode>,
);

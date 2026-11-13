import { defineTheme } from '@astryxdesign/core/theme';
import { neutralTheme } from '@astryxdesign/theme-neutral/built';

/**
 * Theme của Easy FnB: lấy theme neutral của Astryx làm nền, thêm một màu nhấn xanh chàm
 * (nút chính, mục đang chọn, logo) và để các màu xám ngả nhẹ theo màu nhấn cho đỡ lạnh.
 * Màu trạng thái (đỏ, vàng, xanh lá) vẫn là của Astryx, chỉ dùng để báo tình trạng.
 */
export const easyTheme = defineTheme({
  name: 'easy-fnb',
  extends: neutralTheme,
  color: { accent: ['#3a45e0', '#8f9bff'], neutralStyle: 'cool' },
  typography: {
    body: { family: 'Be Vietnam Pro', fallbacks: 'ui-sans-serif, system-ui, sans-serif' },
    code: { family: 'JetBrains Mono', fallbacks: 'ui-monospace, Consolas, monospace' },
  },
});

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type ProxyOptions } from 'vite'

// Máy chủ Easy FnB (FastAPI). Đổi bằng biến môi trường EASYFNB_API nếu chạy ở cổng khác.
const API_TARGET = process.env.EASYFNB_API ?? 'http://127.0.0.1:8080'  // không dùng localhost: Windows thử IPv6 trước, máy chủ chỉ nghe IPv4

const apiProxy: Record<string, ProxyOptions> = {
  '/api': {
    target: API_TARGET,
    changeOrigin: true,
    configure: (proxy) => {
      // Luồng sự kiện SSE phải đi thẳng tới trình duyệt, không được gom hay nén
      proxy.on('proxyRes', (proxyRes, _req, res) => {
        if (!String(proxyRes.headers['content-type'] ?? '').includes('text/event-stream')) return
        proxyRes.headers['cache-control'] = 'no-cache, no-transform'
        proxyRes.headers['x-accel-buffering'] = 'no'
        delete proxyRes.headers['content-length']
        // Máy chủ tắt giữa chừng thì đóng luôn phía trình duyệt để EventSource tự nối lại
        // (mặc định Vite để treo kết nối vì đã gửi header)
        const close = () => {
          if (!res.writableEnded) res.end()
        }
        proxyRes.on('close', close)
        proxyRes.on('error', close)
      })
    },
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // host: true để điện thoại trong cùng mạng Wi-Fi mở được app nhân viên
  server: { host: true, proxy: apiProxy },
  preview: { host: true, proxy: apiProxy },
})

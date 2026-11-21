import { defineConfig, loadEnv } from 'vite';

export default defineConfig(async ({ mode }) => {
  const override = loadEnv(mode, process.cwd(), 'HISOBCHI_').HISOBCHI_DEV_API;
  let target = 'http://127.0.0.1:8000';
  if (override) {
    try {
      const response = await fetch(new URL('/health', override), { signal: AbortSignal.timeout(1500) });
      if (response.ok && (await response.json()).service === 'hisobchi') target = override;
    } catch { /* Use the standard local API when a preview server has stopped. */ }
  }
  const contentPolicy = [
    "default-src 'self'", "script-src 'self'", "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:", "font-src 'self' data:", "worker-src 'self' blob:",
    "object-src 'none'", "base-uri 'none'", "form-action 'self'",
  ].join('; ');
  const securityMeta = {
    name: 'production-content-policy', apply: 'build',
    transformIndexHtml() {
      return [
        { tag:'meta', attrs:{ 'http-equiv':'Content-Security-Policy', content:contentPolicy }, injectTo:'head-prepend' },
        { tag:'meta', attrs:{ name:'referrer', content:'no-referrer' }, injectTo:'head-prepend' },
      ];
    },
  };
  return { plugins:[securityMeta], optimizeDeps:{include:['pdfmake/build/pdfmake','pdfmake/build/vfs_fonts','docx']}, server: { host: '127.0.0.1', port: 5173, proxy: { '/api': { target, changeOrigin: true } } } };
});

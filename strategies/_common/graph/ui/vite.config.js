import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  build: { assetsInlineLimit: 0 },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:9102",
        changeOrigin: true,
        configure(proxy) {
          proxy.on("proxyReq", (req) => req.removeHeader("origin"));
        },
      },
    },
  },
  test: { include: ["src/**/*.test.js"] },
});

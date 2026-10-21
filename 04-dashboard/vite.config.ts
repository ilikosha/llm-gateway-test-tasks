/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// Базовый путь задаётся переменной VITE_BASE_PATH (для GitHub Pages: "/<repo>/").
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const base = env.VITE_BASE_PATH ?? process.env.VITE_BASE_PATH ?? '/';

  return {
    base,
    plugins: [react()],
    build: {
      chunkSizeWarningLimit: 600, // Recharts в отдельном чанке ~525 kB
      rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } },
    },
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts'],
    },
  };
});

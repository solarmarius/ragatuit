import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts', // A file to run before each test file.
    coverage: {
      provider: 'v8', // or 'istanbul'
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/setupTests.ts',
        'src/vitest.setup.ts',
        'src/vite-env.d.ts',
        'eslint.config.js',
        'vite.config.ts',
        'src/mocks/', // Exclude the whole mocks directory
        'src/main.tsx', // It's okay to exclude the entry point
      ],
    },
  },
});

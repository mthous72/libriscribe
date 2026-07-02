import { defineConfig } from '@playwright/test'

/**
 * Responsive / layout regression tests.
 *
 * These build the production bundle, serve it with `vite preview`, and assert
 * the UI stays within the viewport (no horizontal overflow) at phone widths.
 * The frontend is checked in isolation — all `/api` calls are mocked in the
 * spec, so no backend is required.
 *
 * The tests use the Chromium that Playwright manages. In this repo's dev
 * container it is pre-installed (PLAYWRIGHT_BROWSERS_PATH); elsewhere run
 * `npx playwright install chromium` once before `npm run test:responsive`.
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:4174',
    trace: 'off',
  },
  webServer: {
    // Bind IPv4 explicitly: `vite preview` defaults to `localhost`, which on CI runners resolves
    // to IPv6 (::1) first, so Playwright polling http://127.0.0.1 never connects and times out.
    command: 'npm run build && npm run preview -- --port 4174 --strictPort --host 127.0.0.1',
    url: 'http://127.0.0.1:4174',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
})

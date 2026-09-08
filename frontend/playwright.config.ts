import { defineConfig, devices } from '@playwright/test'
export default defineConfig({
  testDir: '../tests/e2e',
  timeout: 60000,
  fullyParallel: false,
  workers: 1,
  use: { baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1536, height: 960 } } }],
})


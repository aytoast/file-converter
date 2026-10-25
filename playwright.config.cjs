const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests/web',
  fullyParallel: true,
  retries: 0,
  workers: 2,
  timeout: 30000,
  use: {
    baseURL: process.env.SITE_URL || 'http://127.0.0.1:8767',
    headless: true,
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
    screenshot: 'only-on-failure'
  },
  webServer: process.env.SITE_URL ? undefined : {
    command: 'python -m http.server 8767 --bind 127.0.0.1 --directory docs',
    url: 'http://127.0.0.1:8767',
    reuseExistingServer: !process.env.CI,
    stdout: 'ignore',
    stderr: 'ignore'
  }
});

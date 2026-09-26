import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for Agentic AI STLC Pipeline
 * Generated tests will use this configuration
 */
export default defineConfig({
  testDir: './tests',
  // Generated suites are validated separately after selector healing;
  // CI executes the curated committed regression suites.
  testIgnore: '**/generated/**',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['line'],
  ],
  
  use: {
    baseURL: process.env.BASE_URL || 'https://staging.example.com',
    // practicesoftwaretesting.com (and saucedemo) use data-test attributes
    testIdAttribute: 'data-test',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },

  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--disable-web-security', '--disable-features=IsolateOrigins'],
        },
      },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Mobile viewports
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // webServer disabled by default - enable when you have a dev server
  // webServer: {
  //   command: 'npm run start:dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120000,
  // },

  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 100,
      threshold: 0.2,
    },
  },

  outputDir: 'test-results/',
});
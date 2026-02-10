import { defineConfig, devices } from "@playwright/test";

const PORT = process.env.PORT || 3000;

const baseURL = `http://localhost:${PORT}`;

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  // Timeout per test
  timeout: 30 * 1000,
  testDir: "./__tests__",
  outputDir: "./test-results",

  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  maxFailures: process.env.CI ? 3 : 0,
  /* Opt out of parallel tests on CI. */
  workers: 1,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [["html", { outputFolder: "./report" }]],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    baseURL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: "retain-on-failure",
    video: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  webServer: {
    command: !process.env.CI ? `cd ../drive && yarn dev --port ${PORT}` : "",
    url: baseURL,
    timeout: 120 * 1000,
    reuseExistingServer: true,
  },
  /* Configure projects for major browsers */
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        locale: "en-US",
        timezoneId: "Europe/Paris",
        contextOptions: {
          permissions: ["clipboard-read", "clipboard-write"],
        },
      },
    },
    {
      name: "webkit",
      use: {
        ...devices["Desktop Safari"],
        locale: "en-US",
        timezoneId: "Europe/Paris",
        contextOptions: {
          permissions: ["clipboard-read"],
        },
      },
    },
    {
      name: "firefox",
      use: {
        ...devices["Desktop Firefox"],
        locale: "en-US",
        timezoneId: "Europe/Paris",
        launchOptions: {
          firefoxUserPrefs: {
            "dom.events.asyncClipboard.readText": true,
            "dom.events.testing.asyncClipboard": true,
          },
        },
      },
    },
  ],
});

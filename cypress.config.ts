import { defineConfig } from "cypress";

export default defineConfig({
  reporter: "mocha-junit-reporter",
  reporterOptions: {
    mochaFile: "test-results/junit-[hash].xml",
  },
  video: true,
  videoCompression: true,
  env: {
    // Detect CI environment - only check CYPRESS_CI
    CI: `${process.env.CYPRESS_CI}` === "true",
  },
  e2e: {
    baseUrl: "http://localhost:8000",
    setupNodeEvents(on, config) {
      // No server startup needed - server should be running on localhost:8000
      // For CI, use: npm run e2e -- --config baseUrl=http://your-ci-server-url
      on("before:browser:launch", (browser, launchOptions) => {
        if (browser.family === "chromium" && browser.name !== "electron") {
          launchOptions.args.push("--no-sandbox");
          launchOptions.args.push("--disable-dev-shm-usage");
        }
        return launchOptions;
      });
      return config;
    },
  },
});

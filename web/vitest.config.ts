import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte({ hot: !process.env.VITEST })],
  test: {
    environment: "jsdom",
    globals: true,
    passWithNoTests: true,
    setupFiles: ["./src/setupTests.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html", "lcov"],
      exclude: [
        "node_modules/**",
        "dist/**",
        "**/*.d.ts",
        "**/*.config.*",
        "**/*.test.*",
        "**/setupTests.ts",
      ],
      // TODO: re-enable thresholds when source files exist
      // thresholds: {
      //   lines: 85,
      //   functions: 85,
      //   branches: 80,
      //   statements: 85,
      // },
    },
  },
});

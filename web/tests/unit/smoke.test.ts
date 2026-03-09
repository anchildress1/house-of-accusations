import { describe, it, expect } from "vitest";

describe("test infrastructure", () => {
  it("vitest and jsdom are configured", () => {
    const el = document.createElement("div");
    expect(el).toBeInstanceOf(HTMLDivElement);
  });
});

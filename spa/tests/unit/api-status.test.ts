import { describe, it, expect } from "vitest";
import { determineApiStatus } from "../../src/application/services/api-status.js";

describe("API status", () => {
  it("is a success when no stop failed", () => {
    expect(determineApiStatus(3, 0)).toBe("success");
  });

  it("is degraded when only some stops failed", () => {
    expect(determineApiStatus(2, 1)).toBe("degraded");
  });

  it("is an error when every stop failed", () => {
    expect(determineApiStatus(0, 4)).toBe("error");
  });
});

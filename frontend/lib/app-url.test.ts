import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { resolveAuthCallbackUrl } from "./app-url";

describe("resolveAuthCallbackUrl", () => {
  it("always uses the production app host on deepfoot.io", () => {
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "deepfoot.io", protocol: "https:", port: "" }),
      "https://app.deepfoot.io/auth/callback"
    );
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "www.deepfoot.io", protocol: "https:", port: "" }),
      "https://app.deepfoot.io/auth/callback"
    );
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "app.deepfoot.io", protocol: "https:", port: "" }),
      "https://app.deepfoot.io/auth/callback"
    );
  });

  it("stays on the same localhost origin (never app.localhost when the user is on localhost)", () => {
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "localhost", protocol: "http:", port: "3000" }),
      "http://localhost:3000/auth/callback"
    );
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "127.0.0.1", protocol: "http:", port: "3000" }),
      "http://127.0.0.1:3000/auth/callback"
    );
  });

  it("keeps app.localhost when the user is already on that host", () => {
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "app.localhost", protocol: "http:", port: "3000" }),
      "http://app.localhost:3000/auth/callback"
    );
  });
});

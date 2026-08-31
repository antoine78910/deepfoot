import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { resolveAuthCallbackUrl } from "./app-url";
import {
  isAppAuthHost,
  isOAuthCallbackParams,
  oauthHopHref,
  sanitizeNextPath,
} from "./oauth-callback";

describe("resolveAuthCallbackUrl", () => {
  it("keeps PKCE on the same origin (never jump deepfoot.io → app.deepfoot.io)", () => {
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "deepfoot.io", protocol: "https:", port: "" }),
      "https://deepfoot.io/auth/callback"
    );
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "www.deepfoot.io", protocol: "https:", port: "" }),
      "https://www.deepfoot.io/auth/callback"
    );
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "app.deepfoot.io", protocol: "https:", port: "" }),
      "https://app.deepfoot.io/auth/callback"
    );
  });

  it("stays on the same localhost origin", () => {
    assert.equal(
      resolveAuthCallbackUrl({ hostname: "localhost", protocol: "http:", port: "3000" }),
      "http://localhost:3000/auth/callback"
    );
  });
});

describe("oauth helpers", () => {
  it("treats app.* as the auth host", () => {
    assert.equal(isAppAuthHost("app.deepfoot.io"), true);
    assert.equal(isAppAuthHost("app.localhost:3000"), true);
    assert.equal(isAppAuthHost("deepfoot.io"), false);
    assert.equal(isAppAuthHost("www.deepfoot.io"), false);
  });

  it("hops Google OAuth from the marketing site to the app host", () => {
    assert.equal(
      oauthHopHref({ hostname: "deepfoot.io", kind: "sign-in" }),
      "https://app.deepfoot.io/sign-in?oauth=google"
    );
    assert.equal(
      oauthHopHref({ hostname: "www.deepfoot.io", kind: "sign-up" }),
      "https://app.deepfoot.io/sign-up?oauth=google"
    );
    assert.equal(oauthHopHref({ hostname: "app.deepfoot.io", kind: "sign-in" }), null);
  });

  it("detects OAuth callback query params", () => {
    assert.equal(isOAuthCallbackParams(new URLSearchParams("code=abc")), true);
    assert.equal(isOAuthCallbackParams(new URLSearchParams("error=invalid_request&error_code=bad_oauth_state")), true);
    assert.equal(isOAuthCallbackParams(new URLSearchParams("next=/matches")), false);
  });

  it("drops next paths that are OAuth error loops", () => {
    assert.equal(sanitizeNextPath("/matches"), "/matches");
    assert.equal(sanitizeNextPath("/?error=invalid_request&error_code=bad_oauth_state"), null);
    assert.equal(sanitizeNextPath("https://evil.com"), null);
  });
});

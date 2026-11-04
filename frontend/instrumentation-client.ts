// This file configures the initialization of Sentry on the client.
// The added config here will be used whenever a users loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";
import { sentryBaseOptions } from "./sentry.options";

Sentry.init({
  ...sentryBaseOptions(),
  integrations: [Sentry.replayIntegration()],
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0.1,
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;

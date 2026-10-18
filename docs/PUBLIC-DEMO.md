# Public demo and Quickstart

The approved public demo is served through Cloudflare Tunnel to the actual local application. It includes the real API, storage services and Docker execution backend. It does not publish a static imitation of those features.

Current demo: https://cars-wellness-considered-yea.trycloudflare.com

Quickstart: https://cars-wellness-considered-yea.trycloudflare.com/quickstart

The Quickstart is public. Start building creates a private browser workspace without a login/signup screen; internal session and tenant permissions still protect project data. Personal AI/search keys are managed in Profile & settings and encrypted at rest. No user inherits host provider keys. The app uses Secure cookies for HTTPS requests, HttpOnly and SameSite Strict sessions, an explicit allowed origin and the request-protection header for mutations. Database, embedding and Docker management ports remain local.

The original allied-motel-suited-shops hostname expired upstream and was replaced. The current hostname is also temporary. Free independent hosting is awaiting the user-owned server described in [FREE-HOSTING.md](FREE-HOSTING.md).

The link depends on this Windows computer, its local services and the tunnel process staying running. A new tunnel gets a new address. Cloudflare Quick Tunnels have no uptime guarantee, support up to 200 in-flight requests and do not support SSE. The current UI uses polling. See [Cloudflare's documentation](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

## Manage the demo

`scripts/start-public.ps1` reuses the recorded live tunnel or starts a new one with the installed official cloudflared binary. It saves the actual URL and process identity in `data/collective/public-tunnel.json`, then updates the explicit allowed origin in the ignored `.env.collective` file. Restart the API with `scripts/restart-app.ps1` after a new origin is assigned. Model provider configuration remains unchanged.

`scripts/stop-public.ps1` stops only the managed tunnel after checking its PID and process start time. Local application services remain running. Stopping the tunnel removes public access. This demo is not an always-on cloud deployment; that needs separately provisioned persistent hosting for the workers, storage and sandbox runtime.

## Verified on 17 October 2026

The full backend suite passed 32 tests with one provider test skipped after the BYOK migration. A later five-test focused suite also covered the dedicated personal admission connection and validation errors that cannot echo keys. No live provider inference was performed. The comprehensive beginner guide now includes eight step-by-step lessons, expected results, status explanations, a glossary and a real downloadable Python exercise. See [BYOK.md](BYOK.md) for current behavior and the response reports under `data/collective/` for live publication checks.

Earlier checks before the no-login/BYOK update:

- Fresh real sandbox inspection and behavior checks passed for unprivileged execution, read-only root, no network, resource limits, absent provider credentials, absent Docker socket and denied paths. Separate run workspaces were checked for file isolation.
- Nineteen backend contract/authentication checks passed, including HTTPS session flags, anonymous denial and origin/request protection. No provider inference was invoked.
- Four local browser checks passed for the existing workspace, evidence views, Quickstart and all 14 navigation destinations. The guide contains no em dashes and its mobile layout has no horizontal overflow.
- Three browser checks passed through the actual public HTTPS hostname. Actual browser sign-in, secure cookies, original artifact SHA-256, anonymous denial, a second tenant's denied memory/artifact access and rejected foreign-origin mutation were verified. The public sign-in/access check passed again after tightening its awaited assertion.

Reports: `data/collective/sandbox-verification-latest.json` and `data/collective/public-verification.json`. The local infrastructure remains separate from provider quality: no new autonomous Groq run, Safeguard model evaluation or remote MCP execution is claimed.

Current browser verification: four checks passed through the replacement public HTTPS hostname, covering Start building, personal connection management, beginner navigation, real artifact downloads and tenant isolation. Seven local regression cases passed across the main run and a focused workflow rerun; the explicit restart-only workflow case was skipped. The workflow test now reselects its project after reload, since new browser workspaces also contain an initial project. Provider inference calls during these checks: zero.

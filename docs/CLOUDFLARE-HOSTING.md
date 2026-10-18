# ENGRAM deployment using Cloudflare startup credits

Status: the ENGRAM ENGINE home page, beginner quickstart, illustrated Medium article and published evidence are deployed to https://engram-collective.spring-cherry-c778.workers.dev. Browser OAuth is connected and the existing Worker was reused. Containers and R2 are enabled for this account. The private artifact bucket and protected storage service are deployed; two real storage integration tests passed. The agent API is temporarily proxied through the existing laptop tunnel. Backend migration is incomplete.

## Deployed and verified

- Worker source and configuration: `infra/cloudflare/worker.mjs` and `infra/cloudflare/wrangler.jsonc`.
- Static assets are uploaded to Cloudflare, rather than fetched from the laptop. Quickstart and evidence remain available independently of the local runtime.
- `/deployment-status` explicitly reports `laptop_independent_backend: false` until the backend is migrated. Every HTML page displays the current hosting boundary.
- Only `/api` routes proxy to the fixed configured backend. Authenticated responses and artifact downloads are not cached. Cross-origin mutations and requests without the protection header are rejected.
- The actual public HTTPS browser test passed: Start building, secure HttpOnly Strict session cookies, artifact upload/download with SHA-256 verification, tenant separation and origin rejection. This test used the real local backend through Cloudflare and made zero provider calls.
- Local database configuration was inspected without disclosing credentials: PostgreSQL, FalkorDB and Qdrant all use loopback endpoints. No existing managed cloud database connections were found in the active configuration.
- Billing/credit APIs returned authorization errors for this OAuth login. Credit balance and product coverage have not been verified.

## Next user action

R2 activation is complete. Configure durable PostgreSQL, TLS-enabled FalkorDB and Qdrant endpoints in the ignored `.env.cloudflare.runtime`, then finish and validate the runtime image. The local Docker image build hit a full C drive and WSL I/O errors; a completed image and cloud deployment have not been verified. The latest public UI check passed home, quickstart and Medium imagery at desktop and mobile sizes, while actual Start building returned HTTP 503 from the affected local backend.

Do not turn off the laptop expecting agent execution to continue yet. Cloudflare deployment access and a working permanent website are complete; durable backend deployment remains outstanding.

Cloudflare can provide the public application and Linux compute independently of the laptop. This requires adapting the deployment and durable storage. The existing Oracle VM installer does not deploy onto Cloudflare.

## Proposed placement

| Component | Placement and required adaptation |
| --- | --- |
| Public website | Workers static assets or Pages, with a stable Cloudflare hostname or existing custom domain |
| FastAPI and DeepAgents workers | Cloudflare Containers; explicit lifecycle and recovery from persistent jobs |
| Code execution | Cloudflare Sandboxes, or documented Docker-in-Docker with the existing non-root, no-network child sandbox restrictions revalidated |
| Published artifacts | Private R2 objects with authorized downloads, immutable content hashes and a local cache |
| SQL records and checkpoints | Durable managed PostgreSQL; an external provider has separate billing and credentials |
| Mandatory graph context | Durable FalkorDB Cloud or another properly persisted FalkorDB deployment; retain FalkorDB for Track 2 |
| Vector index | Managed Qdrant initially; Vectorize requires a tested Mem0 integration and deliberate reindexing |
| Embeddings | Preserve the current model in a suitable container initially, or migrate to Workers AI with a complete re-embedding of stored vectors |
| Mem0 history and workspace state | Move durable state off local SQLite/files; restore and concurrent access must be tested |

Cloudflare documents Linux container execution and Docker-in-Docker. Its sandbox service also supports isolated microVMs and disabled internet access. Its container disks are ephemeral by default, and a host restart can stop an instance. Snapshots and R2 object storage do not automatically make PostgreSQL, FalkorDB, Qdrant or SQLite safe to run on an ephemeral container disk. Do not promise durable databases without a tested storage design.

## Credit and access checks before deployment

1. Verify the actual account's startup credit balance, expiry and product entitlements. The published program lasts one year or until credits are consumed. Containers/Sandboxes coverage should be confirmed for this account; the program's displayed covered-product list does not explicitly resolve that question.
2. Verify Workers Paid and Containers access. Published startup terms require a valid payment method on file, so a credit award does not independently prove that all paid capabilities can be activated without a card.
3. Inspect billing behavior and expenditure limits before creating resources. User authorization covers using the stated startup credits, not cash charges or unrelated external database purchases. Credits do not pay Groq or third-party database invoices.
4. Use scoped deployment access. A local `.env.cloudflare` is ignored by Git; `.env.cloudflare.example` contains only placeholders. Never provide a Global API Key, password or API token in chat. Browser-based Wrangler login is another possible access route.
5. After access is available, inspect existing FalkorDB/PostgreSQL/Qdrant cloud options, build the actual deployment, migrate durable state and rerun restart, sandbox, privacy and browser checks before replacing the temporary link.

## Official references

- Startup benefits, expiry and payment-method terms: <https://www.cloudflare.com/startups/>
- Container persistence, runtime and Docker-in-Docker: <https://developers.cloudflare.com/containers/faq/>
- Container pricing and paid-plan requirement: <https://developers.cloudflare.com/containers/platform/pricing/>
- Linux sandbox capabilities: <https://developers.cloudflare.com/sandbox/>

This document is a deployment proposal, not a claim that migration or Cloudflare credit eligibility has been verified on the user's account.

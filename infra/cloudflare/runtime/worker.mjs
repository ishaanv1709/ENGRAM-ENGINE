import { Container, getContainer } from "@cloudflare/containers";

const SECRET_NAMES = [
  "DATABASE_URL", "FALKOR_HOST", "FALKOR_PORT", "FALKOR_USERNAME", "FALKOR_PASSWORD", "FALKOR_TLS",
  "QDRANT_URL", "QDRANT_API_KEY", "PROVIDER_ENCRYPTION_KEY", "ARTIFACT_SERVICE_ORIGIN",
  "ARTIFACT_SERVICE_TOKEN", "ORIGINS", "MEM0_HISTORY_BACKEND",
];

export class EngramRuntime extends Container {
  defaultPort = 8088;
  sleepAfter = "5m";
  enableInternet = true;

  constructor(ctx, env) {
    super(ctx, env);
    this.envVars = Object.fromEntries(SECRET_NAMES.map(name => [name, env[name] || ""]));
  }

  async fetch(request) {
    // The constant name in the outer Worker and max_instances=1 keep a single
    // scheduler deployment. Background SQL leases remain authoritative.
    await this.startAndWaitForPorts({
      ports: [8088],
      cancellationOptions: { portReadyTimeoutMS: 180_000, instanceGetTimeoutMS: 30_000 },
    });
    return super.fetch(request);
  }
}

async function authorized(request, env) {
  if (!env.RUNTIME_SERVICE_TOKEN) return false;
  const actual = request.headers.get("X-Engram-Runtime-Token") || "";
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([actual, env.RUNTIME_SERVICE_TOKEN]
    .map(value => crypto.subtle.digest("SHA-256", enc.encode(value))));
  const aa = new Uint8Array(a), bb = new Uint8Array(b);
  let different = 0;
  for (let i = 0; i < aa.length; i++) different |= aa[i] ^ bb[i];
  return different === 0;
}

export default {
  async fetch(request, env) {
    if (!(await authorized(request, env))) return new Response("Not found", { status: 404 });
    const url = new URL(request.url);
    if (url.pathname !== "/api" && !url.pathname.startsWith("/api/")) {
      return new Response("Not found", { status: 404 });
    }
    const forwarded = new Request(request);
    forwarded.headers.delete("X-Engram-Runtime-Token");
    const response = await getContainer(env.RUNTIME, "engram-single-runtime").fetch(forwarded);
    const result = new Response(response.body, response);
    result.headers.set("Cache-Control", "no-store");
    result.headers.set("X-Content-Type-Options", "nosniff");
    return result;
  },
  async scheduled(_event, env, ctx) {
    // Cron wakes the same real container while the user's laptop is off.
    // A failed dependency remains a failed health response, never fake ready.
    ctx.waitUntil((async () => {
      const response = await getContainer(env.RUNTIME, "engram-single-runtime")
        .fetch(new Request("http://runtime/api/health"));
      if (!response.ok) throw new Error(`Runtime health returned ${response.status}`);
      const health = await response.json();
      for (const name of ["postgres", "falkordb", "qdrant", "embeddings", "worker", "sandbox"]) {
        if (health.services?.[name]?.state !== "ready") throw new Error(`Runtime dependency unavailable: ${name}`);
      }
    })());
  },
};

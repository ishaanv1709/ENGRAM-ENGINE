const json = (body, status = 200) => Response.json(body, {
  status, headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
});

async function artifactStorage(request, env, url) {
  // This service credential belongs only to the trusted API/worker runtime.
  // Browser cookies never authorize raw object-store access.
  if (!env.ARTIFACT_SERVICE_TOKEN || !env.ARTIFACTS) return json({ detail: "Not found" }, 404);
  const actual = request.headers.get("Authorization") || "";
  const expected = `Bearer ${env.ARTIFACT_SERVICE_TOKEN}`;
  const encoder = new TextEncoder();
  const [left, right] = await Promise.all([actual, expected].map(value => crypto.subtle.digest("SHA-256", encoder.encode(value))));
  let difference = 0;
  const leftBytes = new Uint8Array(left), rightBytes = new Uint8Array(right);
  for (let i = 0; i < leftBytes.length; i++) difference |= leftBytes[i] ^ rightBytes[i];
  if (difference) return json({ detail: "Not found" }, 404);
  const key = url.pathname.slice("/internal/artifacts/".length);
  if (!/^v1\/[a-f0-9-]{36}\/[a-f0-9-]{36}\/[a-f0-9]{64}$/.test(key) || url.search) {
    return json({ detail: "Invalid object key" }, 400);
  }
  const checksum = key.split("/").at(-1);
  if (request.method === "PUT") {
    const length = Number(request.headers.get("Content-Length"));
    if (!Number.isSafeInteger(length) || length < 0 || length > 12_000_000) {
      return json({ detail: "Artifact exceeds storage limit" }, 413);
    }
    // Count the stream too; a forged/missing length must not allocate an
    // unbounded arrayBuffer in the Worker.
    const reader = request.body?.getReader();
    const chunks = [];
    let size = 0;
    if (reader) {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 12_000_000) {
          await reader.cancel();
          return json({ detail: "Artifact exceeds storage limit" }, 413);
        }
        chunks.push(value);
      }
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
    const hex = [...hash].map(value => value.toString(16).padStart(2, "0")).join("");
    if (hex !== checksum) return json({ detail: "Artifact checksum mismatch" }, 409);
    await env.ARTIFACTS.put(key, bytes, {
      sha256: checksum,
      httpMetadata: { contentType: "application/octet-stream", cacheControl: "no-store" },
      customMetadata: { sha256: checksum },
    });
    return json({ stored: true, sha256: checksum, size });
  }
  if (request.method === "GET" || request.method === "HEAD") {
    const object = request.method === "HEAD" ? await env.ARTIFACTS.head(key) : await env.ARTIFACTS.get(key);
    if (!object) return json({ detail: "Artifact unavailable" }, 404);
    return new Response(request.method === "HEAD" ? null : object.body, {
      headers: {
        "Content-Type": "application/octet-stream", "Content-Length": String(object.size),
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Artifact-SHA256": checksum,
      },
    });
  }
  return json({ detail: "Method not allowed" }, 405);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/internal/artifacts/")) return artifactStorage(request, env, url);
    if (url.pathname === "/deployment-status") {
      return json({
        website: "cloudflare-workers", evidence: "cloudflare-static-assets",
        backend: env.BACKEND_HOSTING,
        laptop_independent_backend: env.BACKEND_HOSTING === "cloud",
      });
    }
    if (url.pathname === "/api" || url.pathname.startsWith("/api/")) {
      if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
        const origin = request.headers.get("Origin");
        if (origin && origin !== url.origin) return json({ detail: "Origin not permitted" }, 403);
        if (request.headers.get("X-Engram-Request") !== "1") {
          return json({ detail: "Missing request protection header" }, 403);
        }
      }
      if (!env.API_ORIGIN) return json({ detail: "Cloud backend deployment is not configured" }, 503);
      const upstream = new URL(env.API_ORIGIN);
      if (upstream.protocol !== "https:" || upstream.username || upstream.password || upstream.pathname !== "/") {
        return json({ detail: "Invalid backend deployment configuration" }, 503);
      }
      upstream.pathname = url.pathname;
      upstream.search = url.search;
      const headers = new Headers(request.headers);
      headers.delete("Host");
      headers.set("X-Forwarded-Host", url.host);
      headers.set("X-Forwarded-Proto", "https");
      try {
        const response = await fetch(upstream, {
          method: request.method, headers,
          body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
          redirect: "manual",
        });
        // Authenticated API responses, including artifacts and SSE, are never cached.
        const result = new Response(response.body, response);
        result.headers.set("Cache-Control", "no-store");
        result.headers.set("X-Engram-Backend-Hosting", env.BACKEND_HOSTING);
        return result;
      } catch {
        return json({ detail: env.BACKEND_HOSTING === "cloud"
          ? "The cloud agent backend is temporarily unavailable"
          : "The laptop-hosted agent backend is offline. The website, quickstart and evidence remain available." }, 503);
      }
    }
    const response = await env.ASSETS.fetch(request);
    const result = new Response(response.body, response);
    result.headers.set("X-Content-Type-Options", "nosniff");
    result.headers.set("X-Frame-Options", "DENY");
    result.headers.set("Referrer-Policy", "same-origin");
    result.headers.set("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'");
    if (result.headers.get("Content-Type")?.includes("text/html") && env.BACKEND_HOSTING !== "cloud") {
      let noticeInserted = false;
      return new HTMLRewriter().on("body, main", {
        element(element) {
          // Evidence HTML omits the optional body tag. Match its main element
          // too, while inserting the notice only once in complete documents.
          if (noticeInserted) return;
          noticeInserted = true;
          element.prepend('<div role="complementary" aria-label="Deployment status" style="position:fixed;z-index:1000;right:14px;bottom:14px;box-sizing:border-box;width:calc(100% - 28px);max-width:330px;padding:9px 13px;border:1px solid #b9cbc3;border-radius:9px;background:#f4f5efeF;color:#263f36;font:11px/1.5 system-ui;box-shadow:0 3px 15px #10251b12">Cloudflare hosts this site. Agent execution temporarily uses the developer\u2019s laptop while cloud migration is completed.</div>', { html: true });
        },
      }).transform(result);
    }
    return result;
  },
};

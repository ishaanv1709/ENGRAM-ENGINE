import { useEffect, useState } from "react";
import { Link, Play, ShieldCheck, Terminal } from "lucide-react";
import { api, post, type Row } from "./api";
import { Badge, Empty, JsonDetail } from "./components";

export function SandboxPanel({ events }: { events: Row[] }) {
  const executions = events.filter((e) => e.kind === "tool.executed");
  return (
    <>
      <div className="security-note">
        <ShieldCheck size={22} />
        <div>
          <strong>Restricted Docker execution</strong>
          <p>
            Unprivileged user · Network disabled · Read-only root · Limited CPU,
            memory, and time
          </p>
          <p>
            UID 65534 · 1 CPU · 512 MiB · 128 processes · command timeout up to
            120 seconds. Each run has its own writable volume; the Docker host
            kernel is shared.
          </p>
          <p>
            Safeguard judges memory admission and suspicious input before
            semantic extraction. It is a probabilistic filter, not an
            authorization boundary or a guarantee against prompt injection.
            Quota or provider failure does not grant admission.
          </p>
          <details>
            <summary>What these controls do and do not guarantee</summary>
            <p>
              No host directory or Docker socket is mounted into the sandbox, no
              provider credentials are deliberately passed, all Linux
              capabilities are dropped and privilege escalation is disabled.
              Code can read its own image and run volume. A malicious or
              vulnerable image, shared-kernel escape, incomplete tests, poisoned
              sources or sensitive data explicitly supplied as task input are
              outside these guarantees. Command output is file-backed and
              checked after execution, not a streaming disk quota. Image tags
              are not immutable image digests.
            </p>
          </details>
        </div>
      </div>
      {executions.length ? (
        executions
          .slice()
          .reverse()
          .map((e) => (
            <article className="memory-card" key={e.id}>
              <div className="row">
                <Terminal size={17} />
                <strong>Task {e.run_id?.slice(0, 8)}</strong>
                <Badge
                  value={e.payload.exit_code === 0 ? "completed" : "failed"}
                />
                <span className="subtle">Exit {e.payload.exit_code}</span>
              </div>
              <pre className="console">
                $ {e.payload.command}
                {"\n\n"}
                {e.payload.stdout}
                {e.payload.stderr ? "\nSTDERR\n" + e.payload.stderr : ""}
              </pre>
              <small className="subtle">
                Execution evidence #{e.id} ·{" "}
                {new Date(e.created_at).toLocaleString()}
              </small>
            </article>
          ))
      ) : (
        <Empty
          title="A real terminal, a restricted environment"
          description="Builder and verifier command output appears here when they execute sandbox tools."
        />
      )}
    </>
  );
}

export function MCPPanel({ fail }: { fail: (e: unknown) => void }) {
  const [servers, setServers] = useState<Row[]>([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [allowed, setAllowed] = useState("");
  const [busy, setBusy] = useState(false);
  const [discovered, setDiscovered] = useState<Row | null>(null);
  useEffect(() => {
    api<Row[]>("/tool-servers").then(setServers).catch(fail);
  }, [fail]);
  async function connect() {
    setBusy(true);
    try {
      const result = await post("/tool-servers", {
        name,
        url,
        allowed_tools: allowed
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setDiscovered(result);
      setServers(await api<Row[]>("/tool-servers"));
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="space-top">
      <h2>External tool connections</h2>
      <p className="subtle">
        Workspace owners can authorize named tools from public HTTPS MCP
        servers. Only explicitly allowed tools become available.
      </p>
      <form
        className="connection-form"
        onSubmit={(e) => {
          e.preventDefault();
          void connect();
        }}
      >
        <label>
          Connection name
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label>
          MCP endpoint
          <input
            required
            type="url"
            value={url}
            placeholder="https://…/mcp"
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>
        <label>
          Allowed tool names
          <input
            value={allowed}
            placeholder="Comma-separated exact names; empty grants no tools"
            onChange={(e) => setAllowed(e.target.value)}
          />
        </label>
        <button className="button" disabled={busy}>
          <Link size={14} />
          {busy ? "Connecting…" : "Connect and inspect"}
        </button>
      </form>
      {discovered ? (
        <JsonDetail data={discovered} label="Actual advertised tools" />
      ) : null}
      {servers.map((s) => (
        <div className="job" key={s.id}>
          <strong>{s.name}</strong>
          <span className="subtle">{s.url}</span>
          <Badge value={s.enabled ? "active" : "disabled"} />
          <small>{s.allowed_tools.length} authorized tools</small>
          {s.enabled ? (
            <button
              className="text-button"
              onClick={async () => {
                try {
                  await post(`/tool-servers/${s.id}/disable`);
                  setServers(await api<Row[]>("/tool-servers"));
                } catch (e) {
                  fail(e);
                }
              }}
            >
              Disable
            </button>
          ) : null}
        </div>
      ))}
    </section>
  );
}

export function EvaluationButton({
  project,
  refresh,
  fail,
}: {
  project: string;
  refresh: () => void;
  fail: (e: unknown) => void;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      className="button"
      disabled={busy || !project}
      onClick={async () => {
        setBusy(true);
        try {
          await post(`/projects/${project}/evaluate`);
          refresh();
        } catch (e) {
          fail(e);
        } finally {
          setBusy(false);
        }
      }}
    >
      <Play size={14} />
      {busy ? "Running actual checks…" : "Run memory benchmark"}
    </button>
  );
}

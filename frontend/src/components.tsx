import { useState } from "react";
import {
  Check,
  ChevronDown,
  ExternalLink,
  GitBranch,
  Loader2,
  Play,
  X,
  Search,
} from "lucide-react";
import { api, post, type Row } from "./api";

export function Badge({ value }: { value: string }) {
  return <span className={"badge " + value}>{value.replaceAll("_", " ")}</span>;
}
export function Empty({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="empty">
      <GitBranch size={32} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
export function JsonDetail({
  data,
  label = "Inspect evidence",
}: {
  data: unknown;
  label?: string;
}) {
  return (
    <details className="json-detail">
      <summary>
        {label}
        <ChevronDown size={14} />
      </summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

export function RunCard({
  run,
  refresh,
  fail,
}: {
  run: Row;
  refresh: () => void;
  fail: (e: unknown) => void;
}) {
  const [busy, setBusy] = useState(false);
  async function control(action: string) {
    setBusy(true);
    try {
      await post(`/runs/${run.id}/${action}`);
      refresh();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="run-card">
      <div className="card-top">
        <span className={"agent-dot " + run.role} />
        <strong>{run.role}</strong>
        <Badge value={run.status} />
      </div>
      <h3>
        {run.objective.length > 240
          ? run.objective.slice(0, 240) + "…"
          : run.objective}
      </h3>
      {run.objective.length > 240 ? (
        <details className="plain-details">
          <summary>Full task brief</summary>
          <p>{run.objective}</p>
        </details>
      ) : null}
      <p className="subtle">
        {new Date(run.created_at).toLocaleString()} · attempt {run.attempt}
      </p>
      {run.error ? <p className="inline-error">{run.error}</p> : null}
      {run.status === "stale" && run.memory_refs?.length > 0 && (
        <p className="subtle">
          Bound evidence changed. Open Causal timeline and create a revised plan
          with current context.
        </p>
      )}
      {run.memory_refs != null && (
        <p className="subtle">
          Focused context: {run.memory_refs.length} explicit memories, plus
          pinned obligations.
        </p>
      )}
      {run.result ? (
        <>
          <p>{run.result.summary}</p>
          <JsonDetail data={run.result} />
        </>
      ) : null}
      <div className="card-footer">
        <code>{run.id.slice(0, 8)}</code>
        {run.status === "running" ? (
          <Loader2 className="spin" size={15} />
        ) : null}
        {["queued", "running", "waiting", "awaiting_handoff"].includes(
          run.status,
        ) ? (
          <button
            disabled={busy}
            onClick={() => control("cancel")}
            className="text-button"
          >
            <X size={14} />
            Cancel
          </button>
        ) : null}
        {["blocked", "stale", "failed", "cancelled"].includes(run.status) &&
        !(run.status === "stale" && run.memory_refs?.length > 0) ? (
          <button
            disabled={busy}
            onClick={() => control("resume")}
            className="text-button"
          >
            <Play size={14} />
            Resume
          </button>
        ) : null}
      </div>
    </article>
  );
}

export function MemoryPanel({
  memories,
  project,
  refresh,
  fail,
}: {
  memories: Row[];
  project: string;
  refresh: () => void;
  fail: (e: unknown) => void;
}) {
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Row[] | null>(null);
  const [content, setContent] = useState("");
  const [visibility, setVisibility] = useState("team");
  const [busy, setBusy] = useState(false);
  async function add() {
    setBusy(true);
    try {
      await post(`/projects/${project}/memory`, { content, visibility });
      setContent("");
      refresh();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  async function search() {
    setBusy(true);
    try {
      const r = await post(`/projects/${project}/search`, { content: query });
      setHits(r.memories);
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  async function correct(record: Row) {
    const value = prompt(
      "Correct this memory. Dependent tasks will be marked stale.",
      record.content,
    );
    if (!value || value === record.content) return;
    try {
      await post(`/projects/${project}/memory/${record.id}/correct`, {
        content: value,
        expected_revision: record.revision,
      });
      refresh();
    } catch (e) {
      fail(e);
    }
  }
  async function publishMemory(record: Row) {
    if (
      !confirm(
        "Publish a copy of this memory to everyone in this workspace project?",
      )
    )
      return;
    try {
      await post(`/projects/${project}/memory/${record.id}/publish`);
      refresh();
    } catch (e) {
      fail(e);
    }
  }
  const rows = (hits || memories).filter(
    (m) => filter === "all" || m.memory_type === filter,
  );
  return (
    <>
      <div className="split-panel">
        <div>
          <h3>Add something to remember</h3>
          <p className="subtle">
            Save a useful fact, preference or constraint so your team can use it
            in future work.
          </p>
          <details className="plain-details">
            <summary>How memory works</summary>
            <p>
              Past activity keeps the original observations. Facts hold
              extracted knowledge with sources. Ways of working retain tools and
              checked workflows. New observations pass through admission checks
              before fact extraction.
            </p>
          </details>
        </div>
        <textarea
          aria-label="New memory"
          placeholder="A preference, constraint, observation, or fact…"
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
        <div className="row">
          <select
            aria-label="Memory visibility"
            value={visibility}
            onChange={(e) => setVisibility(e.target.value)}
          >
            <option value="team">Shared with team</option>
            <option value="user">Only me</option>
          </select>
          <button
            className="primary"
            disabled={busy || !content || !project}
            onClick={add}
          >
            Save memory
          </button>
        </div>
      </div>
      <div className="toolbar">
        <div className="tabs">
          {["all", "episodic", "semantic", "procedural"].map((f) => (
            <button
              key={f}
              className={filter === f ? "active" : ""}
              onClick={() => setFilter(f)}
            >
              {
                {
                  all: "All memories",
                  episodic: "Past activity",
                  semantic: "Facts",
                  procedural: "Ways of working",
                }[f]
              }
            </button>
          ))}
        </div>
        <form
          className="search"
          onSubmit={(e) => {
            e.preventDefault();
            void search();
          }}
        >
          <Search size={16} />
          <input
            aria-label="Search memories"
            placeholder="Search connected memory"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (!e.target.value) setHits(null);
            }}
          />
        </form>
      </div>
      {rows.length ? (
        <div className="memory-list">
          {rows.map((m) => (
            <article className="memory-card" key={m.id}>
              <div className="row">
                <Badge value={m.memory_type} />
                <Badge value={m.category} />
                <span className="subtle">
                  {m.visibility} · v{m.revision}
                </span>
                <Badge value={m.status} />
              </div>
              <p>{m.content}</p>
              <div className="card-footer">
                <code>{m.id.slice(0, 8)}</code>
                <span>{m.source_ids?.length || 0} sources</span>
                {m.status === "active" ? (
                  <button className="text-button" onClick={() => correct(m)}>
                    Correct memory
                  </button>
                ) : null}
                {m.visibility !== "team" && m.status === "active" ? (
                  <button
                    className="text-button"
                    onClick={() => publishMemory(m)}
                  >
                    Publish to team
                  </button>
                ) : null}
              </div>
              <JsonDetail data={m} />
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title="Memory starts with experience"
          description="Add an observation or run a task. Sources, facts, and procedures will appear here."
        />
      )}
    </>
  );
}

export function ArtifactPanel({ artifacts }: { artifacts: Row[] }) {
  return artifacts.length ? (
    <div className="memory-list">
      {artifacts.map((a) => (
        <article className="memory-card" key={a.id}>
          <div className="row">
            <Check size={16} />
            <strong>{a.name}</strong>
            <span className="subtle">{(a.size / 1024).toFixed(1)} KB</span>
            <a className="text-button" href={`/api/artifacts/${a.id}/download`}>
              <ExternalLink size={14} />
              Download
            </a>
          </div>
          <details className="plain-details">
            <summary>File details</summary>
            <code className="checksum">SHA-256 {a.sha256}</code>
            <p className="subtle">{new Date(a.created_at).toLocaleString()}</p>
          </details>
        </article>
      ))}
    </div>
  ) : (
    <Empty
      title="A place for finished work"
      description="Upload a document or let a builder publish an artifact. Every file has a checksum and source task."
    />
  );
}

export function UploadButton({
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
    <label className={"button upload " + (busy ? "disabled" : "")}>
      {busy ? "Uploading…" : "Upload document"}
      <input
        type="file"
        disabled={!project || busy}
        onChange={async (e) => {
          const f = e.target.files?.[0];
          if (!f) return;
          const form = new FormData();
          form.append("file", f);
          setBusy(true);
          try {
            await api(`/projects/${project}/documents`, {
              method: "POST",
              body: form,
            });
            refresh();
          } catch (err) {
            fail(err);
          } finally {
            setBusy(false);
            e.target.value = "";
          }
        }}
      />
    </label>
  );
}

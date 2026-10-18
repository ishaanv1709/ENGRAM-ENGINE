import { useCallback, useEffect, useState } from "react";
import { ArrowRight, Plus, Upload } from "lucide-react";
import { api, post, type Row } from "./api";
import { Badge, Empty, JsonDetail } from "./components";

const initialSteps = [
  {
    key: "plan",
    title: "Plan the work",
    role: "coordinator",
    objective:
      "Inspect the source and context. Produce an actionable implementation plan and acceptance criteria. The workflow already schedules implementation and verification; avoid duplicating those milestones. Delegate narrower investigations only when necessary.",
    depends_on: [],
    acceptance: "report",
    needs_approval: false,
  },
  {
    key: "research",
    title: "Investigate the source",
    role: "researcher",
    objective:
      "Use repository_list and repository_read when source is supplied. Identify the relevant files, constraints, risks and evidence. Report concrete findings for the implementation milestone.",
    depends_on: [],
    acceptance: "report",
    needs_approval: false,
  },
  {
    key: "implement",
    title: "Implement and publish",
    role: "builder",
    objective:
      "Read completed predecessor results and source files. Implement the requested change in the sandbox, execute meaningful tests, publish changed files and tests individually, and use repository_patch when a snapshot is available. Do not push or deploy.",
    depends_on: ["plan", "research"],
    acceptance: "artifacts",
    needs_approval: false,
  },
  {
    key: "verify",
    title: "Check independently",
    role: "verifier",
    objective:
      "Inspect the prepared predecessor files without modifying their bytes. Execute meaningful fresh pytest or unittest checks. Report the real check IDs, failures and limits. Do not claim unrelated tests verified the change.",
    depends_on: ["implement"],
    acceptance: "independent_checks",
    needs_approval: false,
  },
  {
    key: "review",
    title: "Prepare the review packet",
    role: "coordinator",
    objective:
      "Summarize the checked changes, actual artifact IDs, patch, test evidence and remaining risks. Prepare a review-ready result. Do not claim a pull request, external review or deployment happened without its real receipt.",
    depends_on: ["verify"],
    acceptance: "report",
    needs_approval: true,
  },
];

export function WorkflowPanel({
  project,
  initialGoal = "",
  fail,
}: {
  project: string;
  initialGoal?: string;
  fail: (e: unknown) => void;
}) {
  const [items, setItems] = useState<Row[]>([]);
  const [profiles, setProfiles] = useState<Row[]>([]);
  const [snapshots, setSnapshots] = useState<Row[]>([]);
  const [selected, setSelected] = useState("");
  const [view, setView] = useState<Row | null>(null);
  const [goal, setGoal] = useState(initialGoal);
  const [snapshot, setSnapshot] = useState("");
  const [steps, setSteps] = useState<Row[]>(initialSteps);
  const [limits, setLimits] = useState<Row>({
    parallel: 3,
    max_tasks: 64,
    max_depth: 6,
    model_calls: 100,
    tool_calls: 600,
  });
  const [busy, setBusy] = useState(false);
  const [duration, setDuration] = useState(1440);
  const [signals, setSignals] = useState<Record<string, string>>({});
  const load = useCallback(async () => {
    const [workflows, specialists, sources] = await Promise.all([
      api<Row[]>(`/projects/${project}/workflows`),
      api(`/projects/${project}/agent-profiles`),
      api<Row[]>(`/projects/${project}/source-snapshots`),
    ]);
    setItems(workflows);
    setProfiles(specialists.profiles);
    setSnapshots(sources);
    if (selected) setView(await api(`/workflows/${selected}`));
  }, [project, selected]);
  useEffect(() => {
    void load().catch(fail);
    const timer = setInterval(() => void load().catch(fail), 5000);
    return () => clearInterval(timer);
  }, [load, fail]);
  const action = async (path: string, body = {}) => {
    setBusy(true);
    try {
      await post(path, body);
      await load();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  };
  const updateStep = (index: number, values: Row) =>
    setSteps((previous) =>
      previous.map((s, i) => (i === index ? { ...s, ...values } : s)),
    );
  async function create() {
    setBusy(true);
    try {
      const result = await post(`/projects/${project}/workflows`, {
        goal,
        steps,
        limits,
        snapshot_id: snapshot || null,
        duration_minutes: duration,
      });
      setSelected(result.id);
      setView(await api(`/workflows/${result.id}`));
      await load();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="workflow-panel">
      <div className="workflow-intro">
        <h2>Goal → Plan → Progress → Results</h2>
        <p>
          Use milestones for work that needs several specialists, independent
          checks or a human decision. Creating a plan saves a draft; starting it
          uses your configured model.
        </p>
      </div>
      <details
        className="workflow-create"
        open={!selected && items.length === 0}
      >
        <summary>Plan a complex workflow</summary>
        <label>
          Workflow goal
          <textarea
            aria-label="Workflow goal"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Investigate this project, implement a specific improvement, verify it, and prepare the changes for review."
          />
        </label>
        <div className="row source-controls">
          <label>
            Source snapshot
            <select
              aria-label="Source snapshot"
              value={snapshot}
              onChange={(e) => setSnapshot(e.target.value)}
            >
              <option value="">No source snapshot</option>
              {snapshots.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.manifest.length} files
                </option>
              ))}
            </select>
          </label>
          <label className="button upload">
            <Upload size={15} />
            Import source ZIP
            <input
              type="file"
              accept=".zip"
              disabled={busy}
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const form = new FormData();
                form.append("file", file);
                setBusy(true);
                try {
                  const source = await api(
                    `/projects/${project}/source-snapshots`,
                    { method: "POST", body: form },
                  );
                  await load();
                  setSnapshot(source.id);
                } catch (error) {
                  fail(error);
                } finally {
                  setBusy(false);
                  e.target.value = "";
                }
              }}
            />
          </label>
        </div>
        <p className="subtle">
          Source files are shared within this project. Environment files and
          generated directories are excluded. ZIP import does not run repository
          code on the host.
        </p>
        <div className="milestone-editor">
          {steps.map((step, i) => (
            <article className="memory-card" key={step.key}>
              <div className="row">
                <span className="eyebrow">MILESTONE {i + 1}</span>
                <Badge value={step.role} />
              </div>
              <label>
                Title
                <input
                  value={step.title}
                  onChange={(e) => updateStep(i, { title: e.target.value })}
                />
              </label>
              <details className="plain-details">
                <summary>Instructions, dependencies and specialist</summary>
                <label>
                  Instructions
                  <textarea
                    value={step.objective}
                    onChange={(e) =>
                      updateStep(i, { objective: e.target.value })
                    }
                  />
                </label>
                <label>
                  Role
                  <select
                    value={step.role}
                    onChange={(e) =>
                      updateStep(i, { role: e.target.value, profile_id: null })
                    }
                  >
                    {[
                      "coordinator",
                      "researcher",
                      "builder",
                      "verifier",
                      "curator",
                    ].map((r) => (
                      <option key={r}>{r}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Custom specialist
                  <select
                    value={step.profile_id || ""}
                    onChange={(e) =>
                      updateStep(i, { profile_id: e.target.value || null })
                    }
                  >
                    <option value="">Default {step.role}</option>
                    {profiles
                      .filter((p) => p.base_role === step.role)
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Depends on milestone keys
                  <input
                    value={step.depends_on.join(", ")}
                    onChange={(e) =>
                      updateStep(i, {
                        depends_on: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                  />
                  <small>This milestone's key: {step.key}</small>
                </label>
                <label>
                  Parent milestone key (optional grouping)
                  <input
                    value={step.parent_key || ""}
                    onChange={(e) =>
                      updateStep(i, {
                        parent_key: e.target.value.trim() || null,
                      })
                    }
                    placeholder="For example: plan"
                  />
                  <small>Grouping does not add a dependency.</small>
                </label>
                <label>
                  Acceptance
                  <select
                    value={step.acceptance}
                    onChange={(e) =>
                      updateStep(i, { acceptance: e.target.value })
                    }
                  >
                    <option value="report">Persisted report</option>
                    <option value="artifacts">Published files</option>
                    <option value="independent_checks">
                      Independent file checks
                    </option>
                  </select>
                </label>
                <label>
                  Wait for an event (optional)
                  <input
                    value={step.wait_for_signal || ""}
                    onChange={(e) =>
                      updateStep(i, { wait_for_signal: e.target.value || null })
                    }
                    placeholder="For example: review_received"
                  />
                </label>
              </details>
              <label className="shared-context-option">
                <input
                  type="checkbox"
                  checked={step.needs_approval}
                  onChange={(e) =>
                    updateStep(i, { needs_approval: e.target.checked })
                  }
                />
                Require my approval before this milestone starts
              </label>
            </article>
          ))}
        </div>
        <button
          className="text-button"
          onClick={() =>
            setSteps((previous) => [
              ...previous,
              {
                key: `step_${previous.length + 1}`,
                title: "New milestone",
                role: "researcher",
                objective:
                  "Inspect the previous milestone and report the next concrete result.",
                depends_on: [previous[previous.length - 1].key],
                acceptance: "report",
                needs_approval: false,
              },
            ])
          }
        >
          <Plus size={14} />
          Add milestone
        </button>
        <details className="plain-details workflow-budgets">
          <summary>Execution budgets</summary>
          <div className="budget-grid">
            <label>
              Deadline after draft creation (minutes)
              <input
                type="number"
                min="1"
                max="10080"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              />
            </label>
            {Object.entries(limits).map(([key, value]) => (
              <label key={key}>
                {
                  (
                    {
                      parallel: "Parallel workers",
                      max_tasks: "Total tasks",
                      max_depth: "Delegation depth",
                      model_calls: "Agent inference attempts",
                      tool_calls: "Tool attempts",
                    } as Row
                  )[key]
                }
                <input
                  type="number"
                  min="1"
                  value={value}
                  onChange={(e) =>
                    setLimits({ ...limits, [key]: Number(e.target.value) })
                  }
                />
              </label>
            ))}
          </div>
          <p>
            Attempts include bounded harness retries. This is not a monetary or
            provider-wide token cap; extraction, policy and transport retries
            have separate costs.
          </p>
        </details>
        <button
          className="primary"
          disabled={busy || !goal.trim()}
          onClick={create}
        >
          Save workflow draft
          <ArrowRight size={15} />
        </button>
      </details>
      <div className="section-title space-top">
        <h2>Your workflows</h2>
        <select
          aria-label="Select workflow"
          value={selected}
          onChange={(e) => {
            setSelected(e.target.value);
            setView(null);
          }}
        >
          <option value="">Select a workflow</option>
          {items.map((w) => (
            <option key={w.id} value={w.id}>
              {w.goal.slice(0, 70)} · {w.status}
            </option>
          ))}
        </select>
      </div>
      {!items.length && !view ? (
        <Empty
          title="Long work needs a durable plan"
          description="Create a draft above. Review its milestones and budgets before starting."
        />
      ) : null}
      {view ? (
        <div className="workflow-progress">
          <div className="row">
            <h2>{view.workflow.goal}</h2>
            <Badge value={view.workflow.status} />
          </div>
          <p className="subtle">
            Deadline: {new Date(view.workflow.deadline_at).toLocaleString()} ·{" "}
            {view.steps.filter((s: Row) => s.status === "completed").length}/
            {view.steps.length} milestones accepted
          </p>
          <div className="row">
            {["draft", "paused", "blocked"].includes(view.workflow.status) ? (
              <button
                className="primary"
                disabled={busy}
                onClick={() =>
                  void action(
                    `/workflows/${selected}/${view.workflow.status === "draft" ? "start" : "resume"}`,
                  )
                }
              >
                {view.workflow.status === "draft"
                  ? "Start workflow"
                  : "Resume workflow"}
              </button>
            ) : null}
            {view.workflow.status === "running" ? (
              <button
                className="button"
                disabled={busy}
                onClick={() => void action(`/workflows/${selected}/pause`)}
              >
                Pause
              </button>
            ) : null}
            {!["completed", "cancelled"].includes(view.workflow.status) ? (
              <button
                className="text-button"
                disabled={busy}
                onClick={() => void action(`/workflows/${selected}/cancel`)}
              >
                Cancel workflow
              </button>
            ) : null}
          </div>
          <div className="workflow-stages">
            {view.steps.map((step: Row, i: number) => (
              <article className="causal-card" key={step.id}>
                <div className="row">
                  <strong>
                    {i + 1}. {step.title}
                  </strong>
                  <Badge value={step.status} />
                  <span className="subtle">
                    {step.profile?.name || step.role}
                  </span>
                </div>
                {step.error ? (
                  <p className="inline-error">{step.error}</p>
                ) : null}
                {step.status === "awaiting_approval" ? (
                  <>
                    <p>
                      Review the completed dependencies before allowing this
                      milestone to begin.
                    </p>
                    <button
                      className="button"
                      disabled={busy}
                      onClick={() =>
                        void action(
                          `/workflows/${selected}/steps/${step.id}/approve`,
                        )
                      }
                    >
                      Approve milestone
                    </button>
                  </>
                ) : null}
                {step.status === "waiting_signal" ? (
                  <div>
                    <label>
                      {step.wait_for_signal}
                      <input
                        value={signals[step.id] || ""}
                        onChange={(e) =>
                          setSignals({ ...signals, [step.id]: e.target.value })
                        }
                        placeholder="Record the event or review outcome"
                      />
                    </label>
                    <button
                      className="button"
                      disabled={busy || !signals[step.id]?.trim()}
                      onClick={() =>
                        void action(
                          `/workflows/${selected}/steps/${step.id}/signal`,
                          { payload: { observation: signals[step.id] } },
                        )
                      }
                    >
                      Record event
                    </button>
                  </div>
                ) : null}
                {["blocked", "failed"].includes(step.status) ? (
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      void action(
                        `/workflows/${selected}/steps/${step.id}/retry`,
                      )
                    }
                  >
                    Retry with fresh approval
                  </button>
                ) : null}
                {view.runs
                  .filter(
                    (r: Row) => r.workflow_step_id === step.id && r.result,
                  )
                  .map((r: Row) => (
                    <div className="milestone-result" key={r.id}>
                      <p>{r.result.summary}</p>
                      {r.result.artifact_ids?.length ? (
                        <p>
                          {r.result.artifact_ids.map((id: string) => (
                            <a
                              className="button"
                              key={id}
                              href={`/api/artifacts/${id}/download`}
                            >
                              Download result
                            </a>
                          ))}
                        </p>
                      ) : null}
                    </div>
                  ))}
                <JsonDetail
                  data={step}
                  label="Milestone instructions and evidence"
                />
              </article>
            ))}
          </div>
          {view.actions.map((a: Row) => (
            <article className="causal-card external-action" key={a.id}>
              <div className="row">
                <h3>External action awaiting review</h3>
                <Badge value={a.status} />
              </div>
              <p>{a.tool}</p>
              <JsonDetail
                data={a.arguments}
                label="Exact arguments to approve"
              />
              {a.status === "pending" ? (
                <div className="row">
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      void action(
                        `/workflows/${selected}/actions/${a.id}/execute`,
                      )
                    }
                  >
                    Approve and execute exact action
                  </button>
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() =>
                      void action(
                        `/workflows/${selected}/actions/${a.id}/reject`,
                      )
                    }
                  >
                    Reject
                  </button>
                </div>
              ) : null}
              <p className="subtle">
                An uncertain external outcome is never repeated automatically.
                Review it in the remote system before taking further action.
              </p>
            </article>
          ))}
          <details className="plain-details">
            <summary>Usage and budget controls</summary>
            <JsonDetail
              data={{ limits: view.workflow.limits, usage: view.usage }}
              label="Reserved execution attempts"
            />
            {["paused", "blocked", "draft"].includes(view.workflow.status) ? (
              <>
                <p>
                  Set the budgets above, then explicitly apply them. Existing
                  attempt usage is retained.
                </p>
                <button
                  className="button"
                  disabled={busy}
                  onClick={() =>
                    void action(`/workflows/${selected}/limits`, { limits })
                  }
                >
                  Apply budgets to this workflow
                </button>
              </>
            ) : null}
          </details>
        </div>
      ) : null}
    </section>
  );
}

export function AgentProfilesPanel({
  project,
  fail,
}: {
  project: string;
  fail: (e: unknown) => void;
}) {
  const [data, setData] = useState<Row>({ profiles: [], roles: [], tools: [] });
  const [name, setName] = useState("");
  const [role, setRole] = useState("researcher");
  const [instructions, setInstructions] = useState("");
  const [tools, setTools] = useState<string[]>([
    "memory_search",
    "memory_read",
    "team_status",
    "artifact_read",
    "repository_list",
    "repository_read",
  ]);
  const [busy, setBusy] = useState(false);
  const load = useCallback(
    () => api(`/projects/${project}/agent-profiles`).then(setData),
    [project],
  );
  useEffect(() => {
    void load().catch(fail);
  }, [load, fail]);
  return (
    <section>
      <h2>Create a specialist</h2>
      <p>
        Give an agent a name, a role and focused instructions. Its role remains
        the permission ceiling; the tool list can only narrow what it can do.
        Profiles are snapshotted when a workflow draft is saved.
      </p>
      <form
        className="profile-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await post(`/projects/${project}/agent-profiles`, {
              name,
              base_role: role,
              instructions,
              allowed_tools: tools,
              context_scope: "team",
            });
            setName("");
            setInstructions("");
            await load();
          } catch (error) {
            fail(error);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Specialist name
          <input
            required
            maxLength={80}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="For example: Python reliability reviewer"
          />
        </label>
        <label>
          Base role
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {data.roles.map((r: string) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </label>
        <label>
          Specialist instructions
          <textarea
            required
            maxLength={6000}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Describe this specialist's responsibilities and the evidence it must produce."
          />
        </label>
        <details className="plain-details">
          <summary>Allowed tools ({tools.length})</summary>
          <div className="tool-choice-grid">
            {data.tools.map((t: string) => (
              <label className="shared-context-option" key={t}>
                <input
                  type="checkbox"
                  checked={tools.includes(t)}
                  onChange={(e) =>
                    setTools((previous) =>
                      e.target.checked
                        ? [...previous, t]
                        : previous.filter((v) => v !== t),
                    )
                  }
                />
                {t}
              </label>
            ))}
          </div>
          <p>
            Builder and verifier profiles generally need artifact_read and
            sandbox_execute; builders also need sandbox_write and
            artifact_publish. Remote integrations retain their separate
            connection and action approvals.
          </p>
        </details>
        <button
          className="primary"
          disabled={busy || !name.trim() || !instructions.trim()}
        >
          Create specialist
        </button>
      </form>
      <div className="run-grid space-top">
        {data.profiles.map((p: Row) => (
          <article className="memory-card" key={p.id}>
            <h3>{p.name}</h3>
            <Badge value={p.base_role} />
            <p>{p.instructions}</p>
            <small>
              {p.allowed_tools.length} allowed tools · shared memory
            </small>
            <JsonDetail data={p} label="Profile permissions" />
          </article>
        ))}
      </div>
    </section>
  );
}

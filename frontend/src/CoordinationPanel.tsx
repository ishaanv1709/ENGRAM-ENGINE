import { useCallback, useEffect, useState } from "react";
import { ArrowRight, GitBranch, ShieldCheck } from "lucide-react";
import { api, post, type Row } from "./api";
import { Badge, Empty, JsonDetail } from "./components";

export function CoordinationPanel({
  project,
  mode,
  refresh,
  fail,
}: {
  project: string;
  mode: "causes" | "conflicts" | "versions";
  refresh: () => Promise<void>;
  fail: (e: unknown) => void;
}) {
  const [showAllPassports, setShowAllPassports] = useState(false);
  const [data, setData] = useState<Row>({
    causes: [],
    claims: [],
    resolutions: [],
    versions: [],
    uses: [],
    benchmarks: [],
    passports: [],
    deliveries: [],
  });
  const load = useCallback(
    () => api(`/projects/${project}/coordination`).then(setData).catch(fail),
    [project, fail],
  );
  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 5000);
    return () => clearInterval(timer);
  }, [load]);
  const action = async (path: string, body = {}) => {
    try {
      await post(path, body);
      await load();
      await refresh();
    } catch (e) {
      fail(e);
    }
  };
  if (mode === "causes")
    return (
      <section className="causal-panel">
        <div className="section-title">
          <h2>See the impact of a corrected fact.</h2>
          <Badge value="causal evidence" />
        </div>
        <p className="subtle">
          Follow a fact correction through invalidated work to a new,
          evidence-linked plan.
        </p>
        {!data.causes.length && (
          <Empty
            title="Corrections leave a trail"
            description="Correct a fact used by a task to see its causal impact here."
          />
        )}
        {data.causes
          .filter((e: Row) => e.kind === "memory.corrected")
          .map((event: Row) => {
            const p = event.payload;
            const plan = data.causes.find(
              (e: Row) =>
                e.kind === "plan.revised" &&
                e.payload.correction_event === event.id,
            );
            return (
              <article className="causal-card" key={event.id}>
                <div className="row">
                  <GitBranch size={18} />
                  <strong>Correction #{event.id}</strong>
                  <time>{new Date(event.created_at).toLocaleString()}</time>
                </div>
                <div className="causal-flow">
                  <div>
                    <span className="eyebrow">PREVIOUS FACT</span>
                    <p className="old-fact">{p.before || p.old}</p>
                    <code>{p.old.slice(0, 8)}</code>
                  </div>
                  <ArrowRight />
                  <div>
                    <span className="eyebrow">CURRENT EVIDENCE</span>
                    <p>{p.after || p.new}</p>
                    <code>{p.new.slice(0, 8)}</code>
                  </div>
                  <ArrowRight />
                  <div>
                    <span className="eyebrow">IMPACT</span>
                    <h2>{p.affected_runs.length} tasks</h2>
                    <p>Previous results marked stale. Old leases revoked.</p>
                  </div>
                </div>
                {p.affected_tasks?.map((task: Row) => (
                  <div className="manifest-row" key={task.id}>
                    <Badge value={task.status} />
                    <strong>{task.role}</strong>
                    <span>{task.objective.slice(0, 160)}</span>
                  </div>
                ))}
                {p.graph_witness && (
                  <div className="graph-witness">
                    <h3>Why this work changed</h3>
                    <p>
                      {p.graph_witness.direct_readers.length}{" "}
                      {p.graph_witness.direct_readers.length === 1
                        ? "task read"
                        : "tasks read"}{" "}
                      the previous fact. Updating that fact makes work based on
                      it stale.
                    </p>
                    <details className="plain-details graph-evidence">
                      <summary>See graph evidence</summary>
                      <p>
                        Live FalkorDB path: task → DEPENDS_ON → previous fact.
                      </p>
                      <p>
                        {p.graph_witness.direct_readers.length} direct readers
                        found · SUPERSEDES edge{" "}
                        {p.graph_witness.supersession_present
                          ? "confirmed"
                          : "not present"}{" "}
                        · {p.graph_witness.revision_edges.length} REPLANS edges.
                      </p>
                      {p.graph_witness.direct_readers.map((id: string) => (
                        <div className="manifest-row" key={id}>
                          <code>{id.slice(0, 8)}</code>
                          <span>DEPENDS_ON</span>
                          <code>{p.old.slice(0, 8)}</code>
                        </div>
                      ))}
                      <p>{p.graph_witness.effect}</p>
                      <small>{p.graph_witness.counterfactual}</small>
                      <JsonDetail
                        data={p.graph_witness}
                        label="Inspect live query, IDs and revision edges"
                      />
                    </details>
                  </div>
                )}
                {plan ? (
                  <div className="revised-plan">
                    <div className="row">
                      <Badge value="new plan" />
                      <Badge value={plan.payload.new_plan_status || "queued"} />
                    </div>
                    <p>
                      {plan.payload.new_plan_result?.summary ||
                        plan.payload.new_plan}
                    </p>
                    <code>Task {plan.payload.new_plan_id}</code>
                    {["failed", "blocked", "cancelled"].includes(
                      plan.payload.new_plan_status,
                    ) && (
                      <button
                        onClick={() =>
                          action(
                            `/projects/${project}/corrections/${event.id}/replan?replace_failed=true`,
                          )
                        }
                      >
                        Create replacement plan
                      </button>
                    )}
                  </div>
                ) : p.affected_runs.length > 0 ? (
                  <button
                    className="primary"
                    onClick={() =>
                      void action(
                        `/projects/${project}/corrections/${event.id}/replan`,
                      )
                    }
                  >
                    Create revised plan <ArrowRight size={15} />
                  </button>
                ) : null}
                <JsonDetail
                  data={p}
                  label="Inspect affected task IDs and source evidence"
                />
              </article>
            );
          })}
      </section>
    );
  if (mode === "conflicts")
    return (
      <section>
        <div className="section-title">
          <h2>Every claim keeps its source.</h2>
          <Badge value="no silent overwrite" />
        </div>
        <p className="subtle">
          Latest active observation wins under the displayed policy. Equal-time
          contradictions stay unresolved. Source timestamps are recorded
          observations, not proof of external truth.
        </p>
        {!data.claims.length && (
          <Empty
            title="Competing claims stay visible"
            description="Agents can submit sourced claims through their tool catalog. Resolution preserves both branches."
          />
        )}
        {data.resolutions.map((r: Row) => (
          <article className="causal-card" key={r.subject + r.predicate}>
            <div className="row">
              <h3>
                {r.subject} · {r.predicate}
              </h3>
              <Badge value={r.evidence.status} />
              <span>revision {r.revision}</span>
            </div>
            <div className="claim-grid">
              {data.claims
                .filter(
                  (c: Row) =>
                    c.subject === r.subject && c.predicate === r.predicate,
                )
                .map((c: Row) => (
                  <div
                    className={c.id === r.winner_id ? "claim winner" : "claim"}
                    key={c.id}
                  >
                    <Badge
                      value={c.id === r.winner_id ? "selected" : "preserved"}
                    />
                    <h3>{c.value}</h3>
                    <p>
                      Source observation:{" "}
                      {new Date(c.source_time).toISOString()}
                    </p>
                    <small>
                      Claimant {c.agent_id.slice(0, 8)} · Source{" "}
                      {c.source_id.slice(0, 8)}
                    </small>
                  </div>
                ))}
            </div>
            <p>{r.evidence.reason}</p>
            <code>{r.evidence.policy}</code>
            <button
              className="text-button"
              onClick={() =>
                void action(`/projects/${project}/claims/resolve`, {
                  subject: r.subject,
                  predicate: r.predicate,
                })
              }
            >
              Re-evaluate evidence
            </button>
          </article>
        ))}
        {!!data.claims.length && (
          <JsonDetail data={data.claims} label="All immutable claim records" />
        )}
      </section>
    );
  return (
    <section>
      <div className="section-title">
        <h2>Saved workflows</h2>
        <ShieldCheck size={20} />
      </div>
      {!data.versions.length && (
        <p className="subtle">
          New workflow proposals bind exact artifact hashes, source checks,
          sandbox preconditions and independent verification.
        </p>
      )}
      {data.versions.map((v: Row) => (
        <article className="causal-card" key={v.id}>
          <div className="row">
            <h3>{v.family}</h3>
            <Badge value={`v${v.version}`} />
            <Badge value={v.status} />
          </div>
          <p>
            {v.manifest.length} files ·{" "}
            {v.verifier_run
              ? "Checked by a separate run"
              : "Waiting for independent checks"}{" "}
            ·{" "}
            {
              data.uses.filter(
                (u: Row) => u.procedure_id === v.id && u.completed_at,
              ).length
            }{" "}
            verified reuses
          </p>
          <details className="plain-details version-details">
            <summary>Files, checks and reuse history</summary>
            <p>
              Independent verifier:{" "}
              {v.verifier_run
                ? v.verifier_run.slice(0, 8)
                : "awaiting real execution"}
            </p>
            {v.manifest.map((a: Row) => (
              <div className="manifest-row" key={a.id}>
                <strong>{a.name}</strong>
                <code>{a.sha256}</code>
              </div>
            ))}
            <JsonDetail data={v.preconditions} label="Bound preconditions" />
            {data.uses
              .filter((u: Row) => u.procedure_id === v.id)
              .map((u: Row) => (
                <div className="reuse-metrics" key={u.run_id}>
                  <Badge
                    value={
                      u.completed_at ? "reuse verified" : "reuse in progress"
                    }
                  />
                  {u.metrics && (
                    <>
                      <p>
                        Source-run execution-call delta:{" "}
                        <strong>{u.metrics.savings.tool_executions}</strong> ·
                        Source-run agent-token delta:{" "}
                        <strong>{u.metrics.savings.model_tokens}</strong>
                      </p>
                      <small>{u.metrics.comparison}</small>
                      <p>
                        Source work and reuse can involve different models and
                        tasks. Use the live comparison below for the matched
                        verification measurement.
                      </p>
                      <JsonDetail
                        data={u.metrics}
                        label="Measured baseline and reuse"
                      />
                    </>
                  )}
                </div>
              ))}
          </details>
        </article>
      ))}
      {!!data.passports?.length && (
        <details className="causal-card memory-passports">
          <summary>Memory passports</summary>
          <p>
            See which exact memory revisions shaped each context selection.
            Token counts describe memory projections, not the complete model
            prompt or billed usage.
          </p>
          {data.passports
            .slice(0, showAllPassports ? 60 : 3)
            .map((receipt: Row) => (
              <article className="graph-witness" key={receipt.id}>
                <div className="row">
                  <strong>{receipt.role}</strong>
                  <code>{receipt.run_id.slice(0, 8)}</code>
                  <Badge value={receipt.payload.mode} />
                </div>
                <p>
                  {receipt.payload.records.length} memories ·{" "}
                  {receipt.payload.context_tokens.toLocaleString()} /{" "}
                  {receipt.payload.budget_tokens.toLocaleString()} projection
                  tokens · {receipt.payload.omitted_count} omitted
                </p>
                <small>
                  Full source records:{" "}
                  {receipt.payload.source_record_tokens.toLocaleString()}{" "}
                  tokens. Receipt #{receipt.id}. The fingerprint records
                  provenance; it is not a cryptographic signature.
                </small>
                <JsonDetail
                  label="Inspect revisions and context fingerprint"
                  data={receipt.payload}
                />
              </article>
            ))}
          {data.passports.length > 3 && (
            <button
              className="text-button"
              onClick={() => setShowAllPassports((value) => !value)}
            >
              {showAllPassports ? "Show fewer receipts" : "Show more receipts"}
            </button>
          )}
        </details>
      )}
      {!!data.deliveries?.length && (
        <details className="causal-card handoff-deliveries">
          <summary>Durable handoff receipts</summary>
          <p>
            Identical handoff retries reuse one receiver. A receiver becomes
            claimable only after its envelope is committed. Evidence revisions
            are checked again before acknowledgement.
          </p>
          {data.deliveries.map((delivery: Row) => (
            <article className="graph-witness" key={delivery.id}>
              <div className="row">
                <code>{delivery.from_run.slice(0, 8)}</code>
                <ArrowRight size={16} />
                <code>{delivery.to_run.slice(0, 8)}</code>
                <Badge
                  value={
                    delivery.acknowledged_at
                      ? "acknowledged"
                      : ["cancelled", "failed", "stale"].includes(
                            delivery.status,
                          )
                        ? "delivery stopped"
                        : "awaiting receiver"
                  }
                />
              </div>
              <p>
                {delivery.role} · {delivery.status} ·{" "}
                {delivery.packet.evidence.length} revision-bound memories
              </p>
              <JsonDetail label="Inspect delivery envelope" data={delivery} />
            </article>
          ))}
        </details>
      )}
      {data.benchmarks?.map((b: Row) => (
        <details className="causal-card procedure-benchmark" key={b.id}>
          <summary>
            {b.payload.kind === "live_model_series"
              ? "Repeated live memory comparison"
              : b.payload.kind === "live_model_comparison"
                ? "Live model reuse comparison"
                : "Measured reuse comparison"}
          </summary>
          <p>{b.payload.method}</p>
          {b.payload.kind === "live_model_series" ? (
            <>
              <p>
                {b.payload.pairs} alternating pairs. Both paths ran the same
                real acceptance tests on the same artifact hashes.
              </p>
              <div className="claim-grid">
                {(["baseline", "reuse"] as const).map((arm) => (
                  <div className="claim" key={arm}>
                    <h3>
                      {arm === "baseline"
                        ? "Known-file baseline"
                        : "Memory capsule reuse"}
                    </h3>
                    <p>
                      Median: {b.payload.summary[arm].provider_calls} provider
                      calls
                    </p>
                    <p>
                      {b.payload.summary[arm].known_tokens.toLocaleString()}{" "}
                      observed tokens
                    </p>
                    <p>
                      {b.payload.summary[arm].elapsed_seconds.toFixed(1)}{" "}
                      seconds including queue and startup
                    </p>
                  </div>
                ))}
              </div>
              <p>
                Median paired savings:{" "}
                {b.payload.median_paired_savings.provider_calls} calls ·{" "}
                {b.payload.median_paired_savings.known_tokens.toLocaleString()}{" "}
                tokens ·{" "}
                {b.payload.median_paired_savings.elapsed_seconds.toFixed(1)}{" "}
                seconds.
              </p>
              <small>
                Small local sample, not a general speed or cost guarantee.
                Positive values favor reuse. Source-run deltas and the
                historical single pair remain separate.
              </small>
            </>
          ) : b.payload.kind === "live_model_comparison" ? (
            <>
              <div className="claim-grid">
                {(["baseline", "reuse"] as const).map((arm) => {
                  const trial = b.payload.comparison.trials[arm];
                  return (
                    <div className="claim" key={arm}>
                      <h3>
                        {arm === "baseline"
                          ? "Exact artifact bundle"
                          : "Verified procedure"}
                      </h3>
                      <p>
                        {trial.provider_calls_observed} observed provider calls
                      </p>
                      <p>
                        {trial.model_tokens_observed.toLocaleString()} observed
                        tokens
                      </p>
                      <p>
                        {trial.elapsed_seconds.toFixed(1)} seconds, including
                        queue and startup
                      </p>
                      <small>
                        {trial.provider_failed_calls} failed provider calls;
                        their billed tokens may be unknown
                      </small>
                    </div>
                  );
                })}
              </div>
              <p>
                Signed savings:{" "}
                {b.payload.comparison.signed_savings.provider_calls_observed}{" "}
                calls ·{" "}
                {b.payload.comparison.signed_savings.model_tokens_observed.toLocaleString()}{" "}
                observed tokens ·{" "}
                {b.payload.comparison.signed_savings.elapsed_seconds.toFixed(1)}{" "}
                seconds
              </p>
              <p>
                Both arms use {b.payload.comparison.trials.baseline.model}. The
                baseline already has the exact source files. This measures
                verification reuse, not code-generation avoidance.
              </p>
            </>
          ) : (
            <>
              <div className="claim-grid">
                <div className="claim">
                  <h3>Exact artifact bundle</h3>
                  <p>
                    {b.payload.summary.baseline_median_ms.toFixed(0)} ms median
                  </p>
                </div>
                <div className="claim">
                  <h3>Verified procedure</h3>
                  <p>
                    {b.payload.summary.reuse_median_ms.toFixed(0)} ms median
                  </p>
                </div>
              </div>
              <p>
                Time saved (median paired difference):{" "}
                {b.payload.summary.time_saved_ms.toFixed(0)} ms · Tool calls
                saved: {b.payload.summary.tool_calls_saved} · Model tokens
                saved: {b.payload.summary.model_tokens_saved}
              </p>
            </>
          )}
          <small>{b.payload.limitations}</small>
          <JsonDetail
            data={b.payload}
            label="Inspect paired trials, checks, hashes and timing"
          />
        </details>
      ))}
    </section>
  );
}

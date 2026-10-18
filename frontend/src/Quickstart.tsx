import { ArrowRight, CheckCircle2, Compass, ShieldCheck } from "lucide-react";
import { BeginnerGuide } from "./BeginnerGuide";

const features = [
  [
    "profile",
    "Profile & settings",
    "Bring your own provider keys",
    "Save encrypted personal connections for Groq, Grok, Anthropic, Gemini, OpenAI, DeepSeek, OpenCode and other supported providers. Select an exact model and API protocol, test it explicitly, and optionally add your own search key. Visitors never inherit host provider keys.",
  ],
  [
    "workspace",
    "Workspace",
    "Start with a clear goal",
    "Write the result you want, your constraints and what success looks like. Choose an existing conversation to continue its history, or start a new one. Memory settings let you use shared context only.",
  ],
  [
    "workflows",
    "Workflows",
    "Plan work with several stages",
    "Save a draft with milestones, dependencies, specialists and acceptance rules. Planning does not call the model. Start explicitly, then follow progress, pause or resume, record requested events and approve milestones when ready.",
  ],
  [
    "agents",
    "Custom agents",
    "Create focused specialists",
    "Choose a name, base role, instructions and allowed tools. Assign the specialist to a matching workflow milestone. The tool list narrows the role's permissions. Saved plans keep their own copy of the profile.",
  ],
  [
    "team",
    "Agent team",
    "Follow delegation and handoffs",
    "Inspect coordinator, researcher, builder, verifier and curator tasks. Independent work can run in parallel. Open a task to see results, child tasks, dependencies, failures and evidence instead of assuming it completed.",
  ],
  [
    "memory",
    "Memory",
    "Keep and correct useful context",
    "Past activity is episodic memory, facts are semantic memory, and ways of working are procedural memory. Add context, filter by type and correct facts as they change. Visibility controls separate shared, user and agent knowledge.",
  ],
  [
    "causes",
    "Causal timeline",
    "See what a correction changes",
    "Follow a corrected fact to the tasks that used it. Inspect the superseded evidence, stale work and revised plan. Expand graph evidence to see the relationships behind the decision.",
  ],
  [
    "procedures",
    "Procedures",
    "Reuse independently checked work",
    "Inspect versioned procedures, preconditions, exact artifact manifests and verification history. A separate verifier must check the files before activation. Open Memory passports to see selected evidence versions and Durable handoff receipts to inspect delivery and acknowledgement. Measurements distinguish observed reuse costs from unproven savings.",
  ],
  [
    "artifacts",
    "Artifacts",
    "Download the real outputs",
    "Find published files, reports and source changes. Download the version you need and expand file details to inspect its hash and producing task. A published file alone does not mean its contents passed tests.",
  ],
  [
    "graph",
    "Knowledge graph",
    "Explore connected evidence",
    "Inspect how memories, entities, sources and tasks connect in FalkorDB. Use it when an answer depends on relationships or when you need to trace which knowledge shaped a task.",
  ],
  [
    "conflicts",
    "Claim resolution",
    "Compare competing observations",
    "Keep both claims and their sources. Review source timestamps and the selected value. Equally timed contradictory observations stay unresolved. A later timestamp does not guarantee that a source is correct.",
  ],
  [
    "timeline",
    "Run timeline",
    "Inspect the recorded activity",
    "Follow actual actions, updates, task transitions and handoffs. Use the event history to understand what happened or investigate a blocked result.",
  ],
  [
    "sandbox",
    "Sandbox console",
    "Inspect execution and tests",
    "Review the actual commands, outputs and test receipts behind a task. Builders and verifiers use separate restricted Docker workspaces. The console does not grant general access to the host computer.",
  ],
  [
    "settings",
    "System & access",
    "Manage connections and access",
    "Check service readiness, workspace membership, ingestion jobs and evaluations. Owners can configure allowed remote MCP tools. Provider keys being configured does not establish that inference works or that quota remains.",
  ],
];

export function Quickstart({
  navigate,
}: {
  navigate?: (page: string) => void;
}) {
  const open = (page: string, label: string) =>
    navigate ? (
      <button className="text-button" onClick={() => navigate(page)}>
        {label}
        <ArrowRight size={15} />
      </button>
    ) : (
      <a className="quick-link" href={`/#/${page}`}>
        {label}
        <ArrowRight size={15} />
      </a>
    );
  return (
    <div className="quickstart">
      <section className="quick-hero">
        <Compass size={28} />
        <div>
          <span className="eyebrow">START HERE</span>
          <h2>A clear path from your goal to checked results.</h2>
          <p>
            ENGRAM ENGINE is a team of AI agents that shares persistent
            graph memory, coordinates work, and traces how changing knowledge
            affects its decisions.
          </p>
          <p>
            Use the workspace for a single goal. Use a workflow when work needs
            several specialists, dependencies or a human decision.
          </p>
          <p>
            <a href="/evidence/live/">
              Inspect the verified ORCHID demo and measurements
            </a>
          </p>
        </div>
      </section>
      <nav className="quick-contents" aria-label="Quickstart contents">
        <a href="#first-run">First five minutes</a>
        <a href="#beginner-guide">Detailed beginner handbook</a>
        <a href="#feature-map">Every feature</a>
        <a href="#memory-guide">How memory works</a>
        <a href="#sandbox-guide">Sandbox boundaries</a>
        <a href="#when-blocked">When work is blocked</a>
      </nav>
      <section id="first-run" className="quick-section">
        <span className="eyebrow">YOUR FIRST FIVE MINUTES</span>
        <h2>Start small, then build up.</h2>
        <ol className="quick-steps">
          <li>
            <strong>Start building in your own workspace.</strong>
            <p>
              Select Start building with no login or sign-up form. Add your own
              AI key in Profile &amp; settings before running work. Your
              workspace separates your team's data. The project selector at the
              top switches the work you are viewing. Use the plus button to
              create a project.
            </p>
          </li>
          <li>
            <strong>Add the context your team needs.</strong>
            <p>
              Upload a document or add a fact in Memory. For coding work, import
              a source ZIP inside Workflows. Source files are shared within that
              project, so check what you upload.
            </p>
          </li>
          <li>
            <strong>Give the team a concrete goal.</strong>
            <p>
              Example: inspect the supplied Python source, repair one failing
              behavior, run its tests in a sandbox and prepare the changes for
              review.
            </p>
          </li>
          <li>
            <strong>Review the plan before starting.</strong>
            <p>
              The suggested workflow plans and investigates in parallel, then
              implements, verifies independently and prepares a review packet.
              Set budgets and approval gates. Save a draft first; start only
              when your provider is ready.
            </p>
          </li>
          <li>
            <strong>Follow progress and inspect the result.</strong>
            <p>
              Review the team, actual test receipts and downloaded artifacts.
              Approve only the milestone or exact external action you intend. A
              blocked task needs attention, not an assumption of success.
            </p>
          </li>
        </ol>
        <div className="row">
          {open("workspace", "Open Workspace")}
          {open("workflows", "Plan a workflow")}
        </div>
      </section>
      <BeginnerGuide />
      <section id="feature-map" className="quick-section">
        <span className="eyebrow">THE COMPLETE WEBSITE</span>
        <h2>Find the right page.</h2>
        <p>
          Work and Memory are always visible in the sidebar. Technical
          inspection and administration are under Inspect &amp; manage. The Go
          to page menu reaches every page directly, including on a phone.
        </p>
        <div className="quick-feature-grid">
          {features.map(([page, name, title, text]) => (
            <article className="quick-card" key={page}>
              <span className="eyebrow">{name}</span>
              <h3>{title}</h3>
              <p>{text}</p>
              {open(page, `Open ${name}`)}
            </article>
          ))}
        </div>
      </section>
      <section id="memory-guide" className="quick-section">
        <h2>Memory has a type, a scope and a lifecycle.</h2>
        <div className="quick-feature-grid">
          {[
            [
              "Episodic",
              "What happened",
              "Conversations, observations, task activity and outcomes preserve history between sessions.",
            ],
            [
              "Semantic",
              "What is known",
              "Sourced facts can be updated and superseded. Corrections preserve the older evidence and identify affected work.",
            ],
            [
              "Procedural",
              "How to do it",
              "Tools and checked procedures can be retrieved when relevant. Procedure versions bind files, preconditions and verification evidence.",
            ],
          ].map(([type, title, text]) => (
            <article className="quick-card" key={type}>
              <span className="eyebrow">{type}</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
        <p>
          Pinned context, a recent revision-aware cache and persistent graph
          retrieval form three storage tiers. These tiers are separate from the
          three memory types. Retrieval uses the permitted visibility scope;
          shared-only tasks exclude private context from normal memory reads.
        </p>
      </section>
      <section id="sandbox-guide" className="quick-section quick-boundaries">
        <ShieldCheck size={24} />
        <h2>What the sandbox enforces.</h2>
        <ul>
          <li>
            Each run has its own Docker workspace. A verifier receives exact
            published predecessor files in a separate workspace.
          </li>
          <li>
            Execution uses an unprivileged user, a read-only root filesystem, no
            container network, dropped capabilities and no new privileges.
          </li>
          <li>
            Commands are bounded to 120 seconds, with one CPU, 512 MiB memory
            and 128 processes. Provider keys, the Docker socket and host folders
            are not mounted into the sandbox.
          </li>
          <li>
            Files and recognized passing Python checks are recorded. Independent
            workflow verification also compares the current file hashes against
            the handed-off versions.
          </li>
        </ul>
        <p>
          Containers share the host kernel. The workspace has no disk quota, and
          tests can be incomplete. Host-side model, search and authorized
          integration tools can use the network. An approval or model-based
          admission check is not proof that content is safe or true.
        </p>
      </section>
      <section id="when-blocked" className="quick-section">
        <CheckCircle2 size={24} />
        <h2>Know what to do next.</h2>
        <dl className="quick-troubleshooting">
          <dt>A service is unavailable</dt>
          <dd>
            Open System &amp; access and check the dependency. A running website
            does not establish that models, graph storage or sandbox execution
            are ready.
          </dd>
          <dt>The model reports quota or tool-argument errors</dt>
          <dd>
            Pause the workflow and inspect the task error. Provider inference
            remains subject to available quota and model reliability. No
            substitute model or successful result is invented.
          </dd>
          <dt>A milestone awaits approval or an event</dt>
          <dd>
            Open Workflows, inspect completed dependencies, then approve the
            milestone or record the requested event. These gates persist across
            restarts.
          </dd>
          <dt>A task failed or became stale</dt>
          <dd>
            Inspect its evidence and fix the cause. Retry explicitly with fresh
            approval. Correcting a fact can invalidate work that depended on it.
          </dd>
          <dt>An external action is pending or uncertain</dt>
          <dd>
            Inspect the exact tool and arguments before approving. An uncertain
            remote outcome is not repeated automatically. Check the remote
            system before reconciliation.
          </dd>
        </dl>
      </section>
    </div>
  );
}

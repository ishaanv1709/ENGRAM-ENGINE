import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Check,
  ChevronDown,
  Command,
  Cpu,
  Compass,
  FileText,
  GitBranch,
  Layers3,
  Network,
  Plus,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { api, post, setWorkspace, type Row } from "./api";
import { SandboxPanel, MCPPanel, EvaluationButton } from "./ServicePanels";
import {
  ArtifactPanel,
  Badge,
  Empty,
  JsonDetail,
  MemoryPanel,
  RunCard,
  UploadButton,
} from "./components";

import { CoordinationPanel } from "./CoordinationPanel";
import { WorkflowPanel, AgentProfilesPanel } from "./WorkflowPanel";
import { Quickstart } from "./Quickstart";
import { ProfilePanel } from "./ProfilePanel";
import { Home } from "./Home";

const NAV = [
  { id: "quickstart", icon: Compass, label: "Quickstart" },
  { id: "profile", icon: Users, label: "Profile & settings" },
  { id: "workspace", icon: Command, label: "Workspace" },
  { id: "workflows", icon: GitBranch, label: "Workflows" },
  { id: "agents", icon: Users, label: "Custom agents" },
  { id: "team", icon: Users, label: "Agent team" },
  { id: "memory", icon: BrainCircuit, label: "Memory" },
  { id: "graph", icon: Network, label: "Knowledge graph" },
  { id: "procedures", icon: Layers3, label: "Procedures" },
  { id: "artifacts", icon: FileText, label: "Artifacts" },
  { id: "causes", icon: GitBranch, label: "Causal timeline" },
  { id: "conflicts", icon: ShieldCheck, label: "Claim resolution" },
  { id: "timeline", icon: Activity, label: "Run timeline" },
  { id: "sandbox", icon: ShieldCheck, label: "Sandbox console" },
  { id: "settings", icon: Settings, label: "System & access" },
];
const WORK_NAV = ["workspace", "workflows", "team", "artifacts"];
const MEMORY_NAV = ["memory", "causes", "procedures"];
const INSPECT_NAV = [
  "agents",
  "graph",
  "conflicts",
  "timeline",
  "sandbox",
  "settings",
];
const PROJECT_DESCRIPTION =
  "ENGRAM ENGINE is a team of AI agents that shares persistent graph memory, coordinates work, and traces how changing knowledge affects its decisions.";
const LOCAL_HOST = ["localhost", "127.0.0.1", "[::1]"].includes(
  location.hostname,
);
const TITLES: Record<string, [string, string]> = {
  profile: [
    "Your profile. Your keys.",
    "Choose the providers and models your team uses, with your own credentials.",
  ],
  quickstart: [
    "Your guide to ENGRAM ENGINE.",
    "Learn the flow, find every feature and understand what each result means.",
  ],
  workflows: [
    "Give complex work a durable plan.",
    "Review milestones, follow progress and approve the actions that need you.",
  ],
  agents: [
    "Build your own specialists.",
    "Choose instructions, role permissions and tools, then assign specialists to workflow milestones.",
  ],
  causes: [
    "What changed, and what needs updating?",
    "Follow a corrected fact to the work that used it and the plan that follows.",
  ],
  conflicts: [
    "Compare conflicting facts.",
    "See each source, which claim was selected, and why.",
  ],
  workspace: ["Give your team a goal.", PROJECT_DESCRIPTION],
  team: [
    "Follow your team's work.",
    "See who is working, what they produced, and what needs attention.",
  ],
  memory: [
    "What your team remembers.",
    "Save useful context, find past knowledge, and correct facts when they change.",
  ],
  graph: [
    "See how everything connects.",
    "Inspect the evidence behind facts, corrections, and decisions.",
  ],
  procedures: [
    "Reuse work that has been checked.",
    "Saved workflows keep their files, versions and verification history together.",
  ],
  artifacts: [
    "Your project's files.",
    "Download published results and inspect where each file came from.",
  ],
  timeline: [
    "The activity behind the work.",
    "Inspect recorded actions, changes, and handoffs in order.",
  ],
  sandbox: [
    "Real execution. Clear boundaries.",
    "Inspect the commands and checks behind each result.",
  ],
  settings: [
    "Manage your workspace.",
    "Check connections, manage access, and inspect processing or evaluation results.",
  ],
};

export default function App() {
  if (location.pathname === "/" && !location.hash.startsWith("#/")) return <Home />;
  return <WorkspaceApp />;
}

function WorkspaceApp() {
  const [me, setMe] = useState<Row | null>(null);
  const [health, setHealth] = useState<Row>({ services: {} });
  const [tab, setTab] = useState(() =>
    NAV.some((item) => item.id === location.hash.slice(2))
      ? location.hash.slice(2)
      : "workspace",
  );
  const [inspectOpen, setInspectOpen] = useState(false);
  const [projects, setProjects] = useState<Row[]>([]);
  const [project, setProject] = useState("");
  const [runs, setRuns] = useState<Row[]>([]);
  const [memories, setMemories] = useState<Row[]>([]);
  const [artifacts, setArtifacts] = useState<Row[]>([]);
  const [events, setEvents] = useState<Row[]>([]);
  const [jobs, setJobs] = useState<Row[]>([]);
  const [graph, setGraph] = useState<Row>({ nodes: [], edges: [] });
  const [error, setError] = useState("");
  const [objective, setObjective] = useState("");
  const [sharedOnly, setSharedOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [conversation, setConversation] = useState("");
  const [messages, setMessages] = useState<Row[]>([]);
  const [conversations, setConversations] = useState<Row[]>([]);
  const [selected, setSelected] = useState<Row | null>(null);
  const [members, setMembers] = useState<Row[]>([]);
  const [evaluations, setEvaluations] = useState<Row[]>([]);
  const fail = useCallback(
    (e: unknown) => setError(e instanceof Error ? e.message : String(e)),
    [],
  );
  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await api("/health"));
    } catch (e) {
      fail(e);
    }
  }, [fail]);
  const loadMe = useCallback(async () => {
    try {
      const user = await api("/me");
      setWorkspace(user.workspace_id);
      setMe(user);
    } catch {
      setMe(null);
    }
  }, []);
  useEffect(() => {
    void loadMe();
    void refreshHealth();
  }, [loadMe, refreshHealth]);
  useEffect(() => {
    if (!me) return;
    api<Row[]>("/projects")
      .then((rows) => {
        setProjects(rows);
        setProject((p) =>
          rows.some((r) => r.id === p) ? p : rows[0]?.id || "",
        );
      })
      .catch(fail);
  }, [me, fail]);
  const refresh = useCallback(async () => {
    if (!project || !me) return;
    const paths = [
      `/projects/${project}/runs`,
      `/projects/${project}/memory`,
      `/projects/${project}/artifacts`,
      "/events",
      "/jobs",
      `/projects/${project}/graph`,
      `/projects/${project}/conversations`,
      "/members",
      "/evaluations",
    ];
    const results = await Promise.allSettled(paths.map((p) => api<Row[]>(p)));
    const setters = [
      setRuns,
      setMemories,
      setArtifacts,
      setEvents,
      setJobs,
      (v: any) => setGraph(v),
      setConversations,
      setMembers,
      setEvaluations,
    ];
    results.forEach((r, i) => {
      if (r.status === "fulfilled") setters[i](r.value);
      else fail(r.reason);
    });
  }, [project, me, fail]);
  useEffect(() => {
    setConversation("");
    setMessages([]);
    setSelected(null);
    void refresh();
  }, [project, refresh]);
  useEffect(() => {
    if (!me || !project) return;
    const timer = setInterval(() => {
      void refresh();
    }, 5000);
    return () => clearInterval(timer);
  }, [me, project, refresh]);
  useEffect(() => {
    if (conversation)
      api<Row[]>(`/conversations/${conversation}/messages`)
        .then(setMessages)
        .catch(fail);
  }, [conversation, runs, fail]);

  async function startBuilding() {
    setBusy(true);
    setError("");
    try {
      setWorkspace("");
      await post("/auth/start");
      await loadMe();
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }
  async function newProject() {
    const value = prompt("Name your project");
    if (!value) return;
    try {
      const p = await post("/projects", { name: value });
      setProjects((prev) => [...prev, p]);
      setProject(p.id);
    } catch (e) {
      fail(e);
    }
  }
  async function submit() {
    if (!objective.trim() || !project) return;
    setBusy(true);
    setError("");
    try {
      let c = conversation;
      if (!c) {
        const created = await post(`/projects/${project}/conversations`, {
          name: objective.slice(0, 70),
        });
        c = created.id;
        setConversation(c);
      }
      await post(`/projects/${project}/runs`, {
        objective,
        conversation_id: c,
        context_scope: sharedOnly ? "team" : "auto",
      });
      setObjective("");
      await refresh();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  async function addMember() {
    const value = prompt("Email of an existing registered user");
    if (!value) return;
    try {
      await post("/members", { email: value, role: "member" });
      await refresh();
    } catch (e) {
      fail(e);
    }
  }
  const running = runs.filter((r) => r.status === "running").length;
  const ready = Object.values<Row>(health.services || {}).filter(
    (s) => s.state === "ready",
  ).length;
  const title = TITLES[tab];
  const navigate = (next: string) => {
    history.replaceState(null, "", `#/${next}`);
    setTab(next);
    setSelected(null);
    if (INSPECT_NAV.includes(next)) setInspectOpen(true);
  };
  const navItem = (id: string) => {
    const item = NAV.find((entry) => entry.id === id)!;
    return (
      <button
        key={id}
        className={tab === id ? "selected" : ""}
        aria-current={tab === id ? "page" : undefined}
        aria-label={item.label}
        title={item.label}
        onClick={() => navigate(id)}
      >
        <item.icon size={18} />
        <span className="nav-text">{item.label}</span>
        {id === "team" && running ? (
          <span className="nav-count">{running}</span>
        ) : null}
      </button>
    );
  };

  if (location.pathname === "/quickstart")
    return (
      <div className="public-guide">
        <header>
          <a className="brand" href="/">
            <img
              className="brand-mark"
              src="/assets/engram-mark.svg"
              alt="ENGRAM ENGINE memory loop"
            />
            ENGRAM ENGINE
          </a>
          <a className="button" href="/">
            Open workspace
          </a>
        </header>
        <main>
          <h1>Quickstart</h1>
          <Quickstart />
        </main>
      </div>
    );

  if (!me)
    return (
      <div className="auth-layout">
        <div className="auth-story">
          <div className="brand">
            <img
              className="brand-mark"
              src="/assets/engram-mark.svg"
              alt="ENGRAM ENGINE memory loop"
            />
            <span>
              ENGRAM<span className="brand-light"> ENGINE</span>
            </span>
          </div>
          <div>
            <span className="eyebrow">A TEAM THAT REMEMBERS</span>
            <h1>
              Build with a team
              <br />
              that remembers.
            </h1>
            <p>{PROJECT_DESCRIPTION}</p>
            <div className="auth-pills">
              <span>
                <GitBranch size={15} />
                Connected memory
              </span>
              <span>
                <ShieldCheck size={15} />
                Isolated execution
              </span>
            </div>
          </div>
          <span className="subtle">
            Built on persistent memory · Powered by FalkorDB
          </span>
        </div>
        <div className="auth-form">
          <span className="eyebrow">YOUR NEXT IDEA STARTS HERE</span>
          <h2>Start building.</h2>
          <p className="subtle">
            No login. No sign-up form. Get your own workspace, bring your own AI
            key and put your team to work.
          </p>
          {error ? (
            <div className="error" role="alert">
              {error}
            </div>
          ) : null}
          <button
            className="primary wide"
            disabled={busy}
            onClick={() => void startBuilding()}
          >
            {busy ? "Opening workspace…" : "Start building"}
            <ArrowRight size={16} />
          </button>
          <p className="subtle space-top">
            This browser remembers your workspace. Clearing site data or using
            another browser creates a separate workspace.
          </p>
          <a className="quick-link" href="/quickstart">
            Read the Quickstart <ArrowRight size={15} />
          </a>
          <div className="auth-readiness">
            <span className="status-dot" />
            {LOCAL_HOST ? "Local deployment" : "HTTPS demo"} · {ready} services
            ready
            <button
              className="icon-button"
              aria-label="Refresh service status"
              onClick={refreshHealth}
            >
              <RefreshCw size={13} />
            </button>
          </div>
          <details className="connection-details">
            <summary>Connection details</summary>
            <div className="mini-services">
              {Object.entries<Row>(health.services || {}).map(
                ([key, value]) => (
                  <span key={key}>
                    {key}
                    <Badge value={value.state} />
                  </span>
                ),
              )}
            </div>
          </details>
        </div>
      </div>
    );

  return (
    <div className="app-shell">
      <aside>
        <a className="brand" href="/" aria-label="ENGRAM ENGINE home">
          <img
            className="brand-mark"
            src="/assets/engram-mark.svg"
            alt="ENGRAM ENGINE memory loop"
          />
          <span>
            ENGRAM <small>ENGINE</small>
          </span>
        </a>
        <div className="workspace-switch">
          <span className="avatar">{me.name.slice(0, 1).toUpperCase()}</span>
          <select
            aria-label="Workspace"
            value={me.workspace_id}
            onChange={(e) => {
              setWorkspace(e.target.value);
              void loadMe();
            }}
          >
            {me.workspaces.map((w: Row) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
          <ChevronDown size={14} />
        </div>
        <nav aria-label="Project navigation">
          <div className="nav-group">
            <span className="nav-label">START HERE</span>
            {navItem("quickstart")}
            {navItem("profile")}
          </div>
          <div className="nav-group">
            <span className="nav-label">WORK</span>
            {WORK_NAV.map(navItem)}
          </div>
          <div className="nav-group">
            <span className="nav-label">MEMORY</span>
            {MEMORY_NAV.map(navItem)}
          </div>
          <details
            className="nav-inspect"
            open={inspectOpen}
            onToggle={(event) => setInspectOpen(event.currentTarget.open)}
          >
            <summary title="Inspect & manage">
              <Settings size={16} />
              <span className="nav-text">Inspect & manage</span>
              <ChevronDown size={13} className="disclosure-chevron" />
            </summary>
            <div>{INSPECT_NAV.map(navItem)}</div>
          </details>
        </nav>
        <div className="sidebar-bottom">
          <div className="local-status">
            <span className="status-dot" />
            {LOCAL_HOST ? "LOCAL ENVIRONMENT" : "PUBLIC DEMO"}
          </div>
          <p>
            Memory persists.
            <br />
            Progress carries forward.
          </p>
          <button className="text-button" onClick={() => navigate("profile")}>
            <Settings size={15} />
            My profile
          </button>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumbs">
            Workspace <span>/</span>
            <select
              aria-label="Project"
              value={project}
              onChange={(e) => setProject(e.target.value)}
            >
              <option value="" disabled>
                Select a project
              </option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <button
              className="icon-button"
              title="Create project"
              aria-label="Create project"
              onClick={newProject}
            >
              <Plus size={16} />
            </button>
          </div>
          <div className="row">
            <select
              className="page-picker"
              aria-label="Go to page"
              value={tab}
              onChange={(e) => navigate(e.target.value)}
            >
              {NAV.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
            <span className="header-status">
              <span className="status-dot" />
              {running ? `${running} agents working` : "No tasks running"}
            </span>
            <span className="avatar small-avatar">
              {me.name.slice(0, 1).toUpperCase()}
            </span>
          </div>
        </header>
        <div className="page">
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                ENGRAM ENGINE /{" "}
                {NAV.find((item) => item.id === tab)?.label.toUpperCase()}
              </span>
              <h1>{title[0]}</h1>
              <p>{title[1]}</p>
            </div>
            <div className="row">
              <UploadButton project={project} refresh={refresh} fail={fail} />
              <button
                className="icon-button bordered"
                aria-label="Refresh workspace"
                onClick={() => {
                  void refresh();
                  void refreshHealth();
                }}
              >
                <RefreshCw size={17} />
              </button>
            </div>
          </div>
          {error ? (
            <div className="error" role="alert">
              <span>{error}</span>
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={16} />
              </button>
            </div>
          ) : null}
          {tab === "quickstart" ? <Quickstart navigate={navigate} /> : null}
          {tab === "profile" ? (
            <ProfilePanel
              fail={fail}
              changed={async () => {
                await loadMe();
                await refreshHealth();
              }}
            />
          ) : null}
          {!me.has_provider && !["profile", "quickstart"].includes(tab) ? (
            <div className="provider-banner">
              <div>
                <strong>Connect your own AI provider.</strong>
                <p>
                  Explore and save drafts now. Add your key before running
                  agents or processing memory.
                </p>
              </div>
              <button className="button" onClick={() => navigate("profile")}>
                Add your AI key
              </button>
            </div>
          ) : null}
          {!project && !["quickstart", "profile"].includes(tab) ? (
            <div className="welcome-create">
              <Sparkles size={36} />
              <h2>Make room for your next idea.</h2>
              <p>
                Create a project to start connecting knowledge and assigning
                work.
              </p>
              <button className="primary" onClick={newProject}>
                <Plus size={16} />
                Create your first project
              </button>
            </div>
          ) : null}
          {project && tab === "workspace" ? (
            <>
              <div className="workspace-grid">
                <section className="mission">
                  <div className="section-title">
                    <span className="green-icon">
                      <Command size={18} />
                    </span>
                    <h2>Start a task</h2>
                  </div>
                  <p>
                    Describe the result you want. Include any constraints and
                    what a good result looks like.
                  </p>
                  <textarea
                    aria-label="Team objective"
                    value={objective}
                    onChange={(e) => setObjective(e.target.value)}
                    placeholder="Review the project documents and create a release checklist with sources and next steps…"
                  />
                  <button
                    className="text-button example-goal"
                    onClick={() =>
                      setObjective(
                        "Review the project documents and create a release checklist with sources, open questions, and next steps.",
                      )
                    }
                  >
                    Use an example goal
                  </button>
                  <button
                    className="text-button workflow-link"
                    onClick={() => navigate("workflows")}
                  >
                    Need several milestones? Plan a workflow{" "}
                    <ArrowRight size={14} />
                  </button>
                  <div className="mission-footer">
                    <details className="task-options">
                      <summary>Memory settings</summary>
                      <label className="shared-context-option">
                        <input
                          type="checkbox"
                          checked={sharedOnly}
                          onChange={(event) =>
                            setSharedOnly(event.target.checked)
                          }
                        />
                        Shared memory only
                      </label>
                      <p>
                        When enabled, the task retrieves shared context only.
                        Otherwise, it may also use private memories you have
                        permission to access.
                      </p>
                    </details>
                    <button
                      className="primary"
                      disabled={busy || !objective.trim()}
                      onClick={submit}
                    >
                      {busy ? "Assigning…" : "Start working"}
                      <ArrowRight size={16} />
                    </button>
                  </div>
                  <div className="capabilities">
                    <span>
                      <GitBranch size={14} />
                      Parallel work
                    </span>
                    <span>
                      <BrainCircuit size={14} />
                      Shared context
                    </span>
                    <span>
                      <Check size={14} />
                      Checks and evidence
                    </span>
                  </div>
                </section>
                <section className="team-summary">
                  <span className="eyebrow">HOW TO USE ENGRAM ENGINE</span>
                  <h2>One goal, shared context.</h2>
                  <div className="start-guide">
                    <button onClick={() => navigate("team")}>
                      <span>1</span>
                      <div>
                        <strong>Follow the work</strong>
                        <small>Tasks, progress and handoffs</small>
                      </div>
                      <ArrowRight size={15} />
                    </button>
                    <button onClick={() => navigate("memory")}>
                      <span>2</span>
                      <div>
                        <strong>See what is remembered</strong>
                        <small>Saved facts and past context</small>
                      </div>
                      <ArrowRight size={15} />
                    </button>
                    <button onClick={() => navigate("causes")}>
                      <span>3</span>
                      <div>
                        <strong>Understand changes</strong>
                        <small>Which work a correction affects</small>
                      </div>
                      <ArrowRight size={15} />
                    </button>
                  </div>
                  <details className="role-guide">
                    <summary>Meet the five specialist roles</summary>
                    {[
                      "coordinator",
                      "researcher",
                      "builder",
                      "verifier",
                      "curator",
                    ].map((role, i) => (
                      <div className="agent-row" key={role}>
                        <span className={"agent-icon " + role}>
                          <Cpu size={17} />
                        </span>
                        <div>
                          <strong>{role}</strong>
                          <small>
                            {
                              [
                                "Plans and coordinates",
                                "Finds grounded evidence",
                                "Creates and executes",
                                "Checks the actual result",
                                "Connects what was learned",
                              ][i]
                            }
                          </small>
                        </div>
                        <span
                          className={
                            "tiny-dot " +
                            (runs.some(
                              (r) => r.role === role && r.status === "running",
                            )
                              ? "live"
                              : "")
                          }
                        />
                      </div>
                    ))}
                  </details>
                </section>
              </div>
              <h2 className="overview-title">Project at a glance</h2>
              <div className="stats-grid">
                {[
                  {
                    label: "Active agents",
                    value: running,
                    icon: Users,
                    caption: "Working in parallel",
                  },
                  {
                    label: "Saved memories",
                    value: memories.length,
                    icon: BrainCircuit,
                    caption: "Context your team can use",
                  },
                  {
                    label: "Published files",
                    value: artifacts.length,
                    icon: FileText,
                    caption: "Results ready to download",
                  },
                  {
                    label: "Checked workflows",
                    value: memories.filter(
                      (m) =>
                        m.memory_type === "procedural" &&
                        m.status === "active" &&
                        m.metadata?.kind === "workflow",
                    ).length,
                    icon: Layers3,
                    caption: "Experience ready to reuse",
                  },
                ].map((s) => (
                  <div className="stat" key={s.label}>
                    <div className="row">
                      <span>{s.label}</span>
                      <s.icon size={17} />
                    </div>
                    <strong>{s.value}</strong>
                    <small>{s.caption}</small>
                  </div>
                ))}
              </div>
              <div className="section-title space-top">
                <h2>Conversation history</h2>
                <select
                  aria-label="Conversation history"
                  value={conversation}
                  onChange={(e) => setConversation(e.target.value)}
                >
                  <option value="">New conversation</option>
                  {conversations.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title}
                    </option>
                  ))}
                </select>
              </div>
              {messages.length ? (
                <div className="messages">
                  {messages.map((m) => (
                    <div key={m.id} className={"message " + m.role}>
                      <strong>
                        {m.role === "user" ? "You" : "ENGRAM ENGINE"}
                      </strong>
                      <p>{m.content}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="subtle">
                  Your conversations persist across sessions.
                </p>
              )}
              <div className="section-title space-top">
                <h2>Recent work</h2>
                <button className="text-button" onClick={() => setTab("team")}>
                  View team board
                  <ArrowRight size={14} />
                </button>
              </div>
              {runs.length ? (
                <div className="run-grid">
                  {runs.slice(0, 3).map((r) => (
                    <RunCard key={r.id} run={r} refresh={refresh} fail={fail} />
                  ))}
                </div>
              ) : (
                <Empty
                  title="The next chapter starts with an objective"
                  description="Your team's work and handoffs will appear here as they happen."
                />
              )}
            </>
          ) : null}
          {project && tab === "team" ? (
            <>
              <button
                className="text-button"
                onClick={() => navigate("agents")}
              >
                Create a custom specialist <Plus size={14} />
              </button>
              <div className="board-summary">
                <span className="status-dot" />
                {running} running <span>·</span>
                {runs.filter((r) => r.status === "completed").length} complete
                <span>·</span>
                {
                  runs.filter((r) =>
                    ["blocked", "failed", "stale"].includes(r.status),
                  ).length
                }{" "}
                need attention
              </div>
              {runs.length ? (
                <div className="run-grid">
                  {runs.map((r) => (
                    <RunCard key={r.id} run={r} refresh={refresh} fail={fail} />
                  ))}
                </div>
              ) : (
                <Empty
                  title="Your team is ready"
                  description="Start a task in the workspace to see real parallel work and handoffs."
                />
              )}
            </>
          ) : null}
          {project && tab === "workflows" ? (
            <WorkflowPanel
              key={`${me.workspace_id}:${project}:workflows`}
              project={project}
              initialGoal={objective}
              fail={fail}
            />
          ) : null}
          {project && tab === "agents" ? (
            <AgentProfilesPanel
              key={`${me.workspace_id}:${project}:agents`}
              project={project}
              fail={fail}
            />
          ) : null}
          {project && tab === "memory" ? (
            <MemoryPanel
              memories={memories}
              project={project}
              refresh={refresh}
              fail={fail}
            />
          ) : null}
          {project && tab === "artifacts" ? (
            <ArtifactPanel artifacts={artifacts} />
          ) : null}
          {project && tab === "procedures" ? (
            <>
              <CoordinationPanel
                key={`${me.workspace_id}:${project}:versions`}
                project={project}
                mode="versions"
                refresh={refresh}
                fail={fail}
              />
              <h2>Capability library</h2>
              {memories.filter((m) => m.memory_type === "procedural").length ? (
                <div className="run-grid">
                  {memories
                    .filter((m) => m.memory_type === "procedural")
                    .map((m) => (
                      <article className="memory-card" key={m.id}>
                        <div className="row">
                          <Layers3 size={18} />
                          <Badge value={m.metadata?.kind || "procedure"} />
                          <Badge value={m.status} />
                        </div>
                        <h3>
                          {m.metadata?.name ||
                            m.metadata?.tool_name ||
                            "Procedure"}
                        </h3>
                        <p>{m.metadata?.purpose || m.content}</p>
                        <JsonDetail
                          data={m.metadata}
                          label="Inspect capability and evidence"
                        />
                      </article>
                    ))}
                </div>
              ) : (
                <Empty
                  title="Capabilities grow through experience"
                  description="Tools register when a worker starts. Learned procedures require independent execution evidence."
                />
              )}
            </>
          ) : null}
          {project && tab === "graph" ? (
            <div className="graph-layout">
              <div className="graph-canvas">
                {graph.nodes.length ? (
                  <svg
                    viewBox="0 0 800 540"
                    role="img"
                    aria-label="Connected memory graph"
                  >
                    <defs>
                      <pattern
                        id="grid"
                        width="24"
                        height="24"
                        patternUnits="userSpaceOnUse"
                      >
                        <circle cx="1" cy="1" r=".7" fill="#33433b" />
                      </pattern>
                    </defs>
                    <rect width="800" height="540" fill="url(#grid)" />
                    {graph.edges.map((e: Row, i: number) => {
                      const a = graph.nodes.findIndex(
                          (n: Row) => n.id === e.source,
                        ),
                        b = graph.nodes.findIndex(
                          (n: Row) => n.id === e.target,
                        );
                      const count = Math.max(graph.nodes.length, 1);
                      return (
                        <line
                          key={i}
                          x1={400 + Math.cos((a / count) * Math.PI * 2) * 195}
                          y1={270 + Math.sin((a / count) * Math.PI * 2) * 195}
                          x2={400 + Math.cos((b / count) * Math.PI * 2) * 195}
                          y2={270 + Math.sin((b / count) * Math.PI * 2) * 195}
                          stroke={
                            e.type === "SUPERSEDES" || e.type === "REPLANS"
                              ? "#c5e6ad"
                              : e.type === "CONFLICTS_WITH"
                                ? "#d7a89a"
                                : "#476956"
                          }
                          strokeWidth={e.type === "REPLANS" ? "3" : "1.5"}
                        >
                          <title>{e.type}</title>
                        </line>
                      );
                    })}
                    {graph.nodes.map((n: Row, i: number) => (
                      <g
                        key={n.id}
                        role="button"
                        tabIndex={0}
                        aria-label={`Inspect ${n.content.slice(0, 50)}`}
                        onClick={() => setSelected(n)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") setSelected(n);
                        }}
                        transform={`translate(${400 + Math.cos((i / graph.nodes.length) * Math.PI * 2) * 195},${270 + Math.sin((i / graph.nodes.length) * Math.PI * 2) * 195})`}
                      >
                        <circle
                          r="16"
                          fill={
                            n.memory_type === "semantic"
                              ? "#a9d5a1"
                              : n.memory_type === "procedural"
                                ? "#d7bd88"
                                : "#8dafc9"
                          }
                          stroke={selected?.id === n.id ? "#fff" : "#172a20"}
                          strokeWidth="3"
                        />
                        <text
                          y="32"
                          textAnchor="middle"
                          fill="#adb9b1"
                          fontSize="10"
                        >
                          {(n.memory_type === "task"
                            ? `${n.role}: ${n.status}`
                            : n.metadata?.name || n.content
                          ).slice(0, 25)}
                        </text>
                        <title>{n.content}</title>
                      </g>
                    ))}
                  </svg>
                ) : (
                  <Empty
                    title="Connections start with evidence"
                    description="Add memory to see source links, corrections, and the paths behind decisions."
                  />
                )}
                <div className="graph-legend">
                  <span className="legend-dot semantic" />
                  Semantic
                  <span className="legend-dot episodic" />
                  Episodic
                  <span className="legend-dot procedural" />
                  Procedural
                </div>
              </div>
              <div className="graph-inspector">
                <span className="eyebrow">EVIDENCE INSPECTOR</span>
                {selected ? (
                  <>
                    <h3>{selected.memory_type} memory</h3>
                    <p>{selected.content}</p>
                    <JsonDetail data={selected} label="Full record" />
                  </>
                ) : (
                  <>
                    <Network size={30} />
                    <h3>Follow the context.</h3>
                    <p>
                      Select a node to inspect its source, version, and scope.
                    </p>
                  </>
                )}
              </div>
            </div>
          ) : null}
          {project && (tab === "causes" || tab === "conflicts") ? (
            <CoordinationPanel
              key={`${me.workspace_id}:${project}:${tab}`}
              project={project}
              mode={tab}
              refresh={refresh}
              fail={fail}
            />
          ) : null}
          {project && tab === "timeline" ? (
            <>
              {events.length ? (
                <div className="timeline">
                  {events
                    .slice()
                    .reverse()
                    .map((e) => (
                      <article key={e.id}>
                        <span className="timeline-dot" />
                        <div>
                          <div className="row">
                            <strong>{e.kind.replaceAll(".", " / ")}</strong>
                            <time>
                              {new Date(e.created_at).toLocaleTimeString()}
                            </time>
                          </div>
                          <JsonDetail
                            data={e.payload}
                            label={`Event #${e.id}${e.run_id ? " · task " + e.run_id.slice(0, 8) : ""}`}
                          />
                        </div>
                      </article>
                    ))}
                </div>
              ) : (
                <Empty
                  title="A timeline you can trust"
                  description="Actual service events appear here. There are no simulated runs."
                />
              )}
            </>
          ) : null}
          {project && tab === "sandbox" ? (
            <SandboxPanel events={events} />
          ) : null}
          {tab === "settings" ? (
            <>
              <div className="section-title">
                <h2>Service readiness</h2>
                <button className="text-button" onClick={refreshHealth}>
                  <RefreshCw size={14} />
                  Check connections
                </button>
              </div>
              <p className="subtle">
                Configured credentials are not the same as verified provider
                calls. Missing dependencies produce visible errors.
              </p>
              <div className="service-grid">
                {Object.entries<Row>(health.services || {}).map(
                  ([key, val]) => (
                    <div className="service" key={key}>
                      <Cpu size={19} />
                      <strong>{key}</strong>
                      <Badge value={val.state} />
                      {val.reason ? <small>{val.reason}</small> : null}
                    </div>
                  ),
                )}
              </div>
              <div className="section-title space-top">
                <h2>Workspace members</h2>
                {me.role === "owner" ? (
                  <button className="button" onClick={addMember}>
                    <Plus size={14} />
                    Add registered member
                  </button>
                ) : null}
              </div>
              <div className="memory-list">
                {members.map((m) => (
                  <div className="member" key={m.id}>
                    <span className="avatar">{m.name.slice(0, 1)}</span>
                    <strong>{m.name}</strong>
                    <span className="subtle">{m.email}</span>
                    <Badge value={m.role} />
                  </div>
                ))}
              </div>
              <div className="section-title space-top">
                <h2>Ingestion & write-back</h2>
              </div>
              {jobs.length ? (
                jobs.map((j) => (
                  <div className="job" key={j.id}>
                    <code>{j.id.slice(0, 8)}</code>
                    <span>{j.kind}</span>
                    <Badge value={j.status} />
                    <span className="subtle">
                      {j.error || `${j.attempts} retries`}
                    </span>
                    {j.status !== "applied" ? (
                      <button
                        className="text-button"
                        onClick={async () => {
                          try {
                            await post(`/jobs/${j.id}/retry`);
                            await refresh();
                          } catch (e) {
                            fail(e);
                          }
                        }}
                      >
                        Retry
                      </button>
                    ) : null}
                  </div>
                ))
              ) : (
                <p className="subtle">No ingestion jobs yet.</p>
              )}
              <div className="section-title space-top">
                <h2>Evaluation results</h2>
                <EvaluationButton
                  project={project}
                  refresh={refresh}
                  fail={fail}
                />
              </div>
              {evaluations.length ? (
                evaluations.map((e) => (
                  <JsonDetail key={e.id} data={e.result} label={e.name} />
                ))
              ) : (
                <p className="subtle">
                  No evaluations have run. Results appear only after real checks
                  execute.
                </p>
              )}
              <MCPPanel fail={fail} />
              <div className="security-note">
                <ShieldCheck size={22} />
                <div>
                  <strong>Explicit boundaries. Auditable actions.</strong>
                  <p>
                    Tenant-scoped memory · Restricted sandboxes · Versioned
                    handoffs · Evidence-backed verification
                  </p>
                </div>
              </div>
            </>
          ) : null}
          <footer>
            ENGRAM ENGINE
            <span>Persistent by design. Connected by FalkorDB.</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

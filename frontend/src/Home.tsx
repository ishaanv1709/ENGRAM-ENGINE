import { useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  Check,
  GitBranch,
  RotateCcw,
} from "lucide-react";
import { api, post, setWorkspace } from "./api";
import "./home.css";

export function Home() {
  const [corrected, setCorrected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [handoffStep, setHandoffStep] = useState(0);
  const handoffSteps = [
    {
      title: "Find the useful context.",
      text: "The researcher gathers sources and records what the team learned. Memory references preserve where a claim came from.",
      label: "Research",
      payload: "Sourced facts + artifact references",
    },
    {
      title: "Pass understanding, not a transcript.",
      text: "A scoped handoff carries the objective, relevant memory and artifact versions to the next specialist. The receiver acknowledges delivery.",
      label: "Handoff",
      payload: "Scoped context + durable acknowledgment",
    },
    {
      title: "Check before you reuse.",
      text: "An independent verifier runs checks in a restricted sandbox. A versioned procedure keeps the files and verification history together.",
      label: "Verify",
      payload: "Independent checks + reusable procedure",
    },
  ];

  async function openWorkspace() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      try {
        const user = await api("/me");
        setWorkspace(user.workspace_id);
      } catch {
        setWorkspace("");
        await post("/auth/start");
      }
      location.assign("/workspace#/workspace");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
      setBusy(false);
    }
  }

  return (
    <div className="engine-home">
      <a className="home-skip" href="#home-content">
        Skip to content
      </a>
      <header className="home-nav">
        <a href="/" className="home-wordmark" aria-label="ENGRAM ENGINE home">
          <img src="/assets/engram-mark.svg" alt="" width="35" height="35" />
          <span>
            ENGRAM <b>ENGINE</b>
          </span>
        </a>
        <nav aria-label="Main navigation">
          <a href="/quickstart">Quickstart</a>
          <a href="/evidence/live/" className="home-nav-evidence">
            The evidence
          </a>
          <button
            className="home-start"
            onClick={() => void openWorkspace()}
            disabled={busy}
          >
            {busy ? "Opening workspace" : "Start building"}
            <ArrowRight size={16} />
          </button>
        </nav>
      </header>

      <main id="home-content">
        {error ? (
          <div className="home-error" role="alert">
            {error} <a href="/quickstart">Read the connection guide</a>
          </div>
        ) : null}
        <section className="home-hero" aria-labelledby="home-title">
          <div className="home-hero-copy">
            <div className="home-overline">
              <span /> AN ENGINE FOR TEAMS THAT REMEMBER
            </div>
            <h1 id="home-title" aria-label="Good teams do not start from zero.">
              Good teams
              <br />
              don’t start
              <br />
              from <em>zero.</em>
            </h1>
            <p className="home-intro">
              Give AI agents a shared memory.
              <br />
              Let them build on what they know.
            </p>
            <p className="home-description">
              ENGRAM ENGINE is a team of AI agents that shares persistent graph
              memory, coordinates work, and traces how changing knowledge
              affects its decisions.
            </p>
            <a className="home-text-link" href="#memory-in-motion">
              See what a memory changes <ArrowDown size={17} />
            </a>
          </div>

          <div className={`home-instrument ${corrected ? "is-corrected" : ""}`}>
            <div className="home-instrument-top">
              <span>MEMORY INSTRUMENT / 001</span>
              <span>ILLUSTRATED MODEL</span>
            </div>
            <svg
              className="home-orbits"
              viewBox="0 0 580 510"
              role="img"
              aria-label="A shared memory core connects researcher, builder and verifier agents. A corrected owner changes only the dependent approval plan."
            >
              <defs>
                <pattern
                  id="home-dots"
                  width="18"
                  height="18"
                  patternUnits="userSpaceOnUse"
                >
                  <circle
                    cx="1"
                    cy="1"
                    r="0.7"
                    fill="currentColor"
                    opacity="0.18"
                  />
                </pattern>
              </defs>
              <rect width="580" height="510" fill="url(#home-dots)" />
              <g className="home-orbit-rings" fill="none" stroke="currentColor">
                <ellipse cx="290" cy="245" rx="178" ry="178" />
                <ellipse
                  cx="290"
                  cy="245"
                  rx="242"
                  ry="94"
                  transform="rotate(-33 290 245)"
                />
                <ellipse
                  cx="290"
                  cy="245"
                  rx="242"
                  ry="94"
                  transform="rotate(33 290 245)"
                />
              </g>
              <g
                className="home-memory-paths"
                fill="none"
                stroke="currentColor"
              >
                <path d="M290 245 L114 143 M290 245 L466 143 M290 245 L290 438" />
                <path className="home-change-path" d="M290 245 L466 350" />
              </g>
              <g className="home-travellers" fill="currentColor">
                <circle r="4">
                  <animateMotion
                    dur="5s"
                    repeatCount="indefinite"
                    path="M114 143 L290 245 L466 143"
                  />
                </circle>
                <circle r="3">
                  <animateMotion
                    dur="6s"
                    repeatCount="indefinite"
                    path="M290 438 L290 245 L114 143"
                  />
                </circle>
              </g>
              <circle className="home-core-halo" cx="290" cy="245" r="77" />
              <circle className="home-core" cx="290" cy="245" r="57" />
              <g
                className="home-core-mark"
                fill="none"
                strokeWidth="7"
                strokeLinecap="round"
              >
                <path d="M313 224a31 31 0 1 0 0 42" />
                <path d="M307 245a18 18 0 1 0-18 18h22M283 245h36" />
              </g>
              <text
                className="home-core-caption"
                x="290"
                y="331"
                textAnchor="middle"
              >
                SHARED MEMORY
              </text>
              <g className="home-agent-node">
                <circle cx="114" cy="143" r="25" />
                <text x="114" y="148" textAnchor="middle">
                  R
                </text>
                <text
                  className="home-node-label"
                  x="114"
                  y="101"
                  textAnchor="middle"
                >
                  RESEARCHER
                </text>
              </g>
              <g className="home-agent-node">
                <circle cx="466" cy="143" r="25" />
                <text x="466" y="148" textAnchor="middle">
                  B
                </text>
                <text
                  className="home-node-label"
                  x="466"
                  y="101"
                  textAnchor="middle"
                >
                  BUILDER
                </text>
              </g>
              <g className="home-agent-node">
                <circle cx="290" cy="438" r="25" />
                <text x="290" y="443" textAnchor="middle">
                  V
                </text>
                <text
                  className="home-node-label"
                  x="290"
                  y="485"
                  textAnchor="middle"
                >
                  VERIFIER
                </text>
              </g>
              <g className="home-plan-node">
                <rect x="408" y="326" width="116" height="48" rx="3" />
                <text x="466" y="346" textAnchor="middle">
                  APPROVAL PLAN
                </text>
                <text x="466" y="363" textAnchor="middle">
                  {corrected ? "REPLAN REQUIRED" : "CURRENT"}
                </text>
              </g>
            </svg>
            <div className="home-instrument-bottom">
              <span>
                <i /> Context travels. Knowledge stays.
              </span>
              <span>01 / ∞</span>
            </div>
            <div className="home-floating-note">
              <span>NOT JUST A CHAT HISTORY</span>
              <strong>A memory with relationships.</strong>
              <GitBranch size={19} />
            </div>
          </div>
          <div className="home-hero-foot">
            <span>BUILT WITH FALKORDB + DEEPAGENTS</span>
            <span>PERSISTENT BY DESIGN. CONNECTED BY CONTEXT.</span>
          </div>
        </section>

        <section
          className="home-story"
          id="memory-in-motion"
          aria-labelledby="home-story-title"
        >
          <div className="home-section-index">01 / THE DIFFERENCE</div>
          <div className="home-story-heading">
            <h2 id="home-story-title">
              One fact changes.
              <br />
              <em>The right work follows.</em>
            </h2>
            <p>
              A useful memory does more than retrieve an answer. It knows which
              decisions depend on that answer.
            </p>
          </div>
          <div className="home-correction-lab">
            <div className="home-fact">
              <span className="home-small-label">RELEASE APPROVER</span>
              <div>
                <span className={corrected ? "home-old-fact" : ""}>Maya</span>
                {corrected ? (
                  <>
                    <ArrowRight size={22} />
                    <strong>Priya</strong>
                  </>
                ) : null}
              </div>
              <p>
                {corrected
                  ? "New source supersedes the previous owner."
                  : "A sourced fact is connected to the work that uses it."}
              </p>
              <button
                className="home-correct-button"
                aria-pressed={corrected}
                onClick={() => setCorrected(!corrected)}
              >
                {corrected ? <RotateCcw size={15} /> : <GitBranch size={15} />}
                {corrected ? "Reset illustration" : "Apply a correction"}
              </button>
            </div>
            <div className="home-dependency-line" aria-hidden="true">
              <span />
              DEPENDS_ON
              <span />
            </div>
            <div className="home-impact" aria-live="polite">
              <div
                className={
                  corrected ? "home-task home-task-changed" : "home-task"
                }
              >
                <span>Approval plan</span>
                <strong>{corrected ? "Replan with Priya" : "Uses Maya"}</strong>
                {corrected ? (
                  <GitBranch size={18} />
                ) : (
                  <span className="home-task-dot" />
                )}
              </div>
              <div className="home-task">
                <span>Calculator verification</span>
                <strong>
                  <Check size={14} /> Preserved
                </strong>
                <span className="home-task-dot" />
              </div>
              <p>
                {corrected
                  ? "Only dependent work changes. The independently checked calculator stays complete."
                  : "The graph records dependencies so a correction has a precise destination."}
              </p>
            </div>
          </div>
          <div className="home-illustration-caption">
            <span>INTERACTIVE EXPLANATION, NOT A LIVE AGENT RUN</span>
            <a href="/evidence/live/">
              Inspect the real restart and correction receipts{" "}
              <ArrowRight size={15} />
            </a>
          </div>
        </section>

        <section
          className="home-principles"
          aria-labelledby="home-principles-title"
        >
          <div className="home-section-index">02 / INSIDE THE ENGINE</div>
          <h2 id="home-principles-title">
            Separate minds.
            <br />
            <em>Connected understanding.</em>
          </h2>
          <div className="home-principle-grid">
            <article>
              <span>01</span>
              <h3>Remember the work.</h3>
              <p>
                Episodes preserve what happened. Semantic memory keeps sourced
                facts. Verified procedures retain how to do it again.
              </p>
              <a href="/quickstart#features">
                Explore the memory system <ArrowRight size={15} />
              </a>
            </article>
            <article>
              <span>02</span>
              <h3>Work as a team.</h3>
              <p>
                Specialists work in parallel and hand off scoped context.
                Durable state keeps the work continuous across a restart.
              </p>
              <a href="/quickstart">
                Meet your workspace <ArrowRight size={15} />
              </a>
            </article>
            <article>
              <span>03</span>
              <h3>Keep the receipts.</h3>
              <p>
                Follow sources, artifact versions, independent checks and
                sandbox execution. Inspect what a result actually proves.
              </p>
              <a href="/evidence/live/">
                Read the measured evidence <ArrowRight size={15} />
              </a>
            </article>
          </div>
        </section>

        <section className="home-team" aria-labelledby="home-team-title">
          <div className="home-section-index">03 / A TEAM, NOT A SOLO CHAT</div>
          <div className="home-team-heading">
            <h2 id="home-team-title">
              Different specialists.
              <br />
              <em>One continuous thread.</em>
            </h2>
            <p>
              Work can split across agents without scattering its context.
              Follow a handoff through the engine.
            </p>
          </div>
          <div className="home-team-lab">
            <div className="home-team-explanation">
              <div className="home-step-buttons" aria-label="Explore a handoff">
                {handoffSteps.map((step, index) => (
                  <button
                    key={step.label}
                    aria-pressed={handoffStep === index}
                    onClick={() => setHandoffStep(index)}
                  >
                    <span>0{index + 1}</span>
                    {step.label}
                  </button>
                ))}
              </div>
              <div aria-live="polite">
                <h3>{handoffSteps[handoffStep].title}</h3>
                <p>{handoffSteps[handoffStep].text}</p>
              </div>
              <span className="home-small-label">ILLUSTRATED WORKFLOW</span>
            </div>
            <div
              className={`home-handoff-diagram home-handoff-stage-${handoffStep}`}
            >
              <div className="home-handoff-rail" aria-hidden="true">
                <i />
                <i />
                <i />
              </div>
              <div className="home-specialist">
                <span>01</span>
                <strong>Researcher</strong>
                <small>Sources & facts</small>
              </div>
              <div className="home-handoff-packet">
                <GitBranch size={18} />
                <span>{handoffSteps[handoffStep].payload}</span>
                <ArrowRight size={18} />
              </div>
              <div className="home-specialist">
                <span>02</span>
                <strong>Verifier</strong>
                <small>Checks & evidence</small>
              </div>
              <div className="home-handoff-ledger">
                <Check size={14} /> Context scoped. State persisted. Provenance
                attached.
              </div>
            </div>
          </div>
        </section>

        <section className="home-proof" aria-labelledby="home-proof-title">
          <div className="home-section-index">04 / MEASURE THE WORK</div>
          <h2 id="home-proof-title">
            Less repetition.
            <br />
            <em>More evidence.</em>
          </h2>
          <div className="home-proof-grid">
            <div>
              <strong>5</strong>
              <span>agents completed a real team workflow</span>
            </div>
            <div>
              <strong>
                50<span>%</span>
              </strong>
              <span>fewer model calls in the reuse comparison</span>
            </div>
            <div>
              <strong>
                20.5<span>%</span>
              </strong>
              <span>fewer tokens, using the median paired savings</span>
            </div>
            <div>
              <strong>1 → 7</strong>
              <span>
                one correction committed, seven conflicting writes rejected
              </span>
            </div>
          </div>
          <p>
            The reuse comparison contains four matched Groq 20B pairs with
            identical artifacts and ten real checks per session. Three timing
            pairs were faster and one was slower. The five-agent workflow used
            Groq 120B and continued through a real API and worker restart. These
            are specific measured runs, not general performance guarantees.
          </p>
          <a href="/evidence/live/">
            Read the trials, receipts and limitations <ArrowRight size={16} />
          </a>
        </section>

        <section className="home-closing">
          <div className="home-section-index">
            05 / BEGIN WITH ONE GOOD QUESTION
          </div>
          <h2>
            Your next idea.
            <br />
            <em>A team that remembers.</em>
          </h2>
          <p>
            Bring your own model key. Give the team a goal.
            <br />
            Follow the work from context to checked result.
          </p>
          <button
            className="home-open-engine"
            disabled={busy}
            onClick={() => void openWorkspace()}
          >
            {busy ? "Opening workspace" : "Open the engine"}
            <ArrowRight size={17} />
          </button>
          <div>
            <a href="/quickstart">
              Read the beginner’s guide <ArrowRight size={17} />
            </a>
            <a href="https://github.com/ishaanv1709/ENGRAM-ENGINE">
              Explore the source <ArrowRight size={17} />
            </a>
          </div>
        </section>
      </main>
      <footer className="home-footer">
        <a href="/">ENGRAM ENGINE</a>
        <a href="/blog/medium/">
          The project story
        </a>
        <span>Memory is part of the work.</span>
        <a href="/evidence/live/">
          Evidence & methodology <ArrowRight size={14} />
        </a>
      </footer>
    </div>
  );
}

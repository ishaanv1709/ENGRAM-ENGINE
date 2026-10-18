type Lesson = {
  id: string;
  label: string;
  title: string;
  intro: string;
  steps: [string, string, string][];
};

const lessons: Lesson[] = [
  {
    id: "before-you-start",
    label: "01 / PREPARATION",
    title: "Before you click Start",
    intro:
      "You do not need to understand graph databases or write code to navigate ENGRAM ENGINE. Begin with a small task and check the evidence it produces.",
    steps: [
      [
        "Know which credentials you need",
        "Select Start building to create a browser workspace without login or sign-up. Your browser session keeps it private. Add your own AI provider API key and exact model ID in Profile & settings. Optional live web research needs your own search key too.",
        "You know which browser workspace and provider connection you are using.",
      ],
      [
        "Check service readiness",
        "Use Go to page to open System & access. PostgreSQL stores history and task state, FalkorDB stores connected memory, Qdrant supports retrieval, embeddings turn text into vectors, the worker executes tasks, and the sandbox runs code.",
        "All required infrastructure services show ready. A configured model key still needs quota and a successful live call.",
      ],
      [
        "Understand what can consume quota",
        "Reading this guide and saving a workflow draft do not start inference. Starting a task does. Saving memory, processing uploaded documents and some retrieval or verification actions can also use configured providers.",
        "You know whether your host's providers are usable before submitting work.",
      ],
      [
        "Choose a bounded result",
        "Ask for one concrete deliverable with explicit checks. For example: compare two supplied documents, produce a cited decision note, or repair one behavior in a small Python repository. Begin with a task you can review yourself.",
        "Your goal states the input, desired output, constraints and how to judge success.",
      ],
      [
        "Choose what to share",
        "Team-visible context can be used by other authorized project members. Only me memory is private to your user. Shared-only task context excludes private knowledge from normal memory reads. Do not upload credentials or documents you are not allowed to share.",
        "The selected visibility matches the intended audience.",
      ],
    ],
  },
  {
    id: "account-setup",
    label: "02 / WORKSPACE AND PROFILE",
    title: "Create your first workspace and project",
    intro:
      "A workspace is your team's boundary. A project is the collection of work and knowledge for one purpose.",
    steps: [
      [
        "Select Start building",
        "Open the application home page and select Start building. There is no email, password, login or sign-up form. A private browser session, a workspace and My first project are created for you.",
        "The sidebar and workspace selector appear with your first project.",
      ],
      [
        "Connect your own model",
        "Open Profile & settings. Choose Groq, Grok, Anthropic, Gemini, OpenAI, DeepSeek, OpenCode or another supported provider. Copy its exact model ID, match its API protocol, paste your own API key and Save connection. Select it for agents, memory and admission.",
        "The connection is active and not tested. No host API key is inherited.",
      ],
      [
        "Test explicitly",
        "Test connection sends a small real inference request and checks an exact tool-call argument. This can consume provider quota or credit. Saving alone does not invoke inference. A passed connection check does not verify an entire autonomous workflow.",
        "The real check either passes or reports an error without selecting a substitute.",
      ],
      [
        "Create a project",
        "Select Create your first project when prompted, or use the plus button next to the project selector at the top. Give it a recognizable name such as Python onboarding or Release planning.",
        "The new project appears in the Project selector.",
      ],
      [
        "Confirm your location",
        "Check both the Workspace selector and Project selector before adding context or starting work. Changing a selector changes the data being viewed. An empty project is normal and is not a failed deployment.",
        "You see the intended project and its initially empty memory and task lists.",
      ],
      [
        "Learn the navigation",
        "Work contains Workspace, Workflows, Agent team and Artifacts. Memory contains Memory, Causal timeline and Procedures. Inspect & manage contains Custom agents and the technical views. Go to page reaches every destination directly.",
        "You can open a page and return to Quickstart without guessing where it lives.",
      ],
      [
        "Return in the same browser",
        "Reopen the site in the same browser profile to use its saved session. Conversations, knowledge and files persist on the deployment. Clearing site cookies or switching devices loses access to this browser workspace. Keep site data if you need to return.",
        "You find your previous workspace and selected connection.",
      ],
    ],
  },
  {
    id: "first-goal",
    label: "03 / YOUR FIRST TASK",
    title: "Submit a small goal and follow its progress",
    intro:
      "Use Workspace for one objective. Use Workflows when you need to control several milestones explicitly.",
    steps: [
      [
        "Prepare a small source",
        "If needed, use Upload document to supply a UTF-8 text/source file or a PDF with extractable text. Document uploads are limited to 10 MB and 200,000 extracted characters. Scanned PDFs may have no readable text; OCR is not supplied here.",
        "The file is retained and its ingestion job is visible. Uploaded does not automatically mean ingestion completed.",
      ],
      [
        "Write the objective",
        "In Workspace, fill Team objective with the source to use, the specific result you want and the evidence you expect. Avoid a goal such as do everything. A request to summarize uploaded notes should specify the intended audience and output length.",
        "Your goal is understandable without referring to an unshared document or an earlier unrelated chat.",
      ],
      [
        "Set memory scope",
        "Expand Memory settings when needed. Select Shared memory only when the team should use shared project context. If you continue a conversation, inspect the conversation selector so the task is attached to the intended history.",
        "The selected conversation and memory scope are intentional.",
      ],
      [
        "Start deliberately",
        "Submit the objective using the task form. This schedules a real coordinator using your active personal provider connection and may consume that provider's credit or quota. Do not repeatedly submit the same objective while waiting.",
        "A durable task record appears. Queued means waiting for a worker, not completed work.",
      ],
      [
        "Watch the team",
        "Open Agent team. The coordinator can delegate research, implementation, verification or curation. Open individual task details to inspect child tasks, handoffs, errors and persisted results. Refreshing the page does not create another task.",
        "You can identify who is working and whether a task is queued, running, waiting or blocked.",
      ],
      [
        "Review the result",
        "Read the task's summary, cited sources and limitations. Open Artifacts for published outputs. For code, inspect actual Sandbox console check receipts. A plausible summary is not a substitute for an existing file or a passing test receipt.",
        "The requested deliverable exists and the supporting evidence matches the claim.",
      ],
    ],
  },
  {
    id: "workflow-walkthrough",
    label: "04 / GUIDED CODING WORKFLOW",
    title: "From a source ZIP to independently checked changes",
    intro:
      "This walkthrough uses the downloadable beginner project below. It contains a deliberately incorrect capacity calculation and two real pytest cases. The guide does not claim the agent has repaired it until actual execution succeeds.",
    steps: [
      [
        "Download the learning project",
        "Download engram-beginner-python.zip below. You can inspect its readable source and tests before uploading. It needs only Python and pytest, which the current sandbox image includes. It does not require network access inside the container.",
        "You have a small source ZIP with src/capacity.py, test_capacity.py and a README.",
      ],
      [
        "Open Workflows and import the ZIP",
        "Choose Workflows, expand Plan a complex workflow if it is collapsed, and use Import source ZIP. Select the imported Source snapshot. This freezes the original text and hashes for comparison. Source import does not execute repository code.",
        "The Source snapshot selector shows the imported archive and retained file count.",
      ],
      [
        "Enter a precise goal",
        "Use the example goal below or write your own. Ask the team to investigate the calculation, preserve the supplied tests, publish changed files, create a patch and use a separate verifier. Do not request deployment for this first exercise.",
        "The goal has a small scope and an observable acceptance rule.",
      ],
      [
        "Review all five milestones",
        "Plan the work and Investigate the source can run in parallel. Implement and publish waits for both. Check independently waits for implementation. Prepare the review packet waits for verification and has an approval gate by default.",
        "Dependency keys match the work order. Grouping a milestone does not create a dependency.",
      ],
      [
        "Review roles, acceptance and budgets",
        "Expand Instructions, dependencies and specialist in each milestone. Keep the implementation acceptance as Published files and verification as Independent file checks. In Execution budgets, choose sensible parallelism, task count, depth, inference/tool attempts and a deadline. These are not a total spending cap.",
        "A small plan is saved with bounded execution and the intended human gates.",
      ],
      [
        "Save before running",
        "Select Save workflow draft. Check the saved goal, source, milestones and budgets. Saving the draft does not invoke the model. Select Start workflow only after confirming provider quota. A deadline is measured from draft creation, so do not leave an old draft indefinitely.",
        "The saved draft becomes running only when you explicitly start it.",
      ],
      [
        "Handle gates and failures",
        "Use Approve milestone only after reviewing the completed dependencies. If a step declares an event, record the requested outcome in its event field. A failed or stale step requires investigation and an explicit retry; the new generation clears its approval and event data.",
        "There is a recorded reason for each approval or retry.",
      ],
      [
        "Accept only the real result",
        "After implementation, the verifier receives published predecessor files in a separate sandbox. Inspect fresh passing tests, matching artifact versions and the resulting patch. Approve the final review milestone only when those receipts support it.",
        "You can download the actual changed files and changes.patch. If the model failed or quota ran out, the workflow is blocked rather than presented as a success.",
      ],
    ],
  },
  {
    id: "specialist-walkthrough",
    label: "05 / CUSTOM AGENTS",
    title: "Create a specialist with a clear responsibility",
    intro:
      "A custom agent is a saved specialist configuration used by the existing agent runtime. Naming an agent does not give it new capabilities automatically.",
    steps: [
      [
        "Open Custom agents",
        "Use Go to page, or open Inspect & manage and select Custom agents. A shortcut is also available from Agent team.",
        "You see Create a specialist and its configuration fields.",
      ],
      [
        "Choose a focused role",
        "For a first specialist, use the name Source evidence reviewer and the researcher base role. Give it instructions to identify relevant source files, cite the actual evidence and state uncertainty. Researchers do not become builders just because the instructions ask them to execute code.",
        "The specialist's responsibility fits its base role.",
      ],
      [
        "Review Allowed tools",
        "Keep only tools the specialist needs. A source reviewer commonly needs repository_list, repository_read and team_status; memory_search and memory_read add relevant context. Builder and verifier roles need execution and artifact tools for their own contracts.",
        "The tool list narrows the base role. It does not override server authorization.",
      ],
      [
        "Create the specialist",
        "Select Create specialist. Its saved card shows the role, instructions and permissions. Built-in tools can be selected here; custom profiles do not currently select remote MCP capabilities.",
        "The profile appears in this user's project.",
      ],
      [
        "Assign it to a draft",
        "In a new workflow's matching researcher milestone, expand Instructions, dependencies and specialist. Select Source evidence reviewer under Custom specialist, then save the draft. The workflow stores its own profile snapshot.",
        "The saved milestone identifies the chosen specialist. Later profile changes do not silently rewrite that plan.",
      ],
    ],
  },
  {
    id: "memory-walkthrough",
    label: "06 / MEMORY AND CORRECTIONS",
    title: "Save a fact and understand what changes when it is corrected",
    intro:
      "Use a factual observation you can justify. The admission model helps classify input, while application permissions govern who can read or change it.",
    steps: [
      [
        "Add one grounded observation",
        "Open Memory. In Add something to remember, enter a useful fact with its context, such as The release checklist names Maya as the approval owner as of the supplied planning note. Select Shared with team or Only me, then Save memory.",
        "The input is submitted for the real memory pipeline. Model or quota errors remain visible.",
      ],
      [
        "Inspect type and status",
        "Use All memories, Past activity, Facts or Ways of working to filter the view. Pending, quarantined, archived, proposed and active represent different lifecycle states. A saved observation is not automatically an admitted active fact.",
        "You distinguish the retained original observation from extracted knowledge.",
      ],
      [
        "Retrieve the fact in context",
        "Search with a relevant question or start a task that uses the fact after the provider is ready. Retrieval follows visibility and connected evidence. A fact cannot affect an older task that never read or depended on it.",
        "The task's evidence identifies which memory it actually used.",
      ],
      [
        "Correct the observation",
        "On an active memory, choose Correct memory and enter the revised fact. For example, a newer source names Priya as the owner. Explain the source and effective time. The correction uses the existing revision to reject conflicting stale edits.",
        "The older fact is preserved as superseded and the corrected knowledge is recorded.",
      ],
      [
        "Inspect affected work",
        "Open Causal timeline. Expand graph evidence to see the supersession edge, direct readers and task dependencies. Dependent work may become stale; unrelated work should not be assumed affected.",
        "You can point to the graph relationship that changed the task's status.",
      ],
      [
        "Review the next plan",
        "Inspect the revised plan and its status. A replan record is not proof that the revised work ran. If a workflow is blocked by stale knowledge, inspect the relevant milestone and explicitly retry with the necessary approvals.",
        "You distinguish a proposed or blocked plan from an executed result.",
      ],
    ],
  },
  {
    id: "verify-results",
    label: "07 / REVIEW AND REUSE",
    title: "Check artifacts, tests and procedure versions",
    intro:
      "Treat the result as a chain of evidence: a particular file version, a particular execution, and a conclusion limited to those checks.",
    steps: [
      [
        "Find the producer",
        "Open Artifacts and identify the task that produced the file. Expand File details for its hash and metadata. Download the actual file rather than copying a summary that says a file was created.",
        "A downloadable artifact exists with a recorded SHA-256 and producing task.",
      ],
      [
        "Inspect the executed command",
        "Open Sandbox console and review the real command, exit status and output. The currently recognized test evidence is pytest or unittest with actual passing tests. Printing the words tests passed is not accepted as a test receipt.",
        "The check refers to an executed command with passing test output.",
      ],
      [
        "Check freshness and independence",
        "Make sure tests ran after the latest preparation or edits. For independent workflow acceptance, inspect the verifier run and the incoming file versions. A changed file after the test needs fresh checks; the verifier also checks its current bytes against the handed-off hashes.",
        "Evidence describes the exact files being delivered, not an earlier version.",
      ],
      [
        "Understand a procedure",
        "Open Procedures to inspect a reusable way of working. Expand the version details for the artifact manifest, preconditions and verification history. A proposal is not active until a separate verifier meets the activation rules.",
        "You know which procedure version and inputs are authorized for reuse.",
      ],
      [
        "Interpret reuse measurements honestly",
        "Expand reuse history or measurements to compare observed calls, tokens and elapsed time against the stated baseline. A baseline using known artifacts without inference cannot establish tokens saved by an autonomous model. Mixed timings do not prove a reliable speedup.",
        "Any claimed saving is supported by actual comparable measurements.",
      ],
    ],
  },
  {
    id: "collaboration-guide",
    label: "08 / TEAMWORK AND INTEGRATIONS",
    title: "Share work without confusing permissions and approvals",
    intro:
      "People, agents and external services have different responsibilities. Keep the audience and the effect of each action explicit.",
    steps: [
      [
        "Keep visitor workspaces separate",
        "Each new browser session starts in its own workspace. This is not an open shared guest account. System & access retains membership administration for existing registered workspace members; the beginner flow does not require registration or automatically invite people.",
        "Another visitor cannot read your project or provider connections.",
      ],
      [
        "Follow agent handoffs",
        "Open Agent team and Run timeline to inspect delegation and handoff records. These can carry checkpoints, source evidence, published artifacts and actual check IDs. A task saying another agent checked it is not equivalent to the receiving agent's persisted result.",
        "The handoff and receiving task both exist.",
      ],
      [
        "Understand shared state",
        "Agents can share permitted project knowledge and completed outputs. User-owned workflows still have their own control scope. A shared memory does not make every user's workflow editable by every other user.",
        "Data visibility and workflow control are treated separately.",
      ],
      [
        "Configure external tools only when needed",
        "Owners can connect allowed public HTTPS MCP servers in System & access. Server-side integration credentials and allowed tool names must be configured for the real service. No GitHub push, CI run or deployment is implied by a local source patch.",
        "The intended integration is actually connected and allowed.",
      ],
      [
        "Approve a precise external effect",
        "A workflow requesting a remote tool records the exact server, tool and arguments and pauses. Inspect Exact arguments to approve, then approve the specific action or reject it. If the outcome is uncertain, inspect the remote service; the system does not blindly repeat it.",
        "A completed external action has a real retained receipt. An unknown outcome is clearly unresolved.",
      ],
    ],
  },
];

const states = [
  [
    "Draft",
    "A saved plan that has not started",
    "Review the source, milestones and budgets before starting.",
  ],
  [
    "Pending",
    "A milestone has not met its prerequisites",
    "Inspect dependencies. Do not approve unrelated work to force progress.",
  ],
  [
    "Queued",
    "A task is waiting for an available worker",
    "Check worker readiness and concurrency limits.",
  ],
  [
    "Running",
    "A worker owns the task or the workflow is active",
    "Inspect live recorded progress. An active workflow may still be waiting at a gate.",
  ],
  [
    "Waiting",
    "A task is waiting for delegated child work",
    "Inspect the children and their persisted results.",
  ],
  [
    "Awaiting approval",
    "A milestone requires a human decision",
    "Review dependencies, then approve that milestone if appropriate.",
  ],
  [
    "Waiting signal",
    "A declared external event has not been recorded",
    "Record the requested event and its outcome in Workflows.",
  ],
  [
    "Completed",
    "The task or milestone met its recorded completion rules",
    "Read the result and judge the limits of its evidence.",
  ],
  [
    "Blocked or failed",
    "A dependency, provider, test or execution failed",
    "Inspect the error, fix its cause and retry explicitly when appropriate.",
  ],
  [
    "Stale",
    "A task relied on knowledge that changed",
    "Inspect the correction and the revised work before retrying.",
  ],
  [
    "Paused or cancelled",
    "Execution was deliberately stopped",
    "Resume a paused workflow when ready. Create revised work for cancelled execution.",
  ],
];

export function BeginnerGuide() {
  return (
    <div className="beginner-guide">
      <section className="quick-section beginner-intro" id="beginner-guide">
        <span className="eyebrow">THE BEGINNER HANDBOOK</span>
        <h2>Follow one walkthrough at a time.</h2>
        <p>
          Each step tells you where to click and what you should see. Expected
          results describe what to verify, not a claim that the work already
          happened. You can read everything and download the sample without
          starting an agent.
        </p>
        <nav className="beginner-contents" aria-label="Beginner walkthroughs">
          {lessons.map((l) => (
            <a href={`#${l.id}`} key={l.id}>
              {l.label.slice(0, 2)}. {l.title}
            </a>
          ))}
          <a href="#status-guide">09. Understand task statuses</a>
          <a href="#glossary">10. Plain-language glossary</a>
        </nav>
      </section>
      {lessons.map((lesson) => (
        <section
          key={lesson.id}
          id={lesson.id}
          className="quick-section beginner-lesson"
        >
          <span className="eyebrow">{lesson.label}</span>
          <h2>{lesson.title}</h2>
          <p>{lesson.intro}</p>
          {lesson.id === "workflow-walkthrough" ? (
            <div className="starter-kit">
              <h3>Your learning project</h3>
              <p>
                This is a real, intentionally failing Python exercise. It is not
                a pre-recorded successful agent run.
              </p>
              <a
                className="button"
                href="/examples/engram-beginner-python.zip"
                download
              >
                Download beginner Python project
              </a>
              <h4>Example goal to paste into Workflow goal</h4>
              <pre>
                Inspect the imported capacity calculation. Repair it so
                capacity(3, 25) is 75 and capacity(0, 25) is 0. Preserve the
                supplied tests. Run real pytest checks, publish the changed
                source and tests, generate changes.patch, and ask a separate
                verifier to check the exact files. Prepare a review packet with
                the actual check receipts. Do not push or deploy.
              </pre>
            </div>
          ) : null}
          <ol className="quick-steps beginner-steps">
            {lesson.steps.map(([title, body, check]) => (
              <li key={title}>
                <h3>{title}</h3>
                <p>{body}</p>
                <p className="expected-result">
                  <strong>What to check:</strong> {check}
                </p>
              </li>
            ))}
          </ol>
        </section>
      ))}
      <section id="status-guide" className="quick-section">
        <span className="eyebrow">09 / STATUS REFERENCE</span>
        <h2>Read the status before deciding what to do.</h2>
        <div className="guide-table-wrap">
          <table className="guide-table">
            <caption>Workflow and task statuses</caption>
            <thead>
              <tr>
                <th>Status</th>
                <th>What it means</th>
                <th>Your next step</th>
              </tr>
            </thead>
            <tbody>
              {states.map(([state, meaning, next]) => (
                <tr key={state}>
                  <th scope="row">{state}</th>
                  <td>{meaning}</td>
                  <td>{next}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section id="glossary" className="quick-section">
        <span className="eyebrow">10 / GLOSSARY</span>
        <h2>The words you will encounter.</h2>
        <dl className="quick-troubleshooting">
          {[
            [
              "Agent",
              "A model-driven worker with a role, context and permitted tools.",
            ],
            [
              "Coordinator",
              "The agent that plans and delegates work to specialists.",
            ],
            [
              "Tenant or workspace",
              "The membership boundary separating one team's application data from another's.",
            ],
            [
              "Project",
              "A workspace's collection of related tasks, files and knowledge.",
            ],
            [
              "Conversation",
              "Persisted messages and their associated task history.",
            ],
            [
              "Workflow and milestone",
              "A durable plan and an individual stage with dependencies and acceptance rules.",
            ],
            [
              "Dependency",
              "Something that must complete first, or evidence a task relies on.",
            ],
            [
              "Handoff",
              "A persisted transfer of remaining work, context and evidence to another agent.",
            ],
            [
              "Artifact",
              "An actual retained file produced or imported by the application.",
            ],
            [
              "Snapshot and manifest",
              "An immutable source version and the list of its files and checksums.",
            ],
            [
              "SHA-256",
              "A checksum used to compare exact file bytes. It does not prove those bytes are safe or correct.",
            ],
            [
              "Graph",
              "Connected nodes and relationships that support retrieval, tracing and dependency invalidation.",
            ],
            [
              "Embedding",
              "A numeric representation of text used to retrieve related content.",
            ],
            [
              "Sandbox",
              "A restricted execution container with its own run workspace.",
            ],
            [
              "Procedure",
              "A reusable instruction/tool workflow, with version and verification requirements where applicable.",
            ],
            [
              "Admission",
              "A probabilistic model-based classification of incoming memory. It is separate from authorization.",
            ],
            [
              "Lease and revision",
              "Ownership controls that reject a task's late result after ownership or relevant knowledge changed.",
            ],
            [
              "MCP",
              "A protocol for connecting external tools. An integration still needs real authorization and configuration.",
            ],
            [
              "Quota",
              "A provider's request or token allowance. Server readiness cannot remove a provider limit.",
            ],
          ].map(([term, definition]) => (
            <div key={term}>
              <dt>{term}</dt>
              <dd>{definition}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";
import { KeyRound, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { api, post, type Row } from "./api";
import { Badge } from "./components";

export function ProfilePanel({
  fail,
  changed,
}: {
  fail: (error: unknown) => void;
  changed: () => Promise<void>;
}) {
  const [data, setData] = useState<Row>({
    catalog: [],
    connections: [],
    services: [],
    name: "",
  });
  const [provider, setProvider] = useState("groq");
  const [protocol, setProtocol] = useState("chat");
  const [label, setLabel] = useState("");
  const [model, setModel] = useState("");
  const [key, setKey] = useState("");
  const [name, setName] = useState("");
  const [activate, setActivate] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [service, setService] = useState("langsearch");
  const [serviceKey, setServiceKey] = useState("");
  const load = useCallback(async () => {
    const value = await api("/profile");
    setData(value);
    setName(value.name);
  }, []);
  useEffect(() => {
    void load().catch(fail);
  }, [load, fail]);
  const selected = data.catalog.find((item: Row) => item.id === provider);
  const perform = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    setMessage("");
    try {
      await action();
      await load();
      await changed();
      setMessage(success);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="profile-panel">
      <div className="profile-intro">
        <KeyRound size={26} />
        <div>
          <h2>Bring your own key.</h2>
          <p>
            Your selected connection powers agents, memory extraction and
            admission judgments. Optional web search uses your own search key.
            No visitor inherits the host's provider keys.
          </p>
        </div>
      </div>
      <form
        className="profile-name"
        onSubmit={(e) => {
          e.preventDefault();
          void perform(
            () => post("/profile/name", { name }),
            "Profile name updated.",
          );
        }}
      >
        <label>
          Display name
          <input
            value={name}
            maxLength={80}
            required
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <button className="button" disabled={busy}>
          Save name
        </button>
      </form>
      <p className="subtle">
        This browser remembers your private workspace through a secure session.
        There is no email or password to enter. Clearing cookies or using
        another browser starts a separate workspace. Do not clear your browser's
        site data if you need to keep access.
      </p>
      {message ? (
        <p role="status" className="profile-success">
          {message}
        </p>
      ) : null}
      <div className="section-title space-top">
        <h2>Your AI connections</h2>
        <span className="subtle">Saved keys are never displayed back</span>
      </div>
      {!data.connections.length ? (
        <p className="subtle">
          Add your first key below. You can explore the site and save plans
          before connecting a model.
        </p>
      ) : null}
      <div className="run-grid">
        {data.connections.map((item: Row) => (
          <article className="memory-card" key={item.id}>
            <div className="row">
              <h3>{item.label}</h3>
              <Badge value={item.active ? "active" : "saved"} />
            </div>
            <p>
              {data.catalog.find((p: Row) => p.id === item.provider)?.name} ·{" "}
              {item.model}
            </p>
            <p className="subtle">
              {item.protocol} · {item.test_status.replaceAll("_", " ")}
            </p>
            <div className="row">
              {!item.active ? (
                <button
                  className="button"
                  disabled={busy}
                  onClick={() =>
                    void perform(
                      () => post(`/profile/connections/${item.id}/activate`),
                      "Connection selected for new operations.",
                    )
                  }
                >
                  Use this connection
                </button>
              ) : null}
              <button
                className="button"
                disabled={busy}
                onClick={() =>
                  void perform(
                    () => post(`/profile/connections/${item.id}/test`),
                    "Actual provider inference and exact tool-call check passed. This does not verify a complete agent workflow.",
                  )
                }
              >
                Test connection
              </button>
              <button
                className="text-button"
                disabled={busy}
                aria-label={`Delete ${item.label}`}
                onClick={() =>
                  void perform(
                    () =>
                      api(`/profile/connections/${item.id}`, {
                        method: "DELETE",
                      }),
                    "Saved connection deleted. Existing provider requests already in flight cannot be revoked here.",
                  )
                }
              >
                <Trash2 size={14} />
                Delete
              </button>
            </div>
            <small>
              Testing sends a small real request using this key and may consume
              provider credit.
            </small>
          </article>
        ))}
      </div>
      <details className="profile-form">
        <summary>Advanced admission model</summary>
        <p>
          By default, admission uses your selected main model. To keep a
          dedicated policy judge, save a separate personal connection, such as
          Groq Safeguard, without making it the main agent model, then select it
          here. The standard connection test checks agent tool calling, which is
          not a requirement for a policy-only model.
        </p>
        <label>
          Admission model connection
          <select
            aria-label="Admission model connection"
            value={data.policy_connection_id || ""}
            disabled={busy}
            onChange={(e) =>
              void perform(
                () =>
                  post("/profile/policy", {
                    connection_id: e.target.value || null,
                  }),
                "Admission model selection saved.",
              )
            }
          >
            <option value="">Use my selected main connection</option>
            {data.connections.map((item: Row) => (
              <option key={item.id} value={item.id}>
                {item.label} · {item.model}
              </option>
            ))}
          </select>
        </label>
      </details>
      <form
        className="profile-form"
        onSubmit={(e) => {
          e.preventDefault();
          void perform(async () => {
            await post("/profile/connections", {
              provider,
              label: label || selected?.name,
              model,
              protocol,
              api_key: key,
              activate,
            });
            setKey("");
            setLabel("");
            setModel("");
          }, "Connection saved encrypted. It has not been live-tested yet.");
        }}
      >
        <h2>Add an AI connection</h2>
        <div className="budget-grid">
          <label>
            AI provider
            <select
              aria-label="AI provider"
              value={provider}
              onChange={(e) => {
                const next = data.catalog.find(
                  (item: Row) => item.id === e.target.value,
                );
                setProvider(e.target.value);
                setProtocol(next.protocols[0]);
                setModel("");
                setKey("");
              }}
            >
              {data.catalog.map((item: Row) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            API protocol
            <select
              aria-label="API protocol"
              value={protocol}
              onChange={(e) => setProtocol(e.target.value)}
            >
              {(selected?.protocols || ["chat"]).map((value: string) => (
                <option key={value} value={value}>
                  {
                    {
                      chat: "Chat Completions",
                      responses: "Responses API",
                      anthropic: "Anthropic Messages",
                    }[value]
                  }
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Connection name
          <input
            value={label}
            maxLength={80}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="For example: My research model"
          />
        </label>
        <label>
          Exact model ID
          <input
            required
            value={model}
            maxLength={160}
            onChange={(e) => setModel(e.target.value)}
            placeholder="Copy the exact tool-capable model ID from your provider"
          />
        </label>
        <label>
          Provider API key
          <input
            type="password"
            required
            autoComplete="off"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="Paste your own API key"
          />
        </label>
        {selected ? (
          <a
            className="quick-link"
            href={selected.docs}
            target="_blank"
            rel="noreferrer"
          >
            Open {selected.name} account and model documentation
          </a>
        ) : null}
        {provider === "opencode" ? (
          <p className="subtle">
            OpenCode Console, formerly Zen, exposes different API protocols for
            different models. Match the exact model and protocol in its current
            model table. ChatGPT/Codex or Claude subscription credentials are
            not API keys.
          </p>
        ) : null}
        <label className="shared-context-option">
          <input
            type="checkbox"
            checked={activate}
            onChange={(e) => setActivate(e.target.checked)}
          />
          Use this connection for agents, memory and admission
        </label>
        <button
          className="primary"
          disabled={busy || !key.trim() || !model.trim()}
        >
          <Plus size={15} />
          Save connection
        </button>
        <p className="subtle">
          Keys are encrypted in storage and are sent server-side to the selected
          provider only when needed. The server operator controls the encryption
          secret. Free hosting does not include free provider inference. Select
          models that support tool calling; saving a key does not establish that
          it works.
        </p>
      </form>
      <details className="profile-form">
        <summary>Optional web search keys</summary>
        <p>
          Research that needs live web results requires your own LangSearch or
          Tavily key. LangSearch is capped at 1,000 reserved requests per
          database day per credential. When both are saved, LangSearch is
          selected.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void perform(async () => {
              await post(`/profile/services/${service}`, {
                api_key: serviceKey,
              });
              setServiceKey("");
            }, "Search key saved encrypted; not live-tested.");
          }}
        >
          <label>
            Search service
            <select
              value={service}
              onChange={(e) => {
                setService(e.target.value);
                setServiceKey("");
              }}
            >
              <option value="langsearch">LangSearch</option>
              <option value="tavily">Tavily</option>
            </select>
          </label>
          <label>
            Search API key
            <input
              type="password"
              autoComplete="off"
              required
              value={serviceKey}
              onChange={(e) => setServiceKey(e.target.value)}
            />
          </label>
          <button className="button" disabled={busy || !serviceKey}>
            Save search key
          </button>
        </form>
        {data.services.map((value: string) => (
          <div className="row space-top" key={value}>
            <Badge value={value} />
            <span>Key saved</span>
            <button
              className="text-button"
              disabled={busy}
              onClick={() =>
                void perform(
                  () => api(`/profile/services/${value}`, { method: "DELETE" }),
                  "Search key removed.",
                )
              }
            >
              Remove {value} key
            </button>
          </div>
        ))}
      </details>
      <div className="security-note">
        <ShieldCheck size={23} />
        <p>
          Your workspace session and permissions still isolate your data.
          Provider keys are never mounted into an agent sandbox. Updating or
          deleting a connection affects future operations; it cannot undo a
          request already sent to a provider.
        </p>
      </div>
    </section>
  );
}

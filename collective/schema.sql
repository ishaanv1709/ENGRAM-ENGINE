CREATE TABLE IF NOT EXISTS users (
 id text PRIMARY KEY, email text UNIQUE NOT NULL, name text NOT NULL,
 password_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS tenants (id text PRIMARY KEY, name text NOT NULL, created_at timestamptz DEFAULT now());
ALTER TABLE users ADD COLUMN IF NOT EXISTS browser_workspace boolean NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS provider_connections (
 id text PRIMARY KEY, user_id text NOT NULL REFERENCES users(id), tenant_id text NOT NULL,
 provider text NOT NULL, label text NOT NULL, model text NOT NULL, protocol text NOT NULL,
 encrypted_key text NOT NULL, active boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 tested_at timestamptz, test_status text NOT NULL DEFAULT 'not_tested'
);
CREATE UNIQUE INDEX IF NOT EXISTS provider_one_active ON provider_connections(user_id,tenant_id) WHERE active;
CREATE TABLE IF NOT EXISTS user_policy_connections (
 user_id text NOT NULL REFERENCES users(id),tenant_id text NOT NULL,
 connection_id text REFERENCES provider_connections(id) ON DELETE SET NULL,
 PRIMARY KEY(user_id,tenant_id)
);
CREATE TABLE IF NOT EXISTS user_service_keys (
 user_id text NOT NULL REFERENCES users(id),tenant_id text NOT NULL,service text NOT NULL,
 encrypted_key text NOT NULL,updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(user_id,tenant_id,service)
);
CREATE TABLE IF NOT EXISTS memberships (
 tenant_id text REFERENCES tenants(id), user_id text REFERENCES users(id),
 role text NOT NULL CHECK(role IN ('owner','member','viewer')), PRIMARY KEY(tenant_id,user_id)
);
CREATE TABLE IF NOT EXISTS auth_sessions (
 token_hash text PRIMARY KEY, user_id text REFERENCES users(id), expires_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
 id text PRIMARY KEY, tenant_id text REFERENCES tenants(id), name text NOT NULL,
 description text NOT NULL DEFAULT '', created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS conversations (
 id text PRIMARY KEY, tenant_id text NOT NULL REFERENCES tenants(id), project_id text REFERENCES projects(id),
 user_id text REFERENCES users(id), title text NOT NULL, created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS messages (
 id text PRIMARY KEY, conversation_id text REFERENCES conversations(id), tenant_id text NOT NULL,
 role text NOT NULL, content text NOT NULL, created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS runs (
 id text PRIMARY KEY, tenant_id text NOT NULL REFERENCES tenants(id), project_id text REFERENCES projects(id),
 user_id text NOT NULL REFERENCES users(id), conversation_id text REFERENCES conversations(id), parent_id text REFERENCES runs(id),
 role text NOT NULL CHECK(role IN ('coordinator','researcher','builder','verifier','curator')),
 objective text NOT NULL, status text NOT NULL DEFAULT 'queued'
 CHECK(status IN ('queued','running','waiting','completed','failed','cancelled','stale','blocked')),
 depends_on text[] NOT NULL DEFAULT '{}', result jsonb, error text, lease_owner text, lease_token text,
 lease_until timestamptz, attempt integer NOT NULL DEFAULT 0, revision integer NOT NULL DEFAULT 1,
 created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS runs_poll ON runs(status,created_at);
CREATE TABLE IF NOT EXISTS handoffs (
 id text PRIMARY KEY, tenant_id text NOT NULL, from_run text REFERENCES runs(id), to_run text REFERENCES runs(id),
 packet jsonb NOT NULL, acknowledged_at timestamptz, created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS events (
 id bigserial PRIMARY KEY, tenant_id text NOT NULL, run_id text, kind text NOT NULL,
 payload jsonb NOT NULL, created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_scope ON events(tenant_id,id);
CREATE TABLE IF NOT EXISTS artifacts (
 id text PRIMARY KEY, tenant_id text NOT NULL, project_id text, run_id text,
 name text NOT NULL, sha256 text NOT NULL, size bigint NOT NULL, path text NOT NULL,
 media_type text NOT NULL, created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS outbox (
 id text PRIMARY KEY, tenant_id text NOT NULL, kind text NOT NULL, payload jsonb NOT NULL,
 status text NOT NULL DEFAULT 'pending', attempts integer NOT NULL DEFAULT 0, error text,
 created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS evaluations (
 id text PRIMARY KEY, tenant_id text NOT NULL, name text NOT NULL, result jsonb NOT NULL,
 created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS tool_servers (
 id text PRIMARY KEY, tenant_id text NOT NULL, name text NOT NULL,
 url text NOT NULL, enabled boolean NOT NULL DEFAULT true, created_at timestamptz DEFAULT now()
);
ALTER TABLE tool_servers ADD COLUMN IF NOT EXISTS allowed_tools text[] NOT NULL DEFAULT '{}';
CREATE TABLE IF NOT EXISTS workers (
 id text PRIMARY KEY, slots integer NOT NULL, last_seen timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE runs ADD COLUMN IF NOT EXISTS visibility text NOT NULL DEFAULT 'team';
ALTER TABLE runs ADD COLUMN IF NOT EXISTS context_scope text NOT NULL DEFAULT 'auto' CHECK(context_scope IN ('auto','team'));
CREATE TABLE IF NOT EXISTS provider_usage (
 provider text NOT NULL, day date NOT NULL, requests integer NOT NULL DEFAULT 0,
 PRIMARY KEY(provider, day)
);
CREATE TABLE IF NOT EXISTS model_reservations (
 id text PRIMARY KEY, key text NOT NULL, tokens integer NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS model_reservations_window ON model_reservations(key,created_at);
CREATE TABLE IF NOT EXISTS knowledge_claims (
 id text PRIMARY KEY, tenant_id text NOT NULL, project_id text NOT NULL,
 subject text NOT NULL, predicate text NOT NULL, value text NOT NULL,
 source_id text NOT NULL, source_time timestamptz NOT NULL, agent_id text NOT NULL,
 memory_id text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS claims_subject ON knowledge_claims(tenant_id,project_id,subject,predicate);
CREATE TABLE IF NOT EXISTS claim_resolutions (
 tenant_id text NOT NULL, project_id text NOT NULL, subject text NOT NULL, predicate text NOT NULL,
 winner_id text, memory_id text, revision integer NOT NULL DEFAULT 0,
 evidence jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(tenant_id,project_id,subject,predicate)
);
CREATE TABLE IF NOT EXISTS procedure_versions (
 id text PRIMARY KEY, tenant_id text NOT NULL, project_id text NOT NULL,
 family text NOT NULL, version integer NOT NULL, proposer_run text NOT NULL,
 manifest jsonb NOT NULL, preconditions jsonb NOT NULL, baseline jsonb NOT NULL,
 status text NOT NULL DEFAULT 'proposed', verifier_run text,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,project_id,family,version)
);
CREATE TABLE IF NOT EXISTS procedure_uses (
 procedure_id text REFERENCES procedure_versions(id), run_id text REFERENCES runs(id),
 tenant_id text NOT NULL, metrics jsonb, started_at timestamptz NOT NULL DEFAULT now(),
 completed_at timestamptz, PRIMARY KEY(procedure_id,run_id)
);
CREATE TABLE IF NOT EXISTS agent_profiles (
 id text PRIMARY KEY, tenant_id text NOT NULL, project_id text NOT NULL, user_id text NOT NULL,
 name text NOT NULL, base_role text NOT NULL, instructions text NOT NULL,
 allowed_tools text[] NOT NULL, context_scope text NOT NULL DEFAULT 'team',
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS workflows (
 id text PRIMARY KEY, tenant_id text NOT NULL, project_id text NOT NULL, user_id text NOT NULL,
 goal text NOT NULL, status text NOT NULL DEFAULT 'draft', limits jsonb NOT NULL,
 context_scope text NOT NULL DEFAULT 'team', snapshot_id text,
 deadline_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS workflow_steps (
 id text PRIMARY KEY, workflow_id text NOT NULL REFERENCES workflows(id), key text NOT NULL,
 parent_key text, title text NOT NULL, role text NOT NULL, objective text NOT NULL,
 depends_on text[] NOT NULL DEFAULT '{}', profile jsonb, acceptance text NOT NULL DEFAULT 'report',
 needs_approval boolean NOT NULL DEFAULT false, approved_by text, approved_at timestamptz,
 wait_for_signal text, signal jsonb, status text NOT NULL DEFAULT 'pending', run_id text,
 generation integer NOT NULL DEFAULT 0, error text, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(workflow_id,key)
);
CREATE TABLE IF NOT EXISTS workflow_reservations (
 id text PRIMARY KEY, workflow_id text NOT NULL REFERENCES workflows(id), run_id text NOT NULL,
 kind text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS repository_snapshots (
 id text PRIMARY KEY, tenant_id text NOT NULL, project_id text NOT NULL, user_id text NOT NULL,
 name text NOT NULL, digest text NOT NULL, manifest jsonb NOT NULL,
 skipped jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE runs ADD COLUMN IF NOT EXISTS workflow_id text REFERENCES workflows(id);
ALTER TABLE runs ADD COLUMN IF NOT EXISTS workflow_step_id text REFERENCES workflow_steps(id);
ALTER TABLE workflow_steps ADD COLUMN IF NOT EXISTS position integer NOT NULL DEFAULT 0;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS agent_profile jsonb;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS depth integer NOT NULL DEFAULT 0;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS auto_curate boolean NOT NULL DEFAULT true;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS memory_refs text[];
ALTER TABLE runs DROP CONSTRAINT IF EXISTS runs_status_check;
ALTER TABLE runs ADD CONSTRAINT runs_status_check CHECK(status IN ('queued','awaiting_handoff','running','waiting','completed','failed','cancelled','stale','blocked'));
CREATE INDEX IF NOT EXISTS workflow_runs ON runs(workflow_id,workflow_step_id);
CREATE TABLE IF NOT EXISTS workflow_actions (
 id text PRIMARY KEY, workflow_id text NOT NULL REFERENCES workflows(id), run_id text NOT NULL,
 tool text NOT NULL, server_id text NOT NULL, server_url text NOT NULL, remote_name text NOT NULL,
 arguments jsonb NOT NULL, digest text NOT NULL, status text NOT NULL DEFAULT 'pending',
 result jsonb, approved_by text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(run_id,tool,digest)
);
CREATE TABLE IF NOT EXISTS mem0_history (
 namespace text NOT NULL, id text NOT NULL, memory_id text NOT NULL,
 old_memory text, new_memory text, event text NOT NULL,
 created_at text, updated_at text, is_deleted boolean NOT NULL DEFAULT false,
 actor_id text, role text, inserted_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(namespace,id)
);
CREATE INDEX IF NOT EXISTS mem0_history_lookup ON mem0_history(namespace,memory_id);

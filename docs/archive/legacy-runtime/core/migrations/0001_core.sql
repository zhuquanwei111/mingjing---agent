CREATE TABLE subjects (
    tenant text NOT NULL, subject text NOT NULL, enabled boolean NOT NULL DEFAULT true,
    administrator boolean NOT NULL DEFAULT false, PRIMARY KEY (tenant, subject)
);
CREATE TABLE credentials (
    id uuid PRIMARY KEY, tenant text NOT NULL, subject text NOT NULL,
    fingerprint text NOT NULL UNIQUE, expires_at timestamptz NOT NULL, revoked boolean NOT NULL DEFAULT false,
    FOREIGN KEY (tenant, subject) REFERENCES subjects
);
CREATE TABLE releases (
    tenant text NOT NULL, capability text NOT NULL, version integer NOT NULL CHECK (version > 0),
    state text NOT NULL CHECK (state IN ('registered','validated')),
    contract jsonb NOT NULL, fingerprint text NOT NULL,
    PRIMARY KEY (tenant, capability, version)
);
CREATE TABLE publications (
    tenant text NOT NULL, capability text NOT NULL, version integer NOT NULL, environment text NOT NULL,
    state text NOT NULL CHECK (state IN ('published','deprecated','disabled')),
    PRIMARY KEY (tenant, capability, version, environment),
    FOREIGN KEY (tenant, capability, version) REFERENCES releases
);
CREATE TABLE grants (
    tenant text NOT NULL, subject text NOT NULL, capability text NOT NULL, version integer NOT NULL,
    resource text NOT NULL, action text NOT NULL
      CHECK (action IN ('execute','read','approve','cancel','artifact','reconcile')),
    allowed boolean NOT NULL,
    PRIMARY KEY (tenant, subject, capability, version, resource, action),
    FOREIGN KEY (tenant, subject) REFERENCES subjects,
    FOREIGN KEY (tenant, capability, version) REFERENCES releases
);
CREATE TABLE tasks (
    id uuid PRIMARY KEY, tenant text NOT NULL, subject text NOT NULL, credential_id uuid NOT NULL REFERENCES credentials,
    capability text NOT NULL, version integer NOT NULL, resource text NOT NULL, environment text NOT NULL,
    operation_id uuid NOT NULL UNIQUE, request_key text NOT NULL, payload_hash text NOT NULL,
    payload jsonb NOT NULL, contract_hash text NOT NULL, kind text NOT NULL,
    state text NOT NULL CHECK (state IN ('queued','waiting','running','succeeded','denied','unknown','cancelled','failed')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(), cancel_requested boolean NOT NULL DEFAULT false,
    UNIQUE (tenant, subject, request_key), UNIQUE (tenant, id), UNIQUE (tenant, operation_id),
    FOREIGN KEY (tenant, subject) REFERENCES subjects,
    FOREIGN KEY (tenant, capability, version) REFERENCES releases
);
CREATE TABLE runs (
    id uuid PRIMARY KEY, task_id uuid NOT NULL UNIQUE REFERENCES tasks,
    workflow_id text UNIQUE, temporal_run_id text,
    engine_state text NOT NULL DEFAULT 'pending',
    started_at timestamptz, ended_at timestamptz
);
CREATE TABLE approvals (
    id uuid PRIMARY KEY, task_id uuid NOT NULL UNIQUE REFERENCES tasks, payload_hash text NOT NULL,
    expires_at timestamptz NOT NULL, decision text CHECK (decision IN ('approved','rejected')),
    approver text, credential_id uuid REFERENCES credentials, decided_at timestamptz
);
CREATE TABLE budgets (
    tenant text PRIMARY KEY, available bigint NOT NULL CHECK (available >= 0)
);
CREATE TABLE attempts (
    id uuid PRIMARY KEY, operation_id uuid NOT NULL REFERENCES tasks(operation_id),
    state text NOT NULL CHECK (state IN ('reserved','settled','released','unknown')),
    reserved bigint NOT NULL CHECK (reserved >= 0), actual bigint CHECK (actual >= 0 AND actual <= reserved),
    provider_reference text, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE receipts (
    tenant text NOT NULL, operation_id uuid NOT NULL, payload_hash text NOT NULL,
    state text NOT NULL CHECK (state IN ('dispatching','succeeded','denied','unknown','cancelled')),
    attempt_id uuid REFERENCES attempts, outcome jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (tenant, operation_id), FOREIGN KEY (tenant, operation_id) REFERENCES tasks (tenant, operation_id)
);
CREATE TABLE artifacts (
    id uuid PRIMARY KEY, tenant text NOT NULL, task_id uuid NOT NULL, version integer NOT NULL CHECK (version > 0),
    digest text NOT NULL CHECK (digest ~ '^[0-9a-f]{64}$'), media_type text NOT NULL, size integer NOT NULL CHECK (size >= 0),
    UNIQUE (task_id, version), FOREIGN KEY (tenant, task_id) REFERENCES tasks (tenant, id)
);
CREATE TABLE audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant text NOT NULL, subject text, task_id uuid, operation_id uuid, attempt_id uuid,
    event text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX audit_task ON audit (tenant, task_id, id);

CREATE TABLE example_notes (
    tenant text NOT NULL, operation_id uuid NOT NULL REFERENCES tasks(operation_id),
    resource text NOT NULL, content text NOT NULL, PRIMARY KEY (tenant, operation_id)
);
CREATE TABLE fake_provider_receipts (
    operation_id uuid PRIMARY KEY, reference text NOT NULL, charged integer NOT NULL CHECK (charged >= 0)
);

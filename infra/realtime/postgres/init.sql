CREATE TABLE IF NOT EXISTS risk_events (
    event_id BIGINT PRIMARY KEY,
    event_time BIGINT NOT NULL,
    src_account BIGINT NOT NULL,
    dst_account BIGINT NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    risk_level TEXT NOT NULL,
    decision TEXT NOT NULL,
    community_id TEXT NOT NULL,
    evidence_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_event_reasons (
    event_id BIGINT NOT NULL REFERENCES risk_events(event_id),
    reason_code TEXT NOT NULL,
    PRIMARY KEY (event_id, reason_code)
);

CREATE TABLE IF NOT EXISTS risk_event_edges (
    event_id BIGINT NOT NULL REFERENCES risk_events(event_id),
    src_account BIGINT NOT NULL,
    dst_account BIGINT NOT NULL,
    relation_type TEXT NOT NULL,
    PRIMARY KEY (event_id, src_account, dst_account, relation_type)
);

CREATE TABLE IF NOT EXISTS risk_audit_logs (
    audit_id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL REFERENCES risk_events(event_id),
    action TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_actions (
    case_id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL REFERENCES risk_events(event_id),
    status TEXT NOT NULL,
    reviewer TEXT NOT NULL DEFAULT 'system',
    note TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (event_id, status)
);

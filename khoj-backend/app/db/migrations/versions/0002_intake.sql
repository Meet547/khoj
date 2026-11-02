ALTER TABLE sessions ADD COLUMN guest_token_hash TEXT;
ALTER TABLE photos ADD COLUMN session_id UUID REFERENCES sessions(id);
ALTER TABLE reports ADD CONSTRAINT reports_session_unique UNIQUE (session_id);
CREATE TABLE intake_requests (session_id UUID REFERENCES sessions(id) ON DELETE CASCADE, key TEXT, body_hash TEXT NOT NULL, response JSONB NOT NULL, PRIMARY KEY(session_id,key));
CREATE TABLE intake_clips (session_id UUID REFERENCES sessions(id) ON DELETE CASCADE, turn_id TEXT, clip_index INTEGER, transcript TEXT NOT NULL, PRIMARY KEY(session_id,turn_id,clip_index));
CREATE TABLE intake_match_jobs (person_id UUID PRIMARY KEY REFERENCES persons(id), report_id UUID NOT NULL REFERENCES reports(id), enqueued_at TIMESTAMPTZ);
CREATE TABLE speech_segments (key TEXT PRIMARY KEY, text TEXT NOT NULL, lang TEXT NOT NULL, voice TEXT NOT NULL, model TEXT NOT NULL, speed DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS checkpoint_migrations (
    v INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
ALTER TABLE checkpoint_blobs ALTER COLUMN blob DROP not null;
SELECT 1;
CREATE INDEX IF NOT EXISTS checkpoints_thread_id_idx ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS checkpoint_blobs_thread_id_idx ON checkpoint_blobs(thread_id);
CREATE INDEX IF NOT EXISTS checkpoint_writes_thread_id_idx ON checkpoint_writes(thread_id);
ALTER TABLE checkpoint_writes ADD COLUMN IF NOT EXISTS task_path TEXT NOT NULL DEFAULT '';
INSERT INTO checkpoint_migrations(v) VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9);

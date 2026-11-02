CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SEQUENCE case_number_seq;
create table users (
  id uuid primary key default gen_random_uuid(),
  phone_hash bytea not null unique,
  phone_enc  bytea not null,
  role text not null check (role in ('citizen','volunteer','officer','admin')),
  lang text not null default 'hi',
  created_at timestamptz not null default now()
);

create table sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  kind text not null check (kind in ('missing','found','search','status')),
  lang text not null, status text not null default 'open',
  created_at timestamptz default now(), updated_at timestamptz default now()
);

create table turns (
  id bigserial primary key, session_id uuid not null references sessions(id) on delete cascade,
  idx int not null, input_mode text check (input_mode in ('voice','text')),
  transcript_original text, transcript_lang text,
  reply_text text, reply_audio_ref text,
  ungrounded jsonb default '[]',
  stt_ms int, llm_ms int, tts_ms int, models jsonb,
  created_at timestamptz default now(), unique (session_id, idx)
);

create table persons (
  id uuid primary key default gen_random_uuid(),
  origin text not null,
  kind text not null check (kind in ('missing','found','unidentified_body')),
  access_class text not null default 'restricted' check (access_class in ('public_summary','restricted','officer_only')),
  status text not null default 'open',
  name_original text, gender text,
  age_min int, age_max int, height_min int, height_max int,
  build text, complexion text, hair text,
  marks_text text, language text[], conditions text[], clothing_text text,
  state text, district text, police_station text, place_text text,
  lat double precision, lng double precision, radius_km real,
  event_at date,
  attrs jsonb not null default '{}',
  search_text tsvector,
  content_hash text, created_at timestamptz default now(), updated_at timestamptz default now()
);
create index persons_blocking on persons (kind, state, gender, event_at);
create index persons_marks_trgm on persons using gin (marks_text gin_trgm_ops);
create index persons_search on persons using gin (search_text);

create table reports (
  id uuid primary key default gen_random_uuid(),
  case_no text not null unique,
  person_id uuid not null references persons(id),
  owner_id uuid not null references users(id), session_id uuid references sessions(id),
  fir_no text, relation text, status text not null default 'active',
  consent jsonb not null, created_at timestamptz default now(), closed_at timestamptz
);

create table person_names (person_id uuid references persons(id) on delete cascade, name text, script text, phonetic text, primary key (person_id, name));
create table photos (id uuid primary key default gen_random_uuid(), person_id uuid references persons(id), r2_key text not null, vision_desc jsonb,  created_at timestamptz default now());


create table connectors (id text primary key, base_url text, enabled bool default true, rate_limit_per_min int, terms_reviewed_at date);
create table crawl_runs (id bigserial primary key, connector_id text references connectors(id), slice_key text, status text, started_at timestamptz, finished_at timestamptz, rows_seen int, rows_new int, errors jsonb);
create table raw_documents (id bigserial primary key, connector_id text references connectors(id), url text, fetched_at timestamptz default now(), content_hash text, storage_ref text);
create table source_records (id bigserial primary key, connector_id text references connectors(id), source_id text not null, raw_doc_id bigint references raw_documents(id), parsed jsonb not null, parse_version int not null, content_hash text, source_status text, first_seen timestamptz default now(), last_seen timestamptz default now(), unique (connector_id, source_id));
create table person_sources (person_id uuid references persons(id), source_record_id bigint references source_records(id), primary key (person_id, source_record_id));


create table scoring_versions (id serial primary key, weights jsonb not null, created_at timestamptz default now(), active bool default false);
create table matches (
  id uuid primary key default gen_random_uuid(),
  missing_id uuid not null references persons(id), found_id uuid not null references persons(id),
  scoring_version int references scoring_versions(id),
  score real not null, band text not null check (band in ('strong','possible','weak')),
  signals jsonb not null,
  status text not null default 'tiered' check (status in ('tiered','pending_review','approved','rejected','notified','expired')),
  created_at timestamptz default now(), updated_at timestamptz default now(), unique (missing_id, found_id)
);
create table llm_cache (pair_hash text, role text, model text, result jsonb, created_at timestamptz default now(), primary key (pair_hash, role));
create table reviews (id bigserial primary key, match_id uuid references matches(id), reviewer_id uuid references users(id), decision text check (decision in ('approve','reject','needs_info')), note text, created_at timestamptz default now());
create table alerts (id uuid primary key default gen_random_uuid(), match_id uuid references matches(id), audience text, template_id text, lang text, status text default 'queued', idempotency_key text unique, sent_at timestamptz);
create table watches (id uuid primary key default gen_random_uuid(), report_id uuid references reports(id), last_checked_at timestamptz, records_checked bigint default 0, active bool default true);
create table case_events (id bigserial primary key, report_id uuid references reports(id), at timestamptz default now(), kind text, text_key text, params jsonb);


create table audit_log (id bigserial primary key, at timestamptz default now(), actor_id uuid, actor_role text, action text, object_type text, object_id text, meta jsonb);
create table consents (id bigserial primary key, user_id uuid, purpose text, text_version text, granted bool, at timestamptz default now());
create table gazetteer_places (id bigserial primary key, name text, name_hi text, kind text, state text, district text, lat double precision, lng double precision);
create table outbox (id bigserial primary key, channel text, to_enc bytea, template_id text, params jsonb, status text default 'queued', demo bool default true, created_at timestamptz default now());

CREATE TABLE auth_sessions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 created_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL,
 revoked_at timestamptz
);
CREATE TABLE refresh_tokens (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 session_id uuid NOT NULL REFERENCES auth_sessions(id) ON DELETE CASCADE,
 token_hash bytea NOT NULL UNIQUE,
 expires_at timestamptz NOT NULL,
 consumed_at timestamptz
);
CREATE INDEX refresh_tokens_session ON refresh_tokens(session_id);
CREATE UNIQUE INDEX scoring_versions_one_active ON scoring_versions (active) WHERE active;
ALTER TABLE persons ADD CONSTRAINT persons_age_range CHECK (age_min IS NULL OR age_max IS NULL OR age_min <= age_max);
ALTER TABLE persons ADD CONSTRAINT persons_height_range CHECK (height_min IS NULL OR height_max IS NULL OR height_min <= height_max);
CREATE VIEW citizen_persons AS SELECT id, name_original, gender, age_min, age_max, marks_text, language, clothing_text, state, district, event_at, origin, status FROM persons WHERE access_class = 'public_summary' AND kind = 'missing';

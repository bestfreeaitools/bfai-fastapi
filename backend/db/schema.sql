create extension if not exists pgcrypto;

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    email varchar(320) not null unique,
    name varchar(200),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists api_keys (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    name varchar(120) not null default 'Default API key',
    key_prefix varchar(16) not null,
    key_hash varchar(64) not null unique,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    last_used_at timestamptz
);

create table if not exists api_usage (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    api_key_id uuid not null references api_keys(id) on delete cascade,
    endpoint varchar(200) not null,
    model varchar(120),
    prompt_tokens integer not null default 0,
    completion_tokens integer not null default 0,
    total_tokens integer not null default 0,
    estimated_cost numeric(12, 8) not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists idx_api_keys_user_id on api_keys(user_id);
create index if not exists idx_api_keys_key_hash on api_keys(key_hash);
create index if not exists idx_api_keys_key_prefix on api_keys(key_prefix);
create index if not exists idx_api_usage_user_id on api_usage(user_id);
create index if not exists idx_api_usage_api_key_id on api_usage(api_key_id);
create index if not exists idx_api_usage_endpoint on api_usage(endpoint);
create index if not exists idx_api_usage_created_at on api_usage(created_at);

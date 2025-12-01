-- 0001_init_documents.sql
-- Base schema for legal document ingestion, versioning, and RLS-ready access.

-- Extensions
create extension if not exists "pgcrypto";
create extension if not exists "vector";

-- Enums
do $$
begin
  if not exists (select 1 from pg_type where typname = 'document_status') then
    create type document_status as enum ('pending', 'validated', 'published', 'archived');
  end if;
  if not exists (select 1 from pg_type where typname = 'ingestion_status') then
    create type ingestion_status as enum ('pending', 'running', 'failed', 'succeeded');
  end if;
  if not exists (select 1 from pg_type where typname = 'ingestion_item_status') then
    create type ingestion_item_status as enum ('pending', 'processing', 'processed', 'failed');
  end if;
end
$$;

-- Helper functions
create or replace function public.current_app_role()
returns text
language sql
stable
as $$
  select coalesce(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', 'anon');
$$;

create or replace function public.is_curator_or_admin()
returns boolean
language sql
stable
as $$
  select current_app_role() in ('curator', 'admin');
$$;

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Tables
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  slug text not null,
  summary text,
  source_path text,
  category text,
  tags text[] not null default '{}',
  jurisdiction text,
  published_at date,
  version_label text,
  checksum text,
  size_bytes bigint,
  status document_status not null default 'pending',
  created_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists idx_documents_slug_unique on public.documents (slug);
create index if not exists idx_documents_category on public.documents (category);
create index if not exists idx_documents_published_at on public.documents (published_at);
create index if not exists gin_documents_tags on public.documents using gin (tags);

create table if not exists public.document_versions (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents (id) on delete cascade,
  version_label text not null,
  checksum text,
  storage_key text not null,
  uploaded_at timestamptz not null default now(),
  uploaded_by uuid references auth.users (id) on delete set null,
  notes text,
  constraint document_versions_document_label_unique unique (document_id, version_label)
);

create index if not exists idx_document_versions_doc on public.document_versions (document_id);
create index if not exists idx_document_versions_label on public.document_versions (version_label);

create table if not exists public.ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status ingestion_status not null default 'pending',
  started_by uuid references auth.users (id) on delete set null,
  notes text,
  total_files integer,
  succeeded integer default 0,
  failed integer default 0
);

create index if not exists idx_ingestion_runs_started_at on public.ingestion_runs (started_at);
create index if not exists idx_ingestion_runs_status on public.ingestion_runs (status);

create table if not exists public.ingestion_items (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.ingestion_runs (id) on delete cascade,
  source_path text not null,
  document_id uuid references public.documents (id) on delete set null,
  status ingestion_item_status not null default 'pending',
  error_message text,
  checksum text,
  size_bytes bigint,
  processed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_ingestion_items_run on public.ingestion_items (run_id);
create index if not exists idx_ingestion_items_status on public.ingestion_items (status);

create table if not exists public.topics (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists public.document_topics (
  document_id uuid not null references public.documents (id) on delete cascade,
  topic_id uuid not null references public.topics (id) on delete cascade,
  primary key (document_id, topic_id)
);

create index if not exists idx_document_topics_document on public.document_topics (document_id);
create index if not exists idx_document_topics_topic on public.document_topics (topic_id);

create table if not exists public.embeddings (
  id bigserial primary key,
  document_id uuid not null references public.documents (id) on delete cascade,
  chunk_id text not null,
  content text not null,
  embedding vector(1536) not null,
  metadata jsonb default '{}',
  created_at timestamptz not null default now(),
  constraint embeddings_document_chunk_unique unique (document_id, chunk_id)
);

create index if not exists idx_embeddings_document_id on public.embeddings (document_id);
create index if not exists idx_embeddings_chunk on public.embeddings (chunk_id);
-- Adjust lists based on data volume; ivfflat requires analyze after insert.
create index if not exists idx_embeddings_vector on public.embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Updated-at triggers
drop trigger if exists set_documents_updated_at on public.documents;
create trigger set_documents_updated_at before update on public.documents
for each row execute function public.touch_updated_at();

-- RLS
alter table public.documents enable row level security;
alter table public.document_versions enable row level security;
alter table public.ingestion_runs enable row level security;
alter table public.ingestion_items enable row level security;
alter table public.topics enable row level security;
alter table public.document_topics enable row level security;
alter table public.embeddings enable row level security;

-- Documents policies
create policy documents_published_read
  on public.documents
  for select
  to authenticated
  using (
    status = 'published'
    or public.is_curator_or_admin()
    or auth.uid() = created_by
  );

create policy documents_insert_curator_admin
  on public.documents
  for insert
  to authenticated
  with check (public.is_curator_or_admin() or auth.uid() = created_by);

create policy documents_update_curator_admin
  on public.documents
  for update
  to authenticated
  using (public.is_curator_or_admin() or auth.uid() = created_by)
  with check (public.is_curator_or_admin() or auth.uid() = created_by);

create policy documents_delete_admin
  on public.documents
  for delete
  to authenticated
  using (public.is_curator_or_admin());

-- Document versions policies
create policy document_versions_read
  on public.document_versions
  for select
  to authenticated
  using (
    exists (
      select 1
      from public.documents d
      where d.id = document_versions.document_id
        and (
          d.status = 'published'
          or public.is_curator_or_admin()
          or d.created_by = auth.uid()
        )
    )
  );

create policy document_versions_write
  on public.document_versions
  for all
  to authenticated
  using (
    public.is_curator_or_admin()
    or exists (
      select 1
      from public.documents d
      where d.id = document_versions.document_id
        and d.created_by = auth.uid()
    )
  )
  with check (
    public.is_curator_or_admin()
    or exists (
      select 1
      from public.documents d
      where d.id = document_versions.document_id
        and d.created_by = auth.uid()
    )
  );

-- Ingestion visibility only for curators/admins
create policy ingestion_runs_curators
  on public.ingestion_runs
  for all
  to authenticated
  using (public.is_curator_or_admin())
  with check (public.is_curator_or_admin());

create policy ingestion_items_curators
  on public.ingestion_items
  for all
  to authenticated
  using (public.is_curator_or_admin())
  with check (public.is_curator_or_admin());

-- Topics
create policy topics_read_all
  on public.topics
  for select
  to public
  using (true);

create policy topics_write_curators
  on public.topics
  for all
  to authenticated
  using (public.is_curator_or_admin())
  with check (public.is_curator_or_admin());

-- Document topics
create policy document_topics_read
  on public.document_topics
  for select
  to public
  using (
    exists (
      select 1
      from public.documents d
      where d.id = document_topics.document_id
        and (
          d.status = 'published'
          or public.is_curator_or_admin()
          or d.created_by = auth.uid()
        )
    )
  );

create policy document_topics_write
  on public.document_topics
  for all
  to authenticated
  using (
    public.is_curator_or_admin()
    or exists (
      select 1
      from public.documents d
      where d.id = document_topics.document_id
        and d.created_by = auth.uid()
    )
  )
  with check (
    public.is_curator_or_admin()
    or exists (
      select 1
      from public.documents d
      where d.id = document_topics.document_id
        and d.created_by = auth.uid()
    )
  );

-- Embeddings
create policy embeddings_read_published
  on public.embeddings
  for select
  to authenticated
  using (
    exists (
      select 1
      from public.documents d
      where d.id = embeddings.document_id
        and (
          d.status = 'published'
          or public.is_curator_or_admin()
          or d.created_by = auth.uid()
        )
    )
  );

create policy embeddings_write_curators
  on public.embeddings
  for all
  to authenticated
  using (
    public.is_curator_or_admin()
    or exists (
      select 1
      from public.documents d
      where d.id = embeddings.document_id
        and d.created_by = auth.uid()
    )
  )
  with check (
    public.is_curator_or_admin()
    or exists (
      select 1
      from public.documents d
      where d.id = embeddings.document_id
        and d.created_by = auth.uid()
    )
  );

comment on table public.documents is 'Metadados de documentos jurídicos ingeridos.';
comment on table public.document_versions is 'Versionamento lógico e armazenamento de arquivos no storage.';
comment on table public.ingestion_runs is 'Execuções de ingestão em lote.';
comment on table public.ingestion_items is 'Itens processados por execução de ingestão.';
comment on table public.topics is 'Tópicos/assuntos para categorização.';
comment on table public.document_topics is 'Relação N:N entre documentos e tópicos.';
comment on table public.embeddings is 'Chunks e vetores para RAG.';

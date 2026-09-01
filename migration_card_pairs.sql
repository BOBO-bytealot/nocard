-- 卡配对表：两张卡配对显示
create table if not exists card_pairs (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  card_a text not null references cards(id) on delete cascade,
  card_b text not null references cards(id) on delete cascade,
  label text default '配对',
  created_at timestamptz default now()
);
create index if not exists idx_card_pairs_owner on card_pairs(owner_id);
create index if not exists idx_card_pairs_card_a on card_pairs(card_a);
create index if not exists idx_card_pairs_card_b on card_pairs(card_b);

alter table card_pairs enable row level security;

-- anon 读写（小圈子公开，和现有表一致）
drop policy if exists "anon_select_card_pairs" on card_pairs;
create policy "anon_select_card_pairs" on card_pairs for select using (true);
drop policy if exists "anon_insert_card_pairs" on card_pairs;
create policy "anon_insert_card_pairs" on card_pairs for insert with check (true);
drop policy if exists "anon_update_card_pairs" on card_pairs;
create policy "anon_update_card_pairs" on card_pairs for update using (true);
drop policy if exists "anon_delete_card_pairs" on card_pairs;
create policy "anon_delete_card_pairs" on card_pairs for delete using (true);

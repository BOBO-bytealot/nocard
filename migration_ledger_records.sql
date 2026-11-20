-- SVT 追星账本 · 云端账目表
-- 用法：Supabase Dashboard → SQL Editor → 粘贴运行一次
-- 说明：账目整条存 JSONB（字段以后加不用改表），另抽几个常用字段做筛选/排序

create table if not exists ledger_records (
  id text primary key,                 -- 账目编号，如 DINO-001
  data jsonb not null,                 -- 完整账目对象（原 ledger.json 的一条 record）
  series text,                         -- 系列，便于筛选
  member text,                         -- 成员
  date date,                           -- 记账日期
  cny numeric(14,2) default 0,         -- 折合人民币（KPI 汇总用）
  type text default 'buy',             -- buy / sell 等
  status text default 'active',
  pay_status text,
  ship_status text,
  owner_id text not null default 'u1783008431210',  -- BOBO
  updated_at timestamptz default now()
);

create index if not exists idx_ledger_series on ledger_records(series);
create index if not exists idx_ledger_member on ledger_records(member);
create index if not exists idx_ledger_date on ledger_records(date);
create index if not exists idx_ledger_owner on ledger_records(owner_id);

alter table ledger_records enable row level security;

-- 和现有卡册一致：anon 可读写（账本页面另有 BOBO 身份闸门）
drop policy if exists "anon_select_ledger_records" on ledger_records;
create policy "anon_select_ledger_records" on ledger_records for select using (true);
drop policy if exists "anon_insert_ledger_records" on ledger_records;
create policy "anon_insert_ledger_records" on ledger_records for insert with check (true);
drop policy if exists "anon_update_ledger_records" on ledger_records;
create policy "anon_update_ledger_records" on ledger_records for update using (true);
drop policy if exists "anon_delete_ledger_records" on ledger_records;
create policy "anon_delete_ledger_records" on ledger_records for delete using (true);

-- 十条新 Data API 权限（2026-10-30 起新表必须显式授权，否则 anon 拿到 401）
grant select, insert, update, delete on public.ledger_records to anon;
grant select, insert, update, delete on public.ledger_records to authenticated;
grant select, insert, update, delete on public.ledger_records to service_role;

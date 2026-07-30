-- 前端用 anon key，不走 Supabase Auth，所以给 anon 角色开放 RLS 写权限
-- 执行方式：Supabase Dashboard → SQL Editor → New query → 粘贴 → Run

-- ========== cards ==========
DROP POLICY IF EXISTS anon_insert_cards ON public.cards;
DROP POLICY IF EXISTS anon_update_cards ON public.cards;
DROP POLICY IF EXISTS anon_delete_cards ON public.cards;
CREATE POLICY anon_insert_cards ON public.cards FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY anon_update_cards ON public.cards FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY anon_delete_cards ON public.cards FOR DELETE TO anon USING (true);

-- ========== records ==========
DROP POLICY IF EXISTS anon_insert_records ON public.records;
DROP POLICY IF EXISTS anon_update_records ON public.records;
DROP POLICY IF EXISTS anon_delete_records ON public.records;
CREATE POLICY anon_insert_records ON public.records FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY anon_update_records ON public.records FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY anon_delete_records ON public.records FOR DELETE TO anon USING (true);

-- ========== users ==========
DROP POLICY IF EXISTS anon_insert_users ON public.users;
DROP POLICY IF EXISTS anon_update_users ON public.users;
DROP POLICY IF EXISTS anon_delete_users ON public.users;
CREATE POLICY anon_insert_users ON public.users FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY anon_update_users ON public.users FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY anon_delete_users ON public.users FOR DELETE TO anon USING (true);

-- ========== invite_codes ==========
DROP POLICY IF EXISTS anon_insert_invite_codes ON public.invite_codes;
DROP POLICY IF EXISTS anon_update_invite_codes ON public.invite_codes;
CREATE POLICY anon_insert_invite_codes ON public.invite_codes FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY anon_update_invite_codes ON public.invite_codes FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- ========== groups ==========
DROP POLICY IF EXISTS anon_insert_groups ON public.groups;
DROP POLICY IF EXISTS anon_update_groups ON public.groups;
DROP POLICY IF EXISTS anon_delete_groups ON public.groups;
CREATE POLICY anon_insert_groups ON public.groups FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY anon_update_groups ON public.groups FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY anon_delete_groups ON public.groups FOR DELETE TO anon USING (true);

-- ========== members ==========
DROP POLICY IF EXISTS anon_insert_members ON public.members;
DROP POLICY IF EXISTS anon_update_members ON public.members;
DROP POLICY IF EXISTS anon_delete_members ON public.members;
CREATE POLICY anon_insert_members ON public.members FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY anon_update_members ON public.members FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY anon_delete_members ON public.members FOR DELETE TO anon USING (true);

-- ========== 验证：查看当前所有 RLS 策略 ==========
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE tablename IN ('cards','records','users','invite_codes','groups','members')
ORDER BY tablename, policyname;

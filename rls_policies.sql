-- RLS 策略收紧：bo 只能改 SEVENTEEN，二丁只能改 CORTIS
-- 执行方式：Supabase Dashboard → SQL Editor → New query → 粘贴 → Run

-- 先创建辅助函数：从 JWT 中提取当前用户 ID
CREATE OR REPLACE FUNCTION public.current_user_id()
RETURNS text AS $$
BEGIN
  RETURN coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    nullif(current_setting('request.jwt.claims', true)::json->>'sub', '')
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ═══════════════════════════════════════════════════════════════
-- 1. cards 表
-- ═══════════════════════════════════════════════════════════════

-- 删除旧的全开放策略
DROP POLICY IF EXISTS public_update_cards ON public.cards;
DROP POLICY IF EXISTS public_delete_cards ON public.cards;
DROP POLICY IF EXISTS public_insert_cards ON public.cards;

-- bo 只能操作 SEVENTEEN
CREATE POLICY bo_cards_seventeen ON public.cards
  FOR ALL
  TO authenticated
  USING (public.current_user_id() = 'u1783008431210' AND group_id = 'seventeen')
  WITH CHECK (public.current_user_id() = 'u1783008431210' AND group_id = 'seventeen');

-- 二丁只能操作 CORTIS
CREATE POLICY erding_cards_cortis ON public.cards
  FOR ALL
  TO authenticated
  USING (public.current_user_id() = 'u1783008431210_2' AND group_id = 'cortis')
  WITH CHECK (public.current_user_id() = 'u1783008431210_2' AND group_id = 'cortis');

-- ═══════════════════════════════════════════════════════════════
-- 2. members 表
-- ═══════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS public_update_members ON public.members;
DROP POLICY IF EXISTS public_delete_members ON public.members;
DROP POLICY IF EXISTS public_insert_members ON public.members;

CREATE POLICY bo_members_seventeen ON public.members
  FOR ALL
  TO authenticated
  USING (public.current_user_id() = 'u1783008431210' AND group_id = 'seventeen')
  WITH CHECK (public.current_user_id() = 'u1783008431210' AND group_id = 'seventeen');

CREATE POLICY erding_members_cortis ON public.members
  FOR ALL
  TO authenticated
  USING (public.current_user_id() = 'u1783008431210_2' AND group_id = 'cortis')
  WITH CHECK (public.current_user_id() = 'u1783008431210_2' AND group_id = 'cortis');

-- ═══════════════════════════════════════════════════════════════
-- 3. records 表（没有 group_id，按 user_id 锁）
-- ═══════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS public_update_records ON public.records;
DROP POLICY IF EXISTS public_delete_records ON public.records;
DROP POLICY IF EXISTS public_insert_records ON public.records;

-- bo 只能操作自己的 records
CREATE POLICY bo_records_own ON public.records
  FOR ALL
  TO authenticated
  USING (public.current_user_id() = 'u1783008431210' AND user_id = 'u1783008431210')
  WITH CHECK (public.current_user_id() = 'u1783008431210' AND user_id = 'u1783008431210');

-- 二丁只能操作自己的 records
CREATE POLICY erding_records_own ON public.records
  FOR ALL
  TO authenticated
  USING (public.current_user_id() = 'u1783008431210_2' AND user_id = 'u1783008431210_2')
  WITH CHECK (public.current_user_id() = 'u1783008431210_2' AND user_id = 'u1783008431210_2');

-- ═══════════════════════════════════════════════════════════════
-- 4. groups / invite_codes 表（只读，删除写权限策略）
-- ═══════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS public_update_groups ON public.groups;
DROP POLICY IF EXISTS public_delete_groups ON public.groups;
DROP POLICY IF EXISTS public_insert_groups ON public.groups;

DROP POLICY IF EXISTS public_update_invite_codes ON public.invite_codes;
DROP POLICY IF EXISTS public_delete_invite_codes ON public.invite_codes;
DROP POLICY IF EXISTS public_insert_invite_codes ON public.invite_codes;

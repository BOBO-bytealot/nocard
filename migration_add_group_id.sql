-- 给 users 表加 group_id 字段
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS group_id TEXT DEFAULT 'seventeen';

-- 同步现有用户
UPDATE public.users SET group_id = 'seventeen' WHERE id = 'u1783008431210';
UPDATE public.users SET group_id = 'cortis' WHERE id = 'u1783008431210_2';

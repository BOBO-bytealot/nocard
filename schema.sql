-- 小卡共享数据库表结构
-- 1. 团体表
CREATE TABLE IF NOT EXISTS groups (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. 成员表
CREATE TABLE IF NOT EXISTS members (
  id TEXT PRIMARY KEY,
  group_id TEXT REFERENCES groups(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 用户表
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('founder','member')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. 邀请码
CREATE TABLE IF NOT EXISTS invite_codes (
  code TEXT PRIMARY KEY,
  created_by TEXT REFERENCES users(id),
  used BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. 卡片图鉴表
CREATE TABLE IF NOT EXISTS cards (
  id TEXT PRIMARY KEY,
  group_id TEXT REFERENCES groups(id),
  member_id TEXT REFERENCES members(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  series TEXT DEFAULT '',
  card_type TEXT NOT NULL DEFAULT '其他',
  image_url TEXT DEFAULT '',
  image_emoji TEXT DEFAULT '',
  note TEXT DEFAULT '',
  created_by TEXT REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. 卡册记录表（个人）
CREATE TABLE IF NOT EXISTS records (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  card_id TEXT REFERENCES cards(id) ON DELETE CASCADE,
  price REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT '未发货' CHECK (status IN ('未发货','在途','已到手')),
  buy_date TEXT DEFAULT '',
  note TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_cards_group ON cards(group_id);
CREATE INDEX IF NOT EXISTS idx_cards_member ON cards(member_id);
CREATE INDEX IF NOT EXISTS idx_cards_series ON cards(series);
CREATE INDEX IF NOT EXISTS idx_records_user ON records(user_id);
CREATE INDEX IF NOT EXISTS idx_records_card ON records(card_id);

-- 插入预设团体
INSERT INTO groups (id, name, sort_order) VALUES
  ('seventeen', 'SEVENTEEN', 1),
  ('cortis', 'CORTIS', 2)
ON CONFLICT (id) DO NOTHING;

-- 插入 SEVENTEEN 成员（应援顺序）
INSERT INTO members (id, group_id, name, sort_order) VALUES
  ('svt_scoups', 'seventeen', '崔胜哲(S.COUPS)', 1),
  ('svt_jeonghan', 'seventeen', '尹净汉', 2),
  ('svt_joshua', 'seventeen', '洪知秀(Joshua)', 3),
  ('svt_jun', 'seventeen', '文俊辉(Jun)', 4),
  ('svt_hoshi', 'seventeen', '权顺荣(Hoshi)', 5),
  ('svt_wonwoo', 'seventeen', '全圆佑', 6),
  ('svt_woozi', 'seventeen', '李知勋(Woozi)', 7),
  ('svt_the8', 'seventeen', '徐明浩(The8)', 8),
  ('svt_mingyu', 'seventeen', '金珉奎', 9),
  ('svt_dk', 'seventeen', '李硕珉(DK)', 10),
  ('svt_seungkwan', 'seventeen', '夫胜宽', 11),
  ('svt_vernon', 'seventeen', '崔韩率(Vernon)', 12),
  ('svt_dino', 'seventeen', '李灿(Dino)', 13)
ON CONFLICT (id) DO NOTHING;

-- 插入 CORTIS 成员（年龄顺序）
INSERT INTO members (id, group_id, name, sort_order) VALUES
  ('ct_zhaoyufan', 'cortis', '赵雨凡', 1),
  ('ct_jinzhuxun', 'cortis', '金主训', 2),
  ('ct_mading', 'cortis', '马丁', 3),
  ('ct_yanchengxuan', 'cortis', '严成玹', 4),
  ('ct_anqianhao', 'cortis', '安乾镐', 5)
ON CONFLICT (id) DO NOTHING;

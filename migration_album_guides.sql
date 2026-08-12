CREATE TABLE IF NOT EXISTS public.album_guides (
  id TEXT PRIMARY KEY,
  series TEXT NOT NULL,
  name TEXT NOT NULL,
  label TEXT DEFAULT '其他',
  image_url TEXT NOT NULL,
  created_by TEXT REFERENCES public.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_album_guides_series ON public.album_guides(series);

-- RLS for anon since the app uses the publishable/anon key
ALTER TABLE public.album_guides ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS anon_select_album_guides ON public.album_guides;
DROP POLICY IF EXISTS anon_insert_album_guides ON public.album_guides;
DROP POLICY IF EXISTS anon_delete_album_guides ON public.album_guides;

CREATE POLICY anon_select_album_guides ON public.album_guides FOR SELECT TO anon USING (true);
CREATE POLICY anon_insert_album_guides ON public.album_guides FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY anon_delete_album_guides ON public.album_guides FOR DELETE TO anon USING (true);

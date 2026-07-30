import os
import requests

SUPABASE_URL = "https://neolxiocucigqrrgueim.supabase.co"
SUPABASE_KEY = "sb_publishable_WW39PvhU8H0FgEdCJk5YRg_eXN7oLIC"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# 获取所有卡片
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/cards?select=id,name,group_id,member_id,image_url,card_type&order=id.desc",
    headers=headers
)
cards = resp.json()

print(f"总共 {len(cards)} 张卡\n")
print("=== 缺卡面（image_url 为 null 或空）===")
for c in cards:
    img = c.get('image_url')
    if not img or img == '':
        member = c.get('member_id', '团卡')
        print(f"  {c['id']}: {c['name']} | {c['group_id']} | member={member} | type={c.get('card_type','')}")

print(f"\n=== 有卡面的卡 ===")
for c in cards:
    img = c.get('image_url')
    if img and img != '':
        member = c.get('member_id', '团卡')
        has_img = "有图" if img and len(img) > 100 else "无图"
        print(f"  {c['id']}: {c['name']} | {c['group_id']} | member={member} | {has_img}")

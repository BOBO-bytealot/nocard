#!/usr/bin/env python3
"""
批量录入记录（无卡面，纯文字）
用法：python3 import_records.py --dry-run 先检查，去掉 --dry-run 正式写入
"""

import json
import time
import urllib.request
import urllib.error

SUPABASE_URL = "https://neolxiocucigqrrgueim.supabase.co"
SUPABASE_KEY = "sb_publishable_WW39PvhU8H0FgEdCJk5YRg_eXN7oLIC"

def fetch_supabase(path, method="GET", data=None):
    url = f"{SUPABASE_URL}{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    req = urllib.request.Request(url, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req.data = body
        req.add_header("Content-Length", str(len(body)))
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

# 二丁的12张可出卡
# 格式：(卡名, 成员编号, 价格)
# 1=赵雨凡 2=金主训 3=马丁 4=严成玹 5=安乾镐
RAW_CARDS = [
    ("yzy中背", 3, 65),
    ("stb", 1, 30),
    ("油管4.0", 5, 29),
    ("环球预售", 1, 35),
    ("环球预售", 3, 35),
    ("aaa", 5, 50),
    ("yzy签售4.0", 5, 43),
    ("yzy520卡背", 1, 63),
    ("yzy5.0", 4, 61),
    ("yes24", 5, 22),
    ("颂钵", 1, 21),
    ("颂钵", 5, 21),
]

MEMBER_MAP = {
    1: ("ct_zhaoyufan", "赵雨凡"),
    2: ("ct_jinzhuxun", "金主训"),
    3: ("ct_mading", "马丁"),
    4: ("ct_yanchengxuan", "严成玹"),
    5: ("ct_anqianhao", "安乾镐"),
}

USER_ID = "u1783008431210_2"  # 二丁
GROUP_ID = "cortis"

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # 先拉现有 cards
    code, body = fetch_supabase(f"/rest/v1/cards?group_id=eq.{GROUP_ID}&select=id,name,member_id,series,card_type")
    existing = json.loads(body) if code == 200 else []
    existing_by_name = {}
    for c in existing:
        key = (c.get("name", ""), c.get("member_id"))
        existing_by_name[key] = c

    # 先创建缺失的 cards，再创建 records
    ts = int(time.time() * 1000)
    new_cards = []
    records = []

    for name, num, price in RAW_CARDS:
        mid, mname = MEMBER_MAP[num]
        card_name = f"{mname} {name}"
        key = (card_name, mid)

        card = existing_by_name.get(key)
        if not card:
            # 新建 card
            cid = f"c_{name.replace(' ', '').replace('.', '')}_{mid.split('_')[-1]}_{ts}"
            card = {
                "id": cid,
                "group_id": GROUP_ID,
                "member_id": mid,
                "name": card_name,
                "series": name,
                "card_type": "特典卡",
                "image_url": None,
                "image_emoji": "",
            }
            new_cards.append(card)
            existing_by_name[key] = card
            print(f"[NEW CARD] {card_name} -> {cid}")
        else:
            print(f"[EXISTING] {card_name} -> {card['id']}")

        # 创建 record（可出状态）
        rid = f"r_{card['id']}_{USER_ID}_{ts}"
        records.append({
            "id": rid,
            "card_id": card["id"],
            "user_id": USER_ID,
            "price": price,
            "status": "已到手",
            "buy_date": None,
            "note": "",
        })
        print(f"  [RECORD] 价格{price} 状态:可出")

    print(f"\n共 {len(new_cards)} 张新卡, {len(records)} 条记录")

    if args.dry_run:
        print("\n--dry-run 模式，跳过写入")
        return

    # 写入 cards
    if new_cards:
        code, body = fetch_supabase("/rest/v1/cards", method="POST", data=new_cards)
        if code in (200, 201):
            print(f"✅ 已写入 {len(new_cards)} 张新卡")
        else:
            print(f"❌ 写卡失败: HTTP {code}")
            print(body[:500])
            return

    # 写入 records
    code, body = fetch_supabase("/rest/v1/records", method="POST", data=records)
    if code in (200, 201):
        print(f"✅ 已写入 {len(records)} 条记录")
    else:
        print(f"❌ 写记录失败: HTTP {code}")
        print(body[:500])

if __name__ == "__main__":
    main()

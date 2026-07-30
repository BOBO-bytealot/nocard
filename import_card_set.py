#!/usr/bin/env python3
"""
批量导入卡册 - 基于坐标裁剪版

两种模式：
1. --positions positions.json   基于人物坐标文件裁剪
2. --rows 2 --cols 3            基于固定网格裁剪（备用）

positions.json 格式：
[
  {"name": "赵雨凡", "x": 0.1, "y": 0.05, "width": 0.3, "height": 0.45},
  {"name": "金主训", "x": 0.4, "y": 0.05, "width": 0.3, "height": 0.45}
]
x/y/width/height 是相对于原图的比例 (0.0 ~ 1.0)

用法：
  python3 import_card_set.py \
    --image photo.jpg \
    --group cortis \
    --series "骰子版专卡" \
    --type "固卡" \
    --positions positions.json \
    --group-card full
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from PIL import Image

SUPABASE_URL = "https://neolxiocucigqrrgueim.supabase.co"
SUPABASE_KEY = "sb_publishable_WW39PvhU8H0FgEdCJk5YRg_eXN7oLIC"

OUTPUT_W = 409
OUTPUT_H = 604


def slugify(s):
    return re.sub(r'[^\w\u4e00-\u9fa5]', '', s)


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


def compress_image_to_chars(img, max_chars=80000, quality=0.92):
    w, h = img.size
    while True:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=int(quality * 100))
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        if len(b64) <= max_chars or (w <= 200 and quality <= 0.5):
            return f"data:image/jpeg;base64,{b64}", img.convert("RGB"), len(b64)
        if quality > 0.5:
            quality -= 0.1
        else:
            w = int(w * 0.85)
            h = int(h * 0.85)
            img = img.resize((w, h), Image.LANCZOS)


def crop_region(img, x, y, width, height, pad=0.05):
    """按相对坐标裁剪。"""
    iw, ih = img.size
    left = max(0, int((x - pad) * iw))
    top = max(0, int((y - pad) * ih))
    right = min(iw, int((x + width + pad) * iw))
    bottom = min(ih, int((y + height + pad) * ih))
    return img.crop((left, top, right, bottom))


def load_metadata(group_id):
    code, body = fetch_supabase(f"/rest/v1/groups?id=eq.{group_id}")
    if code != 200:
        raise RuntimeError(f"加载组合失败: {code} {body}")
    groups = json.loads(body)
    if not groups:
        raise RuntimeError(f"组合 {group_id} 不存在")
    group = groups[0]

    code, body = fetch_supabase(f"/rest/v1/members?group_id=eq.{group_id}&select=id,name")
    if code != 200:
        raise RuntimeError(f"加载成员失败: {code} {body}")
    members = json.loads(body)
    return group, members


def grid_crop(img, rows, cols):
    """生成固定网格下的裁剪区域列表。"""
    w, h = img.size
    regions = []
    for r in range(rows):
        for c in range(cols):
            regions.append({
                "x": c / cols,
                "y": r / rows,
                "width": 1 / cols,
                "height": 1 / rows,
            })
    return regions


def main():
    parser = argparse.ArgumentParser(description="批量导入卡册")
    parser.add_argument("--image", required=True, help="合照图片路径")
    parser.add_argument("--group", required=True, help="组合ID")
    parser.add_argument("--series", required=True, help="系列名")
    parser.add_argument("--type", default="固卡", help="卡类型")
    parser.add_argument("--positions", help="裁剪坐标 JSON 文件（x/y/width/height 相对值）")
    parser.add_argument("--rows", type=int, help="网格行数（没有 positions 时使用）")
    parser.add_argument("--cols", type=int, help="网格列数（没有 positions 时使用）")
    parser.add_argument("--group-card", choices=["none", "full", "separate"], default="none")
    parser.add_argument("--group-image", help="单独团卡图片路径")
    parser.add_argument("--out-dir", help="输出目录")
    parser.add_argument("--dry-run", action="store_true", help="只生成不写入")
    parser.add_argument("--no-upload", action="store_true", help="生成图片和 payload 但不上传 Supabase")
    args = parser.parse_args()

    group, members = load_metadata(args.group)
    member_map = {m["name"]: m for m in members}
    print(f"组合: {group['name']} ({args.group})")
    print(f"成员: {', '.join(m['name'] for m in members)}")

    img = Image.open(args.image).convert("RGB")
    print(f"合照尺寸: {img.size[0]}x{img.size[1]}")

    # 确定裁剪区域
    if args.positions:
        with open(args.positions) as f:
            positions_data = json.load(f)
        regions = []
        member_order = []
        for p in positions_data:
            regions.append(p)
            member_order.append(p.get("name", ""))
    elif args.rows and args.cols:
        regions = grid_crop(img, args.rows, args.cols)
        member_order = [""] * len(regions)
    else:
        print("错误：需要 --positions 或 --rows+--cols")
        sys.exit(1)

    out_dir = args.out_dir or f"{args.group}_{slugify(args.series)}"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(f"{out_dir}/compressed", exist_ok=True)

    records = []
    ts = int(time.time() * 1000)
    position_log = []

    for i, region in enumerate(regions):
        name = member_order[i] if i < len(member_order) else ""
        m = member_map.get(name) if name else None
        if not m and member_order[i]:
            print(f"跳过: {name} 在成员列表中不存在")
            continue

        # 裁剪
        cropped = crop_region(img, region["x"], region["y"], region["width"], region["height"])
        cropped = cropped.resize((OUTPUT_W, OUTPUT_H), Image.LANCZOS)

        crp_path = f"{out_dir}/{slugify(name or f'pos{i+1}')}_{slugify(args.series)}.png"
        cropped.save(crp_path)

        compressed_url, compressed_img, b64_len = compress_image_to_chars(cropped)
        jpg_path = crp_path.replace('.png', '.jpg')
        compressed_img.save(jpg_path, "JPEG", quality=92)
        print(f"[{i+1}] {name or f'位置{i+1}'}: {cropped.size[0]}x{cropped.size[1]} -> base64 {b64_len} chars -> {jpg_path}")

        record = None
        if m:
            record = {
                "id": f"c_{slugify(args.series)}_{m['id'].split('_')[-1]}_{ts}",
                "group_id": args.group,
                "member_id": m["id"],
                "name": f"{name} {args.series}",
                "series": args.series,
                "card_type": args.type,
                "image_url": compressed_url,
                "image_emoji": "",
            }
        else:
            record = {
                "id": f"c_{slugify(args.series)}_pos{i+1}_{ts}",
                "group_id": args.group,
                "member_id": None,
                "name": f"{name or f'位置{i+1}'} {args.series}",
                "series": args.series,
                "card_type": args.type,
                "image_url": compressed_url,
                "image_emoji": "",
            }
        records.append(record)
        position_log.append({
            "name": name, "x": round(region["x"], 3), "y": round(region["y"], 3),
            "width": round(region["width"], 3), "height": round(region["height"], 3)
        })

    # 团卡
    if args.group_card == "full":
        group_cropped = img.resize((OUTPUT_W, OUTPUT_H), Image.LANCZOS)
        label = "原图"
    elif args.group_card == "separate" and args.group_image:
        group_cropped = Image.open(args.group_image).convert("RGB")
        group_cropped = group_cropped.resize((OUTPUT_W, OUTPUT_H), Image.LANCZOS)
        label = "单独上传"
    else:
        group_cropped = None
        label = ""

    if group_cropped:
        compressed_url, compressed_img, b64_len = compress_image_to_chars(group_cropped)
        jpg_path = f"{out_dir}/compressed/group_{slugify(args.series)}.jpg"
        compressed_img.save(jpg_path, "JPEG", quality=92)
        print(f"团卡({label}): base64 {b64_len} chars")
        records.append({
            "id": f"c_{slugify(args.series)}_group_{ts}",
            "group_id": args.group,
            "member_id": None,
            "name": f"{group['name']} {args.series}团卡",
            "series": args.series,
            "card_type": args.type,
            "image_url": compressed_url,
            "image_emoji": "👥",
        })

    # 保存数据
    payload_path = f"{out_dir}/insert_payload.json"
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    log_path = f"{out_dir}/positions_used.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"positions": position_log, "group_card": args.group_card}, f, ensure_ascii=False, indent=2)

    print(f"\n共 {len(records)} 条记录 -> {payload_path}")
    print(f"裁剪位置 -> {log_path}")

    if args.no_upload or args.dry_run:
        print("跳过 Supabase 写入")
        return

    code, body = fetch_supabase("/rest/v1/cards", method="POST", data=records)
    if code in (200, 201):
        print(f"✅ 已写入 Supabase，共 {len(records)} 张卡")
    else:
        print(f"❌ 写入失败: HTTP {code}")
        print(body[:500] if body else "(空)")
        sys.exit(1)


if __name__ == "__main__":
    main()

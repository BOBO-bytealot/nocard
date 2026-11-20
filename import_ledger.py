#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把账本 data/ledger.json 的 94 条历史记录导入 Supabase ledger_records 表。
用法：
  python3 import_ledger.py --dry-run    # 只预览，不写入
  python3 import_ledger.py              # 正式导入（必须先在 SQL Editor 建好表）
重复运行安全：已存在的 id 会跳过，不会覆盖。
"""
import json, urllib.request, urllib.error, sys

BASE = 'https://neolxiocucigqrrgueim.supabase.co/rest/v1/'
KEY = 'sb_publishable_WW39PvhU8H0FgEdCJk5YRg_eXN7oLIC'
SRC = '/Users/bobosmacprp/WorkBuddy/2026-09-07-16-21-28/svt-ledger/data/ledger.json'
OWNER = 'u1783008431210'


def req(path, method='GET', data=None):
    h = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json',
         'Prefer': 'return=minimal'}
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]


def main():
    dry = '--dry-run' in sys.argv
    ledger = json.load(open(SRC, encoding='utf-8'))
    recs = ledger['records']
    print('账本记录数:', len(recs), '| 模式:', 'DRY-RUN 不写入' if dry else '正式导入')

    # 先查已存在的 id，避免重复导入
    code, existing = req('ledger_records?select=id&limit=1000')
    if code != 200:
        print('查表失败 HTTP', code, existing)
        print('请先在 Supabase SQL Editor 运行 migration_ledger_records.sql 建表')
        sys.exit(1)
    have = set(x['id'] for x in existing)
    print('云端已有:', len(have), '条')

    todo = [r for r in recs if r['id'] not in have]
    print('待导入:', len(todo), '条')
    if not todo:
        print('没有新记录，结束')
        return

    ok = fail = 0
    for i, r in enumerate(todo, 1):
        row = {
            'id': r['id'],
            'data': r,
            'series': r.get('series'),
            'member': r.get('member'),
            'date': r.get('date') or None,
            'cny': r.get('cny') or 0,
            'type': r.get('type') or 'buy',
            'status': r.get('status') or 'active',
            'pay_status': r.get('pay_status'),
            'ship_status': r.get('ship_status'),
            'owner_id': OWNER,
        }
        if dry:
            if i <= 2:
                print('  预览', json.dumps(row, ensure_ascii=False)[:260])
            continue
        code, body = req('ledger_records', 'POST', row)
        if code in (200, 201):
            ok += 1
        else:
            fail += 1
            print('  失败', r['id'], 'HTTP', code, str(body)[:200])
        if i % 20 == 0:
            print('  进度', i, '/', len(todo))

    if dry:
        print('DRY-RUN 完成，没写库')
        return
    print('导入完成: 成功', ok, '失败', fail)

    # 复核
    code, after = req('ledger_records?select=id,cny&limit=1000')
    if code == 200:
        total = sum(float(x.get('cny') or 0) for x in after)
        print('复核云端条数:', len(after), '| cny 合计:', round(total, 2))
        src_total = sum(float(x.get('cny') or 0) for x in recs)
        print('源账本 cny 合计:', round(src_total, 2), '| 一致:', abs(total - src_total) < 0.01)


if __name__ == '__main__':
    main()

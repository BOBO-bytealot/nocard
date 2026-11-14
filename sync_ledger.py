#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 SVT 账本看板同步成卡册里的 BOBO 专属只读页 ledger.html。

账本项目保持零改动：
  - 唯一数据源仍是 svt-ledger/data/ledger.json
  - 改完数据照旧跑 python3 build.py 生成 dashboard.html
  - 再跑本脚本，把 dashboard.html 派生出 ledger.html

本脚本额外注入：BOBO 身份闸门、只读保护、与卡册一致的粉紫皮肤、手机端自适应，
以及【账目加密】：仓库是公开的，L 数据 + app.js 整段用口令 AES-256-GCM 加密，
仓库里只有密文；打开时输一次口令解密，浏览器记住。

用法：
  python3 sync_ledger.py                  # 用已有口令重新生成（口令存在 .ledger_pass）
  python3 sync_ledger.py --set-pass XXX   # 换新口令并重新生成
  python3 sync_ledger.py --show-pass      # 只打印当前口令

口令文件 .ledger_pass 已加入 .gitignore，绝不能提交。
"""
import os
import sys
import json
import re
import subprocess
import secrets
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = "/Users/bobosmacprp/WorkBuddy/2026-09-07-16-21-28/svt-ledger/dashboard.html"
OUT = os.path.join(BASE, "ledger.html")
PASS_FILE = os.path.join(BASE, ".ledger_pass")
OWNER_ID = "u1783008431210"  # BOBO

PBKDF2_ITER = 150000
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # 去掉易混淆字符


# Node 端加密：AES-256-GCM，输出 salt(16)+iv(12)+ciphertext+tag(16) 的 base64。
# 与浏览器 WebCrypto 的 PBKDF2(SHA-256) + AES-GCM 完全兼容。
NODE_ENCRYPT = r"""
const crypto = require('crypto');
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', d => raw += d);
process.stdin.on('end', () => {
  const obj = JSON.parse(raw);
  const salt = crypto.randomBytes(16);
  const iv = crypto.randomBytes(12);
  const key = crypto.pbkdf2Sync(obj.pass, salt, ITER, 32, 'sha256');
  const c = crypto.createCipheriv('aes-256-gcm', key, iv);
  const ct = Buffer.concat([c.update(obj.text, 'utf8'), c.final()]);
  process.stdout.write(Buffer.concat([salt, iv, ct, c.getAuthTag()]).toString('base64'));
});
"""


def ensure_gitignore():
    """口令文件绝不能进公开仓库。"""
    gi = os.path.join(BASE, ".gitignore")
    cur = ""
    if os.path.exists(gi):
        with open(gi, encoding="utf-8") as f:
            cur = f.read()
    if ".ledger_pass" not in cur:
        with open(gi, "a", encoding="utf-8") as f:
            if cur and not cur.endswith("\n"):
                f.write("\n")
            f.write("\n# SVT 账本解锁口令（本地私有，切勿提交）\n.ledger_pass\n")
        print("已把 .ledger_pass 加入 .gitignore")


def load_pass(args):
    if "--show-pass" in args:
        if not os.path.exists(PASS_FILE):
            sys.exit("还没有口令文件，先跑一次 python3 sync_ledger.py")
        print(open(PASS_FILE, encoding="utf-8").read().strip())
        sys.exit(0)

    if "--set-pass" in args:
        i = args.index("--set-pass")
        if i + 1 >= len(args) or not args[i + 1].strip():
            sys.exit("--set-pass 后面要跟新口令")
        p = args[i + 1].strip()
        with open(PASS_FILE, "w", encoding="utf-8") as f:
            f.write(p)
        print("口令已更新：%s" % p)
        return p

    if os.path.exists(PASS_FILE):
        return open(PASS_FILE, encoding="utf-8").read().strip()

    p = "svt-" + "-".join("".join(secrets.choice(ALPHABET) for _ in range(4))
                          for _ in range(3))
    with open(PASS_FILE, "w", encoding="utf-8") as f:
        f.write(p)
    print("=" * 56)
    print("首次生成解锁口令： %s" % p)
    print("请保存好（也存了一份在 .ledger_pass，不会进 git）。")
    print("=" * 56)
    return p


def encrypt(passphrase, plaintext):
    js = NODE_ENCRYPT.replace("ITER", str(PBKDF2_ITER))
    try:
        r = subprocess.run(["node", "-e", js],
                           input=json.dumps({"pass": passphrase, "text": plaintext},
                                            ensure_ascii=False).encode("utf-8"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    except FileNotFoundError:
        sys.exit("加密需要 Node.js（本机有 v22）。请先安装 node 再跑。")
    if r.returncode != 0:
        sys.exit("加密失败：%s" % r.stderr.decode("utf-8", "ignore")[:400])
    return r.stdout.decode().strip()


GUARD = """
<script>
/* 卡册身份闸门 + 只读镜像保护。由 sync_ledger.py 注入，勿手工编辑 ledger.html */
(function(){
  var OWNER = "%s";
  /* 本机 / 离线预览放行；线上域名一律严格校验。strict=1 用于本地验证闸门 */
  var local = location.protocol === "file:" ||
              ["localhost","127.0.0.1","::1"].indexOf(location.hostname) >= 0;
  var force = /[?&]strict=1(?:&|$)/.test(location.search);
  var bypass = !force && (local || /[?&]preview=1(?:&|$)/.test(location.search));
  window.__LEDGER_ALLOW__ = true;
  if(!bypass){
    var uid = null;
    try{ uid = localStorage.getItem("kcard_user_id"); }catch(e){}
    if(uid !== OWNER){
      window.__LEDGER_ALLOW__ = false;
      document.addEventListener("DOMContentLoaded", function(){
        var d = document.createElement("div");
        d.id = "ledgerGate";
        d.style.cssText = "position:fixed;inset:0;z-index:999999;background:#f9f5f5;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:14px;font:15px/1.7 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#4a4055;text-align:center;padding:24px";
        d.innerHTML = '<div style="font-size:44px">🔒</div>' +
          '<div style="font-size:17px;font-weight:600">这个记账本只对 BOBO 开放</div>' +
          '<div style="font-size:13px;color:#8b8494;max-width:340px">当前卡册身份不是 BOBO。请在卡册顶部切回 BOBO 后再打开。</div>' +
          '<a href="/" target="_top" style="margin-top:8px;display:inline-block;padding:9px 20px;border-radius:9px;background:linear-gradient(135deg,#92A8D1,#7c8fc4);color:#fff;text-decoration:none;font-size:13px">← 返回卡册</a>';
        document.body.appendChild(d);
      });
    }
  }
  /* 静态部署没有 /api/save，所有写入口一律拦截；capture 阶段早于 app.js 的冒泡监听 */
  var BLOCK = ".field.editable,[data-act='add'],[data-act='dup'],[data-act='del']," +
              "[data-act='cancel-toggle'],[data-act='add-person'],.tag.toggle," +
              "#btn-add,#fab-add,#btn-save,#add-save,#add-save-more";
  document.addEventListener("click", function(e){
    if(!window.__LEDGER_ALLOW__) return;
    var t = e.target && e.target.closest && e.target.closest(BLOCK);
    if(t){ e.preventDefault(); e.stopPropagation(); }
  }, true);
})();
</script>
""" % OWNER_ID


# 皮肤与手机断点。必须注入在原 <style> 之后，靠层叠顺序覆盖；不修改账本项目任何源文件。
SKIN = """
<style>
/* ============ 由 sync_ledger.py 注入：与卡册 BOBO 主题统一 + 手机自适应 ============ */
:root{
  --bg:#f9f5f5; --card:#fff; --border:#eadfe6; --border2:#d5c8df;
  --text:#4a4055; --muted:#8b8494; --faint:#aaa2b0;
  --blue:#92A8D1; --pink:#F7CAC9; --brand:#7c8fc4; --brand-ink:#5b6ba3;
  --brand-soft:#f2eef9;
}
body{background:var(--bg);color:var(--text)}
.wrap{padding-top:20px}
.pagehead{background:linear-gradient(135deg,#fdf2f2,#eef1fa);border:1px solid var(--border);
  border-radius:12px;padding:14px 18px;margin-bottom:16px}
.pagehead h1{color:var(--brand-ink);font-size:22px}
.pagehead .sub{color:var(--muted)}
.tab{border-color:var(--border2);color:var(--brand-ink)}
.tab.on,.tabs .tab.on{background:linear-gradient(135deg,var(--blue),var(--brand));color:#fff;border-color:transparent}
.card,.kpi,.tn,.sc,.car-list,.ord{border-color:var(--border)}
.card>h2,.detail-head,.modal-head,.modal-foot,.car,.field{border-color:var(--border)}
.tn{background:linear-gradient(160deg,#fff,#fdf7fa)}
.tn b,.kpi .v{color:var(--brand-ink)}
.tn b.neg,.kpi .v.neg{color:#c0392b}
.sc.has{background:var(--brand-soft);border-color:var(--border2)}
.sc.common{background:#faf6f9}
.sc.sel{outline:2px solid var(--blue)}
.ord.on,.filter-chip,.btn-primary,.toast,.savebar,.fab{
  background:linear-gradient(135deg,var(--blue),var(--brand));color:#fff;border-color:transparent}
.ord.on span{color:#f0f2fa}
.filter-chip button:hover{background:rgba(255,255,255,.25)}
.optchip.sel{box-shadow:inset 0 0 0 2px var(--blue)}
.addbtn,.btn-ghost,.panel-actions button,.box button,.detail-close{border-color:var(--border2);color:var(--brand-ink)}
.addbtn:hover,.btn-ghost:hover,.panel-actions button:hover,.box button:hover,.detail-close:hover{background:#f6f1f8}
.searchbar input,.filters select.f-sel,.filters input.f-search,input[type=text]{border-color:var(--border2);border-radius:9px}
.searchbar input:focus,.filters select.f-sel:focus,.filters input.f-search:focus{
  border-color:var(--blue);box-shadow:0 0 0 3px rgba(146,168,209,.18)}
.bar-track{background:#f0ebf3}
th{background:#faf5f9;border-color:var(--border2);color:var(--muted)}
tbody tr:nth-child(even) td{background:#fdfafd}
tbody tr.click:hover td{background:#f7f1fa}
.card-detail{border-color:var(--border2)}
.box.info{background:#f2eef9;border-color:var(--border2);color:var(--brand-ink)}
.box.warn{background:#fdf2f2;border-color:#efd3dc;color:#9b5b6d}
.ro-note{background:linear-gradient(135deg,#fdf2f2,#f2eef9);border:1px solid var(--border2);
  color:var(--brand-ink);border-radius:10px;padding:10px 14px;margin-bottom:16px;font-size:12.5px;line-height:1.8}
.ro-note b{color:#4a5a92}
.ro-note code{background:rgba(124,143,196,.13);padding:1px 5px;border-radius:4px;font-size:11.5px}

/* ---------- 只读镜像：隐藏写入口、去掉可编辑暗示 ---------- */
#btn-add,#fab-add,#btn-save,.savebar{display:none!important}
[data-act='add'],[data-act='dup'],[data-act='del'],[data-act='cancel-toggle'],[data-act='add-person']{display:none!important}
.field.editable{cursor:default!important}
.field.editable:hover{background:transparent!important}
.field.editable:hover .field-value::after{content:none!important}

/* ---------- 手机自适应（卡册本身就是 480px 手机壳，账本跟着收） ---------- */
@media(max-width:640px){
  .wrap{padding:12px 12px 40px}
  .pagehead{flex-direction:column;align-items:stretch;gap:10px;padding:12px 14px;margin-bottom:14px;border-radius:10px}
  .pagehead h1{font-size:19px}
  .pagehead .sub{font-size:11.5px;line-height:1.5}
  .nav{width:100%}
  .nav .tab{flex:1;text-align:center;padding:7px 8px;font-size:12px}
  .topnums{grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:14px}
  .tn{padding:10px 12px;border-radius:10px}
  .tn span{font-size:11px}
  .tn b{font-size:18px}
  .ro-note{font-size:11.5px;padding:9px 11px;margin-bottom:12px;line-height:1.7}
  .card{padding:13px 12px;margin-bottom:14px;border-radius:10px}
  .card>h2{font-size:14px;padding-bottom:9px;margin-bottom:11px}
  .card-head{flex-wrap:wrap;gap:8px}
  .card-head .tabs{margin-bottom:0}
  .tabs .tab{padding:5px 9px;font-size:11.5px}
  .hint{font-size:11px;line-height:1.5}
  /* minmax(0,1fr) + min-width:0：否则卡内长文本的 min-content 会把列撑爆、整页横向溢出 */
  .shelf{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .sc{min-width:0;min-height:86px;padding:10px;border-radius:9px}
  .sc-t,.sc-v,.sc-m,.sc-p{min-width:0;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .sc-t{font-size:12.5px}
  .sc-v,.sc-p{font-size:10.5px}
  .sc-m{font-size:15px}
  .searchbar input{padding:10px 12px;font-size:13px}
  .filters{gap:6px}
  .filters select.f-sel,.filters input.f-search{min-width:0;max-width:none;flex:1 1 45%;font-size:12px}
  .table-scroll{margin:0 -12px;padding:0 12px}
  table{font-size:12px}
  th,td{padding:7px 8px}
  .car-h{gap:7px;padding:10px}
  .car-name{min-width:0;font-size:12.5px}
  .car-date{font-size:11px}
  .car-body{padding:0 10px 12px}
  .orders{gap:5px}
  .ord{font-size:11px;padding:5px 8px}
  .detail{width:100%;max-width:100%;border-left:none}
  .detail-head{padding:12px 14px}
  .detail-body{padding:6px 14px 20px}
  .field{gap:8px;padding:9px 0}
  .field-label{width:50px;font-size:11px}
  .field-value{font-size:13px}
  .modal{width:100%}
  .modal-head,.modal-body,.modal-foot{padding-left:14px;padding-right:14px}
  .fgrid{grid-template-columns:84px 1fr;gap:8px}
  .pstat{grid-template-columns:repeat(2,1fr)}
  .two{grid-template-columns:1fr}
  .bar-name{width:88px;font-size:12px}
  .bar-val{width:86px;font-size:12px}
  .box{font-size:12px;padding:9px 11px}
}
</style>
"""

RO_NOTE = """
  <div class="ro-note">📖 <b>只读镜像</b> · 这是卡册里的 BOBO 专属记账本，账目已加密，
  数据来自本地 <code>svt-ledger/data/ledger.json</code>，由 <code>build.py</code> 生成后同步过来。
  要改账请在本机账本里改、跑 <code>python3 build.py</code>，再跑 <code>python3 sync_ledger.py</code> 重新同步；
  本页上的改动不会写回任何地方。</div>
"""


# 解密 + 解锁面板。明文 bundle 解密后用动态 <script> 注入，等价于原本的内联脚本，
# 保证 app.js 顶层 recompute()/renderAll() 与全局词法环境和原页面完全一致。
UNLOCK_JS = r"""
/* 账目加密层：由 sync_ledger.py 注入。仓库里只有密文，口令不在此文件里。 */
(function(){
  var PASS_KEY = "svt_ledger_pass";
  var ITER = __ITER__;
  var encEl = document.getElementById("ledgerCipher");
  var b64 = encEl ? encEl.textContent.replace(/\s+/g, "") : "";
  if(!b64) return;
  /* 线上非 BOBO：身份闸门已经盖了遮罩，这里连解锁面板都不给 */
  if(window.__LEDGER_ALLOW__ === false) return;
  if(!window.crypto || !crypto.subtle){
    document.body.innerHTML = '<div style="padding:40px;font:15px sans-serif;color:#4a4055">' +
      '当前环境不支持 WebCrypto，请用 https 打开卡册站点查看账本。</div>';
    return;
  }

  var panel = null, inp = null, err = null, remember = null, busy = false;

  function showPanel(msg){
    if(panel) { if(msg) setErr(msg); return; }
    panel = document.createElement("div");
    panel.id = "unlockPanel";
    panel.setAttribute("style", "position:fixed;inset:0;z-index:99999;display:flex;" +
      "align-items:center;justify-content:center;padding:20px;overflow:auto;" +
      "background:linear-gradient(135deg,#fdf2f2,#eef1fa);" +
      "font:14px/1.7 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#4a4055");
    panel.innerHTML =
      '<div style="width:100%;max-width:360px;background:#fff;border:1px solid #eadfe6;' +
        'border-radius:16px;padding:26px 24px 22px;box-shadow:0 8px 30px rgba(70,50,90,.10);text-align:center">' +
        '<div style="font-size:38px;line-height:1.2">🔐</div>' +
        '<div style="font-size:18px;font-weight:700;color:#5b6ba3;margin:8px 0 4px">SVT 追星账本</div>' +
        '<div style="font-size:12.5px;color:#8b8494;line-height:1.7;margin-bottom:18px">' +
          '账目已加密存放在公开仓库里。输入口令解锁，<br>口令只保存在你自己的浏览器中。</div>' +
        '<input id="lkPass" type="password" autocomplete="current-password" placeholder="解锁口令"' +
          ' style="width:100%;box-sizing:border-box;padding:11px 13px;font-size:14px;border:1px solid #d5c8df;' +
          'border-radius:9px;outline:none;color:#4a4055;background:#fdfafd">' +
        '<label style="display:flex;align-items:center;gap:7px;font-size:12px;color:#8b8494;' +
          'margin:12px 0 14px;cursor:pointer;text-align:left">' +
          '<input id="lkRemember" type="checkbox" checked style="accent-color:#7c8fc4"> 在这台设备上记住口令</label>' +
        '<button id="lkGo" style="width:100%;padding:11px;border:none;border-radius:9px;cursor:pointer;' +
          'background:linear-gradient(135deg,#92A8D1,#7c8fc4);color:#fff;font-size:14px;font-weight:600">解锁</button>' +
        '<div id="lkErr" style="font-size:12px;color:#c0392b;min-height:18px;margin-top:10px"></div>' +
        '<div style="font-size:11px;color:#aaa2b0;margin-top:6px">仅 BOBO 可见 · 数据只读</div>' +
      '</div>';
    document.body.appendChild(panel);
    inp = document.getElementById("lkPass");
    err = document.getElementById("lkErr");
    remember = document.getElementById("lkRemember");
    document.getElementById("lkGo").addEventListener("click", function(){ attempt(inp.value, remember.checked); });
    inp.addEventListener("keydown", function(e){ if(e.key === "Enter") attempt(inp.value, remember.checked); });
    if(msg) setErr(msg);
    setTimeout(function(){ try{ inp.focus(); }catch(e){} }, 50);
  }

  function setErr(m){ if(err) err.textContent = m || ""; }

  function bytes(){
    var bin = atob(b64), a = new Uint8Array(bin.length);
    for(var i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i);
    return a;
  }

  function decrypt(pass){
    var a = bytes();
    var salt = a.slice(0, 16), iv = a.slice(16, 28), ct = a.slice(28);
    return crypto.subtle.importKey("raw", new TextEncoder().encode(pass), "PBKDF2", false, ["deriveKey"])
      .then(function(km){
        return crypto.subtle.deriveKey({name:"PBKDF2", salt:salt, iterations:ITER, hash:"SHA-256"},
                                       km, {name:"AES-GCM", length:256}, false, ["decrypt"]);
      })
      .then(function(key){ return crypto.subtle.decrypt({name:"AES-GCM", iv:iv}, key, ct); })
      .then(function(buf){ return new TextDecoder().decode(buf); });
  }

  function boot(plain, pass, save){
    if(save){ try{ localStorage.setItem(PASS_KEY, pass); }catch(e){} }
    /* 动态脚本注入：和原本的内联 <script> 处在同一个全局词法环境 */
    var s = document.createElement("script");
    s.textContent = plain;
    document.body.appendChild(s);
    if(panel && panel.parentNode) panel.parentNode.removeChild(panel);
  }

  function attempt(pass, save){
    if(busy) return;
    if(!pass){ setErr("请输入口令"); return; }
    busy = true; setErr("正在解密…");
    decrypt(pass).then(function(plain){
      busy = false; setErr("");
      boot(plain, pass, save);
    }).catch(function(){
      busy = false; setErr("口令不对，再试一次");
    });
  }

  /* 记住过口令就自动解锁；换口令后旧值失效，会清掉并要求重新输入 */
  var saved = null;
  try{ saved = localStorage.getItem(PASS_KEY); }catch(e){}
  if(saved){
    decrypt(saved).then(function(plain){
      boot(plain, saved, false);
    }).catch(function(){
      try{ localStorage.removeItem(PASS_KEY); }catch(e){}
      showPanel("账本已重新同步，请再输一次口令");
    });
  } else {
    showPanel("");
  }
})();
"""


def main():
    args = sys.argv[1:]
    ensure_gitignore()
    passphrase = load_pass(args)

    if not os.path.exists(SRC):
        sys.exit("源看板不存在：%s\n先到 svt-ledger 项目跑 python3 build.py" % SRC)

    with open(SRC, encoding="utf-8") as f:
        html = f.read()

    for ph in ("__DATA__", "__APP_JS__", "__UPDATED__", "__TODAY__"):
        if ph in html:
            sys.exit("源看板还有未替换的占位符 %s，先跑 build.py" % ph)

    # 1) 身份闸门脚本放进 head 最前，早于任何页面脚本
    if "<head>" not in html:
        sys.exit("源看板结构异常：找不到 <head>")
    html = html.replace("<head>", "<head>" + GUARD, 1)

    # 2) 皮肤放在 </head> 前，确保压得住账本自带的 <style>
    if html.count("</head>") != 1:
        sys.exit("源看板结构异常：找不到唯一的 </head>")
    html = html.replace("</head>", SKIN + "</head>", 1)

    # 3) 顶部只读说明
    if '<div class="wrap">' not in html:
        sys.exit("源看板结构异常：找不到 .wrap")
    html = html.replace('<div class="wrap">', '<div class="wrap">' + RO_NOTE, 1)

    # 4) 静态页没有 serve.py 的 /api/save，关掉「已连接本地服务」误判与自动 POST
    old = 'const isServed = () => location.protocol==="http:" || location.protocol==="https:";'
    if html.count(old) != 1:
        sys.exit("isServed 定义找不到或出现多次（%d），账本 app.js 可能改过，请人工确认" % html.count(old))
    html = html.replace(old, 'const isServed = () => false; /* 静态只读镜像，无 /api/save 后端 */', 1)

    # 5) 清掉卡册域里可能残留的账本草稿，避免弹出「恢复未保存更改」
    marker = 'const DRAFT = "svt-ledger-draft";'
    if marker in html:
        html = html.replace(
            marker,
            'const DRAFT = "svt-ledger-draft";\ntry{ localStorage.removeItem(DRAFT); }catch(e){}',
            1,
        )

    # 6) 把 L 数据 + 整段 app.js 加密，替换成「密文 + 解锁器」
    m = re.search(r"const L = (\{.*?\});\n", html, re.S)
    if not m:
        sys.exit("找不到 const L 数据段，源看板结构可能变了")
    n_records = len(json.loads(m.group(1))["records"])

    idx = html.find("const L = ")
    start = html.rfind("<script>", 0, idx)
    end = html.find("</script>", idx)
    if start < 0 or end < 0:
        sys.exit("定位账本脚本失败")
    bundle = html[start + len("<script>"):end]
    if "</script" in bundle.lower():
        sys.exit("账本脚本内含 </script 字面量，需转义，请先人工检查")

    cipher = encrypt(passphrase, bundle)
    unlock = UNLOCK_JS.replace("__ITER__", str(PBKDF2_ITER))
    replacement = ('<script id="ledgerCipher" type="text/plain">' + cipher + '</' + 'script>\n'
                   + '<script>' + unlock + '</' + 'script>')
    html = html[:start] + replacement + html[end + len("</script>"):]

    # 兜底：任何账目明文都不该留在仓库里
    for leak in ('"records"', '"beneficiary"', '"payer"', 'const L = {'):
        if leak in html:
            sys.exit("检测到账目明文残留 %s，已中止写出（未覆盖旧 ledger.html）" % leak)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print("已生成 %s" % OUT)
    print("  源：%s" % SRC)
    print("  记录数：%s 条 | 页面 %.1f KB | 密文 %.1f KB | 同步时间：%s"
          % (n_records, os.path.getsize(OUT) / 1024, len(cipher) / 1024,
             datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
    print("  解锁口令：%s（也存于 .ledger_pass，已 gitignore）" % passphrase)
    print("  注入：身份闸门 / 只读拦截 / 粉紫皮肤 / 640px 手机断点 / AES-256-GCM 加密")


if __name__ == "__main__":
    main()

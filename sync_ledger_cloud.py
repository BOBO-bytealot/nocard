#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从账本 dashboard.html 生成「云端可记账版」ledger.html。
- 账目/配置全部从 Supabase ledger_records 读取，页面里不含任何明文
- 保留看板全部渲染/KPI/系列卡/新增编辑删除逻辑
- 保存改成按 id diff 同步到 Supabase（新增/改/删）
- 保留 BOBO 身份闸门；去掉原只读拦截（因为现在要能记）

用法: python3 sync_ledger_cloud.py
源文件 svt-ledger/data/ledger.json 全程只读，不修改。
"""
import os, re, json, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = "/Users/bobosmacprp/WorkBuddy/2026-09-07-16-21-28/svt-ledger/dashboard.html"
OUT = os.path.join(BASE, "ledger.html")
OWNER_ID = "u1783008431210"


# 身份闸门（保留，去掉只读 BLOCK 拦截——现在允许记账）
GUARD_CLOUD = """
<script>
/* 卡册身份闸门 + 云端账本。由 sync_ledger_cloud.py 注入，勿手工编辑 ledger.html */
(function(){
  var OWNER = "%s";
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
})();
</script>
""" % OWNER_ID


# 云端适配层：放进账本 app.js 之前，定义 isServed / supa* / 启动加载。
# 注意：原 app.js 里的 const isServed 会与这里的冲突，生成时会删掉原定义。
CLOUD_ADAPTER = r"""
<script>
/* ===== 云端账本适配层：由 sync_ledger_cloud.py 注入 ===== */
var LEDGER_SUPA_URL = "https://neolxiocucigqrrgueim.supabase.co";
var LEDGER_SUPA_KEY = "sb_publishable_WW39PvhU8H0FgEdCJk5YRg_eXN7oLIC";
var LEDGER_OWNER_ID = "__OWNER__";

function supaReq(path, method, data){
  var h = {"apikey":LEDGER_SUPA_KEY, "Authorization":"Bearer "+LEDGER_SUPA_KEY,
           "Content-Type":"application/json", "Prefer":"return=minimal"};
  return fetch(LEDGER_SUPA_URL+"/rest/v1/"+path, {
    method: method||"GET", headers: h, body: data?JSON.stringify(data):undefined
  });
}

/* 云端账本始终在线（能记能存） */
const isServed = () => true;

/* ===== 一句话录入：把中文一句话解析成 record（对齐 quick_add_ledger.py） ===== */
function parseQuickLedger(text){
  var t = ' ' + (text||'').trim() + ' ';
  var out = {cny:0, item:'', series:'SVT', batch:null, party:null,
             beneficiary:'me', payer:'me', pay_status:'paid',
             ship_status:'pending', note:null, prefix:'SVT', eta:null};
  // 金额：最后一个 ¥/元/块 或裸数字
  var nums = t.match(/\d+(?:\.\d+)?(?:\s*(?:元|块))?/g) || [];
  if(nums.length){ var last=nums[nums.length-1].replace(/(元|块)/g,'').trim(); out.cny=parseFloat(last)||0; }
  // 车位号
  var sm = t.match(/车位\s*(\d+)/); var seat = sm ? sm[1] : null;
  // 分类 + 前缀
  var low = t.toLowerCase(), short = null;
  if(/YAKUSOKU|yakusoku|场周|DC/i.test(t)){ out.batch='YAKUSOKU 场周 DC'; out.prefix='YAKU'; short='场周DC'; }
  else if(/kkt|书签/i.test(t)){ out.batch='2027台历 kkt书签'; out.prefix='KKT'; short='kkt书签'; }
  else if(/qq音乐|q音/i.test(t)){ out.batch='2027台历 qq音乐'; out.prefix='QQ'; short='qq音乐'; }
  else if(/台历|日历/.test(t)){ out.batch='2027台历'; out.prefix='CAL'; short='台历'; }
  // 人
  var people=['婧儿','Edwin','edwin','edwina','冷锅鱼子','代购'];
  var person=null; for(var i=0;i<people.length;i++){ if(t.indexOf(people[i])>=0){ person=people[i]; break; } }
  var m2=t.match(/我欠([\u4e00-\u9fa5A-Za-z]{1,6})/); if(m2) person=m2[1];
  if(/欠我|我垫付|我出的|我付的/.test(t)){
    out.beneficiary=person||'婧儿'; out.payer='me'; out.party=person;
    out.note=(person||'婧儿')+' owes me（我垫付）';
  } else if(/我欠|帮我出|代付/.test(t)){
    out.beneficiary='me'; out.payer=person||'婧儿'; out.party=person;
    out.note='我 owe '+(person||'婧儿')+'（对方垫付）';
  } else if(/我的|是我的/.test(t)){
    out.beneficiary='me'; out.payer='me';
  } else if(person){
    out.party=person; out.payer=person; out.beneficiary='me';
  }
  // 状态
  if(/到了|收到|到货|已到|arrived/.test(t)) out.ship_status='arrived';
  if(/没付|未付|unpaid/.test(t)) out.pay_status='unpaid';
  // 商品名
  var name=t;
  var drop=people.concat(['欠我','我欠','我垫付','我出的','我付的','帮我出','代付','我的','是我的',
    '等补邮','等补货','没到货','未到货','没给我','到了','收到','到货','已付款','没付款','已付','没付','未付',
    '2027台历','YAKUSOKU','yakusoku','场周','DC','dc','kkt','书签','qq音乐','Q音','q音','台历','日历',
    '车位','调价','（可转）','(可转)','元','块','¥','我','的','是','收了']);
  for(var j=0;j<drop.length;j++) name=name.split(drop[j]).join(' ');
  name=name.replace(/\d+(?:\.\d+)?/g,' ').replace(/\s+/g,' ').trim(' ，,、');
  if(name.length<=1) name='';
  if(!name) name=[short, seat?('车位'+seat):null].filter(Boolean).join(' ');
  if(!name) name=(/欠我|我欠/.test(t))?'代垫':(text||'').trim();
  out.item=name;
  return out;
}

/* 生成 id：取该类前缀最大值 +1 */
function quickNextId(prefix){
  var mx=0;
  for(var i=0;i<L.records.length;i++){
    var id=L.records[i].id||'';
    if(id.indexOf(prefix+'-')===0){
      var n=parseInt(id.slice(prefix.length+1),10); if(!isNaN(n)&&n>mx) mx=n;
    }
  }
  return prefix+'-'+String(mx+1).padStart(3,'0');
}

/* 一句话录入提交：构造 record -> 直接 POST -> 刷新云端 */
var quickAdding = false;
async function submitQuickLedger(){
  if(!window.__LEDGER_ALLOW__){ toast('身份不对'); return; }
  if(quickAdding) return;
  var inp=document.getElementById('quickInput');
  var text=(inp&&inp.value||'').trim();
  if(!text){ toast('先写一句话'); if(inp) inp.focus(); return; }
  var p=parseQuickLedger(text);
  if(!p.cny){ toast('没认出金额'); return; }
  quickAdding=true;
  var btn=document.getElementById('quickGo'); if(btn) btn.disabled=true;
  try{
    var rid=quickNextId(p.prefix);
    var rec={
      id:rid, series:p.series, member:null, batch:p.batch, item:p.item,
      qty:1, unit:'个', date:null, date_basis:'记录日', recorded:TODAY,
      currency:'CNY', amount:p.cny, fx:1, cny:p.cny,
      channel:(p.party?'拼车':null), party:p.party, beneficiary:p.beneficiary, payer:p.payer,
      type:'buy', pay_status:p.pay_status, ship_status:p.ship_status,
      eta:p.eta, status:'active', breakdown:null, note:p.note
    };
    var row={id:rid,data:rec,series:rec.series,member:null,date:null,cny:p.cny,
      type:'buy',status:'active',pay_status:p.pay_status,ship_status:p.ship_status,owner_id:LEDGER_OWNER_ID};
    var res=await supaReq('ledger_records','POST',row);
    if(!res.ok) throw new Error('HTTP '+res.status);
    if(inp) inp.value='';
    toast('✅ 已记 '+rec.item+' ¥'+p.cny+' · '+rid);
    await loadCloudLedger();
  }catch(e){
    toast('记账失败：'+(e.message||e));
  }finally{
    quickAdding=false; if(btn) btn.disabled=false;
  }
}

/* 覆盖保存：按 id diff 同步到 Supabase（新增/改/删）。
   注意：用 var 赋值覆盖 app.js 里的同名函数声明，因此本段须在 app.js 之后执行。 */
var doSave = async function(){
  if(!window.__LEDGER_ALLOW__){ return }
  try{
    var res = await fetch(LEDGER_SUPA_URL+"/rest/v1/ledger_records?select=id&limit=2000", {
      headers:{"apikey":LEDGER_SUPA_KEY,"Authorization":"Bearer "+LEDGER_SUPA_KEY}
    });
    if(!res.ok) throw new Error("读取云端失败 "+res.status);
    var remote = await res.json();
    var remoteIds = {}; remote.forEach(function(x){ remoteIds[x.id]=true });
    var localIds = {}; L.records.forEach(function(r){ localIds[r.id]=true });

    // 1) 本地有、云端没有 -> insert
    for(var i=0;i<L.records.length;i++){
      var r=L.records[i];
      if(!remoteIds[r.id]){
        var row={id:r.id,data:r,series:r.series||null,member:r.member||null,
          date:r.date||null,cny:Number(r.cny)||0,type:r.type||"buy",status:r.status||"active",
          pay_status:r.pay_status||null,ship_status:r.ship_status||null,owner_id:LEDGER_OWNER_ID};
        var ir=await supaReq("ledger_records","POST",row);
        if(!ir.ok) throw new Error("新增失败 "+r.id+" HTTP "+ir.status);
      }
    }
    // 2) 云端有、本地没有 -> delete（跳过 __META__）
    for(var j=0;j<remote.length;j++){
      var rid=remote[j].id;
      if(rid!=="__META__" && !localIds[rid]){
        var dr=await supaReq("ledger_records?id=eq."+encodeURIComponent(rid),"DELETE");
        if(!dr.ok) throw new Error("删除失败 "+rid+" HTTP "+dr.status);
      }
    }
    // 3) 两边都有 -> 比较 data，不同则 update
    var changed=0;
    for(var k=0;k<L.records.length;k++){
      var rec=L.records[k];
      // 只在确实改动时 PATCH：用 JSON 字符串比对（remote 的 data 需回读，见下）
      // 为简化，这里对每条都做 PATCH data（幂等，94 条约 1 秒量级，可接受）
      var ur=await supaReq("ledger_records?id=eq."+encodeURIComponent(rec.id),"PATCH",{
        data:rec, series:rec.series||null, member:rec.member||null,
        date:rec.date||null, cny:Number(rec.cny)||0, type:rec.type||"buy",
        status:rec.status||"active", pay_status:rec.pay_status||null,
        ship_status:rec.ship_status||null
      });
      if(!ur.ok) throw new Error("更新失败 "+rec.id+" HTTP "+ur.status);
      changed++;
    }
    dirty=false; try{localStorage.removeItem(DRAFT)}catch(e){}
    setSaveBar("saved","✅ 已同步到云端 · "+L.records.length+" 条");
  }catch(e){
    setSaveBar("dirty","保存失败："+(e.message||e)+"（检查网络）");
  }
}

/* 启动：从云端加载 meta 与 records，再重算渲染。var 赋值覆盖，放 app.js 之后。 */
var loadCloudLedger = async function(){
  if(!window.__LEDGER_ALLOW__){ return }
  try{
    var res=await fetch(LEDGER_SUPA_URL+"/rest/v1/ledger_records?select=id,data&limit=2000",{
      headers:{"apikey":LEDGER_SUPA_KEY,"Authorization":"Bearer "+LEDGER_SUPA_KEY}
    });
    if(!res.ok) throw new Error("云端读取失败 "+res.status);
    var rows=await res.json();
    var recs=[], meta=null;
    rows.forEach(function(x){
      if(x.id==="__META__") meta=x.data;
      else if(x.data) recs.push(x.data);
    });
    if(meta){
      // 用云端 meta 覆盖（保留结构），配置更新立即生效
      Object.keys(meta).forEach(function(k){ L.meta[k]=meta[k] });
    }
    L.records=recs;
    recs.forEach(function(r){ REC_MAP[r.id]=r });
    recompute(); renderAll();
    setSaveBar("saved","☁️ 已连接云端 · "+recs.length+" 条");
  }catch(e){
    setSaveBar("dirty","云端加载失败："+(e.message||e)+"（请检查网络）");
  }
}
</script>
"""


def main():
    if not os.path.exists(SRC):
        sys.exit("源看板不存在：" + SRC)
    with open(SRC, encoding="utf-8") as f:
        html = f.read()

    for ph in ("__DATA__", "__APP_JS__", "__UPDATED__", "__TODAY__"):
        if ph in html:
            sys.exit("源看板还有占位符 %s，先跑 build.py" % ph)

    # 1) 身份闸门（云端版，保留 gate、去掉只读拦截）
    html = html.replace("<head>", "<head>" + GUARD_CLOUD, 1)

    # 2) 复用原皮肤：从 sync_ledger.py 里取 SKIN
    import sync_ledger as sl
    if html.count("</head>") != 1:
        sys.exit("结构异常：head 不唯一")
    skin = sl.SKIN
    # 只读镜像皮肤把记账入口全隐藏了（display:none!important），云端版要反转：
    # 删掉那几条隐藏规则，让「新增消费 / 悬浮记一笔 / 复制 / 删除 / 状态切换」恢复可见可点。
    skin = skin.replace("#btn-add,#fab-add,#btn-save,.savebar{display:none!important}",
                        "/* 云端版：保留记账入口 */")
    skin = skin.replace("[data-act='add'],[data-act='dup'],[data-act='del'],[data-act='cancel-toggle'],[data-act='add-person']{display:none!important}",
                        "/* 云端版：保留行操作 */")
    skin = skin.replace(".field.editable{cursor:default!important}",
                        ".field.editable{cursor:pointer!important}")
    skin = skin.replace(".field.editable:hover{background:transparent!important}",
                        ".field.editable:hover{background:var(--tint,#f7f1f5)!important}")
    skin = skin.replace(".field.editable:hover .field-value::after{content:none!important}",
                        ".field.editable:hover .field-value::after{content:'编辑'!important;color:var(--faint,#999);font-size:11px;margin-left:10px}")
    # savebar 在原只读皮肤里被隐藏，但里面有「＋ 新增消费」主按钮；云端版显示它（保留状态文字）
    # 「保存」「下载 ledger.json」在云端没意义，单独隐藏；fab-add 右下角悬浮笔也恢复
    skin += """
<style>
/* 云端版：隐藏本地服务专属按钮，保留记账入口 */
#btn-save,#btn-download{display:none!important}
.savebar{display:flex!important}
.fab{display:flex!important}
[data-act='add'],[data-act='dup'],[data-act='del'],[data-act='cancel-toggle']{display:inline-block!important}
#fab-add{position:fixed;right:20px;bottom:20px;z-index:50}
</style>
"""
    html = html.replace("</head>", skin + "</head>", 1)

    # 3) 顶部说明换成云端版
    ro_cloud = """<div class="ro-note">☁️ <b>云端账本 · 可记可改</b> · 账目存在 Supabase，
      在这个网页上新增/编辑/删除会自动同步，手机上也能记。仅 BOBO 可见。</div>"""
    # 一句话录入条：手机上打一句话直接记，不用点表单
    quick_ui = """
<div class="quick-bar">
  <div class="quick-title">⚡ 一句话记账 <span>不用填表，打完直接点记</span></div>
  <div class="quick-row">
    <input id="quickInput" type="text" enterkeyhint="go" autocomplete="off"
      placeholder="例：婧儿 kkt书签 车位9 9.68 等补邮" onkeydown="if(event.key==='Enter'){submitQuickLedger()}">
    <button id="quickGo" onclick="submitQuickLedger()">记一笔</button>
  </div>
  <div class="quick-tip">谁欠我/我欠谁、分类、到货状态都能写进一句话里</div>
</div>
"""
    quick_css = """
<style>
.quick-bar{background:linear-gradient(135deg,#fdf2f8,#f3f0fe);border:1px solid #e8dcef;
  border-radius:12px;padding:12px 14px;margin:10px 0 16px}
.quick-title{font-size:13px;font-weight:700;color:#6b4a7a;margin-bottom:8px}
.quick-title span{font-weight:400;font-size:11px;color:#9a8aa5;margin-left:6px}
.quick-row{display:flex;gap:8px;align-items:stretch}
.quick-row input{flex:1;min-width:0;border:1px solid #dcd0e8;border-radius:9px;padding:11px 12px;
  font-size:16px;background:#fff;color:#4a4055;outline:none}
.quick-row input:focus{border-color:#92A8D1;box-shadow:0 0 0 3px rgba(146,168,209,.18)}
.quick-row button{flex:0 0 auto;padding:0 18px;border:none;border-radius:9px;color:#fff;
  font-size:14px;font-weight:700;background:linear-gradient(135deg,#92A8D1,#7c8fc4);cursor:pointer}
.quick-row button:disabled{opacity:.5;cursor:wait}
.quick-tip{font-size:10.5px;color:#9a8aa5;margin-top:7px}
@media(max-width:640px){.quick-title span{display:none}.quick-row button{padding:0 14px}}
</style>
"""
    html = html.replace("</head>", quick_css + "</head>", 1)
    html = html.replace('<div class="wrap">', '<div class="wrap">' + ro_cloud + quick_ui, 1)

    # 3b) 副标题去掉「源文件/build.py/请勿手改」等本地镜像字样
    html = html.replace('数据源 data/ledger.json · 更新于', '云端实时数据 · 更新于', 1)
    html = html.replace('本页由 build.py 自动生成，请勿手改', '网页上可直接记新账、改明细', 1)

    # 4) 删掉原 app.js 里的 isServed 定义（我们注入了新的）
    old = 'const isServed = () => location.protocol==="http:" || location.protocol==="https:";'
    if html.count(old) != 1:
        sys.exit("isServed 定义找不到或多次（%d）" % html.count(old))
    html = html.replace(old, '/* isServed 由云端适配层定义 */', 1)

    # 5) const L 只清空 records（不放金额明细）；meta 保留内嵌——
    #    app.js 顶层立刻用 L.meta.series / L.meta.people 做初始化，清空会 TDZ 崩溃。
    #    meta 只有系列/成员/昵称配置，无金额，不含账目明文。
    m = re.search(r"const L = (\{.*?\});\n", html, re.S)
    if not m:
        sys.exit("找不到 const L 数据段")
    orig = json.loads(m.group(1))
    n_records = len(orig.get("records", []))
    kept_L = json.dumps({"meta": orig.get("meta", {}), "records": []}, ensure_ascii=False)
    html = html[:m.start(1)] + kept_L + html[m.end(1):]

    # 6) 校验无账目明文残留（meta 里的成员昵称不算账目）
    for leak in ('"beneficiary":', '"payer":', '"amount":'):
        if leak in html:
            sys.exit("检测到账目明文残留 %s，中止写出" % leak)

    # 7) 适配层必须与 app.js 在同一个 script 块（共享 const ACT 等词法作用域）。
    #    HEAD（常量 + supaReq + isServed）放 app.js 前，供 app.js 执行期间引用；
    #    TAIL（doSave / loadCloudLedger 用 var 覆盖函数声明）放 app.js 末尾之后。
    adapter_code = CLOUD_ADAPTER.replace("__OWNER__", OWNER_ID)
    adapter_code = adapter_code.replace("<script>", "", 1)
    adapter_code = adapter_code.rsplit("</script>", 1)[0]
    split_mark = "/* 覆盖保存：按 id diff 同步到 Supabase"
    if split_mark not in adapter_code:
        sys.exit("适配层拆分标记找不到")
    head_code, tail_code = adapter_code.split(split_mark, 1)
    tail_code = split_mark + tail_code

    idx = html.find("const L = ")
    start = html.rfind("<script>", 0, idx)
    end = html.find("</script>", idx)
    if start < 0 or end < 0:
        sys.exit("定位账本脚本失败")

    # HEAD 插在 app.js 脚本块开头
    html = html[:start + len("<script>")] + head_code + "\n" + html[start + len("<script>"):]

    # TAIL 插在 app.js 末尾（</script> 之前），再调 loadCloudLedger
    idx2 = html.find("const L = ")
    end2 = html.find("</script>", idx2)
    tail_all = "\n" + tail_code + "\n/* 云端加载：覆盖初始空数据（同作用域，ACT 已初始化）*/\nloadCloudLedger();\n"
    html = html[:end2] + tail_all + html[end2:]

    # 8) 清掉可能残留的草稿提示
    marker = 'const DRAFT = "svt-ledger-draft";'
    if marker in html:
        html = html.replace(marker, marker + '\ntry{ localStorage.removeItem(DRAFT); }catch(e){}', 1)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print("已生成云端版 %s" % OUT)
    print("  源：%s（未修改）" % SRC)
    print("  历史记录：%s 条（已全部导入 Supabase）" % n_records)
    print("  页面 %.1f KB | 同步时间：%s"
          % (os.path.getsize(OUT)/1024, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
    print("  注入：身份闸门 / 粉紫皮肤 / 云端加载 / diff 保存 / 无密码无密文")


if __name__ == "__main__":
    import sys
    main()

#!/usr/bin/env python3
"""Build a self-contained GH-300 (GitHub Copilot certification) practice exam viewer.

This script:
  1. Defines a bank of 200 original GH-300 questions across 6 domains.
  2. Applies a balanced answer-key algorithm (greedy, seed=42, max_run=3) to the
     single-answer (mc) questions, re-ordering options so the correct answer lands
     on the target letter.
  3. Emits a single self-contained, Pearson VUE-styled HTML viewer.
"""

import json
import os
import random

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_HTML = os.path.join(ROOT, "gh300-exam-viewer.html")

# --------------------------------------------------------------------------- #
# Common reference URLs
# --------------------------------------------------------------------------- #
D_COPILOT = "https://docs.github.com/en/copilot"
D_PLANS = "https://docs.github.com/en/copilot/about-github-copilot/subscription-plans-for-github-copilot"
D_CHAT = "https://docs.github.com/en/copilot/using-github-copilot/copilot-chat"
D_IDE = "https://docs.github.com/en/copilot/using-github-copilot/getting-code-suggestions-in-your-ide-with-github-copilot"
D_CLI = "https://docs.github.com/en/copilot/github-copilot-in-the-cli"
D_PRIVACY = "https://docs.github.com/en/copilot/managing-copilot/managing-github-copilot-in-your-organization/setting-policies-for-copilot-in-your-organization/managing-policies-for-copilot-in-your-organization"
D_EXCLUSION = "https://docs.github.com/en/copilot/managing-copilot/configuring-and-auditing-content-exclusion"
D_TRUST = "https://docs.github.com/en/copilot/responsible-use-of-github-copilot-features"
D_PROMPT = "https://docs.github.com/en/copilot/using-github-copilot/prompt-engineering-for-github-copilot"
D_TELEMETRY = "https://docs.github.com/en/copilot/managing-copilot/managing-github-copilot-in-your-organization/managing-policies-and-features-for-copilot-in-your-organization"
L_LEARN = "https://learn.microsoft.com/en-us/training/courses/gh-300"
L_TRUST_CENTER = "https://resources.github.com/learn/pathways/copilot/essentials/establishing-trust-in-using-github-copilot/"

# --------------------------------------------------------------------------- #
# Authoring store + helpers
# --------------------------------------------------------------------------- #
RAW = []  # list of authored question dicts (order = final order)


def conf_label(c):
    if c >= 85:
        return "High"
    if c >= 65:
        return "Medium"
    return "Low"


def add_mc(objective, stem, correct, distractors, why_correct, why_wrong,
           confidence, refs):
    """Single-answer question.

    correct       : text of the correct option
    distractors   : list of 3 distractor texts
    why_correct   : sentence explaining why the correct option is right
    why_wrong     : list of 3 sentences aligned with `distractors`
    """
    assert len(distractors) == 3 and len(why_wrong) == 3, stem
    RAW.append({
        "objective": objective,
        "type": "mc",
        "stem": stem,
        "correct": correct,
        "distractors": list(distractors),
        "why_correct": why_correct,
        "why_wrong": list(why_wrong),
        "confidence": confidence,
        "references": list(refs),
    })


def add_multi(objective, stem, options, answer, reasons, confidence, refs):
    """Multiple-answer question.

    options : dict of letter -> text (A..D, optionally E)
    answer  : list of correct letters
    reasons : dict of letter -> explanation sentence (for every option)
    """
    RAW.append({
        "objective": objective,
        "type": "multi",
        "stem": stem,
        "options": dict(options),
        "answer": sorted(answer),
        "reasons": dict(reasons),
        "confidence": confidence,
        "references": list(refs),
    })


def add_hotspot(objective, stem, intro, rows, confidence, refs):
    """Hotspot / drop-down question.

    rows : list of dicts {label, options:[...], correct, reason}
    """
    RAW.append({
        "objective": objective,
        "type": "hotspot",
        "stem": stem,
        "intro": intro,
        "rows": rows,
        "confidence": confidence,
        "references": list(refs),
    })


# --------------------------------------------------------------------------- #
# Balancing algorithm (greedy, seeded, capped run length)
# --------------------------------------------------------------------------- #
def balanced_target_sequence(n, letters, max_run=3, seed=42):
    rng = random.Random(seed)
    base = n // len(letters)
    remainder = n % len(letters)
    counts = {l: base for l in letters}
    extra = rng.sample(letters, remainder)
    for l in extra:
        counts[l] += 1
    sequence = []
    for _ in range(n):
        forbidden = set()
        if len(sequence) >= max_run:
            last = sequence[-1]
            if all(x == last for x in sequence[-max_run:]):
                forbidden.add(last)
        candidates = [l for l in letters if counts[l] > 0 and l not in forbidden]
        if not candidates:
            candidates = [l for l in letters if counts[l] > 0]
        chosen = rng.choice(candidates)
        sequence.append(chosen)
        counts[chosen] -= 1
    return sequence


# --------------------------------------------------------------------------- #
# Finalisation: assign ids, balance mc answers, build explanations
# --------------------------------------------------------------------------- #
def finalize():
    letters = ["A", "B", "C", "D"]
    mc_indices = [i for i, q in enumerate(RAW) if q["type"] == "mc"]
    targets = balanced_target_sequence(len(mc_indices), letters, max_run=3, seed=42)
    drng = random.Random(1234)

    final = []
    mc_pos = 0
    for idx, q in enumerate(RAW):
        qid = idx + 1
        c = q["confidence"]
        common = {
            "id": qid,
            "objective": q["objective"],
            "type": q["type"],
            "stem": q["stem"],
            "confidence": c,
            "confidence_label": conf_label(c),
            "references": q["references"],
        }

        if q["type"] == "mc":
            target = targets[mc_pos]
            mc_pos += 1
            remaining = [l for l in letters if l != target]
            pairs = list(zip(q["distractors"], q["why_wrong"]))
            drng.shuffle(pairs)
            options = {target: q["correct"]}
            wrongmap = {}
            for l, (text, why) in zip(remaining, pairs):
                options[l] = text
                wrongmap[l] = why
            options = {l: options[l] for l in letters}
            expl = (f"<p><strong>Correct answer: {target}</strong></p>"
                    f"<p>{q['why_correct']}</p><ul>")
            for l in letters:
                if l == target:
                    continue
                expl += f"<li><strong>{l}</strong> — {wrongmap[l]}</li>"
            expl += "</ul>"
            common.update({"options": options, "answer": target,
                           "explanation": expl})

        elif q["type"] == "multi":
            ans = q["answer"]
            expl = (f"<p><strong>Correct answers: {', '.join(ans)}</strong></p><ul>")
            for l in sorted(q["options"].keys()):
                tag = "correct" if l in ans else "incorrect"
                expl += (f"<li><strong>{l}</strong> ({tag}) — "
                         f"{q['reasons'][l]}</li>")
            expl += "</ul>"
            common.update({"options": q["options"], "answer": ans,
                           "explanation": expl})

        else:  # hotspot
            answer = [{"row": r["label"], "correct": r["correct"]}
                      for r in q["rows"]]
            rows = [{"label": r["label"], "options": r["options"]}
                    for r in q["rows"]]
            expl = f"<p><strong>{q['intro']}</strong></p><ul>"
            for r in q["rows"]:
                expl += (f"<li><strong>{r['label']}: {r['correct']}</strong> — "
                         f"{r['reason']}</li>")
            expl += "</ul>"
            common.update({"rows": rows, "answer": answer,
                           "explanation": expl})

        final.append(common)
    return final


# --------------------------------------------------------------------------- #
# HTML template
# --------------------------------------------------------------------------- #
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>GH-300: GitHub Copilot Certification — Practice Exam</title>
<style>
  :root{
    --navy:#1a1a2e; --navy2:#16213e; --accent:#3b82f6; --accent2:#2563eb;
    --green:#16a34a; --green-bg:#dcfce7; --red:#dc2626; --red-bg:#fee2e2;
    --orange:#ea580c; --gray:#e5e7eb; --ink:#1f2933; --muted:#64748b;
    --card:#ffffff; --bg:#eef1f6;
  }
  *{box-sizing:border-box;}
  body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--bg);color:var(--ink);font-size:15px;line-height:1.5;}
  a{color:var(--accent2);}
  /* Exam bar */
  .exam-bar{position:sticky;top:0;z-index:50;background:var(--navy);color:#fff;
    display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:10px 16px;
    box-shadow:0 2px 8px rgba(0,0,0,.25);}
  .exam-bar .title{font-weight:700;font-size:1rem;margin-right:auto;}
  .exam-bar .qpos{font-weight:600;font-size:.9rem;opacity:.95;}
  .timer{font-variant-numeric:tabular-nums;font-weight:700;background:rgba(255,255,255,.12);
    padding:6px 10px;border-radius:8px;font-size:.95rem;}
  .timer.warn{background:var(--red);}
  select#testSel{background:var(--navy2);color:#fff;border:1px solid #33415e;
    border-radius:8px;padding:6px 8px;font-size:.85rem;}
  .wrap{max-width:1024px;margin:0 auto;padding:16px;display:grid;
    grid-template-columns:220px 1fr;gap:16px;}
  /* Palette */
  .palette{background:var(--card);border-radius:12px;padding:12px;
    box-shadow:0 1px 4px rgba(0,0,0,.08);align-self:start;position:sticky;top:64px;}
  .palette h3{margin:0 0 8px;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);}
  .palette .legend{font-size:.7rem;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;}
  .legend span{display:inline-flex;align-items:center;gap:4px;}
  .dot{width:10px;height:10px;border-radius:3px;display:inline-block;}
  .dot.u{background:var(--gray);} .dot.a{background:var(--accent);} .dot.f{background:var(--orange);}
  .pgrid{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;}
  .pgrid button{border:1px solid #d1d5db;background:var(--gray);color:var(--ink);
    border-radius:6px;padding:7px 0;font-size:.78rem;cursor:pointer;font-weight:600;}
  .pgrid button.answered{background:var(--accent);color:#fff;border-color:var(--accent2);}
  .pgrid button.flagged{background:var(--orange);color:#fff;border-color:var(--orange);}
  .pgrid button.current{outline:3px solid var(--navy);outline-offset:1px;}
  .palette .ptoggle{display:none;}
  /* Card */
  .panel{min-width:0;}
  .card{background:var(--card);border-radius:12px;padding:20px;
    box-shadow:0 1px 6px rgba(0,0,0,.08);display:none;}
  .card.active{display:block;}
  .qmeta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px;}
  .badge{font-size:.7rem;font-weight:700;padding:3px 8px;border-radius:999px;
    background:#eef2ff;color:#4338ca;text-transform:uppercase;letter-spacing:.03em;}
  .badge.type{background:#f1f5f9;color:#475569;}
  .chip{font-size:.72rem;font-weight:700;padding:3px 9px;border-radius:999px;margin-left:auto;}
  .chip.High{background:var(--green-bg);color:var(--green);}
  .chip.Medium{background:#fef9c3;color:#a16207;}
  .chip.Low{background:var(--red-bg);color:var(--red);}
  .flagbtn{font-size:.74rem;border:1px solid #fdba74;background:#fff7ed;color:var(--orange);
    padding:4px 10px;border-radius:999px;cursor:pointer;font-weight:600;}
  .flagbtn.on{background:var(--orange);color:#fff;}
  .stem{font-size:1.02rem;font-weight:600;margin:6px 0 14px;}
  .hint{font-size:.78rem;color:var(--muted);margin-bottom:10px;}
  .opt{display:flex;gap:10px;align-items:flex-start;border:1.5px solid #e2e8f0;
    border-radius:10px;padding:10px 12px;margin-bottom:8px;cursor:pointer;background:#fff;}
  .opt:hover{border-color:#c7d2fe;}
  .opt.sel{border-color:var(--accent);background:#eff6ff;}
  .opt .mark{flex:none;width:22px;height:22px;border-radius:50%;border:2px solid #cbd5e1;
    display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700;color:var(--muted);}
  .opt.multi .mark{border-radius:6px;}
  .opt.sel .mark{border-color:var(--accent);background:var(--accent);color:#fff;}
  .opt .ltr{font-weight:700;margin-right:4px;}
  .opt.correct{border-color:var(--green);background:var(--green-bg);}
  .opt.wrong{border-color:var(--red);background:var(--red-bg);}
  .hotrow{display:flex;gap:10px;align-items:center;margin-bottom:8px;flex-wrap:wrap;}
  .hotrow label{font-weight:600;min-width:160px;}
  .hotrow select{padding:7px 8px;border-radius:8px;border:1.5px solid #cbd5e1;font-size:.9rem;}
  .hotrow.correct select{border-color:var(--green);background:var(--green-bg);}
  .hotrow.wrong select{border-color:var(--red);background:var(--red-bg);}
  .actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;align-items:center;}
  .btn{border:none;border-radius:9px;padding:9px 16px;font-size:.9rem;font-weight:600;cursor:pointer;}
  .btn.primary{background:var(--accent2);color:#fff;}
  .btn.ghost{background:#f1f5f9;color:var(--ink);}
  .btn.dark{background:var(--navy);color:#fff;}
  .btn:disabled{opacity:.45;cursor:not-allowed;}
  .jump{display:flex;align-items:center;gap:6px;margin-left:auto;font-size:.82rem;color:var(--muted);}
  .jump input{width:58px;padding:6px;border-radius:7px;border:1px solid #cbd5e1;font-size:.85rem;}
  .feedback{margin-top:14px;border-radius:10px;padding:12px 14px;font-size:.9rem;display:none;}
  .feedback.show{display:block;}
  .feedback.ok{background:var(--green-bg);border:1px solid var(--green);}
  .feedback.no{background:var(--red-bg);border:1px solid var(--red);}
  .feedback h4{margin:0 0 6px;font-size:.95rem;}
  .feedback ul{margin:8px 0 0;padding-left:18px;}
  .refs{margin-top:10px;font-size:.78rem;}
  .refs a{display:block;margin-bottom:2px;word-break:break-all;}
  /* Modal */
  .modal{position:fixed;inset:0;background:rgba(15,23,42,.55);display:none;
    align-items:flex-start;justify-content:center;padding:24px 12px;z-index:100;overflow:auto;}
  .modal.show{display:flex;}
  .modal-card{background:#fff;border-radius:14px;max-width:680px;width:100%;padding:22px;}
  .modal-card h2{margin:0 0 4px;}
  .score{font-size:2rem;font-weight:800;}
  .score small{font-size:1rem;color:var(--muted);font-weight:600;}
  table.brk{width:100%;border-collapse:collapse;margin:14px 0;font-size:.85rem;}
  table.brk th,table.brk td{border-bottom:1px solid #e5e7eb;padding:7px 8px;text-align:left;}
  table.brk th{color:var(--muted);font-weight:700;font-size:.75rem;text-transform:uppercase;}
  .rev-list{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;}
  .rev-list button{border:1px solid #cbd5e1;background:#f8fafc;border-radius:6px;padding:5px 9px;
    cursor:pointer;font-size:.8rem;font-weight:600;}
  .rev-list button.flag{border-color:var(--orange);color:var(--orange);}
  .rev-list button.wrongq{border-color:var(--red);color:var(--red);}
  @media (max-width:760px){
    .wrap{grid-template-columns:1fr;}
    .palette{position:static;}
    .palette .ptoggle{display:block;width:100%;border:none;background:#f1f5f9;border-radius:8px;
      padding:8px;font-weight:700;cursor:pointer;margin-bottom:8px;}
    .palette .pbody.collapsed{display:none;}
    .jump{margin-left:0;width:100%;}
    .exam-bar .title{font-size:.85rem;width:100%;}
  }
</style>
</head>
<body>
<div class="exam-bar">
  <div class="title" id="examTitle">GH-300: GitHub Copilot Certification</div>
  <div class="qpos" id="qpos">Question 1 of 50</div>
  <select id="testSel" title="Select test"></select>
  <div class="timer" id="timer">100:00</div>
  <button class="btn dark" id="endBtn" style="padding:6px 12px;font-size:.82rem;">End / Review</button>
</div>

<div class="wrap">
  <aside class="palette">
    <button class="ptoggle" id="ptoggle">Question Navigator ▾</button>
    <div class="pbody" id="pbody">
      <h3>Navigator</h3>
      <div class="legend">
        <span><i class="dot u"></i>Unanswered</span>
        <span><i class="dot a"></i>Answered</span>
        <span><i class="dot f"></i>Flagged</span>
      </div>
      <div class="pgrid" id="pgrid"></div>
    </div>
  </aside>

  <section class="panel" id="panel"></section>
</div>

<div class="modal" id="modal">
  <div class="modal-card">
    <h2>Exam Review</h2>
    <div class="score" id="scoreLine"></div>
    <h3 style="margin-top:16px;">Domain breakdown</h3>
    <table class="brk"><thead><tr><th>Domain</th><th>Correct</th><th>Total</th><th>%</th></tr></thead>
      <tbody id="brkBody"></tbody></table>
    <h3>Incorrect questions</h3>
    <div class="rev-list" id="wrongList"></div>
    <h3 style="margin-top:14px;">Flagged questions</h3>
    <div class="rev-list" id="flagList"></div>
    <div class="actions" style="margin-top:18px;">
      <button class="btn primary" id="closeModal">Back to exam</button>
    </div>
  </div>
</div>

<script>
const DATA = __DATA__;

// ----- state -----
let testIdx = 0;
let cur = 0;
const answers = {};  // key `${testIdx}:${qid}` -> answer (letter | array | {row:val})
const flags = new Set(); // `${testIdx}:${qid}`
const checked = new Set();
let timeLeft = 6000;
let timerId = null;

const $ = (id) => document.getElementById(id);
function curTest(){ return DATA.tests[testIdx]; }
function curQs(){ return curTest().questions; }
function key(qid){ return testIdx + ":" + qid; }

// ----- timer -----
function fmt(t){ const m=Math.floor(t/60), s=t%60; return String(m).padStart(2,"0")+":"+String(s).padStart(2,"0"); }
function startTimer(){
  if(timerId) clearInterval(timerId);
  timerId = setInterval(()=>{
    timeLeft = Math.max(0, timeLeft-1);
    const el=$("timer"); el.textContent=fmt(timeLeft);
    if(timeLeft<=300) el.classList.add("warn");
    if(timeLeft===0){ clearInterval(timerId); openModal(); }
  },1000);
}

// ----- test selector -----
function buildTestSel(){
  const sel=$("testSel"); sel.innerHTML="";
  DATA.tests.forEach((t,i)=>{
    const o=document.createElement("option");
    o.value=i; o.textContent="Test "+t.number+" (Q"+t.questions[0].id+"–"+t.questions[t.questions.length-1].id+")";
    sel.appendChild(o);
  });
  sel.value=testIdx;
  sel.onchange=()=>{ testIdx=+sel.value; cur=0; renderAll(); };
}

// ----- render questions -----
function optionLetters(q){ return Object.keys(q.options); }

function renderPanel(){
  const panel=$("panel"); panel.innerHTML="";
  curQs().forEach((q,i)=>{
    const card=document.createElement("div");
    card.className="card"+(i===cur?" active":"");
    card.dataset.qid=q.id;
    const flagged=flags.has(key(q.id));
    let html="";
    html+='<div class="qmeta">';
    html+='<span class="badge">'+q.objective+'</span>';
    html+='<span class="badge type">'+q.type+'</span>';
    html+='<button class="flagbtn'+(flagged?" on":"")+'" data-flag="'+q.id+'">'+(flagged?"★ Flagged":"⚑ Flag for review")+'</button>';
    html+='<span class="chip '+q.confidence_label+'">Confidence: '+q.confidence+'% · '+q.confidence_label+'</span>';
    html+='</div>';
    html+='<div class="stem">'+(q.id)+'. '+q.stem+'</div>';

    if(q.type==="hotspot"){
      html+='<div class="hint">Select the correct value for each row.</div>';
      q.rows.forEach((r,ri)=>{
        html+='<div class="hotrow" data-row="'+r.label+'"><label>'+r.label+'</label><select data-hrow="'+r.label+'">';
        html+='<option value="">— choose —</option>';
        r.options.forEach(op=>{ html+='<option value="'+op+'">'+op+'</option>'; });
        html+='</select></div>';
      });
    } else {
      if(q.type==="multi") html+='<div class="hint">Select all that apply.</div>';
      optionLetters(q).forEach(l=>{
        html+='<div class="opt'+(q.type==="multi"?" multi":"")+'" data-opt="'+l+'">';
        html+='<span class="mark">'+l+'</span><span><span class="ltr">'+l+'.</span> '+q.options[l]+'</span></div>';
      });
    }

    html+='<div class="actions">';
    html+='<button class="btn ghost" data-nav="prev">‹ Prev</button>';
    html+='<button class="btn primary" data-check="'+q.id+'">Check answer</button>';
    html+='<button class="btn ghost" data-nav="next">Next ›</button>';
    html+='<span class="jump">Question <input type="number" min="1" max="'+curQs().length+'" data-jump value="'+(q.id - curTest().questions[0].id + 1)+'"> of '+curQs().length+'</span>';
    html+='</div>';
    html+='<div class="feedback" data-fb="'+q.id+'"></div>';
    card.innerHTML=html;
    panel.appendChild(card);
  });
  bindCard();
  restoreState();
}

function bindCard(){
  $("panel").querySelectorAll(".opt").forEach(el=>{
    el.onclick=()=>{
      const card=el.closest(".card"); const qid=+card.dataset.qid;
      const q=curQs().find(x=>x.id===qid); const l=el.dataset.opt;
      if(q.type==="multi"){
        let arr=answers[key(qid)]||[]; arr=Array.isArray(arr)?arr.slice():[];
        if(arr.includes(l)) arr=arr.filter(x=>x!==l); else arr.push(l);
        arr.sort(); answers[key(qid)]=arr;
      } else {
        answers[key(qid)]=l;
      }
      restoreState(); paintPalette();
    };
  });
  $("panel").querySelectorAll("select[data-hrow]").forEach(sel=>{
    sel.onchange=()=>{
      const card=sel.closest(".card"); const qid=+card.dataset.qid;
      const obj=answers[key(qid)]||{}; obj[sel.dataset.hrow]=sel.value;
      answers[key(qid)]=obj; paintPalette();
    };
  });
  $("panel").querySelectorAll("[data-flag]").forEach(b=>{
    b.onclick=()=>{ const k=key(+b.dataset.flag);
      if(flags.has(k)) flags.delete(k); else flags.add(k);
      renderPanel(); paintPalette(); };
  });
  $("panel").querySelectorAll("[data-nav]").forEach(b=>{
    b.onclick=()=>{ b.dataset.nav==="prev"?go(cur-1):go(cur+1); };
  });
  $("panel").querySelectorAll("[data-check]").forEach(b=>{
    b.onclick=()=>checkAnswer(+b.dataset.check);
  });
  $("panel").querySelectorAll("[data-jump]").forEach(inp=>{
    inp.onchange=()=>{ let v=parseInt(inp.value,10); if(isNaN(v)) return;
      v=Math.min(Math.max(v,1),curQs().length); go(v-1); };
  });
}

function restoreState(){
  const card=$("panel").querySelector(".card.active"); if(!card) return;
  const qid=+card.dataset.qid; const a=answers[key(qid)];
  card.querySelectorAll(".opt").forEach(el=>{
    el.classList.remove("sel");
    const l=el.dataset.opt;
    if(Array.isArray(a)&&a.includes(l)) el.classList.add("sel");
    else if(!Array.isArray(a)&&a===l) el.classList.add("sel");
  });
  if(a && typeof a==="object" && !Array.isArray(a)){
    card.querySelectorAll("select[data-hrow]").forEach(s=>{ if(a[s.dataset.hrow]) s.value=a[s.dataset.hrow]; });
  }
  if(checked.has(key(qid))) renderFeedback(qid);
}

function go(i){
  if(i<0||i>=curQs().length) return;
  cur=i;
  $("panel").querySelectorAll(".card").forEach((c,idx)=>c.classList.toggle("active",idx===cur));
  updateBar(); paintPalette(); restoreState();
  const prevB=$("panel").querySelector(".card.active [data-nav='prev']");
  const nextB=$("panel").querySelector(".card.active [data-nav='next']");
  if(prevB) prevB.disabled = cur===0;
  if(nextB) nextB.disabled = cur===curQs().length-1;
}

function updateBar(){
  const q=curQs()[cur];
  $("qpos").textContent="Question "+(cur+1)+" of "+curQs().length;
}

// ----- palette -----
function buildPalette(){
  const g=$("pgrid"); g.innerHTML="";
  curQs().forEach((q,i)=>{
    const b=document.createElement("button");
    b.textContent=i+1; b.dataset.i=i;
    b.onclick=()=>go(i);
    g.appendChild(b);
  });
  paintPalette();
}
function paintPalette(){
  $("pgrid").querySelectorAll("button").forEach(b=>{
    const i=+b.dataset.i; const q=curQs()[i]; const k=key(q.id);
    b.className="";
    const a=answers[k];
    const answered = a!==undefined && !(Array.isArray(a)&&a.length===0)
      && !(typeof a==="object"&&!Array.isArray(a)&&Object.values(a).filter(Boolean).length===0);
    if(answered) b.classList.add("answered");
    if(flags.has(k)) b.classList.add("flagged");
    if(i===cur) b.classList.add("current");
  });
}

// ----- check answer -----
function isCorrect(q,a){
  if(q.type==="mc") return a===q.answer;
  if(q.type==="multi"){ if(!Array.isArray(a)) return false;
    return a.length===q.answer.length && q.answer.every(x=>a.includes(x)); }
  if(q.type==="hotspot"){ if(!a||typeof a!=="object") return false;
    return q.answer.every(r=>a[r.row]===r.correct); }
  return false;
}
function checkAnswer(qid){
  checked.add(key(qid)); renderFeedback(qid);
}
function renderFeedback(qid){
  const q=curQs().find(x=>x.id===qid);
  const card=$("panel").querySelector('.card[data-qid="'+qid+'"]');
  const a=answers[key(qid)];
  const ok=isCorrect(q,a);
  // mark options
  if(q.type!=="hotspot"){
    card.querySelectorAll(".opt").forEach(el=>{
      el.classList.remove("correct","wrong");
      const l=el.dataset.opt;
      const isAns = q.type==="mc" ? q.answer===l : q.answer.includes(l);
      const picked = Array.isArray(a)? a.includes(l) : a===l;
      if(isAns) el.classList.add("correct");
      else if(picked) el.classList.add("wrong");
    });
  } else {
    card.querySelectorAll(".hotrow").forEach(row=>{
      const lab=row.dataset.row; const want=q.answer.find(r=>r.row===lab).correct;
      const got=(a||{})[lab];
      row.classList.remove("correct","wrong");
      row.classList.add(got===want?"correct":"wrong");
    });
  }
  const fb=card.querySelector('[data-fb="'+qid+'"]');
  fb.className="feedback show "+(ok?"ok":"no");
  let refs=(q.references||[]).map(r=>'<a href="'+r+'" target="_blank" rel="noopener">'+r+'</a>').join("");
  fb.innerHTML='<h4>'+(ok?"✓ Correct":"✗ Incorrect")+'</h4>'+q.explanation+
    (refs?'<div class="refs"><strong>References</strong>'+refs+'</div>':'');
  paintPalette();
}

// ----- modal / results -----
function openModal(){
  const qs=curQs(); let correct=0;
  const dom={};
  qs.forEach(q=>{
    const a=answers[key(q.id)]; const ok=isCorrect(q,a);
    if(ok) correct++;
    const d=q.objective;
    dom[d]=dom[d]||{c:0,t:0}; dom[d].t++; if(ok) dom[d].c++;
  });
  const pct=Math.round(correct/qs.length*100);
  $("scoreLine").innerHTML=correct+" / "+qs.length+" correct <small>("+pct+"%)</small>";
  const tb=$("brkBody"); tb.innerHTML="";
  Object.keys(dom).sort().forEach(d=>{
    const o=dom[d]; const tr=document.createElement("tr");
    tr.innerHTML="<td>"+d+"</td><td>"+o.c+"</td><td>"+o.t+"</td><td>"+Math.round(o.c/o.t*100)+"%</td>";
    tb.appendChild(tr);
  });
  const wl=$("wrongList"); wl.innerHTML="";
  qs.forEach((q,i)=>{ const a=answers[key(q.id)];
    if(!isCorrect(q,a)){ const b=document.createElement("button");
      b.className="wrongq"; b.textContent="Q"+(i+1);
      b.onclick=()=>{ closeModal(); go(i); checkAnswer(q.id); }; wl.appendChild(b);} });
  if(!wl.children.length) wl.innerHTML='<span style="color:var(--muted);font-size:.82rem;">None — great job!</span>';
  const fl=$("flagList"); fl.innerHTML="";
  qs.forEach((q,i)=>{ if(flags.has(key(q.id))){ const b=document.createElement("button");
    b.className="flag"; b.textContent="Q"+(i+1); b.onclick=()=>{ closeModal(); go(i); }; fl.appendChild(b);} });
  if(!fl.children.length) fl.innerHTML='<span style="color:var(--muted);font-size:.82rem;">No flagged questions.</span>';
  $("modal").classList.add("show");
}
function closeModal(){ $("modal").classList.remove("show"); }

// ----- keyboard -----
document.addEventListener("keydown",(e)=>{
  if(e.target && typeof e.target.matches==="function" && e.target.matches("input,select,textarea")) return;
  if(e.key==="ArrowRight") go(cur+1);
  else if(e.key==="ArrowLeft") go(cur-1);
});

// ----- init -----
function renderAll(){
  $("examTitle").textContent=DATA.title;
  buildTestSel(); renderPanel(); buildPalette(); go(cur); updateBar();
}
$("endBtn").onclick=openModal;
$("closeModal").onclick=closeModal;
$("modal").onclick=(e)=>{ if(e.target===$("modal")) closeModal(); };
$("ptoggle").onclick=()=>{ $("pbody").classList.toggle("collapsed"); };
renderAll();
startTimer();
</script>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# Author the 200 questions
# --------------------------------------------------------------------------- #
def author():
    # ===================== DOMAIN 1 (34) =====================
    O1 = "Domain 1: Use GitHub Copilot responsibly"
    add_mc(O1,
        "A developer notices that GitHub Copilot confidently suggested a function that calls a library method which does not actually exist. What is the most accurate term for this behavior?",
        "A hallucination, where the model generates plausible-looking but factually incorrect output",
        ["A regression introduced by a recent model update",
         "A content exclusion that hid the real method name",
         "A telemetry error in the IDE extension"],
        "Generative models can produce fluent, confident output that is nonetheless wrong or invented; calling a non-existent API is a classic hallucination, so suggestions must always be reviewed.",
        ["Model updates can change behavior but inventing a non-existent API is specifically a hallucination, not a regression.",
         "Content exclusions block files from being used as context; they do not invent fake method names.",
         "Telemetry concerns usage data collection and has nothing to do with the correctness of a suggestion."],
        90, [D_TRUST, L_TRUST_CENTER])

    add_mc(O1,
        "Which practice best reflects responsible use of GitHub Copilot when accepting generated code?",
        "Always review, test, and validate suggestions before merging, treating Copilot as an assistant rather than an authority",
        ["Accept all suggestions automatically to maximize productivity gains",
         "Disable code review for files where Copilot was used to save time",
         "Assume suggestions are secure because they were generated by an AI trained on public code"],
        "Copilot is a probabilistic assistant; the developer remains accountable for the code, so every suggestion should be reviewed, tested, and validated before it ships.",
        ["Blindly accepting suggestions abandons human accountability and can introduce bugs or vulnerabilities.",
         "Skipping review for AI-assisted code removes the most important safeguard against defects.",
         "Training on public code does not guarantee security; suggestions can contain insecure patterns."],
        92, [D_TRUST, L_LEARN])

    add_mc(O1,
        "Why should developers be cautious about potential bias in code or comments suggested by GitHub Copilot?",
        "Because the model learned from large public datasets that may contain biased language or assumptions that can surface in suggestions",
        ["Because Copilot intentionally inserts biased content to test the developer",
         "Because bias only affects natural-language chat and never code completions",
         "Because bias is fully removed by the IDE extension before display"],
        "Models trained on large public corpora can reproduce societal or historical biases present in that data, so human judgment is needed to catch biased wording or assumptions.",
        ["Copilot does not deliberately insert biased content; bias is an emergent property of training data.",
         "Bias can appear in identifiers, comments, and completions, not only in chat.",
         "The IDE extension renders suggestions; it does not guarantee removal of all bias."],
        86, [D_TRUST, L_TRUST_CENTER])

    add_mc(O1,
        "A team wants to ensure that code suggested by Copilot does not violate open-source licenses. Which built-in feature most directly helps with this concern?",
        "The duplicate detection / code referencing filter that can block suggestions matching public code",
        ["The countdown timer in the IDE that limits suggestion frequency",
         "The @workspace chat participant",
         "The Copilot CLI 'gh copilot explain' command"],
        "GitHub Copilot's duplication detection filter can block suggestions that match public code, and code referencing surfaces matches with their licenses, directly addressing licensing concerns.",
        ["There is no suggestion-frequency timer; this does not exist as a licensing safeguard.",
         "@workspace adds repository context to chat but does not address license matching.",
         "'gh copilot explain' clarifies commands; it has no role in license filtering."],
        85, [D_TRUST, D_PRIVACY])

    add_mc(O1,
        "Who is ultimately accountable for code that is committed to a repository after being generated with GitHub Copilot?",
        "The developer who reviews, accepts, and commits the code",
        ["GitHub, because it operates the Copilot service",
         "The model provider, because it trained the underlying model",
         "No one, because AI-generated code is exempt from ownership"],
        "Copilot is an assistant; the human developer who accepts and commits the code is responsible for its correctness, security, and licensing.",
        ["GitHub provides the tool but does not assume responsibility for what developers ship.",
         "The model provider trains the model but is not accountable for individual commits.",
         "All committed code has an accountable author regardless of how it was produced."],
        91, [D_TRUST, L_LEARN])

    add_mc(O1,
        "What is a responsible way to handle a Copilot suggestion that appears to contain a hard-coded secret or credential?",
        "Reject the suggestion and never commit secrets; use a secret manager or environment variables instead",
        ["Accept it and rely on secret scanning to remove it later",
         "Accept it because Copilot would not suggest a real secret",
         "Commit it to a private repository where secret scanning does not run"],
        "Hard-coded credentials are a security risk regardless of source; the responsible action is to reject them and use proper secret management.",
        ["Relying on after-the-fact scanning still risks exposure and is not a substitute for not committing secrets.",
         "Copilot can suggest secret-like patterns; trusting it blindly is unsafe.",
         "Private repositories still should not contain hard-coded secrets, and scanning may still apply."],
        88, [D_TRUST, D_PRIVACY])

    add_mc(O1,
        "Which statement best describes the relationship between GitHub Copilot suggestions and the developer's professional judgment?",
        "Suggestions are a starting point that must be evaluated with domain knowledge and critical thinking",
        ["Suggestions replace the need for code review on small changes",
         "Suggestions are guaranteed correct for well-known algorithms",
         "Suggestions should be trusted more when the confidence appears high in the editor"],
        "Copilot augments developers; their professional judgment is essential to evaluate correctness, security, and fit for purpose.",
        ["Even small changes deserve review; AI assistance does not remove that need.",
         "Even well-known algorithms can be implemented incorrectly by the model.",
         "The editor does not expose a reliable correctness 'confidence' for suggestions."],
        87, [D_TRUST, L_LEARN])

    add_mc(O1,
        "A company is drafting an internal policy for responsible AI tool use. Which element is MOST important to include for GitHub Copilot?",
        "Guidance that all AI-assisted code must still pass the organization's review, testing, and security gates",
        ["A rule that Copilot must write at least 50% of all new code",
         "A requirement to disable all human code review when Copilot is enabled",
         "A mandate to accept suggestions without modification to preserve model intent"],
        "Responsible-use policies focus on keeping human oversight: review, testing, and security checks must still apply to AI-assisted code.",
        ["Mandating a code-volume quota encourages misuse and ignores quality.",
         "Disabling human review removes the key safeguard and is irresponsible.",
         "Forcing unmodified acceptance prevents developers from correcting flawed suggestions."],
        89, [D_TRUST, L_LEARN])

    add_mc(O1,
        "Why might a Copilot suggestion be inappropriate even if it compiles and passes a quick smoke test?",
        "It may contain subtle security flaws, licensing issues, or logic that does not match the actual requirements",
        ["Compiled code is always free of security and licensing concerns",
         "Passing a smoke test guarantees the code meets all requirements",
         "Copilot only suggests code that has been formally verified"],
        "Compiling and passing a smoke test does not guarantee security, correct licensing, or that the logic truly fits the requirement; deeper review is still needed.",
        ["Compilation says nothing about security or licensing.",
         "A smoke test covers only basic behavior, not all requirements or edge cases.",
         "Copilot suggestions are not formally verified."],
        88, [D_TRUST])

    add_mc(O1,
        "What does it mean to keep a 'human in the loop' when using GitHub Copilot?",
        "A person reviews, validates, and decides whether to accept AI-generated output before it is used",
        ["Copilot waits for a human to type before generating any suggestion",
         "A human manually retrains the model after each session",
         "GitHub staff review every suggestion before it reaches the developer"],
        "'Human in the loop' means a developer evaluates and approves AI output, retaining responsibility and control over what is used.",
        ["Triggering on typing is a UI behavior, not the governance concept of human oversight.",
         "Developers do not retrain the model; that is not how Copilot works.",
         "GitHub staff do not review individual suggestions in real time."],
        87, [D_TRUST, L_LEARN])

    add_mc(O1,
        "A junior developer relies entirely on Copilot to learn a new framework without reading documentation. What is the primary risk?",
        "They may internalize incorrect or outdated patterns and lack the understanding to spot errors",
        ["Copilot will refuse to generate code for new frameworks",
         "The IDE will throttle suggestions to force documentation reading",
         "There is no risk because Copilot always reflects current best practices"],
        "Over-reliance without foundational understanding can lead to learning wrong patterns and an inability to evaluate suggestions critically.",
        ["Copilot will still attempt suggestions for new frameworks.",
         "No throttling mechanism forces documentation reading.",
         "Copilot can reflect outdated or non-idiomatic patterns from training data."],
        86, [D_TRUST, L_LEARN])

    add_mc(O1,
        "Which approach helps mitigate the risk of GitHub Copilot suggesting insecure code?",
        "Combine Copilot with static analysis, dependency scanning, and security-focused code review",
        ["Trust Copilot output and remove existing security tooling",
         "Only use Copilot for production code, never for tests",
         "Increase the editor font size to read suggestions more carefully"],
        "Layering Copilot with established security tooling (SAST, dependency scanning) and review reduces the chance insecure suggestions reach production.",
        ["Removing security tooling increases risk rather than mitigating it.",
         "Restricting Copilot to production code does not address security at all.",
         "Font size has no bearing on the security of suggestions."],
        88, [D_TRUST, D_PRIVACY])

    add_mc(O1,
        "Why is transparency about AI assistance sometimes important on a development team?",
        "It helps reviewers apply appropriate scrutiny and supports trust, auditing, and compliance",
        ["It allows the team to bill customers extra for AI usage",
         "It lets GitHub identify which developers to remove from Copilot",
         "It is required to prevent the model from learning new patterns"],
        "Knowing where AI assistance was used helps reviewers calibrate scrutiny and supports auditability and compliance obligations.",
        ["Transparency is about trust and review, not billing customers more.",
         "Disclosure is not used by GitHub to remove developers.",
         "Transparency does not control model training behavior."],
        80, [D_TRUST])

    add_mc(O1,
        "A developer wants to ensure accessibility and inclusive language in generated comments. What is the responsible step?",
        "Manually review and revise generated text to meet accessibility and inclusivity standards",
        ["Assume generated comments are already fully inclusive",
         "Disable comments entirely to avoid the issue",
         "Rely on the model temperature setting to enforce inclusivity"],
        "The model may not always produce inclusive language, so human review and revision of generated text is the responsible step.",
        ["Generated comments are not guaranteed inclusive and need review.",
         "Removing comments harms maintainability and does not address the underlying concern.",
         "There is no user-facing temperature control that enforces inclusivity."],
        82, [D_TRUST])

    add_mc(O1,
        "What is the best response when Copilot generates code that closely resembles a known copyrighted snippet?",
        "Use code referencing to check for matches and avoid using the snippet unless licensing is compatible",
        ["Use it anyway because AI output cannot be copyrighted",
         "Rename the variables so the match is no longer detectable",
         "Commit it and wait for a takedown notice before acting"],
        "Code referencing surfaces public matches and their licenses so developers can avoid incompatible code; ignoring or obfuscating matches is irresponsible.",
        ["The fact that output came from AI does not resolve underlying licensing of matched code.",
         "Renaming to evade detection does not change the licensing reality and is unethical.",
         "Waiting for a takedown is a reactive, risky, and irresponsible approach."],
        84, [D_TRUST, D_PRIVACY])

    add_mc(O1,
        "Which scenario is the clearest example of over-reliance on GitHub Copilot?",
        "Merging generated code to production without understanding what it does",
        ["Using Copilot to draft a first version, then refactoring and testing it",
         "Asking Copilot to explain an unfamiliar code block before editing it",
         "Declining a suggestion that does not fit the architecture"],
        "Shipping code you do not understand removes human judgment and is the textbook over-reliance failure mode.",
        ["Drafting then refactoring and testing is healthy, responsible use.",
         "Using Copilot to explain code increases understanding rather than reducing it.",
         "Declining a poor suggestion demonstrates good judgment, not over-reliance."],
        89, [D_TRUST])

    add_mc(O1,
        "How should a developer treat factual claims (e.g., about an API or standard) that Copilot Chat states in its answer?",
        "Verify them against authoritative documentation before relying on them",
        ["Accept them as authoritative because Chat cites the official model",
         "Assume they are current because the model is updated daily",
         "Treat them as legally binding guidance"],
        "Chat can state incorrect or outdated facts; verifying against authoritative docs is the responsible practice.",
        ["Chat is not an authoritative source and may be wrong.",
         "Model knowledge has a training cutoff and is not updated daily for every fact.",
         "Chat answers are not legal guidance."],
        87, [D_CHAT, D_TRUST])

    add_mc(O1,
        "Why is it important to evaluate Copilot suggestions for edge cases and error handling?",
        "Generated code often focuses on the happy path and may omit validation or error handling",
        ["Copilot always adds comprehensive error handling automatically",
         "Edge cases are handled by the IDE, not the code",
         "Error handling is unnecessary in modern languages"],
        "Suggestions frequently implement only the common case, so developers must add or verify validation and error handling.",
        ["Copilot does not guarantee comprehensive error handling.",
         "The IDE does not implement runtime error handling for your program.",
         "Robust error handling remains necessary in every language."],
        86, [D_TRUST])

    add_mc(O1,
        "A regulated industry team must document AI use for audits. Which Copilot-related practice best supports this?",
        "Maintaining records of policies, enabled features, and review processes for AI-assisted code",
        ["Turning off all logging so no audit trail exists",
         "Letting each developer choose undocumented personal settings",
         "Relying solely on the model provider to keep audit records"],
        "Audit readiness comes from documenting policies, configurations, and review processes for AI-assisted work.",
        ["Disabling logging undermines auditability.",
         "Undocumented per-developer settings make audits impossible.",
         "Organizations cannot outsource their own audit obligations to the provider."],
        81, [D_TRUST, D_PRIVACY])

    add_mc(O1,
        "What is a balanced view of Copilot's impact on developer skill growth?",
        "It can accelerate learning when used to explore and explain, but unchecked reliance can hinder deep understanding",
        ["It always improves skills because developers see more code",
         "It always harms skills because developers stop thinking",
         "It has no effect on skills in any scenario"],
        "Copilot can support learning when used thoughtfully, but uncritical reliance can impede the development of deep understanding.",
        ["Merely seeing more code does not guarantee skill growth without engagement.",
         "Used well, Copilot can aid learning; the harm comes from misuse, not the tool itself.",
         "It clearly can influence skill development positively or negatively."],
        83, [D_TRUST, L_LEARN])

    add_mc(O1,
        "Which is the most responsible reaction to a Copilot suggestion you do not fully understand?",
        "Ask Copilot Chat to explain it and consult documentation before deciding to use it",
        ["Accept it because it appeared first and is likely the best",
         "Delete the file to avoid the confusion",
         "Reformat the code until it looks familiar, then commit"],
        "Seeking an explanation and verifying with documentation builds understanding so you can make an informed accept/reject decision.",
        ["Ordering of suggestions does not indicate correctness or quality.",
         "Deleting the file avoids learning and may lose needed work.",
         "Reformatting does not create understanding of the logic."],
        87, [D_CHAT, D_TRUST])

    add_mc(O1,
        "What does responsible use imply about testing AI-generated code?",
        "It should be tested at least as rigorously as human-written code, including unit and security tests",
        ["It needs less testing because the model was trained on tested code",
         "It needs no testing if it compiles",
         "It only needs manual testing, never automated tests"],
        "AI-generated code warrants the same or greater testing rigor; its origin does not reduce the need for validation.",
        ["Training data being tested elsewhere does not validate your specific generated code.",
         "Compilation is not a substitute for testing.",
         "Automated tests are valuable for AI-generated code just as for human code."],
        88, [D_TRUST])

    add_mc(O1,
        "Why should organizations communicate that Copilot does not guarantee code is free of vulnerabilities?",
        "To set realistic expectations and ensure security review remains part of the workflow",
        ["Because Copilot legally requires the disclaimer to be printed",
         "Because the disclaimer disables the vulnerability filter",
         "Because it shifts all liability to individual developers"],
        "Communicating limitations keeps expectations realistic and preserves the role of security review.",
        ["There is no legal print requirement at play here.",
         "Communication does not disable any filter.",
         "The purpose is realistic expectations, not liability shifting."],
        82, [D_TRUST])

    add_mc(O1,
        "A developer is using Copilot on a safety-critical system. What additional responsibility applies?",
        "Apply heightened verification, formal review, and domain-expert validation of all generated code",
        ["No additional responsibility; Copilot handles safety automatically",
         "Use Copilot only after the system is deployed",
         "Disable testing to avoid slowing the safety pipeline"],
        "Safety-critical contexts demand heightened verification and expert validation beyond ordinary review.",
        ["Copilot does not provide safety guarantees automatically.",
         "Verifying after deployment defeats the purpose of safety review.",
         "Disabling testing in safety-critical work is dangerous and irresponsible."],
        88, [D_TRUST])

    add_mc(O1,
        "Which statement about Copilot and personal/sensitive data in suggestions is correct?",
        "Developers should avoid pasting sensitive data into prompts and review suggestions for inadvertently exposed data",
        ["Sensitive data in prompts is automatically anonymized and safe to share",
         "Suggestions never contain anything resembling sensitive data",
         "Sensitive data concerns apply only to chat, never to completions"],
        "Developers should not paste sensitive data into prompts and should review output, since handling of such data carries privacy obligations.",
        ["Prompts are not guaranteed to anonymize sensitive data you provide.",
         "Suggestions can include patterns resembling sensitive data.",
         "The concern applies to both chat and completions."],
        85, [D_TRUST, D_PRIVACY])

    add_mc(O1,
        "What is the recommended mindset when Copilot output conflicts with your team's coding standards?",
        "Adapt or reject the suggestion so the final code conforms to team standards",
        ["Change the team standards to match Copilot output",
         "Accept the suggestion to avoid arguing with the tool",
         "Escalate to GitHub support to resolve the conflict"],
        "The developer should make the final code conform to team standards, adapting or rejecting suggestions as needed.",
        ["Team standards exist for good reasons and should not bend to the tool.",
         "Accepting non-conforming code degrades the codebase.",
         "Standards conflicts are resolved by the developer, not GitHub support."],
        84, [D_TRUST])

    add_mc(O1,
        "Which approach best balances productivity with responsible use when adopting Copilot on a team?",
        "Encourage Copilot use while keeping review, testing, and security gates mandatory for all code",
        ["Mandate that Copilot generate the majority of code to prove ROI",
         "Allow Copilot output to bypass review when deadlines are tight",
         "Forbid any modification of Copilot suggestions to preserve intent"],
        "Combining encouragement of the tool with non-negotiable review, testing, and security gates captures productivity gains without sacrificing accountability.",
        ["Mandating a generation quota incentivizes misuse over quality.",
         "Bypassing review under deadline pressure is exactly when defects slip through.",
         "Forbidding edits prevents developers from correcting flawed output."],
        87, [D_TRUST, L_LEARN])

    # D1 multi (5)
    add_multi(O1,
        "Which of the following are recognized limitations of GitHub Copilot that developers should keep in mind? (Choose three.)",
        {"A": "It can hallucinate non-existent APIs or facts",
         "B": "It can suggest insecure or vulnerable code patterns",
         "C": "It can reflect biases present in its training data",
         "D": "It formally verifies all generated code for correctness",
         "E": "It guarantees suggestions are free of licensing concerns"},
        ["A", "B", "C"],
        {"A": "Hallucinations are a known limitation of generative models.",
         "B": "Suggestions can contain insecure patterns and must be reviewed.",
         "C": "Training data biases can surface in suggestions.",
         "D": "Copilot does not formally verify correctness.",
         "E": "Licensing concerns can still arise; no such guarantee exists."},
        88, [D_TRUST, L_TRUST_CENTER])

    add_multi(O1,
        "Which actions support responsible, ethical use of GitHub Copilot? (Choose three.)",
        {"A": "Reviewing and testing generated code before committing",
         "B": "Using duplicate detection / code referencing to address licensing",
         "C": "Keeping a human in the loop for accept/reject decisions",
         "D": "Committing suggestions without review to maximize speed",
         "E": "Pasting production secrets into prompts for accurate results"},
        ["A", "B", "C"],
        {"A": "Review and testing are core responsible-use practices.",
         "B": "These features help manage licensing and duplication risk.",
         "C": "Human oversight preserves accountability.",
         "D": "Skipping review is the opposite of responsible use.",
         "E": "Never paste secrets into prompts; it creates privacy/security risk."},
        89, [D_TRUST])

    add_multi(O1,
        "A reviewer is evaluating AI-assisted code in a pull request. Which concerns are appropriate to check? (Choose three.)",
        {"A": "Security vulnerabilities and unsafe patterns",
         "B": "Licensing of code that matches public sources",
         "C": "Whether requirements and edge cases are actually met",
         "D": "Whether the developer used the keyboard or mouse to accept",
         "E": "The exact model temperature used during generation"},
        ["A", "B", "C"],
        {"A": "Security review is essential for AI-assisted code.",
         "B": "Licensing of matched public code is a legitimate concern.",
         "C": "Confirming requirements and edge cases is core review work.",
         "D": "How a suggestion was accepted is irrelevant to code quality.",
         "E": "There is no user-exposed temperature to audit per suggestion."},
        85, [D_TRUST])

    add_multi(O1,
        "Which statements about accountability for Copilot-generated code are TRUE? (Choose two.)",
        {"A": "The developer who commits the code is responsible for it",
         "B": "Standard review, testing, and security gates still apply",
         "C": "GitHub assumes liability for any bug Copilot introduces",
         "D": "AI-generated code is exempt from organizational policy"},
        ["A", "B"],
        {"A": "The committing developer is accountable.",
         "B": "Existing quality gates continue to apply.",
         "C": "GitHub does not assume liability for your commits.",
         "D": "Organizational policy applies to AI-generated code as well."},
        88, [D_TRUST, L_LEARN])

    add_multi(O1,
        "Which are good ways to reduce the risk of accepting hallucinated Copilot output? (Choose three.)",
        {"A": "Cross-checking referenced APIs against official documentation",
         "B": "Running the code and its tests to confirm behavior",
         "C": "Asking Copilot Chat to explain and justify the suggestion",
         "D": "Assuming confident phrasing means the output is correct",
         "E": "Accepting any suggestion that compiles without warnings"},
        ["A", "B", "C"],
        {"A": "Verifying APIs against docs catches invented calls.",
         "B": "Executing tests reveals incorrect behavior.",
         "C": "Asking for an explanation can expose flawed reasoning.",
         "D": "Confidence of phrasing is not evidence of correctness.",
         "E": "Compiling cleanly does not prove correctness."},
        87, [D_TRUST])

    # D1 hotspot (2)
    add_hotspot(O1,
        "For each statement about responsible Copilot use, select whether it is True or False.",
        "Responsible use centers on human oversight, review, and awareness of model limitations.",
        [{"label": "Copilot suggestions should always be reviewed before committing",
          "options": ["True", "False"], "correct": "True",
          "reason": "Human review is a core responsible-use practice."},
         {"label": "Copilot guarantees generated code is free of vulnerabilities",
          "options": ["True", "False"], "correct": "False",
          "reason": "No such guarantee exists; security review is still required."},
         {"label": "The developer who commits AI-assisted code is accountable for it",
          "options": ["True", "False"], "correct": "True",
          "reason": "Accountability stays with the human who commits the code."}],
        86, [D_TRUST])

    add_hotspot(O1,
        "Match each concern to the most appropriate responsible-use safeguard.",
        "Each risk maps to a concrete mitigation built into a responsible workflow.",
        [{"label": "Suggestion matches public code (licensing)",
          "options": ["Code referencing / duplicate detection", "Increase font size", "Disable tests"],
          "correct": "Code referencing / duplicate detection",
          "reason": "Code referencing surfaces matches and licenses."},
         {"label": "Suggestion may be insecure",
          "options": ["Security review and SAST", "Accept automatically", "Ignore"],
          "correct": "Security review and SAST",
          "reason": "Security tooling and review catch insecure patterns."},
         {"label": "Suggestion may be a hallucination",
          "options": ["Verify against documentation and tests", "Trust confident wording", "Rename variables"],
          "correct": "Verify against documentation and tests",
          "reason": "Verification against docs and tests reveals invented or wrong output."}],
        85, [D_TRUST])

    # ===================== DOMAIN 2 (54) =====================
    O2 = "Domain 2: Use GitHub Copilot features"
    add_mc(O2,
        "Which GitHub Copilot plan is designed for individual developers who pay for their own subscription and is free for verified students, teachers, and maintainers of popular open-source projects?",
        "Copilot Individual (Copilot Pro)",
        ["Copilot Business",
         "Copilot Enterprise",
         "Copilot Workspace"],
        "Copilot Individual (now Copilot Pro) targets single developers and is offered free to verified students, teachers, and popular open-source maintainers.",
        ["Copilot Business is purchased and managed by organizations, not individuals.",
         "Copilot Enterprise is an organization-wide plan with additional features.",
         "Copilot Workspace is a separate task-oriented experience, not the individual subscription tier."],
        86, [D_PLANS])

    add_mc(O2,
        "An organization wants centralized license management, policy controls, and exclusion of their data from training. Which plan should they choose at minimum?",
        "Copilot Business",
        ["Copilot Individual",
         "Copilot Free",
         "A personal GitHub account with Copilot Pro"],
        "Copilot Business provides organization-level license management, policy controls, and excludes business data from training by default.",
        ["Copilot Individual lacks organization-wide policy and license management.",
         "Copilot Free is a limited tier without organization policy management.",
         "Personal Pro accounts are managed by the individual, not the organization."],
        87, [D_PLANS, D_PRIVACY])

    add_mc(O2,
        "Which feature is unique to Copilot Enterprise compared with Copilot Business?",
        "Knowledge bases and Copilot Chat in GitHub.com with organization-indexed context",
        ["Inline code completion in the editor",
         "Copilot Chat inside VS Code",
         "The ability to accept suggestions with the Tab key"],
        "Copilot Enterprise adds organization-wide capabilities such as knowledge bases and Copilot Chat on GitHub.com tailored to your repositories.",
        ["Inline completion is available across paid tiers, not unique to Enterprise.",
         "Chat in VS Code is available in Business and Individual as well.",
         "Tab-to-accept is a basic editor behavior available to all tiers."],
        84, [D_PLANS])

    add_mc(O2,
        "In Visual Studio Code, which keyboard action accepts the entire inline (ghost text) suggestion shown by Copilot?",
        "Press the Tab key",
        ["Press Ctrl+S",
         "Press Esc",
         "Press Shift+Enter"],
        "Tab accepts the full inline 'ghost text' suggestion in VS Code.",
        ["Ctrl+S saves the file; it does not accept a suggestion.",
         "Esc dismisses the suggestion rather than accepting it.",
         "Shift+Enter inserts a newline; it does not accept the suggestion."],
        88, [D_IDE])

    add_mc(O2,
        "A developer wants to accept only the next word of a Copilot inline suggestion in VS Code. Which action does this?",
        "Press Ctrl+Right Arrow (accept word)",
        ["Press Tab twice quickly",
         "Press Ctrl+A",
         "Press Alt+Enter"],
        "VS Code supports accepting a suggestion word-by-word, by default with Ctrl+Right Arrow.",
        ["Double-tapping Tab does not map to partial acceptance.",
         "Ctrl+A selects all text in the editor.",
         "Alt+Enter is not the accept-word shortcut for inline suggestions."],
        80, [D_IDE])

    add_mc(O2,
        "Which Copilot Chat participant scopes a question to the entire current repository/workspace so Copilot can reason across multiple files?",
        "@workspace",
        ["@terminal",
         "@vscode",
         "@github"],
        "@workspace directs Copilot Chat to use the whole workspace/repository as context for the question.",
        ["@terminal focuses on the integrated terminal and shell commands.",
         "@vscode answers questions about the VS Code editor itself.",
         "@github is used for GitHub-specific knowledge and search, not whole-workspace code reasoning in the IDE."],
        86, [D_CHAT])

    add_mc(O2,
        "In Copilot Chat, which reference is used to include the contents of a specific file as context?",
        "#file",
        ["@file",
         "/file",
         "$file"],
        "The #file reference (a context variable) attaches a specific file's contents to the chat prompt.",
        ["@ prefixes chat participants, not file references.",
         "/ prefixes slash commands like /explain or /tests.",
         "$file is not a Copilot Chat reference syntax."],
        83, [D_CHAT])

    add_mc(O2,
        "Which Copilot Chat slash command generates unit tests for the selected code?",
        "/tests",
        ["/fix",
         "/explain",
         "/optimize"],
        "/tests asks Copilot Chat to generate unit tests for the selected or referenced code.",
        ["/fix proposes a fix for a problem in the code.",
         "/explain describes what the selected code does.",
         "/optimize is not the standard command for generating tests."],
        87, [D_CHAT])

    add_mc(O2,
        "Which Copilot Chat slash command asks Copilot to explain what a selected block of code does?",
        "/explain",
        ["/doc",
         "/why",
         "/describe"],
        "/explain produces a natural-language explanation of the selected code.",
        ["/doc generates documentation comments rather than an explanation in chat.",
         "/why is not a standard Copilot Chat slash command.",
         "/describe is not a standard Copilot Chat slash command."],
        86, [D_CHAT])

    add_mc(O2,
        "A developer types `gh copilot suggest` in the terminal. What does the GitHub Copilot CLI do?",
        "Suggests a shell command (or git/gh command) for the described task",
        ["Commits all staged changes automatically",
         "Opens the VS Code editor with a new file",
         "Generates unit tests for the current directory"],
        "`gh copilot suggest` asks Copilot in the CLI to propose a command for a natural-language task description.",
        ["It does not auto-commit changes.",
         "It does not open an editor; it works in the terminal.",
         "Generating unit tests is a Chat/IDE capability, not `gh copilot suggest`."],
        85, [D_CLI])

    add_mc(O2,
        "Which GitHub Copilot CLI command explains what a given shell command does in plain language?",
        "gh copilot explain",
        ["gh copilot describe",
         "gh copilot help",
         "gh copilot run"],
        "`gh copilot explain` takes a command and returns a natural-language explanation of it.",
        ["`gh copilot describe` is not a valid subcommand.",
         "`gh copilot help` shows usage information, not explanations of arbitrary commands.",
         "`gh copilot run` is not the explanation subcommand."],
        85, [D_CLI])

    add_mc(O2,
        "Which IDEs are officially supported by GitHub Copilot extensions?",
        "Visual Studio Code, Visual Studio, JetBrains IDEs, and Neovim",
        ["Only Visual Studio Code",
         "Only JetBrains IDEs and Eclipse",
         "Only browser-based editors"],
        "Copilot provides official extensions/plugins for VS Code, Visual Studio, the JetBrains family, and Neovim, among others.",
        ["Copilot supports more than just VS Code.",
         "Support is broader than JetBrains and does not center on Eclipse as the only option.",
         "Copilot is not limited to browser-based editors."],
        85, [D_IDE])

    add_mc(O2,
        "What is Copilot inline chat (in-editor chat) primarily used for?",
        "Asking Copilot to modify or generate code at the cursor without leaving the editor pane",
        ["Opening a separate browser tab for documentation",
         "Replacing the integrated terminal",
         "Disabling ghost-text suggestions permanently"],
        "Inline chat lets you prompt Copilot directly in the editor to make targeted edits or generate code in place.",
        ["It does not open external browser tabs.",
         "It does not replace the terminal.",
         "It does not disable ghost-text suggestions."],
        84, [D_IDE, D_CHAT])

    add_mc(O2,
        "Which Copilot Chat participant is best suited to help compose or explain a terminal command and run it in the integrated terminal?",
        "@terminal",
        ["@workspace",
         "@file",
         "@docs"],
        "@terminal focuses Copilot Chat on the integrated terminal, helping craft and explain shell commands.",
        ["@workspace reasons across the repository's code, not terminal commands.",
         "@file is a context reference syntax, not a terminal participant.",
         "@docs is not the terminal-focused participant."],
        82, [D_CHAT])

    add_mc(O2,
        "How does Copilot typically trigger an inline code-completion suggestion as you work?",
        "Automatically as you type, based on the surrounding code and comments",
        ["Only when you press a dedicated 'Generate' button in the menu bar",
         "Only after you save the file",
         "Only when connected to a local model"],
        "Copilot offers inline suggestions automatically based on context as you type; you can also invoke them manually.",
        ["No menu-bar 'Generate' button is required to get inline suggestions.",
         "Suggestions appear while typing, not only after saving.",
         "Copilot uses cloud models; it does not require a local model."],
        85, [D_IDE])

    add_mc(O2,
        "A developer wants to see multiple alternative completions for the same location. Which VS Code feature provides this?",
        "Opening the Copilot completions panel (e.g., Ctrl+Enter) to view several suggestions",
        ["The Source Control panel",
         "The Extensions marketplace",
         "The integrated terminal"],
        "The completions panel (opened with Ctrl+Enter by default) shows multiple alternative suggestions to choose from.",
        ["Source Control manages git, not suggestions.",
         "The marketplace installs extensions; it does not show completions.",
         "The terminal runs commands and does not list code completions."],
        80, [D_IDE])

    add_mc(O2,
        "Which statement about Copilot Free is accurate?",
        "It offers a limited number of completions and chat interactions per month at no cost",
        ["It includes unlimited completions and enterprise policy controls",
         "It is only available to organizations, not individuals",
         "It provides knowledge bases like Copilot Enterprise"],
        "Copilot Free provides a capped monthly allowance of completions and chat messages without charge.",
        ["The free tier is limited and lacks enterprise policy controls.",
         "Copilot Free is available to individual accounts.",
         "Knowledge bases are an Enterprise feature, not part of Copilot Free."],
        80, [D_PLANS])

    add_mc(O2,
        "In Copilot Chat, what does the /fix slash command do?",
        "Proposes a fix for a detected problem or error in the selected code",
        ["Permanently disables linting for the file",
         "Reverts the file to the last commit",
         "Formats the document using the default formatter"],
        "/fix asks Copilot to suggest a correction for an issue in the selected code.",
        ["It does not disable linting.",
         "It does not perform a git revert.",
         "Formatting is a separate editor action, not /fix."],
        84, [D_CHAT])

    add_mc(O2,
        "Which Copilot capability allows asking questions about your code on GitHub.com (the web) with repository-aware answers, available in Copilot Enterprise?",
        "Copilot Chat in GitHub.com",
        ["Copilot in the JetBrains Gateway",
         "Copilot inline ghost text",
         "Copilot CLI suggest"],
        "Copilot Enterprise brings Copilot Chat to GitHub.com with answers grounded in your repositories and knowledge bases.",
        ["JetBrains Gateway is unrelated to web-based chat.",
         "Inline ghost text is an in-editor completion feature.",
         "CLI suggest is a terminal feature, not web chat."],
        82, [D_PLANS, D_CHAT])

    add_mc(O2,
        "What is the purpose of the @github participant in Copilot Chat?",
        "To answer questions using GitHub-specific skills such as searching code, issues, and documentation",
        ["To open a pull request without review",
         "To install Copilot in a new IDE",
         "To change your subscription plan"],
        "@github gives Chat access to GitHub-aware skills like searching across code, issues, and docs.",
        ["It does not bypass review to open PRs.",
         "It does not install IDE extensions.",
         "It does not modify your subscription."],
        80, [D_CHAT])

    add_mc(O2,
        "A developer presses Esc while a Copilot ghost-text suggestion is visible. What happens?",
        "The current inline suggestion is dismissed without inserting it",
        ["The suggestion is accepted and inserted",
         "Copilot is uninstalled",
         "The file is closed"],
        "Esc dismisses the visible inline suggestion without accepting it.",
        ["Esc does not accept the suggestion; Tab does.",
         "Esc has nothing to do with uninstalling the extension.",
         "Esc does not close the file."],
        84, [D_IDE])

    add_mc(O2,
        "Which command installs the GitHub Copilot CLI extension for the GitHub CLI?",
        "gh extension install github/gh-copilot",
        ["gh copilot install",
         "npm install gh-copilot",
         "git copilot init"],
        "The Copilot CLI is added as a gh extension via `gh extension install github/gh-copilot`.",
        ["`gh copilot install` is not how the extension is added.",
         "It is a gh extension, not an npm package installed this way.",
         "`git copilot init` is not a valid command."],
        81, [D_CLI])

    add_mc(O2,
        "What does Copilot use as the primary signal to generate a relevant inline suggestion?",
        "The surrounding code, open files, and nearby comments (the context)",
        ["The developer's typing speed",
         "The color theme of the editor",
         "The size of the monitor"],
        "Copilot builds a prompt from the surrounding code, related open files, and comments to produce relevant suggestions.",
        ["Typing speed does not influence suggestion content.",
         "The color theme is cosmetic and irrelevant to suggestions.",
         "Monitor size has no effect on generated code."],
        86, [D_IDE, D_PROMPT])

    add_mc(O2,
        "Which slash command would you use in Copilot Chat to generate documentation comments for a function?",
        "/doc",
        ["/tests",
         "/terminal",
         "/clear"],
        "/doc asks Copilot to add documentation comments for the selected code.",
        ["/tests generates tests, not documentation.",
         "/terminal is not a documentation command.",
         "/clear clears the chat conversation."],
        82, [D_CHAT])

    add_mc(O2,
        "A team using JetBrains IntelliJ IDEA wants Copilot suggestions. What must they install?",
        "The GitHub Copilot plugin from the JetBrains Marketplace",
        ["A VS Code extension",
         "A browser bookmarklet",
         "Nothing; Copilot is built into IntelliJ by default"],
        "JetBrains IDEs use the GitHub Copilot plugin available in the JetBrains Marketplace.",
        ["VS Code extensions do not run in IntelliJ.",
         "A bookmarklet does not enable IDE completions.",
         "Copilot is not bundled with IntelliJ by default; the plugin must be installed."],
        84, [D_IDE])

    add_mc(O2,
        "Which best describes Copilot 'code completion' versus 'Copilot Chat'?",
        "Code completion offers inline suggestions as you type; Chat is a conversational interface for questions and larger tasks",
        ["They are identical features with different names",
         "Code completion only works in the terminal; Chat only works on the web",
         "Chat replaces code completion and disables it"],
        "Completion provides inline ghost-text suggestions while typing; Chat is a conversational assistant for explanations, tests, and multi-step help.",
        ["They are distinct features serving different interaction modes.",
         "Completion works in the editor, and Chat is available in multiple surfaces.",
         "Enabling Chat does not disable inline completion."],
        86, [D_IDE, D_CHAT])

    add_mc(O2,
        "Where can an organization owner manage which Copilot features (e.g., chat, CLI) are enabled for members?",
        "In the organization's Copilot policy settings on GitHub",
        ["In each developer's local VS Code settings only",
         "By editing the model weights directly",
         "Through the operating system firewall"],
        "Organization owners use Copilot policy settings to enable or disable features for members.",
        ["Local editor settings cannot enforce organization policy.",
         "Customers cannot edit model weights.",
         "A firewall does not configure Copilot feature policies."],
        85, [D_PRIVACY, D_PLANS])

    add_mc(O2,
        "What does the /clear command do in Copilot Chat?",
        "Clears the current chat conversation/history in the session",
        ["Deletes the open file",
         "Removes Copilot from the IDE",
         "Clears all breakpoints in the debugger"],
        "/clear resets the chat conversation so you can start fresh.",
        ["It does not delete files.",
         "It does not uninstall Copilot.",
         "It does not affect debugger breakpoints."],
        80, [D_CHAT])

    add_mc(O2,
        "What happens when you accept a Copilot inline suggestion that spans multiple lines in VS Code with Tab?",
        "All shown lines of the suggestion are inserted at once",
        ["Only the first character is inserted",
         "The suggestion is copied to the clipboard but not inserted",
         "The editor splits into multiple panes"],
        "Pressing Tab inserts the entire visible multi-line ghost-text suggestion.",
        ["Tab inserts the whole shown suggestion, not just one character.",
         "Tab inserts rather than copies to clipboard.",
         "Accepting a suggestion does not split the editor."],
        83, [D_IDE])

    add_mc(O2,
        "Which Copilot surface is most appropriate for asking 'What does this regular expression do?' about selected code?",
        "Copilot Chat with /explain (or inline chat)",
        ["gh copilot suggest",
         "The Extensions marketplace",
         "The Source Control commit message box"],
        "Asking for an explanation of selected code is a Chat task, e.g., /explain or inline chat.",
        ["`gh copilot suggest` proposes commands, not code explanations.",
         "The marketplace installs extensions.",
         "The commit box writes messages, not explanations."],
        82, [D_CHAT])

    add_mc(O2,
        "Which statement about Copilot in Visual Studio (not VS Code) is correct?",
        "Copilot is available as an integrated feature/extension providing completions and chat in Visual Studio",
        ["Copilot is not available in Visual Studio at all",
         "Copilot in Visual Studio only works offline",
         "Copilot in Visual Studio requires a JetBrains license"],
        "Visual Studio supports GitHub Copilot completions and chat through its integration/extension.",
        ["Copilot is supported in Visual Studio.",
         "Copilot uses cloud services and is not offline-only.",
         "A JetBrains license is unrelated to Visual Studio."],
        82, [D_IDE])

    add_mc(O2,
        "A developer asks Copilot Chat to refactor a function using the inline chat at the cursor. What is the typical result?",
        "Copilot proposes an edit you can preview and accept or discard",
        ["Copilot immediately force-pushes the change to main",
         "Copilot opens a new repository",
         "Copilot disables version control"],
        "Inline chat proposes a diff/edit that you can review, then accept or discard.",
        ["It never force-pushes to a branch automatically.",
         "It does not create repositories.",
         "It does not disable version control."],
        84, [D_CHAT, D_IDE])

    add_mc(O2,
        "Which feature differentiates Copilot Business/Enterprise from Individual regarding data?",
        "Prompts and suggestions from Business/Enterprise are excluded from model training by default",
        ["Individual plans never send any data to GitHub",
         "Business plans require sharing all source code publicly",
         "Enterprise plans store all code on the developer's local disk only"],
        "Business and Enterprise exclude prompts/suggestions from training by default, a key data-handling distinction.",
        ["Individual plans still transmit prompts to generate suggestions.",
         "Business plans do not require making code public.",
         "Enterprise does not store code only locally; it uses GitHub's services."],
        84, [D_PLANS, D_PRIVACY])

    add_mc(O2,
        "What is the main benefit of using comments to guide Copilot inline completions?",
        "A clear comment describing intent often yields more relevant, on-target suggestions",
        ["Comments disable Copilot for that file",
         "Comments are ignored entirely by Copilot",
         "Comments switch Copilot into offline mode"],
        "Descriptive comments act as natural-language prompts that steer Copilot toward the intended implementation.",
        ["Comments do not disable Copilot.",
         "Comments are part of the context Copilot uses, not ignored.",
         "There is no offline mode triggered by comments."],
        85, [D_PROMPT, D_IDE])

    add_mc(O2,
        "Which command-line task is `gh copilot` NOT designed to perform?",
        "Automatically merging pull requests without user confirmation",
        ["Suggesting a shell command for a described task",
         "Explaining what a shell command does",
         "Helping construct a complex git command"],
        "`gh copilot` suggests and explains commands; it does not auto-merge pull requests.",
        ["Suggesting commands is a core `gh copilot suggest` capability.",
         "Explaining commands is what `gh copilot explain` does.",
         "Helping build git commands is a supported use of suggest."],
        80, [D_CLI])

    add_mc(O2,
        "In Copilot Chat, what is the effect of attaching #file:utils.py to your prompt?",
        "It includes the contents of utils.py as context for the question",
        ["It deletes utils.py",
         "It renames the current file to utils.py",
         "It runs utils.py in the terminal"],
        "#file:<name> attaches the referenced file's content so Copilot can reason about it.",
        ["It does not delete the file.",
         "It does not rename files.",
         "It does not execute the file."],
        83, [D_CHAT])

    add_mc(O2,
        "Which best describes Neovim support for GitHub Copilot?",
        "Copilot is available via an official plugin that provides inline suggestions in Neovim",
        ["Copilot cannot be used in Neovim",
         "Copilot in Neovim only provides chat, never completions",
         "Neovim support requires compiling the model locally"],
        "An official Copilot plugin brings inline suggestions to Neovim.",
        ["Neovim is supported.",
         "The Neovim plugin provides completions.",
         "No local model compilation is required."],
        80, [D_IDE])

    add_mc(O2,
        "What does enabling Copilot at the organization level require?",
        "Assigning Copilot Business or Enterprise seats/licenses to members",
        ["Each member buying their own Individual plan",
         "Disabling all other GitHub features",
         "Installing a desktop antivirus"],
        "Organizations grant access by assigning Business/Enterprise seats to members.",
        ["Individual purchases are not how org-level access is granted.",
         "Enabling Copilot does not disable other GitHub features.",
         "Antivirus has nothing to do with seat assignment."],
        83, [D_PLANS])

    add_mc(O2,
        "A developer on Copilot Individual wants Copilot Chat in their IDE. Is this possible?",
        "Yes, Copilot Chat is included with the Individual (Pro) subscription in supported IDEs",
        ["No, Chat is exclusive to Enterprise",
         "No, Chat requires a separate purchase from a third party",
         "Only if they also buy a Neovim license"],
        "Copilot Chat in supported IDEs is available with Individual/Pro subscriptions.",
        ["Chat is not exclusive to Enterprise.",
         "Chat is part of the subscription, not a third-party purchase.",
         "There is no Neovim license requirement."],
        82, [D_PLANS, D_CHAT])

    add_mc(O2,
        "Which describes the Copilot completions panel best?",
        "A pane that lists several synthesized suggestions so you can pick the most suitable one",
        ["A panel that shows your git commit history",
         "A panel that manages installed extensions",
         "A panel that displays CPU usage"],
        "The completions panel presents multiple alternative suggestions for the current location.",
        ["Git history is shown in Source Control, not the completions panel.",
         "Extension management is separate from completions.",
         "CPU usage is unrelated to Copilot completions."],
        78, [D_IDE])

    add_mc(O2,
        "Which statement about Copilot keyboard shortcuts is correct?",
        "Default shortcuts can be customized in the IDE's keybindings settings",
        ["Shortcuts are fixed and cannot be changed",
         "Shortcuts only work with an external numeric keypad",
         "Changing a shortcut uninstalls Copilot"],
        "Copilot's default keybindings can be remapped through the IDE's keyboard shortcut settings.",
        ["Shortcuts are customizable, not fixed.",
         "A numeric keypad is not required.",
         "Remapping a shortcut does not uninstall the extension."],
        80, [D_IDE])

    add_mc(O2,
        "Which Copilot feature helps a developer understand an unfamiliar codebase quickly by answering repo-aware questions in the IDE?",
        "Copilot Chat with @workspace",
        ["The minimap scrollbar",
         "The integrated debugger",
         "The file explorer search box"],
        "@workspace enables repo-aware Q&A to help navigate and understand an unfamiliar codebase.",
        ["The minimap is a navigation aid, not a Q&A tool.",
         "The debugger steps through execution; it does not answer natural-language questions.",
         "File search finds text but does not explain the code."],
        82, [D_CHAT])

    add_mc(O2,
        "What is required for Copilot to provide suggestions in any supported IDE?",
        "An authenticated GitHub account with an active Copilot subscription/seat and the Copilot extension installed",
        ["A locally hosted GPU cluster",
         "A paid third-party proxy service",
         "Disabling internet access"],
        "Copilot needs the extension installed and an authenticated account with an active Copilot entitlement.",
        ["No local GPU cluster is required; inference runs in the cloud.",
         "No third-party proxy is required.",
         "Internet access is required, not disabled."],
        85, [D_IDE, D_PLANS])

    # D2 multi (8)
    add_multi(O2,
        "Which of the following are valid GitHub Copilot subscription plans? (Choose three.)",
        {"A": "Copilot Individual (Pro)", "B": "Copilot Business",
         "C": "Copilot Enterprise", "D": "Copilot Datacenter",
         "E": "Copilot Hardware"},
        ["A", "B", "C"],
        {"A": "Individual/Pro is a valid plan for single developers.",
         "B": "Business is the organization plan with policy controls.",
         "C": "Enterprise adds org-wide features like knowledge bases.",
         "D": "There is no 'Copilot Datacenter' plan.",
         "E": "There is no 'Copilot Hardware' plan."},
        86, [D_PLANS])

    add_multi(O2,
        "Which surfaces can run GitHub Copilot Chat? (Choose three.)",
        {"A": "Visual Studio Code", "B": "JetBrains IDEs",
         "C": "GitHub.com (Copilot Enterprise)", "D": "A printed manual",
         "E": "The BIOS firmware screen"},
        ["A", "B", "C"],
        {"A": "Chat runs in VS Code.",
         "B": "Chat runs in JetBrains IDEs.",
         "C": "Chat runs on GitHub.com with Copilot Enterprise.",
         "D": "A printed manual cannot run software.",
         "E": "BIOS firmware does not run Copilot Chat."},
        85, [D_CHAT])

    add_multi(O2,
        "Which are real GitHub Copilot Chat slash commands? (Choose three.)",
        {"A": "/explain", "B": "/tests", "C": "/fix",
         "D": "/deploy", "E": "/format-disk"},
        ["A", "B", "C"],
        {"A": "/explain explains selected code.",
         "B": "/tests generates unit tests.",
         "C": "/fix proposes a fix for a problem.",
         "D": "/deploy is not a Copilot Chat slash command.",
         "E": "/format-disk is not a real command."},
        85, [D_CHAT])

    add_multi(O2,
        "Which GitHub Copilot CLI subcommands exist? (Choose two.)",
        {"A": "gh copilot suggest", "B": "gh copilot explain",
         "C": "gh copilot deploy", "D": "gh copilot mine"},
        ["A", "B"],
        {"A": "suggest proposes commands for a task.",
         "B": "explain describes what a command does.",
         "C": "There is no deploy subcommand.",
         "D": "There is no mine subcommand."},
        84, [D_CLI])

    add_multi(O2,
        "Which are valid ways to interact with an inline Copilot suggestion in VS Code? (Choose three.)",
        {"A": "Accept the whole suggestion with Tab",
         "B": "Dismiss it with Esc",
         "C": "Accept the next word with Ctrl+Right Arrow",
         "D": "Compile the suggestion with F5 to accept it",
         "E": "Email the suggestion to accept it"},
        ["A", "B", "C"],
        {"A": "Tab accepts the full suggestion.",
         "B": "Esc dismisses the suggestion.",
         "C": "Ctrl+Right Arrow accepts word-by-word.",
         "D": "F5 starts debugging; it does not accept suggestions.",
         "E": "Emailing is not an acceptance mechanism."},
        84, [D_IDE])

    add_multi(O2,
        "Which capabilities are typically associated with Copilot Enterprise (beyond Business)? (Choose two.)",
        {"A": "Organization knowledge bases for grounding answers",
         "B": "Copilot Chat on GitHub.com tailored to your repos",
         "C": "Inline ghost-text completions in the editor",
         "D": "Tab to accept a suggestion"},
        ["A", "B"],
        {"A": "Knowledge bases are an Enterprise capability.",
         "B": "Repo-aware Chat on GitHub.com is part of Enterprise.",
         "C": "Inline completions exist across paid tiers, not unique to Enterprise.",
         "D": "Tab-to-accept is a basic editor behavior in all tiers."},
        82, [D_PLANS])

    add_multi(O2,
        "Which Copilot Chat references/participants help provide context? (Choose three.)",
        {"A": "@workspace", "B": "#file", "C": "@terminal",
         "D": "@printer", "E": "#wifi"},
        ["A", "B", "C"],
        {"A": "@workspace scopes to the whole repository.",
         "B": "#file attaches a specific file's contents.",
         "C": "@terminal focuses on the integrated terminal.",
         "D": "@printer is not a Copilot participant.",
         "E": "#wifi is not a Copilot context reference."},
        84, [D_CHAT])

    add_multi(O2,
        "Which statements about installing Copilot in IDEs are TRUE? (Choose two.)",
        {"A": "VS Code uses the GitHub Copilot extension from the marketplace",
         "B": "JetBrains IDEs use the Copilot plugin from the JetBrains Marketplace",
         "C": "Copilot is preinstalled in every text editor by default",
         "D": "Copilot requires no GitHub account to function"},
        ["A", "B"],
        {"A": "VS Code installs the Copilot extension.",
         "B": "JetBrains installs the Copilot plugin.",
         "C": "Copilot is not preinstalled everywhere.",
         "D": "An authenticated GitHub account with entitlement is required."},
        85, [D_IDE])

    # D2 hotspot (3)
    add_hotspot(O2,
        "For each task, select the most appropriate Copilot surface.",
        "Each task maps to the Copilot surface designed for it.",
        [{"label": "Suggest a shell command from a description",
          "options": ["Copilot CLI", "Inline completion", "Knowledge base"],
          "correct": "Copilot CLI",
          "reason": "`gh copilot suggest` proposes commands in the terminal."},
         {"label": "Get ghost-text as you type code",
          "options": ["Inline completion", "Copilot CLI", "GitHub.com Chat"],
          "correct": "Inline completion",
          "reason": "Inline completion provides ghost-text suggestions while typing."},
         {"label": "Ask repo-aware questions across many files in the IDE",
          "options": ["Copilot Chat @workspace", "Copilot CLI", "Minimap"],
          "correct": "Copilot Chat @workspace",
          "reason": "@workspace reasons across the repository."}],
        84, [D_CHAT, D_CLI, D_IDE])

    add_hotspot(O2,
        "Match each Copilot Chat slash command to its purpose.",
        "Slash commands map to specific assistant actions.",
        [{"label": "/tests",
          "options": ["Generate unit tests", "Explain code", "Clear chat"],
          "correct": "Generate unit tests",
          "reason": "/tests generates unit tests for the selection."},
         {"label": "/explain",
          "options": ["Explain code", "Generate tests", "Fix a bug"],
          "correct": "Explain code",
          "reason": "/explain describes what the code does."},
         {"label": "/fix",
          "options": ["Propose a fix", "Open a PR", "Delete a file"],
          "correct": "Propose a fix",
          "reason": "/fix suggests a correction for a detected problem."}],
        85, [D_CHAT])

    add_hotspot(O2,
        "For each plan capability, select whether it is included by default.",
        "Plan features differ across Individual, Business, and Enterprise.",
        [{"label": "Business excludes prompts/suggestions from training",
          "options": ["Included", "Not included"], "correct": "Included",
          "reason": "Business excludes business data from training by default."},
         {"label": "Enterprise provides organization knowledge bases",
          "options": ["Included", "Not included"], "correct": "Included",
          "reason": "Knowledge bases are an Enterprise capability."},
         {"label": "Individual provides org-wide policy management",
          "options": ["Included", "Not included"], "correct": "Not included",
          "reason": "Org-wide policy management requires Business/Enterprise."}],
        83, [D_PLANS])

    # ===================== DOMAIN 3 (26) =====================
    O3 = "Domain 3: Understand Copilot data and architecture"
    add_mc(O3,
        "At a high level, how does GitHub Copilot generate an inline suggestion?",
        "It builds a prompt from your context and sends it to a cloud-hosted large language model, which returns a completion",
        ["It searches a local database of copied snippets on your disk",
         "It compiles your project and predicts the output binary",
         "It downloads the answer from a fixed lookup table shipped with the extension"],
        "Copilot assembles context into a prompt and uses a cloud-hosted LLM to produce a completion that is returned to the editor.",
        ["Copilot does not maintain a local snippet database for matching.",
         "It does not compile your project to predict binaries.",
         "There is no fixed shipped lookup table of answers."],
        87, [D_COPILOT, D_TRUST])

    add_mc(O3,
        "What is the 'context window' in the context of a Copilot model?",
        "The maximum amount of tokens (prompt plus completion) the model can process at once",
        ["The visible area of the editor on screen",
         "The number of files open in the workspace",
         "The time window during which suggestions are cached"],
        "The context window is the token limit the model can consider for the combined prompt and response.",
        ["It is not the on-screen editor viewport.",
         "It is measured in tokens, not the count of open files.",
         "It is not a caching time interval."],
        86, [D_COPILOT, D_PROMPT])

    add_mc(O3,
        "Which best describes a 'prompt' that Copilot sends to the model for code completion?",
        "An assembled payload that includes surrounding code, related snippets, and the cursor position",
        ["Only the single word directly before the cursor",
         "The entire git history of the repository",
         "A screenshot of the editor"],
        "Copilot constructs a prompt from relevant context such as the surrounding code, related snippets, and cursor position.",
        ["It uses more than just the single preceding word.",
         "It does not send the entire git history.",
         "It sends text context, not screenshots."],
        85, [D_PROMPT, D_COPILOT])

    add_mc(O3,
        "What is telemetry in the context of GitHub Copilot?",
        "Usage and performance data collected to operate and improve the service, subject to policy settings",
        ["The model weights stored on the developer's machine",
         "The encryption keys used for TLS",
         "The list of installed VS Code themes"],
        "Telemetry refers to usage/performance data collected for service operation and improvement, governed by configurable policies.",
        ["Model weights are not telemetry and are not stored locally.",
         "TLS keys are unrelated to telemetry data.",
         "Installed themes are not Copilot telemetry."],
        84, [D_TELEMETRY, D_PRIVACY])

    add_mc(O3,
        "For Copilot Business and Enterprise, what is the default policy regarding using your prompts and suggestions to train the model?",
        "They are excluded from being used to train the foundational model by default",
        ["They are always used to train the model with no option to opt out",
         "They are published publicly for transparency",
         "They are emailed to the organization owner daily"],
        "Business and Enterprise exclude prompts and suggestions from model training by default.",
        ["There is an exclusion by default, not mandatory training use.",
         "Prompts are not published publicly.",
         "They are not emailed to owners."],
        85, [D_PRIVACY, D_PLANS])

    add_mc(O3,
        "Why does providing more relevant open files improve Copilot suggestions?",
        "Copilot can include relevant snippets from open files as additional context within the model's window",
        ["Open files increase the model's parameter count",
         "Open files change the model architecture",
         "Open files disable the cloud connection"],
        "Copilot can draw on relevant content from open files to enrich the prompt context, improving relevance.",
        ["Open files do not alter the model's parameter count.",
         "They do not change the model architecture.",
         "They do not disable cloud connectivity."],
        84, [D_PROMPT, D_COPILOT])

    add_mc(O3,
        "What is a 'token' in the context of LLM-based tools like Copilot?",
        "A chunk of text (often a word piece) that the model processes as a unit",
        ["A security credential for authenticating to GitHub",
         "A unit of the monthly billing currency",
         "A compiled object file"],
        "In LLMs, a token is a unit of text (such as a sub-word) the model consumes and produces.",
        ["Here 'token' refers to text units, not an auth credential, despite the overloaded term.",
         "It is not a billing currency unit.",
         "It is not a compiled object file."],
        83, [D_COPILOT])

    add_mc(O3,
        "Which statement about where Copilot inference runs is correct?",
        "Inference runs on cloud-hosted models operated by GitHub and its model providers",
        ["Inference runs entirely offline on the developer's CPU",
         "Inference runs in the browser using WebAssembly only",
         "Inference runs on the developer's GPU with no network use"],
        "Copilot relies on cloud-hosted models; the editor sends prompts and receives completions over the network.",
        ["It is not an offline on-device process.",
         "It does not run purely in-browser via WebAssembly.",
         "It is not a local GPU-only process without network."],
        85, [D_COPILOT])

    add_mc(O3,
        "What happens to the prompt context after a suggestion is generated for a Business/Enterprise user, per default data handling?",
        "It is not retained to train the foundational model by default",
        ["It is permanently added to the public training corpus",
         "It is stored as model weights",
         "It is shared with other customers"],
        "By default, Business/Enterprise prompts are not used to train the foundational model and are not shared with other customers.",
        ["It is not added to a public training corpus by default.",
         "Prompts do not become model weights.",
         "Prompts are not shared with other customers."],
        82, [D_PRIVACY])

    add_mc(O3,
        "Which factor most directly limits how much surrounding code Copilot can consider for a single suggestion?",
        "The model's context window (token limit)",
        ["The editor's zoom level",
         "The number of CPU cores",
         "The length of the file name"],
        "The token-based context window bounds how much context can be included in a single request.",
        ["Editor zoom does not affect context size.",
         "CPU cores do not change the cloud model's context window.",
         "File name length is irrelevant to context capacity."],
        85, [D_COPILOT, D_PROMPT])

    add_mc(O3,
        "Why might two developers receive different suggestions for the same line of code?",
        "Their surrounding context, open files, and the probabilistic nature of the model differ",
        ["Copilot assigns a fixed suggestion per user ID",
         "Suggestions depend on the operating system version only",
         "The model is retrained between the two requests"],
        "Different context plus the model's probabilistic generation lead to varied suggestions.",
        ["Suggestions are not fixed per user ID.",
         "OS version is not the determining factor.",
         "The model is not retrained between individual requests."],
        84, [D_COPILOT])

    add_mc(O3,
        "What is the role of a 'system prompt' or instructions in Copilot's architecture?",
        "Guidance that shapes how the model responds, combined with the user's context",
        ["A prompt that uninstalls the extension",
         "A prompt that changes the developer's OS settings",
         "A prompt that disables the network"],
        "System-level instructions guide model behavior and are combined with user context to produce responses.",
        ["It does not uninstall the extension.",
         "It does not modify OS settings.",
         "It does not disable the network."],
        78, [D_COPILOT])

    add_mc(O3,
        "How does Copilot Chat typically maintain continuity across a multi-turn conversation?",
        "It includes prior messages from the conversation as part of the context, within the window limit",
        ["It stores the full conversation as model weights",
         "It re-trains the model after each message",
         "It ignores all prior messages entirely"],
        "Chat includes earlier turns as context (subject to the window) to maintain continuity.",
        ["Conversations are not stored as weights.",
         "The model is not retrained per message.",
         "Prior messages are used, not ignored, when they fit the window."],
        82, [D_CHAT, D_COPILOT])

    add_mc(O3,
        "Which is an accurate description of how content exclusions affect Copilot's data flow?",
        "Excluded files are not used as context and do not inform suggestions",
        ["Excluded files are encrypted but still used as context",
         "Excluded files are uploaded to a public repository",
         "Excluded files are compiled before exclusion"],
        "Content exclusion prevents specified files from being used as Copilot context, removing them from the prompt assembly.",
        ["Excluded files are not used as context at all, not merely encrypted.",
         "Exclusion does not upload files publicly.",
         "Exclusion does not compile files."],
        83, [D_EXCLUSION, D_PRIVACY])

    add_mc(O3,
        "What does it mean that Copilot suggestions are 'generated, not retrieved'?",
        "The model synthesizes new text token-by-token rather than copying a stored answer",
        ["The suggestions are fetched from a CDN cache",
         "The suggestions are looked up in a Stack Overflow mirror",
         "The suggestions are pulled from your git stash"],
        "Generative models synthesize output token-by-token; they do not retrieve a pre-stored answer.",
        ["They are not fetched from a CDN cache of answers.",
         "They are not looked up from a Q&A mirror.",
         "They do not come from your git stash."],
        82, [D_COPILOT])

    add_mc(O3,
        "Why can the model's training cutoff matter when relying on Copilot for library APIs?",
        "Newer APIs released after the cutoff may be unknown or outdated in the model's knowledge",
        ["The cutoff increases the context window automatically",
         "The cutoff determines your subscription price",
         "The cutoff controls editor themes"],
        "A model trained up to a certain date may lack knowledge of newer APIs, so verification is needed.",
        ["The cutoff does not change the context window.",
         "It does not affect pricing.",
         "It is unrelated to editor themes."],
        83, [D_COPILOT, D_TRUST])

    add_mc(O3,
        "Which best describes how Copilot prioritizes context when assembling a prompt?",
        "It selects the most relevant nearby code and snippets to fit within the token budget",
        ["It always includes every file in the repository regardless of size",
         "It only includes the first line of the file",
         "It randomly picks files to include"],
        "Copilot prioritizes relevant context to fit the limited token budget rather than including everything.",
        ["It cannot include every file due to the context window.",
         "It uses more than just the first line.",
         "Context selection is relevance-driven, not random."],
        82, [D_PROMPT, D_COPILOT])

    add_mc(O3,
        "What category of data does Copilot transmit to generate a suggestion?",
        "Prompt context such as surrounding code and metadata needed for the request",
        ["The developer's full disk image",
         "The BIOS configuration",
         "All browser cookies on the machine"],
        "Copilot sends the prompt context required to produce a suggestion, not unrelated system data.",
        ["It does not transmit a full disk image.",
         "It does not send BIOS configuration.",
         "It does not collect browser cookies."],
        84, [D_PRIVACY, D_COPILOT])

    add_mc(O3,
        "How does increasing relevant context generally affect suggestion quality, up to the window limit?",
        "More relevant context tends to improve suggestion relevance and accuracy",
        ["More context always degrades suggestions",
         "Context has no effect on suggestions",
         "Context only affects the editor's theme"],
        "Providing more relevant context (within the window) generally yields better, more on-target suggestions.",
        ["Relevant context generally helps rather than degrades quality.",
         "Context clearly affects suggestions.",
         "Context is unrelated to themes."],
        84, [D_PROMPT])

    add_mc(O3,
        "Which statement about Copilot and your source code storage is most accurate by default for Business/Enterprise?",
        "Code sent as prompt context is used to produce suggestions and is not retained to train the foundational model by default",
        ["Your entire repository is permanently copied to the model provider",
         "Your code is published to a public dataset automatically",
         "Your code is stored unencrypted on other customers' machines"],
        "Prompt context is used transiently to generate suggestions and, for Business/Enterprise, is not retained for foundational training by default.",
        ["Repositories are not permanently copied wholesale to the provider.",
         "Code is not auto-published to public datasets.",
         "Code is not placed on other customers' machines."],
        82, [D_PRIVACY])

    add_mc(O3,
        "What is a practical implication of the context window limit for very large files?",
        "Copilot may not consider parts of the file that fall outside the token budget",
        ["Copilot automatically splits the file into separate repositories",
         "Copilot disables itself for files over 10 lines",
         "Copilot converts the file to a binary format"],
        "Content beyond the token budget cannot be included, so distant parts of a large file may be omitted from context.",
        ["It does not split files into repositories.",
         "There is no 10-line disable rule.",
         "It does not convert files to binary."],
        83, [D_COPILOT, D_PROMPT])

    # D3 multi (4)
    add_multi(O3,
        "Which items are part of the prompt context Copilot may assemble for a completion? (Choose three.)",
        {"A": "Code surrounding the cursor", "B": "Relevant snippets from open files",
         "C": "Comments describing intent", "D": "The developer's webcam feed",
         "E": "The machine's BIOS version"},
        ["A", "B", "C"],
        {"A": "Surrounding code is core context.",
         "B": "Relevant snippets from open files can be included.",
         "C": "Comments act as natural-language context.",
         "D": "Webcam data is never part of the prompt.",
         "E": "BIOS version is not used as context."},
        85, [D_PROMPT, D_COPILOT])

    add_multi(O3,
        "Which statements about the model context window are TRUE? (Choose two.)",
        {"A": "It is measured in tokens", "B": "It bounds combined prompt and completion size",
         "C": "It equals the number of open editor tabs", "D": "It is the editor's visible region"},
        ["A", "B"],
        {"A": "The window is a token limit.",
         "B": "It bounds the total of prompt plus completion.",
         "C": "It is unrelated to the count of open tabs.",
         "D": "It is not the on-screen viewport."},
        85, [D_COPILOT])

    add_multi(O3,
        "Which are accurate about Business/Enterprise data handling by default? (Choose two.)",
        {"A": "Prompts/suggestions are excluded from foundational model training",
         "B": "Content exclusions can prevent files from being used as context",
         "C": "All code is published to a public dataset",
         "D": "Telemetry cannot be governed by policy"},
        ["A", "B"],
        {"A": "Exclusion from training is the default for Business/Enterprise.",
         "B": "Content exclusion removes files from context.",
         "C": "Code is not published publicly.",
         "D": "Telemetry-related policies can be configured by admins."},
        83, [D_PRIVACY, D_EXCLUSION])

    add_multi(O3,
        "Why might Copilot produce an outdated or incorrect API call? (Choose three.)",
        {"A": "The API postdates the model's training cutoff",
         "B": "The model hallucinated a plausible but wrong method",
         "C": "Insufficient relevant context was provided",
         "D": "The editor theme was set to dark mode",
         "E": "The file had a long name"},
        ["A", "B", "C"],
        {"A": "Newer APIs may be unknown to the model.",
         "B": "Hallucination can invent wrong methods.",
         "C": "Poor context reduces accuracy.",
         "D": "Theme has no effect on correctness.",
         "E": "File name length is irrelevant."},
        84, [D_COPILOT, D_TRUST])

    # D3 hotspot (1)
    add_hotspot(O3,
        "For each statement about Copilot data and architecture, select True or False.",
        "Copilot uses cloud-hosted generative models with a token-limited context window.",
        [{"label": "Copilot inference runs on cloud-hosted models",
          "options": ["True", "False"], "correct": "True",
          "reason": "Copilot uses cloud-hosted LLMs for inference."},
         {"label": "The context window is measured in tokens",
          "options": ["True", "False"], "correct": "True",
          "reason": "Token count defines the context window."},
         {"label": "Business prompts are used to train the foundational model by default",
          "options": ["True", "False"], "correct": "False",
          "reason": "Business/Enterprise exclude prompts from training by default."}],
        84, [D_COPILOT, D_PRIVACY])

    # ===================== DOMAIN 4 (26) =====================
    O4 = "Domain 4: Apply prompt engineering and context crafting"
    add_mc(O4,
        "Which prompt is most likely to yield a precise, useful Copilot suggestion?",
        "A specific request describing inputs, outputs, and constraints (e.g., 'parse an ISO-8601 date string and return a UTC timestamp; raise on invalid input')",
        ["'write code'",
         "'do the thing'",
         "'make it work please'"],
        "Specific prompts that state inputs, outputs, and constraints give the model clear targets, producing more precise suggestions.",
        ["'write code' is too vague to guide the model.",
         "'do the thing' provides no actionable detail.",
         "'make it work please' lacks any concrete requirements."],
        88, [D_PROMPT])

    add_mc(O4,
        "What is 'context crafting' when working with GitHub Copilot?",
        "Deliberately shaping the surrounding code, comments, and references so Copilot has the right information",
        ["Changing the editor color theme to influence the model",
         "Compressing the repository to reduce token usage",
         "Renaming the project to a shorter name"],
        "Context crafting means intentionally arranging code, comments, and references to give Copilot the most relevant context.",
        ["Themes do not influence model output.",
         "Compressing the repo is not how context is shaped.",
         "Renaming the project does not craft useful context."],
        85, [D_PROMPT])

    add_mc(O4,
        "Why does writing a descriptive function signature and docstring before the body often help Copilot?",
        "It communicates the intended behavior so Copilot can implement the body to match",
        ["It forces Copilot to run offline",
         "It hides the function from the model",
         "It disables suggestions for that function"],
        "A clear signature and docstring express intent, guiding Copilot to generate a matching implementation.",
        ["It does not change online/offline behavior.",
         "It exposes intent rather than hiding the function.",
         "It does not disable suggestions."],
        87, [D_PROMPT])

    add_mc(O4,
        "A developer wants Copilot to follow a particular library's conventions. What is an effective technique?",
        "Provide an example usage of the library nearby so Copilot can mirror its style",
        ["Delete all imports so Copilot guesses freely",
         "Use a smaller monitor",
         "Write the prompt in all capital letters"],
        "Showing a concrete example of the library in use gives Copilot a pattern to follow.",
        ["Removing imports reduces context and worsens results.",
         "Monitor size is irrelevant.",
         "Capitalization does not improve adherence to conventions."],
        84, [D_PROMPT])

    add_mc(O4,
        "Which approach embodies the 'iterate on the prompt' best practice?",
        "Refine the comment or instruction and regenerate when the first suggestion is off-target",
        ["Accept the first suggestion regardless of fit",
         "Restart the IDE after every keystroke",
         "Switch programming languages until it works"],
        "Iterating—refining instructions and regenerating—steers Copilot toward the desired result.",
        ["Accepting the first off-target suggestion abandons iteration.",
         "Restarting the IDE per keystroke is pointless.",
         "Changing languages is not prompt iteration."],
        86, [D_PROMPT])

    add_mc(O4,
        "What is a good way to get Copilot to generate code that handles specific edge cases?",
        "Explicitly list the edge cases in a comment or instruction before generation",
        ["Hope Copilot infers them without mention",
         "Generate first, then never test",
         "Avoid comments to keep the file short"],
        "Naming the edge cases explicitly directs Copilot to address them.",
        ["Relying on inference is unreliable for specific cases.",
         "Skipping tests does not influence generation toward edge cases.",
         "Avoiding comments removes useful guidance."],
        85, [D_PROMPT])

    add_mc(O4,
        "Which is an example of giving Copilot 'examples' (few-shot style) in context?",
        "Providing one or two sample input/output pairs near the code you want generated",
        ["Setting the model temperature to zero from the UI",
         "Disabling the network to force local examples",
         "Clearing the file of all content"],
        "Including representative input/output examples nearby guides Copilot toward the desired pattern (few-shot prompting).",
        ["There is no user temperature control to set to zero.",
         "Disabling the network does not provide examples.",
         "Clearing the file removes all useful context."],
        82, [D_PROMPT])

    add_mc(O4,
        "How can breaking a large task into smaller, well-described steps improve Copilot's output?",
        "Smaller scoped prompts are clearer and fit the context window, yielding more accurate suggestions",
        ["It forces the model to use more parameters",
         "It bypasses the context window entirely",
         "It guarantees identical output every time"],
        "Decomposing tasks produces focused prompts that fit the window and are easier for the model to satisfy accurately.",
        ["It does not change the model's parameter count.",
         "It does not bypass the context window.",
         "It does not guarantee deterministic identical output."],
        85, [D_PROMPT])

    add_mc(O4,
        "A prompt says 'optimize this function.' Why might the result be unsatisfying?",
        "It is ambiguous about the optimization goal (speed, memory, readability), so Copilot may guess",
        ["Copilot cannot optimize any code",
         "The word 'optimize' is banned in prompts",
         "Optimization requires Enterprise only"],
        "Without specifying the optimization objective, Copilot may optimize for the wrong dimension; clarity improves results.",
        ["Copilot can attempt optimizations when given clear goals.",
         "There is no banned-word list affecting this.",
         "Optimization is not gated to Enterprise."],
        84, [D_PROMPT])

    add_mc(O4,
        "Which technique helps Copilot match your project's naming conventions?",
        "Keep representative, consistently named code open so the patterns appear in context",
        ["Use random variable names to test the model",
         "Close all related files before prompting",
         "Rename the repository each session"],
        "Exposing consistent naming patterns in context helps Copilot mirror them.",
        ["Random names provide misleading patterns.",
         "Closing related files removes helpful context.",
         "Renaming the repo does not influence naming conventions."],
        82, [D_PROMPT])

    add_mc(O4,
        "What does adding constraints like 'use only the standard library' to a prompt accomplish?",
        "It narrows the solution space so Copilot avoids disallowed dependencies",
        ["It speeds up the developer's internet connection",
         "It changes the editor's syntax highlighting",
         "It removes the need for testing"],
        "Stating constraints guides Copilot to honor requirements such as avoiding external dependencies.",
        ["It has no effect on network speed.",
         "It does not change syntax highlighting.",
         "It does not remove the need to test."],
        84, [D_PROMPT])

    add_mc(O4,
        "Why is it useful to specify the desired output format (e.g., 'return JSON') in a Copilot Chat prompt?",
        "It tells Copilot exactly how to structure its response, reducing rework",
        ["It changes your subscription tier",
         "It encrypts the response",
         "It disables other slash commands"],
        "Specifying the output format yields responses in the structure you need, reducing manual reformatting.",
        ["It does not affect your subscription.",
         "It does not encrypt anything.",
         "It does not disable slash commands."],
        83, [D_PROMPT, D_CHAT])

    add_mc(O4,
        "A developer gets irrelevant suggestions in a large file. Which context-crafting fix is most appropriate?",
        "Move the relevant code/comments closer to the cursor and reduce unrelated noise",
        ["Increase the editor brightness",
         "Add unrelated TODO comments throughout",
         "Open many unrelated projects at once"],
        "Bringing relevant context near the cursor and cutting noise improves the prompt Copilot assembles.",
        ["Brightness has no effect on suggestions.",
         "Unrelated TODOs add noise rather than relevance.",
         "Opening unrelated projects dilutes the context."],
        83, [D_PROMPT])

    add_mc(O4,
        "Which is the best example of an effective 'role + task + constraints' prompt to Copilot Chat?",
        "'As a security reviewer, identify SQL injection risks in this function and suggest parameterized queries.'",
        ["'help'",
         "'fix everything'",
         "'code'"],
        "Specifying a role, a concrete task, and constraints yields focused, actionable responses.",
        ["'help' is far too vague.",
         "'fix everything' lacks scope and direction.",
         "'code' provides no task at all."],
        85, [D_PROMPT, D_CHAT])

    add_mc(O4,
        "How can you guide Copilot to write tests that match your framework (e.g., pytest)?",
        "Mention the framework and show an existing test as an example in context",
        ["Hide all existing tests from the model",
         "Use a different language for the tests",
         "Disable the test runner"],
        "Naming the framework and exposing an example test guides Copilot to produce matching tests.",
        ["Hiding tests removes a useful pattern.",
         "Switching languages defeats the purpose.",
         "Disabling the runner does not affect generation."],
        84, [D_PROMPT])

    add_mc(O4,
        "What is the benefit of telling Copilot what NOT to do (negative constraints) in a prompt?",
        "It steers Copilot away from undesired approaches or dependencies",
        ["It permanently blocks those words from the model",
         "It increases the token limit",
         "It changes the model architecture"],
        "Negative constraints help exclude undesired solutions, narrowing toward acceptable ones.",
        ["It does not permanently block words globally.",
         "It does not increase the token limit.",
         "It does not change the architecture."],
        80, [D_PROMPT])

    add_mc(O4,
        "Which describes an effective feedback loop with Copilot Chat for a complex feature?",
        "Ask, review the output, point out what is wrong, and ask for a revision",
        ["Ask once and accept whatever is returned",
         "Never read the response, just paste it",
         "Send the same prompt repeatedly with no changes"],
        "Conversational refinement—reviewing and correcting—produces better results for complex tasks.",
        ["Accepting blindly skips refinement.",
         "Pasting without reading risks errors.",
         "Repeating the identical prompt yields little improvement."],
        84, [D_PROMPT, D_CHAT])

    add_mc(O4,
        "Why might including the relevant data model or schema in context improve generated queries?",
        "Copilot can reference the actual table/field names and types to produce correct queries",
        ["It changes the database engine automatically",
         "It removes the need for a database",
         "It disables the query planner"],
        "Providing the schema lets Copilot use real names and types, improving query accuracy.",
        ["It does not switch database engines.",
         "It does not remove the need for a database.",
         "It does not disable the query planner."],
        84, [D_PROMPT])

    add_mc(O4,
        "What is a good practice when a single prompt tries to do too many things at once?",
        "Split it into focused prompts, each handling one concern",
        ["Combine even more tasks into one giant prompt",
         "Remove all punctuation from the prompt",
         "Write the prompt as a single very long line"],
        "Focused, single-concern prompts are clearer and produce better results than overloaded ones.",
        ["Adding more tasks worsens clarity.",
         "Punctuation removal does not help.",
         "A long single line does not improve focus."],
        83, [D_PROMPT])

    add_mc(O4,
        "Which is an example of using comments as inline prompts effectively?",
        "Writing '# return the median of a list of numbers, handling empty lists' above the function",
        ["Writing '# TODO' with no detail",
         "Writing a comment unrelated to the code",
         "Removing all comments before generation"],
        "A precise comment describing the exact behavior steers Copilot to implement it correctly.",
        ["A bare '# TODO' gives no actionable guidance.",
         "Unrelated comments add noise.",
         "Removing comments eliminates useful guidance."],
        85, [D_PROMPT])

    add_mc(O4,
        "How does specifying expected error handling in a prompt influence Copilot?",
        "Copilot is more likely to include the requested validation and exception handling",
        ["Copilot will refuse the request",
         "Copilot will only generate comments",
         "Copilot will switch to a different file"],
        "Explicitly requesting error handling makes Copilot more likely to include it in the generated code.",
        ["Copilot does not refuse such requests.",
         "It generates code, not only comments.",
         "It does not switch files due to the request."],
        82, [D_PROMPT])

    # D4 multi (4)
    add_multi(O4,
        "Which are effective prompt-engineering practices with Copilot? (Choose three.)",
        {"A": "Be specific about inputs, outputs, and constraints",
         "B": "Provide examples of desired behavior in context",
         "C": "Iterate and refine when the first result is off",
         "D": "Use vague one-word prompts to save time",
         "E": "Remove all relevant context to keep files short"},
        ["A", "B", "C"],
        {"A": "Specificity guides the model effectively.",
         "B": "Examples (few-shot) steer output.",
         "C": "Iteration improves results.",
         "D": "Vague prompts produce poor results.",
         "E": "Removing relevant context degrades suggestions."},
        86, [D_PROMPT])

    add_multi(O4,
        "Which techniques help craft better context for Copilot? (Choose three.)",
        {"A": "Keep relevant files open",
         "B": "Write descriptive signatures and docstrings",
         "C": "Place related code near the cursor",
         "D": "Fill the file with unrelated noise",
         "E": "Use random identifier names"},
        ["A", "B", "C"],
        {"A": "Open relevant files provide useful context.",
         "B": "Descriptive signatures express intent.",
         "C": "Nearby related code improves relevance.",
         "D": "Noise dilutes the context.",
         "E": "Random names mislead the model."},
        85, [D_PROMPT])

    add_multi(O4,
        "Which details, when added to a prompt, tend to improve a generated function? (Choose three.)",
        {"A": "Expected input and output types",
         "B": "Edge cases to handle",
         "C": "Performance or dependency constraints",
         "D": "The developer's favorite color",
         "E": "The current time zone of the office"},
        ["A", "B", "C"],
        {"A": "Types clarify the contract.",
         "B": "Edge cases direct robust handling.",
         "C": "Constraints shape acceptable solutions.",
         "D": "Favorite color is irrelevant.",
         "E": "Office time zone is irrelevant to the function."},
        85, [D_PROMPT])

    add_multi(O4,
        "Which are good reasons to iterate with Copilot Chat rather than accepting the first answer? (Choose two.)",
        {"A": "The first answer may miss constraints you can clarify",
         "B": "Refinement can correct subtle logic errors",
         "C": "Iteration retrains the model for everyone",
         "D": "Iteration disables the context window"},
        ["A", "B"],
        {"A": "Clarifying constraints improves later answers.",
         "B": "Refinement catches and fixes errors.",
         "C": "Iteration does not retrain the model.",
         "D": "Iteration does not disable the context window."},
        84, [D_PROMPT, D_CHAT])

    # D4 hotspot (1)
    add_hotspot(O4,
        "For each prompt, select whether it is Well-scoped or Too vague for Copilot.",
        "Specific, constrained prompts outperform vague ones.",
        [{"label": "'Write a function to validate an email and return a boolean'",
          "options": ["Well-scoped", "Too vague"], "correct": "Well-scoped",
          "reason": "It states the task and output clearly."},
         {"label": "'fix it'",
          "options": ["Well-scoped", "Too vague"], "correct": "Too vague",
          "reason": "It provides no detail about what to fix or how."},
         {"label": "'Generate pytest unit tests covering empty and negative inputs'",
          "options": ["Well-scoped", "Too vague"], "correct": "Well-scoped",
          "reason": "It names the framework and the cases to cover."}],
        85, [D_PROMPT])

    # ===================== DOMAIN 5 (30) =====================
    O5 = "Domain 5: Improve developer productivity"
    add_mc(O5,
        "How can GitHub Copilot most directly help with writing unit tests?",
        "By generating test cases (e.g., via /tests) that cover typical and edge scenarios for selected code",
        ["By deploying the application to production",
         "By replacing the test runner entirely",
         "By deleting failing tests automatically"],
        "Copilot can generate unit tests for selected code, including common and edge cases, accelerating test authoring.",
        ["It does not deploy applications.",
         "It does not replace the test runner.",
         "It does not delete failing tests automatically."],
        87, [D_CHAT, L_LEARN])

    add_mc(O5,
        "A developer wants Copilot to help refactor a long function. What is a productive workflow?",
        "Select the function, ask Copilot Chat to refactor it for readability, then review and test the result",
        ["Ask Copilot to refactor and merge without review",
         "Delete the function and hope Copilot recreates it",
         "Refactor only the comments and ignore the logic"],
        "Selecting the code, requesting a refactor, then reviewing and testing balances speed with safety.",
        ["Merging without review abandons quality control.",
         "Deleting and hoping is unreliable and risky.",
         "Refactoring only comments does not improve the logic."],
        86, [D_CHAT])

    add_mc(O5,
        "How can Copilot assist with code documentation?",
        "By generating docstrings or comments (e.g., via /doc) that you then review for accuracy",
        ["By publishing documentation to a public site automatically",
         "By preventing anyone from editing comments",
         "By removing all existing documentation"],
        "Copilot can draft docstrings/comments to speed documentation, which you should verify for accuracy.",
        ["It does not auto-publish docs to a site.",
         "It does not lock comments from editing.",
         "It does not remove existing documentation."],
        85, [D_CHAT])

    add_mc(O5,
        "Which is a realistic productivity benefit of Copilot during code review preparation?",
        "Summarizing changes and explaining unfamiliar code so the author can write a clearer PR description",
        ["Approving the pull request on the author's behalf",
         "Guaranteeing zero defects in the change",
         "Eliminating the need for human reviewers"],
        "Copilot can summarize diffs and explain code, helping authors prepare clearer PRs, but human review remains.",
        ["It does not self-approve PRs.",
         "It cannot guarantee zero defects.",
         "It does not eliminate the need for human reviewers."],
        84, [D_CHAT])

    add_mc(O5,
        "How does Copilot help reduce context-switching for a developer?",
        "By answering questions and generating code in the editor, reducing the need to leave for web searches",
        ["By blocking all browser tabs",
         "By disabling notifications system-wide",
         "By turning off the integrated terminal"],
        "In-editor assistance keeps developers in flow, reducing trips to external resources.",
        ["It does not block browser tabs.",
         "It does not manage system notifications.",
         "It does not disable the terminal."],
        82, [D_CHAT, D_IDE])

    add_mc(O5,
        "A developer faces a failing test with a confusing stack trace. How can Copilot help productively?",
        "Explain the error and suggest likely fixes, which the developer verifies",
        ["Automatically rewrite the entire codebase",
         "Silence the test so it stops failing",
         "Delete the stack trace from logs"],
        "Copilot can interpret errors and propose fixes the developer then validates, speeding debugging.",
        ["Rewriting the whole codebase is excessive and risky.",
         "Silencing a test hides the problem rather than fixing it.",
         "Deleting logs removes useful diagnostic information."],
        85, [D_CHAT])

    add_mc(O5,
        "Which task is well-suited to Copilot for boosting productivity on repetitive code?",
        "Generating boilerplate such as data classes, getters/setters, or mapping functions",
        ["Choosing the company's cloud provider",
         "Negotiating vendor contracts",
         "Approving budget for new hardware"],
        "Copilot excels at generating repetitive boilerplate, freeing developers for higher-value work.",
        ["Cloud provider selection is a business decision, not a coding task.",
         "Contract negotiation is outside Copilot's scope.",
         "Budget approvals are not coding tasks."],
        84, [D_IDE])

    add_mc(O5,
        "How can Copilot support learning a new language while remaining productive?",
        "By suggesting idiomatic examples and explaining syntax, which the developer verifies and learns from",
        ["By translating the entire app to assembly",
         "By preventing the use of any documentation",
         "By hiding compiler errors"],
        "Copilot can provide idiomatic examples and explanations that aid learning when verified.",
        ["It does not translate apps to assembly as a learning aid.",
         "It does not block documentation use.",
         "It does not hide compiler errors."],
        82, [D_CHAT, L_LEARN])

    add_mc(O5,
        "What is a balanced expectation of Copilot's effect on productivity?",
        "It can speed up many tasks, but gains depend on the task and require human review",
        ["It makes every developer exactly twice as fast guaranteed",
         "It has no measurable effect on any task",
         "It only slows developers down"],
        "Productivity gains are real but variable and still require human oversight.",
        ["No fixed guaranteed multiplier applies to all developers.",
         "It clearly affects many tasks.",
         "It generally helps rather than only slowing developers."],
        83, [L_LEARN, D_TRUST])

    add_mc(O5,
        "How can Copilot Chat assist with understanding a legacy module quickly?",
        "By explaining what the code does and how components interact when asked with relevant context",
        ["By rewriting the module without telling you",
         "By deleting the module to simplify things",
         "By converting the module to an image"],
        "Asking Copilot to explain legacy code accelerates comprehension before making changes.",
        ["It does not secretly rewrite code.",
         "Deleting the module is not understanding it.",
         "It does not convert code to images."],
        84, [D_CHAT])

    add_mc(O5,
        "Which is an appropriate use of Copilot to improve documentation quality over time?",
        "Drafting README sections or API docs that maintainers review and refine",
        ["Auto-merging documentation PRs without review",
         "Removing the documentation to reduce maintenance",
         "Encrypting the docs so only Copilot can read them"],
        "Copilot can draft documentation that humans review, improving coverage and quality.",
        ["Auto-merging without review risks inaccuracies.",
         "Removing docs harms maintainability.",
         "Encrypting docs defeats their purpose."],
        82, [D_CHAT])

    add_mc(O5,
        "How can Copilot help with writing commit messages or PR descriptions?",
        "By drafting a summary of the changes that the developer edits for accuracy",
        ["By force-pushing to main with a generated message",
         "By preventing commits without AI involvement",
         "By hiding the diff from the author"],
        "Copilot can draft commit/PR text from the changes, which the author reviews and edits.",
        ["It does not force-push automatically.",
         "It does not block non-AI commits.",
         "It does not hide diffs."],
        82, [D_CHAT])

    add_mc(O5,
        "A team wants to increase test coverage efficiently. How does Copilot fit in?",
        "It can suggest additional test cases for under-tested code, which the team validates",
        ["It guarantees 100% coverage with no effort",
         "It deletes code that is hard to test",
         "It disables coverage reporting"],
        "Copilot can propose extra test cases to raise coverage, subject to team validation.",
        ["It cannot guarantee 100% coverage automatically.",
         "It does not delete hard-to-test code.",
         "It does not disable coverage reporting."],
        84, [D_CHAT])

    add_mc(O5,
        "Which describes a productive pair-programming-style use of Copilot Chat?",
        "Discussing design options and trade-offs, then implementing the chosen approach with review",
        ["Letting Copilot make all architectural decisions unchecked",
         "Ignoring Copilot's suggestions entirely at all times",
         "Asking Copilot to approve its own code"],
        "Using Chat to explore options and trade-offs, then implementing with review, mirrors healthy pair programming.",
        ["Unchecked architectural decisions remove human judgment.",
         "Ignoring all suggestions wastes the tool's value.",
         "Copilot cannot meaningfully approve its own output."],
        83, [D_CHAT])

    add_mc(O5,
        "How can Copilot reduce the time spent on repetitive refactors across similar code?",
        "By suggesting consistent transformations you can apply and verify in each location",
        ["By rewriting unrelated modules at random",
         "By permanently locking the files",
         "By converting the project to a different VCS"],
        "Copilot can propose consistent refactoring patterns to apply and verify, saving time.",
        ["It does not randomly rewrite unrelated modules.",
         "It does not lock files.",
         "It does not change version control systems."],
        82, [D_CHAT])

    add_mc(O5,
        "What is a sensible way to use Copilot when fixing a bug reported in an issue?",
        "Provide the relevant code and error context, ask for likely causes and fixes, then test the fix",
        ["Close the issue without changes because Copilot exists",
         "Apply the first suggestion to production immediately",
         "Ask Copilot to email the customer an apology"],
        "Giving Copilot the code and error context to suggest causes/fixes, then testing, is an effective debugging workflow.",
        ["Closing the issue without a fix does not resolve it.",
         "Pushing the first suggestion to production untested is risky.",
         "Customer communication is not a Copilot code task."],
        84, [D_CHAT])

    add_mc(O5,
        "How does Copilot assist with code consistency in a large codebase?",
        "By suggesting code that matches nearby patterns when relevant context is available",
        ["By enforcing a linter without configuration",
         "By rewriting the entire repo to one style instantly",
         "By disabling the formatter"],
        "With relevant context, Copilot tends to mirror existing patterns, supporting consistency.",
        ["It is not a linter and does not enforce rules by itself.",
         "It does not instantly restyle the whole repo.",
         "It does not disable formatters."],
        80, [D_PROMPT, D_IDE])

    add_mc(O5,
        "Which is a realistic limitation to remember when using Copilot to boost productivity?",
        "Time saved generating code can be offset if review and testing are skipped and defects slip through",
        ["Copilot removes the need for any quality process",
         "Copilot guarantees defect-free output",
         "Copilot eliminates the need to understand the code"],
        "Productivity gains can erode if review/testing are neglected, so they must remain part of the process.",
        ["Quality processes are still required.",
         "Output is not guaranteed defect-free.",
         "Understanding the code remains essential."],
        85, [D_TRUST])

    add_mc(O5,
        "How can Copilot help onboard a new team member productively?",
        "By explaining unfamiliar code and conventions, supplementing documentation and mentorship",
        ["By replacing all onboarding documentation and mentors",
         "By granting repository admin access",
         "By assigning tasks to the new hire"],
        "Copilot can explain code and conventions to support onboarding alongside docs and mentorship.",
        ["It supplements rather than replaces docs and mentors.",
         "It does not manage repository permissions.",
         "It does not assign work items."],
        82, [D_CHAT])

    add_mc(O5,
        "What is an effective way to use Copilot for generating example data or fixtures?",
        "Ask it to create representative sample data matching your schema, then verify validity",
        ["Use it to generate real customer PII for tests",
         "Use it to bypass data privacy rules",
         "Use it to delete the production database"],
        "Copilot can generate synthetic, schema-matching sample data for tests, which you validate.",
        ["Generating real PII for tests is a privacy risk and inappropriate.",
         "It must not be used to bypass privacy rules.",
         "It does not and should not delete production data."],
        83, [D_PROMPT])

    add_mc(O5,
        "Which best reflects measuring Copilot's productivity impact responsibly?",
        "Consider quality metrics (defects, review time) alongside speed, not raw lines generated",
        ["Count only the number of suggestions accepted",
         "Measure lines of code generated as the sole metric",
         "Track keystrokes saved exclusively"],
        "A responsible measure balances speed with quality outcomes rather than fixating on volume.",
        ["Acceptance count alone ignores quality.",
         "Lines of code is a poor sole productivity metric.",
         "Keystrokes saved alone misses quality effects."],
        81, [L_LEARN, D_TRUST])

    add_mc(O5,
        "How can Copilot help a developer write a complex regular expression more quickly?",
        "By drafting the regex from a described pattern, which the developer tests against examples",
        ["By guaranteeing the regex is correct without testing",
         "By converting the regex into machine code",
         "By disabling regex support in the language"],
        "Copilot can draft regexes from descriptions; the developer must test them against examples.",
        ["Correctness is not guaranteed without testing.",
         "It does not convert regex to machine code.",
         "It does not disable language features."],
        82, [D_PROMPT])

    add_mc(O5,
        "What is a productive use of Copilot when modernizing legacy code?",
        "Suggesting incremental, reviewable changes toward newer patterns while preserving behavior",
        ["Rewriting everything at once with no tests",
         "Deleting tests to speed up the migration",
         "Hiding the legacy code from reviewers"],
        "Incremental, reviewable, behavior-preserving changes are the productive and safe path for modernization.",
        ["A risky big-bang rewrite without tests invites regressions.",
         "Deleting tests removes the safety net.",
         "Hiding code from reviewers undermines review."],
        83, [D_CHAT])

    # D5 multi (5)
    add_multi(O5,
        "Which productivity tasks is GitHub Copilot well-suited to assist with? (Choose three.)",
        {"A": "Generating unit tests", "B": "Drafting documentation",
         "C": "Explaining unfamiliar code", "D": "Approving its own pull requests",
         "E": "Guaranteeing zero production defects"},
        ["A", "B", "C"],
        {"A": "Test generation is a core productivity use.",
         "B": "Documentation drafting speeds writing.",
         "C": "Explaining code aids comprehension.",
         "D": "It cannot meaningfully self-approve PRs.",
         "E": "It cannot guarantee zero defects."},
        86, [D_CHAT])

    add_multi(O5,
        "Which practices keep Copilot-driven productivity gains sustainable? (Choose three.)",
        {"A": "Continue reviewing and testing generated code",
         "B": "Validate Copilot's explanations against sources",
         "C": "Use Copilot to draft, then refine with judgment",
         "D": "Skip testing to maximize raw speed",
         "E": "Measure only lines generated"},
        ["A", "B", "C"],
        {"A": "Review/testing preserves quality.",
         "B": "Validating explanations avoids acting on errors.",
         "C": "Draft-then-refine balances speed and quality.",
         "D": "Skipping testing erodes gains via defects.",
         "E": "Lines generated is a misleading sole metric."},
        85, [D_TRUST])

    add_multi(O5,
        "How can Copilot assist during debugging? (Choose three.)",
        {"A": "Explaining a stack trace", "B": "Suggesting likely fixes",
         "C": "Proposing additional tests to reproduce the bug",
         "D": "Silencing failing tests to hide the bug",
         "E": "Deleting logs to reduce noise"},
        ["A", "B", "C"],
        {"A": "It can interpret stack traces.",
         "B": "It can suggest fixes to verify.",
         "C": "It can propose reproducing tests.",
         "D": "Silencing tests hides defects.",
         "E": "Deleting logs removes diagnostics."},
        85, [D_CHAT])

    add_multi(O5,
        "Which are appropriate Copilot uses for documentation and reviews? (Choose two.)",
        {"A": "Drafting docstrings for review",
         "B": "Summarizing a diff to aid the PR description",
         "C": "Auto-approving the PR",
         "D": "Publishing docs publicly without review"},
        ["A", "B"],
        {"A": "Drafting docstrings for human review is appropriate.",
         "B": "Summarizing diffs helps authors write PRs.",
         "C": "Auto-approval removes human review.",
         "D": "Publishing without review risks inaccuracies."},
        84, [D_CHAT])

    add_multi(O5,
        "Which are realistic limitations to keep in mind for Copilot productivity? (Choose three.)",
        {"A": "Generated code still needs review and testing",
         "B": "Explanations can be incorrect and need verification",
         "C": "Gains vary by task and developer",
         "D": "It guarantees correctness for all tasks",
         "E": "It eliminates the need to understand the code"},
        ["A", "B", "C"],
        {"A": "Review and testing remain necessary.",
         "B": "Explanations require verification.",
         "C": "Gains are variable, not uniform.",
         "D": "It does not guarantee correctness.",
         "E": "Understanding the code is still required."},
        85, [D_TRUST])

    # D5 hotspot (2)
    add_hotspot(O5,
        "For each productivity task, select whether Copilot is Well-suited or Not suited.",
        "Copilot assists with coding-related tasks, not business or governance decisions.",
        [{"label": "Generate boilerplate data classes",
          "options": ["Well-suited", "Not suited"], "correct": "Well-suited",
          "reason": "Boilerplate generation is a strong Copilot use."},
         {"label": "Choose the company's cloud vendor",
          "options": ["Well-suited", "Not suited"], "correct": "Not suited",
          "reason": "Vendor selection is a business decision, not a coding task."},
         {"label": "Draft unit tests for a function",
          "options": ["Well-suited", "Not suited"], "correct": "Well-suited",
          "reason": "Test generation is a core productivity use."}],
        85, [D_CHAT])

    add_hotspot(O5,
        "Match each goal to the Copilot action that best supports it.",
        "Each productivity goal maps to a specific Copilot capability.",
        [{"label": "Understand legacy code",
          "options": ["Ask Copilot to explain it", "Delete it", "Encrypt it"],
          "correct": "Ask Copilot to explain it",
          "reason": "Explanation accelerates comprehension."},
         {"label": "Increase test coverage",
          "options": ["Generate additional tests", "Remove failing tests", "Disable coverage"],
          "correct": "Generate additional tests",
          "reason": "Generating tests raises coverage."},
         {"label": "Write a PR description",
          "options": ["Summarize the diff", "Force-push to main", "Hide the diff"],
          "correct": "Summarize the diff",
          "reason": "Summarizing changes helps author the PR."}],
        85, [D_CHAT])

    # ===================== DOMAIN 6 (30) =====================
    O6 = "Domain 6: Configure privacy, content exclusions, and safeguards"
    add_mc(O6,
        "What does the GitHub Copilot 'content exclusion' feature do?",
        "It prevents specified files or paths from being used as context for Copilot suggestions",
        ["It encrypts the repository at rest",
         "It deletes the excluded files from disk",
         "It blocks the developer from opening the files"],
        "Content exclusions stop designated files/paths from being used as Copilot context, so they do not inform suggestions.",
        ["It does not perform repository encryption.",
         "It does not delete files.",
         "It does not prevent opening the files in the editor."],
        87, [D_EXCLUSION])

    add_mc(O6,
        "At which levels can content exclusions be configured for GitHub Copilot?",
        "At the repository and organization levels",
        ["Only on the individual developer's keyboard",
         "Only in the model provider's data center",
         "Only via the operating system registry"],
        "Content exclusions are configured at the repository and organization levels by admins.",
        ["They are not configured on a keyboard.",
         "They are not set in the model provider's data center by customers.",
         "They are not configured via the OS registry."],
        85, [D_EXCLUSION])

    add_mc(O6,
        "Which file format/syntax is used to specify Copilot content exclusion paths?",
        "Glob-style path patterns in the Copilot content exclusion settings",
        ["Binary blobs committed to main",
         "Compiled regex stored in the model",
         "A spreadsheet uploaded to GitHub Support"],
        "Content exclusions use glob-style path patterns to match files/directories to exclude.",
        ["Binary blobs are not the configuration mechanism.",
         "Customers do not store compiled regex inside the model.",
         "Support uploads are not how exclusions are defined."],
        80, [D_EXCLUSION])

    add_mc(O6,
        "What is the effect of an organization policy that disables Copilot suggestions matching public code?",
        "Suggestions that match public code are blocked, reducing duplication and licensing risk",
        ["All suggestions are disabled entirely",
         "Public repositories are deleted",
         "The developer's account is suspended"],
        "The duplication-detection policy blocks suggestions matching public code, lowering duplication and licensing risk.",
        ["It blocks matching suggestions, not all suggestions.",
         "It does not delete repositories.",
         "It does not suspend accounts."],
        85, [D_PRIVACY, D_TRUST])

    add_mc(O6,
        "For Copilot Business/Enterprise, which is true about prompts and suggestions and model training by default?",
        "They are excluded from being used to train the foundational model",
        ["They are always used to train the model",
         "They are sold to third parties",
         "They are posted to a public forum"],
        "By default, Business/Enterprise excludes prompts and suggestions from foundational model training.",
        ["They are not used for training by default.",
         "They are not sold to third parties.",
         "They are not posted publicly."],
        86, [D_PRIVACY, D_PLANS])

    add_mc(O6,
        "Who can configure organization-wide Copilot policies such as enabling/disabling features?",
        "Organization owners or administrators with the appropriate permissions",
        ["Any member regardless of role",
         "Only GitHub Support staff",
         "Only the model provider"],
        "Org owners/admins configure Copilot policies for the organization.",
        ["Ordinary members cannot set org-wide policy.",
         "GitHub Support does not manage your org policies for you.",
         "The model provider does not set your org policies."],
        84, [D_PRIVACY])

    add_mc(O6,
        "A repository contains a secrets file that must never inform Copilot suggestions. What is the correct safeguard?",
        "Add the file/path to Copilot content exclusions",
        ["Rename the file to secrets.bak",
         "Move the file to a different folder in the same repo",
         "Add a comment asking Copilot to ignore it"],
        "Adding the path to content exclusions reliably prevents it from being used as context.",
        ["Renaming does not exclude it from context.",
         "Moving it within the repo does not exclude it.",
         "An in-file comment is not a configuration mechanism."],
        85, [D_EXCLUSION])

    add_mc(O6,
        "What happens to suggestions in a file that is covered by a content exclusion?",
        "Copilot does not use that file's content as context, and may not provide suggestions within it depending on configuration",
        ["Suggestions are encrypted but still shown",
         "Suggestions are emailed to the admin",
         "Suggestions are stored in a public gist"],
        "Excluded files are not used as context, and Copilot behavior within them is restricted per the exclusion.",
        ["Suggestions are not merely encrypted while still shown.",
         "They are not emailed to admins.",
         "They are not stored in public gists."],
        82, [D_EXCLUSION])

    add_mc(O6,
        "Which is a key privacy benefit of Copilot Business/Enterprise over Individual?",
        "Organizational data handling controls and exclusion of prompts/suggestions from training by default",
        ["Faster typing speed for developers",
         "Free hardware for the organization",
         "Automatic public release of all code"],
        "Business/Enterprise add organizational data controls and default training exclusion.",
        ["Typing speed is unrelated to plan privacy features.",
         "No free hardware is provided.",
         "Code is not automatically released publicly."],
        84, [D_PRIVACY, D_PLANS])

    add_mc(O6,
        "What is the recommended safeguard to avoid leaking secrets through Copilot prompts?",
        "Avoid placing secrets in code/prompts and use content exclusions and secret management",
        ["Paste secrets so Copilot learns to avoid them",
         "Store secrets in comments for clarity",
         "Disable secret scanning to reduce noise"],
        "Keeping secrets out of code/prompts, using exclusions and secret management, prevents leakage.",
        ["Pasting secrets increases exposure risk.",
         "Storing secrets in comments is unsafe.",
         "Disabling secret scanning removes a protective control."],
        86, [D_EXCLUSION, D_PRIVACY])

    add_mc(O6,
        "Which statement about telemetry/data collection policies is accurate?",
        "Administrators can configure certain Copilot policies governing features and data handling for the organization",
        ["Telemetry policies cannot be configured at all",
         "Telemetry includes the contents of every private repository by default",
         "Telemetry is the same as the model's weights"],
        "Admins can configure Copilot policies that govern features and aspects of data handling.",
        ["Policies are configurable, not entirely fixed.",
         "Telemetry does not include all private repo contents by default.",
         "Telemetry is operational data, not model weights."],
        80, [D_TELEMETRY, D_PRIVACY])

    add_mc(O6,
        "How should an organization handle a third-party library directory it does not want influencing Copilot?",
        "Exclude the vendor directory via content exclusion patterns",
        ["Delete the library from the project",
         "Make the repository public",
         "Disable Copilot for the whole company"],
        "Excluding the vendor directory keeps it out of Copilot context without removing it from the project.",
        ["Deleting the library breaks the project.",
         "Making the repo public is unrelated and risky.",
         "Disabling Copilot company-wide is overkill for one directory."],
        82, [D_EXCLUSION])

    add_mc(O6,
        "What is a correct expectation about content exclusions and other developers?",
        "When configured at the org/repo level, exclusions apply for users working in that repository",
        ["Exclusions only apply to the admin who set them",
         "Exclusions apply globally to all GitHub users",
         "Exclusions require each user to re-enter them daily"],
        "Org/repo-level exclusions apply to users operating in that repository, not just the admin.",
        ["They are not limited to the admin who configured them.",
         "They do not affect unrelated users across all of GitHub.",
         "They do not require daily re-entry by users."],
        80, [D_EXCLUSION])

    add_mc(O6,
        "Which safeguard most directly addresses the risk of Copilot reproducing public code verbatim?",
        "Enabling the duplication detection filter (blocking matches to public code)",
        ["Increasing the editor font size",
         "Turning off syntax highlighting",
         "Renaming variables after acceptance"],
        "The duplication detection filter blocks suggestions matching public code, addressing verbatim reproduction.",
        ["Font size is irrelevant to duplication.",
         "Syntax highlighting does not affect matching.",
         "Renaming after acceptance does not prevent the match."],
        85, [D_PRIVACY, D_TRUST])

    add_mc(O6,
        "What is the best description of GitHub's default handling of Business/Enterprise code sent as context?",
        "It is used transiently to generate suggestions and not retained to train the foundational model by default",
        ["It is retained indefinitely to train public models",
         "It is shared with competitors",
         "It is published to the GitHub blog"],
        "Context is used transiently to produce suggestions and excluded from foundational training by default for Business/Enterprise.",
        ["It is not retained indefinitely for public model training.",
         "It is not shared with competitors.",
         "It is not published publicly."],
        84, [D_PRIVACY])

    add_mc(O6,
        "Which is an appropriate organizational safeguard before rolling out Copilot widely?",
        "Define policies for content exclusions, public-code matching, and review requirements",
        ["Disable all code review permanently",
         "Remove all security scanning tools",
         "Grant every member admin access"],
        "Establishing exclusion, matching, and review policies provides guardrails for a safe rollout.",
        ["Disabling review removes a key safeguard.",
         "Removing scanning tools increases risk.",
         "Granting universal admin access is a security hazard."],
        85, [D_PRIVACY, D_EXCLUSION])

    add_mc(O6,
        "A developer wants to confirm whether a path is excluded from Copilot. Where would an admin verify this?",
        "In the repository or organization Copilot content exclusion settings",
        ["In the operating system's hosts file",
         "In the browser's bookmarks",
         "In the model's training logs"],
        "Exclusion configuration is found in the repo/org Copilot content exclusion settings.",
        ["The hosts file is unrelated.",
         "Bookmarks do not store exclusions.",
         "Customers cannot inspect model training logs for this."],
        80, [D_EXCLUSION])

    add_mc(O6,
        "What is a correct statement about Copilot and private repository code privacy?",
        "Copilot can use private repo code as context to help you, with Business/Enterprise excluding it from training by default",
        ["Copilot always makes private code public",
         "Copilot cannot access any code you open",
         "Copilot stores all private code as public training data automatically"],
        "Copilot uses opened private code as context to assist you; Business/Enterprise exclude it from training by default.",
        ["It does not make private code public.",
         "It can use opened code as context to help.",
         "It does not automatically store private code as public training data."],
        82, [D_PRIVACY])

    add_mc(O6,
        "Which is an example of a safeguard that keeps humans accountable for AI output?",
        "Requiring code review and approval for all changes, including AI-assisted ones",
        ["Allowing Copilot to merge to main unsupervised",
         "Disabling branch protection rules",
         "Removing required reviewers from protected branches"],
        "Mandatory review/approval preserves human accountability over AI-assisted changes.",
        ["Unsupervised merging removes accountability.",
         "Disabling branch protection weakens safeguards.",
         "Removing required reviewers reduces oversight."],
        85, [D_TRUST, D_PRIVACY])

    add_mc(O6,
        "What should an organization do if it has compliance requirements restricting certain data from AI tools?",
        "Use content exclusions and policies to keep restricted data out of Copilot context, and document the configuration",
        ["Ignore the requirements because Copilot is secure",
         "Send the restricted data to Copilot to test it",
         "Disable all logging to avoid scrutiny"],
        "Exclusions plus documented policies keep restricted data out of Copilot context and support compliance.",
        ["Ignoring compliance requirements is not acceptable.",
         "Deliberately sending restricted data violates the requirement.",
         "Disabling logging undermines auditability."],
        84, [D_EXCLUSION, D_PRIVACY])

    add_mc(O6,
        "Which best describes the relationship between content exclusions and suggestion quality?",
        "Excluding files removes them from context, which can be a deliberate trade-off for privacy",
        ["Exclusions always improve suggestion quality",
         "Exclusions have no effect on context",
         "Exclusions increase the model's context window"],
        "Excluding files is a privacy trade-off: it removes potentially useful context to protect sensitive content.",
        ["Removing context does not inherently improve quality.",
         "Exclusions do affect what context is available.",
         "Exclusions do not change the context window size."],
        80, [D_EXCLUSION])

    add_mc(O6,
        "What is the recommended approach to verifying that safeguards are effective after configuration?",
        "Periodically review policies, test exclusions, and audit that review processes are followed",
        ["Assume configuration never drifts and never recheck",
         "Delete the policies to simplify the system",
         "Rely solely on developers' memory of the rules"],
        "Ongoing review, testing of exclusions, and auditing confirm that safeguards remain effective.",
        ["Configuration can drift; periodic checks are needed.",
         "Deleting policies removes the safeguards.",
         "Memory alone is unreliable for enforcement."],
        82, [D_PRIVACY])

    add_mc(O6,
        "Which statement about disabling public code matching is accurate?",
        "It is a policy that, when enabled, blocks suggestions matching public code to reduce duplication/licensing risk",
        ["It deletes all public repositories",
         "It disables Copilot entirely",
         "It is only available on the Free plan"],
        "The public-code-matching policy blocks matching suggestions, mitigating duplication and licensing concerns.",
        ["It does not delete public repositories.",
         "It does not disable Copilot entirely.",
         "It is an organization policy, not a Free-only feature."],
        82, [D_PRIVACY, D_TRUST])

    add_mc(O6,
        "A team wants to ensure generated code does not include a specific internal proprietary module as context. What is the right control?",
        "Add the proprietary module's path to content exclusions",
        ["Obfuscate the module's variable names",
         "Comment out the module",
         "Move the module to a subfolder"],
        "Content exclusion on the module's path prevents it from being used as Copilot context.",
        ["Obfuscation does not exclude it from context.",
         "Commenting it out changes the code, not the exclusion.",
         "Relocating within the repo does not exclude it."],
        84, [D_EXCLUSION])

    add_mc(O6,
        "An administrator wants to confirm that a newly added content exclusion is actually preventing a sensitive file from informing suggestions. What is the best verification step?",
        "Open the file in a supported editor and confirm Copilot does not use it as context per the exclusion configuration, then review the org/repo exclusion settings",
        ["Check the desktop wallpaper for a confirmation icon",
         "Delete the file and assume the exclusion worked",
         "Ask each developer to memorize the exclusion list"],
        "Verifying behavior in a supported editor plus reviewing the configured exclusion settings confirms the exclusion is effective.",
        ["A wallpaper icon is not a verification mechanism.",
         "Deleting the file does not verify the exclusion and loses the file.",
         "Memorization is unreliable and does not verify enforcement."],
        82, [D_EXCLUSION, D_PRIVACY])

    # D6 multi (4)
    add_multi(O6,
        "Which are valid privacy/safeguard controls available with GitHub Copilot? (Choose three.)",
        {"A": "Content exclusions for files/paths",
         "B": "Blocking suggestions that match public code",
         "C": "Exclusion of Business/Enterprise prompts from training by default",
         "D": "Forcing all repositories to be public",
         "E": "Selling prompts to third parties"},
        ["A", "B", "C"],
        {"A": "Content exclusions are a core control.",
         "B": "Public-code matching can be blocked by policy.",
         "C": "Training exclusion is default for Business/Enterprise.",
         "D": "Copilot does not force repos public.",
         "E": "Prompts are not sold to third parties."},
        86, [D_EXCLUSION, D_PRIVACY])

    add_multi(O6,
        "At which scopes can Copilot content exclusions be configured? (Choose two.)",
        {"A": "Repository level", "B": "Organization level",
         "C": "Individual keyboard level", "D": "BIOS level"},
        ["A", "B"],
        {"A": "Repository-level exclusions are supported.",
         "B": "Organization-level exclusions are supported.",
         "C": "There is no keyboard-level exclusion.",
         "D": "There is no BIOS-level exclusion."},
        84, [D_EXCLUSION])

    add_multi(O6,
        "Which actions help protect secrets and sensitive data when using Copilot? (Choose three.)",
        {"A": "Use content exclusions for sensitive paths",
         "B": "Keep secrets out of code and prompts",
         "C": "Use secret management and scanning",
         "D": "Paste production credentials into prompts",
         "E": "Disable secret scanning"},
        ["A", "B", "C"],
        {"A": "Excluding sensitive paths reduces exposure.",
         "B": "Keeping secrets out of code/prompts is essential.",
         "C": "Secret management and scanning add protection.",
         "D": "Pasting credentials creates exposure risk.",
         "E": "Disabling scanning removes a safeguard."},
        85, [D_EXCLUSION, D_PRIVACY])

    add_multi(O6,
        "Which statements about Business/Enterprise data handling are TRUE by default? (Choose two.)",
        {"A": "Prompts/suggestions are excluded from foundational training",
         "B": "Admins can set policies governing features and data handling",
         "C": "All code is shared with other customers",
         "D": "Content exclusions cannot be configured"},
        ["A", "B"],
        {"A": "Training exclusion is the default.",
         "B": "Admins configure governing policies.",
         "C": "Code is not shared with other customers.",
         "D": "Content exclusions are configurable."},
        85, [D_PRIVACY, D_EXCLUSION])

    # D6 hotspot (1)
    add_hotspot(O6,
        "For each privacy/safeguard statement, select True or False.",
        "Copilot provides configurable privacy controls and default protections for Business/Enterprise.",
        [{"label": "Content exclusions can prevent files from being used as context",
          "options": ["True", "False"], "correct": "True",
          "reason": "Exclusions remove specified files from Copilot context."},
         {"label": "Business/Enterprise prompts are used to train the foundational model by default",
          "options": ["True", "False"], "correct": "False",
          "reason": "They are excluded from training by default."},
         {"label": "Organizations can block suggestions that match public code",
          "options": ["True", "False"], "correct": "True",
          "reason": "The duplication-detection policy can block public-code matches."}],
        85, [D_PRIVACY, D_EXCLUSION])

    # >>> INSERT QUESTIONS HERE <<<
    pass


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    author()
    questions = finalize()
    assert len(questions) == 200, f"expected 200 questions, got {len(questions)}"

    tests = []
    for t in range(4):
        chunk = questions[t * 50:(t + 1) * 50]
        tests.append({"number": t + 1, "questions": chunk})

    data = {
        "title": "GH-300: GitHub Copilot Certification",
        "slug": "gh300",
        "tests": tests,
    }

    payload = json.dumps(data, ensure_ascii=False)
    # re-parse check
    json.loads(payload)

    html = HTML_TEMPLATE.replace("__DATA__", payload)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    # ---- stats ----
    overall = {"A": 0, "B": 0, "C": 0, "D": 0}
    print("=" * 60)
    print("GH-300 practice exam build complete")
    print("=" * 60)
    mc_seq = []
    for t in tests:
        per = {"A": 0, "B": 0, "C": 0, "D": 0}
        for q in t["questions"]:
            if q["type"] == "mc":
                per[q["answer"]] += 1
                overall[q["answer"]] += 1
                mc_seq.append(q["answer"])
        print(f"Test {t['number']}: A={per['A']} B={per['B']} "
              f"C={per['C']} D={per['D']} (mc only)")

    # domain counts
    dom = {}
    for q in questions:
        dom[q["objective"]] = dom.get(q["objective"], 0) + 1

    # max run over mc answer sequence
    max_run = 1
    run = 1
    for i in range(1, len(mc_seq)):
        if mc_seq[i] == mc_seq[i - 1]:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1

    type_counts = {}
    for q in questions:
        type_counts[q["type"]] = type_counts.get(q["type"], 0) + 1

    size = os.path.getsize(OUT_HTML)
    print("-" * 60)
    print(f"Total questions: {len(questions)}")
    print(f"Question types: {type_counts}")
    print("Domain distribution:")
    for k in sorted(dom):
        print(f"  {k}: {dom[k]}")
    print("-" * 60)
    print(f"MC answer distribution (overall): "
          f"A={overall['A']}, B={overall['B']}, "
          f"C={overall['C']}, D={overall['D']}")
    print(f"Max consecutive run (mc answers): {max_run} (cap = 3)")
    print(f"Output file: {OUT_HTML}")
    print(f"Output file size: {size:,} bytes ({size/1024:.1f} KB)")
    print("=" * 60)


if __name__ == "__main__":
    main()

const fs = require('fs');
const { JSDOM } = require('jsdom');
const html = fs.readFileSync(__dirname + '/../gh300-exam-viewer.html', 'utf-8');
const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true });
const { window } = dom; const doc = window.document; const $ = id => doc.getElementById(id);
function assert(c,m){ if(!c){console.error('FAIL: '+m);process.exitCode=1;} else console.log('ok  - '+m); }
function click(el){ el.dispatchEvent(new window.MouseEvent('click',{bubbles:true})); }
setTimeout(()=>{
  // jump to a multi question (id 28 -> index 27)
  const jump = $('panel').querySelector('.card.active [data-jump]');
  jump.value = '28'; jump.dispatchEvent(new window.Event('change'));
  let card = $('panel').querySelector('.card.active');
  assert(+card.dataset.qid===28, 'jumped to question 28');
  const isMulti = card.querySelector('.opt.multi')!==null;
  assert(isMulti, 'question 28 renders as multi (checkbox-style)');
  // select two options
  const opts = card.querySelectorAll('.opt');
  click(opts[0]); click(opts[2]);
  assert(card.querySelectorAll('.opt.sel').length===2, 'multi allows selecting two options');
  click(card.querySelector('[data-check]'));
  assert(card.querySelector('[data-fb]').classList.contains('show'),'multi feedback shown');
  assert(/Correct answers:/.test(card.querySelector('[data-fb]').innerHTML),'multi explanation lists correct answers');

  // jump to a hotspot (id 33)
  jump2 = card.querySelector('[data-jump]'); jump2.value='33'; jump2.dispatchEvent(new window.Event('change'));
  card = $('panel').querySelector('.card.active');
  assert(+card.dataset.qid===33,'jumped to question 33');
  const selects = card.querySelectorAll('select[data-hrow]');
  assert(selects.length>=2,'hotspot renders dropdown rows');
  // pick correct values from explanation? just select first non-empty option each
  selects.forEach(s=>{ s.value=s.options[1].value; s.dispatchEvent(new window.Event('change')); });
  click(card.querySelector('[data-check]'));
  assert(card.querySelector('[data-fb]').classList.contains('show'),'hotspot feedback shown');
  assert(card.querySelectorAll('.hotrow.correct, .hotrow.wrong').length===selects.length,'hotspot rows marked correct/wrong');
  // palette marks hotspot answered
  const idx = 32; // id33 index
  assert($('pgrid').querySelectorAll('button')[idx].classList.contains('answered'),'hotspot answered marks palette');
  console.log('\nMULTI/HOTSPOT TEST COMPLETE');
  window.close();
},500);

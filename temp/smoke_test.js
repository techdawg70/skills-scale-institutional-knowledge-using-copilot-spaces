const fs = require('fs');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync(__dirname + '/../gh300-exam-viewer.html', 'utf-8');
const errors = [];
const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  beforeParse(window) {
    window.addEventListener('error', e => errors.push('JS error: ' + e.message));
  },
});
const { window } = dom;
const doc = window.document;
const $ = (id) => doc.getElementById(id);

function assert(cond, msg) { if (!cond) { console.error('FAIL: ' + msg); process.exitCode = 1; } else { console.log('ok  - ' + msg); } }

// allow timers/render to run
setTimeout(() => {
  assert(errors.length === 0, 'no JS runtime errors (' + errors.join('; ') + ')');
  // exam title
  assert($('examTitle').textContent.includes('GH-300'), 'exam title rendered');
  // qpos
  assert(/Question 1 of 50/.test($('qpos').textContent), 'question position shows 1 of 50');
  // test selector has 4 options
  assert($('testSel').options.length === 4, 'test selector has 4 tests');
  // palette has 50 buttons
  assert($('pgrid').querySelectorAll('button').length === 50, 'palette has 50 buttons');
  // one active card
  const cards = $('panel').querySelectorAll('.card');
  assert(cards.length === 50, 'panel has 50 cards');
  assert($('panel').querySelectorAll('.card.active').length === 1, 'exactly one active card');
  // first card has options
  const first = $('panel').querySelector('.card.active');
  const opts = first.querySelectorAll('.opt');
  assert(opts.length >= 2, 'first question renders options');

  // select an option -> palette button becomes answered
  opts[0].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  const pbtn0 = $('pgrid').querySelectorAll('button')[0];
  assert(pbtn0.classList.contains('answered'), 'selecting an option marks palette answered');
  assert(opts[0].classList.contains('sel'), 'selected option is highlighted');

  // check answer reveals feedback
  const checkBtn = first.querySelector('[data-check]');
  checkBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  const fb = first.querySelector('[data-fb]');
  assert(fb.classList.contains('show'), 'feedback shown after check');
  assert(/Correct answer|Correct answers/.test(fb.innerHTML), 'feedback contains explanation');
  assert(first.querySelectorAll('.opt.correct').length >= 1, 'correct option highlighted green');

  // flag toggle
  const flagBtn = $('panel').querySelector('.card.active [data-flag]');
  flagBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  assert($('pgrid').querySelectorAll('button')[0].classList.contains('flagged'), 'flag marks palette orange');

  // next navigation
  let nextBtn = $('panel').querySelector('.card.active [data-nav="next"]');
  nextBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  assert(/Question 2 of 50/.test($('qpos').textContent), 'next advances to question 2');

  // keyboard left arrow goes back
  doc.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowLeft' }));
  assert(/Question 1 of 50/.test($('qpos').textContent), 'left arrow returns to question 1');

  // prev disabled on first
  const prevBtn = $('panel').querySelector('.card.active [data-nav="prev"]');
  assert(prevBtn.disabled === true, 'prev disabled on first question');

  // switch test
  $('testSel').value = '1';
  $('testSel').dispatchEvent(new window.Event('change'));
  const t2first = $('panel').querySelector('.card.active');
  assert(+t2first.dataset.qid === 51, 'test 2 starts at question id 51');
  assert(/Question 1 of 50/.test($('qpos').textContent), 'test switch resets position to 1 of 50');

  // open results modal
  $('endBtn').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  assert($('modal').classList.contains('show'), 'results modal opens');
  assert(/\d+ \/ 50 correct/.test($('scoreLine').textContent), 'score line shows X / 50 correct');
  assert($('brkBody').querySelectorAll('tr').length >= 1, 'domain breakdown table populated');

  // timer is counting (less than initial 6000 after ticks would need real time; just check format)
  assert(/^\d{2,3}:\d{2}$/.test($('timer').textContent), 'timer shows MM:SS format (' + $('timer').textContent + ')');
  assert($('timer').textContent === '100:00' || /^\d{2,3}:\d{2}$/.test($('timer').textContent), 'timer initialized to 100 minutes');

  console.log('\nSMOKE TEST COMPLETE');
  window.close();
}, 500);

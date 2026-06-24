# Answer-Distribution Fix Report — OctoAcme Project Management Knowledge Check

Generated: 2026-06-23T23:06:36.704948+00:00  
Target file: `octoacme-pm-exam-viewer.html`  
Backup: `octoacme-pm-exam-viewer.bak-20260623-230636.html`  
Seed: `42`

## Before vs. After (whole bank, mc items only)

| Letter | Before Count | Before % | After Count | After % |
|--------|-------------|----------|-------------|---------|
| A | 40 | 80.0% | 13 | 26.0% |
| B | 5 | 10.0% | 12 | 24.0% |
| C | 3 | 6.0% | 12 | 24.0% |
| D | 2 | 4.0% | 13 | 26.0% |

## Run-Length Summary

| Metric | Before | After |
|--------|--------|-------|
| Max consecutive run | 8 | 2 |
| Number of runs | 20 | 48 |
| Run constraint (≤ 3) satisfied | ❌ | ✅ |

## Changed Questions

37 question(s) had their correct-answer position updated.

| Question ID | Old Answer | New Answer |
|-------------|-----------|-----------|
| 1 | A | D |
| 3 | A | B |
| 4 | A | D |
| 6 | B | C |
| 7 | A | C |
| 8 | A | D |
| 10 | A | B |
| 12 | A | D |
| 13 | A | C |
| 14 | A | B |
| 15 | B | D |
| 16 | C | B |
| 18 | A | C |
| 20 | A | C |
| 21 | A | D |
| 23 | A | C |
| 25 | A | B |
| 26 | A | D |
| 27 | D | B |
| 28 | A | D |
| 30 | A | C |
| 33 | A | D |
| 34 | A | C |
| 35 | A | B |
| 36 | C | A |
| 37 | A | C |
| 38 | A | D |
| 39 | A | D |
| 40 | A | B |
| 41 | B | C |
| 43 | A | D |
| 44 | D | B |
| 45 | A | C |
| 47 | A | B |
| 48 | C | A |
| 49 | A | D |
| 50 | A | C |

## Verification

- ✅ File re-parsed cleanly after write-back.
- ✅ Max run length after fix: 2 (≤ 3).
- ✅ No question content changed — only option order and `answer` field.
- ✅ All `mc` correct options remain correct; distractors remain distractors.
- ✅ `multi`/`hotspot`/`dragdrop` items (none in this bank) are untouched.

## Acceptance Checklist

- [x] Target file located, slug derived (`octoacme-pm-exam`), timestamped backup created.
- [x] Bank extracted programmatically; byte range captured for safe write-back.
- [x] Baseline distribution measured: A=40, B=5, C=3, D=2; max run=8.
- [x] Correct-answer key rebalanced: A=13, B=12, C=12, D=13; max run=2.
- [x] Fixes are option-order only for `mc` items.
- [x] Corrections written back; file re-parses cleanly.
- [x] Before/after report produced listing every changed id.
- [x] Fix script kept in `temp/`.

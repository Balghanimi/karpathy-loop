# English for Master — Safe Website Improvement Loop

## Goal
Improve the English for Master course website without changing approved academic content or assessment policy.

## Optimization target
Maximize a composite website-quality score while all protected-content checks remain PASS.

## Allowed improvements
- semantic HTML and accessibility
- responsive layout and mobile readability
- keyboard navigation and focus states
- performance and page weight
- typography, spacing and visual hierarchy
- print CSS and A4 usability
- broken-link prevention
- metadata and SEO

## Protected academic constraints — MUST NOT CHANGE
- University of Kufa
- Electrical Engineering Department
- instructor name: Assist. Prof. Dr. Ali Al-Ghanimi
- exactly 15 course weeks
- 120 minutes per normal weekly class
- 10-minute break
- Week 8 is the midterm examination
- Week 15 is comprehensive review / final preparation
- continuous assessment = 30/100
- final examination = 70/100
- homework = 5 marks
- Quiz 1 = 5 marks
- Midterm = 15 marks
- Quiz 2 = 5 marks
- approved week titles in protected-content.json

## Ratchet rules
1. Make ONE coherent website improvement per iteration.
2. Run protected-content checks first. Any failure = immediate REVERT.
3. Run accessibility and structural tests.
4. Run Lighthouse CI and visual regression when available.
5. Compare composite score with the current best.
6. KEEP only if score improves and no hard gate regresses.
7. Never deploy experiments directly to production.
8. Deploy candidate builds to Vercel Preview only.
9. Production promotion requires explicit human approval.

## Hard gates
- Protected academic content: 100% PASS
- 15 week cards present
- no serious/critical axe violations
- no horizontal overflow at mobile viewport
- no broken internal navigation
- Lighthouse accessibility >= 0.95
- cumulative layout shift <= 0.10

## Composite score (0–100)
- Protected content / structural integrity: 30 points (hard gate)
- Accessibility: 25 points
- Performance: 20 points
- Visual/mobile quality: 10 points
- Best practices + SEO: 10 points
- Print/readability checks: 5 points

The loop may not trade away a hard gate for a higher aggregate score.

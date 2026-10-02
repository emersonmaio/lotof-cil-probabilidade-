# V6 exploratory test

This is an exploratory prototype test run before the canonical GitHub Actions
implementation was added. It uses the same V6-C concept (multi-window smoothed
inclusion scores, recency, candidate generation and overlap penalty) but a
different deterministic random-number implementation. Therefore these numbers
are directional and are **not** the canonical CI result.

Validation 2275-3032:
- V6-A: mean best 10.924802; 13+ = 10; 14+ = 0
- V6-B: mean best 10.894459; 13+ = 11; 14+ = 0
- V6-C: mean best 10.920844; 13+ = 12; 14+ = 1
- V6-D: mean best 10.935356; 13+ = 11; 14+ = 0
- Random10 prototype baseline: mean best 10.903694; 13+ = 12; 14+ = 0

Using validation to select V6-C, the exploratory holdout 3033-3791 produced:
- V6-C: mean best 10.920949; 13+ = 14; 14+ = 0
- Random10 prototype: mean best 10.857708; 13+ = 9; 14+ = 0

Interpretation: promising signal for further testing, but not enough evidence to
declare a robust advantage. The canonical implementation in src/v6_probabilistic.py
must be evaluated by the repository workflow before any production decision.

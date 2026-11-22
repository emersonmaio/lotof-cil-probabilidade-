"""Calibração e poder dos testes de aleatoriedade e de hipóteses; ausência de vazamento."""
import numpy as np
import pytest

import hypotheses_test as ht
import randomness_audit as ra


def test_holm_is_monotone_and_bounded():
    adj = ra.holm([0.001, 0.04, 0.5, 0.02])
    assert all(0 <= a <= 1 for a in adj)
    # ordenados: 0,001(x4) 0,02(x3) 0,04(x2) 0,5(x1) -> 0,004 0,06 0,08 0,5 (monótonos)
    assert adj == pytest.approx([0.004, 0.08, 0.5, 0.06])


def test_randomness_audit_calibrated_on_random_history(tmp_path):
    """Histórico simulado sob H0: nenhum teste deve rejeitar após Holm."""
    rng = np.random.default_rng(11)
    m = ra.simulate_matrix(1500, rng)
    order = ra.simulate_ordered(1500, rng)
    csv_path = tmp_path / "sim.csv"
    lines = ["Concurso,Data," + ",".join(f"bola {i}" for i in range(1, 16))]
    for i, row in enumerate(order, start=1):
        lines.append(f"{i},01/01/2020," + ",".join(str(x) for x in row))
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rep = ra.run(str(csv_path), reps=200, seed=5)
    assert not any(r["rejeita_H0_5pct"] for r in rep["resultados"]), rep["resultados"]


def test_randomness_audit_detects_injected_dependence():
    rng = np.random.default_rng(2)
    base = ra.simulate_matrix(1500, rng)
    # injeta repetição: com prob. 0,5 o concurso copia 12 dezenas do anterior
    for t in range(1, len(base)):
        if rng.random() < 0.5:
            keep = rng.choice(np.flatnonzero(base[t - 1]), 12, replace=False)
            rest = rng.choice(np.flatnonzero(~np.isin(np.arange(25), keep)), 3, replace=False)
            base[t] = False
            base[t, keep] = True
            base[t, rest] = True
    obs = ra.s_repeat(base)
    sims = [ra.s_repeat(ra.simulate_matrix(1500, rng)) for _ in range(100)]
    assert obs > max(sims)


def test_hypothesis_scores_use_only_the_past():
    rng = np.random.default_rng(4)
    m = ra.simulate_matrix(600, rng)
    t0 = 400
    changed = m.copy()
    changed[t0:] = ra.simulate_matrix(200, rng)             # troca alvo e futuro
    for h in ht.HYPOTHESES:
        a = ht.scores(m, h)[t0]
        b = ht.scores(changed, h)[t0]
        assert np.array_equal(a, b), h


def test_hypotheses_calibrated_under_null_and_powerful_under_signal():
    rng = np.random.default_rng(3)
    zs = [ht.z_of(ht.top15_hits(ra.simulate_matrix(2000, rng), h))["z"] for h in ht.HYPOTHESES for _ in range(3)]
    assert abs(np.mean(zs)) < 0.4 and 0.7 < np.std(zs) < 1.3
    w = np.ones(25)
    w[:5] = 1.25
    n = 2000
    biased = np.zeros((n, 25), bool)
    for i in range(n):
        biased[i, rng.choice(25, 15, replace=False, p=w / w.sum())] = True
    assert ht.z_of(ht.top15_hits(biased, "freq_all"))["z"] > 4


def test_overdue_hypothesis_is_not_duplicated():
    assert len(set(ht.HYPOTHESES)) == len(ht.HYPOTHESES) == 11

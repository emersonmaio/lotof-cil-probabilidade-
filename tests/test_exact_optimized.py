import random
import numpy as np
import exact_eval as ex
import optimized_structure as op


def test_single_ticket_exact_mean_is_9():
    h = ex.hits_matrix([ex.mask(range(1, 16))])
    assert abs(h.mean() - 9.0) < 1e-9
    assert abs(h.astype(float).var() - 1.5) < 1e-9


def test_expected_tickets_by_tier_equal_for_any_portfolio():
    """Linearidade: prêmio esperado independe da escolha dos jogos."""
    rng = random.Random(3)
    a = ex.exact_stats([ex.mask(rng.sample(range(1, 26), 15)) for _ in range(10)])
    b = ex.exact_stats(op.STRUCTURE)
    for k in (11, 12, 13, 14, 15):
        assert abs(b["E_tickets_exact"][k] - 10 * ex.exact_stats([op.STRUCTURE[0]])["E_tickets_exact"][k]) < 1e-9
    assert abs(a["E_tickets_exact"][13] - b["E_tickets_exact"][13]) < 0.01


def test_optimized_beats_random_and_is_valid():
    assert len(set(op.STRUCTURE)) == 10 and all(bin(m).count("1") == 15 for m in op.STRUCTURE)
    s = ex.exact_stats(op.STRUCTURE)
    assert s["E_best"] > 10.95


def test_relabel_preserves_exact_stats_and_varies():
    r = random.Random(1)
    g1, g2 = op.choose(r), op.choose(r)
    assert g1 != g2
    assert abs(ex.exact_stats(g1)["E_best"] - ex.exact_stats(op.STRUCTURE)["E_best"]) < 1e-12

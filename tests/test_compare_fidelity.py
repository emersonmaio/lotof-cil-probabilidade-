"""O harness de comparação deve reproduzir exatamente os `evaluate` do repositório."""
import numpy as np
import pytest

import compare_models as cm
import v6_probabilistic as v6
import v7_1_optimized as v71
import v8_adaptive as v8

START, END, SEED = 3100, 3112, 424242


@pytest.fixture(scope="module")
def data(history):
    rows6 = [(c, d) for c, d, _ in history]
    rows71 = [(c, d, sum(1 << (n - 1) for n in d)) for c, d, _ in history]
    dm = {c: m for c, _, m in rows71}
    return rows6, rows71, dm


def _best(portfolios, dm):
    return [max((g & dm[START + i]).bit_count() for g in games) for i, games in enumerate(portfolios)]


def test_v6_matches_repo_evaluate(data):
    rows6, _, dm = data
    assert _best(cm.portfolios_v6(rows6, START, END, "V6-C", SEED), dm) == v6.evaluate(rows6, START, END, "V6-C", SEED)


def test_v71_matches_repo_evaluate(data):
    _, rows71, dm = data
    st = v71.build_states(rows71, START, END)
    assert _best(cm.portfolios_v71(rows71, st, START, END, "V7-B", SEED), dm) == \
        v71.evaluate(rows71, START, END, "V7-B", SEED, st, 220)


def test_v8_matches_repo_evaluate(data):
    _, rows71, dm = data
    st = v71.build_states(rows71, START, END)
    assert _best(cm.portfolios_v8(rows71, st, START, END, "V7-A", SEED, 100), dm) == \
        v8.evaluate(rows71, START, END, "V7-A", SEED, st, 100)


def test_null_stats_agree_with_exact_for_a_single_ticket_portfolio():
    """Um portfólio de 10 bilhetes IGUAIS = 1 bilhete: E[acertos] exato = 15*15/25 = 9."""
    game = cm.mask(range(1, 16))
    E, V, P = cm.null_stats([[game] * 10], cm.null_pool(seed=5, r=40000))
    assert abs(E[0] - 9.0) < 0.03
    assert abs(V[0] - 15 * (15 / 25) * (10 / 25) * (10 / 24)) < 0.06   # variância hipergeométrica


def test_diversified_control_is_valid_and_uses_no_history():
    ports = cm.portfolios_diversified(1, 3, 99, candidates=40)
    assert len(ports) == 3
    for games in ports:
        assert len(games) == 10 and len(set(games)) == 10
        assert all(bin(g).count("1") == 15 for g in games)
    assert ports == cm.portfolios_diversified(1, 3, 99, candidates=40)   # determinístico

"""Reprodutibilidade por semente e correção do baseline aleatório."""
import math
import random
from math import comb

import backtest_8plus2
import experiment
import stage2
import v6_probabilistic as v6
import v7_1_optimized as v71
import v8_adaptive as v8


def _states(history, c):
    rows = [(cc, d, sum(1 << (n - 1) for n in d)) for cc, d, _ in history]
    return rows, v71.build_states(rows, c, c)[c]


def test_v6_same_seed_same_portfolio(history):
    hist = [(c, d) for c, d, _ in history if c < 3500]
    a = v6.portfolio(hist, random.Random(11), "V6-B", 50)
    b = v6.portfolio(hist, random.Random(11), "V6-B", 50)
    c = v6.portfolio(hist, random.Random(12), "V6-B", 50)
    assert a == b and a != c


def test_v71_and_v8_same_seed_same_portfolio(history):
    _, st = _states(history, 3500)
    indiv, pair = st["V7-B"]
    cfg = v71.CONFIGS["V7-B"]
    a = v71.portfolio(indiv, pair, random.Random(3), cfg, 60)
    b = v71.portfolio(indiv, pair, random.Random(3), cfg, 60)
    assert [g[1] for g in a] == [g[1] for g in b]
    c8a = v8.choose10(v8.make_candidates(indiv, pair, cfg, random.Random(3), 80), pair, cfg)
    c8b = v8.choose10(v8.make_candidates(indiv, pair, cfg, random.Random(3), 80), pair, cfg)
    assert [g[1] for g in c8a] == [g[1] for g in c8b]


def test_portfolios_have_10_distinct_valid_games(history):
    hist = [(c, d) for c, d, _ in history if c < 3500]
    _, st = _states(history, 3500)
    indiv, pair = st["V7-A"]
    cfg = v71.CONFIGS["V7-A"]
    sets = {
        "v6": v6.portfolio(hist, random.Random(1), "V6-A", 60),
        "v71": [g[1] for g in v71.portfolio(indiv, pair, random.Random(1), cfg, 60)],
        "v8": [g[1] for g in v8.choose10(v8.make_candidates(indiv, pair, cfg, random.Random(1), 80), pair, cfg)],
    }
    for name, games in sets.items():
        assert len(games) == 10 and len(set(games)) == 10, name
        for g in games:
            assert len(g) == 15 and len(set(g)) == 15 and min(g) >= 1 and max(g) <= 25, name


def test_experiment_strategies_give_10_unique_games(history):
    hist = [(c, d) for c, d, _ in history if c < 3000]
    for name in ["random10", "freq8_cov2", "blend8_cov2", "freq8_inv2", "blend8_inv2"]:
        games = experiment.portfolio(hist, random.Random(4), name, 100)
        assert len(games) == 10 and len(set(games)) == 10, name


def test_all_random10_implementations_are_unique_and_valid():
    impls = [
        experiment.portfolio([], random.Random(9), "random10", 100),
        backtest_8plus2.random10(random.Random(9)),
        stage2.random10(__import__("numpy").random.default_rng(9)),
    ]
    for games in impls:
        assert len(games) == 10 and len(set(games)) == 10
        assert all(len(g) == 15 and len(set(g)) == 15 and 1 <= min(g) and max(g) <= 25 for g in games)


def _exact_expected_best_of_10():
    """E[max de 10 bilhetes independentes] contra um sorteio uniforme (hipergeométrica exata)."""
    pk = {k: comb(15, k) * comb(10, 15 - k) / comb(25, 15) for k in range(5, 16)}
    cdf, acc = {}, 0.0
    for k in range(5, 16):
        acc += pk[k]
        cdf[k] = acc
    return sum(k * (cdf[k] ** 10 - (cdf[k - 1] ** 10 if k > 5 else 0.0)) for k in range(5, 16))


def test_exact_random_baseline_is_consistent_with_documented_empirical_value():
    # Valor EXATO (10 bilhetes iid vs sorteio uniforme) = 10,8402. A documentação cita 10,829015
    # (média empírica de 5 sementes, 772 concursos, DP entre sementes 0,0315): diferença dentro
    # do ruído amostral. O valor exato deve ser preferido como referência do baseline.
    exact = _exact_expected_best_of_10()
    assert abs(exact - 10.8402) < 1e-3
    assert abs(exact - 10.829015) < 2 * 0.0315


def test_random10_empirical_mean_matches_exact_expectation():
    rng = random.Random(2026)
    vals = []
    for _ in range(20000):
        target = set(rng.sample(range(1, 26), 15))
        vals.append(max(len(set(g) & target) for g in experiment.portfolio([], rng, "random10", 100)))
    mean = sum(vals) / len(vals)
    # random10 repete bilhetes distintos (sem reposição) -> praticamente igual ao iid
    assert abs(mean - _exact_expected_best_of_10()) < 0.03

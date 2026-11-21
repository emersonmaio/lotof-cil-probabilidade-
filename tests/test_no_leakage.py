"""Nenhum modelo pode usar o concurso-alvo (nem os posteriores) para montar seus jogos."""
import random

import pytest

import experiment
import v6_probabilistic as v6
import v7_1_optimized as v71
import v7_cooccurrence as v7


def scramble_from(rows, first_contest, seed=7):
    """Troca as dezenas de todos os concursos >= first_contest por sorteios aleatórios."""
    rng = random.Random(seed)
    out = []
    for c, d, m in rows:
        if c >= first_contest:
            d = tuple(sorted(rng.sample(range(1, 26), 15)))
            m = sum(1 << (n - 1) for n in d)
        out.append((c, d, m))
    return out


@pytest.mark.parametrize("target", [2275, 3033, 3500, 3794, 3810])
def test_v71_states_ignore_target_and_future(history, target):
    rows = [(c, d, sum(1 << (n - 1) for n in d)) for c, d, _ in history]
    shuffled = scramble_from(rows, target)
    a = v71.build_states(rows, target, target)[target]
    b = v71.build_states(shuffled, target, target)[target]
    assert a == b


def test_v71_states_do_depend_on_past(history):
    """Controle negativo: mudar o PASSADO tem de mudar o estado (o teste não é vazio)."""
    rows = [(c, d, sum(1 << (n - 1) for n in d)) for c, d, _ in history]
    target = 3500
    changed = list(rows)
    d = tuple(range(1, 16))
    changed[target - 2] = (target - 1, d, sum(1 << (n - 1) for n in d))
    assert v71.build_states(rows, target, target)[target] != v71.build_states(changed, target, target)[target]


@pytest.mark.parametrize("target", [3033, 3810])
def test_v6_portfolio_ignores_target_and_future(history, target):
    rows = [(c, d) for c, d, _ in history]
    scrambled = [(c, d) for c, d, _ in scramble_from(history, target)]
    seen = []
    for r in (rows, scrambled):
        hist = [x for x in r if x[0] < target]   # mesma regra usada por v6.evaluate
        seen.append(v6.portfolio(hist, random.Random(5), "V6-C", 60))
    assert seen[0] == seen[1]


def test_v6_evaluate_uses_only_prior_contests(history, monkeypatch):
    rows = [(c, d) for c, d, _ in history]
    lengths = []
    real = v6.portfolio

    def spy(hist, rng, config, candidates=180):
        lengths.append((max(c for c, _ in hist), len(hist)))
        return real(hist, rng, config, 40)

    monkeypatch.setattr(v6, "portfolio", spy)
    v6.evaluate(rows, 3000, 3004, "V6-A", 1)
    assert [m for m, _ in lengths] == [2999, 3000, 3001, 3002, 3003]
    assert [n for _, n in lengths] == [2999, 3000, 3001, 3002, 3003]


def test_experiment_evaluate_uses_only_prior_contests(history, monkeypatch):
    rows = [(c, d) for c, d, _ in history]
    seen = []
    real = experiment.portfolio

    def spy(hist, rng, name, w):
        seen.append(len(hist))
        return real(hist, rng, name, w)

    monkeypatch.setattr(experiment, "portfolio", spy)
    experiment.evaluate(rows, 3100, 3103, "freq8_cov2", 100, 1)
    assert seen == [3099, 3100, 3101, 3102]


def test_v7_original_and_v71_scores_are_equivalent(history):
    """V7.1 diz ser só otimização do V7: os escores têm de coincidir."""
    target = 3400
    rows7 = [(c, d) for c, d, _ in history if c < target]
    rows71 = [(c, d, sum(1 << (n - 1) for n in d)) for c, d, _ in history]
    states = v71.build_states(rows71, target, target)[target]
    for cfg_name, cfg in v71.CONFIGS.items():
        indiv71, pair71 = states[cfg_name]
        indiv7 = v7.individual_scores(rows7, v7.CONFIGS[cfg_name])
        pair7 = v7.pair_scores(rows7, v7.CONFIGS[cfg_name])
        assert max(abs(a - b) for a, b in zip(indiv71, indiv7)) < 1e-9, cfg_name
        for pi, p in enumerate(v71.PAIRS):
            assert abs(pair71[pi] - pair7[p]) < 1e-9, (cfg_name, p)

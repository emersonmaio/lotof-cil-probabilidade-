"""Integridade do histórico e consistência entre os loaders (antigos e o novo)."""
import pytest

import data_io
import experiment
import freeze_portfolio  # noqa: F401  (garante que o módulo importa)
import stage2
import v6_probabilistic
import v7_1_optimized

# Resultados conferidos em cobertura jornalística (Diário do Nordeste) em 19/11/2026.
# Confirmar também na página oficial da CAIXA antes de tratar como definitivo.
KNOWN = {
    3808: (1, 4, 7, 10, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 24),
    3809: (1, 3, 4, 5, 6, 8, 9, 11, 17, 18, 19, 20, 21, 23, 25),
    3810: (1, 5, 6, 7, 10, 11, 14, 15, 16, 17, 18, 19, 20, 23, 24),
}
# Anomalias de DATA (não de dezenas) já conhecidas e documentadas em docs/AUDITORIA_2026-11-19.md.
KNOWN_DATE_ANOMALIES = {3082, 3716}


def test_history_is_continuous_and_valid(history):
    assert [c for c, _, _ in history] == list(range(1, len(history) + 1))
    assert len(history) >= 3810
    for c, d, _ in history:
        assert len(d) == 15 and len(set(d)) == 15 and 1 <= d[0] and d[-1] <= 25, c


def test_no_duplicate_draws(history):
    draws = [d for _, d, _ in history]
    assert len(draws) == len(set(draws))


@pytest.mark.parametrize("contest,expected", KNOWN.items())
def test_recent_results_match_verified_values(history, contest, expected):
    assert history[contest - 1][1] == expected


def test_date_anomalies_are_only_the_known_ones(history):
    bad = set()
    for i in range(1, len(history)):
        a, b = history[i - 1][2], history[i][2]
        if a is None or b is None or b <= a:
            bad.add(history[i][0])
    assert bad <= KNOWN_DATE_ANOMALIES, f"novas anomalias de data: {sorted(bad - KNOWN_DATE_ANOMALIES)}"


def test_all_loaders_return_identical_draws(csv_path, history):
    ref = [(c, d) for c, d, _ in history]
    assert experiment.load_lotofacil(csv_path) == ref
    assert v6_probabilistic.load(csv_path) == ref
    assert [(c, d) for c, d, _ in v7_1_optimized.load(csv_path)] == ref
    assert list(stage2.load(csv_path).items()) == ref


def _write(tmp_path, lines):
    p = tmp_path / "h.csv"
    head = "Concurso,Data," + ",".join(f"bola {i}" for i in range(1, 16))
    p.write_text("\n".join([head] + lines) + "\n", encoding="utf-8")
    return str(p)


def _row(c, nums, date="01/01/2020"):
    return f"{c},{date}," + ",".join(str(n) for n in nums)


GOOD = list(range(1, 16))


def test_loader_rejects_gap(tmp_path):
    p = _write(tmp_path, [_row(1, GOOD), _row(3, GOOD[:-1] + [16])])
    with pytest.raises(ValueError):
        data_io.load_history(p)


def test_loader_rejects_repeated_numbers(tmp_path):
    p = _write(tmp_path, [_row(1, GOOD[:-1] + [1])])
    with pytest.raises(ValueError):
        data_io.load_history(p)


def test_loader_rejects_out_of_range(tmp_path):
    p = _write(tmp_path, [_row(1, GOOD[:-1] + [26])])
    with pytest.raises(ValueError):
        data_io.load_history(p)


def test_loader_rejects_missing_header(tmp_path):
    p = tmp_path / "h.csv"
    p.write_text(_row(1, GOOD) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        data_io.load_history(str(p))

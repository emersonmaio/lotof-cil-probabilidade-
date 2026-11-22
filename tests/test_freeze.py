"""Regras de congelamento: sem vazamento, sem sobrescrita, sem retroatividade."""
import json
from datetime import datetime, timedelta, timezone

import pytest

import data_io
import freeze_portfolio as fp


@pytest.fixture()
def truncated_csv(tmp_path, csv_path):
    """CSV até o concurso 3500 (alvo = 3501)."""
    lines = open(csv_path, encoding="utf-8-sig").read().splitlines()
    p = tmp_path / "h.csv"
    p.write_text("\n".join(lines[:3501]) + "\n", encoding="utf-8")
    return str(p)


def _now_after(csv, days):
    last = data_io.load_history(csv)[-1][2]
    return datetime(last.year, last.month, last.day, 12, tzinfo=timezone.utc) + timedelta(days=days)


def test_record_is_prospective_and_complete(truncated_csv):
    rec = fp.build_record(truncated_csv, 3501, 123, 40, now=_now_after(truncated_csv, 1))
    assert rec["prospective"] is True
    assert rec["history_through"] == 3500 and rec["target_contest"] == 3501
    assert rec["data_sha256"] == data_io.sha256_file(truncated_csv)
    assert set(rec["games"]) == {"V6-A", "V6-B", "V6-C", "V6-D", "V7-A", "V7-B", "V7-C", "V7-D",
                                 "V8-V7-A", "V8-V7-B", "V8-V7-C", "V8-V7-D", "ALEATORIO", "DIVERSIFICADO", "OTIMIZADO"}
    for name, games in rec["games"].items():
        assert len(games) == 10 and len({tuple(g) for g in games}) == 10, name


def test_target_must_be_next_contest(truncated_csv):
    now = _now_after(truncated_csv, 1)
    for bad in (3500, 3499, 3502, 3600):
        with pytest.raises(ValueError):
            fp.build_record(truncated_csv, bad, 1, 20, now=now)


def test_stale_history_is_refused_unless_flagged(truncated_csv):
    stale = _now_after(truncated_csv, 40)
    with pytest.raises(ValueError, match="retroativo"):
        fp.build_record(truncated_csv, 3501, 1, 20, now=stale)
    rec = fp.build_record(truncated_csv, 3501, 1, 20, now=stale, allow_retroactive=True)
    assert rec["prospective"] is False


def test_frozen_record_never_overwritten(tmp_path, truncated_csv):
    now = _now_after(truncated_csv, 1)
    rec = fp.build_record(truncated_csv, 3501, 1, 20, now=now)
    out = tmp_path / "frozen"
    path = fp.write_frozen(rec, out)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        fp.write_frozen(fp.build_record(truncated_csv, 3501, 999, 20, now=now), out)
    assert path.read_bytes() == original


def test_retroactive_cannot_shadow_prospective_for_same_target(tmp_path, truncated_csv):
    out = tmp_path / "frozen"
    fp.write_frozen(fp.build_record(truncated_csv, 3501, 1, 20, now=_now_after(truncated_csv, 1)), out)
    retro = fp.build_record(truncated_csv, 3501, 1, 20, now=_now_after(truncated_csv, 40), allow_retroactive=True)
    with pytest.raises(FileExistsError):
        fp.write_frozen(retro, out)


def test_manifest_detects_tampering(tmp_path, truncated_csv):
    out = tmp_path / "frozen"
    path = fp.write_frozen(fp.build_record(truncated_csv, 3501, 1, 20, now=_now_after(truncated_csv, 1)), out)
    assert fp.verify_manifest(out) == []
    data = json.loads(path.read_text(encoding="utf-8"))
    data["games"]["ALEATORIO"][0][0] = 99
    path.write_text(json.dumps(data), encoding="utf-8")
    assert fp.verify_manifest(out)


def test_games_depend_only_on_history_before_target(tmp_path, csv_path):
    """Mesma semente + mesmo histórico => mesmos jogos, mesmo que o CSV completo tenha concursos
    posteriores (o script só enxerga o arquivo truncado; aqui provamos que o conteúdo é função
    apenas do histórico fornecido)."""
    lines = open(csv_path, encoding="utf-8-sig").read().splitlines()
    a = tmp_path / "a.csv"
    a.write_text("\n".join(lines[:3401]) + "\n", encoding="utf-8")
    b = tmp_path / "b.csv"
    b.write_text("\n".join(lines[:3401]) + "\n", encoding="utf-8")
    now = _now_after(str(a), 1)
    r1 = fp.build_record(str(a), 3401, 5, 30, now=now)
    r2 = fp.build_record(str(b), 3401, 5, 30, now=now)
    assert r1["games"] == r2["games"]


def test_repo_frozen_dir_is_intact(root):
    assert fp.verify_manifest(root / "results" / "frozen") == []


def test_controls_change_from_one_contest_to_the_next(csv_path, tmp_path):
    """Regressão: com semente fixa os controles eram idênticos em todos os concursos."""
    lines = open(csv_path, encoding="utf-8-sig").read().splitlines()
    recs = []
    for n in (3400, 3401):
        p = tmp_path / f"h{n}.csv"
        p.write_text("\n".join(lines[: n + 1]) + "\n", encoding="utf-8")
        recs.append(fp.build_record(str(p), n + 1, 20261019, 20, now=_now_after(str(p), 1)))
    assert recs[0]["games"]["ALEATORIO"] != recs[1]["games"]["ALEATORIO"]
    assert recs[0]["games"]["DIVERSIFICADO"] != recs[1]["games"]["DIVERSIFICADO"]
    assert recs[0]["seed"] == 20261019 + 3401 and recs[0]["seed_base"] == 20261019

"""append_result + freeze + score_frozen: o ciclo prospectivo ponta a ponta, com as recusas."""
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import compare_models as cm
import data_io
import freeze_portfolio as fp
import score_frozen as sf
from append_result import append_result

PREREG = str(Path(__file__).resolve().parents[1] / "config" / "preregistration.json")
POOL = None


@pytest.fixture(scope="module")
def pool():
    return cm.null_pool(seed=1, r=600)


@pytest.fixture()
def world(tmp_path, csv_path):
    """CSV até 3500 + registro congelado do 3501 (gerado na véspera); depois o resultado real do 3501 entra."""
    lines = Path(csv_path).read_text(encoding="utf-8-sig").splitlines()
    p = tmp_path / "h.csv"
    p.write_text("\n".join(lines[:3501]) + "\n", encoding="utf-8")
    last = data_io.load_history(str(p))[-1][2]
    real = lines[3501].split(",")                     # linha do concurso 3501
    now = datetime(last.year, last.month, last.day, 12, tzinfo=timezone.utc) + timedelta(hours=1)
    rec = fp.build_record(str(p), 3501, 7, 20, now=now)
    frozen = tmp_path / "frozen"
    fp.write_frozen(rec, frozen)
    return {"csv": str(p), "frozen": frozen, "out": tmp_path / "prospective", "real": real, "tmp": tmp_path}


def _append_real(w):
    r = w["real"]
    return append_result(w["csv"], 3501, r[1], r[2:17], "teste automatizado")


# ---------------------------------------------------------------- append_result
def test_append_result_validations(world):
    r = world["real"]
    good = dict(csv_path=world["csv"], contest=3501, date_str=r[1], numbers=r[2:17], source="x")
    with pytest.raises(ValueError, match="fonte|source"):
        append_result(**{**good, "source": " "})
    with pytest.raises(ValueError, match="lacunas"):
        append_result(**{**good, "contest": 3502})
    with pytest.raises(ValueError, match="posterior"):
        append_result(**{**good, "date_str": "01/01/2000"})
    with pytest.raises(ValueError, match="15 dezenas"):
        append_result(**{**good, "numbers": r[2:16] + [r[2]]})
    with pytest.raises(ValueError, match="15 dezenas"):
        append_result(**{**good, "numbers": r[2:16] + ["26"]})
    assert len(data_io.load_history(world["csv"])) == 3500          # nada foi gravado nas recusas


def test_append_result_writes_same_format_and_source(world):
    line = _append_real(world)
    nums = sorted(int(x) for x in world["real"][2:17])
    assert line == f"3501,{world['real'][1]}," + ",".join(f"{n:02d}" for n in nums) + "\n"
    assert len(data_io.load_history(world["csv"])) == 3501
    src = (Path(world["csv"]).with_name("SOURCES.csv")).read_text(encoding="utf-8")
    assert "3501,teste automatizado" in src


# ---------------------------------------------------------------- score_frozen
def test_score_matches_manual_hits_and_logs_once(world, pool):
    _append_real(world)
    e = sf.score_contest(world["csv"], 3501, world["frozen"], world["out"], pool=pool)
    draw = set(data_io.load_history(world["csv"])[3500][1])
    rec = json.loads((world["frozen"] / "concurso_3501_congelado.json").read_text(encoding="utf-8"))
    for name, games in rec["games"].items():
        assert e["models"][name]["hits"] == [len(set(g) & draw) for g in games], name
    with pytest.raises(FileExistsError):
        sf.score_contest(world["csv"], 3501, world["frozen"], world["out"], pool=pool)
    rows = sf.summarize(world["out"], PREREG)
    assert rows and "insuficiente" in (world["out"] / "SUMMARY.md").read_text(encoding="utf-8")


def test_score_refuses_before_result_exists(world, pool):
    with pytest.raises(ValueError, match="ainda não está"):
        sf.score_contest(world["csv"], 3501, world["frozen"], world["out"], pool=pool)


def test_score_refuses_changed_history(world, pool):
    _append_real(world)
    p = Path(world["csv"])
    lines = p.read_text(encoding="utf-8").splitlines()
    parts = lines[1500].split(",")
    present = {int(x) for x in parts[2:17]}
    parts[2] = f"{next(n for n in range(1, 26) if n not in present):02d}"      # troca 1 dezena: linha continua VÁLIDA
    lines[1500] = ",".join(parts)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    data_io.load_history(str(p))                                               # o arquivo ainda carrega normalmente
    with pytest.raises(ValueError, match="alterado depois do congelamento"):
        sf.score_contest(world["csv"], 3501, world["frozen"], world["out"], pool=pool)


def test_score_refuses_tampered_record(world, pool):
    _append_real(world)
    f = world["frozen"] / "concurso_3501_congelado.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["games"]["ALEATORIO"][0][0] = 99
    f.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="Manifesto"):
        sf.score_contest(world["csv"], 3501, world["frozen"], world["out"], pool=pool)


def test_score_refuses_record_generated_after_draw(tmp_path, csv_path, pool):
    lines = Path(csv_path).read_text(encoding="utf-8-sig").splitlines()
    p = tmp_path / "h.csv"
    p.write_text("\n".join(lines[:3501]) + "\n", encoding="utf-8")
    full = tmp_path / "full.csv"
    full.write_text("\n".join(lines[:3502]) + "\n", encoding="utf-8")
    draw_date = data_io.load_history(str(full))[3500][2]
    last = data_io.load_history(str(p))[-1][2]
    late = datetime(draw_date.year, draw_date.month, draw_date.day, 23, tzinfo=timezone.utc)   # depois do corte das 22h UTC
    if (late.date() - last).days > 4:
        pytest.skip("intervalo grande entre concursos")
    rec = fp.build_record(str(p), 3501, 7, 20, now=late)
    fp.write_frozen(rec, tmp_path / "frozen")
    with pytest.raises(ValueError, match="pré-sorteio"):
        sf.score_contest(str(full), 3501, tmp_path / "frozen", tmp_path / "out", pool=pool)


def test_score_refuses_retroactive_record(tmp_path, csv_path, pool):
    lines = Path(csv_path).read_text(encoding="utf-8-sig").splitlines()
    p = tmp_path / "h.csv"
    p.write_text("\n".join(lines[:3501]) + "\n", encoding="utf-8")
    rec = fp.build_record(str(p), 3501, 7, 20, now=datetime(2026, 11, 20, tzinfo=timezone.utc), allow_retroactive=True)
    fp.write_frozen(rec, tmp_path / "frozen")
    p.write_text("\n".join(lines[:3502]) + "\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        sf.score_contest(str(p), 3501, tmp_path / "frozen", tmp_path / "out", pool=pool)


def test_preregistration_is_consistent(root):
    pr = json.loads((root / "config" / "preregistration.json").read_text(encoding="utf-8"))
    from statistics import NormalDist
    assert pr["limiar_z_bonferroni"] == pytest.approx(NormalDist().inv_cdf(1 - pr["alfa_familia"] / pr["familia_de_testes"]), abs=1e-3)
    assert len(pr["bracos_primarios"]) == pr["familia_de_testes"]
    games = fp.generate_games([(c, d, sum(1 << (n - 1) for n in d)) for c, d, _ in data_io.load_history(str(root / "data" / "lotofacil.csv"))[:3000]], 1, 20)
    assert set(pr["bracos_primarios"]) | set(pr["controles"]) <= set(games)

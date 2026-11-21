"""O holdout padrão deve ir até o último concurso do CSV (não parar silenciosamente em 3794)."""
import json
import re
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"


def test_no_hardcoded_holdout_end_default():
    for p in SRC.glob("*.py"):
        assert not re.search(r"holdout-end[^\n]*default\s*=\s*3\d{3}", p.read_text(encoding="utf-8")), p.name


def test_v71_default_holdout_reaches_last_contest(tmp_path, csv_path, history):
    last = history[-1][0]
    out = subprocess.run(
        [sys.executable, str(SRC / "v7_1_optimized.py"), "--csv", csv_path, "--out", str(tmp_path),
         "--validation-start", str(last - 60), "--validation-end", str(last - 31), "--holdout-start", str(last - 30)],
        capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["holdout"]["contests"] == 31

"""Leitura e validação estrita do histórico da Lotofácil.

Módulo único de referência para os scripts novos (compare_models, freeze_portfolio,
backtest_8plus2). Os loaders antigos (experiment, v6, v7_1, stage2) foram mantidos
para preservar a reprodutibilidade das versões anteriores; tests/test_data_integrity.py
garante que todos devolvem exatamente os mesmos dados.
"""
import csv
import hashlib
from datetime import date, datetime

K = 15
MAX_NUM = 25


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_history(path):
    """Devolve lista de (concurso, dezenas_ordenadas, data|None), validada.

    Levanta ValueError se: linha com <17 colunas, dezenas repetidas/fora de 1..25,
    concursos duplicados, faltantes ou fora de ordem.
    """
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or header[0].strip().lower() != "concurso":
            raise ValueError("Cabeçalho ausente: a primeira coluna deve ser 'Concurso'.")
        for line_no, row in enumerate(reader, start=2):
            if not row or not row[0].strip():
                continue
            if not row[0].strip().isdigit():
                raise ValueError(f"Linha {line_no}: concurso inválido {row[0]!r}")
            contest = int(row[0])
            if len(row) < 2 + K:
                raise ValueError(f"Concurso {contest}: colunas insuficientes ({len(row)})")
            draw = tuple(sorted(int(x) for x in row[2:2 + K]))
            if len(set(draw)) != K or draw[0] < 1 or draw[-1] > MAX_NUM:
                raise ValueError(f"Concurso {contest}: dezenas inválidas {draw}")
            try:
                d = datetime.strptime(row[1].strip(), "%d/%m/%Y").date()
            except ValueError:
                d = None
            rows.append((contest, draw, d))
    ids = [c for c, _, _ in rows]
    if not ids:
        raise ValueError("Histórico vazio.")
    if ids != list(range(1, len(ids) + 1)):
        raise ValueError("Concursos ausentes, duplicados ou fora de ordem (esperado 1..N contínuo).")
    return rows


def last_contest_date(rows):
    """Data do último concurso do histórico (ou None se não parseável)."""
    return rows[-1][2]


def staleness_days(rows, today=None):
    d = last_contest_date(rows)
    if d is None:
        return None
    today = today or date.today()
    return (today - d).days

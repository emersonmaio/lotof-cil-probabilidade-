"""Acrescenta UM resultado oficial ao histórico, com validação e registro de proveniência.

Uso:
  python src/append_result.py --csv data/lotofacil.csv --contest 3811 --date 22/10/2026 \
      --numbers 01,02,...,25 --source "https://loterias.caixa.gov.br/... (conferido em 22/10/2026)"

Regras: o concurso tem de ser exatamente o próximo (sem lacunas), a data tem de ser posterior à do
último concurso, 15 dezenas únicas entre 1 e 25. A fonte é obrigatória e fica em data/SOURCES.csv.
O arquivo é gravado no mesmo formato das linhas atuais (dezenas ordenadas, dois dígitos, fim de linha LF).
"""
import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from data_io import load_history


def append_result(csv_path, contest, date_str, numbers, source):
    if not source or not source.strip():
        raise ValueError("--source é obrigatório (de onde o resultado foi conferido).")
    hist = load_history(csv_path)
    if contest != hist[-1][0] + 1:
        raise ValueError(f"Próximo concurso esperado: {hist[-1][0] + 1} (recebido {contest}); não pode haver lacunas.")
    try:
        d = datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError("Data inválida; use dd/mm/aaaa.")
    if hist[-1][2] and d <= hist[-1][2]:
        raise ValueError(f"A data {date_str} não é posterior à do concurso {hist[-1][0]} ({hist[-1][2]:%d/%m/%Y}).")
    nums = sorted(int(x) for x in numbers)
    if len(nums) != 15 or len(set(nums)) != 15 or nums[0] < 1 or nums[-1] > 25:
        raise ValueError("São necessárias 15 dezenas únicas entre 01 e 25.")
    raw = Path(csv_path).read_bytes()
    if b"\r\n" in raw:
        raise ValueError("CSV com fim de linha CRLF; normalize para LF antes de acrescentar.")
    line = f"{contest},{date_str}," + ",".join(f"{n:02d}" for n in nums) + "\n"
    with open(csv_path, "ab") as f:
        if not raw.endswith(b"\n"):
            f.write(b"\n")
        f.write(line.encode("utf-8"))
    load_history(csv_path)  # revalida o arquivo inteiro após a escrita
    src = Path(csv_path).with_name("SOURCES.csv")
    new = not src.exists()
    with open(src, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["concurso", "fonte", "registrado_em_utc"])
        w.writerow([contest, source.strip(), datetime.now(timezone.utc).isoformat(timespec="seconds")])
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--contest", type=int, required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--numbers", required=True, help="15 dezenas separadas por vírgula")
    ap.add_argument("--source", required=True)
    a = ap.parse_args()
    try:
        line = append_result(a.csv, a.contest, a.date, a.numbers.split(","), a.source)
    except ValueError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
    print("Acrescentado:", line.strip())


if __name__ == "__main__":
    main()

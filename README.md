# Lotofácil — Probabilidade / Backtest 8+2

Projeto de experimentação para avaliar, sem olhar o resultado futuro, estratégias de 10 jogos formadas por **8 jogos-base + 2 complementares**.

## Objetivo
Medir média do melhor jogo, média dos 10 jogos e frequência de 11, 12, 13, 14 e 15 acertos. Isto testa hipóteses; não implica previsão de sorteios aleatórios.

## Dados
A base de trabalho está até o concurso **3810 (21/10/2026)**. Em 19/11/2026 o concurso 3827 (11/11) já havia sido sorteado, portanto a base está defasada: atualize o CSV com os resultados oficiais antes de congelar qualquer portfólio (o script de congelamento recusa histórico velho). O próximo concurso deve ser tratado como desconhecido até o resultado oficial estar disponível.

Fonte oficial CAIXA:
https://loterias.caixa.gov.br/Paginas/LOTOFACIL.aspx

Coloque o CSV em `data/lotofacil.csv`, mantendo o cabeçalho com concurso, data e 15 dezenas.

## Estratégias
- random10: baseline aleatório.
- freq8_cov2: 8 por frequência + 2 por cobertura.
- blend8_cov2: 8 por frequência/recência + 2 por cobertura.
- freq8_inv2: 8 por frequência + 2 por ponderação inversa.
- blend8_inv2: combinação de frequência/recência + complementação inversa.
- **V6**: pontuação probabilística suavizada em múltiplas janelas + recência + geração de candidatos + seleção de portfólio com penalização de sobreposição.

## Backtest
O concurso-alvo nunca entra na construção dos jogos. Exemplo: para avaliar t, somente concursos < t são usados.

Validação: 2275–3032.
Holdout: 3033 até o último concurso da base (padrão dinâmico). Atenção: como V6/V7/V7.1/V8 foram desenvolvidas depois de observar esse intervalo, ele não é um holdout independente (ver `docs/TESTE.md` e `docs/AUDITORIA_2026-11-19.md`).

A seleção da configuração ocorre exclusivamente na validação. O holdout é usado apenas depois para medir desempenho fora da amostra.

## Auditoria de estabilidade
`src/v6_stability.py` repete a seleção temporal com várias sementes. Para cada semente:
1. avalia as configurações na validação;
2. escolhe uma configuração somente pela validação;
3. avalia essa configuração uma vez no holdout;
4. agrega média, desvio-padrão e frequência de seleção.

Isso reduz o risco de concluir que uma diferença observada veio apenas de uma semente específica.

## Protocolo temporal
Para qualquer concurso futuro:
1. usar somente concursos anteriores ao alvo;
2. gerar e armazenar o portfólio antes do sorteio;
3. depois do resultado oficial, avaliar o portfólio armazenado;
4. somente então acrescentar o resultado ao CSV;
5. repetir os testes walk-forward.

Um registro pré-sorteio armazenado não deve ser regenerado depois que o resultado se torna conhecido.

## Status
V6 é uma hipótese experimental. Resultados históricos fora da amostra não garantem desempenho futuro e não devem ser tratados como previsão de sorteios.

## Testes e auditoria
- `python -m pytest -q -m "not slow"` — dados, vazamento temporal, determinismo, baseline, congelamento, workflows.
- `python src/compare_models.py --csv data/lotofacil.csv --out results/compare` — V6, V7.1, V8 e aleatório sob as mesmas condições, com teste contra a hipótese nula.
- `python src/randomness_audit.py --csv data/lotofacil.csv` — testes de aleatoriedade do histórico (Monte Carlo + Holm).
- `python src/hypotheses_test.py --csv data/lotofacil.csv` — 11 regras pré-definidas, teste walk-forward com Bonferroni.
- `python src/append_result.py ...` e `python src/score_frozen.py ...` — ciclo prospectivo (ver `docs/GUIA_GITHUB.md`).
- Auditoria e diagnóstico: `docs/AUDITORIA_2026-11-19.md` (ciclo 1) e `docs/AUDITORIA_CICLO2.md` (ciclo 2).
- Onde colocar cada coisa no GitHub e rotina por concurso: `docs/GUIA_GITHUB.md`.
- Pré-registro da avaliação prospectiva: `config/preregistration.json`.
- Portfólios congelados ficam em `results/frozen/` com `MANIFEST.jsonl` (SHA-256); nunca são regenerados.

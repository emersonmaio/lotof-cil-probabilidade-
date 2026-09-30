# Lotofácil — Probabilidade / Backtest 8+2

Projeto de experimentação para avaliar, sem olhar o resultado futuro, estratégias de 10 jogos formadas por **8 jogos-base + 2 complementares**.

## Objetivo
Medir média do melhor jogo, média dos 10 jogos e frequência de 11, 12, 13, 14 e 15 acertos. Isto testa hipóteses; não implica previsão de sorteios aleatórios.

## Dados
Fonte histórica consultada em 30/09/2026: ValorFinal, que declara como fonte primária as Loterias CAIXA:
https://valorfinal.com.br/dados/loteria-lotofacil

A versão consultada contém 3.792 concursos, de 29/09/2003 a 29/09/2026. SHA-256 do CSV informado pela fonte:
6b25243187ae82e6346598235f06205db5e316844675620e5bd5e... (ver fonte para o hash completo).

Fonte oficial CAIXA:
https://loterias.caixa.gov.br/Paginas/LOTOFACIL.aspx

Coloque o CSV em data/lotofacil.csv, mantendo o cabeçalho concurso;data;dezenas.

## Estratégias
- random10: baseline aleatório.
- freq8_cov2: 8 por frequência + 2 por cobertura.
- blend8_cov2: 8 por frequência/recência + 2 por cobertura.
- freq8_inv2: 8 por frequência + 2 por ponderação inversa.
- blend8_inv2: combinação de frequência/recência + complementação inversa.

## Backtest
O concurso-alvo nunca entra na construção dos jogos. Exemplo: para avaliar t, somente concursos < t são usados.

```bash
python src/backtest_8plus2.py --csv data/lotofacil.csv --out results/backtest.csv --start 500 --end 3792 --window 100
```

Para validação séria, repita com várias sementes/janelas e mantenha um holdout final intocado.

## Status
V5: 8+2 registrado como hipótese de diversificação/cobertura. Qualquer diferença observada precisa sobreviver a testes fora da amostra antes de ser considerada robusta.

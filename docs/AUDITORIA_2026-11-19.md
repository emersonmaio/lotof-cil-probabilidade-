# Auditoria técnica — ciclo 1 (19/11/2026)

Base auditada: `data/lotofacil.csv` (3.810 concursos, SHA-256 `d40eaac7…ff3ca4`). Não foi possível ver o estado do
GitHub (commits, execuções das Actions): o trabalho foi feito sobre o zip do repositório. Nada abaixo foi
executado nas GitHub Actions.

## 1. Conclusões

1. **Nenhuma versão (V6, V7.1, V8) demonstra vantagem sobre o acaso.** O resultado documentado de V8
   (+0,091 acerto sobre o baseline aleatório) reproduz exatamente, mas é explicado por **diversificação** dos 10
   jogos, não por previsão (seção 4).
2. **O histórico está defasado.** Termina no 3810 (21/10/2026); o 3827 foi sorteado em 11/11/2026. Congelar o 3811
   hoje seria retroativo. O script agora recusa.
3. **A integridade do congelamento foi reforçada** (sem sobrescrita, hash, manifesto append-only, recusa de
   histórico velho).
4. O holdout 3033–3794 **deixou de ser independente** para V7, V7.1 e V8 (foram desenhadas depois de observá-lo).
   Só a avaliação prospectiva congelada é evidência independente.

## 2. Estado verificado dos dados

| Verificação | Resultado |
|---|---|
| Concursos 1..3810 contínuos, sem duplicatas | OK |
| 15 dezenas únicas em 1..25 em todas as linhas | OK |
| Nenhum sorteio repetido (15 dezenas idênticas) | OK |
| 3808, 3809, 3810 conferidos em cobertura jornalística (Diário do Nordeste) | Coincidem com o CSV |
| Conferência na página oficial da CAIXA | **Não feita** (site não acessível aqui) |
| Datas: 3082 (08/04/2024, anterior ao 3081 de 17/04/2024) e 3716 (20/06/2026, igual ao 3715) | Anomalias **de data**; dezenas não afetadas |
| Sorteios aos domingos (13 no total, 12 deles em 2026) | Plausível; não tratado como erro |

## 3. Diagnóstico

| # | Problema | Arquivo | Causa | Correção | Teste | Resultado |
|---|---|---|---|---|---|---|
| 1 | Congelar o "próximo" concurso com histórico velho seria retroativo | `freeze_portfolio.py`, workflows | O alvo era só `último+1`; nada comparava com a data atual | Recusa se o último concurso tem mais de 4 dias; `--allow-retroactive` marca `prospective=false` e sufixo `_RETROATIVO` | `test_stale_history_is_refused_unless_flagged` | Corrigido |
| 2 | Registro congelado podia ser sobrescrito/regenerado; só existia como artefato temporário | `freeze_portfolio.py`, `freeze-portfolio.yml` | `write_text` sem proteção; sem commit | Gravação exclusiva (`open(..., "x")`), SHA-256 do CSV e do registro, `MANIFEST.jsonl` append-only, `--verify-only`, commit do registro pela Action | `test_frozen_record_never_overwritten`, `test_manifest_detects_tampering` | Corrigido (passo de commit da Action **não testado**: não há como rodar Actions aqui) |
| 3 | Dois workflows congelavam o mesmo alvo com a mesma semente | `v6.yml`, `freeze-portfolio.yml` | Duplicação | Só `freeze-portfolio.yml` congela; `v6.yml` apenas publica os relatórios | `test_only_freeze_workflow_freezes_portfolios` | Corrigido |
| 4 | `full-backtest.yml` baixava CSV de site de terceiros por cima de `data/lotofacil.csv`; `backtest_8plus2.py` não lia o CSV do repositório (`KeyError: 'dezenas'`); `--end 3792` fixo | `full-backtest.yml`, `backtest_8plus2.py` | Formato divergente + fonte não validada | Lê o CSV do repositório via `data_io.load_history`; sem download; sem fim fixo | `test_no_workflow_overwrites_repository_history`, execução manual de `backtest_8plus2.py` | Corrigido |
| 5 | `--holdout-end` padrão fixo em 3794 em 8 scripts (mesmo defeito já corrigido em `experiment.py`) | `v6_*`, `v7_*`, `v7_1_*`, `v8_*` | Valor literal | Padrão = último concurso do CSV | `test_v71_default_holdout_reaches_last_contest` | Corrigido |
| 6 | `requirements.txt` com `python>=3.10` (inválido para pip) | `requirements.txt` | — | `numpy`, `pytest`, `PyYAML` | workflow `tests.yml` | Corrigido |
| 7 | Nenhum teste automatizado | — | — | `tests/` (58+ testes) e `tests.yml` | — | Corrigido |
| 8 | `docs/TESTE.md` com `\n` literais, cita `lotofacil.csv.gz` inexistente e holdout 3791; README em 3794 | docs | Desatualizado | Reescritos | — | Corrigido |
| 9 | **Baseline inadequado** para portfólios diversificados | método | O baseline `random10` (10 bilhetes independentes) tem E[melhor]=10,840; um portfólio de 10 jogos pouco sobrepostos tem E≈10,923 **mesmo sem informação nenhuma** | `src/compare_models.py`: teste pareado contra o nulo de cada portfólio + controle "só diversificação" | `tests/test_compare_fidelity.py` | Corrigido (método); ver seção 4 |
| 10 | Holdout contaminado pelo desenvolvimento | docs | V7/V7.1/V8 criadas após ver 3033–3794 | Aviso em README e `TESTE.md` | — | **Pendente** (só a avaliação prospectiva resolve) |
| 11 | Seleção da configuração por contagem de 13+ na validação (~10 eventos em 758 concursos) é ruído: a configuração escolhida muda entre sementes (V6: A/B/C; V7.1: A/C/D) | `v6_*`, `v7_1_*` | Regra de seleção instável | Não alterada (preservar versões); documentado | — | **Pendente** (sugestão: regra de seleção estável, p.ex. média na validação, definida antes) |
| 12 | Congelamento gera 13 portfólios (12 modelos + aleatório) sem declarar o modelo primário → múltiplas comparações | `freeze_portfolio.py` | Sem pré-registro | — | — | **Pendente**: declarar antes quais portfólios contam |
| 13 | Anomalias de data 3082 e 3716 | CSV | Provável erro de digitação na fonte | Guardado por teste (`KNOWN_DATE_ANOMALIES`); dezenas intactas | `test_date_anomalies_are_only_the_known_ones` | **Pendente**: corrigir as datas na fonte oficial |
| 14 | 3808–3810 só conferidos em imprensa | CSV | Sem acesso à CAIXA | — | `test_recent_results_match_verified_values` | **Pendente**: conferir na CAIXA |

### Investigado e **não** confirmado como defeito

- Vazamento temporal: V6, V7.1, V8 e `experiment.py` usam somente concursos anteriores ao alvo
  (testes com troca do alvo e dos futuros por sorteios aleatórios deixam o estado idêntico; controle negativo
  confirma que o teste detecta mudanças no passado).
- V7.1 equivale ao V7 (escores individuais e de pares iguais a 1e-9).
- Os quatro loaders antigos devolvem exatamente os mesmos dados.
- `weighted_game` não produz jogo com menos de 15 dezenas no caso-limite testado.
- Reprodutibilidade: com o CSV truncado em 3804, `v8_stability.py` devolve exatamente os números de
  `TEMPORAL_AUDIT.md` (10,920207; 10,829015; +0,091192).
- Código morto cosmético em `v7_1_optimized.py` (loop `GAME_PAIRS` com `break`): inofensivo, não alterado.

## 4. Comparação V6 × V7.1 × V8 × baseline

Condições: holdout 3033–3810 (778 concursos), 10 jogos por concurso para todos, 5 sementes
(20261002 + i·1009), configuração escolhida só na validação 2275–3032 pela regra de cada versão, V8 com 300
candidatos. Para cada concurso e cada portfólio congelado, o valor esperado e a variância do "melhor jogo" sob
sorteio uniforme foram estimados contra 4.000 sorteios aleatórios; a diferença observada − esperada tem média
zero sob H0 e é testada por Z (martingale). O baseline aleatório passa pelo mesmo procedimento e serve de
calibração.

| Modelo | Melhor jogo (média) | Esperado sob H0 | Diferença | EP | Z por semente | 13+ obs / esp. |
|---|---:|---:|---:|---:|---|---:|
| V6 | 10,9329 | 10,9235 | +0,0094 | 0,0249 | −1,48 · 0,89 · 1,21 · 0,25 · 1,01 | 13,0 / 11,6 |
| V7.1 | 10,9195 | 10,9230 | −0,0035 | 0,0249 | −0,63 · 0,87 · 0,55 · −1,81 · 0,33 | 10,6 / 11,6 |
| V8 | 10,9206 | 10,9229 | −0,0024 | 0,0248 | 1,61 · −1,73 · −0,55 · 0,84 · −0,65 | 11,8 / 11,5 |
| Aleatório (10 bilhetes) | 10,8303 | 10,8398 | −0,0095 | 0,0269 | −1,64 · 1,44 · −0,07 · −1,53 · 0,04 | 10,8 / 11,5 |
| Só diversificação (sem dados) | 10,9185 | 10,9272 | −0,0087 | 0,0248 | −0,28 · 0,39 · −1,89 · −0,64 · 0,67 | 11,0 / 11,6 |

Leitura:

- Os três modelos ficam em ~10,92–10,93, **igual ao controle sem histórico** (10,9185). O ganho de ~0,09 sobre
  o aleatório puro é o efeito de diversificar os 10 jogos, que o próprio nulo já prevê (10,923 contra 10,840).
- Nenhum |Z| passa de 1,96; os Z do baseline aleatório (calibração) têm a mesma amplitude, como esperado de N(0,1).
- Estabilidade por blocos de 100 concursos: a diferença é positiva em apenas 3–4 de 8 blocos em média, sem padrão.
- Frequências de 13+ estão dentro do esperado; 14+ e 15 são raros demais para qualquer teste (no máximo um 14+ por execução e nenhum 15 no período).

Limitações: as 5 sementes compartilham os mesmos concursos, então não reduzem o erro amostral entre concursos
(usa-se o EP de uma execução); o nulo é estimado com 4.000 sorteios (erro desprezível frente ao EP); testamos
três versões sem correção para múltiplas comparações, o que só tornaria qualquer achado mais difícil — e
nenhum apareceu. Ausência de efeito detectável não prova ausência de efeito: com 778 concursos, o EP de 0,025
só detectaria (com ~80% de poder) diferenças acima de ~0,07 acerto no melhor jogo.

## 5. Hipóteses

| Hipótese | Situação |
|---|---|
| Frequência histórica/recente, janelas 10–200, recência, coocorrência (V6/V7/V7.1/V8) | Testadas aqui: sem vantagem além da diversificação |
| Diversificação do portfólio melhora o "melhor jogo" | **Confirmada** (+0,083 sob H0), mas é propriedade combinatória, não previsão |
| Atraso das dezenas, soma, pares/ímpares, repetição entre concursos, posições | Não testadas neste ciclo |
| Características físicas das bolas/globo | **Não testável**: não há dados físicos medidos; não incorporada |

## 6. Como reproduzir

```
python -m pytest -q -m "not slow"
python src/compare_models.py --csv data/lotofacil.csv --out results/compare --seeds 5
python src/freeze_portfolio.py --csv data/lotofacil.csv --target <ultimo+1> --out results/frozen
```

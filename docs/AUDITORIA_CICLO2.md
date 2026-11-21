# Auditoria técnica — ciclo 2 (20/11/2026)

Continuação de `AUDITORIA_2026-11-19.md`. Mesma base (`data/lotofacil.csv`, concursos 1–3810) e mesmas limitações:
sem acesso ao GitHub/Actions, nada foi executado nas Actions.

## 1. Resumo

1. **Aleatoriedade do histórico.** De 10 testes, só a uniformidade das frequências por dezena rejeita H0 após
   correção de Holm (p ≈ 0,0005). Repetição entre concursos, dependência lag-1, atraso, soma, paridade,
   coocorrência de pares e posições das bolas não mostram desvio.
2. **Hipóteses de seleção.** Das 11 regras pré-definidas (frequência em 6 janelas e total, dezenas frias,
   atraso, repetição do concurso anterior), **nenhuma** supera o acaso após Bonferroni. A melhor (`freq_all`)
   rende +0,033 acerto por bilhete (Z = 1,57; p = 0,12).
3. **Novo defeito corrigido:** com semente fixa, os controles `ALEATORIO` e `DIVERSIFICADO` saíam idênticos
   em todos os concursos. A semente efetiva passou a ser `base + alvo`.
4. **Ciclo prospectivo automatizado** (`append_result.py`, `score_frozen.py`, `config/preregistration.json`).

## 2. Aleatoriedade do histórico (`src/randomness_audit.py`)

Cada estatística é comparada com 2.000 históricos simulados sob H0 (sorteios uniformes independentes, mesmo número
de concursos). Holm sobre os 10 testes. Calibração: em histórico simulado nenhum teste rejeita; com dependência
injetada o teste de repetição detecta (`tests/test_audit_and_hypotheses.py`).

| Teste | p (MC) | p (Holm) | Rejeita H0? |
|---|---:|---:|---|
| T1 uniformidade das frequências por dezena | 0,0005 | 0,005 | **sim** |
| T2 repetição entre concursos consecutivos | 0,213 | 1,0 | não |
| T3 dependência lag-1 (ajustada pela marginal) | 0,724 | 1,0 | não |
| T4 atraso (ajustado pela marginal) | 0,039 | 0,347 | não |
| T5a soma (média) | 0,716 | 1,0 | não |
| T5b soma (variância) | 0,316 | 1,0 | não |
| T6 paridade | 0,913 | 1,0 | não |
| T7 coocorrência de pares (ajustada pelas marginais) | 0,830 | 1,0 | não |
| T8 posições (3.787 concursos com ordem de sorteio) | 0,406 | 1,0 | não |
| T9 primeira bola | 0,690 | 1,0 | não |

**Correção de método feita durante o ciclo.** A primeira versão de T3, T4 e T7 comparava com 0,6 e com
frequências uniformes, e "rejeitava" apenas porque as frequências por dezena não são uniformes (T1). Foram
reescritos para comparar com a marginal da própria dezena; só T1 permanece.

**Sobre T1 (leitura cuidadosa).** Há desvio real de frequência por dezena: 16 aparece em 57,2% dos sorteios
(Z = −3,6) e 20, 25 e 10 em ~62% (Z ≈ +2,6 a +3,0), contra 60% esperado. Análise **exploratória e post hoc**
(não entra na correção): o desvio se concentra nos concursos 2001–3000 (p = 0,0025) e não aparece em 3001–3810
(p = 0,51). Isso é compatível com uma assimetria que mudou ao longo do tempo (ou com acaso em um período, dado
que os períodos foram olhados depois), e **não** autoriza apostar nessas dezenas: a regra "mais frequentes no
histórico todo" (`freq_all`) não passa no teste walk-forward da seção 3.

## 3. Hipóteses de seleção (`src/hypotheses_test.py`)

Para cada concurso (a partir do 301), cada regra pontua as dezenas com os concursos anteriores e forma **um**
bilhete com as 15 melhores. Sob H0 o bilhete acerta em média 9 (variância 1,5), então Z = (média − 9)/√(1,5/n).
Teste bem mais potente que "melhor de 10 jogos": com 3.510 concursos detecta ~0,08 acerto após Bonferroni.
Calibração: em 240 estatísticas simuladas sob H0 (20 históricos × 12 regras, incluindo a removida por duplicidade) Z tem média −0,07 e desvio 0,99; com viés injetado (dezenas 1–5 com peso 1,25)
`freq_all` dá Z ≈ 9.

K = 11 hipóteses, α = 0,05/11 = 0,0045 (|Z| > 2,84).

| Hipótese | Todos (diff; Z) | Desenvolvimento (≤3032) | Holdout (≥3033) |
|---|---|---|---|
| freq_5 | +0,005 (0,22) | −0,004 (−0,19) | +0,036 (0,82) |
| freq_10 | −0,028 (−1,36) | −0,037 (−1,56) | +0,001 (0,03) |
| freq_20 | −0,007 (−0,34) | −0,026 (−1,11) | +0,059 (1,35) |
| freq_50 | +0,011 (0,55) | +0,016 (0,69) | −0,005 (−0,12) |
| freq_100 | +0,013 (0,63) | +0,017 (0,70) | +0,001 (0,03) |
| freq_200 | +0,007 (0,34) | +0,023 (0,97) | −0,048 (−1,08) |
| freq_all | +0,033 (1,57) | +0,026 (1,11) | +0,055 (1,26) |
| cold_20 | −0,013 (−0,65) | −0,018 (−0,78) | +0,004 (0,09) |
| cold_100 | −0,015 (−0,74) | −0,026 (−1,11) | +0,022 (0,50) |
| overdue | −0,002 (−0,11) | −0,002 (−0,09) | −0,003 (−0,06) |
| repeat_prev | −0,030 (−1,43) | −0,041 (−1,76) | +0,012 (0,26) |

Nenhuma rejeita. A hipótese "anti-repetição" foi removida da lista por ser **idêntica** a `overdue` (as 10 dezenas
que não saíram no anterior têm sempre o maior atraso); manter as duas contaria duas vezes o mesmo teste.
Ausência de significância não prova ausência de efeito menor que ~0,08 acerto por bilhete.

## 4. Defeitos e melhorias deste ciclo

| # | Problema / melhoria | Arquivo | Teste |
|---|---|---|---|
| 15 | **Controles idênticos em todos os concursos** (semente fixa 20261019) | `freeze_portfolio.py` | `test_controls_change_from_one_contest_to_the_next` |
| 16 | Não havia como acrescentar um resultado com validação e fonte | `append_result.py` (novo) | `test_append_result_*` |
| 17 | Pontuação do registro congelado era manual e sem checagens | `score_frozen.py` (novo) | `test_score_*` (hash do histórico, manifesto, corte pré-sorteio, retroativo, duplicidade) |
| 18 | Sem pré-registro: 14 portfólios, qualquer um poderia ser eleito depois | `config/preregistration.json` | `test_preregistration_is_consistent` |
| 19 | Sem controle "só diversificação" no congelamento | `diversified.py`, `freeze_portfolio.py` | `test_record_is_prospective_and_complete` |
| 20 | Workflow não pontuava o concurso anterior | `freeze-portfolio.yml` | `test_freeze_workflow_*` |

Pré-registro (`config/preregistration.json`): braços primários `V6-A`, `V7-C`, `V8-V7-D` (configuração mais
escolhida pela regra de validação nas 5 sementes; empate → ordem alfabética); controles `ALEATORIO` e
`DIVERSIFICADO`; mínimo de 100 concursos prospectivos; Bonferroni sobre 3 braços (Z ≥ 2,128 unilateral) e
maioria dos blocos de 25 concursos positiva. Abaixo de 100 concursos o resumo diz "insuficiente".

## 5. Pendências

- Conferir 3808–3810 na CAIXA e **atualizar o CSV** até o último concurso realizado com `append_result.py`
  (o histórico está ~3 semanas defasado; o congelamento recusa até isso ser feito).
- Corrigir as datas dos concursos 3082 e 3716 na fonte.
- Congelar o próximo concurso **antes** do sorteio e acumular ≥ 100 concursos prospectivos.
- Ainda não testadas: modelos com várias variáveis combinadas (regressão logística regularizada) — só vale
  testar com avaliação walk-forward e Bonferroni, porque a evidência acima não indica sinal a explorar.
- Características físicas das bolas/globo: sem dados medidos, não testável.

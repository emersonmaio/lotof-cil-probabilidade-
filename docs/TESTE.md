# Protocolo de teste

## Base
`data/lotofacil.csv` é a base de trabalho (cabeçalho `Concurso,Data,bola 1..bola 15`). Os scripts validam
15 dezenas únicas entre 01 e 25 e a continuidade dos concursos (1..N sem lacunas). A validação central está em
`src/data_io.py` e é coberta por `tests/test_data_integrity.py`.

## Separação temporal
- Treino implícito: tudo anterior ao concurso avaliado.
- Validação: 2275-3032.
- Holdout: 3033 até o último concurso da base (calculado dinamicamente).

O resultado do concurso-alvo nunca é usado para montar os jogos daquele concurso.

> Atenção: o intervalo 3033-3794 foi observado durante o desenvolvimento de V6, V7, V7.1 e V8 (as versões
> foram criadas depois de ver resultados nesse intervalo). Por isso ele **não é mais um holdout independente
> para essas versões**; a única evidência realmente independente é a avaliação prospectiva congelada.

## Comparação
Todas as estratégias são avaliadas com exatamente 10 jogos por concurso:
- random10: baseline aleatório.
- freq8_cov2: 8 jogos por frequência + 2 complementares por cobertura.
- blend8_cov2: frequência + recência + cobertura.
- freq8_inv2: frequência + 2 complementares por inversão de frequência.
- blend8_inv2: combinação frequência/recência + inversão.

Métricas: concursos com 13+, 12+, 11+ e demais indicadores; média do melhor jogo como auxiliar.
A comparação com o acaso usa `src/compare_models.py` (teste pareado contra a hipótese nula, por portfólio).

## Critério
Uma estratégia não será considerada robusta por apresentar um pico isolado. Ela precisa mostrar comportamento
consistente fora da amostra e ser comparada ao baseline com o mesmo número de jogos.

## Como rodar os testes
`python -m pytest -q -m "not slow"`

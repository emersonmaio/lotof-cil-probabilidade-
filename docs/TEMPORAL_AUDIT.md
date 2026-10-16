# Temporal audit protocol

For every future target contest, the experiment must be run before the target result
is appended to the historical CSV.

Required order:
1. Use only contests with number lower than the target.
2. Generate the candidate portfolios.
3. Store the generated portfolio with the target contest number and generation timestamp.
4. After the official result is available, evaluate the stored portfolio.
5. Only then append the official result to the historical CSV.
6. Re-run walk-forward tests using the new contest as historical information.

A stored pre-draw record must never be regenerated after the result is known.

## Backtest atualizado em 2026-10-15

Histórico validado localmente até o concurso 3804 (3.804 linhas de resultados, 15 dezenas únicas por linha e sequência contínua). A execução do workflow `V6 and V7 probabilistic backtests` terminou com sucesso: https://github.com/emersonmaio/lotof-cil-probabilidade-/actions/runs/38798927269

### Resultado V8: interpretação cautelosa

- Período de validação usado para seleção: concursos 2275–3032.
- Holdout: concursos 3033–3804 (772 concursos).
- Cinco sementes; 300 candidatos por concurso.
- Média do melhor jogo entre 10: 10,920207 (desvio-padrão entre sementes 0,028727).
- Linha de base aleatória com 10 jogos por concurso: média 10,829015 (desvio-padrão 0,031538).
- Diferença média: +0,091192 acerto; contagens médias de 13+ foram 11,8 contra 10,8 para aleatório.
- Nenhuma ocorrência de 15 acertos no holdout; a métrica de 14+ não mostrou vantagem estável.

Essa diferença é pequena e não demonstra, sozinha, uma vantagem preditiva real. A seleção entre configurações e a busca de candidatos também podem introduzir otimismo. Não declarar o V8 vencedor com base apenas nesse teste.

## Próxima fase: avaliação prospectiva congelada

1. Antes do próximo sorteio, gerar e gravar os 10 jogos de cada método concorrente (V6, V7.1, V8 e aleatório) com número-alvo, timestamp, versão/commit, semente e parâmetros.
2. Não alterar nem regenerar os jogos após o sorteio.
3. Depois da publicação oficial, comparar os acertos por método e registrar o resultado sem excluir concursos desfavoráveis.
4. Repetir por pelo menos 30 concursos; tratar esse número como acompanhamento inicial, não como prova estatística definitiva.
5. Manter uma linha de base aleatória reproduzível e avaliar diferença média, distribuição de acertos e incerteza; não escolher parâmetros usando os resultados prospectivos acumulados.

**Regra de integridade:** os concursos adicionados ao histórico só podem ser usados em avaliações futuras após os jogos prospectivos correspondentes terem sido congelados e pontuados.

# Lotofácil — Probabilidade / Backtest 8+2

Projeto de experimentação para avaliar, sem olhar o resultado futuro, estratégias de 10 jogos formadas por **8 jogos-base + 2 complementares**.

## Objetivo
Medir média do melhor jogo, média dos 10 jogos e frequência de 11, 12, 13, 14 e 15 acertos. Isto testa hipóteses; não implica previsão de sorteios aleatórios.

## Dados
A base de trabalho foi atualizada até o concurso **3794 (01/10/2026)**. O próximo concurso deve ser tratado como desconhecido até o resultado oficial estar disponível.

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

Validação V6: 2275–3032.
Holdout V6: 3033–3794.

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

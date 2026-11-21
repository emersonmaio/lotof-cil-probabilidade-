# Resultado do backtest

Base temporal: concursos 1-3810. Para cada alvo, somente concursos anteriores sao usados.

| split | estrategia | 15 | 14+ | 13+ | 12+ | 11+ | media | mediana | DP | minimo | maximo |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| validation | random10 | 0 | 0 | 9 | 132 | 515 | 10.849604 | 11.0 | 0.745129 | 9 | 13 |
| validation | freq8_cov2 | 0 | 1 | 13 | 132 | 526 | 10.879947 | 11.0 | 0.737316 | 9 | 14 |
| validation | blend8_cov2 | 0 | 0 | 14 | 134 | 522 | 10.873351 | 11.0 | 0.747769 | 9 | 13 |
| validation | freq8_inv2 | 0 | 0 | 10 | 119 | 490 | 10.80343 | 11.0 | 0.742341 | 9 | 13 |
| validation | blend8_inv2 | 0 | 0 | 10 | 125 | 510 | 10.836412 | 11.0 | 0.740565 | 9 | 13 |
| holdout | random10 | 0 | 0 | 17 | 153 | 530 | 10.876607 | 11.0 | 0.796969 | 9 | 13 |
| holdout | freq8_cov2 | 0 | 1 | 22 | 134 | 530 | 10.874036 | 11.0 | 0.770317 | 9 | 14 |
| holdout | blend8_cov2 | 0 | 2 | 14 | 144 | 556 | 10.910026 | 11.0 | 0.74835 | 9 | 14 |
| holdout | freq8_inv2 | 0 | 1 | 5 | 125 | 526 | 10.822622 | 11.0 | 0.737816 | 9 | 14 |
| holdout | blend8_inv2 | 0 | 2 | 18 | 127 | 537 | 10.863753 | 11.0 | 0.763531 | 9 | 14 |

O holdout final (3033-3810) e avaliacao fora da amostra.

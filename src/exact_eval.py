"""Avaliação EXATA de portfólios de jogos da Lotofácil, sem simulação.

Enumera os C(25,15) = 3.268.760 sorteios possíveis (todos equiprováveis sob H0) e calcula, para um
conjunto de jogos, a distribuição exata do "melhor jogo", P(melhor >= k) e o número esperado de
bilhetes por faixa de prêmio.

Fato central (linearidade): o número esperado de bilhetes com k acertos é a SOMA dos bilhetes, e cada
bilhete sozinho tem a mesma distribuição hipergeométrica. Logo o prêmio esperado NÃO depende de como
os jogos são escolhidos. Só muda a probabilidade de "pelo menos um bilhete bom".
"""
import numpy as np

N_NUM, K = 25, 15
_DRAWS = None


def all_draws():
    """Máscaras (uint32) de todos os sorteios possíveis; cacheado."""
    global _DRAWS
    if _DRAWS is None:
        a = np.arange(1 << N_NUM, dtype=np.uint32)
        _DRAWS = a[np.bitwise_count(a) == K]
        del a
    return _DRAWS


def hits_matrix(games, draws=None):
    """Matriz (n_jogos x n_sorteios) de acertos."""
    d = all_draws() if draws is None else draws
    g = np.asarray(games, dtype=np.uint32)[:, None]
    return np.bitwise_count(g & d[None, :]).astype(np.uint8)


def exact_stats(games, draws=None):
    h = hits_matrix(games, draws)
    best = h.max(axis=0)
    n = best.shape[0]
    pk = np.bincount(best, minlength=K + 1) / n
    out = {
        "n_draws": int(n),
        "n_games": len(games),
        "E_best": float((best.astype(np.float64)).mean()),
        "P_best": {int(k): float(pk[k]) for k in range(K + 1)},
        "P_ge": {k: float(pk[k:].sum()) for k in (11, 12, 13, 14, 15)},
        # linearidade: esperado de bilhetes por faixa (igual para qualquer portfólio de mesmo tamanho)
        "E_tickets_tier": {k: float((h >= k).sum(axis=0).mean()) for k in (11, 12, 13, 14, 15)},
        "E_tickets_exact": {k: float((h == k).sum(axis=0).mean()) for k in (11, 12, 13, 14, 15)},
    }
    return out


def mask(game):
    m = 0
    for n in game:
        m |= 1 << (n - 1)
    return m

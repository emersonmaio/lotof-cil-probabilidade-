"""Controle "só diversificação": 10 jogos sem usar nenhum dado histórico.

180 jogos uniformes e distintos; escolha gulosa de 10 que minimizam a sobreposição com os já
escolhidos (mesma penalização do V6). Serve para separar o efeito de diversificar do efeito de prever.
"""


def mask(game):
    m = 0
    for n in game:
        m |= 1 << (n - 1)
    return m


def mask_to_game(m):
    return [n for n in range(1, 26) if m >> (n - 1) & 1]


def choose(rng, candidates=180, overlap_penalty=0.55):
    """Devolve 10 máscaras de bits (um portfólio). Consome `rng` (random.Random)."""
    seen, cand = set(), []
    while len(cand) < candidates:
        g = tuple(sorted(rng.sample(range(1, 26), 15)))
        if g not in seen:
            seen.add(g)
            cand.append(mask(g))
    chosen = []
    for _ in range(10):
        best, bu = None, -1e99
        for m in cand:
            if m in chosen:
                continue
            u = -overlap_penalty * sum((m & x).bit_count() for x in chosen)
            if u > bu:
                bu, best = u, m
        chosen.append(best)
    return chosen

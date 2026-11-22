"""Estrutura de 10 jogos otimizada para cobertura (ver optimize_portfolio.py).
E[melhor jogo] exato = 10,9798 (aleatório 10,84; diversificado 10,93). NÃO usa histórico e NÃO muda o
prêmio esperado (linearidade). Em cada concurso os rótulos 1..25 são permutados aleatoriamente."""
import random

from optimize_portfolio import relabel

STRUCTURE = [2880755, 8339265, 30644854, 5041079, 28386287, 33330319, 32205212, 9862461, 24561400, 26074954]


def choose(rng: random.Random):
    return relabel(STRUCTURE, rng)

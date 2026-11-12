"""Incerteza e testes que respeitam a dependência entre anúncios.

O mesmo criativo aparece em vários anúncios, e os anúncios sobem em lotes. Tratar cada anúncio
como uma observação independente estreita os intervalos e infla a significância. Aqui a unidade
sorteada (no bootstrap) ou embaralhada (na permutação) é o bloco: o grupo de criativo ou o lote.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse


def codigos(blocos: pd.Series | np.ndarray) -> tuple[np.ndarray, int]:
    """Número inteiro de 0 a B−1 para cada bloco."""
    numeros, valores = pd.factorize(np.asarray(blocos))
    return numeros, len(valores)


def somas_por_bloco(valores: np.ndarray, blocos: np.ndarray, n_blocos: int) -> np.ndarray:
    return np.bincount(blocos, weights=np.asarray(valores, dtype=float), minlength=n_blocos)


def pesos_de_bootstrap(gerador: np.random.Generator, n_blocos: int, repeticoes: int) -> np.ndarray:
    """Quantas vezes cada bloco é sorteado em cada reamostragem (sorteio com reposição de n blocos)."""
    sorteados = gerador.integers(0, n_blocos, size=(repeticoes, n_blocos))
    sorteados += np.arange(repeticoes)[:, None] * n_blocos  # desloca cada linha para contar tudo de uma vez
    return np.bincount(sorteados.ravel(), minlength=repeticoes * n_blocos).reshape(repeticoes, n_blocos).astype(float)


def contagens_reamostradas(
    idades: np.ndarray, blocos: np.ndarray, idade_maxima: int, repeticoes: int = 2000, semente: int = 42
) -> np.ndarray:
    """Contagens por idade (1..idade_maxima) de cada reamostragem, sorteando blocos inteiros.

    Sortear um bloco traz todos os anúncios dele, com as idades que têm. Com um bloco por anúncio,
    vira o bootstrap comum (o que trata os anúncios como independentes). Devolve uma matriz
    reamostragem × idade.
    """
    idades = np.asarray(idades, dtype=int)
    numeros, n_blocos = codigos(blocos)
    pesos = pesos_de_bootstrap(np.random.default_rng(semente), n_blocos, repeticoes)
    # Matriz esparsa bloco × idade (quantos anúncios do bloco têm cada idade); o produto com os
    # pesos dá as contagens de cada reamostragem sem montar a matriz cheia.
    bloco_por_idade = sparse.csr_matrix((np.ones(len(idades)), (numeros, idades - 1)), shape=(n_blocos, idade_maxima))
    return np.asarray((bloco_por_idade.T @ pesos.T).T)


def intervalo(valores: np.ndarray, nivel: float = 0.95) -> tuple[float, float]:
    """Intervalo percentil dos valores de uma estatística nas reamostragens."""
    valores = np.asarray(valores, dtype=float)
    valores = valores[np.isfinite(valores)]
    cauda = (1 - nivel) / 2
    return float(np.quantile(valores, cauda)), float(np.quantile(valores, 1 - cauda))


def diferenca_de_medias(y: np.ndarray, x: np.ndarray) -> float:
    """Média de y entre quem tem o atributo (x = 1) menos a média entre quem não tem."""
    x = np.asarray(x, dtype=bool)
    return float(np.mean(y[x]) - np.mean(y[~x]))


def intervalo_da_diferenca(
    y: np.ndarray, x: np.ndarray, blocos: np.ndarray, n_blocos: int, repeticoes: int = 2000, semente: int = 42
) -> tuple[float, float]:
    """Intervalo de 95% da diferença de médias, reamostrando blocos inteiros."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    com, sem = somas_por_bloco(x, blocos, n_blocos), somas_por_bloco(1 - x, blocos, n_blocos)
    soma_com, soma_sem = somas_por_bloco(x * y, blocos, n_blocos), somas_por_bloco((1 - x) * y, blocos, n_blocos)
    pesos = pesos_de_bootstrap(np.random.default_rng(semente), n_blocos, repeticoes)
    with np.errstate(divide="ignore", invalid="ignore"):
        valores = (pesos @ soma_com) / (pesos @ com) - (pesos @ soma_sem) / (pesos @ sem)
    valores = valores[np.isfinite(valores)]
    return float(np.quantile(valores, 0.025)), float(np.quantile(valores, 0.975))


def p_por_permutacao_de_blocos(
    y: np.ndarray, x: np.ndarray, blocos: np.ndarray, n_blocos: int, repeticoes: int = 5000, semente: int = 42
) -> float:
    """p-valor bicaudal da diferença de médias, embaralhando a idade entre blocos.

    Cada bloco fica com a sua composição (quantos anúncios com e sem o atributo) e recebe a idade
    média de outro bloco, sorteado. Se a idade não tem relação com o atributo, a diferença observada
    deve parecer uma dessas diferenças embaralhadas. Com um bloco por anúncio é a permutação comum.
    Quando a idade varia dentro do bloco, o bloco entra com a sua idade média.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    com, sem = somas_por_bloco(x, blocos, n_blocos), somas_por_bloco(1 - x, blocos, n_blocos)
    idade_do_bloco = somas_por_bloco(y, blocos, n_blocos) / (com + sem)

    def estatistica(idades: np.ndarray) -> np.ndarray:
        return idades @ com / com.sum() - idades @ sem / sem.sum()

    observada = abs(float(estatistica(idade_do_bloco)))
    gerador = np.random.default_rng(semente)
    extremos = 0
    for inicio in range(0, repeticoes, 500):  # em pedaços, para não ocupar memória
        linhas = min(500, repeticoes - inicio)
        embaralhadas = gerador.permuted(np.tile(idade_do_bloco, (linhas, 1)), axis=1)
        extremos += int((np.abs(estatistica(embaralhadas)) >= observada - 1e-12).sum())
    return (extremos + 1) / (repeticoes + 1)


def benjamini_hochberg(p_valores: pd.Series) -> pd.Series:
    """p-valores ajustados para a taxa de falsas descobertas (Benjamini-Hochberg)."""
    ordenados = p_valores.sort_values()
    m = len(ordenados)
    ajustados = (ordenados * m / np.arange(1, m + 1))[::-1].cummin()[::-1].clip(upper=1.0)
    return ajustados.reindex(p_valores.index)


def curva_de_lorenz(quantidades: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fração acumulada das unidades (da menor para a maior) e fração acumulada do total."""
    ordenadas = np.sort(np.asarray(quantidades, dtype=float))
    x = np.arange(len(ordenadas) + 1) / len(ordenadas)
    y = np.concatenate([[0.0], np.cumsum(ordenadas) / ordenadas.sum()])
    return x, y


def gini(quantidades: np.ndarray) -> float:
    """Índice de Gini: 0 = todos iguais; perto de 1 = quase tudo em poucas unidades."""
    x, y = curva_de_lorenz(quantidades)
    return float(1 - 2 * np.trapezoid(y, x))


def indice_de_dispersao(contagens: np.ndarray, esperadas: np.ndarray) -> float:
    """Qui-quadrado de Pearson dividido pelos graus de liberdade.

    Perto de 1 quando as contagens variam como um Poisson em torno do esperado; muito acima de 1
    quando chegam em lotes.
    """
    contagens = np.asarray(contagens, dtype=float)
    esperadas = np.asarray(esperadas, dtype=float)
    usar = esperadas > 0
    return float(((contagens[usar] - esperadas[usar]) ** 2 / esperadas[usar]).sum() / (usar.sum() - 1))

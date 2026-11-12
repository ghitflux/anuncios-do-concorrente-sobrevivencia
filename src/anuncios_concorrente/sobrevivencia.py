"""Da foto dos anúncios vivos para a curva de sobrevivência: o núcleo do método.

A biblioteca de anúncios mostra quem está no ar hoje. "Dias no ar" é a idade do anúncio, não a
duração total dele. Tudo aqui trabalha em dias inteiros:

- idade `a` = 1 para quem foi lançado no dia da foto, 2 para a véspera, e assim por diante;
- duração `D` = número de dias em que o anúncio fica no ar (pelo menos 1);
- sobrevivência `S(a)` = P(D ≥ a), a fração dos anúncios que chega ao a-ésimo dia. S(1) = 1.

Um anúncio lançado há `a − 1` dias aparece na foto se D ≥ a. Se o anunciante lança `w(a)` anúncios
por dia (em termos relativos) há `a − 1` dias, o número esperado de anúncios com idade `a` na foto é

    n(a) = taxa · w(a) · S(a).

Com ritmo constante (w = 1), a distribuição das idades é proporcional a S: p(a) = S(a) / E[D].
Daí saem a duração média, E[D] = 1 / p(1), e a curva, S(a) = p(a) / p(1). Como S não pode crescer,
a estimativa de p é a melhor sequência não crescente (estimador de Grenander, na versão discreta),
calculada por regressão isotônica.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Regressão isotônica decrescente
# ---------------------------------------------------------------------------


def regressao_antitonica(valores: np.ndarray, pesos: np.ndarray | None = None) -> np.ndarray:
    """Melhor sequência não crescente, por mínimos quadrados ponderados (algoritmo PAVA).

    Percorre os valores da esquerda para a direita. Sempre que um bloco tem média maior que a do
    bloco anterior (o que violaria "não crescente"), os dois são fundidos na média ponderada.
    """
    valores = np.asarray(valores, dtype=float)
    pesos = np.ones_like(valores) if pesos is None else np.asarray(pesos, dtype=float)
    somas: list[float] = []  # soma de peso × valor de cada bloco
    massas: list[float] = []  # soma dos pesos de cada bloco
    tamanhos: list[int] = []
    for valor, peso in zip(valores, pesos):
        somas.append(valor * peso)
        massas.append(peso)
        tamanhos.append(1)
        while len(somas) > 1 and somas[-1] / massas[-1] > somas[-2] / massas[-2]:
            soma, massa, tamanho = somas.pop(), massas.pop(), tamanhos.pop()
            somas[-1] += soma
            massas[-1] += massa
            tamanhos[-1] += tamanho
    return np.repeat([s / m for s, m in zip(somas, massas)], tamanhos)


def antitonica_em_lote(contagens: np.ndarray, exposicao: np.ndarray | None = None, pedaco: int = 250) -> np.ndarray:
    """A mesma regressão para muitas linhas de uma vez (uma por reamostragem), pela fórmula min-max.

    Para taxas não crescentes: ajuste(i) = min sobre s ≤ i do max sobre t ≥ i da média do trecho s..t,
    onde a média do trecho é (soma das contagens) / (soma da exposição). Dá o mesmo resultado que o
    PAVA aplicado a contagens/exposição com pesos = exposição (conferido nos testes).
    """
    contagens = np.atleast_2d(np.asarray(contagens, dtype=float))
    n_linhas, k = contagens.shape
    exposicao = np.ones(k) if exposicao is None else np.asarray(exposicao, dtype=float)
    acumulada_w = np.concatenate([[0.0], np.cumsum(exposicao)])
    massa = acumulada_w[None, 1:] - acumulada_w[:-1, None]  # massa[s, t] = exposição de s..t
    valido = np.triu(np.ones((k, k), dtype=bool))
    massa = np.where(valido, massa, 1.0)
    saida = np.empty_like(contagens)
    for inicio in range(0, n_linhas, pedaco):
        bloco = contagens[inicio : inicio + pedaco]
        acumulada = np.concatenate([np.zeros((len(bloco), 1)), np.cumsum(bloco, axis=1)], axis=1)
        media = (acumulada[:, None, 1:] - acumulada[:, :-1, None]) / massa[None]  # [linha, s, t]
        media = np.where(valido[None], media, -np.inf)
        maior_adiante = np.flip(np.maximum.accumulate(np.flip(media, axis=2), axis=2), axis=2)  # max em t ≥ i
        maior_adiante = np.where(valido[None], maior_adiante, np.inf)
        saida[inicio : inicio + pedaco] = np.minimum.accumulate(maior_adiante, axis=1)[:, np.arange(k), np.arange(k)]
    return saida


# ---------------------------------------------------------------------------
# Estimadores a partir da foto
# ---------------------------------------------------------------------------


def contagem_por_idade(idades: np.ndarray, idade_maxima: int | None = None) -> np.ndarray:
    """Quantos anúncios da foto têm cada idade, de 1 até a idade máxima."""
    idades = np.asarray(idades, dtype=int)
    idade_maxima = int(idades.max()) if idade_maxima is None else idade_maxima
    return np.bincount(idades, minlength=idade_maxima + 1)[1 : idade_maxima + 1].astype(float)


def exposicao_do_ritmo(idade_maxima: int, razao: float = 1.0) -> np.ndarray:
    """Ritmo relativo de lançamento por idade, w(a), com w(1) = 1.

    `razao` = (lançamentos por dia hoje) / (lançamentos por dia no começo da janela). Com 1, o ritmo
    é constante; com 2, o anunciante dobrou o ritmo ao longo da janela (crescimento exponencial).
    """
    if idade_maxima == 1:
        return np.ones(1)
    return razao ** (-np.arange(idade_maxima) / (idade_maxima - 1))


@dataclass
class Estimativa:
    """O que a foto diz sobre a sobrevivência, sob uma hipótese de ritmo de lançamento."""

    sobrevivencia: np.ndarray  # S(a), a = 1..K
    duracao_media: float  # E[D] limitada à janela observada
    lancados_por_dia: float  # ritmo de lançamento hoje
    lancados_na_janela: float  # total lançado nos K dias, vivos ou não
    vivos: float  # o que a foto mostra


def estimar_pela_foto(contagens: np.ndarray, exposicao: np.ndarray | None = None) -> Estimativa:
    """Curva de sobrevivência e duração média a partir das contagens por idade.

    A taxa por idade, n(a)/w(a), é ajustada como sequência não crescente com pesos w(a): é a máxima
    verossimilhança de contagens de Poisson com média taxa·w(a)·S(a) e S não crescente.
    A duração média é a soma de S(a) na janela observada; com ritmo constante, isso é 1/p(1).
    """
    contagens = np.asarray(contagens, dtype=float)
    exposicao = np.ones_like(contagens) if exposicao is None else np.asarray(exposicao, dtype=float)
    taxa = regressao_antitonica(contagens / exposicao, exposicao)
    if taxa[0] <= 0:
        raise ValueError("foto vazia: não há anúncio para estimar")
    sobrevivencia = taxa / taxa[0]
    return Estimativa(
        sobrevivencia=sobrevivencia,
        duracao_media=float(sobrevivencia.sum()),
        lancados_por_dia=float(taxa[0]),
        lancados_na_janela=float(taxa[0] * exposicao.sum()),
        vivos=float(contagens.sum()),
    )


def duracao_media_em_lote(contagens: np.ndarray) -> np.ndarray:
    """Duração média corrigida, com ritmo constante, para muitas reamostragens de uma vez.

    Com ritmo constante, p(1) ajustado é a maior média corrida das contagens (a inclinação do menor
    majorante côncavo na origem), e a duração média é N / essa média.
    """
    contagens = np.atleast_2d(np.asarray(contagens, dtype=float))
    medias_corridas = np.cumsum(contagens, axis=1) / np.arange(1, contagens.shape[1] + 1)
    return contagens.sum(axis=1) / medias_corridas.max(axis=1)


def media_ingenua_em_lote(contagens: np.ndarray) -> np.ndarray:
    """Média de "dias no ar" (a leitura ingênua), para muitas reamostragens de uma vez."""
    contagens = np.atleast_2d(np.asarray(contagens, dtype=float))
    idades = np.arange(1, contagens.shape[1] + 1)
    return contagens @ idades / contagens.sum(axis=1)


def sobrevivencia_ingenua(contagens: np.ndarray) -> np.ndarray:
    """A leitura ingênua como curva: fração dos anúncios da foto com idade ≥ a."""
    contagens = np.asarray(contagens, dtype=float)
    return np.cumsum(contagens[::-1])[::-1] / contagens.sum()


# ---------------------------------------------------------------------------
# O que a teoria diz que a foto mostra
# ---------------------------------------------------------------------------


def idade_media_esperada(pmf_duracao: np.ndarray) -> float:
    """Média de "dias no ar" que a foto mostra, com ritmo constante: E[D(D+1)] / (2·E[D])."""
    d = np.arange(1, len(pmf_duracao) + 1)
    return float((pmf_duracao * d * (d + 1)).sum() / (2 * (pmf_duracao * d).sum()))


def duracao_media_dos_fotografados(pmf_duracao: np.ndarray) -> float:
    """Duração total média dos anúncios que aparecem na foto: E[D²] / E[D] (viés pelo comprimento)."""
    d = np.arange(1, len(pmf_duracao) + 1)
    return float((pmf_duracao * d * d).sum() / (pmf_duracao * d).sum())


# ---------------------------------------------------------------------------
# Simulação de resposta conhecida
# ---------------------------------------------------------------------------


@dataclass
class Duracao:
    """Uma distribuição de duração de anúncios, com sorteio e a função de massa (para a teoria)."""

    nome: str
    sortear: Callable[[np.random.Generator, int], np.ndarray]
    pmf: np.ndarray

    @property
    def media(self) -> float:
        return float((self.pmf * np.arange(1, len(self.pmf) + 1)).sum())


def _pmf_geometrica(media: float, teto: int) -> np.ndarray:
    p = 1.0 / media
    pmf = p * (1 - p) ** np.arange(teto)
    return pmf / pmf.sum()


def duracao_fixa(dias: int, teto: int = 2000) -> Duracao:
    pmf = np.zeros(teto)
    pmf[dias - 1] = 1.0
    return Duracao(f"Todo anúncio dura {dias} dias", lambda g, n: np.full(n, dias), pmf)


def duracao_geometrica(media: float, teto: int = 2000) -> Duracao:
    return Duracao(
        "Risco constante de sair do ar", lambda g, n: g.geometric(1.0 / media, size=n), _pmf_geometrica(media, teto)
    )


def duracao_mistura(media_curta: float, media_longa: float, fracao_longa: float, teto: int = 2000) -> Duracao:
    def sortear(g: np.random.Generator, n: int) -> np.ndarray:
        longa = g.random(n) < fracao_longa
        return np.where(longa, g.geometric(1.0 / media_longa, size=n), g.geometric(1.0 / media_curta, size=n))

    pmf = (1 - fracao_longa) * _pmf_geometrica(media_curta, teto) + fracao_longa * _pmf_geometrica(media_longa, teto)
    return Duracao("Muitos testes curtos, poucos anúncios longos", sortear, pmf)


def ritmo_constante(horizonte: int, por_dia: float) -> Callable[[np.random.Generator], np.ndarray]:
    return lambda g: np.full(horizonte, por_dia)


def ritmo_crescente(horizonte: int, por_dia_hoje: float, dias_para_dobrar: float) -> Callable[[np.random.Generator], np.ndarray]:
    """O anunciante dobra o ritmo de lançamento a cada `dias_para_dobrar` dias."""
    atras = np.arange(horizonte)[::-1]  # dias antes da foto
    return lambda g: por_dia_hoje * 2.0 ** (-atras / dias_para_dobrar)


def ritmo_em_lotes(horizonte: int, por_dia: float, intervalo_medio: float, dispersao: float = 1.0) -> Callable[[np.random.Generator], np.ndarray]:
    """Lançamentos em lotes: só há lançamento em 1 a cada `intervalo_medio` dias, com tamanho irregular."""

    def sortear(g: np.random.Generator) -> np.ndarray:
        dia_de_lote = g.random(horizonte) < 1.0 / intervalo_medio
        tamanho = g.lognormal(-dispersao**2 / 2, dispersao, size=horizonte)  # média 1
        return np.where(dia_de_lote, por_dia * intervalo_medio * tamanho, 0.0)

    return sortear


def ritmo_de_conta_nova(horizonte: int, por_dia: float, dias_de_conta: int) -> Callable[[np.random.Generator], np.ndarray]:
    """A conta só começou a anunciar há `dias_de_conta` dias."""
    ritmo = np.zeros(horizonte)
    ritmo[-dias_de_conta:] = por_dia
    return lambda g: ritmo


def simular_foto(
    gerador: np.random.Generator,
    duracao: Duracao,
    ritmo: Callable[[np.random.Generator], np.ndarray],
    anuncios_por_criativo: float = 1.0,
    dependencia: float = 0.0,
) -> dict[str, np.ndarray]:
    """Lança anúncios ao longo do tempo e tira uma foto no último dia.

    Cada criativo vira 1 ou mais anúncios lançados no mesmo dia (1 + Poisson). Com probabilidade
    `dependencia`, os anúncios de um criativo saem do ar juntos (mesma duração); senão, cada um tem
    a sua. Devolve, só para os anúncios vivos na foto: idade, duração total (que na vida real não
    se vê) e o criativo de cada um.
    """
    criativos_por_dia = gerador.poisson(ritmo(gerador) / anuncios_por_criativo)
    horizonte = len(criativos_por_dia)
    idade_do_criativo = np.repeat(horizonte - np.arange(horizonte), criativos_por_dia)  # 1 = lançado hoje
    n_criativos = len(idade_do_criativo)
    tamanho = 1 + gerador.poisson(anuncios_por_criativo - 1.0, size=n_criativos)
    criativo = np.repeat(np.arange(n_criativos), tamanho)
    idade = idade_do_criativo[criativo]
    propria = duracao.sortear(gerador, len(criativo))
    comum = duracao.sortear(gerador, n_criativos)[criativo]
    juntos = (gerador.random(n_criativos) < dependencia)[criativo]
    total = np.where(juntos, comum, propria)
    vivo = total >= idade
    return {"idade": idade[vivo], "duracao": total[vivo], "criativo": criativo[vivo], "lancados": np.array(len(criativo))}

import numpy as np
import pandas as pd
import pytest

from anuncios_concorrente import estatistica as est
from anuncios_concorrente import sobrevivencia as sob


def _copias(n_grupos: int = 60, copias: int = 10, efeito: float = 0.0, semente: int = 0):
    """Cada grupo tem uma idade e um atributo; cada um aparece `copias` vezes (anúncios do mesmo criativo)."""
    gerador = np.random.default_rng(semente)
    atributo = gerador.random(n_grupos) < 0.5
    idade = gerador.normal(30, 10, n_grupos) + efeito * atributo
    grupo = np.repeat(np.arange(n_grupos), copias)
    return idade[grupo], atributo[grupo], grupo, n_grupos


def test_contagens_reamostradas_mantem_o_bloco_inteiro_e_o_total_esperado():
    idades = np.array([1, 1, 1, 2, 2, 3, 3, 3, 3])
    blocos = np.array([0, 0, 0, 1, 1, 2, 2, 2, 2])
    contagens = est.contagens_reamostradas(idades, blocos, 3, repeticoes=500, semente=1)
    assert contagens.shape == (500, 3)
    assert (contagens[:, 0] % 3 == 0).all() and (contagens[:, 1] % 2 == 0).all() and (contagens[:, 2] % 4 == 0).all()
    assert (contagens[:, 0] / 3 + contagens[:, 1] / 2 + contagens[:, 2] / 4 == 3).all()  # sempre 3 blocos sorteados
    assert contagens.mean(axis=0) == pytest.approx([3, 2, 4], rel=0.1)


def test_bootstrap_por_bloco_e_mais_largo_que_o_por_anuncio_quando_ha_copias():
    idade, _, grupo, _ = _copias()
    idades = np.clip(np.round(idade), 1, 80).astype(int)
    por_anuncio = est.intervalo(sob.media_ingenua_em_lote(est.contagens_reamostradas(idades, np.arange(len(idades)), 80, 1000, 2)))
    por_grupo = est.intervalo(sob.media_ingenua_em_lote(est.contagens_reamostradas(idades, grupo, 80, 1000, 2)))
    assert por_grupo[0] < idades.mean() < por_grupo[1]
    razao = (por_grupo[1] - por_grupo[0]) / (por_anuncio[1] - por_anuncio[0])
    assert razao == pytest.approx(np.sqrt(10), rel=0.2)  # 10 cópias por grupo: intervalo raiz de 10 vezes mais largo


def test_permutacao_por_bloco_nao_se_engana_com_copias():
    idade, atributo, grupo, n_grupos = _copias(efeito=4.0, semente=3)
    anuncio = np.arange(len(idade))
    p_por_anuncio = est.p_por_permutacao_de_blocos(idade, atributo, anuncio, len(anuncio), repeticoes=1000)
    p_por_grupo = est.p_por_permutacao_de_blocos(idade, atributo, grupo, n_grupos, repeticoes=1000)
    assert p_por_anuncio < 0.01  # 600 "observações" tornam qualquer diferença significativa
    assert p_por_grupo > 0.05  # são só 60 grupos, e a diferença cabe no acaso


def test_permutacao_por_bloco_encontra_efeito_grande():
    idade, atributo, grupo, n_grupos = _copias(efeito=25.0, semente=4)
    assert est.p_por_permutacao_de_blocos(idade, atributo, grupo, n_grupos, repeticoes=1000) < 0.01


def test_permutacao_sem_relacao_da_p_uniforme_e_nao_pequeno_demais():
    pequenos = 0
    for semente in range(40):
        idade, atributo, grupo, n_grupos = _copias(n_grupos=40, copias=5, semente=100 + semente)
        pequenos += est.p_por_permutacao_de_blocos(idade, atributo, grupo, n_grupos, repeticoes=300, semente=semente) < 0.05
    assert pequenos <= 6  # esperado: 2 em 40


def test_diferenca_de_medias_e_intervalo():
    idade, atributo, grupo, n_grupos = _copias(efeito=25.0, semente=5)
    diferenca = est.diferenca_de_medias(idade, atributo)
    inferior, superior = est.intervalo_da_diferenca(idade, atributo, grupo, n_grupos, repeticoes=1000)
    assert inferior < diferenca < superior
    assert inferior > 10  # efeito de 25 dias fica longe do zero


def test_benjamini_hochberg_exemplo_conhecido():
    p = pd.Series([0.01, 0.04, 0.03, 0.20], index=list("abcd"))
    ajustado = est.benjamini_hochberg(p)
    assert ajustado["a"] == pytest.approx(0.04)
    assert ajustado["b"] == pytest.approx(0.0533, abs=1e-3)
    assert ajustado["c"] == pytest.approx(0.0533, abs=1e-3)
    assert ajustado["d"] == pytest.approx(0.20)
    assert (ajustado >= p).all()


def test_gini_e_lorenz_casos_conhecidos():
    assert est.gini([5, 5, 5, 5]) == pytest.approx(0.0)
    assert est.gini([0, 0, 0, 10]) == pytest.approx(0.75)  # (n − 1) / n
    x, y = est.curva_de_lorenz([1, 3])
    assert x.tolist() == [0, 0.5, 1] and y.tolist() == [0, 0.25, 1]


def test_indice_de_dispersao_separa_poisson_de_lotes():
    gerador = np.random.default_rng(6)
    esperadas = np.full(200, 20.0)
    assert est.indice_de_dispersao(gerador.poisson(20, 200), esperadas) == pytest.approx(1.0, abs=0.3)
    em_lotes = np.where(np.arange(200) % 5 == 0, 100, 0)  # tudo num dia a cada cinco
    assert est.indice_de_dispersao(em_lotes, esperadas) > 20

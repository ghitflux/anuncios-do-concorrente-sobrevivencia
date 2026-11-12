import numpy as np
import pytest
from sklearn.isotonic import IsotonicRegression

from anuncios_concorrente import sobrevivencia as sob


def test_regressao_antitonica_casos_conhecidos():
    assert sob.regressao_antitonica([3, 1, 2]) == pytest.approx([3, 1.5, 1.5])
    assert sob.regressao_antitonica([1, 2, 3]) == pytest.approx([2, 2, 2])
    assert sob.regressao_antitonica([5, 4, 4, 1]) == pytest.approx([5, 4, 4, 1])  # já não crescente: fica igual
    assert sob.regressao_antitonica([1, 3], pesos=[3, 1]) == pytest.approx([1.5, 1.5])  # média ponderada


def test_regressao_antitonica_bate_com_o_scikit_learn_e_preserva_o_total():
    gerador = np.random.default_rng(0)
    for _ in range(20):
        valores = gerador.poisson(10, size=40).astype(float)
        pesos = gerador.uniform(0.5, 2.0, size=40)
        nossa = sob.regressao_antitonica(valores, pesos)
        referencia = IsotonicRegression(increasing=False).fit_transform(np.arange(40), valores, sample_weight=pesos)
        assert nossa == pytest.approx(referencia)
        assert (np.diff(nossa) <= 1e-12).all()
        assert (nossa * pesos).sum() == pytest.approx((valores * pesos).sum())


def test_formula_em_lote_da_o_mesmo_que_o_pava():
    gerador = np.random.default_rng(1)
    contagens = gerador.poisson(8, size=(30, 25)).astype(float)
    exposicao = sob.exposicao_do_ritmo(25, 3.0)
    em_lote = sob.antitonica_em_lote(contagens, exposicao, pedaco=7)
    for linha, esperado in zip(contagens, em_lote):
        assert sob.regressao_antitonica(linha / exposicao, exposicao) == pytest.approx(esperado)
    sem_exposicao = sob.antitonica_em_lote(contagens)
    assert sob.regressao_antitonica(contagens[0]) == pytest.approx(sem_exposicao[0])


def test_estimador_recupera_a_curva_quando_a_foto_e_exata():
    idades = np.arange(1, 61)
    sobrevivencia = 0.9 ** (idades - 1)  # S(1) = 1
    estimativa = sob.estimar_pela_foto(1000 * sobrevivencia)
    assert estimativa.sobrevivencia == pytest.approx(sobrevivencia)
    assert estimativa.duracao_media == pytest.approx(sobrevivencia.sum())
    assert estimativa.lancados_por_dia == pytest.approx(1000)
    assert estimativa.lancados_na_janela == pytest.approx(60_000)


def test_duracao_media_com_ritmo_constante_e_um_sobre_p1():
    gerador = np.random.default_rng(2)
    contagens = gerador.poisson(20 * 0.95 ** np.arange(50)).astype(float)
    p1 = sob.regressao_antitonica(contagens / contagens.sum())[0]
    assert sob.estimar_pela_foto(contagens).duracao_media == pytest.approx(1 / p1)
    assert sob.duracao_media_em_lote(contagens)[0] == pytest.approx(1 / p1)


def test_ritmo_crescente_ignorado_subestima_a_duracao_e_informado_corrige():
    idades = np.arange(1, 61)
    sobrevivencia = 0.95 ** (idades - 1)
    ritmo = sob.exposicao_do_ritmo(60, razao=4.0)  # hoje se lança 4 vezes mais que no começo da janela
    foto = 500 * ritmo * sobrevivencia
    assert sob.estimar_pela_foto(foto, ritmo).sobrevivencia == pytest.approx(sobrevivencia)
    assert sob.estimar_pela_foto(foto).duracao_media < 0.8 * sobrevivencia.sum()  # parece que os anúncios duram menos


def test_exposicao_do_ritmo():
    assert sob.exposicao_do_ritmo(10, 1.0) == pytest.approx(np.ones(10))
    cresceu = sob.exposicao_do_ritmo(10, 2.0)
    assert cresceu[0] == pytest.approx(1.0) and cresceu[-1] == pytest.approx(0.5)


def test_o_que_a_teoria_diz_que_a_foto_mostra():
    fixa = sob.duracao_fixa(20)
    assert sob.idade_media_esperada(fixa.pmf) == pytest.approx(10.5)  # metade da duração
    assert sob.duracao_media_dos_fotografados(fixa.pmf) == pytest.approx(20)
    geometrica = sob.duracao_geometrica(20)
    assert geometrica.media == pytest.approx(20, abs=1e-6)
    assert sob.idade_media_esperada(geometrica.pmf) == pytest.approx(20, abs=1e-6)  # sem memória: idade = duração
    assert sob.duracao_media_dos_fotografados(geometrica.pmf) == pytest.approx(39, abs=1e-6)  # 2·média − 1
    mistura = sob.duracao_mistura(5, 80, 0.2)
    assert mistura.media == pytest.approx(20, abs=1e-6)
    assert sob.idade_media_esperada(mistura.pmf) > 3 * mistura.media  # cauda longa: a foto exagera


@pytest.mark.parametrize("duracao", [sob.duracao_fixa(20), sob.duracao_geometrica(20), sob.duracao_mistura(5, 80, 0.2)])
def test_simulacao_com_ritmo_constante_confirma_a_teoria_e_a_correcao(duracao):
    gerador = np.random.default_rng(3)
    foto = sob.simular_foto(gerador, duracao, sob.ritmo_constante(800, 400))  # foto grande: pouco ruído
    assert (foto["duracao"] >= foto["idade"]).all()  # só aparece quem ainda está no ar
    assert foto["idade"].mean() == pytest.approx(sob.idade_media_esperada(duracao.pmf), rel=0.06)
    assert foto["duracao"].mean() == pytest.approx(sob.duracao_media_dos_fotografados(duracao.pmf), rel=0.06)
    corrigida = sob.estimar_pela_foto(sob.contagem_por_idade(foto["idade"])).duracao_media
    assert corrigida == pytest.approx(duracao.media, rel=0.12)


def test_simulacao_com_ritmo_crescente_puxa_a_correcao_para_baixo():
    gerador = np.random.default_rng(4)
    duracao = sob.duracao_geometrica(20)
    foto = sob.simular_foto(gerador, duracao, sob.ritmo_crescente(800, 400, dias_para_dobrar=30))
    corrigida = sob.estimar_pela_foto(sob.contagem_por_idade(foto["idade"])).duracao_media
    assert corrigida < 0.8 * duracao.media


def test_criativos_que_saem_juntos_compartilham_a_duracao():
    gerador = np.random.default_rng(5)
    foto = sob.simular_foto(gerador, sob.duracao_geometrica(20), sob.ritmo_constante(400, 60), anuncios_por_criativo=3.0, dependencia=1.0)
    _, primeiro, contagem = np.unique(foto["criativo"], return_index=True, return_counts=True)
    assert contagem.max() > 1
    assert (foto["duracao"] == np.repeat(foto["duracao"][primeiro], contagem)).all()


def test_leitura_ingenua_como_curva_e_contagem_por_idade():
    contagens = sob.contagem_por_idade(np.array([1, 1, 2, 5]), 5)
    assert contagens.tolist() == [2, 1, 0, 0, 1]
    assert sob.sobrevivencia_ingenua(contagens) == pytest.approx([1, 0.5, 0.25, 0.25, 0.25])
    assert sob.media_ingenua_em_lote(contagens)[0] == pytest.approx(9 / 4)


def test_foto_vazia_e_recusada():
    with pytest.raises(ValueError):
        sob.estimar_pela_foto(np.zeros(5))

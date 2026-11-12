"""Contrato do extrato publicado: o que ele tem de ter e o que não pode ter."""

import re
from pathlib import Path

import pandas as pd
import pytest

from anuncios_concorrente import analise, dados
from anuncios_concorrente.texto import CATEGORIAS

DATA = Path(__file__).resolve().parents[1] / "data"

COLUNAS = [
    "anuncio", "pais", "pagina", "inicio", "dias_no_ar", "dias_desde_ultimo_registro", "formato",
    "n_plataformas", "variacoes", "tem_video", "duracao_video_s", "grupo_criativo", "tipo_criativo", "cena",
    "texto_id", "idioma", "comprimento_texto", "n_emojis", "tem_preco", "tem_prova_social", "tem_urgencia",
    "tem_ocasiao", "cita_natal", "tem_pergunta", "tem_previa_gratis", "descricao_tem_prova_social",
    "categoria_gancho",
]


@pytest.fixture(scope="module")
def anuncios() -> pd.DataFrame:
    return dados.carregar_anuncios(DATA)


def test_data_tem_so_os_dois_arquivos_do_extrato():
    assert sorted(p.name for p in DATA.iterdir()) == ["anuncios.csv", "coleta.json"]


def test_colunas_do_extrato_sao_exatamente_as_documentadas(anuncios):
    assert list(anuncios.columns) == COLUNAS


def test_extrato_bate_com_os_metadados_da_coleta(anuncios):
    coleta = dados.carregar_coleta(DATA)
    assert len(anuncios) == coleta["anuncios"]
    for pais, resumo in coleta["paises"].items():
        assert (anuncios["pais"] == pais).sum() == resumo["anuncios"]
    assert anuncios["grupo_criativo"].nunique() == coleta["grupos_de_criativo"]


def test_dias_no_ar_e_a_idade_na_data_da_coleta(anuncios):
    coleta = pd.Timestamp(dados.carregar_coleta(DATA)["data_da_coleta"])
    assert ((coleta - anuncios["inicio"]).dt.days + 1 == anuncios["dias_no_ar"]).all()
    assert (anuncios["dias_no_ar"] >= 1).all()


def test_identificadores_sao_rotulos_embaralhados(anuncios):
    assert anuncios["anuncio"].is_unique
    assert anuncios["anuncio"].str.fullmatch(r"a\d{4}").all()
    assert anuncios["grupo_criativo"].str.fullmatch(r"g\d{4}").all()
    assert anuncios["texto_id"].str.fullmatch(r"t\d{2}").all()
    assert anuncios["pagina"].str.fullmatch(r"[A-Z]{2}-\d").all()


def test_nada_de_link_dominio_id_original_ou_texto_no_extrato():
    for arquivo in ["anuncios.csv", "coleta.json"]:
        conteudo = (DATA / arquivo).read_text(encoding="utf-8").lower()
        assert not re.search(r"https?://|www\.|\.com\b|\.br\b|\.mp4|facebook|utm[_]", conteudo), arquivo
        assert not re.search(r"\d{12,}", conteudo), arquivo  # ids da biblioteca têm 15 dígitos ou mais
    como_texto = pd.read_csv(DATA / "anuncios.csv", dtype=str)
    assert como_texto.apply(lambda coluna: coluna.dropna().str.len().max()).max() <= 22  # só rótulos curtos e números


def test_categoria_do_gancho_vem_da_lista_fechada(anuncios):
    assert set(anuncios["categoria_gancho"]) <= set(CATEGORIAS)


def test_cada_grupo_de_criativo_fica_num_pais_so(anuncios):
    assert (anuncios.groupby("grupo_criativo")["pais"].nunique() == 1).all()


def test_tabelas_rapidas_da_analise_rodam_no_extrato(anuncios):
    eua = dados.do_pais(anuncios, "US")
    resumo = analise.resumo_da_coleta(anuncios)
    assert resumo.loc["US", "anúncios"] == len(eua)
    lotes = analise.lotes(anuncios)
    assert lotes.loc["US", "índice de dispersão"] > 5  # lançamentos em lotes, longe de um Poisson
    duracao = analise.duracao_estimada(eua, repeticoes=200)
    tabela = duracao["tabela"]
    assert tabela.loc["lote de lançamento", "largura corrigida"] > tabela.loc["grupo de criativo", "largura corrigida"] > tabela.loc["anúncio", "largura corrigida"]
    assert tabela.loc["anúncio", "corrigida inferior"] < duracao["duracao_corrigida"] < tabela.loc["anúncio", "corrigida superior"]
    ganchos = analise.categorias_de_gancho(anuncios)
    assert list(ganchos.columns) == ["EUA: fração dos anúncios", "EUA: fração dos anúncios com 30 dias ou mais", "Brasil: fração dos anúncios"]
    assert ganchos["EUA: fração dos anúncios"].sum() == pytest.approx(1.0)

"""Forma do bloco `para_o_site.graficos_extras` em reports/resultados.json."""

import json
import re
from pathlib import Path

import pytest

RESULTADOS = Path(__file__).resolve().parents[1] / "reports" / "resultados.json"
IDIOMAS = {"pt", "en", "es"}
PAPEIS = {"principal", "base", "alternativa", "neutro"}
DATA = re.compile(r"\d{4}-\d{2}-\d{2}")


@pytest.fixture(scope="module")
def extras() -> list[dict]:
    return json.loads(RESULTADOS.read_text(encoding="utf-8"))["para_o_site"]["graficos_extras"]


def _tres_idiomas(campo: dict) -> bool:
    return isinstance(campo, dict) and set(campo) == IDIOMAS and all(isinstance(v, str) and v.strip() for v in campo.values())


def test_tem_de_tres_a_cinco_graficos(extras):
    assert 3 <= len(extras) <= 5


@pytest.mark.parametrize("indice", range(5))
def test_cada_grafico_segue_a_especificacao(extras, indice):
    if indice >= len(extras):
        pytest.skip("menos gráficos")
    g = extras[indice]
    assert g["tipo"] in {"linhas", "barras", "pontos"}
    for campo in ("titulo", "eixo_x", "eixo_y", "leitura"):
        assert _tres_idiomas(g[campo]), campo
    assert all(len(t) <= 90 for t in g["titulo"].values())
    assert g["formato_x"] in {"numero", "percentual", "moeda", "data"} and g["formato_y"] in {"numero", "percentual", "moeda", "data"}
    assert "moeda" not in (g["formato_x"], g["formato_y"])  # nada em moeda neste estudo
    assert 1 <= len(g["series"]) <= 4
    limite = 300 if g["tipo"] == "pontos" else 80
    for serie in g["series"]:
        assert _tres_idiomas(serie["nome"]) and serie["papel"] in PAPEIS
        assert 1 <= len(serie["pontos"]) <= limite
        for x, y in serie["pontos"]:
            assert isinstance(y, (int, float))
            if g["tipo"] == "barras":
                assert isinstance(x, str)
            elif g["formato_x"] == "data":
                assert DATA.fullmatch(x)
            else:
                assert isinstance(x, (int, float))
        if g["tipo"] == "barras" and "rotulos" in serie:
            assert set(serie["rotulos"]) == IDIOMAS
            assert all(len(r) == len(serie["pontos"]) for r in serie["rotulos"].values())
            assert serie["rotulos"]["pt"] == [x for x, _ in serie["pontos"]]
        if g["formato_y"] == "percentual":
            assert all(0 <= y <= 1 for _, y in serie["pontos"])
    if "faixa" in g:
        assert g["tipo"] == "linhas"
        faixa = g["faixa"]
        assert 0 <= faixa["serie"] < len(g["series"])
        assert len(faixa["inferior"]) == len(faixa["superior"]) == len(g["series"][faixa["serie"]]["pontos"])
        assert all(i[1] <= s[1] for i, s in zip(faixa["inferior"], faixa["superior"]))


def test_numeros_no_formato_de_cada_idioma(extras):
    for g in extras:
        texto_en = g["leitura"]["en"] + g["titulo"]["en"]
        texto_pt = g["leitura"]["pt"] + g["titulo"]["pt"]
        assert not re.search(r"\d,\d", texto_en)  # inglês usa ponto decimal
        assert not re.search(r"\d\.\d", texto_pt)  # português usa vírgula decimal

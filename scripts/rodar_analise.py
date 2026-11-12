"""Roda a análise completa a partir do extrato em data/ e grava reports/resultados.json e as figuras."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from anuncios_concorrente import analise, dados, graficos

SAIDA = Path("reports")
FIGURAS = SAIDA / "figuras"


def _json(tabela: pd.DataFrame, orient: str = "index"):
    return json.loads(tabela.to_json(orient=orient, force_ascii=False, double_precision=6))


def _n(valor: float, casas: int, idioma: str) -> str:
    """Número no formato do idioma: vírgula decimal em pt e es, ponto em en; milhar ao contrário."""
    texto = f"{valor:,.{casas}f}"
    return texto if idioma == "en" else texto.replace(",", "§").replace(".", ",").replace("§", ".")


def bloco_para_o_site(coleta: dict, resumo: pd.DataFrame, duracao: dict, atributos: dict) -> dict:
    """Textos e gráfico do estudo para o site do portfólio, nos três idiomas, montados a partir dos resultados."""
    total, por_anuncio = atributos["atributos testados"], atributos["significativos por anúncio"]
    por_criativo, por_lote = atributos["significativos por criativo"], atributos["significativos por lote"]
    ingenua, corrigida = duracao["media_ingenua"], duracao["duracao_corrigida"]
    inferior = float(duracao["tabela"].loc["lote de lançamento", "corrigida inferior"])
    superior = float(duracao["tabela"].loc["lote de lançamento", "corrigida superior"])
    eua, brasil = int(resumo.loc["US", "anúncios"]), int(resumo.loc["BR", "anúncios"])
    criativos = int(resumo["grupos de criativo"].sum())
    dia = pd.Timestamp(coleta["data_da_coleta"])
    return {
        "numero_chave": {idioma: f"{por_anuncio} → {por_lote}" for idioma in ("pt", "en", "es")},
        "pergunta": {
            "pt": "O que o líder do mercado mantém no ar, e o que isso diz (e não diz) sobre o que funciona?",
            "en": "What does the market leader keep running, and what does that tell us (or not) about what works?",
            "es": "¿Qué mantiene al aire el líder del mercado, y qué dice (y qué no dice) eso sobre lo que funciona?",
        },
        "resultado": {
            "pt": f"De {total} atributos de anúncio, {por_anuncio} parecem ligados à longevidade quando cada anúncio conta como independente; quando a unidade é o lote de lançamento, sobra {por_lote}, e é uma configuração de campanha. A foto dos anúncios ativos mostra o que foi lançado antes, não o que funciona.",
            "en": f"Of {total} ad attributes, {por_anuncio} look tied to longevity when every ad counts as independent; once the unit is the launch batch, {por_lote} is left, and it is a campaign setting. A snapshot of active ads shows what was launched earlier, not what works.",
            "es": f"De {total} atributos de anuncio, {por_anuncio} parecen ligados a la longevidad cuando cada anuncio cuenta como independiente; cuando la unidad es el lote de lanzamiento, queda {por_lote}, y es una configuración de campaña. La foto de los anuncios activos muestra lo que se lanzó antes, no lo que funciona.",
        },
        "detalhe": {
            "pt": f"A média de {_n(ingenua, 1, 'pt')} “dias no ar” também não é a duração de um anúncio: corrigido o viés da foto, a estimativa é de {_n(corrigida, 0, 'pt')} dias, com intervalo honesto de {_n(inferior, 0, 'pt')} a {_n(superior, 0, 'pt')}. Só fotos semanais, para ver quais anúncios saem do ar, separam sobrevivência de calendário.",
            "en": f"The average of {_n(ingenua, 1, 'en')} “days running” is not an ad's lifetime either: corrected for snapshot bias the estimate is {_n(corrigida, 0, 'en')} days, with an honest interval of {_n(inferior, 0, 'en')} to {_n(superior, 0, 'en')}. Only weekly snapshots, showing which ads get pulled, can tell survival from calendar.",
            "es": f"El promedio de {_n(ingenua, 1, 'es')} “días al aire” tampoco es la duración de un anuncio: corregido el sesgo de la foto, la estimación es de {_n(corrigida, 0, 'es')} días, con un intervalo honesto de {_n(inferior, 0, 'es')} a {_n(superior, 0, 'es')}. Solo fotos semanales, para ver qué anuncios salen del aire, separan supervivencia de calendario.",
        },
        "dados": {
            "pt": f"{_n(eua + brasil, 0, 'pt')} anúncios ativos do concorrente líder do segmento ({_n(eua, 0, 'pt')} nos EUA e {brasil} no Brasil), em {criativos} criativos distintos, coletados na Biblioteca de Anúncios da Meta em {dia:%d/%m/%Y}.",
            "en": f"{_n(eua + brasil, 0, 'en')} active ads from the segment's leading competitor ({_n(eua, 0, 'en')} in the US, {brasil} in Brazil) across {criativos} distinct creatives, collected from the Meta Ad Library on {dia:%B} {dia.day}, {dia.year}.",
            "es": f"{_n(eua + brasil, 0, 'es')} anuncios activos del competidor líder del segmento ({_n(eua, 0, 'es')} en EE. UU. y {brasil} en Brasil), en {criativos} creatividades distintas, recogidos de la Biblioteca de Anuncios de Meta el {dia:%d/%m/%Y}.",
        },
        "etiquetas": ["viés de sobrevivência", "paradoxo da inspeção", "regressão isotônica", "bootstrap por grupo", "teste de permutação", "inteligência competitiva"],
        "grafico": {
            "tipo": "barras",
            "titulo": {
                "pt": f"De {total} atributos, {por_anuncio} parecem explicar a longevidade; respeitando os lotes, sobra {por_lote}",
                "en": f"Of {total} attributes, {por_anuncio} seem to explain longevity; respecting launch batches, {por_lote} is left",
                "es": f"De {total} atributos, {por_anuncio} parecen explicar la longevidad; respetando los lotes, queda {por_lote}",
            },
            "eixo_x": {
                "pt": "O que o teste trata como observação independente",
                "en": "What the test treats as an independent observation",
                "es": "Lo que la prueba trata como observación independiente",
            },
            "eixo_y": {
                "pt": f"Atributos associados à idade do anúncio (de {total})",
                "en": f"Attributes associated with ad age (out of {total})",
                "es": f"Atributos asociados a la edad del anuncio (de {total})",
            },
            "formato_x": "numero",
            "formato_y": "numero",
            "series": [
                {
                    "nome": {
                        "pt": "Atributos significativos a 5% (Benjamini-Hochberg)",
                        "en": "Attributes significant at 5% (Benjamini-Hochberg)",
                        "es": "Atributos significativos al 5% (Benjamini-Hochberg)",
                    },
                    "papel": "principal",
                    "pontos": [["Cada anúncio", por_anuncio], ["Cada criativo", por_criativo], ["Cada lote de lançamento", por_lote]],
                    "rotulos": {
                        "pt": ["Cada anúncio", "Cada criativo", "Cada lote de lançamento"],
                        "en": ["Each ad", "Each creative", "Each launch batch"],
                        "es": ["Cada anuncio", "Cada creatividad", "Cada lote de lanzamiento"],
                    },
                }
            ],
        },
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    inicio = time.time()
    FIGURAS.mkdir(parents=True, exist_ok=True)

    anuncios, coleta = dados.carregar_anuncios(), dados.carregar_coleta()
    eua = dados.do_pais(anuncios, "US")

    resumo = analise.resumo_da_coleta(anuncios)
    simulacao = analise.simulacao()
    cobertura = analise.cobertura_dos_intervalos()
    duracao = analise.duracao_estimada(eua)
    curva = analise.curva_de_sobrevivencia(eua)
    sensibilidade = analise.sensibilidade_ao_ritmo(eua)
    lotes = analise.lotes(anuncios)
    por_data = analise.lancamentos_por_data(eua)
    estrutura = analise.estrutura_do_portfolio(anuncios)
    atributos = analise.atributos_e_idade(eua)
    resumo_atributos = analise.resumo_dos_atributos(atributos)
    relancamento = analise.relancamento(eua)
    ganchos = analise.categorias_de_gancho(anuncios)

    figuras = {
        "rigor": graficos.rigor(resumo_atributos),
        "simulacao": graficos.simulacao(simulacao),
        "sobrevivencia": graficos.sobrevivencia(curva, duracao),
        "lotes": graficos.lotes(por_data, lotes.loc["US"]),
        "intervalos": graficos.intervalos(duracao),
        "atributos": graficos.atributos(atributos),
    }
    for nome, figura in figuras.items():
        figura.savefig(FIGURAS / f"{nome}.png")
        plt.close(figura)

    resultados = {
        "coleta": coleta,
        "resumo_da_coleta": _json(resumo),
        "cobertura_da_classificacao_eua": _json(analise.cobertura_da_classificacao(eua)),
        "simulacao": _json(simulacao, "records"),
        "cobertura_dos_intervalos": _json(cobertura, "records"),
        "duracao_estimada_eua": {**{k: v for k, v in duracao.items() if k != "tabela"}, "intervalos_por_unidade": _json(duracao["tabela"])},
        "curva_de_sobrevivencia_eua": _json(curva.round(5), "records"),
        "sensibilidade_ao_ritmo_eua": _json(sensibilidade.reset_index(), "records"),
        "lotes": _json(lotes),
        "lancamentos_por_data_eua": _json(por_data.round(3), "records"),
        "estrutura_do_portfolio": estrutura,
        "atributos_e_idade_eua": _json(atributos),
        "resumo_dos_atributos": resumo_atributos,
        "relancamento_eua": relancamento,
        "categorias_de_gancho": _json(ganchos),
        "para_o_site": bloco_para_o_site(coleta, resumo, duracao, resumo_atributos),
    }

    def padrao(valor):
        if isinstance(valor, (np.integer,)):
            return int(valor)
        if isinstance(valor, (np.floating,)):
            return float(valor)
        if isinstance(valor, (np.bool_,)):
            return bool(valor)
        return str(valor)

    texto = json.dumps(resultados, indent=2, ensure_ascii=False, default=padrao).replace("NaN", "null")
    (SAIDA / "resultados.json").write_text(texto + "\n", encoding="utf-8", newline="\n")

    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.float_format", lambda v: f"{v:.3f}")
    print(resumo.T.to_string())
    print(simulacao[["duração", "ritmo", "leitura ingênua", "erro da ingênua", "corrigida", "erro da corrigida", "duração real dos fotografados"]].to_string())
    print(cobertura.to_string())
    print({k: v for k, v in duracao.items() if k != "tabela"})
    print(duracao["tabela"].T.to_string())
    print(sensibilidade.to_string())
    print(lotes.T.to_string())
    print(atributos[["com o atributo", "diferença (dias)", "IC 95% inferior", "IC 95% superior", "p ajustado por anúncio", "p ajustado por criativo", "p ajustado por lote"]].to_string())
    print(resumo_atributos)
    print(ganchos.to_string())
    print(f"Gravado em {SAIDA / 'resultados.json'} e {FIGURAS}")
    print(f"Tempo total: {time.time() - inicio:.0f} s")


if __name__ == "__main__":
    main()

"""Figuras do estudo. Azul é sempre o método principal; laranja, a leitura ingênua; verde-água, a alternativa."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

from anuncios_concorrente.estilo import (
    APAGADO, AQUA, AZUL, EIXO, ESTILO, LARANJA, TINTA, TINTA_SECUNDARIA, milhar, nova_figura, numero, percentual,
)


def _grade_vertical(ax: plt.Axes) -> None:
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)


def rigor(resumo: dict) -> Figure:
    """Quantos atributos parecem ligados à idade, conforme a unidade tratada como independente."""
    barras = [
        ("Cada anúncio é independente\n(a leitura ingênua)", resumo["significativos por anúncio"], LARANJA),
        ("Cada grupo de criativo\né independente", resumo["significativos por criativo"], AQUA),
        ("Cada lote de lançamento\né independente", resumo["significativos por lote"], AZUL),
    ]
    total = resumo["atributos testados"]
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            f"De {total} atributos, {barras[0][1]} parecem explicar a longevidade; respeitando os lotes, sobra {barras[2][1]}",
            "Atributos com diferença de idade significativa na foto (5%, após Benjamini-Hochberg), conforme a unidade embaralhada no teste.",
            altura=3.5,
        )
        fig.subplots_adjust(left=0.27, bottom=0.17, right=0.95)
        _grade_vertical(ax)
        for y, (rotulo, valor, cor) in enumerate(barras):
            ax.barh(y, valor, height=0.5, color=cor, zorder=3)
            ax.annotate(f"{valor} de {total}", (valor, y), xytext=(7, 0), textcoords="offset points", va="center", color=TINTA, fontsize=10.5, fontweight="bold")
        ax.set_yticks(range(len(barras)), [b[0] for b in barras])
        ax.set_ylim(-0.6, len(barras) - 0.4)
        ax.invert_yaxis()
        ax.set_xlim(0, total * 1.12)
        ax.set_xticks(range(0, total + 1, 5))
        ax.set_xlabel("atributos associados à idade do anúncio na foto")
        return fig


def simulacao(tabela: pd.DataFrame) -> Figure:
    """Leitura ingênua e correção contra a duração real conhecida, em fotos simuladas."""
    constante = tabela[tabela["ritmo"] == "Ritmo constante"]
    mistura = tabela[(tabela["duração"] == "Muitos testes curtos, poucos anúncios longos") & (tabela["ritmo"] != "Ritmo constante")]
    linhas = [(f"{r['duração']}\n(ritmo constante)", r) for _, r in constante.iterrows()]
    linhas += [(f"Testes curtos e anúncios longos\n({r['ritmo'][0].lower() + r['ritmo'][1:]})", r) for _, r in mistura.iterrows()]
    real = float(tabela["duração média real"].iloc[0])
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            "A média de “dias no ar” erra a duração real para os dois lados",
            f"Fotos simuladas de anúncios cuja duração média real é de {numero(real, 0)} dias. Ponto = média das fotos; traço = 95% das fotos.",
            altura=5.2,
        )
        fig.subplots_adjust(left=0.33, bottom=0.16, right=0.97, top=0.84)
        _grade_vertical(ax)
        posicoes = [0, 1, 2, 3.6, 4.6, 5.6]
        for y, (_, r) in zip(posicoes, linhas):
            for desvio, chave, cor in [(-0.17, "ingênua", LARANJA), (0.17, "corrigida", AZUL)]:
                centro = r["leitura ingênua"] if chave == "ingênua" else r["corrigida"]
                ax.plot([r[f"{chave} inferior"], r[f"{chave} superior"]], [y + desvio] * 2, color=cor, linewidth=2, zorder=2)
                ax.plot(centro, y + desvio, "o", color=cor, zorder=3)
                ax.annotate(numero(centro, 0), (r[f"{chave} superior"], y + desvio), xytext=(6, 0), textcoords="offset points", va="center", color=TINTA_SECUNDARIA, fontsize=8.5)
        ax.axvline(real, color=TINTA, linewidth=1.2, zorder=1)
        ax.annotate(f"duração real: {numero(real, 0)} dias", (real, -0.72), xytext=(5, 0), textcoords="offset points", color=TINTA, fontsize=8.5, va="center")
        ax.annotate(
            "quando o ritmo de lançamento não é constante", (real, 2.83), xytext=(8, 0), textcoords="offset points", color=TINTA_SECUNDARIA,
            fontsize=8.5, va="center", bbox={"facecolor": "#fcfcfb", "edgecolor": "none", "pad": 1.5},
        )
        ax.set_yticks(posicoes, [rotulo for rotulo, _ in linhas], fontsize=8.8)
        ax.set_ylim(-1.0, 6.2)
        ax.invert_yaxis()
        ax.set_xlim(0, max(150, float(tabela.loc[mistura.index, "corrigida superior"].max()) * 1.08))
        ax.set_xlabel("dias")
        marcas = [
            Line2D([], [], marker="o", color=LARANJA, label="leitura ingênua: média de “dias no ar”"),
            Line2D([], [], marker="o", color=AZUL, label="correção: duração média estimada pela foto"),
        ]
        ax.legend(handles=marcas, loc="upper center", bbox_to_anchor=(0.32, -0.1), ncol=2, fontsize=8.8)
        return fig


def sobrevivencia(curva: pd.DataFrame, duracao: dict) -> Figure:
    """Curva de sobrevivência: leitura ingênua, correção com faixa por lote e alternativa de ritmo."""
    saem = 1 - duracao["chegam_ao_dia_8"]
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            "Corrigida, a curva cai cedo; mas a faixa honesta cabe quase qualquer curva",
            f"Fração dos anúncios que chega a cada dia no ar (EUA). Com ritmo constante, {percentual(saem)} sairiam na 1ª semana. Faixa: 95% reamostrando lotes.",
            altura=4.6, largura=8.6,
        )
        fig.subplots_adjust(bottom=0.25, left=0.08)
        dia = curva["dia"]
        ax.fill_between(dia, curva["inferior (lote)"], curva["superior (lote)"], step="post", color=AZUL, alpha=0.13, linewidth=0, zorder=1)
        ax.step(dia, curva["leitura ingênua"], where="post", color=LARANJA, zorder=3, label="leitura ingênua: fração dos anúncios da foto com essa idade ou mais")
        ax.step(dia, curva["corrigida, ritmo 2x"], where="post", color=AQUA, zorder=3, label="correção, se o ritmo de lançamento dobrou ao longo da janela")
        ax.step(dia, curva["corrigida"], where="post", color=AZUL, zorder=4, label="correção, com ritmo de lançamento constante")
        ax.set_xlim(1, float(dia.max()))
        ax.set_ylim(0, 1.02)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: percentual(v)))
        ax.set_xticks([1, 7, 14, 21, 30, 45, 60, 76])
        ax.set_xlabel("dias no ar")
        ax.set_ylabel("anúncios que chegam a esse dia")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, fontsize=8.8)
        return fig


def lotes(por_data: pd.DataFrame, resumo: pd.Series) -> Figure:
    """Anúncios ainda no ar por data de início, com a curva decrescente que o ritmo constante exigiria."""
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            f"Os anúncios sobem em lotes: três datas concentram {percentual(resumo['três maiores lotes (fração)'])} do que está no ar",
            "Anúncios ativos na foto por data de início (EUA). A linha é o que se esperaria com lançamentos no mesmo ritmo todo dia.",
            altura=4.2, largura=8.6,
        )
        fig.subplots_adjust(bottom=0.2, left=0.08)
        x = -por_data["idade"].to_numpy()
        ax.bar(x, por_data["anúncios"], width=0.72, color=APAGADO, zorder=2, label="anúncios ainda no ar, por data de início")
        ax.step(x, por_data["ajuste decrescente"], where="mid", color=AZUL, zorder=3, label="o que o ritmo constante permitiria (só pode cair com a idade)")
        ax.set_ylim(0, float(por_data["anúncios"].max()) * 1.22)
        maiores = por_data.sort_values("anúncios", ascending=False).head(3)
        for _, linha in maiores.iterrows():
            ax.annotate(f"{int(linha['anúncios'])}", (-linha["idade"], linha["anúncios"]), xytext=(0, 3), textcoords="offset points", ha="center", color=TINTA, fontsize=8.5)
        marcos = por_data.iloc[[len(por_data) - 1, 60, 45, 30, 15, 0]]
        ax.set_xticks(-marcos["idade"].to_numpy(), [f"{d[8:10]}/{d[5:7]}" for d in marcos["data"]])
        ax.set_xlabel("data de início do anúncio (a foto é do último dia)")
        ax.set_ylabel("anúncios")
        ax.legend(loc="upper left", fontsize=8.8)
        return fig


def intervalos(duracao: dict) -> Figure:
    """Intervalos de 95% da leitura ingênua e da correção, conforme a unidade reamostrada."""
    tabela = duracao["tabela"]
    vezes = float(tabela.loc["lote de lançamento", "vezes mais largo (ingênua)"])
    with plt.rc_context(ESTILO):
        fig, ax = nova_figura(
            f"Tratar cada anúncio como independente estreita o intervalo em {numero(vezes, 0)} vezes",
            "Intervalos de 95% por bootstrap (EUA), conforme o que é sorteado: anúncios soltos, criativos inteiros ou lotes inteiros.",
            altura=4.3,
        )
        fig.subplots_adjust(left=0.36, bottom=0.15, right=0.97)
        _grade_vertical(ax)
        blocos = [
            ("Leitura ingênua: média de “dias no ar”", "ingênua", duracao["media_ingenua"], LARANJA, 0),
            ("Correção: duração média (ritmo constante)", "corrigida", duracao["duracao_corrigida"], AZUL, 4),
        ]
        posicoes, rotulos = [], []
        for titulo, chave, centro, cor, base in blocos:
            ax.annotate(titulo, (0, base - 0.75), xycoords=("axes fraction", "data"), xytext=(-8, 0), textcoords="offset points", ha="right", va="center", color=TINTA, fontsize=9, fontweight="bold", annotation_clip=False)
            for i, unidade in enumerate(tabela.index):
                y = base + i
                inferior, superior = tabela.loc[unidade, f"{chave} inferior"], tabela.loc[unidade, f"{chave} superior"]
                ax.plot([inferior, superior], [y, y], color=cor, linewidth=2, zorder=2)
                ax.plot(centro, y, "o", color=cor, zorder=3)
                ax.annotate(f"{numero(inferior, 1)} a {numero(superior, 1)}", (superior, y), xytext=(8, 0), textcoords="offset points", va="center", color=TINTA_SECUNDARIA, fontsize=8.8)
                posicoes.append(y)
                rotulos.append(f"sorteando {unidade}s ({milhar(tabela.loc[unidade, 'blocos'])})".replace("lote de lançamentos", "lotes de lançamento").replace("grupo de criativos", "grupos de criativo"))
        ax.set_yticks(posicoes, rotulos, fontsize=8.8)
        ax.set_ylim(-1.3, 6.6)
        ax.invert_yaxis()
        ax.set_xlim(0, float(tabela["corrigida superior"].max()) * 1.25)
        ax.set_xlabel("dias")
        return fig


def atributos(tabela: pd.DataFrame, limiar: float = 0.05) -> Figure:
    """Diferença de idade média por atributo, com intervalo por criativo e o resultado dos três testes."""
    with plt.rc_context(ESTILO):
        passam = int((tabela["p ajustado por lote"] < limiar).sum())
        fig, ax = nova_figura(
            f"Quase todo atributo “anda junto” com a idade; só {passam} resiste quando a unidade é o lote",
            "Diferença de idade média na foto entre anúncios com e sem o atributo (EUA). Traço: IC de 95% reamostrando criativos.",
            altura=6.6, largura=8.8,
        )
        fig.subplots_adjust(left=0.34, bottom=0.14, right=0.86, top=0.845)
        _grade_vertical(ax)
        for y, (nome, linha) in enumerate(tabela.iterrows()):
            if linha["p ajustado por lote"] < limiar:
                cor = AZUL
            elif linha["p ajustado por anúncio"] < limiar or linha["p ajustado por criativo"] < limiar:
                cor = LARANJA
            else:
                cor = APAGADO
            ax.plot([linha["IC 95% inferior"], linha["IC 95% superior"]], [y, y], color=cor, linewidth=2, zorder=2)
            ax.plot(linha["diferença (dias)"], y, "o", color=cor, zorder=3)
            ax.annotate(
                f"p por lote: {numero(linha['p ajustado por lote'])}", (1.0, y), xycoords=("axes fraction", "data"), xytext=(6, 0),
                textcoords="offset points", va="center", color=TINTA_SECUNDARIA, fontsize=8.2, annotation_clip=False,
            )
        ax.axvline(0, color=EIXO, linewidth=1.2, zorder=1)
        ax.set_yticks(range(len(tabela)), list(tabela.index), fontsize=8.8)
        ax.set_ylim(-0.7, len(tabela) - 0.3)
        ax.invert_yaxis()
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.0f}".replace("-", "−") if v else "0"))
        ax.set_xlabel("diferença de idade média, em dias (com o atributo − sem o atributo)")
        marcas = [
            Line2D([], [], marker="o", color=AZUL, label="passa também por lote"),
            Line2D([], [], marker="o", color=LARANJA, label="passa só por anúncio ou por criativo"),
            Line2D([], [], marker="o", color=APAGADO, label="não passa"),
        ]
        ax.legend(handles=marcas, loc="upper center", bbox_to_anchor=(0.4, -0.085), ncol=3, fontsize=8.8)
        return fig

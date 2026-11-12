"""Gráficos extras do site do portfólio: as figuras do README como especificação em dados, em três idiomas.

Cada função recebe as mesmas tabelas que geram as figuras PNG; nenhum número é digitado aqui.
"""

from __future__ import annotations

import pandas as pd

IDIOMAS = ("pt", "en", "es")


def _n(valor: float, casas: int, idioma: str) -> str:
    """Número no formato do idioma: vírgula decimal em pt e es, ponto em en; milhar ao contrário."""
    texto = f"{valor:,.{casas}f}"
    return texto if idioma == "en" else texto.replace(",", "§").replace(".", ",").replace("§", ".")


def _r(valor: float, casas: int = 4) -> float:
    return round(float(valor), casas)


# Tradução dos nomes dos atributos testados (mesma chave que `analise.atributos_e_idade` usa).
ATRIBUTOS = {
    "Formato: vídeo único (não dinâmico)": ("Single video (not dynamic)", "Video único (no dinámico)"),
    "Veicula em 5 ou mais plataformas": ("Runs on 5+ placements", "Se publica en 5 o más plataformas"),
    "Tem 2 ou mais variações": ("2+ variations", "2 o más variaciones"),
    "Vídeo mais longo que a mediana": ("Video longer than median", "Video más largo que la mediana"),
    "Vídeo gerado por IA (vs. real)": ("AI-generated video (vs. real)", "Video generado por IA (vs. real)"),
    "Cena de reação (vs. outras cenas)": ("Reaction scene (vs. others)", "Escena de reacción (vs. otras)"),
    "Promete prévia grátis": ("Promises a free preview", "Promete una muestra gratis"),
    "Prova social no texto ou título": ("Social proof in copy or headline", "Prueba social en texto o título"),
    "Urgência (tempo limitado)": ("Urgency (limited time)", "Urgencia (tiempo limitado)"),
    "Cita ocasião ou data": ("Mentions an occasion or date", "Menciona ocasión o fecha"),
    "Tem pergunta": ("Asks a question", "Hace una pregunta"),
    "Texto mais longo que a mediana": ("Copy longer than median", "Texto más largo que la mediana"),
    "Mais emojis que a mediana": ("More emojis than median", "Más emojis que la mediana"),
    "Texto em espanhol (vs. inglês)": ("Copy in Spanish (vs. English)", "Texto en español (vs. inglés)"),
    "Gancho: preço": ("Hook: price", "Gancho: precio"),
    "Gancho: prova social": ("Hook: social proof", "Gancho: prueba social"),
    "Gancho: reação emocionada": ("Hook: emotional reaction", "Gancho: reacción emocionada"),
    "Gancho: troca de presente": ("Hook: swap the usual gift", "Gancho: cambiar el regalo de siempre"),
    "Gancho: nicho (fé, country, amizade)": ("Hook: niche (faith, country, friendship)", "Gancho: nicho (fe, country, amistad)"),
    "Gancho: ocasião ou data": ("Hook: occasion or date", "Gancho: ocasión o fecha"),
    "Gancho: oferta ou objeção": ("Hook: offer or objection", "Gancho: oferta u objeción"),
    "Gancho: promessa ou curiosidade": ("Hook: promise or curiosity", "Gancho: promesa o curiosidad"),
}

# Os cenários da figura de simulação, na mesma ordem dela.
CENARIOS = [
    ("Todo anúncio dura 20 dias", "Ritmo constante", ("Fixed lifetime, steady pace", "Duración fija, ritmo constante")),
    ("Risco constante de sair do ar", "Ritmo constante", ("Constant risk, steady pace", "Riesgo constante, ritmo constante")),
    ("Muitos testes curtos, poucos anúncios longos", "Ritmo constante", ("Short tests + long runners, steady pace", "Pruebas cortas + anuncios largos, ritmo constante")),
    ("Muitos testes curtos, poucos anúncios longos", "Ritmo dobra a cada 30 dias", ("Short tests + long runners, pace doubling", "Pruebas cortas + anuncios largos, ritmo que se duplica")),
    ("Muitos testes curtos, poucos anúncios longos", "Lançamentos em lotes irregulares", ("Short tests + long runners, batch launches", "Pruebas cortas + anuncios largos, lanzamientos en lotes")),
    ("Muitos testes curtos, poucos anúncios longos", "Conta começou há 30 dias", ("Short tests + long runners, account opened 30 days ago", "Pruebas cortas + anuncios largos, cuenta de 30 días")),
]
ROTULO_PT_DO_CENARIO = [
    "Duração fixa, ritmo constante",
    "Risco constante, ritmo constante",
    "Testes curtos e anúncios longos, ritmo constante",
    "Testes curtos e anúncios longos, ritmo dobrando",
    "Testes curtos e anúncios longos, lançamentos em lotes",
    "Testes curtos e anúncios longos, conta de 30 dias",
]


def _simulacao(simulacao: pd.DataFrame) -> dict:
    linhas = [simulacao[(simulacao["duração"] == d) & (simulacao["ritmo"] == r)].iloc[0] for d, r, _ in CENARIOS]
    rotulos = {"pt": ROTULO_PT_DO_CENARIO, "en": [c[2][0] for c in CENARIOS], "es": [c[2][1] for c in CENARIOS]}
    real = float(linhas[0]["duração média real"])
    menor, maior = min(float(x["erro da ingênua"]) for x in linhas[:3]), max(float(x["erro da ingênua"]) for x in linhas[:3])

    def serie(nome: dict, papel: str, coluna: str) -> dict:
        return {"nome": nome, "papel": papel, "pontos": [[rotulos["pt"][i], _r(x[coluna], 2)] for i, x in enumerate(linhas)], "rotulos": rotulos}

    return {
        "tipo": "barras",
        "titulo": {
            "pt": "A média de “dias no ar” erra a duração real para os dois lados",
            "en": "Average “days running” misses the true lifetime in both directions",
            "es": "El promedio de “días al aire” falla la duración real hacia ambos lados",
        },
        "eixo_x": {"pt": "Cenário simulado", "en": "Simulated scenario", "es": "Escenario simulado"},
        "eixo_y": {"pt": "Dias", "en": "Days", "es": "Días"},
        "formato_x": "numero",
        "formato_y": "numero",
        "series": [
            serie({"pt": "Leitura ingênua (média de dias no ar)", "en": "Naive reading (mean days running)", "es": "Lectura ingenua (promedio de días al aire)"}, "base", "leitura ingênua"),
            serie({"pt": "Correção pela foto", "en": "Snapshot correction", "es": "Corrección por la foto"}, "principal", "corrigida"),
            serie({"pt": "Duração média real", "en": "True mean lifetime", "es": "Duración media real"}, "neutro", "duração média real"),
        ],
        "leitura": {
            "pt": f"Em fotos simuladas de anúncios que duram {_n(real, 0, 'pt')} dias em média, a leitura ingênua erra de {_n(menor * 100, 0, 'pt')}% a +{_n(maior * 100, 0, 'pt')}% com ritmo constante; a correção acerta nesse caso e erra quando o ritmo muda.",
            "en": f"In simulated snapshots of ads that last {_n(real, 0, 'en')} days on average, the naive reading is off by {_n(menor * 100, 0, 'en')}% to +{_n(maior * 100, 0, 'en')}% at a steady pace; the correction gets it right there and fails when the pace changes.",
            "es": f"En fotos simuladas de anuncios que duran {_n(real, 0, 'es')} días en promedio, la lectura ingenua se equivoca entre {_n(menor * 100, 0, 'es')}% y +{_n(maior * 100, 0, 'es')}% con ritmo constante; la corrección acierta en ese caso y falla cuando el ritmo cambia.",
        },
    }


def _sobrevivencia(curva: pd.DataFrame, duracao: dict) -> dict:
    dia = curva["dia"].astype(int).tolist()

    def pontos(coluna: str) -> list:
        return [[d, _r(v)] for d, v in zip(dia, curva[coluna])]

    sai = 1 - duracao["chegam_ao_dia_8"]
    return {
        "tipo": "linhas",
        "titulo": {
            "pt": "Corrigida, a curva cai cedo; mas a faixa honesta cabe quase qualquer curva",
            "en": "Corrected, the curve drops early, but the honest band fits almost any curve",
            "es": "Corregida, la curva cae pronto, pero la banda honesta admite casi cualquier curva",
        },
        "eixo_x": {"pt": "Dias no ar", "en": "Days running", "es": "Días al aire"},
        "eixo_y": {"pt": "Anúncios que chegam a esse dia", "en": "Ads that reach this day", "es": "Anuncios que llegan a ese día"},
        "formato_x": "numero",
        "formato_y": "percentual",
        "series": [
            {"nome": {"pt": "Correção, ritmo constante", "en": "Correction, steady pace", "es": "Corrección, ritmo constante"}, "papel": "principal", "pontos": pontos("corrigida")},
            {"nome": {"pt": "Leitura ingênua", "en": "Naive reading", "es": "Lectura ingenua"}, "papel": "base", "pontos": pontos("leitura ingênua")},
            {"nome": {"pt": "Correção, se o ritmo dobrou", "en": "Correction, if the pace doubled", "es": "Corrección, si el ritmo se duplicó"}, "papel": "alternativa", "pontos": pontos("corrigida, ritmo 2x")},
        ],
        "faixa": {"serie": 0, "inferior": pontos("inferior (lote)"), "superior": pontos("superior (lote)")},
        "leitura": {
            "pt": f"Com ritmo de lançamento constante, {_n(sai * 100, 0, 'pt')}% dos anúncios do concorrente nos EUA sairiam do ar na primeira semana; a faixa de 95%, sorteando lotes, mostra que a foto não fixa a curva.",
            "en": f"At a steady launch pace, {_n(sai * 100, 0, 'en')}% of the competitor's US ads would be pulled within the first week; the 95% band, resampling launch batches, shows the snapshot does not pin the curve down.",
            "es": f"Con un ritmo de lanzamiento constante, el {_n(sai * 100, 0, 'es')}% de los anuncios del competidor en EE. UU. saldría del aire en la primera semana; la banda del 95%, remuestreando lotes, muestra que la foto no fija la curva.",
        },
    }


def _intervalos(duracao: dict) -> dict:
    tabela = duracao["tabela"]
    rotulos = {
        "pt": ["Anúncios soltos", "Grupos de criativo", "Lotes de lançamento"],
        "en": ["Single ads", "Creative groups", "Launch batches"],
        "es": ["Anuncios sueltos", "Grupos de creatividad", "Lotes de lanzamiento"],
    }
    unidades = ["anúncio", "grupo de criativo", "lote de lançamento"]
    vezes = float(tabela.loc["lote de lançamento", "vezes mais largo (ingênua)"])

    def serie(nome: dict, papel: str, coluna: str) -> dict:
        return {"nome": nome, "papel": papel, "pontos": [[rotulos["pt"][i], _r(tabela.loc[u, coluna], 2)] for i, u in enumerate(unidades)], "rotulos": rotulos}

    return {
        "tipo": "barras",
        "titulo": {
            "pt": f"Tratar cada anúncio como independente estreita o intervalo em {_n(vezes, 0, 'pt')} vezes",
            "en": f"Treating every ad as independent makes the interval {_n(vezes, 0, 'en')} times too narrow",
            "es": f"Tratar cada anuncio como independiente estrecha el intervalo {_n(vezes, 0, 'es')} veces",
        },
        "eixo_x": {"pt": "O que o bootstrap sorteia", "en": "What the bootstrap resamples", "es": "Lo que remuestrea el bootstrap"},
        "eixo_y": {"pt": "Largura do intervalo de 95% (dias)", "en": "Width of the 95% interval (days)", "es": "Ancho del intervalo del 95% (días)"},
        "formato_x": "numero",
        "formato_y": "numero",
        "series": [
            serie({"pt": "Leitura ingênua", "en": "Naive reading", "es": "Lectura ingenua"}, "base", "largura ingênua"),
            serie({"pt": "Correção (ritmo constante)", "en": "Correction (steady pace)", "es": "Corrección (ritmo constante)"}, "principal", "largura corrigida"),
        ],
        "leitura": {
            "pt": f"O mesmo cálculo, nos EUA, com intervalos de 95% conforme o que é sorteado: de {_n(tabela.loc['anúncio', 'ingênua inferior'], 1, 'pt')} a {_n(tabela.loc['anúncio', 'ingênua superior'], 1, 'pt')} dias sorteando anúncios, de {_n(tabela.loc['lote de lançamento', 'ingênua inferior'], 1, 'pt')} a {_n(tabela.loc['lote de lançamento', 'ingênua superior'], 1, 'pt')} sorteando lotes.",
            "en": f"The same estimate for the US, with 95% intervals by what is resampled: {_n(tabela.loc['anúncio', 'ingênua inferior'], 1, 'en')} to {_n(tabela.loc['anúncio', 'ingênua superior'], 1, 'en')} days resampling ads, {_n(tabela.loc['lote de lançamento', 'ingênua inferior'], 1, 'en')} to {_n(tabela.loc['lote de lançamento', 'ingênua superior'], 1, 'en')} resampling batches.",
            "es": f"El mismo cálculo, en EE. UU., con intervalos del 95% según lo que se sortea: de {_n(tabela.loc['anúncio', 'ingênua inferior'], 1, 'es')} a {_n(tabela.loc['anúncio', 'ingênua superior'], 1, 'es')} días sorteando anuncios, de {_n(tabela.loc['lote de lançamento', 'ingênua inferior'], 1, 'es')} a {_n(tabela.loc['lote de lançamento', 'ingênua superior'], 1, 'es')} sorteando lotes.",
        },
    }


def _atributos(atributos: pd.DataFrame, limiar: float = 0.05) -> dict:
    nomes = list(atributos.index)
    rotulos = {"pt": nomes, "en": [ATRIBUTOS[n][0] for n in nomes], "es": [ATRIBUTOS[n][1] for n in nomes]}
    passam = int((atributos["p ajustado por lote"] < limiar).sum())
    return {
        "tipo": "barras",
        "titulo": {
            "pt": f"Quase todo atributo “anda junto” com a idade; só {passam} resiste quando a unidade é o lote",
            "en": f"Almost every attribute “moves with” ad age; only {passam} survives at the batch level",
            "es": f"Casi todo atributo “va de la mano” con la edad; solo {passam} resiste por lote",
        },
        "eixo_x": {"pt": "Atributo do anúncio", "en": "Ad attribute", "es": "Atributo del anuncio"},
        "eixo_y": {"pt": "Diferença de idade média (dias)", "en": "Difference in mean age (days)", "es": "Diferencia de edad media (días)"},
        "formato_x": "numero",
        "formato_y": "numero",
        "series": [
            {
                "nome": {"pt": "Com o atributo − sem o atributo", "en": "With the attribute − without it", "es": "Con el atributo − sin él"},
                "papel": "principal",
                "pontos": [[n, _r(v, 2)] for n, v in zip(nomes, atributos["diferença (dias)"])],
                "rotulos": rotulos,
            }
        ],
        "leitura": {
            "pt": f"Diferença de idade média na foto entre anúncios com e sem cada atributo, nos EUA. Pela permutação por anúncio quase todos são significativos; embaralhando lotes inteiros, {passam} de {len(nomes)} passa.",
            "en": f"Difference in snapshot age between US ads with and without each attribute. Under ad-level permutation almost all are significant; shuffling whole launch batches, {passam} of {len(nomes)} passes.",
            "es": f"Diferencia de edad en la foto entre anuncios con y sin cada atributo, en EE. UU. Con permutación por anuncio casi todos son significativos; barajando lotes enteros, pasa {passam} de {len(nomes)}.",
        },
    }


def _lotes(por_data: pd.DataFrame, lotes_eua: pd.Series) -> dict:
    ordem = por_data.sort_values("data")
    tres = float(lotes_eua["três maiores lotes (fração)"])
    dispersao = float(lotes_eua["índice de dispersão"])
    return {
        "tipo": "linhas",
        "titulo": {
            "pt": f"Os anúncios sobem em lotes: três datas concentram {_n(tres * 100, 0, 'pt')}% do que está no ar",
            "en": f"Ads launch in batches: three dates hold {_n(tres * 100, 0, 'en')}% of what is running",
            "es": f"Los anuncios salen en lotes: tres fechas concentran el {_n(tres * 100, 0, 'es')}% de lo que está al aire",
        },
        "eixo_x": {"pt": "Data de início do anúncio", "en": "Ad start date", "es": "Fecha de inicio del anuncio"},
        "eixo_y": {"pt": "Anúncios ainda no ar", "en": "Ads still running", "es": "Anuncios todavía al aire"},
        "formato_x": "data",
        "formato_y": "numero",
        "series": [
            {"nome": {"pt": "Anúncios ainda no ar, por data de início", "en": "Ads still running, by start date", "es": "Anuncios al aire, por fecha de inicio"}, "papel": "neutro", "pontos": [[d, int(v)] for d, v in zip(ordem["data"], ordem["anúncios"])]},
            {"nome": {"pt": "O que o ritmo constante permitiria", "en": "What a steady pace would allow", "es": "Lo que permitiría un ritmo constante"}, "papel": "principal", "pontos": [[d, _r(v, 2)] for d, v in zip(ordem["data"], ordem["ajuste decrescente"])]},
        ],
        "leitura": {
            "pt": f"Anúncios ativos do concorrente nos EUA por data de início. Com lançamentos no mesmo ritmo todo dia, as barras seguiriam a linha; o índice de dispersão é {_n(dispersao, 0, 'pt')}, quando seria perto de 1.",
            "en": f"The competitor's active US ads by start date. With launches at the same pace every day the counts would follow the line; the dispersion index is {_n(dispersao, 0, 'en')}, where it would be close to 1.",
            "es": f"Anuncios activos del competidor en EE. UU. por fecha de inicio. Con lanzamientos al mismo ritmo cada día, los conteos seguirían la línea; el índice de dispersión es {_n(dispersao, 0, 'es')}, cuando sería cercano a 1.",
        },
    }


def graficos_extras(simulacao: pd.DataFrame, curva: pd.DataFrame, duracao: dict, atributos: pd.DataFrame, por_data: pd.DataFrame, lotes_eua: pd.Series) -> list[dict]:
    """Os cinco gráficos extras, do achado mais importante para o menos."""
    return [
        _simulacao(simulacao),
        _sobrevivencia(curva, duracao),
        _intervalos(duracao),
        _atributos(atributos),
        _lotes(por_data, lotes_eua),
    ]

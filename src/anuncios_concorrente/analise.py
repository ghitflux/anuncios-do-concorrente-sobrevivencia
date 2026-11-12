"""Cada tabela do estudo sai de uma função daqui. `scripts/rodar_analise.py` grava tudo em reports/."""

from __future__ import annotations

import numpy as np
import pandas as pd

from anuncios_concorrente import estatistica as est
from anuncios_concorrente import sobrevivencia as sob
from anuncios_concorrente.texto import CATEGORIAS, ROTULOS_DA_CATEGORIA

SEMENTE = 13
UNIDADES = {"anúncio": None, "grupo de criativo": "grupo_criativo", "lote de lançamento": "inicio"}
RAZOES_DE_RITMO = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]


def _blocos(anuncios: pd.DataFrame, unidade: str) -> np.ndarray:
    coluna = UNIDADES[unidade]
    return np.arange(len(anuncios)) if coluna is None else anuncios[coluna].to_numpy()


# ---------------------------------------------------------------------------
# 0. O que há na coleta
# ---------------------------------------------------------------------------


def resumo_da_coleta(anuncios: pd.DataFrame) -> pd.DataFrame:
    """Tamanho e forma da foto, por país."""
    linhas = {}
    for pais, grupo in anuncios.groupby("pais"):
        linhas[pais] = {
            "anúncios": len(grupo),
            "grupos de criativo": grupo["grupo_criativo"].nunique(),
            "textos distintos": grupo["texto_id"].nunique(),
            "datas de lançamento": grupo["inicio"].nunique(),
            "páginas": grupo["pagina"].nunique(),
            "idade média (dias)": grupo["dias_no_ar"].mean(),
            "idade mediana (dias)": grupo["dias_no_ar"].median(),
            "idade máxima (dias)": int(grupo["dias_no_ar"].max()),
            "com vídeo": grupo["tem_video"].mean(),
            "com classificação do vídeo": grupo["tipo_criativo"].notna().mean(),
        }
    return pd.DataFrame(linhas).T


def cobertura_da_classificacao(anuncios: pd.DataFrame) -> pd.DataFrame:
    """Fração dos anúncios com vídeo classificado (real ou gerado, tipo de cena), por faixa de idade."""
    faixa = pd.cut(anuncios["dias_no_ar"], [0, 30, 60, np.inf], labels=["até 30 dias", "31 a 60 dias", "mais de 60 dias"])
    tabela = anuncios.groupby(faixa, observed=True)["tipo_criativo"].agg(anúncios="size", classificados="count")
    tabela["fração classificada"] = tabela["classificados"] / tabela["anúncios"]
    return tabela


# ---------------------------------------------------------------------------
# 1. Simulação de resposta conhecida
# ---------------------------------------------------------------------------

HORIZONTE = 800
ANUNCIOS_POR_DIA = 62.0
DURACAO_REAL = 20


def _cenarios_de_duracao() -> list[sob.Duracao]:
    return [sob.duracao_fixa(DURACAO_REAL), sob.duracao_geometrica(DURACAO_REAL), sob.duracao_mistura(5, 80, 0.2)]


def _cenarios_de_ritmo() -> dict[str, object]:
    return {
        "Ritmo constante": sob.ritmo_constante(HORIZONTE, ANUNCIOS_POR_DIA),
        "Ritmo dobra a cada 30 dias": sob.ritmo_crescente(HORIZONTE, ANUNCIOS_POR_DIA, 30),
        "Lançamentos em lotes irregulares": sob.ritmo_em_lotes(HORIZONTE, ANUNCIOS_POR_DIA, 5, 1.0),
        "Conta começou há 30 dias": sob.ritmo_de_conta_nova(HORIZONTE, ANUNCIOS_POR_DIA, 30),
    }


def simulacao(repeticoes: int = 150, semente: int = SEMENTE) -> pd.DataFrame:
    """Fotos simuladas de anúncios com duração conhecida: quanto erram a leitura ingênua e a correção.

    Em todos os cenários a duração média verdadeira é de 20 dias; muda a forma da distribuição e o
    ritmo de lançamento. Cada linha resume `repeticoes` fotos independentes.
    """
    gerador = np.random.default_rng(semente)
    linhas = []
    for duracao in _cenarios_de_duracao():
        for nome_do_ritmo, ritmo in _cenarios_de_ritmo().items():
            ingenuas, corrigidas, fotografados, vivos = [], [], [], []
            for _ in range(repeticoes):
                foto = sob.simular_foto(gerador, duracao, ritmo, anuncios_por_criativo=2.3, dependencia=0.7)
                if len(foto["idade"]) == 0:
                    continue
                ingenuas.append(foto["idade"].mean())
                corrigidas.append(sob.estimar_pela_foto(sob.contagem_por_idade(foto["idade"])).duracao_media)
                fotografados.append(foto["duracao"].mean())
                vivos.append(len(foto["idade"]))
            constante = nome_do_ritmo == "Ritmo constante"
            linhas.append({
                "duração": duracao.nome,
                "ritmo": nome_do_ritmo,
                "duração média real": duracao.media,
                "anúncios na foto": float(np.mean(vivos)),
                "leitura ingênua": float(np.mean(ingenuas)),
                "ingênua inferior": float(np.quantile(ingenuas, 0.025)),
                "ingênua superior": float(np.quantile(ingenuas, 0.975)),
                "erro da ingênua": float(np.mean(ingenuas) / duracao.media - 1),
                "corrigida": float(np.mean(corrigidas)),
                "corrigida inferior": float(np.quantile(corrigidas, 0.025)),
                "corrigida superior": float(np.quantile(corrigidas, 0.975)),
                "erro da corrigida": float(np.mean(corrigidas) / duracao.media - 1),
                "duração real dos fotografados": float(np.mean(fotografados)),
                "ingênua pela teoria": sob.idade_media_esperada(duracao.pmf) if constante else np.nan,
                "fotografados pela teoria": sob.duracao_media_dos_fotografados(duracao.pmf) if constante else np.nan,
            })
    return pd.DataFrame(linhas)


def cobertura_dos_intervalos(repeticoes: int = 150, reamostragens: int = 300, semente: int = SEMENTE) -> pd.DataFrame:
    """Com que frequência o intervalo de 95% contém a verdade, conforme a unidade reamostrada.

    Mundo simulado com muitos testes curtos e poucos anúncios longos, criativos com mais de um
    anúncio que saem do ar juntos em 70% dos casos. O alvo da leitura ingênua é a idade média que a
    teoria prevê; o alvo da correção é a duração média real.
    """
    duracao = sob.duracao_mistura(5, 80, 0.2)
    alvo_ingenua = sob.idade_media_esperada(duracao.pmf)
    ritmos = _cenarios_de_ritmo()
    linhas = []
    for nome_do_ritmo in ["Ritmo constante", "Lançamentos em lotes irregulares"]:
        gerador = np.random.default_rng(semente)
        acertos = {u: np.zeros(2) for u in UNIDADES}
        larguras = {u: [] for u in UNIDADES}
        for r in range(repeticoes):
            foto = sob.simular_foto(gerador, duracao, ritmos[nome_do_ritmo], anuncios_por_criativo=2.3, dependencia=0.7)
            idade_maxima = int(foto["idade"].max())
            blocos = {"anúncio": np.arange(len(foto["idade"])), "grupo de criativo": foto["criativo"], "lote de lançamento": foto["idade"]}
            for unidade, bloco in blocos.items():
                contagens = est.contagens_reamostradas(foto["idade"], bloco, idade_maxima, reamostragens, semente + r)
                ingenua = est.intervalo(sob.media_ingenua_em_lote(contagens))
                corrigida = est.intervalo(sob.duracao_media_em_lote(contagens))
                acertos[unidade] += [ingenua[0] <= alvo_ingenua <= ingenua[1], corrigida[0] <= duracao.media <= corrigida[1]]
                larguras[unidade].append([ingenua[1] - ingenua[0], corrigida[1] - corrigida[0]])
        for unidade in UNIDADES:
            largura = np.mean(larguras[unidade], axis=0)
            linhas.append({
                "ritmo": nome_do_ritmo,
                "unidade reamostrada": unidade,
                "cobertura (leitura ingênua)": acertos[unidade][0] / repeticoes,
                "cobertura (correção)": acertos[unidade][1] / repeticoes,
                "largura média (leitura ingênua)": float(largura[0]),
                "largura média (correção)": float(largura[1]),
            })
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 2 e 3. Da foto real para a duração, com a incerteza na unidade certa
# ---------------------------------------------------------------------------


def duracao_estimada(anuncios: pd.DataFrame, repeticoes: int = 2000, semente: int = SEMENTE) -> dict:
    """Leitura ingênua e duração corrigida (ritmo constante), com intervalos por unidade reamostrada."""
    idades = anuncios["dias_no_ar"].to_numpy()
    janela = int(idades.max())
    contagens = sob.contagem_por_idade(idades, janela)
    estimativa = sob.estimar_pela_foto(contagens)
    linhas = {}
    for unidade in UNIDADES:
        blocos = _blocos(anuncios, unidade)
        reamostradas = est.contagens_reamostradas(idades, blocos, janela, repeticoes, semente)
        ingenua = est.intervalo(sob.media_ingenua_em_lote(reamostradas))
        duracao = sob.duracao_media_em_lote(reamostradas)
        corrigida = est.intervalo(duracao)
        lancados = est.intervalo(janela * reamostradas.sum(axis=1) / duracao)
        linhas[unidade] = {
            "blocos": len(np.unique(blocos)),
            "ingênua inferior": ingenua[0],
            "ingênua superior": ingenua[1],
            "corrigida inferior": corrigida[0],
            "corrigida superior": corrigida[1],
            "lançados inferior": lancados[0],
            "lançados superior": lancados[1],
        }
    tabela = pd.DataFrame(linhas).T
    tabela["largura ingênua"] = tabela["ingênua superior"] - tabela["ingênua inferior"]
    tabela["largura corrigida"] = tabela["corrigida superior"] - tabela["corrigida inferior"]
    tabela["vezes mais largo (ingênua)"] = tabela["largura ingênua"] / tabela.loc["anúncio", "largura ingênua"]
    tabela["vezes mais largo (corrigida)"] = tabela["largura corrigida"] / tabela.loc["anúncio", "largura corrigida"]
    sem_registro_antigo = anuncios[anuncios["dias_desde_ultimo_registro"] == 0]
    return {
        "anuncios": len(anuncios),
        "janela_em_dias": janela,
        "media_ingenua": float(idades.mean()),
        "mediana_ingenua": float(np.median(idades)),
        "duracao_corrigida": estimativa.duracao_media,
        "lancados_por_dia": estimativa.lancados_por_dia,
        "lancados_na_janela": estimativa.lancados_na_janela,
        "ja_sairam_do_ar": estimativa.lancados_na_janela - estimativa.vivos,
        "fracao_que_ja_saiu": 1 - estimativa.vivos / estimativa.lancados_na_janela,
        **{
            f"chegam_ao_dia_{dia}": float(estimativa.sobrevivencia[dia - 1]) if janela >= dia else float("nan")
            for dia in (8, 15, 31, 61)
        },
        "so_com_registro_no_dia_da_coleta": {
            "anuncios": len(sem_registro_antigo),
            "media_ingenua": float(sem_registro_antigo["dias_no_ar"].mean()),
            "duracao_corrigida": sob.estimar_pela_foto(
                sob.contagem_por_idade(sem_registro_antigo["dias_no_ar"].to_numpy(), janela)
            ).duracao_media,
        },
        "tabela": tabela,
    }


def curva_de_sobrevivencia(anuncios: pd.DataFrame, repeticoes: int = 1000, semente: int = SEMENTE) -> pd.DataFrame:
    """Por idade: a leitura ingênua, a curva corrigida (ritmo constante) com faixas, e duas alternativas de ritmo."""
    idades = anuncios["dias_no_ar"].to_numpy()
    janela = int(idades.max())
    contagens = sob.contagem_por_idade(idades, janela)
    curva = pd.DataFrame({
        "dia": np.arange(1, janela + 1),
        "anúncios com essa idade": contagens,
        "leitura ingênua": sob.sobrevivencia_ingenua(contagens),
        "corrigida": sob.estimar_pela_foto(contagens).sobrevivencia,
    })
    for unidade, sufixo in [("grupo de criativo", "criativo"), ("lote de lançamento", "lote")]:
        reamostradas = est.contagens_reamostradas(idades, _blocos(anuncios, unidade), janela, repeticoes, semente)
        taxa = sob.antitonica_em_lote(reamostradas)
        sobrevivencia = taxa / taxa[:, :1]
        curva[f"inferior ({sufixo})"] = np.quantile(sobrevivencia, 0.025, axis=0)
        curva[f"superior ({sufixo})"] = np.quantile(sobrevivencia, 0.975, axis=0)
    for razao in (2.0, 4.0):
        curva[f"corrigida, ritmo {razao:g}x"] = sob.estimar_pela_foto(contagens, sob.exposicao_do_ritmo(janela, razao)).sobrevivencia
    return curva


def sensibilidade_ao_ritmo(anuncios: pd.DataFrame, repeticoes: int = 2000, semente: int = SEMENTE) -> pd.DataFrame:
    """A mesma foto lida com hipóteses diferentes sobre o ritmo de lançamento ao longo da janela.

    `razão` = lançamentos por dia hoje ÷ lançamentos por dia no início da janela. O intervalo
    reamostra lotes de lançamento.
    """
    idades = anuncios["dias_no_ar"].to_numpy()
    janela = int(idades.max())
    contagens = sob.contagem_por_idade(idades, janela)
    reamostradas = est.contagens_reamostradas(idades, _blocos(anuncios, "lote de lançamento"), janela, repeticoes, semente)
    linhas = []
    for razao in RAZOES_DE_RITMO:
        exposicao = sob.exposicao_do_ritmo(janela, razao)
        estimativa = sob.estimar_pela_foto(contagens, exposicao)
        taxa = sob.antitonica_em_lote(reamostradas, exposicao)
        inferior, superior = est.intervalo((taxa / taxa[:, :1]).sum(axis=1))
        linhas.append({
            "razão do ritmo": razao,
            "duração média": estimativa.duracao_media,
            "inferior (lote)": inferior,
            "superior (lote)": superior,
            "lançados na janela": estimativa.lancados_na_janela,
            "já saíram do ar": estimativa.lancados_na_janela - estimativa.vivos,
            "chegam ao dia 31": float(estimativa.sobrevivencia[30]),
        })
    return pd.DataFrame(linhas).set_index("razão do ritmo")


# ---------------------------------------------------------------------------
# 4. Estrutura do portfólio de criativos
# ---------------------------------------------------------------------------


def lotes(anuncios: pd.DataFrame) -> pd.DataFrame:
    """Ritmo e tamanho dos lotes de lançamento (entre os anúncios que ainda estão no ar), por país."""
    linhas = {}
    for pais, grupo in anuncios.groupby("pais"):
        janela = int(grupo["dias_no_ar"].max())
        contagens = sob.contagem_por_idade(grupo["dias_no_ar"].to_numpy(), janela)
        por_data = np.sort(contagens[contagens > 0])[::-1]
        datas = np.sort(grupo["inicio"].unique())
        intervalos = np.diff(datas).astype("timedelta64[D]").astype(int)
        linhas[pais] = {
            "janela (dias)": janela,
            "datas com lançamento": int((contagens > 0).sum()),
            "anúncios por data (mediana)": float(np.median(por_data)),
            "maior lote (anúncios)": int(por_data[0]),
            "maior lote (fração)": float(por_data[0] / len(grupo)),
            "três maiores lotes (fração)": float(por_data[:3].sum() / len(grupo)),
            "dias entre lançamentos (mediana)": float(np.median(intervalos)) if len(intervalos) else float("nan"),
            "lançados nos últimos 7 dias (fração)": float((grupo["dias_no_ar"] <= 7).mean()),
            "índice de dispersão": est.indice_de_dispersao(contagens, sob.regressao_antitonica(contagens)),
        }
    return pd.DataFrame(linhas).T


def lancamentos_por_data(anuncios: pd.DataFrame) -> pd.DataFrame:
    """Anúncios ainda no ar por data de início, com a curva decrescente ajustada (ritmo constante)."""
    janela = int(anuncios["dias_no_ar"].max())
    contagens = sob.contagem_por_idade(anuncios["dias_no_ar"].to_numpy(), janela)
    ultima = anuncios["inicio"].max()
    return pd.DataFrame({
        "idade": np.arange(1, janela + 1),
        "data": [(ultima - pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(janela)],
        "anúncios": contagens,
        "ajuste decrescente": sob.regressao_antitonica(contagens),
    })


def _proporcao(anuncios: pd.DataFrame, marca: pd.Series, repeticoes: int, semente: int) -> dict:
    """Proporção com intervalo de 95% reamostrando grupos de criativo."""
    numeros, n_blocos = est.codigos(anuncios["grupo_criativo"])
    sim = est.somas_por_bloco(marca.to_numpy(dtype=float), numeros, n_blocos)
    total = est.somas_por_bloco(np.ones(len(anuncios)), numeros, n_blocos)
    pesos = est.pesos_de_bootstrap(np.random.default_rng(semente), n_blocos, repeticoes)
    inferior, superior = est.intervalo(pesos @ sim / (pesos @ total))
    return {"valor": float(marca.mean()), "inferior": inferior, "superior": superior, "n": int(len(anuncios))}


def estrutura_do_portfolio(anuncios: pd.DataFrame, repeticoes: int = 2000, semente: int = SEMENTE) -> dict:
    """Quantos anúncios por criativo, concentração, formatos e mistura de mensagens, por país."""
    numeros: dict[str, dict] = {}
    proporcoes: dict[str, dict] = {}
    lorenz: dict[str, list] = {}
    for pais, grupo in anuncios.groupby("pais"):
        por_criativo = grupo.groupby("grupo_criativo").size().to_numpy()
        por_texto = grupo.groupby("texto_id").size().to_numpy()
        ordenado = np.sort(por_criativo)[::-1]
        decimo = max(1, int(round(0.1 * len(ordenado))))
        numeros[pais] = {
            "anúncios": len(grupo),
            "criativos distintos": len(por_criativo),
            "anúncios por criativo (média)": float(por_criativo.mean()),
            "anúncios por criativo (máximo)": int(por_criativo.max()),
            "criativos com um anúncio só (fração)": float((por_criativo == 1).mean()),
            "10% dos criativos com mais anúncios (fração dos anúncios)": float(ordenado[:decimo].sum() / len(grupo)),
            "Gini dos anúncios por criativo": est.gini(por_criativo),
            "textos distintos": len(por_texto),
            "anúncios por texto (média)": float(por_texto.mean()),
            "texto mais usado (fração dos anúncios)": float(por_texto.max() / len(grupo)),
            "Gini dos anúncios por texto": est.gini(por_texto),
            "duração do vídeo (mediana, s)": float(grupo["duracao_video_s"].median()),
            "variações por anúncio (média)": float(grupo["variacoes"].mean()),
            "plataformas por anúncio (média)": float(grupo["n_plataformas"].mean()),
        }
        x, y = est.curva_de_lorenz(por_criativo)
        lorenz[pais] = [[float(a), float(b)] for a, b in zip(x, y)]
        classificados = grupo[grupo["tipo_criativo"].notna()]
        marcas = {
            "formato dinâmico (dco)": (grupo, grupo["formato"] == "dco"),
            "formato vídeo único": (grupo, grupo["formato"] == "video"),
            "formato imagem": (grupo, grupo["formato"] == "image"),
            "promete prévia grátis": (grupo, grupo["tem_previa_gratis"]),
            "prova social no texto ou título": (grupo, grupo["tem_prova_social"]),
            "prova social na descrição": (grupo, grupo["descricao_tem_prova_social"]),
            "urgência": (grupo, grupo["tem_urgencia"]),
            "cita ocasião ou data": (grupo, grupo["tem_ocasiao"]),
            "cita Natal": (grupo, grupo["cita_natal"]),
            "cita preço": (grupo, grupo["tem_preco"]),
            "tem pergunta": (grupo, grupo["tem_pergunta"]),
            "gancho de reação emocionada": (grupo, grupo["categoria_gancho"] == "reacao"),
            "gancho de prova social": (grupo, grupo["categoria_gancho"] == "prova_social"),
            "vídeo real (entre os classificados)": (classificados, classificados["tipo_criativo"] == "real"),
            "cena de reação (entre os classificados)": (classificados, classificados["cena"] == "reacao"),
        }
        proporcoes[pais] = {nome: _proporcao(base, marca, repeticoes, semente) for nome, (base, marca) in marcas.items() if len(base)}
        numeros[pais]["idiomas"] = grupo["idioma"].value_counts(normalize=True).round(4).to_dict()
        numeros[pais]["com classificação do vídeo (fração)"] = float(grupo["tipo_criativo"].notna().mean())
    return {"numeros": numeros, "proporcoes": proporcoes, "lorenz": lorenz}


# ---------------------------------------------------------------------------
# 5. Que atributos andam junto com a idade na foto
# ---------------------------------------------------------------------------


def _atributos_binarios(anuncios: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    """Cada atributo como (quem entra na comparação, quem tem o atributo)."""
    todos = pd.Series(True, index=anuncios.index)
    com_video = anuncios["duracao_video_s"].notna()
    com_variacoes = anuncios["variacoes"].notna()
    classificados = anuncios["tipo_criativo"].isin(["real", "ia"])
    com_cena = anuncios["cena"].notna()
    ingles_ou_espanhol = anuncios["idioma"].isin(["en", "es"])
    atributos = {
        "Formato: vídeo único (não dinâmico)": (todos, anuncios["formato"] == "video"),
        "Veicula em 5 ou mais plataformas": (todos, anuncios["n_plataformas"] >= 5),
        "Tem 2 ou mais variações": (com_variacoes, anuncios["variacoes"] >= 2),
        "Vídeo mais longo que a mediana": (com_video, anuncios["duracao_video_s"] > anuncios.loc[com_video, "duracao_video_s"].median()),
        "Vídeo gerado por IA (vs. real)": (classificados, anuncios["tipo_criativo"] == "ia"),
        "Cena de reação (vs. outras cenas)": (com_cena, anuncios["cena"] == "reacao"),
        "Promete prévia grátis": (todos, anuncios["tem_previa_gratis"]),
        "Prova social no texto ou título": (todos, anuncios["tem_prova_social"]),
        "Urgência (tempo limitado)": (todos, anuncios["tem_urgencia"]),
        "Cita ocasião ou data": (todos, anuncios["tem_ocasiao"]),
        "Tem pergunta": (todos, anuncios["tem_pergunta"]),
        "Texto mais longo que a mediana": (todos, anuncios["comprimento_texto"] > anuncios["comprimento_texto"].median()),
        "Mais emojis que a mediana": (todos, anuncios["n_emojis"] > anuncios["n_emojis"].median()),
        "Texto em espanhol (vs. inglês)": (ingles_ou_espanhol, anuncios["idioma"] == "es"),
    }
    for categoria in CATEGORIAS:
        marca = anuncios["categoria_gancho"] == categoria
        if marca.sum() >= 20:
            atributos[f"Gancho: {ROTULOS_DA_CATEGORIA[categoria].lower()}"] = (todos, marca)
    return atributos


def atributos_e_idade(anuncios: pd.DataFrame, repeticoes: int = 4000, semente: int = SEMENTE) -> pd.DataFrame:
    """Diferença de idade média na foto entre anúncios com e sem cada atributo.

    O tamanho do efeito é a diferença em dias, com intervalo de 95% reamostrando grupos de criativo.
    O p-valor é calculado três vezes, embaralhando a idade entre anúncios (a leitura ingênua),
    entre grupos de criativo e entre lotes de lançamento, cada um com ajuste de Benjamini-Hochberg.
    """
    linhas = {}
    for nome, (base, marca) in _atributos_binarios(anuncios).items():
        recorte = anuncios[base]
        x = marca[base].to_numpy(dtype=bool)
        y = recorte["dias_no_ar"].to_numpy(dtype=float)
        if x.sum() < 10 or (~x).sum() < 10:
            continue
        criativos, n_criativos = est.codigos(recorte["grupo_criativo"])
        inferior, superior = est.intervalo_da_diferenca(y, x, criativos, n_criativos, 2000, semente)
        linha = {
            "com o atributo": int(x.sum()),
            "sem o atributo": int((~x).sum()),
            "idade média com": float(y[x].mean()),
            "idade média sem": float(y[~x].mean()),
            "diferença (dias)": est.diferenca_de_medias(y, x),
            "IC 95% inferior": inferior,
            "IC 95% superior": superior,
            "lotes com o atributo": int(recorte.loc[x, "inicio"].nunique()),
        }
        for unidade, rotulo in [("anúncio", "p por anúncio"), ("grupo de criativo", "p por criativo"), ("lote de lançamento", "p por lote")]:
            blocos, n_blocos = est.codigos(_blocos(recorte, unidade))
            linha[rotulo] = est.p_por_permutacao_de_blocos(y, x, blocos, n_blocos, repeticoes, semente)
        linhas[nome] = linha
    tabela = pd.DataFrame(linhas).T
    for rotulo in ["p por anúncio", "p por criativo", "p por lote"]:
        tabela[rotulo.replace("p por", "p ajustado por")] = est.benjamini_hochberg(tabela[rotulo].astype(float))
    return tabela.sort_values("diferença (dias)", ascending=False)


def resumo_dos_atributos(tabela: pd.DataFrame, limiar: float = 0.05) -> dict:
    """Quantos atributos passam no teste em cada nível de rigor."""
    return {
        "atributos testados": int(len(tabela)),
        "significativos por anúncio": int((tabela["p ajustado por anúncio"] < limiar).sum()),
        "significativos por criativo": int((tabela["p ajustado por criativo"] < limiar).sum()),
        "significativos por lote": int((tabela["p ajustado por lote"] < limiar).sum()),
        "menor p ajustado por lote": float(tabela["p ajustado por lote"].min()),
        "que passam por lote": list(tabela.index[tabela["p ajustado por lote"] < limiar]),
    }


# ---------------------------------------------------------------------------
# Um sinal alternativo: o que o anunciante volta a lançar
# ---------------------------------------------------------------------------


def criativos(anuncios: pd.DataFrame) -> pd.DataFrame:
    """Um criativo por linha: quantos anúncios, em quantos lotes apareceu, idade do mais antigo e do mais novo."""
    def moda(serie: pd.Series) -> object:
        validos = serie.dropna()
        return validos.mode().iloc[0] if len(validos) else np.nan

    return anuncios.groupby("grupo_criativo").agg(
        anuncios=("anuncio", "size"),
        lotes=("inicio", "nunique"),
        idade_do_mais_antigo=("dias_no_ar", "max"),
        idade_do_mais_novo=("dias_no_ar", "min"),
        categoria_gancho=("categoria_gancho", moda),
        cena=("cena", moda),
        tipo_criativo=("tipo_criativo", moda),
        duracao_video_s=("duracao_video_s", "median"),
        previa_gratis=("tem_previa_gratis", "mean"),
    )


def relancamento(anuncios: pd.DataFrame, antigo: int = 30, recente: int = 14, repeticoes: int = 500, semente: int = SEMENTE) -> dict:
    """Separa, entre os criativos antigos, os que o anunciante voltou a lançar dos que só ficaram no ar.

    "Antigo" = o anúncio mais velho do criativo tem `antigo` dias ou mais. "Relançado" = o mesmo
    criativo também aparece num anúncio lançado nos últimos `recente` dias: uma decisão ativa e
    recente de usar de novo, que a idade sozinha não distingue da inércia.
    """
    tabela = criativos(anuncios)
    postos_idade = tabela["idade_do_mais_antigo"].rank().to_numpy()
    postos_lotes = tabela["lotes"].rank().to_numpy()
    correlacao = float(np.corrcoef(postos_idade, postos_lotes)[0, 1])
    gerador = np.random.default_rng(semente)
    idade, n_lotes = tabela["idade_do_mais_antigo"].to_numpy(), tabela["lotes"].to_numpy()
    reamostradas = [  # reamostra criativos inteiros
        np.corrcoef(pd.Series(idade[s]).rank(), pd.Series(n_lotes[s]).rank())[0, 1]
        for s in gerador.integers(0, len(tabela), size=(repeticoes, len(tabela)))
    ]
    antigos = tabela[tabela["idade_do_mais_antigo"] >= antigo]
    relancados = antigos[antigos["idade_do_mais_novo"] <= recente]
    parados = antigos[antigos["idade_do_mais_novo"] > recente]

    def perfil(grupo: pd.DataFrame) -> dict:
        return {
            "criativos": int(len(grupo)),
            "anúncios": int(grupo["anuncios"].sum()),
            "lotes (mediana)": float(grupo["lotes"].median()) if len(grupo) else float("nan"),
            "duração do vídeo (mediana, s)": float(grupo["duracao_video_s"].median()) if len(grupo) else float("nan"),
            "categorias do gancho": grupo["categoria_gancho"].value_counts(normalize=True).round(4).to_dict(),
            "cenas (entre os classificados)": grupo["cena"].value_counts(normalize=True).round(4).to_dict(),
            "com classificação": int(grupo["cena"].notna().sum()),
        }

    mais_antigos = tabela.sort_values("idade_do_mais_antigo", ascending=False).head(20)
    return {
        "criativos": int(len(tabela)),
        "por número de lotes": {
            "1 lote": float((tabela["lotes"] == 1).mean()),
            "2 lotes": float((tabela["lotes"] == 2).mean()),
            "3 ou mais lotes": float((tabela["lotes"] >= 3).mean()),
        },
        "correlação de postos entre idade e número de lotes": correlacao,
        "correlação inferior": float(np.quantile(reamostradas, 0.025)),
        "correlação superior": float(np.quantile(reamostradas, 0.975)),
        "limiar de antigo (dias)": antigo,
        "limiar de recente (dias)": recente,
        "antigos": int(len(antigos)),
        "antigos relançados": perfil(relancados),
        "antigos parados": perfil(parados),
        "fração dos antigos que foi relançada": float(len(relancados) / len(antigos)) if len(antigos) else float("nan"),
        "dos 20 mais antigos, relançados recentemente": int((mais_antigos["idade_do_mais_novo"] <= recente).sum()),
        "dos 20 mais antigos, em um lote só": int((mais_antigos["lotes"] == 1).sum()),
    }


# ---------------------------------------------------------------------------
# 6. Ponte para a decisão: a mistura de categorias de gancho no concorrente
# ---------------------------------------------------------------------------


def categorias_de_gancho(anuncios: pd.DataFrame, antigo: int = 30) -> pd.DataFrame:
    """Categoria do gancho no concorrente: o que predomina e o que está entre os anúncios mais antigos."""
    eua = anuncios[anuncios["pais"] == "US"]
    brasil = anuncios[anuncios["pais"] == "BR"]
    linhas = {}
    for categoria in CATEGORIAS:
        linhas[ROTULOS_DA_CATEGORIA[categoria]] = {
            "EUA: fração dos anúncios": float((eua["categoria_gancho"] == categoria).mean()),
            "EUA: fração dos anúncios com 30 dias ou mais": float((eua.loc[eua["dias_no_ar"] >= antigo, "categoria_gancho"] == categoria).mean()),
            "Brasil: fração dos anúncios": float((brasil["categoria_gancho"] == categoria).mean()),        }
    return pd.DataFrame(linhas).T

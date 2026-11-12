"""Atributos derivados do texto de um anúncio, por regras fixas e documentadas.

O texto original do concorrente não é publicado. O que vai para o extrato são estes atributos,
calculados uma vez na extração.

As regras são listas de expressões em português, inglês, espanhol e chinês (os quatro idiomas
que aparecem na coleta). São simples de propósito: dá para ler a lista e discordar dela.
"""

from __future__ import annotations

import re

# Símbolos contados como emoji: pictogramas, símbolos diversos, setas e estrelas.
_EMOJI = re.compile("[\U0001f000-\U0001faff☀-➿⬀-⯿←-⇿⌀-⏿]")

_PRECO = re.compile(r"(r\$|us\$|\$|€)\s?\d|\b\d{1,4},\d{2}\b", re.IGNORECASE)

_PROVA_SOCIAL = re.compile(
    r"\breviews?\b|rese[ñn]a|avalia[çc]|\brating|estrel|\bstars?\b|trustpilot|★|⭐|評價|評分"
    r"|helped (hundreds|thousands)|(hundreds|thousands) of|happy customers|clientes|#1"
    r"|\d[\d.,]*\+|\+\s?\d[\d.,]*",
    re.IGNORECASE,
)

_URGENCIA = re.compile(
    r"limited time|tiempo limitado|tempo limitado|only today|s[óo] hoje|last[- ]minute|hurry"
    r"|ends (soon|today)|限時|[úu]ltimas? (horas?|dias?|vagas?)",
    re.IGNORECASE,
)

_OCASIAO = re.compile(
    r"anniversar|wedding|first dance|mother-son|birthday|christmas|xmas|new year|valentine"
    r"|mother'?s day|father'?s day|baptism|celebration of life|\bguests\b"
    r"|\bnatal\b|navidad|amigo secreto|anivers[áa]rio|casamento|\bbodas?\b|dia das m[ãa]es|dia dos pais"
    r"|dia dos namorados|聖誕|生日",
    re.IGNORECASE,
)

_NATAL = re.compile(r"christmas|xmas|\bnatal\b|navidad|聖誕|\bceia\b|amigo secreto|secret santa", re.IGNORECASE)

_PREVIA = re.compile(
    r"free preview|pr[ée]via gr[áa]tis|previa gratis|muestra gratis|免費試聽|don'?t pay until"
    r"|before you (buy|pay)|antes de (comprar|pagar)",
    re.IGNORECASE,
)

_PERGUNTA = re.compile(r"[?？]")

_CHINES = re.compile("[一-鿿]")
_ESPANHOL = re.compile(r"\b(canci[oó]n|canciones|rese[ñn]as|regalo|estrellas|pod[ií]a|escucha|muestra|horas)\b", re.IGNORECASE)
_PORTUGUES = re.compile(r"\b(voc[êe]|m[úu]sica|presente|pr[ée]via|hist[óo]ria|n[ãa]o|uma|para|seu|sua)\b", re.IGNORECASE)

# Categoria do gancho: a primeira regra que casar com a abertura do texto, nesta ordem.
# A ordem importa e é uma escolha: preço e prova vêm antes porque, quando aparecem na abertura,
# são o argumento; "troca de presente" vem antes de "ocasião" porque a comparação é o gancho
# e a ocasião é só o contexto.
REGRAS_DO_GANCHO: list[tuple[str, re.Pattern[str]]] = [
    ("preco", _PRECO),
    (
        "prova_social",
        re.compile(
            r"\breviews?\b|rese[ñn]a|avalia[çc]|\brating|estrel|\bstars?\b|trustpilot|★|⭐|評價"
            r"|helped (hundreds|thousands)|(hundreds|thousands) of|happy customers",
            re.IGNORECASE,
        ),
    ),
    (
        "reacao",
        re.compile(
            r"cried|\bcry\b|crying|tears|couldn'?t believe|could not believe|chor[aoe]|n[ãa]o acreditou"
            r"|no pod[ií]a creer|surpreendid|\bsurprised\b|感動|哭|反應|emocion|rea[çc][ãa]o|\bcara del[ae]\b",
            re.IGNORECASE,
        ),
    ),
    (
        "troca_de_presente",
        re.compile(
            r"skip the|forget (the )?flowers|flowers fade|roses die|predictable|doesn'?t need another"
            r"|hard to shop|wants nothing|em vez de (flores|perfume|outro presente)",
            re.IGNORECASE,
        ),
    ),
    (
        "nicho",
        re.compile(r"christian|worship|country|bestie|\bfriend\b|praying|pastor|gospel|sertanejo", re.IGNORECASE),
    ),
    ("ocasiao", _OCASIAO),
    (
        "oferta_objecao",
        re.compile(
            r"free preview|before you pay|don'?t pay|haven'?t heard|you don'?t need to|pr[ée]via|antes de pagar"
            r"|\bmedo\b|\bd[úu]vidas?\b|perguntas? frequentes?|muestra gratis|試聽",
            re.IGNORECASE,
        ),
    ),
]
CATEGORIA_PADRAO = "promessa_curiosidade"
CATEGORIAS = [nome for nome, _ in REGRAS_DO_GANCHO] + [CATEGORIA_PADRAO]

ROTULOS_DA_CATEGORIA = {
    "preco": "Preço",
    "prova_social": "Prova social",
    "reacao": "Reação emocionada",
    "troca_de_presente": "Troca de presente",
    "nicho": "Nicho (fé, country, amizade)",
    "ocasiao": "Ocasião ou data",
    "oferta_objecao": "Oferta ou objeção",
    "promessa_curiosidade": "Promessa ou curiosidade",
}

_FIM_DE_FRASE = re.compile(r"(?<=[.!?…。！？])\s+|\n+")


def abertura(texto: str, minimo: int = 40, maximo: int = 160) -> str:
    """O gancho do texto: as primeiras frases, até somar `minimo` caracteres (teto em `maximo`).

    Uma frase curta demais ("Flores murcham.") não diz qual é o gancho; por isso junta a seguinte.
    """
    frases = [f.strip() for f in _FIM_DE_FRASE.split(texto.strip()) if f.strip()]
    junto = ""
    for frase in frases:
        junto = f"{junto} {frase}".strip()
        if len(junto) >= minimo:
            break
    return junto[:maximo]


def categoria_do_gancho(texto: str) -> str:
    """Categoria da abertura do texto, pela primeira regra que casar."""
    inicio = abertura(texto)
    for nome, regra in REGRAS_DO_GANCHO:
        if regra.search(inicio):
            return nome
    return CATEGORIA_PADRAO


def idioma(texto: str) -> str:
    """Idioma do texto: zh, es, pt ou en, por caracteres e palavras marcadoras."""
    if _CHINES.search(texto):
        return "zh"
    if _ESPANHOL.search(texto):
        return "es"
    if _PORTUGUES.search(texto):
        return "pt"
    return "en"


def contar_emojis(texto: str) -> int:
    return len(_EMOJI.findall(texto))


def atributos(texto: str, titulo: str = "") -> dict[str, object]:
    """Atributos de um anúncio a partir do texto principal e do título.

    Comprimento, emojis e categoria do gancho usam só o texto principal. As presenças (preço,
    prova social, urgência, ocasião, pergunta, prévia grátis) olham texto e título juntos,
    porque os dois são escritos pelo anunciante e lidos em sequência.
    """
    copia = f"{texto}\n{titulo}"
    return {
        "idioma": idioma(texto),
        "comprimento_texto": len(texto),
        "n_emojis": contar_emojis(texto),
        "tem_preco": bool(_PRECO.search(copia)),
        "tem_prova_social": bool(_PROVA_SOCIAL.search(copia)),
        "tem_urgencia": bool(_URGENCIA.search(copia)),
        "tem_ocasiao": bool(_OCASIAO.search(copia)),
        "cita_natal": bool(_NATAL.search(copia)),
        "tem_pergunta": bool(_PERGUNTA.search(copia)),
        "tem_previa_gratis": bool(_PREVIA.search(copia)),
        "categoria_gancho": categoria_do_gancho(texto),
    }


def tem_prova_social(texto: str) -> bool:
    return bool(_PROVA_SOCIAL.search(texto))

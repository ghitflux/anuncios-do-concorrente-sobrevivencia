import pytest

from anuncios_concorrente import texto

# Exemplos inventados para o teste (nenhum é texto de anúncio real).
EXEMPLOS = [
    ("Minha avó escutou a faixa no almoço de domingo e chorou na frente de todo mundo 😭", "reacao"),
    ("Grandpa could not believe his own nickname was in the chorus 😭", "reacao"),
    ("⭐ Mais de 10.000 avaliações\n🎵 Entrega em horas", "prova_social"),
    ("Thousands of families have already wrapped a tune like this one for the holidays.", "prova_social"),
    ("Skip the usual bouquet. This time, hand her something she can listen to.", "troca_de_presente"),
    ("Skip the usual bouquet this anniversary and hand her something she can listen to.", "troca_de_presente"),  # a troca vem antes da ocasião
    ("Planning your wedding? Walk down the aisle to a track nobody else has.", "ocasiao"),
    ("O Natal está chegando e a lista de presentes continua em branco.", "ocasiao"),
    ("Does he live for country music? Turn his life into a track in that style.", "nicho"),
    ("Ficou com dúvida se vai gostar? Dá para escutar um trecho antes de pagar.", "oferta_objecao"),
    ("Custa menos que um jantar fora: € 19, sem assinatura.", "preco"),
    ("Algumas ideias simplesmente ficam melhores quando viram canção.", "promessa_curiosidade"),
]


@pytest.mark.parametrize("frase, categoria", EXEMPLOS)
def test_categoria_do_gancho(frase, categoria):
    assert texto.categoria_do_gancho(frase) == categoria


def test_toda_categoria_tem_rotulo_e_a_lista_e_fechada():
    assert set(texto.CATEGORIAS) == set(texto.ROTULOS_DA_CATEGORIA)
    assert all(texto.categoria_do_gancho(frase) in texto.CATEGORIAS for frase, _ in EXEMPLOS)


def test_previa_nao_conta_como_avaliacao():
    # "preview" contém "review": a regra de prova social precisa de palavra inteira.
    atributos = texto.atributos("Picture a brand-new tune written around her name. Listen to a free preview first 🎁")
    assert atributos["tem_previa_gratis"] is True
    assert atributos["tem_prova_social"] is False
    assert atributos["categoria_gancho"] == "promessa_curiosidade"


def test_abertura_junta_frases_curtas_e_respeita_o_teto():
    assert texto.abertura("Chove. Venta. Depois o tempo abre de vez. E a tarde segue.") == "Chove. Venta. Depois o tempo abre de vez."
    assert len(texto.abertura("a" * 500)) == 160
    assert texto.abertura("Primeira linha bem comprida, com mais de quarenta caracteres.\nSegunda linha.") == "Primeira linha bem comprida, com mais de quarenta caracteres."


def test_atributos_de_presenca_olham_texto_e_titulo():
    atributos = texto.atributos("Uma canção só para ela ❤️🎁", "Só por tempo limitado: prévia grátis antes de comprar")
    assert atributos["tem_urgencia"] and atributos["tem_previa_gratis"]
    assert not atributos["tem_preco"] and not atributos["tem_pergunta"] and not atributos["tem_ocasiao"]
    assert atributos["n_emojis"] == 2
    assert atributos["comprimento_texto"] == len("Uma canção só para ela ❤️🎁")


def test_natal_preco_e_pergunta():
    atributos = texto.atributos("A ceia é sábado e falta um presente? Só hoje, por € 19.")
    assert atributos["cita_natal"] and atributos["tem_preco"] and atributos["tem_pergunta"] and atributos["tem_urgencia"]


@pytest.mark.parametrize(
    "frase, esperado",
    [
        ("Uma lembrança boa para guardar", "pt"),
        ("The whole family sang along at dinner", "en"),
        ("Nunca pensé que una canción pudiera llevar su nombre", "es"),
        ("這首歌是送給媽媽的禮物", "zh"),
    ],
)
def test_idioma(frase, esperado):
    assert texto.idioma(frase) == esperado

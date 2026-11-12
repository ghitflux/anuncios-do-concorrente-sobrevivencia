"""Guarda de publicação: o repositório é público e o produto ainda não foi lançado.

Varre todos os arquivos do projeto (menos ambiente e caches) e falha se aparecer o que não pode ir
a público: valor em reais, nome de pasta de criativo, citação de regra ou documento interno do plano
de lançamento, e qualquer contagem ou menção aos criativos do próprio produto.
"""

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
IGNORAR = {".venv", ".git", "__pycache__", ".pytest_cache", ".ipynb_checkpoints"}
ESTE_ARQUIVO = Path(__file__).resolve()

VALOR_EM_REAIS = re.compile(r"R\$\s?\d", re.IGNORECASE)
PASTA_DE_CRIATIVO = re.compile(r"(?<![\w-])\d{2}-[a-z]{3,}(?:-[a-z]{2,})+(?![\w-])")  # dois dígitos e palavras com hífen

# Termos que só aparecem quando se cita regra, premissa ou documento interno do plano.
TERMOS_DO_PLANO = re.compile(
    r"plano de lan[çc]amento|plano-marketing|plano-lancamento|se[çc][ãa]o \d+\.\d+"
    r"|regras? de (corte|escala|verba)|\bcac\b|\broas\b|faturamento|\bmargem\b"
    r"|primeira onda|\bonda \d|ondas de (teste|criativo)"
    r"|depoimento (inventado|fabricado)|banco de ganchos|grade de criativos|utm_"
    r"|modelad[oa]s? na estrutura|refer[êe]ncias? do plano|plano de criativos"
    r"|\bo plano (aposta|pro[íi]be|cobre|n[ãa]o cobre|tem|dizia|escolheu|[ée]) ",
    re.IGNORECASE,
)

# Menção aos criativos do próprio produto ou contagem deles (o padrão é montado em pedaços para
# que este arquivo não contenha, ele mesmo, os termos que procura).
CRIATIVOS_DO_PRODUTO = re.compile("planej" + "ad" + r"|\bde 1" + r"2(?![,.\d])", re.IGNORECASE)


def _arquivos() -> list[Path]:
    return [p for p in sorted(RAIZ.rglob("*")) if p.is_file() and not (set(p.relative_to(RAIZ).parts) & IGNORAR)]


def _texto(caminho: Path) -> str:
    dados = caminho.read_bytes()
    return dados.decode("latin-1") if caminho.suffix.lower() == ".png" else dados.decode("utf-8", errors="ignore")


def _trecho(texto: str, achado: re.Match) -> str:
    return texto[max(0, achado.start() - 40) : achado.end() + 40].replace("\n", " ")


def test_nenhum_valor_em_reais_em_arquivo_do_projeto():
    achados = [(str(p.relative_to(RAIZ)), _trecho(t, m)) for p in _arquivos() for t in [_texto(p)] for m in VALOR_EM_REAIS.finditer(t)]
    assert not achados, achados[:5]


def test_nenhum_nome_de_pasta_de_criativo_em_arquivo_do_projeto():
    achados = [
        (str(p.relative_to(RAIZ)), m.group(0))
        for p in _arquivos()
        if p.name != "uv.lock" and p.suffix.lower() != ".png"
        for m in PASTA_DE_CRIATIVO.finditer(_texto(p))
    ]
    assert not achados, achados[:5]


def test_nenhuma_citacao_de_regra_ou_documento_do_plano():
    achados = [
        (str(p.relative_to(RAIZ)), _trecho(t, m))
        for p in _arquivos()
        if p.resolve() != ESTE_ARQUIVO and p.name != "uv.lock" and p.suffix.lower() != ".png"
        for t in [_texto(p)]
        for m in TERMOS_DO_PLANO.finditer(t)
    ]
    assert not achados, achados[:5]


def test_nenhuma_mencao_ou_contagem_dos_criativos_do_produto():
    achados = [
        (str(p.relative_to(RAIZ)), _trecho(t, m))
        for p in _arquivos()
        if p.name != "uv.lock" and p.suffix.lower() != ".png"
        for t in [_texto(p)]
        for m in CRIATIVOS_DO_PRODUTO.finditer(t)
    ]
    assert not achados, achados[:5]


def test_resultados_so_trazem_o_concorrente():
    resultados = json.loads((RAIZ / "reports" / "resultados.json").read_text(encoding="utf-8"))
    assert not [chave for chave in resultados if "plano" in chave or "dedico" in chave]
    tabela = resultados["categorias_de_gancho"]
    assert all(set(linha) == {"EUA: fração dos anúncios", "EUA: fração dos anúncios com 30 dias ou mais", "Brasil: fração dos anúncios"} for linha in tabela.values())
    site = json.dumps(resultados["para_o_site"], ensure_ascii=False)
    assert not VALOR_EM_REAIS.search(site) and not TERMOS_DO_PLANO.search(site)

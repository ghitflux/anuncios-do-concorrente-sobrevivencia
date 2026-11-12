"""Gera o extrato anonimizado em data/ a partir da coleta original da biblioteca de anúncios.

Uso (só para quem tem a pasta privada da coleta):

    uv run python scripts/extrair_dados.py PASTA_DA_COLETA

A pasta da coleta tem um `dados-<PAÍS>.json` por país, `classificacao.json` e `grupos.json`.
Grava `anuncios.csv` e `coleta.json`.

O que NÃO sai daqui: nome do anunciante, nomes de página, domínios, links, ids da biblioteca,
textos dos anúncios, nomes de arquivo e mídia. Os ids são embaralhados com um sal aleatório que
não é gravado em lugar nenhum; rodar de novo gera outros ids. No fim, o script confere que nenhum
desses valores originais aparece nos arquivos gravados e falha se aparecer.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import secrets
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from anuncios_concorrente import texto as regras

COLUNAS = [
    "anuncio", "pais", "pagina", "inicio", "dias_no_ar", "dias_desde_ultimo_registro", "formato",
    "n_plataformas", "variacoes", "tem_video", "duracao_video_s", "grupo_criativo", "tipo_criativo", "cena",
    "texto_id", "idioma", "comprimento_texto", "n_emojis", "tem_preco", "tem_prova_social", "tem_urgencia",
    "tem_ocasiao", "cita_natal", "tem_pergunta", "tem_previa_gratis", "descricao_tem_prova_social",
    "categoria_gancho",
]


class Uniao:
    """Conjuntos disjuntos: junta anúncios que compartilham algum vídeo repetido."""

    def __init__(self) -> None:
        self.pai: dict[object, object] = {}

    def achar(self, x: object) -> object:
        self.pai.setdefault(x, x)
        while self.pai[x] != x:
            self.pai[x] = self.pai[self.pai[x]]
            x = self.pai[x]
        return x

    def unir(self, a: object, b: object) -> None:
        ra, rb = self.achar(a), self.achar(b)
        if ra != rb:
            self.pai[ra] = rb


def _ler(caminho: Path) -> object:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _rotulos(chaves: list[object], sal: str, prefixo: str, largura: int) -> dict[object, str]:
    """Rótulo sequencial para cada chave, na ordem de um hash com sal (a ordem original se perde)."""
    ordenadas = sorted(set(chaves), key=lambda c: hashlib.sha256(f"{sal}|{c!r}".encode()).hexdigest())
    return {chave: f"{prefixo}{i + 1:0{largura}d}" for i, chave in enumerate(ordenadas)}


def _classificacao_do_anuncio(arquivos: list[str], mapa: dict[str, str], classificacao: dict[str, dict]) -> tuple[str, str]:
    """Tipo (real, ia, misto, indeterminado) e cena do anúncio, a partir dos seus vídeos classificados."""
    achados = [classificacao[mapa[a]] for a in arquivos if mapa.get(a) in classificacao]
    if not achados:
        return "", ""
    tipos = {c["tipo"] for c in achados}
    cenas = [c["cena"] for c in achados if c["cena"] != "outro"] or ["outro"]
    return (tipos.pop() if len(tipos) == 1 else "misto"), Counter(cenas).most_common(1)[0][0]


def extrair_anuncios(origem: Path, sal: str) -> tuple[list[dict], dict, list[str]]:
    classificacao = _ler(origem / "classificacao.json")
    grupos = _ler(origem / "grupos.json")
    mapa: dict[str, str] = grupos["mapa"]
    duracao = {g["fica"]: g.get("duracao") for g in grupos["grupos"]}

    brutos: list[tuple[str, dict]] = []
    resumo: dict[str, dict] = {}
    data_da_coleta = ""
    for arquivo in sorted(origem.glob("dados-*.json")):
        pais = arquivo.stem.split("-")[-1].upper()
        conteudo = _ler(arquivo)
        data_da_coleta = max(data_da_coleta, conteudo["coletadoEm"][:10])
        resumo[pais] = {"anuncios": len(conteudo["anuncios"]), "total_informado_pela_busca": conteudo.get("totalNaBusca")}
        brutos += [(pais, a) for a in conteudo["anuncios"]]

    # Grupo de criativo: componente conexo dos anúncios que compartilham algum vídeo repetido.
    # Anúncio sem vídeo (imagem) não tem impressão digital de mídia: agrupa pelo texto e título idênticos.
    uniao = Uniao()
    for pais, a in brutos:
        no = ("anuncio", a["id"])
        uniao.achar(no)
        if a["arquivos"]:
            for arq in a["arquivos"]:
                uniao.unir(no, ("video", mapa[arq]))
        else:
            uniao.unir(no, ("copia", pais, a["texto"], a["titulo"]))

    rotulo_anuncio = _rotulos([a["id"] for _, a in brutos], sal, "a", 4)
    rotulo_grupo = _rotulos([uniao.achar(("anuncio", a["id"])) for _, a in brutos], sal, "g", 4)
    rotulo_texto = _rotulos([a["texto"] for _, a in brutos], sal, "t", 2)
    paginas: dict[str, Counter] = defaultdict(Counter)
    for pais, a in brutos:
        paginas[pais][a["pagina"]] += 1
    rotulo_pagina = {
        (pais, nome): f"{pais}-{i + 1}" for pais, contagem in paginas.items() for i, (nome, _) in enumerate(contagem.most_common())
    }

    coleta = date.fromisoformat(data_da_coleta)
    linhas = []
    for pais, a in brutos:
        tipo, cena = _classificacao_do_anuncio(a["arquivos"], mapa, classificacao)
        duracoes = [duracao[mapa[arq]] for arq in a["arquivos"] if duracao.get(mapa[arq])]
        linha = {
            "anuncio": rotulo_anuncio[a["id"]],
            "pais": pais,
            "pagina": rotulo_pagina[(pais, a["pagina"])],
            "inicio": a["inicio"],
            "dias_no_ar": int(a["diasNoAr"]),
            "dias_desde_ultimo_registro": (coleta - date.fromisoformat(a["fim"])).days,
            "formato": a["formato"],
            "n_plataformas": len(a["plataformas"]),
            "variacoes": "" if a["variacoes"] is None else int(a["variacoes"]),
            "tem_video": int(bool(a["arquivos"])),
            "duracao_video_s": max(duracoes) if duracoes else "",
            "grupo_criativo": rotulo_grupo[uniao.achar(("anuncio", a["id"]))],
            "tipo_criativo": tipo,
            "cena": cena,
            "texto_id": rotulo_texto[a["texto"]],
            "descricao_tem_prova_social": int(regras.tem_prova_social(a.get("descricao") or "")),
        }
        derivados = regras.atributos(a["texto"], a.get("titulo") or "")
        linha.update({k: (int(v) if isinstance(v, bool) else v) for k, v in derivados.items()})
        linhas.append(linha)
    linhas.sort(key=lambda linha: linha["anuncio"])

    classificados = sum(1 for linha in linhas if linha["tipo_criativo"])
    metadados = {
        "data_da_coleta": data_da_coleta,
        "o_que_e": "anúncios ativos de um anunciante na biblioteca de anúncios da Meta, numa única data",
        "paises": resumo,
        "anuncios": len(linhas),
        "grupos_de_criativo": len({linha["grupo_criativo"] for linha in linhas}),
        "textos_distintos": len({linha["texto_id"] for linha in linhas}),
        "anuncios_com_classificacao_do_video": classificados,
        "limiar_do_agrupamento_de_videos": grupos.get("limiar"),
    }

    # Valores originais que não podem aparecer em nenhum arquivo gravado.
    proibidos = {a["id"] for _, a in brutos} | {a["pagina"] for _, a in brutos}
    for _, a in brutos:
        proibidos |= {a.get("dominio") or "", a.get("destino") or "", a.get("biblioteca") or "", a.get("titulo") or ""}
        proibidos |= set(a["arquivos"])
        if len(a["texto"]) >= 20:
            proibidos.add(a["texto"])
    proibidos |= {re.sub(r"^www\.", "", re.sub(r"/.*$", "", re.sub(r"^https?://", "", a.get("destino") or ""))) for _, a in brutos}
    return linhas, metadados, sorted(p for p in proibidos if len(p) >= 6)


def _gravar(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    argumentos = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    argumentos.add_argument("coleta", type=Path, help="pasta da coleta original (privada)")
    argumentos.add_argument("--saida", type=Path, default=Path("data"))
    opcoes = argumentos.parse_args()
    opcoes.saida.mkdir(parents=True, exist_ok=True)

    sal = secrets.token_hex(16)  # nunca gravado
    linhas, metadados, proibidos = extrair_anuncios(opcoes.coleta, sal)
    gravados = [opcoes.saida / "anuncios.csv", opcoes.saida / "coleta.json"]
    _gravar(gravados[0], COLUNAS, linhas)
    gravados[1].write_text(json.dumps(metadados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    # Conferência: nenhum valor original do concorrente pode ter ido parar nos arquivos gravados.
    for caminho in gravados:
        conteudo = caminho.read_text(encoding="utf-8").lower()
        vazados = [p for p in proibidos if p.lower() in conteudo]
        if vazados:
            for outro in gravados:
                outro.unlink(missing_ok=True)
            raise SystemExit(f"Anonimização falhou: {len(vazados)} valores originais apareceram em {caminho.name}. Nada foi gravado.")
    print(f"{len(linhas)} anúncios, {metadados['grupos_de_criativo']} grupos de criativo, {metadados['textos_distintos']} textos distintos.")
    print(f"Classificação do vídeo em {metadados['anuncios_com_classificacao_do_video']} anúncios.")
    print(f"Conferência de anonimização: {len(proibidos)} valores originais procurados, nenhum encontrado.")
    print("Gravado:", ", ".join(str(c) for c in gravados))


if __name__ == "__main__":
    main()

"""Leitura do extrato anonimizado em data/ (o estudo roda só com ele, sem os arquivos originais)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PASTA = Path("data")

BOOLEANAS = [
    "tem_video", "tem_preco", "tem_prova_social", "tem_urgencia", "tem_ocasiao", "cita_natal", "tem_pergunta",
    "tem_previa_gratis", "descricao_tem_prova_social",
]


def carregar_anuncios(pasta: Path = PASTA) -> pd.DataFrame:
    """Um anúncio por linha: a foto dos anúncios ativos do concorrente na data da coleta."""
    anuncios = pd.read_csv(pasta / "anuncios.csv", parse_dates=["inicio"])
    for coluna in BOOLEANAS:
        anuncios[coluna] = anuncios[coluna].astype(bool)
    return anuncios


def carregar_coleta(pasta: Path = PASTA) -> dict:
    return json.loads((pasta / "coleta.json").read_text(encoding="utf-8"))


def do_pais(anuncios: pd.DataFrame, pais: str) -> pd.DataFrame:
    return anuncios[anuncios["pais"] == pais].reset_index(drop=True)

"""Funções e constantes compartilhadas pelos scripts de tratamento de dados."""
import re
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PASTA_RAW = RAIZ / "data" / "raw"
PASTA_PROCESSED = RAIZ / "data" / "processed"

# código IBGE da UF -> (nome, sigla)
UFS = {
    "11": ("Rondônia", "RO"), "12": ("Acre", "AC"), "13": ("Amazonas", "AM"),
    "14": ("Roraima", "RR"), "15": ("Pará", "PA"), "16": ("Amapá", "AP"),
    "17": ("Tocantins", "TO"), "21": ("Maranhão", "MA"), "22": ("Piauí", "PI"),
    "23": ("Ceará", "CE"), "24": ("Rio Grande do Norte", "RN"),
    "25": ("Paraíba", "PB"), "26": ("Pernambuco", "PE"), "27": ("Alagoas", "AL"),
    "28": ("Sergipe", "SE"), "29": ("Bahia", "BA"), "31": ("Minas Gerais", "MG"),
    "32": ("Espírito Santo", "ES"), "33": ("Rio de Janeiro", "RJ"),
    "35": ("São Paulo", "SP"), "41": ("Paraná", "PR"),
    "42": ("Santa Catarina", "SC"), "43": ("Rio Grande do Sul", "RS"),
    "50": ("Mato Grosso do Sul", "MS"), "51": ("Mato Grosso", "MT"),
    "52": ("Goiás", "GO"), "53": ("Distrito Federal", "DF"),
}

MESES = {
    "Jan": "01", "Fev": "02", "Mar": "03", "Abr": "04",
    "Mai": "05", "Jun": "06", "Jul": "07", "Ago": "08",
    "Set": "09", "Out": "10", "Nov": "11", "Dez": "12",
}

_PADRAO_COLUNA_MES = re.compile(r"^\d{4}/(" + "|".join(MESES) + r")$")


def ler_csv(caminho):
    """Lê o CSV como texto, tentando UTF-8 e depois latin1."""
    for encoding in ("utf-8-sig", "latin1"):
        try:
            return pd.read_csv(caminho, sep=";", dtype=str, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não foi possível decodificar {caminho}")


def corrigir_mojibake(texto):
    """Repara texto UTF-8 lido como latin1 (ex.: 'RondÃ´nia' -> 'Rondônia')."""
    if pd.isna(texto) or not re.search(r"[ÃÂ]", texto):
        return texto
    try:
        return texto.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def limpar_texto(texto):
    """Remove espaços nas pontas e espaços repetidos; repara mojibake."""
    if pd.isna(texto):
        return texto
    return re.sub(r"\s+", " ", corrigir_mojibake(str(texto))).strip()


def colunas_mensais(df):
    """Colunas no formato 'AAAA/Mes'; ignora identificadores e 'Total'."""
    return [c for c in df.columns if _PADRAO_COLUNA_MES.match(c)]


def converter_valores(df, colunas):
    """Troca '-' e vazios por 0 e converte para inteiro. Retorna (df, qtd_trocas)."""
    bloco = df[colunas].apply(lambda s: s.str.strip())
    trocas = int(bloco.isin(["-", ""]).sum().sum() + bloco.isna().sum().sum())
    bloco = bloco.replace({"-": "0", "": "0"}).fillna("0")
    df = df.copy()
    df[colunas] = bloco.astype("int64")
    return df, trocas


def para_formato_longo(df, id_vars, colunas):
    """Converte colunas mensais em linhas e cria a coluna datetime 'data'."""
    longo = df.melt(id_vars=id_vars, value_vars=colunas,
                    var_name="data", value_name="valor")
    ano_mes = longo["data"].str.split("/")
    longo["data"] = pd.to_datetime(
        ano_mes.str[0] + "-" + ano_mes.str[1].map(MESES) + "-01"
    )
    return longo


def salvar_processado(df, nome_arquivo):
    PASTA_PROCESSED.mkdir(parents=True, exist_ok=True)
    destino = PASTA_PROCESSED / nome_arquivo
    df.to_csv(destino, index=False, encoding="utf-8")
    return destino

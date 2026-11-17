"""Download, extração e agregação mensal por UF dos dados meteorológicos do INMET.

Fontes oficiais anuais:
    https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip

O script baixa cada arquivo anual em memória/stream, extrai as séries horárias das
estações meteorológicas, calcula as métricas climáticas agregadas por dia e por mês,
e consolida a base por UF em:
    data/processed/inmet_uf_mensal.csv

Uso:
    venv/bin/python src/tratamento_dados/tratar_inmet.py --piloto        # Processa apenas 2024
    venv/bin/python src/tratamento_dados/tratar_inmet.py --ano 2024      # Processa ano específico
    venv/bin/python src/tratamento_dados/tratar_inmet.py                 # Processa 2008 a 2026
"""
import argparse
import io
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

DIRETORIO_PROJETO = Path(__file__).resolve().parents[2]
CSV_SAIDA = DIRETORIO_PROJETO / "data" / "processed" / "inmet_uf_mensal.csv"
URL_BASE_INMET = "https://portal.inmet.gov.br/uploads/dadoshistoricos"

SIGLA_PARA_CODIGO_UF = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41,
    "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}

PADROES_COLUNAS = {
    "data": re.compile(r"^data", re.IGNORECASE),
    "precipitacao": re.compile(r"precipita[cç][aã]o.*total", re.IGNORECASE),
    "temp_ar": re.compile(r"temperatura.*bulbo|temperatura.*ar.*hor[aá]ria", re.IGNORECASE),
    "temp_max": re.compile(r"temperatura.*m[aá]xima", re.IGNORECASE),
    "temp_min": re.compile(r"temperatura.*m[ií]nima", re.IGNORECASE),
    "umidade": re.compile(r"umidade.*relativa.*ar.*hor[aá]ria|umidade.*relativa.*\(%\)", re.IGNORECASE),
    "umidade_min": re.compile(r"umidade.*rel.*m[ií]n", re.IGNORECASE),
}

REGEX_NOME_ARQUIVO_UF = re.compile(r"INMET_[A-Z]+_([A-Z]{2})_[A-Z0-9]+_", re.IGNORECASE)
REGEX_METADADO_UF = re.compile(r"^UF:\s*;?\s*([A-Z]{2})", re.IGNORECASE)


def _identificar_colunas(nomes_colunas):
    """Mapeia os nomes brutos das colunas do INMET para as variáveis padronizadas."""
    mapeamento = {}
    for col in nomes_colunas:
        col_limpa = col.strip()
        for chave, padrao in PADROES_COLUNAS.items():
            if chave not in mapeamento and padrao.search(col_limpa):
                mapeamento[chave] = col
                break
    return mapeamento


def baixar_zip_ano(ano, timeout=180):
    """Baixa o arquivo compactado de um ano do INMET retornando um BytesIO."""
    url = f"{URL_BASE_INMET}/{ano}.zip"
    print(f"[{ano}] Baixando {url} ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            conteudo = resp.read()
        print(f"[{ano}] Download concluído ({len(conteudo) / (1024 * 1024):.1f} MB).", flush=True)
        return io.BytesIO(conteudo)
    except Exception as e:
        print(f"[{ano}] Erro ao baixar: {e}", file=sys.stderr)
        return None


def processar_csv_estacao(conteudo_csv, uf_sigla=None):
    """Processa um CSV de estação horária e agrega diária e mensalmente."""
    try:
        linhas = conteudo_csv.decode("latin-1").splitlines()
    except Exception:
        return None

    if len(linhas) < 20:
        return None

    # Se a UF não veio pelo nome do arquivo, extrai do cabeçalho de metadados
    if not uf_sigla:
        for idx in range(min(10, len(linhas))):
            m = REGEX_METADADO_UF.search(linhas[idx].strip())
            if m:
                uf_sigla = m.group(1).upper()
                break

    if not uf_sigla or uf_sigla not in SIGLA_PARA_CODIGO_UF:
        return None

    # O cabeçalho dos dados contém "data" e "hora" separados por ponto e vírgula
    linha_cabecalho = -1
    for idx in range(min(15, len(linhas))):
        linha = linhas[idx].lower()
        if "data" in linha and "hora" in linha and ";" in linha:
            linha_cabecalho = idx
            break

    if linha_cabecalho == -1:
        return None

    texto_tabela = "\n".join(linhas[linha_cabecalho:])
    try:
        df = pd.read_csv(
            io.StringIO(texto_tabela),
            sep=";",
            decimal=",",
            low_memory=False,
            na_values=["-9999", "-9999.0", "", "nan", "NaN"]
        )
    except Exception:
        return None

    col_map = _identificar_colunas(df.columns)
    if "data" not in col_map or "temp_ar" not in col_map:
        return None

    col_data = col_map["data"]
    df["data_dt"] = pd.to_datetime(df[col_data].astype(str).str.replace("/", "-"), errors="coerce")
    df = df.dropna(subset=["data_dt"])
    if df.empty:
        return None

    # Mapear e converter colunas numéricas
    for k in ["temp_ar", "temp_max", "temp_min", "umidade", "umidade_min", "precipitacao"]:
        if k in col_map and col_map[k] in df.columns:
            nome_real = col_map[k]
            df[k] = pd.to_numeric(df[nome_real], errors="coerce")
        else:
            df[k] = np.nan

    # Limpeza de ruídos de sensor / limites físicos
    df.loc[(df["temp_ar"] < -15) | (df["temp_ar"] > 55), "temp_ar"] = np.nan
    df.loc[(df["temp_max"] < -15) | (df["temp_max"] > 55), "temp_max"] = np.nan
    df.loc[(df["temp_min"] < -15) | (df["temp_min"] > 55), "temp_min"] = np.nan
    df.loc[(df["umidade"] < 0) | (df["umidade"] > 100), "umidade"] = np.nan
    df.loc[(df["umidade_min"] < 0) | (df["umidade_min"] > 100), "umidade_min"] = np.nan
    df.loc[df["precipitacao"] < 0, "precipitacao"] = np.nan

    # Se temp_min / temp_max horárias estiverem ausentes, usar temp_ar
    t_min_col = "temp_min" if df["temp_min"].notna().sum() > 50 else "temp_ar"
    t_max_col = "temp_max" if df["temp_max"].notna().sum() > 50 else "temp_ar"
    u_min_col = "umidade_min" if df["umidade_min"].notna().sum() > 50 else "umidade"

    df["dia"] = df["data_dt"].dt.date
    df["mes_ano"] = df["data_dt"].dt.to_period("M").dt.to_timestamp()

    # 1º Passo: Agregação diária por estação
    diario = df.groupby(["mes_ano", "dia"]).agg(
        t_media=("temp_ar", "mean"),
        t_min=(t_min_col, "min"),
        t_max=(t_max_col, "max"),
        u_media=("umidade", "mean"),
        u_min=(u_min_col, "min"),
        precip=("precipitacao", "sum"),
        horas=("temp_ar", "count")
    ).reset_index()

    # Considerar dias com pelo menos 12 horas válidas
    diario = diario[diario["horas"] >= 12]
    if diario.empty:
        return None

    # 2º Passo: Agregação mensal da estação
    mensal = diario.groupby("mes_ano").agg(
        temp_media=("t_media", "mean"),
        temp_min_media=("t_min", "mean"),
        temp_min_abs=("t_min", "min"),
        temp_max_media=("t_max", "mean"),
        umidade_media=("u_media", "mean"),
        umidade_min_media=("u_min", "mean"),
        precipitacao_total=("precip", "sum"),
        dias_validos=("dia", "count")
    ).reset_index()

    # Exigir pelo menos 15 dias válidos no mês
    mensal = mensal[mensal["dias_validos"] >= 15].copy()
    if mensal.empty:
        return None

    mensal["uf"] = uf_sigla
    return mensal.drop(columns=["dias_validos"])


def processar_zip_ano(buffer_zip, ano):
    """Lê todas as estações contidas no ZIP de um ano e consolida por UF."""
    with zipfile.ZipFile(buffer_zip) as zf:
        lista_arquivos = [f for f in zf.namelist() if f.upper().endswith(".CSV")]
        print(f"[{ano}] Processando {len(lista_arquivos)} estações...", flush=True)

        dfs_estacoes = []
        for caminho in lista_arquivos:
            match_uf = REGEX_NOME_ARQUIVO_UF.search(caminho)
            uf = match_uf.group(1).upper() if match_uf else None

            try:
                with zf.open(caminho) as arq_csv:
                    conteudo = arq_csv.read()
                res = processar_csv_estacao(conteudo, uf)
                if res is not None and not res.empty:
                    dfs_estacoes.append(res)
            except Exception:
                continue

    if not dfs_estacoes:
        print(f"[{ano}] Nenhuma estação com dados válidos processada.", file=sys.stderr)
        return None

    todos = pd.concat(dfs_estacoes, ignore_index=True)
    ufs_processadas = todos["uf"].nunique()
    print(f"[{ano}] Dados consolidados de {len(dfs_estacoes)} estações em {ufs_processadas} UFs.")

    # Agregação consolidada por UF e Mês (média das estações operantes do estado)
    uf_mensal = todos.groupby(["uf", "mes_ano"]).agg(
        temp_media=("temp_media", "mean"),
        temp_min_media=("temp_min_media", "mean"),
        temp_min_abs=("temp_min_abs", "min"),
        temp_max_media=("temp_max_media", "mean"),
        umidade_media=("umidade_media", "mean"),
        umidade_min_media=("umidade_min_media", "mean"),
        precipitacao_total=("precipitacao_total", "mean")
    ).reset_index()

    uf_mensal["amplitude_termica"] = uf_mensal["temp_max_media"] - uf_mensal["temp_min_media"]
    uf_mensal["codigo_uf"] = uf_mensal["uf"].map(SIGLA_PARA_CODIGO_UF)
    uf_mensal = uf_mensal.rename(columns={"mes_ano": "data"})
    return uf_mensal


def processar_anos(anos):
    """Executa a extração e consolidação para a lista de anos."""
    resultados = []
    for ano in anos:
        buffer_zip = baixar_zip_ano(ano)
        if buffer_zip is None:
            continue
        try:
            df_ano = processar_zip_ano(buffer_zip, ano)
            if df_ano is not None and not df_ano.empty:
                resultados.append(df_ano)
                print(f"[{ano}] Sucesso: {len(df_ano)} registros mensais de UFs gerados.")
        except Exception as e:
            print(f"[{ano}] Erro no processamento: {e}", file=sys.stderr)

    if not resultados:
        print("Nenhum dado processado.")
        return None

    df_consolidado = pd.concat(resultados, ignore_index=True)

    # Se já existir um arquivo anterior e estivermos rodando incrementalmente, fazemos a junção
    if CSV_SAIDA.exists():
        try:
            existente = pd.read_csv(CSV_SAIDA, parse_dates=["data"])
            anos_processados = df_consolidado["data"].dt.year.unique()
            existente = existente[~existente["data"].dt.year.isin(anos_processados)]
            df_consolidado = pd.concat([existente, df_consolidado], ignore_index=True)
        except Exception as e:
            print(f"Aviso ao ler CSV existente: {e}")

    ordem_colunas = [
        "codigo_uf", "uf", "data", "temp_media", "temp_min_media", "temp_min_abs",
        "temp_max_media", "umidade_media", "umidade_min_media", "precipitacao_total",
        "amplitude_termica"
    ]
    df_consolidado = df_consolidado.sort_values(["codigo_uf", "data"]).reset_index(drop=True)
    df_consolidado = df_consolidado[[c for c in ordem_colunas if c in df_consolidado.columns]]

    # Arredondar para 2 casas decimais
    cols_float = df_consolidado.select_dtypes(include="float").columns
    df_consolidado[cols_float] = df_consolidado[cols_float].round(2)

    CSV_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df_consolidado.to_csv(CSV_SAIDA, index=False)
    tamanho_kb = CSV_SAIDA.stat().st_size / 1024
    print(f"\nBase consolidada salva em: {CSV_SAIDA}")
    print(f"Total de registros: {len(df_consolidado)} | Tamanho: {tamanho_kb:.1f} KB")
    return df_consolidado


def main():
    parser = argparse.ArgumentParser(description="Extração e tratamento de dados meteorológicos do INMET.")
    parser.add_argument("--ano", type=int, help="Ano específico para processar (ex: 2024).")
    parser.add_argument("--inicio", type=int, default=2008, help="Ano inicial da série (padrão: 2008).")
    parser.add_argument("--fim", type=int, default=2026, help="Ano final da série (padrão: 2026).")
    parser.add_argument("--piloto", action="store_true", help="Modo piloto: processa apenas 2024 para validação rápida.")

    args = parser.parse_args()

    if args.piloto:
        anos = [2024]
        print("--- EXECUTANDO MODO PILOTO (ANO 2024) ---")
    elif args.ano:
        anos = [args.ano]
        print(f"--- PROCESSANDO ANO ESPECÍFICO ({args.ano}) ---")
    else:
        anos = list(range(args.inicio, args.fim + 1))
        print(f"--- PROCESSANDO SÉRIE COMPLETA ({args.inicio} A {args.fim}) ---")

    processar_anos(anos)


if __name__ == "__main__":
    main()

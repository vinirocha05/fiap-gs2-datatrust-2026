"""Trata data/raw/internacoes.csv e salva data/processed/internacoes_tratado.csv.

Saída (formato longo): codigo_uf, estado, data (datetime), valor.
"""
import pandas as pd

from utils_tratamento import (
    PASTA_RAW, UFS, colunas_mensais, converter_valores, ler_csv,
    limpar_texto, para_formato_longo, salvar_processado,
)


def corrigir_estado(valor):
    """Padroniza 'código Nome' usando o código da UF (ex.: '35 Sao Paulo')."""
    valor = limpar_texto(valor)
    if pd.isna(valor):
        return valor
    codigo = valor.split(maxsplit=1)[0]
    if codigo in UFS:
        return f"{codigo} {UFS[codigo][0]}"
    return valor


def main():
    df = ler_csv(PASTA_RAW / "internacoes.csv")
    df["estado"] = df["estado"].apply(corrigir_estado)

    # remove a linha de total geral (a coluna 'Total' é ignorada nas mensais)
    df = df[df["estado"].str.lower() != "total"].copy()

    meses = colunas_mensais(df)
    df, trocas = converter_valores(df, meses)

    longo = para_formato_longo(df, ["estado"], meses)
    partes = longo["estado"].str.split(n=1, expand=True)
    longo["codigo_uf"] = partes[0].astype(int)
    longo["estado"] = partes[1]
    longo = (longo[["codigo_uf", "estado", "data", "valor"]]
             .sort_values(["codigo_uf", "data"]).reset_index(drop=True))

    assert longo["codigo_uf"].nunique() == len(UFS), "UFs faltando"
    assert not longo.duplicated(["codigo_uf", "data"]).any(), "datas duplicadas"
    assert longo.notna().all().all(), "valores nulos"

    destino = salvar_processado(longo, "internacoes_tratado.csv")
    print(f"'-' trocados por 0: {trocas}")
    print(f"{longo.shape[0]} linhas | {longo['codigo_uf'].nunique()} UFs | "
          f"{longo['data'].min():%Y-%m} a {longo['data'].max():%Y-%m}")
    print(f"Salvo em: {destino}")


if __name__ == "__main__":
    main()

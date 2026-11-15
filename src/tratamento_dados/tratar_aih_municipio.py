"""Trata data/raw/aih_municio.csv e salva data/processed/aih_municipio_tratado.csv.

Saída (formato longo): codigo_municipio, municipio, codigo_uf, uf, data (datetime), valor.
"""
from utils_tratamento import (
    PASTA_RAW, UFS, colunas_mensais, converter_valores, ler_csv,
    limpar_texto, para_formato_longo, salvar_processado,
)


def main():
    # o arquivo original se chama 'aih_municio.csv' (sem o "p")
    df = ler_csv(PASTA_RAW / "aih_municio.csv")
    df["municipio"] = df["municipio"].apply(limpar_texto)

    # remove a linha de total geral
    df = df[df["municipio"].str.lower() != "total"].copy()

    # '522200 VIANOPOLIS' -> codigo_municipio, municipio, codigo_uf, uf
    partes = df["municipio"].str.extract(r"^(\d{6})\s+(.+)$")
    invalidos = partes[0].isna()
    assert not invalidos.any(), f"Municípios fora do padrão: {df.loc[invalidos, 'municipio'].tolist()[:5]}"
    df["codigo_municipio"] = partes[0]
    df["municipio"] = partes[1].str.upper()
    df["codigo_uf"] = df["codigo_municipio"].str[:2]
    assert df["codigo_uf"].isin(UFS).all(), "Código de UF desconhecido"
    df["uf"] = df["codigo_uf"].map(lambda c: UFS[c][1])
    df["codigo_uf"] = df["codigo_uf"].astype(int)

    meses = colunas_mensais(df)
    df, trocas = converter_valores(df, meses)

    ids = ["codigo_municipio", "municipio", "codigo_uf", "uf"]
    longo = (para_formato_longo(df, ids, meses)
             .sort_values(["codigo_municipio", "data"]).reset_index(drop=True))

    assert not longo.duplicated(["codigo_municipio", "data"]).any(), "datas duplicadas"
    assert longo.notna().all().all(), "valores nulos"

    destino = salvar_processado(longo, "aih_municipio_tratado.csv")
    print(f"'-' trocados por 0: {trocas}")
    print(f"{longo.shape[0]} linhas | {longo['codigo_municipio'].nunique()} municípios | "
          f"{longo['data'].min():%Y-%m} a {longo['data'].max():%Y-%m}")
    print(f"Salvo em: {destino}")


if __name__ == "__main__":
    main()

"""Cálculos dos insights exibidos na aba Insights do app.

Mesmas regras de limpeza dos notebooks em `src/eda/`: zeros de UF viram dado
ausente, meses recentes incompletos ficam de fora e 2020/2021 são excluídos
das médias de sazonalidade (pandemia).
"""
import numpy as np
import pandas as pd

from previsao import CSV_INTERNACOES

CSV_MUNICIPIOS = CSV_INTERNACOES.with_name("aih_municipio_tratado.csv")
ANOS_PANDEMIA = (2020, 2021)
ANO_BASE_SAZONALIDADE = 2012


def serie_nacional(df):
    """Soma das UFs por mês, só dos meses em que as 27 UFs têm dado."""
    por_mes = df.groupby("data")["valor"].agg(["sum", "count"])
    completos = por_mes[por_mes["count"] == df["codigo_uf"].nunique()]["sum"]
    return completos


def _fator_sazonal(serie):
    """Média de cada mês dividida pela média do próprio ano (1,0 = mês típico)."""
    serie = serie[(serie.index.year >= ANO_BASE_SAZONALIDADE) & ~serie.index.year.isin(ANOS_PANDEMIA)]
    # só anos fechados, para a média anual não ficar enviesada
    anos_fechados = serie.groupby(serie.index.year).count().loc[lambda c: c == 12].index
    serie = serie[serie.index.year.isin(anos_fechados)]
    relativa = serie / serie.groupby(serie.index.year).transform("mean")
    return relativa.groupby(relativa.index.month).mean()


def sazonalidade_nacional(df):
    return _fator_sazonal(serie_nacional(df))


def sazonalidade_uf(df, codigo_uf):
    return _fator_sazonal(df[df["codigo_uf"] == codigo_uf].set_index("data")["valor"].dropna())


def matriz_sazonalidade(df):
    """Linhas = estado, colunas = mês (1 a 12)."""
    linhas = {}
    for estado, grupo in df.groupby("estado"):
        linhas[estado] = _fator_sazonal(grupo.set_index("data")["valor"].dropna())
    return pd.DataFrame(linhas).T


def totais_anuais(df):
    """Total por UF e ano, só de anos fechados (12 meses de dados)."""
    base = df.dropna(subset=["valor"])
    contagem = base.groupby(["estado", base["data"].dt.year])["valor"].agg(["sum", "count"])
    return contagem[contagem["count"] == 12]["sum"].unstack()


def crescimento_uf(df, ano_ini=2012, ano_fim=2025):
    anual = totais_anuais(df)
    return (anual[ano_fim] / anual[ano_ini] - 1).sort_values()


def concentracao_uf(df, ano=2025):
    anual = totais_anuais(df)[ano].sort_values(ascending=False)
    return anual / anual.sum()


def queda_pandemia(df):
    """Maior queda mensal da série nacional (abr/2020)."""
    serie = serie_nacional(df)
    variacao = serie.pct_change()
    return variacao.idxmin(), variacao.min()


def carregar_municipios():
    """Municípios no formato longo, sem o último mês se estiver incompleto."""
    mu = pd.read_csv(CSV_MUNICIPIOS, parse_dates=["data"])
    ativos = mu[mu["valor"] > 0].groupby("data")["municipio"].count()
    referencia = ativos.rolling(12).median().shift(1)
    incompletos = ativos[ativos < 0.9 * referencia].index
    return mu[~mu["data"].isin(incompletos)]


def volume_municipios(mu, ano=2025):
    """Internações no ano por município, do maior para o menor."""
    ano_mu = mu[mu["data"].dt.year == ano]
    return (ano_mu.groupby(["municipio", "uf"])["valor"].sum()
            .sort_values(ascending=False).reset_index())


def pareto_municipios(volume):
    """Porcentagem acumulada das internações pelos municípios em ordem de volume."""
    acumulado = volume["valor"].cumsum() / volume["valor"].sum()
    return pd.Series(acumulado.values * 100, index=np.arange(1, len(volume) + 1))


def anual_nacional(df):
    """Total nacional por ano, só de anos fechados (12 meses com as 27 UFs)."""
    serie = serie_nacional(df)
    contagem = serie.groupby(serie.index.year).count()
    anos_fechados = contagem[contagem == 12].index
    por_ano = serie.groupby(serie.index.year).sum()
    return por_ano[por_ano.index.isin(anos_fechados)]


def marcar_rotulo(mu):
    """Nome + UF, porque há municípios com o mesmo nome em estados diferentes."""
    mu = mu.copy()
    mu["rotulo"] = mu["municipio"].str.title() + " (" + mu["uf"] + ")"
    return mu


def pct_sem_internacao(mu, ano=2025):
    """Porcentagem de municípios sem nenhuma internação no ano."""
    por_municipio = mu[mu["data"].dt.year == ano].groupby("codigo_municipio")["valor"].sum()
    return (por_municipio == 0).mean() * 100


def maior_municipio_por_uf(mu, ano=2025):
    """Participação do maior município nas internações de cada UF."""
    ano_mu = mu[mu["data"].dt.year == ano]
    total_uf = ano_mu.groupby("uf")["valor"].sum()
    maior = (ano_mu.groupby(["uf", "rotulo"])["valor"].sum().reset_index()
             .sort_values("valor", ascending=False).drop_duplicates("uf").set_index("uf"))
    maior["participacao"] = maior["valor"] / total_uf * 100
    return maior.sort_values("participacao", ascending=False)


CSV_CLIMA = CSV_INTERNACOES.with_name("inmet_uf_mensal.csv")


def carregar_clima():
    """Lê a base meteorológica consolidada do INMET por UF e mês."""
    if not CSV_CLIMA.exists():
        return None
    try:
        return pd.read_csv(CSV_CLIMA, parse_dates=["data"])
    except Exception:
        return None


def _adicionar_indice_sazonal(comb):
    """Remove a tendência de crescimento secular (2008-2026) calculando o desvio %
    de cada mês em relação à média do próprio ano (isolando o efeito sazonal/climático)."""
    comb = comb.copy()
    media_ano = comb.groupby(comb["data"].dt.year)["valor"].transform("mean")
    comb["indice_sazonal"] = (comb["valor"] / media_ano - 1.0) * 100.0
    return comb


def correlacao_clima_uf(df_internacoes, df_clima, codigo_uf):
    """Calcula a correlação dessazonalizada e a série combinada de internações e clima da UF."""
    if df_clima is None or df_clima.empty:
        return None, {}

    cols_int = [c for c in ["codigo_uf", "data", "valor"] if c in df_internacoes.columns]
    sub_int = df_internacoes[df_internacoes["codigo_uf"] == codigo_uf][cols_int].dropna(subset=["valor"])
    sub_cli = df_clima[df_clima["codigo_uf"] == codigo_uf].dropna(subset=["temp_media"])

    if sub_int.empty or sub_cli.empty:
        return None, {}

    comb = pd.merge(sub_int, sub_cli, on=["codigo_uf", "data"], how="inner").sort_values("data")
    if len(comb) < 12:
        return None, {}

    comb = _adicionar_indice_sazonal(comb)

    # Exclui anos de pandemia (2020/2021) para evitar distorções
    comb_valida = comb[~comb["data"].dt.year.isin(ANOS_PANDEMIA)].copy()

    # Correlação com o índice sazonal (sem o viés do crescimento demográfico de 18 anos)
    corr_temp_min = comb_valida["indice_sazonal"].corr(comb_valida["temp_min_media"])
    corr_temp_med = comb_valida["indice_sazonal"].corr(comb_valida["temp_media"])
    corr_umidade = comb_valida["indice_sazonal"].corr(comb_valida["umidade_media"])

    # Correlação no ciclo climatológico médio (12 meses)
    ciclo = comb_valida.groupby(comb_valida["data"].dt.month)[["indice_sazonal", "temp_min_media"]].mean()
    corr_ciclo = ciclo["indice_sazonal"].corr(ciclo["temp_min_media"])

    metricas = {
        "corr_temp_min": corr_temp_min,
        "corr_temp_med": corr_temp_med,
        "corr_umidade": corr_umidade,
        "corr_ciclo": corr_ciclo,
    }
    return comb, metricas


def perfil_mensal_clima(df_clima, codigo_uf):
    """Calcula médias sazonais dos 12 meses do ano para o clima da UF."""
    if df_clima is None or df_clima.empty:
        return None
    sub = df_clima[df_clima["codigo_uf"] == codigo_uf].copy()
    if sub.empty:
        return None
    sub["mes"] = sub["data"].dt.month
    return sub.groupby("mes").agg(
        temp_media=("temp_media", "mean"),
        temp_min_media=("temp_min_media", "mean"),
        temp_max_media=("temp_max_media", "mean"),
        umidade_media=("umidade_media", "mean"),
        precipitacao_total=("precipitacao_total", "mean")
    ).round(1)


def correlacao_clima_brasil(df_internacoes, df_clima):
    """Calcula a correlação dessazonalizada e a série combinada nacional."""
    if df_clima is None or df_clima.empty:
        return None, {}

    cols_int = [c for c in ["codigo_uf", "data", "valor"] if c in df_internacoes.columns]
    sub_int = df_internacoes[cols_int].dropna(subset=["valor"]).groupby("data")["valor"].sum().reset_index()

    sub_cli = df_clima.groupby("data").agg(
        temp_media=("temp_media", "mean"),
        temp_min_media=("temp_min_media", "mean"),
        umidade_media=("umidade_media", "mean"),
        precipitacao_total=("precipitacao_total", "mean")
    ).reset_index()

    comb = pd.merge(sub_int, sub_cli, on="data", how="inner").sort_values("data")
    if len(comb) < 12:
        return None, {}

    comb = _adicionar_indice_sazonal(comb)

    comb_valida = comb[~comb["data"].dt.year.isin(ANOS_PANDEMIA)].copy()
    corr_temp_min = comb_valida["indice_sazonal"].corr(comb_valida["temp_min_media"])
    corr_temp_med = comb_valida["indice_sazonal"].corr(comb_valida["temp_media"])
    corr_umidade = comb_valida["indice_sazonal"].corr(comb_valida["umidade_media"])

    ciclo = comb_valida.groupby(comb_valida["data"].dt.month)[["indice_sazonal", "temp_min_media"]].mean()
    corr_ciclo = ciclo["indice_sazonal"].corr(ciclo["temp_min_media"])

    metricas = {
        "corr_temp_min": corr_temp_min,
        "corr_temp_med": corr_temp_med,
        "corr_umidade": corr_umidade,
        "corr_ciclo": corr_ciclo,
    }
    return comb, metricas


def perfil_mensal_clima_brasil(df_clima):
    """Calcula médias sazonais dos 12 meses do ano agregadas para todo o Brasil."""
    if df_clima is None or df_clima.empty:
        return None
    sub = df_clima.copy()
    sub["mes"] = sub["data"].dt.month
    return sub.groupby("mes").agg(
        temp_media=("temp_media", "mean"),
        temp_min_media=("temp_min_media", "mean"),
        temp_max_media=("temp_max_media", "mean"),
        umidade_media=("umidade_media", "mean"),
        precipitacao_total=("precipitacao_total", "mean")
    ).round(1)




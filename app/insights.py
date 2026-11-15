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

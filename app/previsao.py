"""Dados, modelo e previsão usados pelo app Streamlit.

Segue a mesma lógica do notebook `src/models/regressao.ipynb`: Ridge com
defasagens, médias móveis, mês e UF, prevendo o mês seguinte.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CSV_INTERNACOES = Path(__file__).resolve().parents[1] / "data" / "processed" / "internacoes_tratado.csv"

COL_NUM = ["lag_1", "lag_2", "lag_3", "lag_12", "media_3m", "media_12m"]
COL_CAT = ["codigo_uf", "mes"]
CORTE_BACKTEST = pd.Timestamp("2024-01-01")
MAX_MESES = 12
# mês final abaixo dessa fração da mediana dos 12 anteriores é tratado como incompleto
LIMITE_MES_INCOMPLETO = 0.4
# z de ~80% de confiança (faixa entre os percentis 10 e 90)
Z_FAIXA = 1.28


@dataclass
class Previsao:
    historico: pd.Series          # série válida da UF, indexada por mês
    descartados: pd.Series        # meses finais ignorados por parecerem incompletos
    previsao: pd.DataFrame        # colunas: previsto, minimo, maximo
    erro_tipico: float            # erro relativo típico de um passo (backtest)


def _aparar_final(serie):
    """Remove do fim da série os meses vazios ou muito abaixo do normal."""
    valida = serie.copy()
    descartados = {}
    while len(valida) > 13:
        ultimo = valida.iloc[-1]
        referencia = valida.iloc[-13:-1].median()
        if pd.notna(ultimo) and ultimo >= LIMITE_MES_INCOMPLETO * referencia:
            break
        descartados[valida.index[-1]] = ultimo
        valida = valida.iloc[:-1]
    return valida, pd.Series(descartados, dtype="float64").sort_index()


def carregar_dados():
    """Lê o CSV tratado. Zeros viram NaN (no SIH, '-' significa dado ausente)
    e meses finais incompletos são removidos de cada UF."""
    df = pd.read_csv(CSV_INTERNACOES, parse_dates=["data"])
    df["valor"] = df["valor"].replace(0, np.nan)
    df = df.sort_values(["codigo_uf", "data"]).reset_index(drop=True)

    for codigo, grupo in df.groupby("codigo_uf"):
        serie = grupo.set_index("data")["valor"]
        _, descartados = _aparar_final(serie)
        df.loc[(df["codigo_uf"] == codigo) & df["data"].isin(descartados.index), "valor"] = np.nan
    return df


def descartados_da_uf(codigo_uf):
    """Meses finais que foram ignorados para a UF, com o valor original."""
    original = pd.read_csv(CSV_INTERNACOES, parse_dates=["data"])
    serie = original.query("codigo_uf == @codigo_uf").set_index("data")["valor"].replace(0, np.nan)
    return _aparar_final(serie)[1]


def calcular_variaveis(df):
    df = df.sort_values(["codigo_uf", "data"]).copy()
    por_uf = df.groupby("codigo_uf")["valor"]
    for meses in (1, 2, 3, 12):
        df[f"lag_{meses}"] = por_uf.shift(meses)
    for janela in (3, 12):
        df[f"media_{janela}m"] = por_uf.transform(lambda s: s.shift(1).rolling(janela).mean())
    df["mes"] = df["data"].dt.month
    return df.dropna()


def montar_pipeline():
    preparo = ColumnTransformer([
        ("num", StandardScaler(), COL_NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), COL_CAT),
    ])
    return Pipeline([("preparo", preparo), ("modelo", Ridge(alpha=100))])


def treinar(df, ate=None):
    """Ajusta o modelo com os dados anteriores a `ate` (ou todos, se None)."""
    dados = calcular_variaveis(df)
    if ate is not None:
        dados = dados[dados["data"] < ate]
    modelo = montar_pipeline()
    modelo.fit(dados[COL_NUM + COL_CAT], dados["valor"])
    return modelo


def erro_tipico_por_uf(df):
    """Erro relativo típico (MAD robusto) de um passo no holdout, por UF.

    O modelo é treinado até 2023-12 e avaliado de 2024-01 em diante.
    """
    modelo = treinar(df, ate=CORTE_BACKTEST)
    teste = calcular_variaveis(df)
    teste = teste[teste["data"] >= CORTE_BACKTEST]
    previsto = modelo.predict(teste[COL_NUM + COL_CAT])
    erro_relativo = (previsto - teste["valor"]) / teste["valor"]
    por_uf = erro_relativo.groupby(teste["codigo_uf"])
    return por_uf.apply(lambda e: 1.4826 * (e - e.median()).abs().median())


def _variaveis_do_proximo_mes(historico, codigo_uf, mes):
    return pd.DataFrame([{
        "lag_1": historico.iloc[-1],
        "lag_2": historico.iloc[-2],
        "lag_3": historico.iloc[-3],
        "lag_12": historico.iloc[-12],
        "media_3m": historico.iloc[-3:].mean(),
        "media_12m": historico.iloc[-12:].mean(),
        "mes": mes,
        "codigo_uf": codigo_uf,
    }])


def prever_uf(df, modelo, erros, codigo_uf, meses):
    """Previsão recursiva: cada mês previsto entra como defasagem do seguinte."""
    serie = df.query("codigo_uf == @codigo_uf").set_index("data")["valor"]
    historico = serie.dropna()
    ultimo_mes = historico.index[-1]

    base = serie[serie.index <= ultimo_mes].ffill()
    valores = []
    datas = []
    for passo in range(1, meses + 1):
        data = ultimo_mes + pd.DateOffset(months=passo)
        x = _variaveis_do_proximo_mes(base, codigo_uf, data.month)
        previsto = float(modelo.predict(x[COL_NUM + COL_CAT])[0])
        base.loc[data] = previsto
        datas.append(data)
        valores.append(previsto)

    erro = float(erros.get(codigo_uf, erros.median()))
    horizonte = np.arange(1, meses + 1)
    margem = Z_FAIXA * erro * np.sqrt(horizonte)
    previsto = np.array(valores)
    tabela = pd.DataFrame({
        "previsto": previsto,
        "minimo": np.clip(previsto * (1 - margem), 0, None),
        "maximo": previsto * (1 + margem),
    }, index=pd.DatetimeIndex(datas, name="data"))

    return Previsao(historico, descartados_da_uf(codigo_uf), tabela, erro)


def indicadores(df, codigo_uf):
    """Indicadores do último mês completo da UF."""
    serie = df.query("codigo_uf == @codigo_uf").set_index("data")["valor"].dropna()
    ultimo_mes = serie.index[-1]
    ultimo = serie.iloc[-1]
    mes_anterior = serie.get(ultimo_mes - pd.DateOffset(months=1))
    mesmo_mes_ano_passado = serie.get(ultimo_mes - pd.DateOffset(years=1))

    total_brasil = df.loc[df["data"] == ultimo_mes, "valor"].sum()
    return {
        "ultimo_mes": ultimo_mes,
        "ultimo_valor": ultimo,
        "var_mensal": (ultimo / mes_anterior - 1) if mes_anterior else None,
        "var_anual": (ultimo / mesmo_mes_ano_passado - 1) if mesmo_mes_ano_passado else None,
        "media_12m": serie.iloc[-12:].mean(),
        "pico_valor": serie.max(),
        "pico_data": serie.idxmax(),
        "participacao": ultimo / total_brasil,
    }

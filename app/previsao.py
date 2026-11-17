"""Dados, modelo e previsão usados pelo app Streamlit.

Compara dois métodos distintos de predição:
1. Modelo Refinado com Clima (INMET + Sazonalidade): Ridge enriquecido com anomalias
   termo-hídricas ponderadas pelo porte hospitalar da UF (frio relativo, secura,
   amplitude térmica, choque térmico), defasagem anual (lag_12) e ciclo mensal.
2. Modelo Baseline Inercial (Sem Clima): Ridge puramente autorregressivo de curto/médio
   prazo (lag_1, lag_2, lag_3, media_3m, media_12m), sem modulação meteorológica.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CSV_INTERNACOES = Path(__file__).resolve().parents[1] / "data" / "processed" / "internacoes_tratado.csv"
CSV_CLIMA = Path(__file__).resolve().parents[1] / "data" / "processed" / "inmet_uf_mensal.csv"

# Baseline inercial (sem variáveis climáticas/sazonais)
COL_NUM_BASE = ["lag_1", "lag_2", "lag_3", "media_3m", "media_12m"]
COL_CAT_BASE = ["codigo_uf"]

# Modelo enriquecido com Clima (INMET) e Sazonalidade
COL_NUM_CLIMA = [
    "lag_1", "lag_2", "lag_3", "lag_12", "media_3m", "media_12m",
    "frio_relativo", "secura_relativa", "amp_relativa", "choque_frio"
]
COL_CAT_CLIMA = ["codigo_uf", "mes"]

COL_NUM = COL_NUM_BASE  # retrocompatibilidade
COL_CAT = COL_CAT_CLIMA

CORTE_BACKTEST = pd.Timestamp("2024-01-01")
MAX_MESES = 12
LIMITE_MES_INCOMPLETO = 0.4
Z_FAIXA = 1.28


@dataclass
class Previsao:
    historico: pd.Series          # série válida da UF, indexada por mês
    descartados: pd.Series        # meses finais ignorados por parecerem incompletos
    previsao: pd.DataFrame        # colunas: previsto, minimo, maximo (com clima se disponível)
    erro_tipico: float            # erro relativo típico de um passo (backtest)
    previsao_base: pd.DataFrame = None  # colunas: previsto (baseline inercial sem clima)
    tem_clima: bool = False       # indica se o modelo usou dados climáticos
    mae_clima: float = None       # MAE no holdout com clima
    mae_base: float = None        # MAE no holdout sem clima


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
    """Lê o CSV tratado de internações e cruza com dados climáticos do INMET, se disponíveis."""
    df = pd.read_csv(CSV_INTERNACOES, parse_dates=["data"])
    df["valor"] = df["valor"].replace(0, np.nan)
    df = df.sort_values(["codigo_uf", "data"]).reset_index(drop=True)

    for codigo, grupo in df.groupby("codigo_uf"):
        serie = grupo.set_index("data")["valor"]
        _, descartados = _aparar_final(serie)
        df.loc[(df["codigo_uf"] == codigo) & df["data"].isin(descartados.index), "valor"] = np.nan

    if CSV_CLIMA.exists():
        try:
            df_cli = pd.read_csv(CSV_CLIMA, parse_dates=["data"])
            cols_clima = [
                "codigo_uf", "data", "temp_media", "temp_min_media", "temp_min_abs",
                "temp_max_media", "umidade_media", "umidade_min_media",
                "precipitacao_total", "amplitude_termica"
            ]
            cols_presentes = [c for c in cols_clima if c in df_cli.columns]
            df = pd.merge(df, df_cli[cols_presentes], on=["codigo_uf", "data"], how="left")
        except Exception:
            pass

    return df


def descartados_da_uf(codigo_uf):
    """Meses finais que foram ignorados para a UF, com o valor original."""
    original = pd.read_csv(CSV_INTERNACOES, parse_dates=["data"])
    serie = original.query("codigo_uf == @codigo_uf").set_index("data")["valor"].replace(0, np.nan)
    return _aparar_final(serie)[1]


def obter_normais_climaticas(df):
    """Calcula normais mensais por UF e médias anuais de referência da UF."""
    if "temp_min_media" not in df.columns:
        return None, None
    df_c = df.copy()
    df_c["mes"] = df_c["data"].dt.month
    normais_mes = df_c.groupby(["codigo_uf", "mes"]).agg(
        temp_min_norm=("temp_min_media", "mean"),
        umid_norm=("umidade_media", "mean"),
        amp_norm=("amplitude_termica", "mean"),
    ).reset_index()

    medias_uf = df_c.groupby("codigo_uf").agg(
        temp_min_anual=("temp_min_media", "mean"),
        umid_anual=("umidade_media", "mean"),
        amp_anual=("amplitude_termica", "mean"),
    ).reset_index()
    return normais_mes, medias_uf


def calcular_variaveis(df, com_clima=False):
    """Cria preditoras autorregressivas e, quando `com_clima=True`, interações termo-hídricas escaladas."""
    df = df.sort_values(["codigo_uf", "data"]).copy()
    por_uf = df.groupby("codigo_uf")

    for meses in (1, 2, 3, 12):
        df[f"lag_{meses}"] = por_uf["valor"].shift(meses)
    for janela in (3, 12):
        df[f"media_{janela}m"] = por_uf["valor"].transform(lambda s: s.shift(1).rolling(janela).mean())
    df["mes"] = df["data"].dt.month

    if com_clima and "temp_min_media" in df.columns:
        normais_mes, medias_uf = obter_normais_climaticas(df)
        df = df.merge(normais_mes, on=["codigo_uf", "mes"], how="left").merge(medias_uf, on="codigo_uf", how="left")
        df = df.sort_values(["codigo_uf", "data"]).reset_index(drop=True)

        temp_efetiva = df["temp_min_media"].fillna(df["temp_min_norm"])
        umid_efetiva = df["umidade_media"].fillna(df["umid_norm"])
        amp_efetiva = df["amplitude_termica"].fillna(df["amp_norm"])

        # Variáveis físicas ponderadas pela escala hospitalar da UF (media_12m)
        df["frio_relativo"] = (df["temp_min_anual"] - temp_efetiva) * df["media_12m"]
        df["secura_relativa"] = (df["umid_anual"] - umid_efetiva) * df["media_12m"]
        df["amp_relativa"] = (amp_efetiva - df["amp_anual"]) * df["media_12m"]
        df["lag_1_frio"] = df.groupby("codigo_uf")["frio_relativo"].shift(1)
        df["choque_frio"] = df["frio_relativo"] - df["lag_1_frio"]

        return df.dropna(subset=["lag_12", "media_12m", "valor"])

    return df.dropna(subset=COL_NUM_BASE + ["valor"])


def montar_pipeline(com_clima=False):
    """Constrói o pipeline Scikit-Learn distinto para cada estratégia de modelagem."""
    cols_num = COL_NUM_CLIMA if com_clima else COL_NUM_BASE
    cols_cat = COL_CAT_CLIMA if com_clima else COL_CAT_BASE
    alpha = 50 if com_clima else 100

    preparo = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), cols_num),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cols_cat),
    ])
    return Pipeline([("preparo", preparo), ("modelo", Ridge(alpha=alpha))])


def treinar(df, ate=None, com_clima=False):
    """Ajusta o modelo com os dados anteriores a `ate` (ou todos, se None)."""
    dados = calcular_variaveis(df, com_clima=com_clima)
    if ate is not None:
        dados = dados[dados["data"] < ate]

    cols_num = COL_NUM_CLIMA if com_clima else COL_NUM_BASE
    cols_cat = COL_CAT_CLIMA if com_clima else COL_CAT_BASE
    modelo = montar_pipeline(com_clima=com_clima)
    modelo.fit(dados[cols_num + cols_cat], dados["valor"])
    return modelo


def erro_tipico_por_uf(df, com_clima=False):
    """Erro relativo típico (MAD robusto) de um passo no holdout (2024 em diante), por UF."""
    modelo = treinar(df, ate=CORTE_BACKTEST, com_clima=com_clima)
    teste = calcular_variaveis(df, com_clima=com_clima)
    teste = teste[teste["data"] >= CORTE_BACKTEST]

    cols_num = COL_NUM_CLIMA if com_clima else COL_NUM_BASE
    cols_cat = COL_CAT_CLIMA if com_clima else COL_CAT_BASE
    previsto = modelo.predict(teste[cols_num + cols_cat])
    erro_relativo = (previsto - teste["valor"]) / teste["valor"]
    por_uf = erro_relativo.groupby(teste["codigo_uf"])
    return por_uf.apply(lambda e: 1.4826 * (e - e.median()).abs().median())


def mae_holdout_por_uf(df, com_clima=False):
    """Retorna o MAE absoluto no período de holdout (2024+) por UF."""
    modelo = treinar(df, ate=CORTE_BACKTEST, com_clima=com_clima)
    teste = calcular_variaveis(df, com_clima=com_clima)
    teste = teste[teste["data"] >= CORTE_BACKTEST]

    cols_num = COL_NUM_CLIMA if com_clima else COL_NUM_BASE
    cols_cat = COL_CAT_CLIMA if com_clima else COL_CAT_BASE
    previsto = modelo.predict(teste[cols_num + cols_cat])
    erro_abs = (previsto - teste["valor"]).abs()
    return erro_abs.groupby(teste["codigo_uf"]).mean()


def _variaveis_proximo_mes_base(historico, codigo_uf):
    return pd.DataFrame([{
        "lag_1": historico.iloc[-1],
        "lag_2": historico.iloc[-2],
        "lag_3": historico.iloc[-3],
        "media_3m": historico.iloc[-3:].mean(),
        "media_12m": historico.iloc[-12:].mean(),
        "codigo_uf": codigo_uf,
    }])


def prever_uf(df, modelo_clima, erros_clima, codigo_uf, meses, modelo_base=None, erros_base=None):
    """Previsão recursiva comparando o Modelo Climático (INMET) com o Baseline Inercial."""
    serie = df.query("codigo_uf == @codigo_uf").set_index("data")["valor"]
    historico = serie.dropna()
    ultimo_mes = historico.index[-1]

    tem_clima = "temp_min_media" in df.columns and modelo_clima is not None
    normais_mes, medias_uf = obter_normais_climaticas(df)

    # 1. Projeção Baseline Inercial (Sem Clima)
    mod_b = modelo_base if modelo_base is not None else modelo_clima
    base_b = serie[serie.index <= ultimo_mes].ffill()
    valores_base = []
    datas = []

    for passo in range(1, meses + 1):
        data = ultimo_mes + pd.DateOffset(months=passo)
        x_b = _variaveis_proximo_mes_base(base_b, codigo_uf)
        p_b = float(mod_b.predict(x_b[COL_NUM_BASE + COL_CAT_BASE])[0])
        base_b.loc[data] = p_b
        datas.append(data)
        valores_base.append(p_b)

    tabela_base = pd.DataFrame({"previsto": np.array(valores_base)}, index=pd.DatetimeIndex(datas, name="data"))

    # 2. Projeção Refinada com Clima (INMET)
    if tem_clima and normais_mes is not None and medias_uf is not None:
        base_c = serie[serie.index <= ultimo_mes].ffill()
        valores_clima = []

        norm_uf = normais_mes[normais_mes["codigo_uf"] == codigo_uf].set_index("mes")
        anual_uf = medias_uf[medias_uf["codigo_uf"] == codigo_uf].iloc[0]

        t_anual = float(anual_uf["temp_min_anual"])
        u_anual = float(anual_uf["umid_anual"])
        a_anual = float(anual_uf["amp_anual"])

        for passo in range(1, meses + 1):
            data = ultimo_mes + pd.DateOffset(months=passo)
            m = data.month
            m_ant = (data - pd.DateOffset(months=1)).month

            m12 = float(base_c.iloc[-12:].mean())
            t_m = float(norm_uf.loc[m, "temp_min_norm"]) if m in norm_uf.index else t_anual
            t_ant = float(norm_uf.loc[m_ant, "temp_min_norm"]) if m_ant in norm_uf.index else t_anual
            u_m = float(norm_uf.loc[m, "umid_norm"]) if m in norm_uf.index else u_anual
            a_m = float(norm_uf.loc[m, "amp_norm"]) if m in norm_uf.index else a_anual

            frio_m = (t_anual - t_m) * m12
            frio_ant = (t_anual - t_ant) * m12
            secura_m = (u_anual - u_m) * m12
            amp_m = (a_m - a_anual) * m12

            x_c = pd.DataFrame([{
                "lag_1": base_c.iloc[-1],
                "lag_2": base_c.iloc[-2],
                "lag_3": base_c.iloc[-3],
                "lag_12": base_c.iloc[-12],
                "media_3m": base_c.iloc[-3:].mean(),
                "media_12m": m12,
                "frio_relativo": frio_m,
                "secura_relativa": secura_m,
                "amp_relativa": amp_m,
                "choque_frio": frio_m - frio_ant,
                "codigo_uf": codigo_uf,
                "mes": m,
            }])
            p_c = float(modelo_clima.predict(x_c[COL_NUM_CLIMA + COL_CAT_CLIMA])[0])
            base_c.loc[data] = p_c
            valores_clima.append(p_c)

        erro = float(erros_clima.get(codigo_uf, erros_clima.median()))
        horizonte = np.arange(1, meses + 1)
        margem = Z_FAIXA * erro * np.sqrt(horizonte)
        previsto_arr = np.array(valores_clima)

        tabela_clima = pd.DataFrame({
            "previsto": previsto_arr,
            "minimo": np.clip(previsto_arr * (1 - margem), 0, None),
            "maximo": previsto_arr * (1 + margem),
        }, index=pd.DatetimeIndex(datas, name="data"))

        return Previsao(
            historico=historico,
            descartados=descartados_da_uf(codigo_uf),
            previsao=tabela_clima,
            erro_tipico=erro,
            previsao_base=tabela_base,
            tem_clima=True
        )

    err_b = erros_base if erros_base is not None else erros_clima
    erro = float(err_b.get(codigo_uf, err_b.median()))
    horizonte = np.arange(1, meses + 1)
    margem = Z_FAIXA * erro * np.sqrt(horizonte)
    previsto_arr = np.array(valores_base)
    tabela_base["minimo"] = np.clip(previsto_arr * (1 - margem), 0, None)
    tabela_base["maximo"] = previsto_arr * (1 + margem)

    return Previsao(
        historico=historico,
        descartados=descartados_da_uf(codigo_uf),
        previsao=tabela_base,
        erro_tipico=erro,
        previsao_base=None,
        tem_clima=False
    )


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


def prever_brasil(df, modelo_clima, erros_clima, meses, modelo_base=None, erros_base=None):
    """Gera previsão consolidada para todo o Brasil agregando as projeções das 27 UFs."""
    serie_nacional = df.dropna(subset=["valor"]).groupby("data")["valor"].sum()
    data_inicio_nacional = pd.Timestamp("2026-09-01")
    datas_nacionais = [data_inicio_nacional + pd.DateOffset(months=i) for i in range(meses)]

    ufs_codigos = sorted(df["codigo_uf"].unique())
    previsoes_c = []
    previsoes_b = []

    for cod in ufs_codigos:
        serie = df.query("codigo_uf == @cod").set_index("data")["valor"].dropna()
        ult = serie.index[-1]
        passos = (datas_nacionais[-1].year - ult.year) * 12 + (datas_nacionais[-1].month - ult.month)
        if passos > 0:
            res = prever_uf(df, modelo_clima, erros_clima, cod, passos, modelo_base=modelo_base, erros_base=erros_base)
            p_c = res.previsao.reindex(datas_nacionais)
            previsoes_c.append(p_c)
            if res.previsao_base is not None:
                p_b = res.previsao_base.reindex(datas_nacionais)
                previsoes_b.append(p_b)

    tot_c = pd.concat(previsoes_c).groupby("data").sum()
    tot_b = pd.concat(previsoes_b).groupby("data").sum() if previsoes_b else None

    erro_nacional = float(np.median([erros_clima.get(c, 0.05) for c in ufs_codigos]))
    horizonte = np.arange(1, meses + 1)
    margem = Z_FAIXA * (erro_nacional / np.sqrt(len(ufs_codigos)) * 1.5) * np.sqrt(horizonte)
    tot_c["minimo"] = np.clip(tot_c["previsto"] * (1 - margem), 0, None)
    tot_c["maximo"] = tot_c["previsto"] * (1 + margem)

    return Previsao(
        historico=serie_nacional,
        descartados=pd.Series(dtype="float64"),
        previsao=tot_c,
        erro_tipico=erro_nacional,
        previsao_base=tot_b,
        tem_clima=True
    )


def indicadores_brasil(df):
    """Indicadores consolidados do último mês completo do Brasil."""
    serie = df.dropna(subset=["valor"]).groupby("data")["valor"].sum()
    ultimo_mes = serie.index[-1]
    ultimo = serie.iloc[-1]
    mes_anterior = serie.get(ultimo_mes - pd.DateOffset(months=1))
    mesmo_mes_ano_passado = serie.get(ultimo_mes - pd.DateOffset(years=1))

    return {
        "ultimo_mes": ultimo_mes,
        "ultimo_valor": ultimo,
        "var_mensal": (ultimo / mes_anterior - 1) if mes_anterior else None,
        "var_anual": (ultimo / mesmo_mes_ano_passado - 1) if mesmo_mes_ano_passado else None,
        "media_12m": serie.iloc[-12:].mean(),
        "pico_valor": serie.max(),
        "pico_data": serie.idxmax(),
        "participacao": 1.0,
    }

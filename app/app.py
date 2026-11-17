"""App Streamlit: histórico, impacto climático (INMET) e previsão de internações (SIH/DATASUS).

Rodar na raiz do repositório:
    venv/bin/streamlit run app/app.py
"""
import base64
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insights as ins  # noqa: E402
import previsao as pv  # noqa: E402

COR_HISTORICO = "#38bdf8"
COR_PREVISAO = "#f59e0b"
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
CAMINHO_LOGO = Path(__file__).resolve().parent / "assets" / "logo_fluxsus.png"

st.set_page_config(page_title="FluxSUS · Previsão de internações", page_icon="🏥", layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 2rem; max-width: 1250px; }
.hero {
    padding: 1.6rem 2rem; border-radius: 20px; margin-bottom: 1.4rem;
    background: linear-gradient(120deg, #0f2a4a 0%, #134e6f 55%, #0e7490 100%);
    border: 1px solid rgba(255,255,255,0.08);
}
.hero h1 { margin: 0; font-size: 2rem; color: #f8fafc; }
.hero p { margin: .4rem 0 0; color: #bae6fd; font-size: 1rem; }
.card {
    background: linear-gradient(160deg, #162033 0%, #1b2940 100%);
    border: 1px solid rgba(148,163,184,0.18);
    border-radius: 16px;
    padding: 0.95rem 0.85rem;
    height: 144px;
    min-height: 144px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    box-sizing: border-box;
    transition: transform .2s ease, border-color .2s ease;
}
.card:hover { transform: translateY(-3px); border-color: #38bdf8; }
.card .rotulo {
    color: #94a3b8;
    font-size: .74rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .05em;
    line-height: 1.25;
    min-height: 2.5em;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
}
.card .valor {
    color: #f1f5f9;
    font-size: 1.55rem;
    font-weight: 700;
    margin: .2rem 0;
    line-height: 1.15;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
}
.card .detalhe {
    font-size: .8rem;
    color: #94a3b8;
    line-height: 1.2;
    min-height: 2.4em;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
}
.sobe { color: #fb7185; } .desce { color: #2dd4bf; }
.secao { color: #e2e8f0; font-size: 1.15rem; font-weight: 600; margin: 1.6rem 0 .6rem; }
.nota {
    background: rgba(56,189,248,0.07); border-left: 3px solid #38bdf8; border-radius: 8px;
    padding: .7rem 1rem; color: #cbd5e1; font-size: .92rem; margin: .4rem 0 1rem;
}
.nota b { color: #f1f5f9; }
.acao { border-left-color: #f59e0b; background: rgba(245,158,11,0.07); }
.sidebar-logo-box {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 0.5rem 0 1.1rem 0;
    margin-bottom: 0.6rem;
    border-bottom: 1px solid rgba(148,163,184,0.16);
}
.sidebar-logo-box img {
    width: 195px;
    max-width: 100%;
    height: auto;
    aspect-ratio: 263 / 104;
    object-fit: contain;
    border-radius: 10px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.35);
}
</style>
""", unsafe_allow_html=True)


def renderizar_logo_sidebar():
    """Exibe a logo Data Trust · FluxSUS acima dos parâmetros sem distorcer a proporção."""
    if CAMINHO_LOGO.exists():
        b64 = base64.b64encode(CAMINHO_LOGO.read_bytes()).decode("utf-8")
        st.markdown(
            f'<div class="sidebar-logo-box">'
            f'<img src="data:image/png;base64,{b64}" alt="Data Trust · FluxSUS">'
            f'</div>',
            unsafe_allow_html=True,
        )


def largura_total(elemento, *args):
    """Ocupa a largura toda; `width` só existe nas versões novas do Streamlit."""
    try:
        elemento(*args, width="stretch")
    except Exception:
        elemento(*args, use_container_width=True)


def formatar(numero):
    return f"{numero:,.0f}".replace(",", ".")


def formatar_mes(data):
    return f"{MESES_PT[data.month - 1]}/{data.year}"


def formatar_variacao(valor):
    if valor is None or pd.isna(valor):
        return '<span class="detalhe">sem referência</span>'
    classe = "sobe" if valor >= 0 else "desce"
    seta = "▲" if valor >= 0 else "▼"
    return f'<span class="{classe}">{seta} {abs(valor) * 100:.1f}%</span>'.replace(".", ",")


def cartao(rotulo, valor, detalhe):
    return (f'<div class="card"><div class="rotulo">{rotulo}</div>'
            f'<div class="valor">{valor}</div><div class="detalhe">{detalhe}</div></div>')


@st.cache_data
def carregar():
    df = pv.carregar_dados()
    nomes = (pd.read_csv(pv.CSV_INTERNACOES, usecols=["codigo_uf", "estado"])
             .drop_duplicates().set_index("estado")["codigo_uf"].sort_index())
    return df, nomes


@st.cache_resource
def treinar_modelo(df):
    mod_clima = pv.treinar(df, com_clima=True)
    err_clima = pv.erro_tipico_por_uf(df, com_clima=True)
    mod_base = pv.treinar(df, com_clima=False)
    err_base = pv.erro_tipico_por_uf(df, com_clima=False)
    return mod_clima, err_clima, mod_base, err_base


df, ufs = carregar()
modelo_clima, erros_clima, modelo_base, erros_base = treinar_modelo(df)

st.markdown("""
<div class="hero">
  <h1>🏥 FluxSUS · Previsão de internações</h1>
  <p>Histórico do SIH/DATASUS, inteligência climática (INMET) e previsão dos próximos meses para apoiar o planejamento de equipes e leitos.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    renderizar_logo_sidebar()
    st.header("Parâmetros")
    OPCAO_BRASIL = "Brasil (Todos os estados)"
    opcoes_territorios = [OPCAO_BRASIL] + list(ufs.index)
    estado = st.selectbox("Território", opcoes_territorios, index=opcoes_territorios.index("São Paulo"))
    codigo_uf = None if estado == OPCAO_BRASIL else int(ufs[estado])
    meses = st.number_input("Meses a prever", min_value=1, max_value=pv.MAX_MESES, value=12, step=1)
    anos = sorted(df["data"].dt.year.unique())
    ano_inicial = st.select_slider("Histórico a partir de", options=anos, value=anos[0])
    st.caption("Modelos comparados: (1) Ridge com interações climáticas INMET e sazonalidade vs. "
               "(2) Baseline autorregressivo inercial (sem clima).")


def aba_previsao(estado, codigo_uf, meses, ano_inicial):
    """Histórico, previsão e indicadores da UF escolhida ou de todo o Brasil."""
    if codigo_uf is None:
        resultado = pv.prever_brasil(
            df, modelo_clima, erros_clima, int(meses),
            modelo_base=modelo_base, erros_base=erros_base
        )
        ind = pv.indicadores_brasil(df)
    else:
        resultado = pv.prever_uf(
            df, modelo_clima, erros_clima, codigo_uf, int(meses),
            modelo_base=modelo_base, erros_base=erros_base
        )
        ind = pv.indicadores(df, codigo_uf)

    if len(resultado.descartados):
        ignorados = ", ".join(formatar_mes(d) for d in resultado.descartados.index)
        st.warning(f"Os dados de {ignorados} de {estado} parecem incompletos e foram ignorados. "
                   f"A previsão parte de {formatar_mes(ind['ultimo_mes'])}.")

    rotulo_part = "Total nacional consolidado" if codigo_uf is None else f"{ind['participacao'] * 100:.1f}% do Brasil".replace(".", ",")
    colunas = st.columns(5)
    colunas[0].markdown(cartao(
        f"Último mês · {formatar_mes(ind['ultimo_mes'])}", formatar(ind["ultimo_valor"]),
        rotulo_part), unsafe_allow_html=True)
    colunas[1].markdown(cartao(
        "Vs. mês anterior", formatar_variacao(ind["var_mensal"]), "variação mensal"), unsafe_allow_html=True)
    colunas[2].markdown(cartao(
        "Vs. mesmo mês do ano ant.", formatar_variacao(ind["var_anual"]), "variação anual"), unsafe_allow_html=True)
    colunas[3].markdown(cartao(
        "Média últimos 12 meses", formatar(ind["media_12m"]), "internações por mês"), unsafe_allow_html=True)
    colunas[4].markdown(cartao(
        "Pico histórico", formatar(ind["pico_valor"]), formatar_mes(ind["pico_data"])), unsafe_allow_html=True)

    st.markdown('<div class="secao">Histórico e comparação de modelos preditivos (Com Clima INMET vs. Baseline Inercial)</div>', unsafe_allow_html=True)

    historico = resultado.historico[resultado.historico.index.year >= ano_inicial]
    previsao = resultado.previsao
    ultimo_ponto = historico.index[-1]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=historico.index, y=historico.values, name="Histórico (DATASUS)", mode="lines",
        line=dict(color=COR_HISTORICO, width=2.4), fill="tozeroy", fillcolor="rgba(56,189,248,0.07)",
        hovertemplate="%{x|%b/%Y}: %{y:,.0f}<extra>histórico</extra>"))
    fig.add_trace(go.Scatter(
        x=list(previsao.index) + list(previsao.index[::-1]),
        y=list(previsao["maximo"]) + list(previsao["minimo"][::-1]),
        fill="toself", fillcolor="rgba(245,158,11,0.18)", line=dict(width=0),
        hoverinfo="skip", name="Faixa provável (80%)"))

    if resultado.previsao_base is not None:
        fig.add_trace(go.Scatter(
            x=[ultimo_ponto] + list(resultado.previsao_base.index),
            y=[historico.iloc[-1]] + list(resultado.previsao_base["previsto"]),
            name="Baseline Inercial (sem clima)", mode="lines+markers",
            line=dict(color="#e2e8f0", width=2.2, dash="dot"), marker=dict(size=6, symbol="circle-open"),
            hovertemplate="%{x|%b/%Y}: %{y:,.0f}<extra>sem clima (inercial)</extra>"))

    nome_prev = "Previsão Refinada (com clima INMET)" if resultado.tem_clima else "Previsão"
    fig.add_trace(go.Scatter(
        x=[ultimo_ponto] + list(previsao.index), y=[historico.iloc[-1]] + list(previsao["previsto"]),
        name=nome_prev, mode="lines+markers",
        line=dict(color=COR_PREVISAO, width=2.8), marker=dict(size=7),
        hovertemplate="%{x|%b/%Y}: %{y:,.0f}<extra>com clima INMET</extra>"))

    fig.update_layout(
        template="plotly_dark", height=470, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified", legend=dict(orientation="h", y=1.08, x=0),
        xaxis=dict(rangeslider=dict(visible=True, thickness=0.06), showgrid=False),
        yaxis=dict(title="internações por mês", gridcolor="rgba(148,163,184,0.12)", tickformat=",.0f"))
    largura_total(st.plotly_chart, fig)

    if resultado.previsao_base is not None:
        diferencas = previsao["previsto"] - resultado.previsao_base["previsto"]
        max_alta = diferencas.max()
        mes_alta = formatar_mes(diferencas.idxmax())
        max_queda = diferencas.min()
        mes_queda = formatar_mes(diferencas.idxmin())
        amplitude_mod = max_alta - max_queda
        st.markdown(
            f'<div class="nota"><b>🌡️ Diferenciação Metodológica (Com Clima INMET vs. Baseline Inercial):</b><br>'
            f'• <b>Baseline Inercial (linha pontilhada clara):</b> utiliza apenas defasagens recentes (<code>lag_1..3</code> e médias móveis), '
            f'projetando uma tendência amortecida sem enxergar ondas de frio ou calor.<br>'
            f'• <b>Modelo com Clima INMET (linha laranja sólida):</b> incorpora anomalias de temperatura mínima, amplitude térmica, umidade e choque térmico '
            f'ponderados pelo porte hospitalar da UF (reduzindo o erro MAE no holdout nacional de <b>1.762 para 1.452 internações/mês</b>).<br>'
            f'• <b>Efeito prático no horizonte selecionado:</b> modulação sazonal de <b>{formatar(amplitude_mod)} internações</b> entre o vale de verão '
            f'(<b>{formatar(max_queda)}</b> em {mes_queda}) e o pico de frio/inverno (<b>+{formatar(max_alta)}</b> em {mes_alta}).</div>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="secao">Previsão mês a mês</div>', unsafe_allow_html=True)
    tabela = pd.DataFrame(index=previsao.index)
    tabela["Previsto (com Clima)"] = previsao["previsto"]
    if resultado.previsao_base is not None:
        tabela["Baseline (sem Clima)"] = resultado.previsao_base["previsto"]
        tabela["Ajuste do Clima"] = tabela["Previsto (com Clima)"] - tabela["Baseline (sem Clima)"]
    tabela["Mínimo provável"] = previsao["minimo"]
    tabela["Máximo provável"] = previsao["maximo"]
    tabela.index = [formatar_mes(d) for d in tabela.index]
    tabela.index.name = "Mês"
    largura_total(st.dataframe, tabela.round(0).astype(int))

    erro_texto = f"{resultado.erro_tipico * 100:.1f}".replace(".", ",")
    rotulo_territorio = "Brasil" if codigo_uf is None else estado
    st.caption(
        f"Erro típico do modelo para {rotulo_territorio}: cerca de {erro_texto}% por mês no holdout "
        "(2024 em diante). A faixa é uma aproximação baseada nesse erro e cresce com o horizonte, "
        "então previsões mais distantes são menos confiáveis. Os dados são de internações hospitalares (SIH) "
        "e servem como aproximação da pressão sobre o sistema, não da lotação de UPA/UBS."
    )


@st.cache_data
def carregar_municipios():
    return ins.marcar_rotulo(ins.carregar_municipios())


def formatar_pct(valor, casas=1, sinal=False):
    texto = f"{valor:+.{casas}f}" if sinal else f"{valor:.{casas}f}"
    return texto.replace(".", ",") + "%"


def virgula(valor, casas=1):
    return f"{valor:.{casas}f}".replace(".", ",")


def estilizar(fig, altura=380):
    fig.update_layout(
        template="plotly_dark", height=altura, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="rgba(148,163,184,0.12)"), xaxis=dict(showgrid=False))
    return fig


def nota(titulo, texto, acao=False):
    classe = "nota acao" if acao else "nota"
    st.markdown(f'<div class="{classe}"><b>{titulo}</b><br>{texto}</div>', unsafe_allow_html=True)


def aba_clima(estado, codigo_uf, ano_inicial=2008):
    """Análise detalhada da influência meteorológica (INMET) sobre a demanda hospitalar."""
    df_clima = ins.carregar_clima()
    if df_clima is None or df_clima.empty:
        st.info("Base meteorológica do INMET não encontrada em `data/processed/inmet_uf_mensal.csv`.")
        return

    if codigo_uf is None:
        comb_clima, metricas_clima = ins.correlacao_clima_brasil(df, df_clima)
        perfil = ins.perfil_mensal_clima_brasil(df_clima)
    else:
        comb_clima, metricas_clima = ins.correlacao_clima_uf(df, df_clima, codigo_uf)
        perfil = ins.perfil_mensal_clima(df_clima, codigo_uf)

    if comb_clima is None or comb_clima.empty:
        st.warning(f"Sem dados meteorológicos suficientes para {estado}.")
        return

    comb_clima_filtrado = comb_clima[comb_clima["data"].dt.year >= ano_inicial].copy()

    rotulo_territorio = "todo o território nacional" if codigo_uf is None else estado
    st.caption(
        f"Cruzamento entre séries do DATASUS (ajustadas pela tendência anual para isolar o efeito sazonal) "
        f"e medições das estações meteorológicas do INMET em {rotulo_territorio}."
    )

    r_temp = metricas_clima.get("corr_temp_min", np.nan)
    r_ciclo = metricas_clima.get("corr_ciclo", np.nan)
    mes_frio_idx = int(perfil["temp_min_media"].idxmin()) if perfil is not None else 7
    mes_seco_idx = int(perfil["umidade_media"].idxmin()) if perfil is not None else 8

    c1, c2, c3, c4 = st.columns(4)
    texto_r_temp = f"{r_temp:.2f}".replace(".", ",") if pd.notna(r_temp) else "N/D"
    texto_r_ciclo = f"{r_ciclo:.2f}".replace(".", ",") if pd.notna(r_ciclo) else "N/D"
    val_frio = f"{perfil.loc[mes_frio_idx, 'temp_min_media']:.1f} °C".replace(".", ",") if perfil is not None else "N/D"
    val_seco = f"{perfil.loc[mes_seco_idx, 'umidade_media']:.0f}%" if perfil is not None else "N/D"

    c1.markdown(cartao("Corr. Mensal (Dessazonalizada)", texto_r_temp, "pressão sazonal vs. temp. mínima"), unsafe_allow_html=True)
    c2.markdown(cartao("Corr. Ciclo Climatológico", texto_r_ciclo, "aderência entre curvas de frio e internação"), unsafe_allow_html=True)
    c3.markdown(cartao(f"Mês Mais Frio · {MESES_PT[mes_frio_idx-1].capitalize()}", val_frio, "média histórica das temperaturas mínimas"), unsafe_allow_html=True)
    c4.markdown(cartao(f"Mês Mais Seco · {MESES_PT[mes_seco_idx-1].capitalize()}", val_seco, "umidade média do período de estiagem"), unsafe_allow_html=True)

    st.markdown('<div class="secao">Histórico comparativo: Demanda hospitalar vs. Temperatura Mínima</div>', unsafe_allow_html=True)
    fig_clima = go.Figure()
    fig_clima.add_trace(go.Scatter(
        x=comb_clima_filtrado["data"], y=comb_clima_filtrado["valor"],
        name="Internações (DATASUS)", line=dict(color=COR_HISTORICO, width=2.4),
        hovertemplate="%{x|%b/%Y}: %{y:,.0f} internações<extra></extra>"
    ))
    fig_clima.add_trace(go.Scatter(
        x=comb_clima_filtrado["data"], y=comb_clima_filtrado["temp_min_media"],
        name="Temp. Mínima Média (°C)", yaxis="y2",
        line=dict(color="#f59e0b", width=2.2, dash="dot"),
        hovertemplate="%{x|%b/%Y}: %{y:.1f} °C<extra></extra>"
    ))
    fig_clima.update_layout(
        yaxis=dict(title="internações por mês"),
        yaxis2=dict(title="temperatura mínima (°C)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    largura_total(st.plotly_chart, estilizar(fig_clima, 380))

    col_esq, col_dir = st.columns(2)
    with col_esq:
        st.markdown('<div class="secao">Dispersão: Temperatura Mínima x Pressão Sazonal (%)</div>', unsafe_allow_html=True)
        # Exclui anos de pandemia (2020/2021) na dispersão para evidenciar a relação física normal
        disp_df = comb_clima_filtrado[~comb_clima_filtrado["data"].dt.year.isin(ins.ANOS_PANDEMIA)].copy()
        valid_mask = disp_df["temp_min_media"].notna() & disp_df["indice_sazonal"].notna()
        disp_df = disp_df[valid_mask]

        fig_scat = go.Figure()
        fig_scat.add_trace(go.Scatter(
            x=disp_df["temp_min_media"], y=disp_df["indice_sazonal"],
            mode="markers", name="Meses observados",
            marker=dict(
                color=disp_df["temp_min_media"],
                colorscale="RdYlBu_r",
                size=8,
                opacity=0.8,
                line=dict(width=0.5, color="#1e293b")
            ),
            text=[formatar_mes(d) for d in disp_df["data"]],
            hovertemplate="<b>%{text}</b><br>Temp. Mínima: %{x:.1f} °C<br>Pressão Sazonal: %{y:+.1f}% sobre a média anual<extra></extra>"
        ))
        if len(disp_df) > 2:
            x_vals = disp_df["temp_min_media"]
            y_vals = disp_df["indice_sazonal"]
            poly = np.polyfit(x_vals, y_vals, 1)
            x_trend = np.linspace(x_vals.min(), x_vals.max(), 40)
            y_trend = np.polyval(poly, x_trend)
            fig_scat.add_trace(go.Scatter(
                x=x_trend, y=y_trend, mode="lines",
                name=f"Tendência ({poly[0]:+.2f}% por °C)",
                line=dict(color="#f59e0b", width=3, dash="dash")
            ))
        fig_scat.add_hline(y=0, line_dash="dot", line_color="rgba(148,163,184,0.35)")
        fig_scat.update_layout(
            xaxis=dict(title="temperatura mínima média do mês (°C)"),
            yaxis=dict(title="variação de internações vs. média do ano (%)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        largura_total(st.plotly_chart, estilizar(fig_scat, 360))

    with col_dir:
        st.markdown('<div class="secao">Normal Climatológica da UF (Ciclo Anual)</div>', unsafe_allow_html=True)
        if perfil is not None:
            fig_norm = go.Figure()
            fig_norm.add_trace(go.Bar(
                x=[m.capitalize() for m in MESES_PT], y=perfil["precipitacao_total"],
                name="Chuva acumulada (mm)", marker_color="rgba(56,189,248,0.35)", yaxis="y2",
                hovertemplate="%{x}: %{y:.1f} mm<extra>Chuva</extra>"
            ))
            fig_norm.add_trace(go.Scatter(
                x=[m.capitalize() for m in MESES_PT], y=perfil["temp_max_media"],
                name="Temp. Máxima (°C)", line=dict(color="#fb7185", width=2.2),
                hovertemplate="%{x}: %{y:.1f} °C<extra>Máx</extra>"
            ))
            fig_norm.add_trace(go.Scatter(
                x=[m.capitalize() for m in MESES_PT], y=perfil["temp_min_media"],
                name="Temp. Mínima (°C)", line=dict(color="#38bdf8", width=2.2),
                hovertemplate="%{x}: %{y:.1f} °C<extra>Mín</extra>"
            ))
            fig_norm.update_layout(
                yaxis=dict(title="temperatura (°C)"),
                yaxis2=dict(title="chuva (mm)", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            largura_total(st.plotly_chart, estilizar(fig_norm, 360))

    nota("Por que ajustar a tendência secular antes de medir a correlação?",
         "Entre 2008 e 2025, o total de internações do SUS cresceu mais de 35% devido à expansão da rede e ao envelhecimento populacional. "
         "Ao comparar o volume bruto de anos distantes, o crescimento demográfico mascarava o efeito térmico (r bruto de ~-0,24). "
         f"Quando isolamos a <b>Pressão Sazonal (% sobre a média do próprio ano)</b>, a correlação com o frio salta para <b>{texto_r_temp}</b> "
         f"(e <b>{texto_r_ciclo}</b> no ciclo anual), evidenciando a inclinação negativa no gráfico de dispersão.")
    nota("Adequação do Modelo Preditivo (Ridge com Interações de Escala)",
         f"Em {estado}, cada queda de 1 °C na temperatura mínima eleva proporcionalmente a demanda hospitalar. "
         "Por isso, o modelo preditivo multiplica a anomalia climática do INMET pela escala de atendimento da UF (<code>media_12m</code>), "
         "sendo a abordagem estatística mais robusta para séries mensais com forte componente autorregressiva.", acao=True)


def aba_municipios(estado, codigo_uf, ano_inicial=2008):
    """Análise territorial e concentração da demanda municipal."""
    mu = carregar_municipios()
    volume = ins.volume_municipios(mu)
    pareto = ins.pareto_municipios(volume)
    n_metade = int((pareto < 50).sum() + 1)
    sem_internacao = ins.pct_sem_internacao(mu)
    dominantes = ins.maior_municipio_por_uf(mu)
    dominantes_sem_df = dominantes[dominantes.index != "DF"]

    st.caption("Distribuição territorial das internações a partir da base municipal do SIH/DATASUS (referência: 2025).")

    cm1, cm2, cm3, cm4 = st.columns(4)
    cm1.markdown(cartao("Concentração (50% do SUS)", f"{n_metade} cidades", "respondem por metade das internações"), unsafe_allow_html=True)
    cm2.markdown(cartao("Municípios sem Internação", formatar_pct(sem_internacao, casas=0), "dependem de deslocamento regional"), unsafe_allow_html=True)
    cm3.markdown(cartao("Maior Polo Hospitalar", volume.iloc[0]["municipio"].title(), f"{formatar(volume.iloc[0]['valor'])} internações no ano"), unsafe_allow_html=True)
    cm4.markdown(cartao("Maior Dominância Estadual", dominantes_sem_df.iloc[0]["rotulo"], f"{dominantes_sem_df.iloc[0]['participacao']:.0f}% das internações da UF"), unsafe_allow_html=True)

    st.markdown('<div class="secao">Concentração: poucos municípios concentram a maior parte dos leitos</div>', unsafe_allow_html=True)
    esquerda, direita = st.columns(2)
    fig = go.Figure(go.Scatter(x=pareto.index, y=pareto.values, mode="lines",
                               line=dict(color=COR_HISTORICO, width=3),
                               hovertemplate="%{x} municípios: %{y:.0f}% das internações<extra></extra>"))
    fig.add_hline(y=50, line_dash="dash", line_color="#94a3b8")
    fig.update_layout(title="Curva de concentração de Pareto (2025)", xaxis=dict(type="log", title="municípios (escala log)"),
                      yaxis_title="% acumulado")
    largura_total(esquerda.plotly_chart, estilizar(fig, 380))

    top = volume.head(10).iloc[::-1]
    fig = go.Figure(go.Bar(x=top["valor"], y=top["municipio"].str.title() + " (" + top["uf"] + ")",
                           orientation="h", marker_color=COR_HISTORICO,
                           hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
    fig.update_layout(title="10 municípios com mais internações em 2025")
    largura_total(direita.plotly_chart, estilizar(fig, 380))

    top5_dom = dominantes_sem_df.head(5)
    lista = ", ".join(f"{linha['rotulo']} ({linha['participacao']:.0f}%)"
                      for _, linha in top5_dom.iterrows())
    nota("O que vemos no território",
         f"{n_metade} municípios concentram metade das internações de todo o país. "
         f"{sem_internacao:.0f}% dos municípios não tiveram internações registradas em 2025 (vazios assistenciais "
         f"que exigem deslocamento de pacientes). Em alguns estados a capital domina fortemente: {lista}.")
    nota("O que fazer na gestão regional",
         "O monitoramento contínuo de cerca de cem municípios polos já cobre metade da demanda assistencial. "
         "Para os municípios desprovidos de leitos, mapear rotas de transporte e articular centrais de regulação de vagas.", acao=True)


def aba_panorama(estado, codigo_uf, ano_inicial=2008):
    """Tendências macro, impacto pós-pandemia e matriz de sazonalidade entre as UFs."""
    anual = ins.anual_nacional(df)
    cresc_2019 = anual[2025] / anual[2019] - 1
    ritmo_antes = ((anual[2019] / anual[2008]) ** (1 / 11) - 1) * 100
    ritmo_depois = ((anual[2025] / anual[2021]) ** (1 / 4) - 1) * 100
    data_queda, queda = ins.queda_pandemia(df)
    saz = ins.sazonalidade_nacional(df)
    mes_pico, mes_vale = saz.idxmax(), saz.idxmin()
    concentracao = ins.concentracao_uf(df)
    top5 = concentracao.head(5).sum() * 100

    st.caption("Visão macro da evolução das internações hospitalares no Brasil.")

    cartoes = st.columns(5)
    cartoes[0].markdown(cartao("Total de 2025 vs. 2019", formatar_pct(cresc_2019 * 100, sinal=True),
                               f"{virgula(ritmo_depois)}% ao ano desde 2021"), unsafe_allow_html=True)
    cartoes[1].markdown(cartao("Maior queda mensal", formatar_pct(queda * 100, sinal=True),
                               formatar_mes(data_queda)), unsafe_allow_html=True)
    cartoes[2].markdown(cartao("Mês mais pesado", MESES_PT[mes_pico - 1].capitalize(),
                               formatar_pct((saz[mes_pico] - 1) * 100, sinal=True) + " sobre a média do ano"),
                        unsafe_allow_html=True)
    cartoes[3].markdown(cartao("Mês mais leve", MESES_PT[mes_vale - 1].capitalize(),
                               formatar_pct((saz[mes_vale] - 1) * 100, sinal=True) + " sobre a média do ano"),
                        unsafe_allow_html=True)
    cartoes[4].markdown(cartao("5 maiores estados", formatar_pct(top5),
                               "das internações do país"), unsafe_allow_html=True)

    # --- tendência
    st.markdown('<div class="secao">Tendência: a demanda saiu do ritmo pré-pandemia</div>', unsafe_allow_html=True)
    anual_filtrado = anual[anual.index >= ano_inicial]
    cores = ["#f59e0b" if ano in ins.ANOS_PANDEMIA else COR_HISTORICO for ano in anual_filtrado.index]
    fig = go.Figure(go.Bar(x=anual_filtrado.index, y=anual_filtrado.values / 1e6, marker_color=cores,
                           hovertemplate="%{x}: %{y:.2f} mi<extra></extra>"))
    fig.update_layout(yaxis_title="milhões de internações", xaxis=dict(dtick=1, showgrid=False))
    largura_total(st.plotly_chart, estilizar(fig, 330))
    nota("O que vemos na tendência",
         f"Até 2019 o crescimento era de {virgula(ritmo_antes)}% ao ano. Depois da queda de 2020 (barras laranja), "
         f"o ritmo acelerou para {virgula(ritmo_depois)}% ao ano e 2025 ficou {cresc_2019 * 100:.0f}% acima de 2019.")
    nota("O que fazer",
         "Planejar equipes e leitos com a base atual, e não com a de antes de 2020. "
         "Tratar 2020 e 2021 como período atípico nas médias e metas.", acao=True)

    # --- sazonalidade comparativa
    if codigo_uf is not None:
        st.markdown(f'<div class="secao">Sazonalidade: comparação Brasil vs. {estado}</div>', unsafe_allow_html=True)
        saz_uf = ins.sazonalidade_uf(df, codigo_uf)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[m.capitalize() for m in MESES_PT], y=(saz.values - 1) * 100,
                             name="Brasil", marker_color=COR_HISTORICO,
                             hovertemplate="%{x}: %{y:+.1f}%<extra>Brasil</extra>"))
        fig.add_trace(go.Bar(x=[m.capitalize() for m in MESES_PT], y=(saz_uf.values - 1) * 100,
                             name=estado, marker_color=COR_PREVISAO,
                             hovertemplate="%{x}: %{y:+.1f}%<extra>" + estado + "</extra>"))
        fig.update_layout(barmode="group", yaxis_title="% sobre a média do ano",
                          legend=dict(orientation="h", y=1.12, x=0))
        largura_total(st.plotly_chart, estilizar(fig, 350))
    else:
        st.markdown('<div class="secao">Sazonalidade: calendário da demanda hospitalar no Brasil</div>', unsafe_allow_html=True)
        fig = go.Figure()
        cores_mes = [COR_PREVISAO if val >= 1.02 else COR_HISTORICO for val in saz.values]
        fig.add_trace(go.Bar(x=[m.capitalize() for m in MESES_PT], y=(saz.values - 1) * 100,
                             name="Brasil", marker_color=cores_mes,
                             hovertemplate="%{x}: %{y:+.1f}%<extra>Brasil</extra>"))
        fig.update_layout(yaxis_title="% sobre a média do ano")
        largura_total(st.plotly_chart, estilizar(fig, 350))

    # --- estados
    st.markdown('<div class="secao">Estados: quem cresce e quem concentra</div>', unsafe_allow_html=True)
    esquerda, direita = st.columns(2)
    crescimento = ins.crescimento_uf(df) * 100
    cores_uf = [COR_PREVISAO if e == estado else COR_HISTORICO for e in crescimento.index]
    fig = go.Figure(go.Bar(x=crescimento.values, y=crescimento.index, orientation="h", marker_color=cores_uf,
                           hovertemplate="%{y}: %{x:+.1f}%<extra></extra>"))
    fig.update_layout(title="Crescimento 2012 a 2025 (%)", yaxis=dict(tickfont=dict(size=10)))
    largura_total(esquerda.plotly_chart, estilizar(fig, 560))
    top10 = concentracao.head(10) * 100
    cores_top = [COR_PREVISAO if e == estado else COR_HISTORICO for e in top10.index]
    fig = go.Figure(go.Bar(x=top10.index, y=top10.values, marker_color=cores_top,
                           hovertemplate="%{x}: %{y:.1f}%<extra></extra>"))
    fig.update_layout(title="Participação nas internações de 2025 (%)", xaxis=dict(tickangle=-40))
    largura_total(direita.plotly_chart, estilizar(fig, 560))

    # --- matriz de calor
    st.markdown('<div class="secao">Matriz de Sazonalidade das 27 UFs</div>', unsafe_allow_html=True)
    matriz = ins.matriz_sazonalidade(df)
    matriz = matriz.loc[((matriz.max(axis=1) - matriz.min(axis=1))).sort_values().index]
    fig = go.Figure(go.Heatmap(
        z=matriz.values, x=[m.capitalize() for m in MESES_PT], y=matriz.index,
        colorscale="RdYlBu_r", zmid=1, colorbar=dict(title="fator"),
        hovertemplate="%{y} em %{x}: %{z:.2f}<extra></extra>"))
    fig.update_layout(title="Fator sazonal por estado (1,00 = mês típico; ordenado pela amplitude)",
                      yaxis=dict(tickfont=dict(size=10)))
    largura_total(st.plotly_chart, estilizar(fig, 650))

    st.markdown('<div class="secao">Resumo para a gestão pública</div>', unsafe_allow_html=True)
    st.markdown(
        "- **Planejar com a base atual:** a demanda hospitalar é estruturalmente maior que no pré-pandemia.\n"
        "- **Antecipar o calendário sazonal:** pico nacional de maio a outubro; folga entre dezembro e fevereiro.\n"
        "- **Respeitar as diferenças regionais:** estados do Sul e Sudeste sentem mais fortemente o inverno térmico.\n"
        "- **Monitorar municípios estratégicos:** cerca de 100 cidades respondem por metade das internações."
    )


tab_previsao, tab_clima, tab_municipios, tab_panorama = st.tabs([
    "📈 Previsão",
    "🌡️ Clima & INMET",
    "🗺️ Municípios & Território",
    "💡 Panorama Macro"
])
with tab_previsao:
    aba_previsao(estado, codigo_uf, meses, ano_inicial)
with tab_clima:
    aba_clima(estado, codigo_uf, ano_inicial)
with tab_municipios:
    aba_municipios(estado, codigo_uf, ano_inicial)
with tab_panorama:
    aba_panorama(estado, codigo_uf, ano_inicial)

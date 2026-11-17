"""App Streamlit: histórico e previsão de internações (SIH/DATASUS) por estado.

Rodar na raiz do repositório:
    venv/bin/streamlit run app/app.py
"""
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
    border: 1px solid rgba(148,163,184,0.18); border-radius: 16px;
    padding: 1rem 1.2rem; height: 100%;
    transition: transform .2s ease, border-color .2s ease;
}
.card:hover { transform: translateY(-3px); border-color: #38bdf8; }
.card .rotulo { color: #94a3b8; font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }
.card .valor { color: #f1f5f9; font-size: 1.7rem; font-weight: 700; margin: .2rem 0; }
.card .detalhe { font-size: .85rem; color: #94a3b8; }
.sobe { color: #fb7185; } .desce { color: #2dd4bf; }
.secao { color: #e2e8f0; font-size: 1.15rem; font-weight: 600; margin: 1.6rem 0 .6rem; }
.nota {
    background: rgba(56,189,248,0.07); border-left: 3px solid #38bdf8; border-radius: 8px;
    padding: .7rem 1rem; color: #cbd5e1; font-size: .92rem; margin: .4rem 0 1rem;
}
.nota b { color: #f1f5f9; }
.acao { border-left-color: #f59e0b; background: rgba(245,158,11,0.07); }
</style>
""", unsafe_allow_html=True)


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
    return pv.treinar(df), pv.erro_tipico_por_uf(df)


df, ufs = carregar()
modelo, erros = treinar_modelo(df)

st.markdown("""
<div class="hero">
  <h1>🏥 FluxSUS · Previsão de internações</h1>
  <p>Histórico do SIH/DATASUS por estado e previsão dos próximos meses para apoiar o planejamento de equipes e leitos.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Parâmetros")
    estado = st.selectbox("Estado", ufs.index, index=list(ufs.index).index("São Paulo"))
    meses = st.number_input("Meses a prever", min_value=1, max_value=pv.MAX_MESES, value=6, step=1)
    anos = sorted(df["data"].dt.year.unique())
    ano_inicial = st.select_slider("Histórico a partir de", options=anos, value=anos[0])
    st.caption("Modelo: regressão Ridge treinada com defasagens, médias móveis, mês e UF "
               "(ver `src/models/regressao.ipynb`).")


def aba_previsao(estado, codigo_uf, meses, ano_inicial):
    """Histórico, previsão e indicadores da UF escolhida."""
    resultado = pv.prever_uf(df, modelo, erros, codigo_uf, int(meses))
    ind = pv.indicadores(df, codigo_uf)

    if len(resultado.descartados):
        ignorados = ", ".join(formatar_mes(d) for d in resultado.descartados.index)
        st.warning(f"Os dados de {ignorados} de {estado} parecem incompletos e foram ignorados. "
                   f"A previsão parte de {formatar_mes(ind['ultimo_mes'])}.")

    colunas = st.columns(5)
    colunas[0].markdown(cartao(
        f"Último mês · {formatar_mes(ind['ultimo_mes'])}", formatar(ind["ultimo_valor"]),
        f"{ind['participacao'] * 100:.1f}% do Brasil".replace(".", ",")), unsafe_allow_html=True)
    colunas[1].markdown(cartao(
        "Vs. mês anterior", formatar_variacao(ind["var_mensal"]), "variação mensal"), unsafe_allow_html=True)
    colunas[2].markdown(cartao(
        "Vs. mesmo mês do ano anterior", formatar_variacao(ind["var_anual"]), "variação anual"), unsafe_allow_html=True)
    colunas[3].markdown(cartao(
        "Média dos últimos 12 meses", formatar(ind["media_12m"]), "internações por mês"), unsafe_allow_html=True)
    colunas[4].markdown(cartao(
        "Pico histórico", formatar(ind["pico_valor"]), formatar_mes(ind["pico_data"])), unsafe_allow_html=True)

    st.markdown('<div class="secao">Histórico e previsão</div>', unsafe_allow_html=True)

    historico = resultado.historico[resultado.historico.index.year >= ano_inicial]
    previsao = resultado.previsao
    ultimo_ponto = historico.index[-1]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=historico.index, y=historico.values, name="Histórico", mode="lines",
        line=dict(color=COR_HISTORICO, width=2.4), fill="tozeroy", fillcolor="rgba(56,189,248,0.07)",
        hovertemplate="%{x|%b/%Y}: %{y:,.0f}<extra>histórico</extra>"))
    fig.add_trace(go.Scatter(
        x=list(previsao.index) + list(previsao.index[::-1]),
        y=list(previsao["maximo"]) + list(previsao["minimo"][::-1]),
        fill="toself", fillcolor="rgba(245,158,11,0.18)", line=dict(width=0),
        hoverinfo="skip", name="Faixa provável (80%)"))
    fig.add_trace(go.Scatter(
        x=[ultimo_ponto] + list(previsao.index), y=[historico.iloc[-1]] + list(previsao["previsto"]),
        name="Previsão", mode="lines+markers",
        line=dict(color=COR_PREVISAO, width=2.6, dash="dash"), marker=dict(size=7),
        hovertemplate="%{x|%b/%Y}: %{y:,.0f}<extra>previsão</extra>"))
    fig.update_layout(
        template="plotly_dark", height=470, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified", legend=dict(orientation="h", y=1.08, x=0),
        xaxis=dict(rangeslider=dict(visible=True, thickness=0.06), showgrid=False),
        yaxis=dict(title="internações por mês", gridcolor="rgba(148,163,184,0.12)", tickformat=",.0f"))
    largura_total(st.plotly_chart, fig)

    st.markdown('<div class="secao">Previsão mês a mês</div>', unsafe_allow_html=True)
    tabela = previsao.copy()
    tabela.index = [formatar_mes(d) for d in tabela.index]
    tabela.index.name = "Mês"
    tabela.columns = ["Previsto", "Mínimo provável", "Máximo provável"]
    largura_total(st.dataframe, tabela.round(0).astype(int))

    erro_texto = f"{resultado.erro_tipico * 100:.1f}".replace(".", ",")
    st.caption(
        f"Erro típico do modelo para {estado}: cerca de {erro_texto}% por mês no holdout "
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


def aba_insights(estado, codigo_uf):
    """Achados da análise exploratória (ver `src/eda/`), recalculados a partir dos dados."""
    anual = ins.anual_nacional(df)
    cresc_2019 = anual[2025] / anual[2019] - 1
    ritmo_antes = ((anual[2019] / anual[2008]) ** (1 / 11) - 1) * 100
    ritmo_depois = ((anual[2025] / anual[2021]) ** (1 / 4) - 1) * 100
    data_queda, queda = ins.queda_pandemia(df)
    saz = ins.sazonalidade_nacional(df)
    mes_pico, mes_vale = saz.idxmax(), saz.idxmin()
    concentracao = ins.concentracao_uf(df)
    top5 = concentracao.head(5).sum() * 100

    mu = carregar_municipios()
    volume = ins.volume_municipios(mu)
    pareto = ins.pareto_municipios(volume)
    n_metade = int((pareto < 50).sum() + 1)
    sem_internacao = ins.pct_sem_internacao(mu)

    st.caption("Achados da análise exploratória (`src/eda/`) sobre internações hospitalares do SIH/DATASUS. "
               "Eles descrevem a pressão sobre o sistema, e não a lotação de UPA/UBS.")

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
    cores = ["#f59e0b" if ano in ins.ANOS_PANDEMIA else COR_HISTORICO for ano in anual.index]
    fig = go.Figure(go.Bar(x=anual.index, y=anual.values / 1e6, marker_color=cores,
                           hovertemplate="%{x}: %{y:.2f} mi<extra></extra>"))
    fig.update_layout(yaxis_title="milhões de internações", xaxis=dict(dtick=1, showgrid=False))
    largura_total(st.plotly_chart, estilizar(fig, 330))
    nota("O que vemos",
         f"Até 2019 o crescimento era de {virgula(ritmo_antes)}% ao ano. Depois da queda de 2020 (barras laranja), "
         f"o ritmo foi de {virgula(ritmo_depois)}% ao ano e 2025 ficou {cresc_2019 * 100:.0f}% acima de 2019.")
    nota("O que fazer",
         "Planejar equipes e leitos com a base atual, e não com a de antes de 2020. "
         "Tratar 2020 e 2021 como período atípico nas médias e metas.", acao=True)

    # --- sazonalidade
    st.markdown('<div class="secao">Sazonalidade: quando a demanda aperta</div>', unsafe_allow_html=True)
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
    meses_pesados = [MESES_PT[m - 1] for m in saz[saz >= 1.02].index]
    nota("O que vemos",
         f"Os meses acima da média em mais de 2% são {', '.join(meses_pesados)}; os mais leves são "
         f"{MESES_PT[mes_vale - 1]}, dez e jan. O padrão se repete todos os anos. "
         f"Em {estado}, o mês mais pesado é {MESES_PT[saz_uf.idxmax() - 1]} e o mais leve é {MESES_PT[saz_uf.idxmin() - 1]}.")
    nota("O que fazer",
         "Reforçar escalas e estoques de maio a outubro e usar dezembro a fevereiro para férias e reposição. "
         "Comparar um mês com o mesmo mês do ano anterior, e não com o mês anterior.", acao=True)

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
    mais_cresceu, menos_cresceu = crescimento.index[-1], crescimento.index[0]
    nota("O que vemos",
         f"{mais_cresceu} cresceu {crescimento.iloc[-1]:.0f}% desde 2012, enquanto {menos_cresceu} quase não cresceu "
         f"({crescimento.iloc[0]:.0f}%). Os cinco maiores estados somam {top5:.0f}% das internações e "
         f"{concentracao.index[0]} sozinho tem {concentracao.iloc[0] * 100:.0f}%.")
    nota("O que fazer",
         "Priorizar capacidade nos estados de crescimento acelerado e monitorar com mais atenção os maiores, "
         "onde um pequeno erro percentual pesa muito em volume. Estagnação pode indicar oferta saturada ou "
         "subnotificação: cruzar com a população (IBGE) antes de concluir.", acao=True)

    matriz = ins.matriz_sazonalidade(df)
    matriz = matriz.loc[((matriz.max(axis=1) - matriz.min(axis=1))).sort_values().index]
    fig = go.Figure(go.Heatmap(
        z=matriz.values, x=[m.capitalize() for m in MESES_PT], y=matriz.index,
        colorscale="RdYlBu_r", zmid=1, colorbar=dict(title="fator"),
        hovertemplate="%{y} em %{x}: %{z:.2f}<extra></extra>"))
    fig.update_layout(title="Fator sazonal por estado (1,00 = mês típico; ordenado pela amplitude)",
                      yaxis=dict(tickfont=dict(size=10)))
    largura_total(st.plotly_chart, estilizar(fig, 650))
    nota("O que fazer",
         "Usar um calendário sazonal por estado, e não um único para o país: a diferença entre o mês mais "
         "pesado e o mais leve vai de poucos pontos percentuais até mais de 20.", acao=True)

    # --- municípios
    st.markdown('<div class="secao">Municípios: a demanda é muito concentrada</div>', unsafe_allow_html=True)
    esquerda, direita = st.columns(2)
    fig = go.Figure(go.Scatter(x=pareto.index, y=pareto.values, mode="lines",
                               line=dict(color=COR_HISTORICO, width=3),
                               hovertemplate="%{x} municípios: %{y:.0f}% das internações<extra></extra>"))
    fig.add_hline(y=50, line_dash="dash", line_color="#94a3b8")
    fig.update_layout(title="Curva de concentração (2025)", xaxis=dict(type="log", title="municípios (escala log)"),
                      yaxis_title="% acumulado")
    largura_total(esquerda.plotly_chart, estilizar(fig, 380))
    top = volume.head(10).iloc[::-1]
    fig = go.Figure(go.Bar(x=top["valor"], y=top["municipio"].str.title() + " (" + top["uf"] + ")",
                           orientation="h", marker_color=COR_HISTORICO,
                           hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
    fig.update_layout(title="10 municípios com mais internações em 2025")
    largura_total(direita.plotly_chart, estilizar(fig, 380))

    dominantes = ins.maior_municipio_por_uf(mu)
    dominantes = dominantes[dominantes.index != "DF"].head(5)
    lista = ", ".join(f"{linha['rotulo']} ({linha['participacao']:.0f}%)"
                      for _, linha in dominantes.iterrows())
    nota("O que vemos",
         f"{n_metade} municípios concentram metade das internações do país. "
         f"{sem_internacao:.0f}% dos municípios não tiveram nenhuma internação em 2025 (provavelmente sem leito SUS "
         f"próprio, já que a base usa o município da internação). Em alguns estados a capital domina: {lista}.")
    nota("O que fazer",
         "Monitorar de perto cerca de cem municípios já cobre metade da demanda; o restante pede gestão regional. "
         "Antes de investir nos municípios sem internação, mapear para onde seus moradores se deslocam. "
         "Onde a capital domina, o estado depende de uma cidade só.", acao=True)

    # --- clima e demanda (INMET)
    df_clima = ins.carregar_clima()
    if df_clima is not None and not df_clima.empty:
        comb_clima, metricas_clima = ins.correlacao_clima_uf(df, df_clima, codigo_uf)
        if comb_clima is not None and not comb_clima.empty:
            st.markdown(f'<div class="secao">Clima e Demanda em {estado}: a influência das temperaturas (INMET)</div>', unsafe_allow_html=True)
            r_temp = metricas_clima.get("corr_temp_min", np.nan)
            r_umid = metricas_clima.get("corr_umidade", np.nan)

            cl1, cl2 = st.columns(2)
            texto_r_temp = f"{r_temp:.2f}".replace(".", ",") if pd.notna(r_temp) else "N/D"
            texto_r_umid = f"{r_umid:.2f}".replace(".", ",") if pd.notna(r_umid) else "N/D"
            cl1.markdown(cartao("Correlação (Temp. Mínima x Internações)", texto_r_temp,
                                "correlação negativa indica alta de internações no frio"), unsafe_allow_html=True)
            cl2.markdown(cartao("Correlação (Umidade x Internações)", texto_r_umid,
                                "relação entre ar seco e demanda hospitalar"), unsafe_allow_html=True)

            fig_clima = go.Figure()
            fig_clima.add_trace(go.Scatter(
                x=comb_clima["data"], y=comb_clima["valor"],
                name="Internações", line=dict(color=COR_HISTORICO, width=2.5),
                hovertemplate="%{x|%b/%Y}: %{y:,.0f} internações<extra></extra>"
            ))
            fig_clima.add_trace(go.Scatter(
                x=comb_clima["data"], y=comb_clima["temp_min_media"],
                name="Temp. Mínima Média (°C)", yaxis="y2",
                line=dict(color="#f59e0b", width=2, dash="dot"),
                hovertemplate="%{x|%b/%Y}: %{y:.1f} °C<extra></extra>"
            ))
            fig_clima.update_layout(
                title=f"Histórico comparativo: Internações vs. Temperatura Mínima em {estado}",
                yaxis=dict(title="Internações mensais"),
                yaxis2=dict(title="Temp. Mínima (°C)", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            largura_total(st.plotly_chart, estilizar(fig_clima, 360))
            nota("Impacto Operacional do Clima",
                 f"Em {estado}, períodos com queda acentuada de temperatura e ar seco coincidem com aumentos nas admissões hospitalares. "
                 "O cruzamento com os dados meteorológicos do INMET permite antecipar a compra preventiva de insumos respiratórios e remanejamento de plantonistas.", acao=True)

    st.markdown('<div class="secao">Resumo para a gestão</div>', unsafe_allow_html=True)
    st.markdown(
        "- **Planejar com a base atual:** a demanda é maior que antes de 2020 e continua crescendo.\n"
        "- **Antecipar o calendário:** reforço de maio a outubro, folga de dezembro a fevereiro.\n"
        "- **Olhar cada estado:** o calendário e o ritmo de crescimento mudam bastante entre eles.\n"
        "- **Focar nos grandes, sem esquecer os pequenos:** os maiores pesam mais, os pequenos oscilam mais.\n"
        "- **Validar os dados recentes:** os últimos meses costumam vir incompletos."
    )


codigo_uf = int(ufs[estado])
tab_previsao, tab_insights = st.tabs(["📈 Previsão", "💡 Insights"])
with tab_previsao:
    aba_previsao(estado, codigo_uf, meses, ano_inicial)
with tab_insights:
    aba_insights(estado, codigo_uf)

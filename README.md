# FluxoSUS

Projeto CitizenTech de análise e previsão de internações hospitalares do SUS, com visualização em um dashboard Streamlit. A proposta busca apoiar o planejamento de recursos de saúde a partir de dados históricos do SIH/DATASUS.

> **Escopo atual:** as bases disponíveis registram internações hospitalares por estado e município. Elas não medem diretamente filas ou lotação de UPAs e UBSs. Dados do INMET, IBGE e unidades de atendimento ainda não estão integrados ao pipeline.

## Por onde começar

1. **Entenda o desafio e os critérios**
   - [Contexto e proposta do projeto](docs/contexto.md)
   - [Requisitos da entrega](docs/requisitos_entrega.md)
2. **Conheça a estrutura e o fluxo dos arquivos**
   - [Relatório dos arquivos do projeto](docs/relatorio_arquivos_projeto.md)
   - [Guia de contexto e convenções da equipe](agents.md)
3. **Acompanhe o pipeline de dados e análise**, na sequência abaixo.

## Fluxo do projeto

### 1. Dados originais

Os arquivos em [`data/raw/`](data/raw/) são as fontes originais e não devem ser editados:

- [`internacoes.csv`](data/raw/internacoes.csv) — série mensal de internações por UF, de 2008 a ago/2026.
- [`aih_municio.csv`](data/raw/aih_municio.csv) — série mensal por município, de 2008 a set/2026. O nome está mantido conforme o arquivo original.

**AIH** significa Autorização de Internação Hospitalar; **SIH** é o Sistema de Informações Hospitalares do SUS. A base municipal refere-se ao município da internação, que pode ser diferente do município de residência do paciente.

### 2. Tratamento

Os scripts convertem os CSVs originais do formato largo para o formato longo e salvam os resultados em [`data/processed/`](data/processed/):

- [`utils_tratamento.py`](src/tratamento_dados/utils_tratamento.py) — funções compartilhadas de leitura, limpeza e transformação.
- [`tratar_internacoes.py`](src/tratamento_dados/tratar_internacoes.py) — prepara os dados por UF.
- [`tratar_aih_municipio.py`](src/tratamento_dados/tratar_aih_municipio.py) — prepara os dados por município.

As saídas são [`internacoes_tratado.csv`](data/processed/internacoes_tratado.csv) e [`aih_municipio_tratado.csv`](data/processed/aih_municipio_tratado.csv).

### 3. Análise exploratória

Os notebooks descrevem padrões e limitações das bases:

- [`eda_internacoes_uf.ipynb`](src/eda/eda_internacoes_uf.ipynb) — tendência, sazonalidade e concentração de internações por UF.
- [`eda_aih_municipio.ipynb`](src/eda/eda_aih_municipio.ipynb) — distribuição e concentração de internações por município.

### 4. Modelo de previsão

- [`regressao.ipynb`](src/models/regressao.ipynb) — notebook de previsão mensal de internações por UF, com comparação de modelos, validação temporal e métricas.

### 5. Dashboard

- [`app.py`](app/app.py) — interface Streamlit com as abas **Previsão** e **Insights**.
- [`previsao.py`](app/previsao.py) — preparação dos dados e cálculo das previsões.
- [`insights.py`](app/insights.py) — cálculos apresentados na aba de insights.

## Tecnologias

- **Python** para tratamento, análise e aplicação;
- **pandas** e **NumPy** para manipulação de dados;
- **scikit-learn** para modelos de Machine Learning;
- **Matplotlib** e **Seaborn** para gráficos nos notebooks;
- **Plotly** e **Streamlit** para visualização interativa e dashboard;
- **Jupyter**, **ipykernel** e **nbconvert** para desenvolvimento e execução dos notebooks.

As versões das dependências estão registradas em [`requirements.txt`](requirements.txt). O tema do dashboard está configurado em [`.streamlit/config.toml`](.streamlit/config.toml).

## Preparar o ambiente

Execute os comandos na raiz do repositório. No Linux ou macOS:

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

No Windows PowerShell:

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Iniciar o dashboard

Com o ambiente preparado, rode na raiz do repositório:

```bash
venv/bin/streamlit run app/app.py
```

No Windows PowerShell:

```powershell
.\venv\Scripts\streamlit.exe run app/app.py
```

Depois que o servidor iniciar, abra [http://localhost:8501](http://localhost:8501). O link abre o dashboard quando o Streamlit já está rodando; ele não inicia o servidor por conta própria.

## Regenerar os dados tratados

Se necessário, rode os scripts a partir da raiz:

```bash
venv/bin/python src/tratamento_dados/tratar_internacoes.py
venv/bin/python src/tratamento_dados/tratar_aih_municipio.py
```

No Windows PowerShell, substitua `venv/bin/python` por `.\venv\Scripts\python.exe`.

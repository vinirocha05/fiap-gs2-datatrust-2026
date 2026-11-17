# Relatório dos arquivos do projeto

**Data do inventário:** 16/11/2026
**Escopo:** arquivos e pastas do projeto, excluindo `venv/` e `.git/`.

Para inspecionar os notebooks sem imprimir suas saídas extensas, foram feitas cópias temporárias e convertidas com `nbconvert`. O Jupytext não está instalado; não foi necessário adicionar uma dependência. Os notebooks originais não foram alterados durante essa análise.

## Visão geral do fluxo

```text
dados originais → tratamento → dados processados → EDA e modelo → app Streamlit
```

O projeto parte de séries históricas agregadas de internações do SIH/DATASUS. Os notebooks fazem a análise exploratória e a previsão mensal por UF. O app apresenta histórico, previsões e insights calculados sobre as bases tratadas.

## 1. Orientações e configuração do ambiente

**Pastas:** raiz do projeto (`.`) e `.streamlit/`.

- [`README.md`](../README.md) — página inicial com descrição, tecnologias, navegação pelo fluxo do projeto e instruções para executar o dashboard.
- [`agents.md`](../agents.md) — guia de contexto, convenções, regras do trabalho, descrição das bases e decisões/pedências registradas.
- [`.gitignore`](../.gitignore) — evita versionar o ambiente `venv/`, bytecode e caches Python/Jupyter, além de segredos locais do Streamlit.
- [`requirements.txt`](../requirements.txt) — versões fixadas das dependências Python instaladas, incluindo bibliotecas de análise, notebooks, scikit-learn e Streamlit.
- [`.streamlit/config.toml`](../.streamlit/config.toml) — tema escuro e configuração do servidor Streamlit.

## 2. Definição do problema e critérios de entrega

**Pasta:** `docs/`.

- [`contexto.md`](contexto.md) — descreve a proposta FluxSUS, público, problema, solução, arquitetura e cuidados éticos. A seção “Parte 2: Pipeline” ainda está pendente.
- [`requisitos_entrega.md`](requisitos_entrega.md) — enunciado e critérios para a proposta em PDF, vídeo pitch e entrega técnica de Machine Learning.
- [`relatorio_arquivos_projeto.md`](relatorio_arquivos_projeto.md) — este inventário, organizado pelo fluxo de desenvolvimento.

## 3. Dados de entrada

**Pasta:** `data/raw/`. Esses arquivos são as fontes originais usadas pelo tratamento e não devem ser editados.

- [`internacoes.csv`](../data/raw/internacoes.csv) — série mensal em formato largo por UF, de 2008 a ago/2026, com uma linha adicional de total.
- [`aih_municio.csv`](../data/raw/aih_municio.csv) — série mensal em formato largo por município, de 2008 a set/2026. O nome original está escrito “municio”, sem “p”.

## 4. Tratamento e preparação dos dados

**Pasta:** `src/tratamento_dados/`.

- [`utils_tratamento.py`](../src/tratamento_dados/utils_tratamento.py) — funções compartilhadas para leitura e limpeza dos CSVs, identificação de colunas mensais, conversão de valores e transformação do formato largo para longo.
- [`tratar_internacoes.py`](../src/tratamento_dados/tratar_internacoes.py) — normaliza as UFs, remove a linha de total, transforma os meses em registros e salva a base tratada por UF.
- [`tratar_aih_municipio.py`](../src/tratamento_dados/tratar_aih_municipio.py) — separa código e nome dos municípios, deriva UF, transforma os meses em registros e salva a base tratada municipal.
- [`t.ipynb`](../src/tratamento_dados/t.ipynb) — notebook exploratório antigo, útil como referência do início do tratamento. Ele tenta ler `data_sus2.csv`, arquivo que não aparece no inventário atual; os scripts acima são o fluxo de tratamento vigente.

## 5. Bases preparadas para análise

**Pasta:** `data/processed/`. Arquivos gerados pelos scripts de tratamento; não são a fonte original.

- [`internacoes_tratado.csv`](../data/processed/internacoes_tratado.csv) — formato longo com `codigo_uf`, `estado`, `data` e `valor`; 6.048 registros, até ago/2026.
- [`aih_municipio_tratado.csv`](../data/processed/aih_municipio_tratado.csv) — formato longo com `codigo_municipio`, `municipio`, `codigo_uf`, `uf`, `data` e `valor`; 814.275 registros, até set/2026.

Nos CSVs originais, `-` e campos vazios são convertidos em zero pelo tratamento. Para a série por UF, o app/modelo interpreta zeros como ausências em determinadas análises; essa diferença deve ser considerada ao alterar a limpeza.

## 6. Análise exploratória (EDA)

**Pasta:** `src/eda/`.

- [`eda_internacoes_uf.ipynb`](../src/eda/eda_internacoes_uf.ipynb) — analisa qualidade dos dados, tendência nacional, pandemia, sazonalidade, crescimento e concentração por UF e variação entre estados.
- [`eda_aih_municipio.ipynb`](../src/eda/eda_aih_municipio.ipynb) — analisa qualidade e concentração municipal, municípios sem internações, perfil por volume, crescimento, peso do maior município por UF e variações atípicas.

## 7. Modelagem preditiva

**Pasta:** `src/models/`.

- [`regressao.ipynb`](../src/models/regressao.ipynb) — notebook de previsão mensal de internações por UF. Cria preditoras temporais, faz divisão cronológica treino/holdout, compara baselines e modelos supervisionados, calcula métricas, valida no treino e apresenta gráficos e análise. É a referência metodológica do modelo usado no app.

## 8. Aplicação para visualização

**Pasta:** `app/`.

- [`app.py`](../app/app.py) — interface Streamlit. Reúne as abas **Previsão** e **Insights**, filtros de estado/horizonte/período, indicadores, gráficos e tabelas.
- [`previsao.py`](../app/previsao.py) — carrega os dados por UF, constrói as variáveis defasadas e médias móveis, treina o Ridge, gera previsões recursivas e calcula indicadores e faixa aproximada de incerteza.
- [`insights.py`](../app/insights.py) — funções analíticas da aba Insights: totais, sazonalidade, crescimento, concentração e estatísticas municipais.

O app usa internações hospitalares do SIH como aproximação da pressão sobre o sistema. Isso **não mede diretamente a lotação ou a fila de UPAs/UBSs**. As bases de INMET, IBGE e dados operacionais de UPA/UBS ainda não aparecem em `data/`.

## 9. Arquivos gerados automaticamente

**Pastas:** `app/__pycache__/` e `src/tratamento_dados/__pycache__/`.

São caches de bytecode Python, não código-fonte nem entradas do projeto:

- `app/__pycache__/`: `app.cpython-312.pyc`, `insights.cpython-312.pyc`, `insights.cpython-313.pyc`, `previsao.cpython-312.pyc` e `previsao.cpython-313.pyc`.
- `src/tratamento_dados/__pycache__/`: `tratar_aih_municipio.cpython-312.pyc`, `tratar_internacoes.cpython-312.pyc`, `utils_tratamento.cpython-312.pyc` e `utils_tratamento.cpython-313.pyc`.

## Pastas do projeto

Organizadas pelas etapas descritas acima:

1. `.` — página inicial, configuração e guia do projeto.
2. `.streamlit/` — configuração visual e de execução do app.
3. `docs/` — contexto, requisitos e este relatório.
4. `data/raw/` — fontes originais.
5. `src/tratamento_dados/` — scripts e notebook de preparação.
6. `data/processed/` — dados tratados.
7. `src/eda/` — notebooks exploratórios.
8. `src/models/` — notebook de modelagem.
9. `app/` — aplicação e módulos de cálculo.
10. `app/__pycache__/` e `src/tratamento_dados/__pycache__/` — caches gerados pelo Python.

## Como executar

Na raiz do repositório:

```bash
venv/bin/streamlit run app/app.py
```

Para regenerar os CSVs processados:

```bash
venv/bin/python src/tratamento_dados/tratar_internacoes.py
venv/bin/python src/tratamento_dados/tratar_aih_municipio.py
```

Não foi encontrada uma pasta de testes no inventário. Para mudanças na preparação, modelagem ou app, consulte também as convenções e pendências em [`agents.md`](../agents.md).

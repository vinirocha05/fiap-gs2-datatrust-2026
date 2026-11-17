# Plano de Implementação: Integração com Dados Meteorológicos do INMET (Projeto FluxSUS)

**Data de elaboração:** 17/11/2026  
**Status:** Em execução / Referência técnica  
**Escopo:** Ingestão, tratamento e integração de séries meteorológicas históricas do INMET com os dados hospitalares do DATASUS (SIH) para o projeto FluxSUS (FIAP 2TSCO · CitizenTech).

---

## 1. Visão Geral e Motivação

O projeto **FluxSUS** prevê a antecipação de picos de demanda em unidades de saúde decorrentes de sazonalidade climática e eventos extremos (ex.: aumento de síndromes respiratórias após ondas de frio ou ar seco).

O modelo preditivo atual opera com regressão linear regularizada (Ridge) baseada puramente em histórico autorregressivo (`lag_1`, `lag_2`, `lag_3`, `lag_12`, médias móveis e mês). A integração com dados do INMET introduz **variáveis exógenas reais**, permitindo que o modelo capture variações atípicas que o simples mês do calendário não prevê.

### Diretriz Fundamental: Não Quebrar o Projeto Existente
1. Os dados brutos originais em `data/raw/` permanecem inalterados.
2. Os dados processados vigentes (`internacoes_tratado.csv` e `aih_municipio_tratado.csv`) continuam existindo e mantendo seus esquemas intactos.
3. A nova base meteorológica consolidada reside em `data/processed/inmet_uf_mensal.csv`.
4. Todos os módulos preditivos e visuais devem implementar **fallback gracioso**: se o arquivo de clima estiver presente, as variáveis climáticas são utilizadas; se não estiver, o sistema opera no modo autorregressivo puro sem falhas.

---

## 2. Dicionário de Dados Meteorológicos (Base Consolidada)

Arquivo de saída: `data/processed/inmet_uf_mensal.csv`  
Granularidade: **Mensal por Unidade Federativa (UF)**  
Período histórico: **2008 a 2026** (alinhado ao DATASUS)

| Coluna | Tipo | Unidade | Descrição / Fórmula |
| :--- | :---: | :---: | :--- |
| `codigo_uf` | int | - | Código numérico IBGE do estado (11 a 53). Chave de ligação com DATASUS. |
| `uf` | str | - | Sigla da UF (SP, RJ, MG, etc.). |
| `data` | date | YYYY-MM-01 | Primeiro dia do mês correspondente às medições. |
| `temp_media` | float | °C | Média mensal da temperatura horária do ar de bulbo seco. |
| `temp_min_media` | float | °C | Média mensal das temperaturas mínimas diárias. |
| `temp_min_abs` | float | °C | Menor temperatura absoluta registrada no mês na UF (frio extremo). |
| `temp_max_media` | float | °C | Média mensal das temperaturas máximas diárias. |
| `umidade_media` | float | % | Média mensal da umidade relativa do ar horária. |
| `umidade_min_media`| float | % | Média mensal da umidade relativa mínima diária. |
| `precipitacao_total`| float | mm | Volume acumulado de chuva no mês (média entre estações da UF). |
| `amplitude_termica` | float | °C | Diferença entre `temp_max_media` e `temp_min_media`. |

---

## 3. Etapas Lógicas de Implementação (Priorizadas por Criticidade)

A execução foi ordenada das tarefas de maior dependência de infraestrutura/rede (críticas) para as de modelagem e interface (que qualquer IA convencional consegue finalizar a partir dos dados prontos).

### Etapa 1 [CRÍTICA]: Script de Extração e Tratamento em Streaming
* **Objetivo:** Baixar os arquivos anuais compactados oficiais do INMET (`https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip`), ler os CSVs das estações diretamente da memória (sem inflar o disco com gigabytes de dados brutos) e agregar em nível mensal por UF.
* **Arquivo:** `src/tratamento_dados/tratar_inmet.py`
* **Cuidados técnicos:**
  * Padrão numérico brasileiro: separador de campo `;`, decimal com vírgula `,`.
  * Cabeçalho de metadados: as primeiras 8 linhas de cada CSV contêm dados da estação (UF, latitude, longitude, etc.); a linha 9 em diante contém os registros horários.
  * Valores ausentes ou códigos de falha de sensor (`-9999` ou vazios) devem ser convertidos em `NaN`.
  * Conversão da sigla da UF para o código IBGE padrão (tabela `SIGLA_PARA_IBGE`).

### Etapa 2 [CRÍTICA]: Geração do Dataset Processado
* **Objetivo:** Executar o script de tratamento para gerar `data/processed/inmet_uf_mensal.csv`.
* **Critério de Aceite:**
  * Arquivo gerado em formato longo ordenado por `codigo_uf` e `data`.
  * Volume final em torno de **~400 KB** (cerca de 6.000 linhas).
  * Sem valores infinitos; nulos tratados de forma transparente.

### Etapa 3 [INTERMEDIÁRIA]: Enriquecimento de Recursos (Feature Engineering)
* **Objetivo:** Criar a rotina de fusão (`merge`) entre `internacoes_tratado.csv` e `inmet_uf_mensal.csv`.
* **Local:** `src/tratamento_dados/utils_tratamento.py` ou diretamente em `app/previsao.py`.
* **Features Derivadas:**
  * Lags climáticos: `lag_1_temp_min` (o frio do mês anterior refletindo no mês seguinte).
  * Variação de temperatura: `delta_temp_1m = temp_media - lag_1_temp_media` (choque térmico).
  * Lags de umidade: `lag_1_umidade_min`.

### Etapa 4 [INTERMEDIÁRIA]: Retreino e Comparação dos Modelos de ML
* **Objetivo:** Atualizar e documentar a avaliação preditiva no notebook `src/models/regressao.ipynb`.
* **Critério de Aceite:**
  * Comparar Ridge original (MAE baseline ~1.500) com Ridge + Features Climáticas.
  * Validação cruzada temporal (`TimeSeriesSplit`) no treino (até 2023) e avaliação cega no holdout (2024–2026).
  * Gerar gráfico de importância de variáveis com as features de clima incluídas.

### Etapa 5 [INTERFACE]: Atualização do Dashboard Streamlit
* **Objetivo:** Exibir a influência climática para os gestores de saúde pública.
* **Arquivos:** `app/app.py`, `app/previsao.py`, `app/insights.py`.
* **Componentes a adicionar:**
  * Na aba **Previsão**: Incorporar as variáveis climáticas na projeção quando disponíveis.
  * Na aba **Insights**: Novo painel "Clima e Sazonalidade", com correlação entre temperatura mínima/umidade e picos de internações, reforçando o caso de uso do FluxSUS.

### Etapa 6 [GOVERNANÇA]: Atualização de Documentação e Guias
* **Objetivo:** Manter a consistência do repositório conforme `agents.md`.
* **Arquivos a atualizar:**
  * `agents.md` (registro de decisões e novos datasets).
  * `README.md` (instruções atualizadas de execução).
  * `docs/contexto.md` (preencher o fluxo de dados na Parte 2: Pipeline).

---

## 4. Guia para Continuidade em Modelos de IA Convencionais

Caso a sessão atual termine ou seja necessário continuar o desenvolvimento em plataformas de IA conversacional (como ChatGPT, Claude ou Gemini Web), siga este roteiro:

1. **Contexto a fornecer para a IA:**
   * "Estou desenvolvendo o projeto **FluxSUS** (previsão de internações do SUS por UF com dados do DATASUS e clima do INMET)."
   * "Os dados tratados estão disponíveis em `data/processed/internacoes_tratado.csv` e `data/processed/inmet_uf_mensal.csv`."
   * "O arquivo `docs/plano_implementacao_inmet.md` contém o plano mestre do projeto."
2. **Para trabalhar na Modelagem (Etapa 4):**
   * Peça: *"Atualize a função `calcular_variaveis` para fazer o left merge com `inmet_uf_mensal.csv`, crie os lags climáticos `lag_1_temp_min` e `lag_1_umidade_min` e reavalie o Ridge e o GradientBoosting com TimeSeriesSplit."*
3. **Para trabalhar no Streamlit (Etapa 5):**
   * Peça: *"No arquivo `app/insights.py`, crie uma função `correlacao_clima_internacoes(df_internacoes, df_clima)` e adicione um gráfico Plotly de eixo duplo (internações vs temperatura mínima) na aba Insights do `app/app.py`."*
4. **Comandos de Terminal Úteis:**
   * Rodar o tratamento do INMET: `venv/bin/python src/tratamento_dados/tratar_inmet.py`
   * Testar o dashboard: `venv/bin/streamlit run app/app.py`
   * Reexecutar notebook: `venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace src/models/regressao.ipynb`

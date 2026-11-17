## Parte 1: Estrutura da Proposta Executiva (PDF baseado no Template)

Organize os slides do template (`GS_2026_2_-_2TSCO_template.pptx`) seguindo a lógica abaixo[cite: 2]:

### 1. Identificação e Nome do Projeto (Slides 1 e 2)

- **Nome do projeto:** FluxSUS (acompanhado de um logotipo limpo)[cite: 2].
- **Identificação:** Informar a turma, listar os integrantes em ordem alfabética (Nome completo + RM) e destacar o aluno responsável[cite: 2].

### 2. Contextualização e Recorte do Problema (Slide 3)

- **Problema e Território:** Superlotação e imprevisibilidade de demanda em Unidades de Pronto Atendimento (UPAs) e Unidades Básicas de Saúde (UBSs) em regiões metropolitanas (ex.: Grande São Paulo ou município específico da base de dados escolhida)[cite: 2].
- **Evidências e Fontes:** Utilizar dados do **DATASUS** (histórico de atendimentos ambulatoriais/internações) e do **Mapa da Desigualdade** (Instituto Cidades Sustentáveis) para demonstrar a disparidade no tempo de espera e na distribuição de leitos/equipes por distrito[cite: 2].
- **Persona Afetada:** Cidadão trabalhador ou idoso dependente do SUS que busca atendimento de baixa/média complexidade, enfrenta horas de fila sem previsão e, muitas vezes, se desloca até uma unidade colapsada quando outra unidade próxima possui menor fluxo[cite: 2].

### 3. Proposta de Solução CitizenTech (Slide 4)

- **O que é:** Uma plataforma integrada de inteligência preditiva que antecipa picos de demanda nas unidades de saúde e traduz essa informação em dois canais[cite: 2]:
  - **Painel de Gestão (B2G/Operacional):** Alerta gestores municipais sobre picos previstos (ex.: aumento de síndromes respiratórias após quedas bruscas de temperatura), permitindo o remanejamento preventivo de plantonistas e estoques[cite: 2].
  - **Canal Cidadão (B2C/Inclusivo):** Consulta rápida de lotação estimada por unidade e triagem orientativa (indicando se o caso exige UPA ou UBS e qual unidade próxima está mais livre)[cite: 2].
- **Acessibilidade e Baixa Conectividade (Critério Obrigatório):** Para atender cidadãos com pouco letramento digital, idosos ou baixa conectividade, a solução oferece consulta via **bot de WhatsApp/SMS** com respostas de texto simples e áudio, além de integração com painéis físicos nas recepções das UBSs e totens comunitários[cite: 2].

### 4. Benefícios, Impactos e ODS da ONU (Slides 5, 6 e 7)

- **Impactos e Indicadores (KPIs):** Redução do tempo médio de espera na triagem, diminuição da taxa de evasão de pacientes (desistência por demora) e otimização da taxa de ocupação entre unidades da mesma região[cite: 2].
- **ODS Atendidos (Foco em 3 principais):**
  - **ODS 3 (Saúde e Bem-Estar):** Amplia a eficiência e a resolutividade do atendimento primário e de urgência[cite: 2, 3].
  - **ODS 10 (Redução das Desigualdades):** Garante acesso equitativo à informação de saúde em regiões periféricas e com menor cobertura digital[cite: 2, 3].
  - **ODS 11 (Cidades e Comunidades Sustentáveis):** Melhora a gestão de serviços públicos essenciais e reduz deslocamentos urbanos desnecessários[cite: 2, 3].

### 5. Tecnologias e Arquitetura da Solução (Slides 8 e 9)

- **Fluxo de Dados (Diagrama):**
  - **Ingestão:** Extração de séries históricas do DATASUS (SIA/SIH), dados meteorológicos do INMET e dados demográficos do IBGE[cite: 2].
  - **Armazenamento e Processamento:** Data Lake (ex.: AWS S3 ou Azure Blob Storage) + scripts de ETL e modelagem em Python (Pandas, Scikit-learn)[cite: 2].
  - **Consumo/Visualização:** Banco relacional (PostgreSQL/SQL Database) alimentando dashboards em Power BI / Streamlit (para gestores) e API conectada a bot de mensagens (para cidadãos)[cite: 2].

### 6. Protótipo e Uso Responsável dos Dados (Slides 10 e 12)

- **Protótipo (Baixa Fidelidade):** Apresentar duas telas principais:
  1. Dashboard gerencial com curva de previsão de atendimentos para os próximos 7 dias e alerta de capacidade[cite: 2];
  2. Tela de celular/WhatsApp mostrando o "Semáforo de Lotação" das unidades do bairro[cite: 2].
- **LGPD e Ética:** O sistema opera exclusivamente com dados agregados e anonimizados (volume de atendimentos por CID/faixa etária/unidade), sem armazenar CPF ou prontuário individual[cite: 2].
- **Mitigação de Vieses:** Evitar que o modelo subestime a demanda de bairros periféricos onde o sub-registro histórico ocorre por falta de unidades locais (cruzando dados de atendimento com densidade populacional do IBGE)[cite: 2].

---

## Parte 2: Pipeline de Dados e Modelagem (Implementado)

### 1. Ingestão e Tratamento (`src/tratamento_dados/`)
- **DATASUS (SIH):** Conversão das matrizes originais (`data/raw/internacoes.csv` e `data/raw/aih_municio.csv`) para formato longo padronizado em `data/processed/internacoes_tratado.csv` (mensal por UF) e `data/processed/aih_municipio_tratado.csv` (mensal por município).
- **INMET (Meteorologia):** Extração automatizada via streaming dos pacotes anuais históricos (2008 a 2026) de mais de 500 estações meteorológicas, com agregação diária e mensal por UF (`data/processed/inmet_uf_mensal.csv`, ~366 KB).

### 2. Engenharia de Recursos e Modelagem Preditiva (`src/models/` e `app/previsao.py`)
- **Variável-alvo:** Volume mensal de internações hospitalares por UF (`valor`).
- **Estratégias Comparadas:**
  1. **Baseline Inercial (Sem Clima):** Regressão Ridge sobre defasagens recentes (`lag_1`, `lag_2`, `lag_3`) e médias móveis (`media_3m`, `media_12m`).
  2. **Modelo Refinado com Clima (INMET + Sazonalidade):** Regressão Ridge enriquecida com anomalias de frio, secura do ar, amplitude térmica e choque térmico ponderadas pelo porte hospitalar da UF (`media_12m`), reduzindo o erro absoluto médio (MAE) no holdout (2024–2026) de **1.762 para 1.452 internações/mês**.
- **Correlação Dessazonalizada:** Isolamento da pressão sazonal (`desvio % sobre a média anual`) para remover o viés do crescimento demográfico de 18 anos, revelando forte correlação negativa entre temperatura mínima e internações ($r = -0,57$ mensal e $r = -0,76$ a $-0,86$ no ciclo anual no Centro-Sul).

### 3. Visualização e Suporte à Decisão (`app/`)
- **Dashboard Streamlit (`app/app.py`):** Organizado em 4 abas temáticas (`📈 Previsão`, `🌡️ Clima & INMET`, `🗺️ Municípios & Território` e `💡 Panorama Macro`), com suporte à visão nacional consolidada (`Brasil - Todos os estados`) e filtro temporal integrado.


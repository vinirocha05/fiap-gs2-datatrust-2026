# agents.md — Guia para agentes (CitizenTech · Saúde Pública)

> Memória compartilhada entre sessões. Leia inteiro antes de agir e **atualize ao final de cada sessão** (seção 10).

## 1. Visão geral
- **Trabalho:** Global Solution 2026/2 · FIAP · turma 2TSCO · tema **CitizenTech** (Data Science + inovação para resolver um problema real do cidadão).
- **Área:** dados de saúde pública no Brasil (DATASUS).
- **Projeto:** **FluxSUS** · Grupo: **A definir** · Aluno responsável: **A definir** · Prazo: **A definir**.
- **3 entregas:** (1) proposta executiva em PDF, (2) vídeo pitch ≤ 5 min, (3) entrega técnica de Machine Learning (.zip).

## 2. Fonte de verdade
- [docs/contexto.md](docs/contexto.md): recorte e estrutura da proposta escolhida pelo time.
- [docs/requisitos_entrega.md](docs/requisitos_entrega.md): enunciado e critérios de aceite.
- Se houver conflito, o enunciado vence. Mudou um requisito: atualize o doc em `docs/` e depois este arquivo.
- A seção "Parte 2: Pipeline" do `contexto.md` foi preenchida e documenta o fluxo implementado.

## 3. Recorte do problema (resumo)
- **Problema:** superlotação e imprevisibilidade de demanda em UPAs/UBSs de regiões metropolitanas (ex.: Grande SP).
- **Persona:** cidadão trabalhador ou idoso dependente do SUS, com casos de baixa/média complexidade, que enfrenta filas sem previsão.
- **Fontes:** DATASUS (SIA/SIH), INMET (clima), IBGE (demografia), Mapa da Desigualdade.
- **Solução:** painel de gestão (B2G) com previsão de picos + canal do cidadão (B2C) com semáforo de lotação via bot WhatsApp/SMS (texto simples e áudio) e totens.
- **ODS:** 3, 10 e 11.
- **KPIs:** tempo médio de espera na triagem, taxa de evasão, taxa de ocupação entre unidades.
- **Ética:** só dados agregados e anonimizados (LGPD); mitigar subnotificação em bairros periféricos cruzando com densidade populacional (IBGE).

## 4. Checklist de aceite
**PDF** `GS_2TSCOA_Pitch_<projeto>_<grupo>.pdf` (a partir do template `GS_2026_2_-_2TSCO_template.pptx`):
- [ ] 1 Identificação (turma, projeto, integrantes em ordem alfabética com RM, responsável)
- [ ] 2 Contextualização e recorte (problema, território, evidências, persona)
- [ ] 3 Público beneficiado e ecossistema
- [ ] 4 Proposta de solução (inclui acessibilidade para baixa conectividade/letramento/deficiência)
- [ ] 5 Benefícios, indicadores e ODS (poucos ODS, com justificativa)
- [ ] 6 Arquitetura e tecnologias (diagrama do fluxo de dados)
- [ ] 7 Protótipo (baixa fidelidade)
- [ ] 8 Uso responsável dos dados (LGPD, segurança, vieses)
- [ ] 9 Link do vídeo na última página

**Vídeo:**
- [ ] ≤ 5 min, YouTube **público**, link abre sem pedir permissão
- [ ] `linkvideo.txt` (equipe, turma, RMs e nomes em ordem alfabética, link)

**ML** `GS_2TSCOA_ML_<projeto>_<grupo>.zip` (notebook `.ipynb` **executado, com saídas visíveis** + CSV(s) ou TXT com link direto):
- [ ] 10 Título e descrição do problema (e ligação com a 1ª parte)
- [ ] 11 Dataset descrito, fonte, **variável-alvo** e **preditoras** explícitas
- [ ] 12 Pré-processamento (limpeza, ausentes, seleção/transformação)
- [ ] 13 Divisão treino/teste; CV só no treino; pré-processamento ajustado só no treino; **ordem cronológica** em séries temporais
- [ ] 14 Pelo menos 2 modelos supervisionados
- [ ] 15 Métricas adequadas (RMSE/MAE/R² ou Accuracy/Precision/Recall/F1)
- [ ] 16 Visualizações (importância de variáveis, comparação de modelos, matriz de confusão se classificação)
- [ ] 17 Conclusão (modelo escolhido, justificado por métricas e contexto)
- [ ] 18 Texto analítico (escolhas, limitações, vieses, contribuição à decisão)

## 5. Estrutura do repositório e dados
```
agents.md                  este guia
docs/                      contexto.md, requisitos_entrega.md
data/raw/                  dados originais (imutáveis)
data/processed/            internacoes_tratado.csv, aih_municipio_tratado.csv
src/tratamento_dados/      t.ipynb (exemplo), utils_tratamento.py, tratar_internacoes.py, tratar_aih_municipio.py
src/eda/                   eda_internacoes_uf.ipynb, eda_aih_municipio.ipynb (análise exploratória, executados)
src/models/regressao.ipynb notebook de regressão (executado)
app/                       app Streamlit: app.py (interface, abas Previsão e Insights), previsao.py (dados, modelo, previsão), insights.py (cálculos dos insights)
.streamlit/config.toml     tema escuro do app
venv/                      ambiente virtual (deps em requirements.txt)
requirements.txt           versões instaladas no venv
```
- `data/raw/internacoes.csv`: separador `;`, formato **largo** (27 UFs + linha "Total"; colunas `2008/Jan` … `2026/Ago`); coluna `estado` traz código + nome (ex.: "35 São Paulo"). É apenas análise exploratória inicial; **mais dados virão em `data/`**.
- `data/raw/aih_municio.csv` (nome sem o "p"): 3619 municípios + linha "Total", mesmas colunas mensais até `2026/Set`; `-` (120.424 células) significa zero.
- Tratamento: `venv/bin/python src/tratamento_dados/tratar_internacoes.py` e `tratar_aih_municipio.py` geram CSVs em formato longo (`data` datetime, `valor` int, sem "Total", `-`→0). Saídas: `internacoes_tratado.csv` (`codigo_uf, estado, data, valor`; 6048 linhas) e `aih_municipio_tratado.csv` (`codigo_municipio, municipio, codigo_uf, uf, data, valor`; 814.275 linhas). Soma mensal validada contra a linha "Total" original.
- Git: ainda sem commits.

## 6. Convenções
- Idioma: **português do Brasil** em textos, comentários e docstrings.
- Nomes de arquivos de entrega exatamente como no enunciado.
- `data/raw` nunca é editado; todo tratamento gera saída em `data/processed`.
- Sem dados pessoais (CPF, prontuário); só agregados.
- Reprodutibilidade: `random_state=42`.
- Notebooks entregues executados do início ao fim (Restart & Run All) com saídas visíveis.
- Preservar comentários e docstrings existentes não relacionados à alteração.

## 7. Regras de ML
- Sem vazamento: imputação, escala e codificação dentro de `Pipeline` ajustado só no treino.
- Séries temporais: divisão cronológica (sem embaralhar) e `TimeSeriesSplit` na validação cruzada do treino.
- Teste usado apenas na avaliação final.
- Comparar ao menos 2 modelos e um baseline simples (ex.: média móvel ou último valor).
- Escolha de métrica justificada pelo custo do erro (falso alerta vs. caso não detectado).
- Alvo: internações do mês seguinte por UF (`internacoes_tratado.csv`). Preditoras: `lag_1/2/3/12`, `media_3m/12m`, `mes`, `codigo_uf`. Escopo e dados novos (INMET/IBGE) ainda **A definir**.

## 8. Ambiente
- Python em `venv/` com pandas, scikit-learn, matplotlib, seaborn, ipykernel, nbformat, nbconvert, streamlit e plotly (aprovado pelo time); versões em `requirements.txt`.
- Rodar o app: `venv/bin/streamlit run app/app.py`.
- Reexecutar o notebook: `venv/bin/python -m jupyter nbconvert --to notebook --execute --inplace src/models/regressao.ipynb` (idem para `src/eda/*.ipynb`).
- Novos pacotes: pedir aprovação antes de instalar.

## 9. Comportamento do agente
- Respostas concisas, em português, em markdown.
- Tarefas não triviais: pesquisar, planejar (`/plan`) e obter aprovação antes de mudar código.
- Ambiguidade: perguntar em vez de assumir.
- Links clicáveis para arquivos citados.

## 10. Registro de decisões e aprendizados
- **2026-11-14** — Primeira sessão: leitura de `docs/`, inventário do repo e criação deste guia. Notebook `regressao.ipynb` e `contexto.md` (Parte 2) estavam vazios/pendentes. Decisões sobre alvo do modelo, prazo e dependências não foram respondidas e ficam em aberto.
- **2026-11-14** — Criados scripts de tratamento em `src/tratamento_dados/` (só pandas) e CSVs em `data/processed/`. Períodos diferem: internações vai até 2026/Ago, AIH municipal até 2026/Set.
- **2026-11-14** — Criado `regressao.ipynb`: modelo global das 27 UFs, split cronológico (treino até 2023-12, holdout 2024-01 a 2026-08), `TimeSeriesSplit` no treino, baselines (último mês e mesmo mês do ano anterior), Ridge, Random Forest e Gradient Boosting. Melhor: **Ridge** (MAE 1.500, RMSE 2.920, MAPE 5,6% no holdout; baseline último mês MAE 1.755). Modelo escolhido pela CV, não pelo teste.
- **2026-11-14** — Qualidade dos dados: zeros de UF/mês (Acre 2009-09 e 2026-08, Roraima 2026-08) são dado ausente, tratados como NaN no notebook. Roraima 2026-07 (515) parece mês incompleto. `-` do raw vira 0 no tratamento, mas em séries de UF isso é ausência.
- **2026-11-14** — Criado app Streamlit em `app/`: escolha da UF, histórico com filtro de ano, previsão de 1 a 12 meses (Ridge treinada no app com todo o histórico, previsão recursiva, faixa de ~80% baseada no erro relativo de 1 passo no holdout, crescendo com √horizonte) e cartões de indicadores. Meses finais com valor < 40% da mediana dos 12 anteriores (ou vazios) são ignorados e o app avisa (Roraima jul/ago 2026, Acre ago/2026). Testado com `AppTest` (sem navegador: o browser automatizado não funciona neste ambiente). Fora do escopo por ora: ranking entre UFs, sazonalidade, mapa, qualidade do modelo e download CSV.
- **2026-11-14** — Criada `src/eda/` (dois notebooks) e aba **Insights** no app. Achados: crescimento de 1,1% a.a. até 2019 e 6,0% a.a. desde 2021 (2025 = +19% sobre 2019); maior queda em abr/2020 (-18,9%); pico sazonal em mai/jul/ago/out e vale em fev/dez/jan; 5 UFs = 51% das internações; 96 municípios = 50%; 13% dos municípios sem internação em 2025 (base é pelo município da internação, não o de residência). Cuidados: há municípios homônimos em UFs diferentes (usar nome+UF ou código); ago e set/2026 estão incompletos no nível municipal; 2020 e 2021 ficam fora das médias sazonais. Nomes de município no CSV não têm acento. No app, `use_container_width`/`width="stretch"` varia entre versões do Streamlit (o Python global tinha a 1.45; use sempre o `venv`).
- **2026-11-15** — Repositório clonado na pasta de trabalho; criado `venv/` com Python 3.12.3 e dependências do `requirements.txt`. O arquivo passou a registrar as versões resolvidas das dependências diretas e transitivas. Criado `.gitignore` para o ambiente virtual, caches de Python/notebooks e segredos do Streamlit. `pip check`, imports principais e smoke test do app via `AppTest` passaram.
- **2026-11-16** — Criado `docs/relatorio_arquivos_projeto.md`, inventário dos arquivos e pastas por etapa. Notebooks foram inspecionados por cópias temporárias convertidas com `nbconvert`, sem modificar os originais ou instalar Jupytext.
- **2026-11-16** — Reformatado `docs/requisitos_entrega.md` com hierarquia de títulos, listas e espaçamento; texto original preservado.
- **2026-11-16** — Criado `README.md` como página inicial do repositório, com navegação relativa pelas etapas, tecnologias, limitações, preparo do ambiente e execução do dashboard.
- **2026-11-16** — Definido o nome do projeto como **FluxSUS** e atualizado nos documentos e no título do dashboard Streamlit.
- **2026-11-17** — Elaborado o plano mestre de integração em `docs/plano_implementacao_inmet.md`. Criado o pipeline automatizado de ingestão e agregação meteorológica em `src/tratamento_dados/tratar_inmet.py` (leitura em streaming de ZIPs anuais, agregação diária e mensal por UF, conversão para códigos IBGE). Executado e validado o piloto de 2024 e concluída com sucesso a consolidação histórica completa de 2008 a 2026 em `data/processed/inmet_uf_mensal.csv` (5.972 registros, 366.2 KB, cobrindo as 27 UFs). Integradas funções analíticas em `app/insights.py` e gráfico comparativo com correlações em `app/app.py`, validado com sucesso via `AppTest` (sem quebras no projeto original).
- **2026-11-17** — [Tarefa 6 e 3] Refinamento preditivo no Streamlit: implementada a inclusão de variáveis meteorológicas do INMET (`lag_1_temp_min`, `delta_temp`, `lag_1_umidade`, `temp_min_normal`) no Ridge com imputação robusta via `SimpleImputer`. No holdout nacional, o modelo com clima reduziu o MAE de 1.499,65 para 1.477,92 (-21,73 internações). O dashboard agora exibe modo comparativo sobreposto (Previsão com Clima vs Baseline sem Clima), cálculo do impacto térmico médio e tabela discriminada. Os gráficos históricos climáticos agora respeitam o slider "Histórico a partir de". Validado com 0 erros via `AppTest`. Commit `ca4b8ff` registrado.
- **2026-11-17** — [Tarefa 4 - Opção B] Reestruturação da interface em 4 abas lógicas temáticas: (1) `📈 Previsão` (projeção recursiva, comparativo com/sem clima e tabela discriminada); (2) `🌡️ Clima & INMET` (painel dedicado com cartões de frio extremo e ar seco, série temporal de eixo duplo internações x temperatura, dispersão scatter com linha de tendência linear e normal climatológica sazonal com chuva x temperatura); (3) `🗺️ Municípios & Território` (curva de Pareto, maiores cidades, vazios assistenciais e dependência da capital); (4) `💡 Panorama Macro` (tendências pós-pandemia, sazonalidade comparativa Brasil x UF e matriz térmica das 27 UFs). Validado com `AppTest` para múltiplos estados com 0 erros.
- **2026-11-17** — [Tarefa 5] Adicionada a opção 'Brasil (Todos os estados)' no seletor de territórios do Streamlit. Na aba de previsão, gera a série nacional consolidada agregando as 27 UFs (~1,22 mi internações/mês) com comparação entre modelos com e sem clima. Nas abas de clima, municípios e panorama macro, exibe métricas e sazonalidades consolidadas para todo o país. Testado com `AppTest` para execução em nível nacional e estadual com 0 erros.
- **2026-11-17** — [Refinamento Estatístico, UI e Revisão Geral] (1) Diferenciação metodológica em `app/previsao.py`: o Baseline agora é um modelo puramente inercial (`lag_1..3`, `media_3m`, `media_12m`), enquanto o Modelo com Clima (INMET) utiliza anomalias de frio, secura, amplitude e choque térmico ponderadas pelo porte hospitalar da UF (`media_12m`), reduzindo o MAE no holdout de 1.762,5 para 1.452,6 (-309,9 internações/mês) e separando nitidamente as curvas de verão e inverno no gráfico; (2) Dessazonalização em `app/insights.py`: criado o Índice de Pressão Sazonal (`desvio % sobre a média anual`), eliminando o viés do crescimento demográfico de 18 anos (+35%) que mascarava a correlação bruta; a correlação com a temperatura mínima em SP salta de -0,24 para -0,57 (e -0,76 a -0,86 no ciclo anual do Centro-Sul), exibindo inclinação negativa clara no gráfico de dispersão; (3) Adicionada a logo `app/assets/logo_fluxsus.png` no topo da sidebar com proporção nativa preservada (263:104); (4) Padronizados todos os cartões (`.card`) em todas as abas com altura uniforme (`144px`) e centralização vertical/horizontal via Flexbox; (5) Revisão geral de documentação concluída (`README.md`, `docs/contexto.md` Parte 2 preenchida, `docs/relatorio_arquivos_projeto.md`).

## 11. Pendências e dúvidas em aberto
- [ ] Prazo, nome do grupo e aluno responsável.
- [ ] Alvo do modelo e escopo geográfico (UF nacional vs. Grande SP/UPA/UBS).
- [ ] Datasets adicionais para `data/` (INMET implementado; IBGE e SIA/SIH detalhado pendentes).
- [x] Aprovação para `requirements.txt` e instalação de dependências.
- [x] Preencher "Parte 2: Pipeline" em `docs/contexto.md`.

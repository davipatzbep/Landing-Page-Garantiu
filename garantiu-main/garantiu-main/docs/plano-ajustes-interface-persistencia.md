# Plano de implementação — interface, histórico e formatação

## Objetivo

Executar os ajustes visuais e funcionais solicitados para o Garantiu:

- remover fundos brancos dos elementos de marca;
- simplificar textos com aparência artificial, como `01 · PREPARAR RELEASE`;
- explicar melhor as entradas de qualidade da primeira página;
- persistir as evidências de bugs e incidentes por análise;
- permitir a exportação do histórico em CSV;
- iniciar o campo de repositório vazio;
- padronizar a apresentação de datas e scores.

Este documento é um roteiro de execução. Marque os itens conforme forem concluídos.

## Escopo e decisões

### Persistência

Usar SQLite como fonte principal do histórico e CSV apenas para importação e
exportação.

Essa decisão preserva a arquitetura existente: o projeto já usa SQLite para
decisões, execuções de testes, scores e resultados de releases. Usar apenas CSV
como banco principal dificultaria consultas, relacionamentos, deduplicação e
gravações atômicas.

### Histórico de bugs

No MVP, bugs continuam sendo identificados automaticamente pelo histórico Git.
O código atual considera commits cujas mensagens contêm termos como `fix`,
`bug` e `corrige`. Não será criado um formulário de cadastro manual de bugs
nesta entrega, para evitar duplicidade entre registros manuais e commits.

### Datas e scores

- Datas e timestamps permanecem armazenados em ISO 8601 e UTC.
- A conversão para o padrão brasileiro acontece somente na interface.
- Scores permanecem numericamente como `float` entre 0 e 100.
- A interface apresenta sempre uma casa decimal, por exemplo `82,5 / 100`.
- Gráficos continuam recebendo valores numéricos, sem formatação textual.

## Estado atual confirmado

- `garantiu-logo-full.jpeg` possui fundo branco porque JPEG não suporta
  transparência.
- `garantiu-symbol.png` e `garantiu-wordmark.png` já possuem canal de
  transparência.
- O CSS adiciona fundos claros ao logo, ao símbolo das páginas e ao logo do
  rodapé.
- As sete páginas usam um cabeçalho numerado no formato `NN · AÇÃO`.
- O campo de repositório recebe `.` como valor inicial.
- JUnit e incidentes são fornecidos na primeira página, dentro de “Dados
  adicionais de qualidade”.
- Bugs são extraídos automaticamente do Git, não de um arquivo enviado pelo
  usuário.
- Scores, testes e decisões já são persistidos localmente, mas as evidências
  detalhadas de bugs e incidentes não são preservadas por análise.

## Fase 1 — Helpers de apresentação

### Implementação

- [x] Adicionar em `garantiu/ui.py`:
  - [x] `format_score(value)`;
  - [x] `format_date_br(value)`;
  - [x] `format_datetime_br(value, timezone_name="America/Sao_Paulo")`.
- [x] Usar `zoneinfo.ZoneInfo`, disponível na biblioteca padrão do Python.
- [x] Fazer os helpers aceitarem strings ISO, `date` e `datetime`, conforme a
  necessidade real dos chamadores.
- [x] Caso exista um valor legado inválido, devolver o texto original em vez
  de interromper a página.
- [x] Não alterar os valores armazenados no banco.

### Padrões visuais

| Tipo | Formato |
|---|---|
| Data | `10/09/2026` |
| Data e hora | `10/09/2026 14:35` |
| Score | `82,5 / 100` |
| Percentual | `82,5%` |

### Testes

- [x] Criar testes unitários para data sem horário.
- [x] Criar testes para timestamp UTC convertido para São Paulo.
- [x] Criar teste para valor ISO com e sem offset.
- [x] Criar teste para valor legado inválido.
- [x] Criar testes de score inteiro e decimal.
- [x] Confirmar que os limites de risco 40 e 70 não foram alterados.

## Fase 2 — Campo de repositório vazio

### Implementação

- [x] Alterar o valor inicial de `repository_source` de `"."` para `""` em
  `app.py`.
- [x] Manter a persistência do valor ao navegar entre as páginas.
- [x] Manter a limpeza da análise quando o usuário troca de repositório.
- [x] Não consultar o histórico enquanto o campo estiver vazio.
- [x] Exibir uma mensagem clara ao tentar analisar sem informar o repositório.

### Testes

- [x] Atualizar o teste de pipeline completo para preencher explicitamente o
  caminho do repositório usado no teste.
- [x] Testar que a aplicação inicia com o campo vazio.
- [x] Testar a validação ao clicar em “Analisar mudanças” com o campo vazio.
- [x] Revalidar a navegação entre “Conectar release” e “Histórico & tendências”.

## Fase 3 — Revisão dos textos

### Implementação

- [x] Simplificar `render_page_header()` para receber somente título e
  descrição.
- [x] Remover da interface:
  - [x] `01 · PREPARAR RELEASE`;
  - [x] `02 · AVALIAR RELEASE`;
  - [x] `03 · DIRECIONAR TESTE`;
  - [x] `04 · PRIORIZAR AUTOMAÇÃO`;
  - [x] `05 · EXPLICAR RISCO`;
  - [x] `06 · DECIDIR`;
  - [x] `07 · APRENDER`;
  - [x] `FLUXO DA RELEASE` na tela bloqueada.
- [x] Remover a classe `.page-eyebrow` do CSS.
- [x] Alterar “Fluxo da release” para “Etapas da release”.
- [x] Revisar textos em caixa alta que não sejam siglas ou dados técnicos.

### Sugestões de substituição

| Texto atual | Texto sugerido |
|---|---|
| `RELEASE ANALISADA` | `Release analisada` |
| `FOCO RECOMENDADO` | `Onde testar primeiro` |
| `ARQUIVOS` | `Arquivos` |
| `MÓDULOS` | `Módulos` |
| `STATUS` | `Status` |

Os títulos funcionais atuais, como “Conectar release” e “Visão geral do
risco”, devem permanecer.

### Testes

- [x] Atualizar testes que dependem da assinatura de `render_page_header()`.
- [x] Criar uma asserção garantindo que nenhum HTML renderizado contenha o
  padrão de cabeçalho `NN · AÇÃO`.
- [x] Revisar as sete páginas em uma sessão completa do AppTest.

## Fase 4 — Imagens com fundo transparente

### Implementação

- [x] Parar de usar `garantiu-logo-full.jpeg` em `render_brand()`.
- [x] Montar o logo principal com `garantiu-symbol.png` e
  `garantiu-wordmark.png`.
- [x] Adaptar o wordmark para manter contraste no tema escuro:
  - criar uma versão transparente para fundo escuro; ou
  - aplicar um tratamento CSS aprovado visualmente.
- [x] Remover os fundos claros de:
  - [x] `.brand-full-crop`;
  - [x] `.sidebar-footer img`;
  - [x] `.page-brand-symbol`.
- [x] Remover bordas e sombras que ainda produzam aparência de caixa branca.
- [x] Manter textos alternativos adequados.
- [x] Após confirmar que não há referências, remover o JPEG antigo em uma
  alteração separada e recuperável.

### Critérios de aceite

- [x] Nenhuma imagem apresenta retângulo branco no tema escuro.
- [x] Símbolo e nome continuam legíveis.
- [x] Não existem halos brancos nas bordas transparentes.
- [x] A identidade visual continua legível em desktop e viewport estreito.
- [x] O ícone da página continua funcionando.

### Testes

- [x] Atualizar `tests/test_app_smoke.py` para não exigir o JPEG antigo.
- [x] Verificar no HTML que os assets usados são PNG.
- [x] Fazer inspeção visual real no navegador; AppTest não substitui esta
  validação.

## Fase 5 — Clareza dos dados adicionais de qualidade

### Conteúdo que deve ser explicado

| Fonte | Para que serve | Origem |
|---|---|---|
| JUnit XML | Status dos testes executados | Terminal ou CI |
| CSV de incidentes | Quantidade de incidentes por módulo | Histórico operacional da equipe |
| CSV de detalhes | Descrição e data dos incidentes | Histórico operacional da equipe |
| Histórico de bugs | Correções anteriores relacionadas aos arquivos | Extraído automaticamente do Git |

JUnit informa resultados de execução. Ele não representa cobertura de código.

### Implementação

- [x] Renomear o expander para “Resultados de testes e incidentes — opcional”.
- [x] Explicar cada entrada logo abaixo do respectivo campo.
- [x] Informar que o histórico de bugs é obtido automaticamente do Git.
- [x] Informar que a ausência de uma fonte não significa ausência de risco.
- [x] Exibir a configuração de armazenamento local na área de dados opcionais.
- [x] Localizar também os relatórios colocados na pasta de armazenamento.
- [x] Depois da análise, mostrar quais fontes foram utilizadas e quais estavam
  ausentes.

### Formatos de entrada

Contagem de incidentes:

```csv
module,incident_count
checkout,3
auth,1
```

Detalhes de incidentes:

```csv
module,description,date
checkout,Falha ao confirmar pagamento,2026-09-10
```

### Testes

- [x] Confirmar que os botões de download foram removidos.
- [x] Confirmar preenchimento automático para um candidato e escolha para vários.
- [x] Testar análise sem dados opcionais.
- [x] Testar análise com JUnit e os dois CSVs.

## Fase 6 — Persistência das evidências

### Banco selecionado

Adicionar as novas tabelas a `garantiu_release_history.db`. Não criar outro
banco para o mesmo domínio.

### Modelo proposto

#### `release_module_scores`

- `analysis_id`: referência ao registro em `release_scores`;
- `module`;
- `score`;
- `complexity_score`;
- `bug_score`;
- `test_health_score`;
- `incident_score`.

#### `release_bug_evidence`

- `analysis_id`;
- `module`;
- `file_path`;
- `commit_hash`;
- `message`;
- `occurred_on`.

#### `release_incident_counts`

- `analysis_id`;
- `module`;
- `incident_count`.

#### `release_incident_details`

- `analysis_id`;
- `module`;
- `description`;
- `occurred_on`.

### Regras

- [x] Usar chaves estrangeiras para relacionar as evidências ao score da
  análise.
- [x] Ativar `PRAGMA foreign_keys = ON` nas conexões responsáveis.
- [x] Criar índices para `analysis_id` e consultas por módulo.
- [x] Não alterar nem apagar os registros existentes.
- [x] Permitir que duas análises do mesmo intervalo sejam preservadas como
  snapshots distintos.
- [x] Continuar mostrando apenas a análise mais recente por release no resumo
  atual.
- [x] Gravar score, módulos, bugs e incidentes em uma única transação.
- [x] Se uma evidência for inválida, reverter toda a gravação da análise.

### Integração

- [x] Fazer `record_release_score()` continuar disponível para compatibilidade.
- [x] Criar uma operação de nível mais alto, como
  `record_release_analysis()`, responsável pela transação completa.
- [x] Usar o ID da análise na gravação dos módulos e evidências.
- [x] Não gravar caminhos temporários de clones do GitHub; usar sempre a
  `repo_key` normalizada.

### Testes

- [x] Migração sobre banco vazio.
- [x] Migração sobre banco já existente com scores e resultados.
- [x] Persistência dos quatro fatores por módulo.
- [x] Persistência de commits que alteram mais de um arquivo.
- [x] Persistência de incidentes com e sem detalhes.
- [x] Isolamento por repositório.
- [x] Rollback completo quando uma inserção falhar.
- [x] Consulta após reiniciar a aplicação.

## Fase 7 — Consulta e exportação do histórico

### Interface

Organizar “Histórico & tendências” em três áreas:

1. Releases;
2. Bugs encontrados;
3. Incidentes importados.

### Implementação

- [x] Adicionar filtro por release.
- [x] Adicionar filtro por módulo.
- [x] Mostrar estado vazio específico em cada área.
- [x] Aplicar os helpers de data e score nas tabelas.
- [x] Adicionar “Baixar CSV” para releases, bugs e incidentes.
- [x] Gerar o CSV em memória, sem criar arquivos permanentes na pasta do
  projeto.
- [x] Manter no CSV os valores canônicos necessários para reprocessamento:
  timestamps ISO e scores numéricos com ponto decimal.
- [x] Usar UTF-8 e cabeçalhos documentados.

### Testes

- [x] Consultar somente o repositório selecionado.
- [x] Filtrar por release e módulo.
- [x] Exportar histórico vazio e preenchido.
- [x] Validar cabeçalhos, quantidade de linhas e codificação.
- [x] Confirmar que a exportação não modifica o banco.

## Fase 8 — Aplicar formatação em todas as telas

- [x] Visão geral do risco.
- [x] Tabela de módulos.
- [x] Cabeçalho dos fatores.
- [x] Roteiro de teste manual.
- [x] Suíte automatizada priorizada.
- [x] Detalhe do módulo.
- [x] Decisão de publicação e auditoria.
- [x] Histórico e tendências.
- [x] Gráfico temporal, mantendo o eixo numérico/temporal.
- [x] CSVs de exportação, conforme a regra canônica definida neste plano.

## Fase 9 — Documentação

- [x] Atualizar o `README.md` com:
  - origem automática do histórico de bugs;
  - significado de JUnit e dos dois CSVs;
  - localização dos bancos;
  - política de datas e fuso horário;
  - persistência das evidências;
  - exportação CSV.
- [x] Atualizar `docs/implementacao-concluida.md` somente depois que a
  implementação estiver concluída e verificada.
- [x] Remover referências ao JPEG da documentação e dos testes.

## Fase 10 — Validação final

### Automatizada

- [ ] Restaurar ou recriar o ambiente virtual, pois o `.venv` atual aponta
  para um executável Python inexistente.
- [x] Instalar as dependências de `requirements.txt` no ambiente restaurado.
- [x] Executar:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

- [x] Executar a cobertura:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov=garantiu --cov-report=term-missing
```

- [x] Iniciar a aplicação:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### Verificação manual

- [x] Abrir a aplicação com estado inicial limpo.
- [x] Confirmar que o repositório começa vazio.
- [ ] Analisar um repositório sem fontes opcionais.
- [ ] Analisar outro repositório com JUnit e incidentes.
- [ ] Reiniciar a aplicação e consultar as evidências persistidas.
- [ ] Exportar os três CSVs e conferir o conteúdo.
- [ ] Verificar todas as sete páginas em desktop.
- [x] Verificar o layout abaixo de 900 px.
- [x] Confirmar ausência de fundos e halos brancos nos logos.
- [ ] Confirmar que datas e scores seguem o mesmo padrão em todas as telas.

## Arquivos principais afetados

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Campos, textos, navegação, gravação e histórico |
| `garantiu/ui.py` | Logo, cabeçalhos e formatadores |
| `garantiu/ui.css` | Transparência, contraste e remoção dos eyebrows |
| `garantiu/release_history.py` | Migração, persistência e consultas |
| `garantiu/bug_history.py` | Evidências extraídas do Git |
| `garantiu/incidents.py` | Importação dos CSVs |
| `tests/test_app_smoke.py` | Fluxos completos da interface |
| `tests/test_release_history.py` | Migração e persistência |
| `tests/test_bug_history.py` | Extração de bugs |
| `tests/test_incidents.py` | Validação dos CSVs |
| `README.md` | Orientação ao usuário |

## Critérios de conclusão

A implementação só deve ser considerada concluída quando:

- [x] todos os logos estiverem transparentes e legíveis;
- [x] não houver cabeçalhos no formato `NN · AÇÃO`;
- [x] o campo de repositório iniciar vazio;
- [x] as fontes de qualidade estiverem explicadas na primeira página;
- [x] bugs, incidentes e scores puderem ser consultados após reiniciar o app;
- [x] o histórico puder ser exportado em CSV;
- [x] datas e scores estiverem padronizados;
- [x] migrações preservarem os bancos existentes;
- [x] todos os testes automatizados passarem;
- [x] a inspeção visual em navegador estiver aprovada;
- [x] o diff final não incluir bancos SQLite, arquivos temporários ou outros
  artefatos gerados durante os testes.

## Estimativa

Estimativa inicial: **3 a 4 dias de desenvolvimento**, incluindo testes,
documentação e revisão visual. A estimativa deve ser revista caso seja incluído
cadastro manual de bugs ou importação direta de ferramentas externas.

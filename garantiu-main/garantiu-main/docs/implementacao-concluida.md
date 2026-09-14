# Implementação do plano

## Correção da geração e modelos de dados — 10/09/2026

A geração de JUnit durante a análise aceita o estado atual da pasta local,
inclusive alterações rastreadas, preparadas ou arquivos novos. Quando isso
ocorre, a interface e o nome da análise informam que os testes incluíram
alterações locais; o diff continua representando apenas o intervalo Git.
O caminho do XML gerado é exibido e há um botão para baixá-lo.

Ao selecionar uma pasta de armazenamento, o Garantiu cria os modelos ausentes
`modelo-junit.xml`, `modelo-incidents.csv` e
`modelo-incident_details.csv`. Eles são vazios, não substituem arquivos
existentes e são excluídos da descoberta e da análise. Para importar um CSV,
o usuário deve preencher dados reais e salvar uma cópia sem `modelo-`.

Verificação: 236 testes aprovados, 95% de cobertura total e 100% no executor
de testes, cobrindo geração com alterações locais, download, modelos,
preservação de arquivos existentes e exclusão dos modelos da análise. Houve
o aviso conhecido `WinError 6` ao finalizar um subprocesso Git no Windows,
sem falha.

## Geração de JUnit durante a análise — 10/09/2026

Conectar release oferece **Gerar JUnit com pytest ao analisar**, inicialmente
desativado e preservado por projeto na sessão. Quando ativado, Analisar
mudanças executa pytest localmente, salva um XML por rodada na pasta escolhida
e usa os resultados na análise e no histórico de testes. Exige o commit
selecionado aberto; alterações locais são testadas e sinalizadas. Usa a
`.venv` local ou o Python do Garantiu. O prazo de execução é de 10 minutos.

Testes reprovados são evidência válida. Falhas de execução interrompem a
análise sem novo snapshot, e XML parcial não é importado. Relatórios gerados
ficam separados da descoberta automática. O botão Procurar novamente fica no
final da seção opcional. CSVs de incidentes continuam manuais.

Verificação: 230 testes aprovados com cobertura total de 95% e 100% no módulo
`test_execution.py`. Inclui execuções reais de pytest, falhas, suíte vazia,
reanálise, navegação por AppTest e persistência. O aviso de finalização de
subprocesso `WinError 6` voltou a ocorrer em um teste Git, sem falha.
Não houve validação visual manual nem validação de outros executores de teste.

## Incremento de classificação — 10/09/2026

Concluída a fase 2 de `plano-correcao-detalhe-modulos-e-score.md`: somente
código de produto segue para score, roteiro e persistência dos módulos.
Arquivos excluídos ficam auditáveis na sessão com categoria e motivo; o
detalhe de bugs desconsidera correções apenas de suporte. Intervalos sem
código mostram estado vazio na visão geral.

Verificação: 215 testes aprovados, 95% de cobertura de `garantiu`, incluindo
AppTest e leitura dos snapshots SQLite. Um aviso `WinError 6` ocorreu na
finalização de subprocesso, sem falhas. Validação visual manual pendente.
Este incremento não conclui o plano completo: binários, evidências de bugs,
fontes ausentes e score v2 continuam pendentes.

## Plano original do MVP

Referência: `garantiu-plano-de-implementacao.pdf` (37 páginas), com fonte
Markdown em `superpowers/plans/2026-09-09-garantiu-mvp-implementation.md`.
O PDF define o escopo técnico de sete telas; o wireframe e o relatório de
funcionalidades descrevem também ideias que não fazem parte dessas 14 tarefas.

| Tarefas | Entrega | Evidência automatizada |
|---|---|---|
| 1–2 | Diff Git, mineração de correções | `test_git_reader.py`, `test_bug_history.py` |
| 3–4 | JUnit e contagem de incidentes CSV | `test_test_reports.py`, `test_incidents.py` |
| 5–6 | Score ponderado, máximo por release e roteiro manual | `test_scoring.py`, `test_manual_test_guide.py` |
| 7–8 | Auditoria e quatro telas originais | `test_decision_log.py`, `test_app_smoke.py` |
| 9 | Rodadas SQLite e flakiness por mudanças de status | `test_test_history.py` |
| 10 | Priorização por score, status, flakiness e nome | `test_test_prioritization.py` |
| 11 | Bugs e incidentes detalhados com datas | `test_bug_history.py`, `test_incidents.py` |
| 12 | Agregação do detalhe de módulo | `test_module_detail.py` |
| 13 | Score previsto e resultado real persistidos | `test_release_history.py` |
| 14 | Sete telas integradas e histórico ligado ao score | `test_app_smoke.py` |

## Ajustes necessários ao exemplo do plano

- Preservada a fórmula e o contrato público das tarefas já implementadas.
- Histórico isolado por caminho do repositório; identidade do release inclui
  os hashes base/final para não misturar análises de intervalos distintos.
- Histórico de bugs respeita o commit final analisado, mesmo que outra branch
  esteja em checkout. As telas de detalhe usam os dados capturados na análise.
- Histórico apresenta somente o último score e resultado de cada release,
  com desempate por id quando datas são iguais; os registros anteriores ficam
  preservados no SQLite.
- Importação de uma rodada é atômica; testes duplicados e status inválidos
  são rejeitados antes de gravar. Resultados reais exigem um release existente.
- Validação de entrada, estados vazios e erros recuperáveis na interface;
  nome em branco não registra decisão. Testes de UI usam dados temporários.
- Gráfico temporal dos scores e tabela com o resultado observado. Ausência
  de resultado real continua desconhecida, sem ser convertida em sucesso.

## Limites mantidos

Os quatro fatores continuam com peso igual, sem recalibração automática.
JUnit fornece status, não cobertura. Flakiness usa todo o histórico importado
e as mudanças de status do algoritmo da Task 9, sem janela de 30 dias.
O roteiro é baseado em templates. A suíte recomenda uma ordem e as decisões
são registros, sem execução de testes ou deploy. Não há autenticação ou
integrações externas. Esses recursos não integram a implementação exigida
pelo código e pelos testes das 14 tarefas do PDF.

Instruções de execução, formatos, persistência e verificação: `../README.md`.

## Ajustes de interface e persistência

O roteiro `plano-ajustes-interface-persistencia.md` também foi implementado:

- a marca usa somente PNGs transparentes, combinando símbolo e nome sem caixas
  claras no tema escuro;
- os cabeçalhos numerados foram removidos e o campo de repositório inicia vazio;
- JUnit e os dois formatos de incidentes são explicados na primeira tela;
- cada análise grava, em uma transação, o score da release, os quatro fatores
  por módulo, as correções relacionadas aos arquivos e os incidentes importados;
- reanálises do mesmo intervalo são preservadas como snapshots, enquanto o
  resumo continua exibindo somente a versão mais recente;
- o histórico pode ser filtrado por release e módulo e exportado, em memória,
  como CSV UTF-8 de releases, bugs ou incidentes;
- a apresentação usa datas brasileiras, horário de São Paulo e scores com uma
  casa decimal, sem alterar timestamps ISO ou valores numéricos persistidos.
- a área de dados opcionais permite escolher a pasta de armazenamento local;
  os bancos SQLite são criados e consultados nesse local na sessão atual, e
  relatórios colocados na mesma pasta entram na descoberta automática.
- a primeira tela descobre relatórios JUnit e CSVs de incidentes pelo conteúdo,
  preenche candidatos únicos e oferece escolha quando encontra vários arquivos;
  a mesma descoberta funciona para arquivos versionados em links GitHub.

## Validação desta entrega

- `python -m pytest -q`: **142 testes passaram** (Python 3.12.10), incluindo
  migrações aditivas, rollback atômico, filtros, exportações e apresentação.
- `python -m pytest -q --cov=garantiu --cov-report=term-missing`: **96% de
  cobertura de linha** no pacote `garantiu`.
- Servidor Streamlit iniciado em `127.0.0.1:8502`; endpoint
  `/_stcore/health` retornou `ok`.
- As sete telas foram exercitadas com AppTest, incluindo dados preenchidos,
  publicação/cancelamento, resultado real e nova sessão lendo o histórico.
- Inspeção visual realizada no Chrome em viewports de 1440 × 1000 e 390 × 844,
  sem overlay de erro ou mensagens de erro do navegador. O campo inicial vazio,
  a responsividade e a transparência dos logos foram conferidos.
- CI (`.github/workflows/tests.yml`) roda a mesma suíte com cobertura a cada
  push/PR para `main`, sem depender de configuração local de identidade Git
  (as fixtures de teste que criam commits configuram um autor local via
  `tests/conftest.py`, em vez de depender do `git config` global da máquina).

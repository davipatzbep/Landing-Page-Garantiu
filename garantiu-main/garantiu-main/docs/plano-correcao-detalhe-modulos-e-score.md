# Plano de implementação — detalhe dos módulos, fatores de risco e filtro de código

## Progresso em 10/09/2026 — segundo incremento

Concluído: classificador `classify_changed_path()` em `garantiu/git_reader.py`,
com categorias, motivos, precedência centralizada e exclusão de tipos
desconhecidos. O filtro legado `is_documentation_change()` foi preservado.
Os testes cobrem categorias, linguagens reconhecidas, caminhos Windows e
renomes entre código e diretórios de teste.

Implementado neste incremento: classificação conectada ao pipeline antes dos
cálculos, roteiro e persistência; `all_changed_files`, `changed_code_files` e
`excluded_files` preservados na sessão. `changed_files` permanece como alias
filtrado para os consumidores existentes. Conectar release e Visão geral do
risco mostram a lista auditável com caminho, categoria e motivo. Sem código
de produto, a visão geral apresenta estado vazio. O detalhe de bugs ignora
correções exclusivamente de suporte dentro do módulo.

Pendente: binários e explicação das linhas (fase 1), contagem e janela de bugs,
disponibilidade de testes e incidentes, score v2, persistência dos novos
contratos, exportações e apresentação dos fatores. A fórmula do score ainda
é a anterior. A auditoria de exclusões está na sessão; ainda não é exportada
nem persistida. A validação manual final do plano permanece pendente.

Verificação deste incremento: 215 testes aprovados com
`python -m pytest -q --cov=garantiu --cov-report=term-missing`, cobertura de
95% de `garantiu`. Houve um aviso de finalização de subprocesso no Windows
(`WinError 6`), sem falha de teste. AppTest validou exclusões, navegação,
estado vazio e os registros SQLite; não houve validação visual manual.

## Objetivo

Corrigir três problemas observados na análise de releases:

1. explicar os números exibidos ao lado dos arquivos na página “Detalhe do
   módulo”;
2. impedir que os fatores de bugs, testes e incidentes apresentem valores
   enganosos ou sempre iguais;
3. retirar do cálculo arquivos que não representam código de produto, como
   `.gitignore`, documentação, imagens, relatórios e metadados do repositório.

Este documento é um roteiro de implementação. Cada fase possui alterações,
testes e critérios de aceite próprios.

## Resumo do diagnóstico

### Números `+` e `-` ao lado dos arquivos

Na tabela atual, `+` representa a quantidade de linhas adicionadas e `-` a
quantidade de linhas removidas no intervalo Git selecionado.

Essa informação vem de `git diff --numstat` e é armazenada nos campos
`lines_added` e `lines_removed` de `garantiu/git_reader.py`.

Problemas atuais:

- os nomes das colunas não explicam o significado;
- arquivos binários são retornados pelo Git com `-` no lugar da contagem, mas
  o código converte esse valor para zero;
- `0/0` pode, portanto, significar “sem alteração de linhas” ou “arquivo
  binário sem contagem disponível”.

### Histórico de bugs em 100

O comportamento é consequência de três decisões atuais:

1. cada correção é contada por arquivo;
2. as contagens dos arquivos do módulo são somadas, de modo que um único
   commit que altera vários arquivos pode ser contado mais de uma vez;
3. a normalização divide todas as contagens pelo maior valor da análise.

Com a fórmula atual, o módulo com mais correções sempre recebe 100. Quando
existe apenas um módulo alterado com pelo menos uma correção, ele necessariamente
recebe 100, independentemente de ter uma ou cinquenta correções.

Além disso, todo o histórico alcançável pelo commit analisado é considerado.
Correções antigas continuam influenciando releases atuais.

### Saúde dos testes em 0

O valor chamado de “Saúde dos testes” no score não é uma porcentagem de saúde.
Ele é um valor de risco calculado a partir de:

```text
risco de teste = 50% × (100 - taxa de aprovação) + 50% × flakiness
```

Por isso, testes totalmente aprovados e estáveis geram risco zero. Entretanto,
quando não existe JUnit associado ao módulo, o código também usa aprovação
100 e flakiness zero. A interface não consegue distinguir:

- testes saudáveis;
- relatório ausente;
- relatório presente sem correspondência entre o `classname` e o módulo.

### Incidentes em 0

Incidentes ausentes usam zero como padrão. Assim, o mesmo valor significa:

- o CSV foi fornecido e o módulo realmente não possui incidentes; ou
- nenhum CSV foi fornecido;
- o nome do módulo no CSV não corresponde ao módulo do Git.

### Arquivos que não são código

O filtro atual considera como documentação apenas:

- arquivos dentro de `docs/`;
- extensões `.md`, `.mdx`, `.pdf`, `.rst`, `.txt` e `.adoc`.

Por isso, itens como os seguintes ainda entram na análise:

- `.gitignore`;
- `.gitattributes` e `.editorconfig`;
- `.github/workflows/*.yml`;
- `.streamlit/config.toml`;
- imagens e outros assets;
- arquivos em `sample_data/`;
- relatórios XML e CSV;
- código de testes, que não representa diretamente código de produção;
- arquivos gerados, lockfiles e metadados de ferramentas.

No intervalo automático atual deste repositório não há tags anteriores. A
comparação começa no primeiro commit, o que aumenta a visibilidade desses
arquivos de suporte.

## Decisões de implementação

### Separar classificação de arquivo e leitura do diff

`get_changed_files()` continuará responsável por ler o Git. Uma nova função
classificará cada caminho depois que renomes forem resolvidos.

Categorias propostas:

| Categoria | Entra no score | Exemplos |
|---|---:|---|
| `product_code` | Sim | `.py`, `.ts`, `.java`, `.go`, `.css`, `.sql` |
| `test_code` | Não | `tests/`, `__tests__/`, `*.spec.ts` |
| `documentation` | Não | `docs/`, `README.md`, PDFs |
| `repository_meta` | Não | `.gitignore`, `.gitattributes`, `.github/` |
| `configuration` | Não | `.streamlit/`, arquivos de configuração |
| `dependency_metadata` | Não | lockfiles e manifests |
| `asset` | Não | imagens, fontes, áudio e vídeo |
| `generated_or_vendor` | Não | `dist/`, `build/`, `vendor/` |
| `quality_data` | Não | JUnit XML, CSVs e relatórios de cobertura |
| `unknown` | Não | extensão ou tipo não reconhecido |

Arquivos desconhecidos devem ser excluídos por padrão. Isso segue a exigência
de calcular risco somente sobre código reconhecido, sem presumir que todo
arquivo desconhecido seja produto.

O resultado completo do Git continuará disponível para auditoria. A aplicação
deve separar:

- `all_changed_files`: tudo que mudou;
- `changed_code_files`: somente `product_code`;
- `excluded_files`: caminho, categoria e motivo da exclusão.

### Versão do algoritmo de score

As correções mudam o significado do score. Registrar `score_version = 2` nas
novas análises e preservar scores históricos como versão 1.

Não recalcular nem sobrescrever registros antigos automaticamente. Na tela de
histórico, indicar a versão usada para evitar comparar números como se tivessem
a mesma fórmula.

### Valor ausente não é zero

Cada fator deverá transportar valor, evidência e disponibilidade:

```python
{
    "risk_score": 40.0,       # None quando não há dado suficiente
    "status": "available",   # available, partial ou missing
    "raw_value": 2,
    "summary": "2 correções distintas nos últimos 180 dias",
}
```

Regras:

- `0` significa um dado disponível que resultou em risco zero;
- `None` significa que não há informação suficiente;
- `partial` significa que existe informação, mas ela não é específica do
  módulo ou está incompleta;
- a interface nunca deve converter `missing` em `0%`.

### Cálculo com fontes ausentes

Calcular a média ponderada somente com fatores disponíveis. Renormalizar os
pesos disponíveis para somarem 100% e apresentar separadamente a completude
dos dados.

Exemplo:

```text
Fatores disponíveis: complexidade e bugs
Completude: 2 de 4 fontes
Score: média ponderada apenas dos dois fatores disponíveis
```

Essa regra impede que a falta de JUnit ou incidentes reduza artificialmente o
risco. A decisão deve ser acompanhada por um aviso de baixa completude.

## Fase 1 — Explicar a tabela de arquivos

### Implementação

- [ ] Renomear as colunas da tabela:
  - [ ] `+` para `Linhas adicionadas`;
  - [ ] `-` para `Linhas removidas`.
- [ ] Adicionar antes da tabela a explicação:

  > As contagens mostram quantas linhas foram adicionadas e removidas no
  > intervalo Git selecionado.

- [ ] Adicionar `is_binary` ao contrato retornado por
  `get_changed_files()`.
- [ ] Quando o Git retornar `-` no `numstat`, manter as contagens como `None`
  e marcar `is_binary=True`.
- [ ] Exibir `Não disponível — arquivo binário` em vez de `0/0` para binários.
- [ ] Mostrar um resumo do módulo:
  - quantidade de arquivos de código alterados;
  - total de linhas adicionadas;
  - total de linhas removidas.
- [ ] Não somar `None` nos totais.

### Arquivos afetados

- `garantiu/git_reader.py`
- `garantiu/module_detail.py`
- `app.py`
- `tests/test_git_reader.py`
- `tests/test_module_detail.py`
- `tests/test_app_smoke.py`

### Testes

- [ ] Diff com linhas somente adicionadas.
- [ ] Diff com linhas somente removidas.
- [ ] Diff com adições e remoções.
- [ ] Arquivo vazio.
- [ ] Arquivo binário.
- [ ] Arquivo renomeado.
- [ ] Tabela com cabeçalhos descritivos.

### Critérios de aceite

- [ ] Um usuário entende os números sem consultar documentação externa.
- [ ] Arquivos binários nunca aparecem como se tivessem zero alterações.
- [ ] Os totais correspondem à soma do `git diff --numstat` para os arquivos
  de código exibidos.

## Fase 2 — Classificar arquivos de código

### Implementação

- [x] Substituir `is_documentation_change()` por uma classificação mais ampla,
  mantendo um wrapper temporário se necessário para compatibilidade.
- [x] Criar `classify_changed_path(path) -> {category, include_in_risk, reason}`.
- [x] Centralizar as regras em constantes testáveis; não espalhar listas de
  extensões pelo `app.py`.
- [x] Considerar como código de produto, inicialmente:
  - Python, JavaScript e TypeScript;
  - Java, Kotlin, Go, Rust, Ruby, PHP e C#;
  - C, C++, Swift e Dart;
  - Vue e Svelte;
  - HTML, CSS, Sass e Less;
  - SQL;
  - scripts shell, PowerShell e batch.
- [x] Excluir explicitamente caminhos e nomes conhecidos:
  - `.gitignore`, `.gitattributes`, `.editorconfig`;
  - `.github/`, `.gitlab/`, `.circleci/`;
  - `docs/`, `sample_data/`, `examples/`, `fixtures/`;
  - `dist/`, `build/`, `coverage/`, `htmlcov/`, `vendor/`;
  - `node_modules/`, `.venv/`, caches e arquivos gerados;
  - imagens, fontes, áudio, vídeo, PDFs, XMLs e CSVs;
  - lockfiles e manifests de dependência;
  - diretórios e padrões de teste.
- [x] Aplicar a classificação antes de:
  - agrupar arquivos por módulo;
  - calcular complexidade;
  - selecionar evidências de bugs;
  - gerar roteiro manual;
  - persistir detalhes do módulo.
- [x] Preservar `excluded_files` na sessão e mostrar um resumo recolhível:

  > 12 arquivos de suporte foram ignorados no cálculo.

- [x] Dentro do resumo, listar caminho, categoria e motivo.

### Regra de precedência

Aplicar as regras nesta ordem:

1. diretórios ignorados;
2. nomes especiais ignorados;
3. padrões de teste;
4. documentação, assets e dados;
5. extensão reconhecida como código;
6. desconhecido.

Essa ordem impede, por exemplo, que um arquivo `.py` dentro de `tests/` seja
classificado como código de produto.

### Compatibilidade

- [x] Manter `all_changed_files` para contagens e mensagens informativas.
- [x] Renomear gradualmente `changed_files` para `changed_code_files` ou
  documentar explicitamente que ele já está filtrado.
- [x] Releases sem código de produto devem resultar em estado vazio, não em
  score calculado a partir de arquivos de configuração.
- [x] Informar que houve mudanças, mas nenhuma foi classificada como código de
  produto.

### Testes

- [x] Teste parametrizado para cada categoria.
- [x] `.gitignore` não entra no score.
- [x] workflow YAML não entra no score.
- [x] configuração Streamlit não entra no score.
- [x] PNG e PDF não entram no score.
- [x] JUnit XML e CSV de incidentes não entram no score.
- [x] arquivo Python dentro de `tests/` não entra no score.
- [x] arquivo Python dentro de `garantiu/` entra no score.
- [x] CSS de produto entra no score.
- [x] extensão desconhecida fica em `excluded_files`.
- [x] rename entre categoria ignorada e código usa o caminho novo.
- [x] análise contendo somente arquivos ignorados gera score vazio.

### Critérios de aceite

- [x] `.gitignore` e arquivos equivalentes não aparecem como módulos.
- [x] Somente código de produto influencia complexidade e score.
- [x] Arquivos excluídos continuam auditáveis em uma seção secundária.
- [x] Nenhum arquivo desconhecido entra silenciosamente no cálculo.

## Fase 3 — Corrigir a evidência de bugs

### Implementação

- [ ] Contar commits distintos por módulo, não ocorrências por arquivo.
- [ ] Se um commit de correção alterar cinco arquivos do mesmo módulo, contar
  uma correção para esse módulo.
- [ ] Se o mesmo commit alterar dois módulos, contar uma correção em cada
  módulo afetado.
- [ ] Considerar somente arquivos classificados como `product_code`.
- [ ] Introduzir uma janela temporal baseada na data do commit analisado.
- [ ] Usar como padrão inicial 180 dias, com constante documentada
  `BUG_LOOKBACK_DAYS`.
- [ ] Registrar no resultado:
  - quantidade bruta de correções distintas;
  - período considerado;
  - score de risco derivado;
  - hashes usados como evidência.

### Normalização recomendada para a versão 2

Usar uma escala absoluta e explicável em vez de dividir pelo maior módulo da
release:

```text
risco de bugs = min(100, correções distintas × 20)
```

Escala inicial:

| Correções distintas em 180 dias | Risco |
|---:|---:|
| 0 | 0 |
| 1 | 20 |
| 2 | 40 |
| 3 | 60 |
| 4 | 80 |
| 5 ou mais | 100 |

O multiplicador deve ser uma constante nomeada e documentada. Revisar essa
calibração quando houver histórico real suficiente; não alterar silenciosamente
a fórmula dentro da mesma versão do score.

### Interface

- [ ] Alterar o título visual para `Risco por histórico de bugs`.
- [ ] Exibir o valor bruto próximo ao score:

  > 2 correções distintas nos últimos 180 dias · risco 40/100

- [ ] Não apresentar o risco como porcentagem de bugs.
- [ ] No detalhe, continuar listando commit, mensagem e data.

### Testes

- [ ] Um commit que altera vários arquivos do mesmo módulo conta uma vez.
- [ ] Um commit que altera dois módulos conta uma vez por módulo.
- [ ] Commit fora da janela de 180 dias não influencia o score.
- [ ] Commit dentro da janela aparece no detalhe e no cálculo.
- [ ] 0, 1, 2 e 5 correções produzem os valores esperados.
- [ ] Apenas um módulo alterado com uma correção recebe 20, não 100.
- [ ] Arquivos ignorados em commits de correção não criam evidência.

### Critérios de aceite

- [ ] O fator não recebe 100 apenas por ser o maior módulo da análise.
- [ ] O valor exibido permite conferir a conta a partir dos commits listados.
- [ ] Correções antigas e arquivos não produtivos não distorcem o score.

## Fase 4 — Separar saúde, risco e ausência de testes

### Contrato

Para cada módulo, produzir:

- `pass_rate`: taxa de aprovação atual;
- `flakiness`: instabilidade histórica;
- `risk_score`: contribuição de risco;
- `status`: `available`, `partial` ou `missing`;
- `mapping_reason`: explicação da correspondência entre teste e módulo.

### Implementação

- [ ] Não usar aprovação 100 como valor padrão quando o módulo não possui
  testes associados.
- [ ] Retornar `risk_score=None` e `status=missing` sem correspondência.
- [ ] Distinguir:
  - JUnit não fornecido;
  - JUnit vazio;
  - JUnit válido sem teste para o módulo;
  - testes associados e todos aprovados;
  - testes associados com falhas ou flakiness.
- [ ] Normalizar nomes antes da correspondência:
  - remover espaços laterais;
  - comparar com regra documentada de maiúsculas/minúsculas;
  - manter o nome original para apresentação.
- [ ] Não atribuir automaticamente a saúde global do projeto a cada módulo.
  Sem evidência de associação, mostrar `Sem dados para este módulo`.
- [ ] Considerar, como evolução separada, um arquivo explícito de mapeamento
  entre classes de teste e módulos. Não inferir relações por semelhança de
  texto nesta entrega.

### Interface

- [ ] Mostrar `Saúde dos testes: 100%` quando a taxa de aprovação for 100%.
- [ ] Mostrar também `Risco dos testes: 0/100` para deixar clara a inversão.
- [ ] Quando não houver dados, mostrar `Sem dados`, nunca `0%`.
- [ ] Mostrar a flakiness somente quando existir histórico suficiente.
- [ ] Informar quantos testes foram associados ao módulo.

### Testes

- [ ] Sem JUnit resulta em `missing`.
- [ ] JUnit sem correspondência resulta em `missing` com motivo diferente.
- [ ] Todos aprovados resultam em saúde 100 e risco 0.
- [ ] Metade aprovada produz saúde 50 e o risco esperado.
- [ ] Flakiness aumenta o risco conforme a fórmula documentada.
- [ ] Módulos com nomes semelhantes não são associados por engano.

### Critérios de aceite

- [ ] Zero nunca representa simultaneamente “saudável” e “sem dados”.
- [ ] A interface diferencia saúde observada de risco calculado.
- [ ] O usuário consegue identificar por que um JUnit não foi associado.

## Fase 5 — Separar zero incidente de fonte ausente

### Implementação

- [ ] Passar ao score a informação de que o CSV foi ou não fornecido.
- [ ] Normalizar os nomes dos módulos na entrada e no Git com a mesma função.
- [ ] Se o CSV foi fornecido e o módulo não consta nele, tratar como zero
  incidentes disponíveis.
- [ ] Se o CSV não foi fornecido, usar `risk_score=None` e `status=missing`.
- [ ] Se somente a contagem foi fornecida, marcar os detalhes como parciais,
  sem invalidar a contagem.
- [ ] Validar módulos duplicados no CSV em vez de sobrescrever silenciosamente.
- [ ] Persistir o status da fonte junto ao snapshot da análise.

### Interface

- [ ] Exibir uma das mensagens:
  - `Sem dados de incidentes`;
  - `Nenhum incidente registrado`;
  - `2 incidentes registrados`;
  - `2 incidentes, sem detalhes importados`.
- [ ] Não mostrar `0%` quando a fonte estiver ausente.
- [ ] Exibir o score de risco separadamente da contagem bruta.

### Testes

- [ ] CSV ausente.
- [ ] CSV vazio válido.
- [ ] Módulo ausente em CSV fornecido.
- [ ] Módulo com contagem zero explícita.
- [ ] Módulo com incidentes e detalhes.
- [ ] Módulos duplicados.
- [ ] Diferenças de caixa e espaços nos nomes.

### Critérios de aceite

- [ ] A interface não confunde ausência de fonte com ausência de incidentes.
- [ ] O valor bruto exibido corresponde ao CSV selecionado.
- [ ] Problemas de associação ficam visíveis e acionáveis.

## Fase 6 — Introduzir o score versão 2

### Estrutura proposta

Cada módulo deve conter:

```python
{
    "module": "garantiu",
    "score": 47.5,
    "score_version": 2,
    "data_completeness": 0.75,
    "factors": {
        "complexidade": {...},
        "bugs": {...},
        "saude_testes": {...},
        "incidentes": {...},
    },
}
```

### Implementação

- [ ] Definir um tipo ou estrutura única para fatores; evitar dicionários
  montados de formas diferentes entre módulos.
- [ ] Atualizar `score_modules()` para aceitar a disponibilidade das fontes.
- [ ] Renormalizar somente os pesos disponíveis.
- [ ] Calcular `data_completeness` pela soma dos pesos originalmente
  disponíveis.
- [ ] Manter os quatro pesos-base em 25% nesta versão.
- [ ] Tratar complexidade e bugs como fontes automáticas disponíveis quando
  houver código de produto.
- [ ] Não calcular score quando não existir código de produto.
- [ ] Persistir `score_version`, completude, valores brutos, status e motivos.
- [ ] Atualizar exportações CSV com essas colunas.

### Histórico e compatibilidade

- [ ] Adicionar colunas de forma aditiva nas tabelas SQLite existentes.
- [ ] Marcar registros legados como versão 1 durante a leitura, sem reescrever
  o banco inteiro.
- [ ] Mostrar a versão na tabela histórica.
- [ ] Não desenhar uma linha contínua misturando versões 1 e 2 sem indicação.
- [ ] Documentar que uma mudança de versão pode causar variação mesmo sem
  mudança equivalente no perfil do repositório.

### Testes

- [ ] Quatro fatores disponíveis usam pesos de 25%.
- [ ] Dois fatores disponíveis são renormalizados corretamente.
- [ ] Fonte ausente não contribui como zero.
- [ ] Completude de duas fontes é 50%.
- [ ] Banco legado continua legível.
- [ ] Novos registros recebem versão 2.
- [ ] Histórico diferencia as versões.

## Fase 7 — Atualizar a apresentação dos fatores

### Implementação

- [ ] Atualizar `render_factor_heading()` para receber a estrutura completa
  do fator.
- [ ] Remover o símbolo `%` de valores que representam risco relativo.
- [ ] Usar `/100` somente para scores.
- [ ] Exibir valores brutos em linguagem natural.
- [ ] Exibir badges distintos:
  - `Dados disponíveis`;
  - `Dados parciais`;
  - `Sem dados`.
- [ ] Adicionar uma explicação curta e acessível para cada fator.
- [ ] Mostrar a completude da análise junto ao score da release.
- [ ] Quando houver fonte ausente, informar como fornecê-la na página
  “Conectar release”.

### Texto sugerido

| Fator | Apresentação |
|---|---|
| Complexidade | `240 linhas alteradas · risco 55/100` |
| Bugs | `2 correções em 180 dias · risco 40/100` |
| Testes saudáveis | `100% aprovados · risco 0/100` |
| Testes ausentes | `Sem testes associados a este módulo` |
| Sem incidentes | `Nenhum incidente registrado · risco 0/100` |
| Fonte ausente | `Sem dados de incidentes` |

### Critérios de aceite

- [ ] Todo score possui uma evidência bruta próxima.
- [ ] Nenhum dado ausente aparece como zero.
- [ ] Percentual é usado somente para taxa de aprovação, flakiness e
  completude.
- [ ] O usuário consegue explicar por que um fator recebeu determinado valor.

## Fase 8 — Atualizar persistência e exportação

### Implementação

- [ ] Persistir a classificação do arquivo ou apenas os arquivos de produto,
  conforme a necessidade de auditoria definida no banco atual.
- [ ] Persistir valores brutos e disponibilidade dos quatro fatores.
- [ ] Persistir a versão do algoritmo.
- [ ] Incluir nos CSVs:
  - versão do score;
  - completude;
  - score de cada fator;
  - valor bruto;
  - status da fonte;
  - motivo quando ausente ou parcial.
- [ ] Manter exportação de arquivos excluídos separada ou incluir uma coluna
  clara que impeça confusão com código analisado.

### Testes

- [ ] Round-trip de análise completa no SQLite.
- [ ] Round-trip com fontes ausentes.
- [ ] Leitura de registro legado.
- [ ] CSV não converte `Sem dados` em zero.
- [ ] Arquivos excluídos não aparecem como módulos de risco.

## Fase 9 — Documentação

- [ ] Atualizar `README.md` com:
  - significado de linhas adicionadas e removidas;
  - categorias de arquivos e política de exclusão;
  - diferença entre saúde e risco dos testes;
  - diferença entre zero e dado ausente;
  - janela e escala do histórico de bugs;
  - versão do algoritmo e completude.
- [ ] Atualizar `docs/relatorio-funcionalidades.md`, que atualmente descreve
  conceitos mais amplos que os dados realmente disponíveis no MVP.
- [ ] Atualizar `docs/implementacao-concluida.md` somente depois da entrega e
  da verificação.
- [ ] Incluir a versão do score em exemplos e capturas atualizadas.

## Fase 10 — Validação final

### Testes focados

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_git_reader.py tests/test_bug_history.py tests/test_scoring.py tests/test_module_detail.py tests/test_incidents.py tests/test_test_reports.py
```

### Suíte completa

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Cobertura

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov=garantiu --cov-report=term-missing
```

O ambiente virtual foi localizado e executado com Python 3.12.10. No ambiente
restrito do agente, o acesso ao executável requer execução com permissão
ampliada; não foi necessário recriar o ambiente.

### Cenários manuais obrigatórios

- [ ] Release que altera somente `.gitignore`.
- [ ] Release que altera documentação, imagem e configuração.
- [ ] Release que altera somente um arquivo Python.
- [ ] Release com um commit de bug tocando vários arquivos.
- [ ] Release sem JUnit e sem incidentes.
- [ ] Release com JUnit sem correspondência de módulo.
- [ ] Release com todos os testes aprovados.
- [ ] Release com falhas e flakiness.
- [ ] Release com CSV que registra zero incidentes.
- [ ] Release com incidentes e detalhes.
- [ ] Arquivo binário alterado.
- [ ] Histórico contendo scores versão 1 e versão 2.

## Arquivos principais afetados

| Arquivo | Alteração esperada |
|---|---|
| `garantiu/git_reader.py` | Binários e classificação de caminhos |
| `garantiu/bug_history.py` | Commits distintos, janela e filtro de código |
| `garantiu/scoring.py` | Disponibilidade, valores brutos e score v2 |
| `garantiu/test_reports.py` | Estado e correspondência dos testes |
| `garantiu/incidents.py` | Estado da fonte e módulos duplicados |
| `garantiu/module_detail.py` | Resumo de linhas e evidências estruturadas |
| `garantiu/release_history.py` | Migração e persistência do score v2 |
| `garantiu/ui.py` | Apresentação de fatores e estados ausentes |
| `app.py` | Integração, mensagens e arquivos excluídos |
| `tests/` | Regressões unitárias e fluxos completos |
| `README.md` | Explicação da nova semântica |

## Ordem recomendada de execução

1. Criar os testes de classificação e binários.
2. Implementar a classificação de arquivos.
3. Aplicar o filtro em toda a análise antes de alterar o score.
4. Corrigir a contagem e a janela de bugs.
5. Introduzir os estados de disponibilidade para testes e incidentes.
6. Implementar o score versão 2 e a completude.
7. Migrar a persistência de forma aditiva.
8. Atualizar a interface e a exportação.
9. Atualizar a documentação.
10. Executar testes focados, suíte completa e validação visual.

## Critérios de conclusão

A entrega estará concluída somente quando:

- [ ] os números da tabela de arquivos estiverem claramente identificados;
- [ ] arquivos binários não aparecerem como `0/0`;
- [ ] `.gitignore` e outros arquivos de suporte não influenciarem o score;
- [ ] o mesmo commit não for contado várias vezes no mesmo módulo;
- [ ] um módulo com uma correção não receber automaticamente risco 100;
- [ ] saúde zero, risco zero e dado ausente tiverem apresentações diferentes;
- [ ] incidentes ausentes não forem interpretados como zero incidentes;
- [ ] o score mostrar sua versão e a completude dos dados;
- [ ] o histórico antigo continuar legível;
- [ ] testes automatizados e cenários manuais estiverem aprovados;
- [ ] o diff final não incluir bancos, relatórios ou artefatos de execução.

## Estimativa

Estimativa inicial: **4 a 6 dias de desenvolvimento**.

A mudança é maior que um ajuste visual porque altera o contrato dos fatores, a
fórmula do score e a persistência histórica. A estimativa inclui migração
compatível, testes de regressão, documentação e validação visual.

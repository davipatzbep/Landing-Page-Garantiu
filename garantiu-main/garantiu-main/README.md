# garantiu

[![tests](https://github.com/bernardohorn/garantiu/actions/workflows/tests.yml/badge.svg)](https://github.com/bernardohorn/garantiu/actions/workflows/tests.yml)

Dashboard local de risco de releases, implementado em Python e Streamlit.
Cruza mudanças do Git, resultados JUnit e incidentes CSV para priorizar
testes manuais e automatizados e registrar decisões humanas.

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Início rápido (primeira vez)](#início-rápido-primeira-vez)
- [Rodar de novo (depois da primeira vez)](#rodar-de-novo-depois-da-primeira-vez)
- [Problemas comuns](#problemas-comuns)
- [Usar as sete telas](#usar-as-sete-telas)
- [Analisar um repositório do GitHub](#analisar-um-repositório-do-github)
- [Entradas e cálculo](#entradas-e-cálculo)
- [Persistência e limites](#persistência-e-limites)
- [Verificação e referências](#verificação-e-referências)

## Pré-requisitos

Antes de começar, confira se você tem os dois programas abaixo instalados e
visíveis no terminal. Abra o **PowerShell** (menu Iniciar → digite
"PowerShell") e rode:

```powershell
python --version
git --version
```

- `python --version` deve mostrar **3.10 ou mais recente** (o projeto foi
  validado com 3.12.10). Se der erro `não é reconhecido...`, instale o
  Python em <https://www.python.org/downloads/> marcando a opção
  **"Add python.exe to PATH"** durante a instalação, e abra um novo
  PowerShell depois.
- `git --version` deve mostrar algum número de versão. Se der erro, instale
  o Git em <https://git-scm.com/downloads> (aceite as opções padrão do
  instalador).

Se as duas versões apareceram, pode seguir para o próximo passo.

## Início rápido (primeira vez)

Rode os comandos abaixo **um de cada vez**, na ordem, dentro da pasta do
projeto. Se algum comando der erro, veja [Problemas comuns](#problemas-comuns)
antes de continuar para o próximo.

**1. Entre na pasta do projeto.** Troque o caminho abaixo pelo local onde
você salvou/clonou o garantiu:

```powershell
cd "C:\caminho\para\garantiu"
```

**2. Crie o ambiente virtual** (uma pasta `.venv` isolada, só para as
dependências deste projeto — não interfere no seu Python global):

```powershell
py -m venv .venv
```

Isso não imprime nada se der certo; só demora alguns segundos e cria a pasta
`.venv`.

**3. Instale as dependências do projeto** dentro desse ambiente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Espere terminar — você vai ver várias linhas `Collecting...`/`Installing...`
e, no fim, algo como `Successfully installed streamlit-... gitpython-...`.
Isso pode levar 1–2 minutos na primeira vez.

**4. Rode os testes automatizados**, para confirmar que tudo foi instalado
certo:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Se aparecer algo como `104 passed in Xs` (sem a palavra `failed`), está tudo
certo e você pode seguir. Se aparecer erro, veja
[Problemas comuns](#problemas-comuns).

**5. Inicie a aplicação:**

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

O terminal vai mostrar algo como:

```
You can now view your Streamlit app in your browser.
Local URL: http://127.0.0.1:8501
```

**6. Abra esse endereço no navegador**: <http://localhost:8501>. Se o
navegador não abrir sozinho, copie e cole o endereço manualmente. Você deve
ver a tela **"Conectar release"**, com o menu de sete telas na lateral
esquerda.

**7. Para encerrar**, volte ao terminal onde o Streamlit está rodando e
aperte `Ctrl+C`. O terminal volta ao prompt normal quando o servidor parou.

## Rodar de novo (depois da primeira vez)

Depois que você já criou a `.venv` uma vez, não repita os passos 2–4 do
início rápido — vá direto para o essencial. Dentro da pasta do projeto:

```powershell
cd "C:\caminho\para\garantiu"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Isso é tudo. Abra <http://localhost:8501> e `Ctrl+C` para encerrar, como
antes. Só repita a instalação de dependências (passo 3) se você atualizar o
`requirements.txt` ou trocar de máquina.

Não é necessário ativar a `.venv` (`.\.venv\Scripts\Activate.ps1`) nem
alterar a política de execução do PowerShell — os comandos acima chamam o
Python de dentro da `.venv` diretamente pelo caminho completo.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| `python : O termo 'python' não é reconhecido...` ou `py : O termo...` | Python não está instalado ou não foi adicionado ao PATH. Reinstale marcando "Add python.exe to PATH" e abra um **novo** PowerShell. |
| `git : O termo 'git' não é reconhecido...` | Instale o Git (link acima) e abra um novo PowerShell. |
| Comando trava/erro ao ativar a `.venv` (`não pode ser carregado porque a execução de scripts foi desabilitada`) | Não é necessário ativar a `.venv`. Use sempre `.\.venv\Scripts\python.exe -m ...` como nos comandos acima, sem ativar nada. |
| `pip install` falha com erro de rede/timeout | Verifique sua conexão com a internet e rode o comando do passo 3 novamente; ele pode ser repetido sem problema. |
| `streamlit run` diz que a porta 8501 já está em uso | Outro Streamlit já está rodando. Fecha o terminal antigo (`Ctrl+C` nele) ou rode nesta janela com outra porta: `... run app.py --server.address 127.0.0.1 --server.port 8502` e abra `http://localhost:8502`. |
| Página abre em branco ou trava carregando | Confira o terminal: se não houver erro visível ali, aguarde alguns segundos (primeira renderização é mais lenta) e recarregue a página. Se persistir, `Ctrl+C` no terminal e rode o comando do passo 5 de novo. |
| `pytest` mostra `failed` em vez de `passed` | Rode de novo isolado: `.\.venv\Scripts\python.exe -m pytest -q -k nome_do_teste_que_falhou` para ver o erro completo, e confira se os passos 2–3 foram concluídos sem erro. |
| A análise mostra apenas documentação | Confira o intervalo escolhido. O modo `AUTO` usa a última tag anterior à branch e, quando não há tags, o primeiro commit alcançável. Arquivos exclusivamente de documentação são informados, mas não influenciam o score. |
| Erro de acesso a arquivo/CSV/XML/banco de dados | O caminho informado nos campos da tela "Conectar Release" está errado ou o arquivo não existe/está aberto em outro programa. Confira o caminho e tente de novo — a aplicação mostra a mensagem de erro na própria tela. |

Se nada disso resolver, copie a mensagem de erro completa do terminal antes
de pedir ajuda — ela quase sempre diz exatamente qual arquivo ou comando
falhou.

## Usar as sete telas

1. **Conectar Release:** informe uma pasta Git local ou link HTTPS do GitHub e duas referências
   existentes (branch, tag ou commit). O padrão `AUTO` / `HEAD` compara desde
   a última tag anterior; sem tags, usa o primeiro commit alcançável.
   O diff considera os commits selecionados, não mudanças sem commit.
2. **Visão Geral do Risco:** veja o score 0–100, seus quatro fatores, os
   módulos alterados ordenados por risco e, quando houver mais de um módulo em
   risco alto/médio além do que define o score, um aviso de que o risco está
   espalhado, não concentrado só no módulo que define o score do release.
3. **Roteiro de Teste Manual:** veja o que mudou, o motivo da prioridade,
   três cenários sugeridos por módulo e deixe uma nota curta pro QA (campo
   opcional, válido só durante a sessão atual — não é salvo no histórico).
4. **Suíte Automatizada Priorizada:** consulte os testes do relatório em ordem
   de risco, status, flakiness e nome. A tela não executa comandos do projeto.
5. **Detalhe do Módulo:** consulte arquivos, correções de bugs, incidentes,
   aprovação dos testes e flakiness do módulo.
6. **Decisão de Publicação:** informe seu nome e registre publicar ou cancelar.
   Isso grava uma decisão de auditoria; não faz deploy.
7. **Histórico & Tendências:** filtre releases, bugs e incidentes por release
   ou módulo, exporte cada área em CSV e marque `ok` ou `falhou` após observar
   o resultado real. O histórico continua disponível depois de reiniciar a
   aplicação, informando a mesma pasta ou link do repositório.

Os exemplos de `sample_data/` usam módulos fictícios (`checkout`, `auth`,
`catalogo`). Eles demonstram os formatos, mas não representam os testes deste
repositório. Para uma análise real, forneça dados do produto selecionado.

### Analisar um repositório do GitHub

No campo **Pasta local ou link do GitHub**, cole, por exemplo:

```text
https://github.com/bernardohorn/garantiu
```

Use `AUTO` em **Comparar desde** e `HEAD` em **Branch do release** para
comparar o conjunto acumulado da release: desde a última tag anterior ou,
quando o repositório não tem tags, desde o primeiro commit. Também é possível informar
branches como `main`, `release/test`, tags ou hashes existentes no remoto.
O sufixo `.git` e uma barra final são aceitos. Links de páginas como
`/tree/main`, `/blob/arquivo`, URLs SSH e URLs com credenciais não são aceitos;
use o link da raiz e informe a referência no campo de branch.

Ao analisar, o app faz um clone temporário com o histórico completo e as
branches, sem checkout nem execução do código baixado. Cada análise baixa
novamente o estado remoto atual; não depende de um clone anterior. A cópia
temporária é removida depois da leitura, inclusive em caso de erro de análise.
O download tem limite de 120 segundos; para repositórios grandes, clone com
seu Git e use a pasta local. É necessário ter Git instalado e conexão à rede.

Repositórios públicos funcionam diretamente. Para privados, a conta que
executa o Streamlit deve ter autenticação HTTPS já configurada no Git (por
exemplo, no gerenciador de credenciais). A aplicação não solicita login nem
token; se o acesso não estiver disponível, mostra uma mensagem de erro.
Para repositórios renomeados, use a URL atual, pois redirecionamentos não são
seguidos automaticamente.

O app não baixa artefatos do GitHub Actions nem executa testes do repositório
remoto. Ele pode ler JUnit e CSVs versionados no commit usando caminhos
`repo:caminho/arquivo`, além de continuar aceitando arquivos locais.
Depois de importar seus relatórios, as sete telas funcionam como na análise
local. Em **Histórico & Tendências**, informe o mesmo link para consultar os
resultados sem precisar baixar novamente o repositório.

## Entradas e cálculo

- **Arquivos analisados:** somente código de produto reconhecido participa do
  score, do roteiro manual e dos detalhes de módulos. Testes, documentação,
  metadados do repositório, configurações, manifests/lockfiles, assets,
  relatórios, código gerado ou de terceiros e tipos desconhecidos são excluídos.
  As regras estão centralizadas em `garantiu/git_reader.py`; diretórios e nomes
  especiais têm precedência sobre a extensão (`tests/app.py` é teste).
  Em Conectar release e Visão geral do risco, expanda o resumo dos arquivos
  ignorados para consultar caminho, categoria e motivo. Essa lista fica na
  sessão; sua exportação e persistência ainda pertencem às próximas etapas do
  plano. Um intervalo sem código de produto não gera módulos de risco.
- **Git:** módulo é a primeira pasta do arquivo; arquivos na raiz usam o
  próprio nome. Correções são inferidas de mensagens contendo palavras como
  `fix`, `bug` ou `corrige`, no histórico alcançável pelo commit final escolhido.
- **JUnit XML:** aceita raiz `testsuites` ou `testsuite`; cada teste usa
  `classname`, `name`, status e tempo. O primeiro segmento de `classname`
  separado por ponto deve corresponder ao módulo Git. Identidades repetidas
  (`classname`, `name`) na mesma rodada são rejeitadas. Testes sem classe
  ficam em `sem_modulo`; sem nome, em `sem_nome`. Esse arquivo vem de uma
  execução no terminal ou na CI e informa resultados, não cobertura de código.
- **Contagem de incidentes:** CSV UTF-8 com `module,incident_count`.
  Linhas com módulo vazio ou contagem inválida/negativa são ignoradas. A fonte
  esperada é o histórico operacional da equipe.
- **Detalhes de incidentes:** CSV UTF-8 com `module,description,date`;
  datas no formato `YYYY-MM-DD`. O caminho pode ficar vazio se não houver
  detalhes. Cabeçalhos ou detalhes inválidos geram erro visível.

Ao informar a pasta ou o link do repositório, o Garantiu procura automaticamente
por XMLs JUnit e CSVs que tenham esses cabeçalhos. Um único candidato preenche o
campo correspondente; quando houver vários, a tela oferece uma lista para
escolha. Diretórios de dependências, builds, exemplos, fixtures e `sample_data`
são ignorados para evitar importar arquivos fictícios. A busca fica restrita ao
projeto informado e à pasta definida em **Armazenamento local**, e pode ser
repetida pelo botão **Procurar novamente**. Essa configuração fica dentro da
área **Resultados de testes e incidentes — opcional**.

Ao clicar em **Usar esta pasta**, o Garantiu cria modelos para as fontes que
não encontrar nela: `modelo-junit.xml`, `modelo-incidents.csv` e
`modelo-incident_details.csv`. Não sobrescreve arquivos existentes. O JUnit
modelo é vazio, e os CSVs contêm apenas os cabeçalhos; não representam testes
executados nem incidentes reais e não são importados na análise. Para usar um
CSV, preencha dados reais e salve uma cópia sem o prefixo `modelo-`. O JUnit
real é produzido pela execução descrita a seguir.

Para gerar o relatório junto com a análise, marque **Gerar JUnit com pytest ao
analisar** nessa área e clique em **Analisar mudanças**. A opção fica guardada
para esse projeto durante a sessão. Ela executa os testes Python locais e usa
o novo XML na análise, mesmo que outro relatório esteja informado no campo.

O projeto precisa estar no commit selecionado. Alterações pendentes e arquivos
novos não bloqueiam a execução: os testes avaliam o estado atual da pasta.
Nesse caso, a interface avisa e o nome da análise registra
`testes com alterações locais`. O diff Git continua usando os commits
selecionados; seus números não incluem alterações ainda não commitadas.
O executor usa `.venv/Scripts/python.exe` no Windows ou `.venv/bin/python`
nos demais sistemas; sem `.venv`, usa o Python que executa o Garantiu. Instale
pytest e as dependências do projeto nesse ambiente antes de analisar.
Não há instalação automática de dependências nem execução por link do GitHub.

Cada rodada salva um arquivo independente em
`<pasta escolhida>/garantiu-junit/<identificador do projeto>/<rodada>/junit.xml`.
Resultados anteriores são preservados. Essa pasta fica fora da descoberta
automática para não associar resultados antigos ou de outro projeto à análise;
o caminho gerado é mostrado na interface, com **Baixar JUnit gerado**, e pode
ser importado explicitamente.
Os caches do pytest também ficam na pasta da rodada.

Testes reprovados geram um aviso e são incorporados ao histórico. Uma suíte
sem testes gera um XML vazio e um aviso. Falhas de execução, coleta ou tempo
limite (10 minutos) interrompem a análise, sem registrar um novo snapshot nem
importar XML parcial. Para diagnosticar, execute `python -m pytest` no terminal
do projeto. A geração executa código local com as permissões do processo do
Garantiu; ela começa desativada. Os CSVs de incidentes continuam sendo entradas
manuais.

O histórico de bugs não é enviado manualmente. Ele é extraído do histórico
Git alcançável pela referência final, procurando mensagens como `fix`, `bug` e
`corrige`, e relacionado aos arquivos alterados. Todas as fontes adicionais
são opcionais; a ausência de uma delas não comprova ausência de risco.

Complexidade (linhas adicionadas/removidas), bugs e incidentes são
normalizados de 0 a 100 relativamente aos módulos alterados naquela análise.
Saúde dos testes combina 50% taxa de não aprovação atual e 50% flakiness
histórica. Cada fator pesa 25%; o score do release é o maior score de módulo.
Sem dados de testes, esse sinal não acrescenta risco. Isso não significa
que existe cobertura de testes. O JUnit não mede cobertura de código.

Flakiness é a média, por módulo, da proporção de mudanças entre status
consecutivos de cada teste, incluindo `skipped`, conforme o plano. Com uma
única observação é zero. Cada clique em analisar importa uma rodada: use
relatórios de execuções distintas, pois reimportar o mesmo resultado conta
como outra observação. Esse indicador não distingue, sozinho, instabilidade
de um teste de uma correção deliberada do código.

Para gerar um relatório dos testes deste projeto:

```powershell
.\.venv\Scripts\python.exe -m pytest --junitxml=relatorio.xml
```

Os testes desta biblioteca ficam no módulo `tests` no XML; para outros
produtos, ajuste a organização/classes de seus testes para corresponder aos
módulos Git. O score é relativo, não uma probabilidade calibrada de falha.

## Persistência e limites

Três bancos SQLite são criados automaticamente na raiz da aplicação:
`garantiu.db` (decisões), `garantiu_test_history.db` (testes) e
`garantiu_release_history.db` (snapshots de scores, fatores por módulo,
evidências de bugs, incidentes e resultados). Para escolher outro local na
interface, abra **Armazenamento local** na seção de dados opcionais, informe a pasta e
clique em **Usar esta pasta**. O Garantiu passa a utilizar esse local na sessão
atual e cria cada banco quando houver dados daquele tipo. Também é possível definir
`GARANTIU_DATA_DIR` antes de iniciar para estabelecer o local padrão. Faça
backup dos três arquivos com a aplicação encerrada; para restaurar, coloque-os
de volta na mesma pasta.

Os históricos locais são separados pelo caminho canônico do repositório.
Para GitHub, a identidade é a URL normalizada (sem `.git` e sem distinção de
maiúsculas/minúsculas), independente da pasta temporária. Uma pasta local e
um link do mesmo projeto têm históricos separados. Releases
registram a referência final e os hashes completos do intervalo comparado.
Reanalisar o mesmo intervalo cria um snapshot distinto e preserva as
evidências anteriores. O resumo apresenta apenas o snapshot mais recente de
cada release, sem duplicar a opção de release. Mover o repositório para outro
caminho inicia um novo contexto de histórico.

Datas e timestamps são armazenados em ISO 8601 e UTC. A interface os apresenta
no padrão brasileiro e no fuso `America/Sao_Paulo`; scores aparecem com uma
casa decimal e vírgula, sem alterar os valores numéricos armazenados. Os CSVs
baixados em **Histórico & Tendências** usam UTF-8 e preservam timestamps ISO e
scores com ponto decimal para permitir reprocessamento.

Esta entrega segue as 14 tarefas de `docs/garantiu-plano-de-implementacao.pdf`.
Não inclui autenticação multiusuário, conectores Jira, LLM, execução de testes
remota nem publicação automática. Use como aplicação local; o campo de nome
é uma identificação declarada, não uma autenticação.

Erros de arquivo, XML, CSV, referência Git e acesso ao banco são exibidos na
tela. Corrija a entrada e tente novamente. Sem mudanças ou sem resultados de
testes, as telas mostram estados vazios. Uma análise que falha limpa o resumo
anterior para evitar decisões com dados desatualizados. Os três bancos cobrem
domínios independentes. Dentro do histórico de releases, score, fatores por
módulo, bugs e incidentes são gravados em uma única transação: se qualquer
evidência for inválida, o snapshot inteiro é revertido.

## Verificação e referências

`python -m pytest -q` executa testes de cálculo, Git, CSV/XML, SQLite e as
sete telas com [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
Os testes de interface usam bancos temporários e incluem análise, navegação,
decisão, resultado, repetição com status diferentes, entradas inválidas e
estados vazios. O parser utiliza a interface documentada do
[junitparser](https://junitparser.readthedocs.io/en/stable/api_generated/junitparser.html).
O mapeamento da entrega está em `docs/implementacao-concluida.md`.

Para ver a cobertura de linhas por módulo:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov=garantiu --cov-report=term-missing
```

Um workflow do GitHub Actions (`.github/workflows/tests.yml`) roda essa mesma
suíte a cada push/PR para `main`; não há gate de cobertura mínima, é só
visibilidade no log do CI.

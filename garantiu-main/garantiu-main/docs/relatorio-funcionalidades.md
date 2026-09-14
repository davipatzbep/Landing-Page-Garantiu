# garantiu — Relatório de Funcionalidades

Como o produto funcionaria de ponta a ponta, o que cada tela faz por trás dos panos, e o
que um time de desenvolvimento precisaria construir para tirar isso do wireframe e colocar
no ar. Baseado no wireframe de 7 telas e no problema validado (`docs/superpowers/specs/2026-09-09-garantiu-wireframe-design.md`).

## Resumo em um parágrafo

A tela Conectar release também permite marcar **Gerar JUnit com pytest ao
analisar**. Ao analisar uma pasta local no commit selecionado, executa pytest,
inclusive com alterações pendentes, salva o XML na pasta escolhida e incorpora os
resultados reais à mesma análise. Testes reprovados são aceitos como evidência;
erro de execução interrompe a análise. A opção é inicialmente desativada e
não executa projetos remotos nem gera incidentes.

Usar esta pasta cria modelos JUnit e CSV ausentes sem sobrescrever arquivos.
São modelos vazios, identificados por `modelo-`, excluídos da análise. Testes
com alterações locais recebem aviso e identificação no nome da análise; o
diff continua restrito aos commits selecionados.

Estado implementado do filtro de arquivos: o pipeline usa apenas código de
produto reconhecido para score e roteiro. Arquivos de suporte e tipos
desconhecidos ficam fora do cálculo e podem ser auditados na sessão, com
caminho, categoria e motivo. O detalhe de bugs também exclui commits que
alteram apenas suporte no módulo. A fórmula de score ainda é a anterior;
disponibilidade das fontes e score v2 seguem pendentes no
`plano-correcao-detalhe-modulos-e-score.md`.

O garantiu lê três fontes de dado que praticamente qualquer empresa já tem (histórico do
Git, relatório de testes automatizados, e opcionalmente o rastreador de bugs/incidentes),
calcula um **score de risco por release**, e usa esse score pra duas coisas: priorizar a
suíte automatizada que já existe, e — o diferencial real — gerar um **roteiro de teste
manual em linguagem simples**, porque os dados validados mostram que teste manual nunca
desaparece, mesmo em empresas com automação madura.

## As 7 telas — o que fazem e de onde vem o dado

| # | Tela | O que o usuário faz | De onde vem o dado |
|---|------|----------------------|---------------------|
| 1 | Conectar release | Escolhe repositório, branch e intervalo de mudanças | Input do usuário (config, não é calculado) |
| 2 | Visão geral do risco | Vê o score consolidado e os módulos mais arriscados | Calculado pelo motor de score (ver abaixo) |
| 3 | Roteiro de teste manual | Lê, por módulo, o que mudou e o que testar na mão | Gerado a partir do diff + score + histórico |
| 4 | Suíte automatizada priorizada | Roda os testes automatizados na ordem certa | Relatório de testes do CI (formato JUnit XML) |
| 5 | Detalhe do módulo | Investiga por que um módulo específico está arriscado | Diff + histórico de bugs/incidentes daquele módulo |
| 6 | Decisão de publicação | Formaliza "publica ou não", com nome e hora | Input do usuário + score no momento da decisão |
| 7 | Histórico & tendências | Compara score previsto x o que realmente quebrou | Snapshots de releases anteriores + status real reportado depois |

## O motor por trás: como o score de risco (0–100) é calculado

O score é a soma ponderada de 4 sinais, cada um normalizado de 0 a 100:

1. **Complexidade da mudança** — conta arquivos alterados, linhas adicionadas/removidas e
   se a área tocada é historicamente "central" no sistema (muitos outros módulos dependem
   dela). Vem direto do `git diff` entre a branch do release e o intervalo escolhido.
2. **Histórico de bugs** — quantos bugs foram fechados nos últimos N meses apontando pros
   mesmos arquivos/módulos que mudaram agora. Vem do rastreador de bugs, quando conectado
   (é o único fator opcional — sem ele, o score roda só com os outros 3 e avisa que está
   "menos confiável").
3. **Saúde dos testes** — cobertura de código da área + taxa de flakiness dos testes
   relacionados nos últimos 30 dias. Vem do relatório de testes do CI.
4. **Incidentes anteriores** — incidentes de produção já registrados que envolveram aquele
   módulo. Vem do rastreador de incidentes (mesma fonte do fator 2, geralmente).

Os pesos entre os 4 fatores começam iguais (25% cada) e são o primeiro ponto a recalibrar
com a tela 7: se o score previsto bater com o que realmente quebrou ao longo de vários
releases, os pesos ficam confiáveis; se não bater, ajusta-se o peso do fator que mais errou.

## O que o dev vai ter que implementar, por área

### 1. Ingestão de dados (a parte que dá pra automatizar sem risco)
- Leitor de `git diff`/`git log` entre duas referências (branch/tag) — não depende de
  GitHub/GitLab específico, só de acesso ao repositório.
- Parser de relatório de testes em **JUnit XML** (formato que a grande maioria dos
  frameworks de teste e CIs já exporta) — cobertura, flakiness (comparando execuções ao
  longo do tempo) e status por teste.
- Adaptador opcional para rastreador de bugs/incidentes (Jira, Linear, etc.) via API —
  tratado como plugável, não obrigatório.
- Health-check simples (ping HTTP) pra saber se o ambiente de teste está no ar, se a
  empresa tiver um servidor de testes dedicado.

### 2. Motor de cálculo do score
- Serviço que recebe os dados brutos da ingestão, normaliza cada fator pra 0–100, aplica
  os pesos e devolve o score do release + o score por módulo (usado na tela 2 e 5).
- Precisa rodar sob demanda (quando o usuário clica "Analisar mudanças" na tela 1) e
  também em lote (pra recalcular o histórico da tela 7).

### 3. Gerador do roteiro de teste manual (tela 3) — a parte mais nova
Duas formas de implementar, do mais simples ao mais robusto:
- **Baseado em regra**: para cada módulo de risco alto/médio, montar o texto a partir de
  um template + os dados já coletados ("mudou X arquivos, histórico de bug Y, sugestão de
  cenário baseada no nome da função alterada"). Mais previsível, mais rápido de construir,
  mais raso.
- **Assistido por LLM**: dar pro modelo o diff, o histórico de bugs e o objetivo ("explique
  o impacto em português simples e sugira 2-3 cenários de teste manual") e gerar o texto.
  Mais rico, mas precisa de revisão humana antes de virar público — por isso a tela já foi
  desenhada com o rascunho editável e o campo de nota do dev, em vez de publicar o texto
  gerado direto sem revisão.

### 4. Interface (as 7 telas)
- Aplicação web com as 7 telas do wireframe, autenticação básica (quem é o usuário, qual
  empresa/repositório ele pode ver).
- Sem necessidade de nada muito customizado por tela — a maior complexidade de UI está na
  tela 3 (cards dinâmicos por módulo) e na tela 7 (gráfico previsto x real).

### 5. Registro de decisão (tela 6) — auditoria
- Tabela simples de log: quem, quando, qual score no momento, publicou ou cancelou.
  Não precisa de nada além de um banco relacional básico.

### 6. Histórico e recalibração (tela 7)
- Depois de cada release, alguém (ou uma integração com o monitoramento de produção)
  informa se aquele release "falhou" ou "ok". Isso alimenta o gráfico previsto x real e,
  no médio prazo, os pesos do motor de score (item 2).

## O que fica de fora, de propósito, e por quê

- **Provisionamento automático de credenciais de teste** — é a parte mais sensível em
  termos de segurança; não deveria ser construída sem uma etapa de validação própria.
- **Integração profunda por ferramenta específica** (ex: "app oficial do Jira") — o motor
  fala com formatos genéricos (Git, JUnit XML, webhook), não com cada ferramenta do
  mercado; isso é decisão deliberada pra não amarrar o produto a uma empresa/stack.
- **Decisão automática de publicar** — a ferramenta nunca decide sozinha; a tela 6 sempre
  exige uma pessoa confirmando, pelos motivos de rastreabilidade já discutidos.

## Se fosse construir de verdade: 3 fases

1. **Fase 1 — MVP só leitura**: telas 1, 2 e 4. Só isso já entrega o "score do release +
   suíte automatizada priorizada", sem gerar nada em linguagem natural ainda.
2. **Fase 2 — o diferencial**: tela 3 (roteiro de teste manual) e tela 6 (decisão/
   auditoria). É aqui que o produto para de ser "só mais um dashboard de CI" e vira a
   resposta ao problema validado.
3. **Fase 3 — confiança ao longo do tempo**: tela 5 (detalhe) e tela 7 (histórico/
   recalibração), que são o que sustenta o produto depois que a novidade passa.

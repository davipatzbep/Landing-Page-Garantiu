# garantiu — Wireframe de Solução (Dia 1)

## Contexto

Hackathon, Tema 4 — "Dá para entregar com segurança?". Etapa 1 (empatia/definição do
problema) já concluída com pesquisa baseada em fontes reais (DORA, Google flaky tests,
World Quality Report, CISQ, caso CrowdStrike). Este documento cobre a Etapa 2: desenhar
um conceito de solução e um wireframe de baixa fidelidade para apresentar ainda no dia 1,
explicitamente sujeito a mudanças nos dias 2 e 3.

**Problema (revisado — Etapa 2, validado com dados):** Times de desenvolvimento de
software — com ou sem QA dedicado — enfrentam dificuldade para saber onde concentrar o
teste manual (que continua indispensável para interface, UX e cenários complexos, mesmo em
empresas com automação madura) quando muitas alterações se acumulam antes de um release,
causando teste manual mal direcionado, bugs de interface escapando para produção e
retrabalho sob prazo apertado.

**Como poderíamos:** direcionar o esforço de teste manual para onde o risco realmente está,
para times que precisam publicar um release com prazo apertado e mudanças acumuladas, de
forma que o teste manual cubra o que importa sem precisar aumentar o volume de teste
manual?

*Outras versões da pergunta:*
- Como poderíamos ajudar quem testa manualmente a confiar que cobriu os pontos certos, mesmo sob prazo curto?
- Como poderíamos usar o que já é automatizado para apontar exatamente onde o teste manual precisa entrar?

<details>
<summary>Versão original (Etapa 1, hipótese antes da validação)</summary>

**Problema:** Times de desenvolvimento de software enfrentam dificuldade para decidir o
que testar primeiro e qual o risco real de publicar quando muitas alterações se acumulam
antes de um release, causando falhas em produção, retrabalho e perda de confiança nos
próprios testes.

**Como poderíamos:** dar visibilidade sobre onde está o risco de cada release para times
que acumulam muitas alterações antes de publicar, de forma que saibam o que testar
primeiro e publiquem com mais confiança sem precisar rodar mais testes?

A versão original tratava "o que testar" de forma genérica (automatizado + manual). A
validação (ver seção abaixo) mostrou que o gargalo real é especificamente o **teste
manual** — automação já cobre bem o previsível, e ninguém espera que isso mude.
</details>

## Conceito

**Nome: garantiu.** Dashboard web que, antes de cada release, cruza dados hoje espalhados
(diff do código, histórico de bugs, cobertura/estabilidade dos testes, incidentes
passados) e devolve um **score de risco do release** com a lista priorizada do que testar
primeiro.

### Score de risco — 4 fatores

1. **Magnitude/complexidade da mudança** — arquivos e linhas alteradas, área do sistema tocada.
2. **Densidade histórica de bugs** do módulo alterado.
3. **Saúde dos testes relacionados** — cobertura + taxa de flakiness.
4. **Histórico de incidentes** naquela área do sistema.

Esses 4 fatores respondem diretamente às causas levantadas na Etapa 1 (falta de
visibilidade, informação espalhada, testes instáveis virando ruído, falta de estratégia de
priorização).

## Escopo do wireframe (fluxo completo — 7 telas)

1. **Conectar Release** — setup: escolher repositório/branch e o intervalo de mudanças
   (ex.: desde a última tag) a ser analisado.
2. **Visão Geral do Risco (home)** — score geral do release, breakdown pelos 4 fatores,
   ranking dos módulos/arquivos mais arriscados, CTA para os testes recomendados.
3. **Resumo para QA** — tradução do risco técnico em linguagem simples, por módulo:
   o que mudou, por que testar aquilo, cenários sugeridos de teste manual/exploratório,
   e um espaço para o dev deixar uma nota direta pro QA. Ver "Adendo" abaixo.
4. **Lista Priorizada de Testes** — checklist ordenado por contribuição ao risco, com
   status (a rodar / passou / falhou / flaky), tempo estimado, filtro por módulo.
5. **Detalhe do Módulo/Arquivo** — por que aquele item está arriscado: o que mudou,
   histórico de bugs, incidentes, cobertura e flakiness específicos dali.
6. **Decisão de Publicação** — score atual, % do checklist concluído, quem aprova e
   quando; fecha o loop da decisão "publica ou não publica".
7. **Histórico & Tendências** — releases passados: risco previsto x resultado real
   (falhou em produção ou não), para construir confiança na ferramenta ao longo do tempo.

## Adendo (dia 1, tarde) — persona QA e tela "Resumo para QA"

Em conversa informal com um desenvolvedor (Murilo, 09/09), surgiu um ponto que a
pesquisa da manhã não tinha capturado: hoje o dev calcula o impacto de uma mudança "na
cabeça" e explica pro QA manualmente/verbalmente — não existe um artefato disso. Ou seja,
o QA também é um usuário do problema original (não sabe o que foi impactado), só que sem
acesso ao raciocínio técnico do dev.

Decisão: o QA passa a ser uma segunda persona do garantiu, com uma tela própria (não é
só reaproveitar as telas técnicas). A tela 3 — **Resumo para QA** — mora logo depois da
Visão Geral e, por módulo/área de risco, traz:

- **O que mudou**, em linguagem simples (sem nome de arquivo, sem diff).
- **Por que testar isso** — o impacto explicado, a "conta" que o dev fazia de cabeça.
- **Cenários sugeridos** — testes manuais/exploratórios em linguagem humana (não é a
  lista técnica de testes automatizados, que continua sendo a tela 4).
- **Nota do dev** — campo curto e opcional onde quem fez a mudança deixa um aviso
  direto pro QA, reproduzindo em produto a conversa que hoje é informal.

Isso não muda o problema/HMW da Etapa 1, mas amplia o público de "times de
desenvolvimento" para deixar explícito que inclui QA como consumidor do impacto, não só
quem decide publicar. Vale confirmar isso nas entrevistas de validação.

## Validação (Etapa 2) — o que mudou o problema

Fonte: relatório de entrevista/formulário com ~9-10 profissionais de diversas empresas
(`docs/Grupo 1 - 2° Hackathon ifc - Garantiu.pdf`), papéis variados (dev, QA, liderança
técnica, produto, DevOps, suporte, CTO). Achados que sustentam a reformulação do
problema:

- **Automação tem um teto estrutural, não de maturidade** (Q8): testes automatizados
  cobrem fluxos previsíveis e repetitivos (unitários, integrações técnicas, login,
  cadastro). Interface, testes gráficos, UX, cenários complexos e testes exploratórios
  seguem dependendo de execução manual — em todas as empresas representadas na amostra.
- **Mesmo esperando ganho grande com automação, ninguém espera eliminar o manual** (Q10):
  estimativas de ganho de produtividade variam de 30–40% a 80–100%, mas com a ressalva
  unânime de que revisão humana e teste exploratório manual continuam necessários.
- **A dificuldade de decidir o que testar é frequente/moderada** (Q6), com causas que
  batem com a Etapa 1 (efeito cascata de mudanças, módulos interligados, falta de tempo)
  e uma causa nova: **falta de equipe dedicada a testes** — reforça por que a solução não
  pode presumir QA dedicado.
- **Prazo apertado corta testes sem critério sistemático** (Q7): sob pressão, a equipe
  prioriza "o que dá tempo", não necessariamente o que é mais arriscado.
- **A decisão de publicar já depende de um resumo informal que alguém sobe pra quem
  decide** (Q9) — validando que a tela de Decisão de Publicação (tela 6) formaliza algo
  que já acontece na prática, não introduz um passo novo.

## Fidelidade e formato de entrega

Wireframe de **baixa fidelidade, tons de cinza** — caixas, texto placeholder, sem
cores/branding definitivos. Sinaliza claramente que é conceito/rascunho, não UI final.
Entregue como um único artifact HTML navegável (abas ou botões prev/next entre as 7
telas), sem dependências externas, para uso direto no pitch do dia 1.

## Fora de escopo (dia 1)

- Algoritmo real de cálculo do score (fica para os dias 2–3, com dados de exemplo/mock).
- Integrações reais com Git/CI (mencionadas na tela de setup, não implementadas).
- Identidade visual/branding definitiva (cores, logotipo).
- Autenticação, permissões, multi-time.

## Próximos passos (dias 2–3)

- Refletir a reformulação do problema no tom/copy do wireframe: reduzir a ênfase em
  "automatizar mais" e reforçar "direcionar o teste manual" (telas 3 e 4 principalmente).
- Ajustar telas/score conforme o restante do relatório de validação for analisado.
- Se o hackathon pedir protótipo funcional, decidir stack nesse momento (fora do escopo
  deste documento).

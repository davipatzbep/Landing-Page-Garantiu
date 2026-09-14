# garantiu — Escopo do MVP e Distribuição de Tarefas

Entregável pedido pelos professores: (1) definição clara do escopo do MVP e (2) tarefas
distribuídas entre a equipe. Baseado no problema validado (`docs/superpowers/specs/2026-09-09-garantiu-wireframe-design.md`)
e no plano de implementação completo (`docs/superpowers/plans/2026-09-09-garantiu-mvp-implementation.md`).

> **Atualização pós-entrega:** este documento registra o planejamento do MVP (4 telas,
> Tasks 1–8) feito quando ainda restavam 2 dias de hackathon. O time terminou com tempo
> sobrando e implementou as 14 tarefas do plano completo — as 7 telas estão entregues e
> testadas (ver `docs/implementacao-concluida.md`). O planejamento abaixo é mantido como
> registro histórico da decisão de priorização, não como o estado atual do produto.

## 1. Escopo do MVP

O produto completo tem 7 telas (wireframe em `docs/wireframe/garantiu-wireframe.html`).
O **MVP é um subconjunto de 4 telas** — não o subconjunto tecnicamente mais fácil de
construir, mas o mínimo que já prova a hipótese validada nas entrevistas: *"um score de
risco calculado a partir do que mudou, direcionando onde focar o teste manual, sem
precisar aumentar o volume de teste."*

**Dentro do MVP:**

| Tela | Por quê está no MVP |
|---|---|
| 1. Conectar Release | Sem ela não existe dado real pra calcular nada |
| 2. Visão Geral do Risco | O score em si — o núcleo da proposta de valor |
| 3. Roteiro de Teste Manual | O diferencial validado pelos dados (automação nunca elimina o teste manual — Q8 do relatório de entrevistas) |
| 6. Decisão de Publicação | Barata de construir (formulário + log) e fecha a narrativa de "decisão registrada" pro pitch |

**Fora do MVP (fazem parte da visão completa do produto, não da entrega mínima):**

| Tela | Por que fica de fora agora |
|---|---|
| 4. Suíte Automatizada Priorizada | É conveniência sobre o que o CI já mostra, não o diferencial sendo testado |
| 5. Detalhe do Módulo | Enriquecimento de uma tela que já existe (2 e 3), dá pra adiar |
| 7. Histórico & Tendências | Exige múltiplos releases reais ao longo do tempo — dado que uma ferramenta nova ainda não tem |

O plano técnico completo (14 tasks) já cobre as 7 telas, para não travar o time caso sobre
tempo — mas o **compromisso de entrega desta etapa é só o MVP** (Tasks 1 a 8 do plano).

## 2. Tarefas distribuídas

Distribuição baseada nos papéis que cada pessoa já tem no grupo. É um ponto de partida —
ajustem conforme disponibilidade real de cada um.

| Pessoa | Papel(is) | Tarefa nesta etapa |
|---|---|---|
| **Davi Muriel Fedrizzi Patzlaff** | Gestão | Dono do cronograma dos 2 dias restantes; garante que os checkpoints (este documento, os entregáveis anteriores) cheguem aos professores no prazo certo |
| **Anna Clara de Oliveira Figueiredo** | Comunicação | Monta a apresentação/pitch (slides ou roteiro de fala), traduz problema + solução pra linguagem de banca, cronometra o tempo de apresentação |
| **Ketlin Cristina Lodi** | Gestão, Pesquisa | Conduz entrevistas extras focadas na lacuna identificada na validação: custo do problema hoje e disposição a pagar (perguntas que faltaram no formulário original) |
| **Eduardo Schultz de Oliveira** | Dev, Pesquisa | Implementa as Tasks 1, 2 e 9 do plano — leitura do Git, histórico de bugs, histórico de execuções de teste/flakiness |
| **Vinicius Pecini Giordani** | Design, Pesquisa | Ajustes visuais finais no wireframe pro pitch; prepara os prints/telas que vão pro slide de demonstração |
| **Breno Biazus Farina** | Gestão, Pesquisa | Acompanha o progresso dos 3 devs (check-ins rápidos), apoia a Ketlin nas entrevistas extras |
| **Bernardo Pellizzaro Horn** | Design, Pesquisa | Mantém o wireframe e a documentação técnica (spec, plano, relatórios) atualizados conforme o time evolui |
| **Murilo Victor Jochkeck** | Dev | Implementa as Tasks 3, 4 e 10 do plano — leitura do relatório de testes, leitura de incidentes, priorização da suíte automatizada |
| **Pedro Henrique Renosto de Menezes** | Dev, Gestão | Implementa as Tasks 5, 6 e 7 (motor de score, roteiro de teste manual, log de decisão) e integra tudo na Task 8 (app Streamlit); lidera o sub-time de dev |
| **Victor Andrin Bonissoni** | Gestão, Comunicação | Apoia a Anna Clara na apresentação; organiza a logística da entrega final (workbook, formulários do hackathon) |

**Se sobrar tempo depois do MVP:** as Tasks 11, 12 e 13 do plano (detalhe de módulo e
histórico de releases) ficam como próximo passo natural pra quem entre os 3 devs
terminar primeiro — não são compromisso desta etapa.

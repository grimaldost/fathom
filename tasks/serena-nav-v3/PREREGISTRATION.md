# serena-nav-v3 — pré-registo da decisão

- **Data:** 2026-07-25
- **Estado:** PRÉ-REGISTO — escrito **antes** de existirem fixtures ou dados. Nada
  neste documento pode ser alterado depois do primeiro ensaio pago sem registar a
  alteração numa secção de emendas datada, com a razão.
- **Antecedentes:** `serena-nav-v1` (34 ficheiros) saturou e a sua primeira execução
  foi invalidada por variante desarmada. `serena-nav-v2` (422 ficheiros, 27 ensaios,
  $21,51) deu um resultado indicativo mas não conclusivo: serena 9/9 contra 8/9 das
  outras duas variantes, com economia plana. Detalhe em
  `feedback/2026-07-25-serena-nav-arming-defect.md` e
  `feedback/2026-07-25-serena-nav-v2-scale-run.md`.

---

## 1. A pergunta é uma decisão, não uma hipótese

**Devo colocar o serena no meu stack — e, se sim, em que forma?**

As saídas possíveis são quatro, e o desenho tem de as separar:

| saída | significado operacional |
|---|---|
| **A. Adotar sempre-ligado** | serena montado por omissão em todas as sessões de código |
| **B. Adotar por projeto** | montado só em repositórios grandes / trabalho de refactorização |
| **C. Recusar, promover alternativa** | serena fora; a disciplina de navegação com as ferramentas existentes passa a skill do stack |
| **D. Recusar** | sem lugar no stack; revisitar apenas com evidência nova |

Um resultado nulo com potência adequada **é** uma decisão (D ou C), não um falhanço
do teste.

## 2. Efeitos mínimos de interesse (pré-registados)

Nenhum número razoável de ensaios prova um efeito de 3% — e um efeito de 3% não
justifica uma dependência no stack. Por isso o teste é dimensionado para detectar o
efeito que **mudaria a decisão**:

| eixo | efeito mínimo de interesse (EMI) |
|---|---|
| qualidade nas famílias grep-incapazes (1–3) | **≥ 20 pontos percentuais** de taxa de sucesso do `serena` sobre o `grep-discipline` |
| economia | **≥ 15%** de redução de custo a qualidade igual (ou, no sentido inverso, custo não pior que **+10%** para justificar uma vitória de qualidade) |
| custo de espectador (família 7) | um agravamento **> 10%** de custo ou turnos em tarefas que não precisam de navegação chumba a saída A e empurra para B |
| deslocação de tier (eixo de modelos) | `haiku + serena` igualar ou superar `sonnet bare` nas famílias 1–4 **sem** custo superior |

Se, com a potência planeada, nenhum destes limiares for atingido, a decisão é C ou D.

## 3. Variantes

| variante | ferramentas base | instruções injectadas | serena montado |
|---|---|---|---|
| `bare` | Read, Write, Edit, Glob, Grep, Bash(python:*) | ❌ | ❌ |
| **`grep-discipline`** | as mesmas | ✅ método sistemático **com as ferramentas existentes** | ❌ |
| `serena` | as mesmas | ✅ instruções de navegação simbólica | ✅ (ferramentas `mcp__plugin_serena-arm_serena__*`) |

**O `brief-only` do v2 é descartado**: já está caracterizado (é nocivo — instruções
que pressupõem uma ferramenta ausente degradam o agente) e não informa mais nada.

**O `grep-discipline` é a novidade decisiva.** O v2 comparou o serena contra
doutrina-sem-instrumento, o que é um adversário fraco. O v3 compara-o contra a
**melhor versão do que já existe de graça**: instruções que ensinam a enumerar
candidatos, verificar cada um e confirmar ausências usando grep e leitura dirigida.
Se esta variante fechar o buraco de completude, o serena é dispensável — e o
subproduto (a skill) fica.

## 4. Famílias de tarefas e o seu único desfecho primário

Cada família declara **um** desfecho primário. Os restantes critérios são
secundários/exploratórios e **não podem** sustentar a decisão. Isto existe para
evitar o erro do v2: com muitos critérios, olhar para todos e escolher o que
separa produz efeitos espúrios.

| # | família | pergunta ao agente | desfecho **primário** | porque o grep não chega |
|---|---|---|---|---|
| 1 | `implements-audit` | listar todas as implementações do protocolo `P` | igualdade exacta de conjuntos | **incapacidade estrutural**: nenhum texto liga `class FooAdapter` ao `Protocol` que cumpre |
| 2 | `override-map` | que subclasses redefinem `m`, quais herdam | igualdade exacta do mapa | herança atravessa ficheiros sem repetir o nome |
| 3 | `dead-symbol-proof` | de 10 candidatos, quais estão realmente sem uso | igualdade exacta do conjunto de mortos | **completude negativa**: provar ausência exige rejeitar todos os falsos positivos |
| 4 | `deep-closure` | fecho transitivo com 3–4 saltos | igualdade exacta de conjuntos | v2 mostrou ser onde o `bare` falha; v3 aumenta profundidade e escala |
| 5 | `shadowed-rename` | mudar nome com sombreamento, decoradores, reexportações | distratores byte-idênticos (sha256) **e** suite verde | o mesmo texto refere coisas diferentes conforme o escopo |
| 6 | `real-repo` | impacto + rename num repositório OSS real vendorizado | igualdade de conjuntos (impacto) / suite verde (rename) | validade externa: responde a "isso só funciona no teu corpus fabricado" |
| 7 | `bystander-cost` | correcção local que **não** precisa de navegação | **custo e turnos** (a qualidade é controlo) | mede o preço de ter a ferramenta ligada quando é inútil |

**Famílias 1–3 são as decisivas** (grep-incapazes). A 4 é confirmação de escala, a 5
é precisão, a 6 é validade externa, a 7 decide a *forma* da adoção (A vs B).

## 5. Corpus

- **~1.500 ficheiros** Python sintéticos (contra 422 no v2), com hierarquias de
  classes, `typing.Protocol`, decoradores e reexportações.
- **Distratores não formuláicos**: o v2 gerava 5 tipos de distrator em ciclo, o que
  é um padrão aprendível. No v3 os distratores variam em forma, densidade e
  localização, gerados a partir de uma semente fixa mas sem periodicidade.
- **Verdade do lado do arnês**: `truth.json` junto do verificador, nunca em
  `fixtures/` (o fathom só copia `fixtures/`). Nenhuma pista da solução nos testes
  ou nos nomes de ficheiros.
- **Família 6** vendoriza um commit fixado de um repositório OSS real do mundo de
  dados (candidatos: `sqlfluff`, `dagster`), com licença compatível registada.

## 6. Eixo de modelos

| célula | propósito |
|---|---|
| `claude-sonnet-5` × {bare, grep-discipline, serena} | comparação primária |
| `claude-haiku-4-5` × {bare, serena} | **deslocação de tier**: uma ferramenta que permita a um modelo barato igualar um caro nas tarefas de navegação liga-se directamente à política `choosing-models` e à governação de tiers do convoy — seria o argumento de adopção mais forte possível, porque é economia composta |
| Opus | **excluído**: tarefas de navegação nunca serão roteadas para lá; a célula teria custo sem valor decisório |

Verificado antes de escrever fixtures (2026-07-25): a string `claude-haiku-4-5` é a
convenção já usada em 9 cenários deste repo, o CLI responde a ela, e a tabela de
preços do fathom resolve a família por subcadeia (`haiku` → tier fraco), pelo que a
contabilidade de custo das células haiku é correcta. Um id não reconhecido cairia em
preço de opus — era o risco silencioso que esta verificação eliminou.

## 7. Potência e plano de análise

- **n = 5 por célula** nas comparações primárias (sonnet × 3 variantes × famílias 1–5).
- **n = 3** nas secundárias (haiku, `real-repo`, `bystander-cost`).
- **Economia lê-se por mediana e IQR**, nunca só pela média — no v2 a média de cache
  inverteu de sinal entre n=2 e n=3 e produziu uma conclusão falsa. Qualquer
  afirmação sobre economia exige a dispersão ao lado.
- **Truncagem conta-se e reporta-se**: uma variante que bata no limite de turnos tem
  a taxa de sucesso lida como **limite inferior** (no v2 o `brief-only` correu a 41,1
  turnos contra um limite de 40, o que confunde "navegou mal" com "ficou sem
  orçamento").
- **Limite de turnos apertado a 25** nas famílias 1–5 (contra 40 no v2), para forçar
  eficiência em vez de força bruta.
- Intervalos de confiança de Wilson são **larguras heurísticas** (ensaios repetidos
  são correlacionados) — servem para ver sobreposição, não para inferência formal.

## 8. Portão anti-saturação (DoR — antes de qualquer gasto)

O v2 ensinou que escala é necessária mas **não suficiente**: 11 dos 14 critérios
ficaram a 100% em todas as variantes. Antes de pagar, cada família tem de passar:

1. **Razão de discriminação declarada** — nº de ficheiros que o sinal ingénuo
   (grep/leitura directa) devolve, contra nº de sítios genuínos. Impressa pelo
   selftest.
2. **Estimativa de tecto** — um piloto de **1 ensaio `bare`** por família mostra que
   o `bare` **não** passa o desfecho primário de forma trivial. Uma família em que o
   `bare` passe à primeira volta para a bancada e **não** entra na matriz paga.
3. **Vermelho-verde dos verificadores** — vermelho no fixture intocado, verde numa
   solução de referência scriptada (como no v1 e v2, onde apanhou dois bugs de
   autoria reais).
4. **Armamento provado** — `arming_probe.py` com `ARMING: PASS` na variante `serena`,
   nas duas células de modelo.

Uma família que falhe 1 ou 2 é **cortada antes de gastar**, não corrigida depois.

## 9. Regra de decisão (pré-registada — aplica-se aos desfechos primários apenas)

```
1. O serena vence as famílias 1-3 por >= 20pp sobre grep-discipline,
   com custo não pior que +10%?
      SIM -> o custo de espectador (familia 7) é <= 10%?
                 SIM -> SAÍDA A: adotar sempre-ligado
                 NÃO -> SAÍDA B: adotar por projeto (repos grandes / refactor)
2. NÃO, mas o grep-discipline supera o bare nas famílias 1-3 por >= 20pp?
      -> SAÍDA C: recusar o serena; promover o grep-discipline a skill do stack
3. NÃO, e nada separa com a potência planeada?
      -> SAÍDA D: recusar; revisitar só com evidência de uso real
```

**Três das quatro saídas produzem valor independentemente do serena**: uma decisão de
adopção calibrada, uma skill gratuita, ou uma recusa firme que poupa uma dependência.
É isso que torna o gasto defensável.

## 10. Regras de paragem

- Se, depois do bloco núcleo, o ramo 2 ou 3 já for evidente, **para-se** e não se
  gastam os blocos secundários.
- Se o piloto revelar custo por ensaio > $1,50, reduz-se n=5 para n=3 nas primárias e
  regista-se a alteração como emenda.
- Se qualquer família apresentar erro de infraestrutura em > 1 ensaio, suspende-se
  essa família e diagnostica-se antes de continuar.

## 11. Orçamento e faseamento

| bloco | ensaios | estimativa |
|---|---|---|
| autoria + selftest + sondas | 0 | **$0** (+ cêntimos nas sondas) |
| piloto de calibração (fixa o preço real por ensaio) | ~6 | $5–10 |
| núcleo: sonnet × 3 variantes × famílias 1–5 × n=5 | 75 | $55–75 |
| haiku × {bare, serena} × famílias 1–4 × n=3 | 24 | $6–10 |
| `real-repo`: sonnet × 3 variantes × 2 tarefas × n=3 | 18 | $18–25 |
| `bystander-cost`: {com, sem} × 3 tarefas × n=3 | 18 | $8–12 |
| **total** | **~141** | **$90–120** |

Núcleo mínimo decisório, se se cortar: famílias 1, 3, 4 + as três variantes + haiku
(~$40–50). O bloco `real-repo` é o primeiro a cair, porque a validade externa também
se obtém pilotando o serena em trabalho real durante duas semanas — que o anel
`pilot` do radar já autoriza.

## 12. Ameaças à validade, e o que este banco NÃO decide

- **Saturação** (a ameaça principal, já materializada no v2) — mitigada pelo portão
  §8.2, que corta famílias fáceis antes de gastar.
- **Corpus sintético** — mitigado pela família 6; não eliminado.
- **Multiplicidade** — mitigada pelo desfecho primário único por família (§4).
- **Instabilidade de médias** — mitigada por mediana + IQR obrigatórios (§7).
- **Confusão por truncagem** — mitigada pela contagem de truncagem (§7).
- **Versão do serena** — fixada em `serena-agent==1.6.1`; o resultado não se
  generaliza a versões futuras.
- **A terceira perna da adopção — encaixe no trabalho real — não é medida por este
  banco.** Mas é mapeável: a família 4 (`deep-closure`) *é* a análise de impacto que
  faço no treasuryutils antes de alterar um schema com consumidores a jusante; a
  família 3 (`dead-symbol-proof`) é a auditoria de código morto numa migração. Se as
  famílias que vencerem forem as que correspondem ao trabalho real, esta perna fecha
  por inspecção. Se vencerem apenas as que não correspondem, a decisão é B ou D
  mesmo com vitória técnica.

## 13. Emendas

_(nenhuma; o desenho nunca chegou a ensaio pago — ver §14)_

---

## 14. PRÉ-MORTEM: NOT_READY — o desenho não avança nesta forma

**Data:** 2026-07-25. Painel adversarial de 5 lentes independentes (validade
estatística, viabilidade do arnês, corpus/*cheatability*, adversarial-nulificação,
`keel:pre-mortem-review`) + síntese. 6 agentes, 157 usos de ferramenta.
Transcrição: `subagents/workflows/wf_827caf97-3a4/journal.jsonl`.

**Veredito: NOT_READY — 14 achados bloqueantes.** A síntese conclui que não são
remendos: são cinco mudanças de *forma* que compõem uma experiência diferente.

### 14.1 O achado que anula a premissa central (verificado no código do serena)

`serena-agent==1.6.1` **não responde a `textDocument/implementation` em Python.**
`supports_implementation_request()` devolve `False` por omissão
(`solidlsp/ls.py:390`), com override para `True` apenas em Angular, C#, Eclipse JDT,
gopls, rust-analyzer e typescript-language-server — **não há override para Python** —
e `FindImplementationsTool` está registada **sem guarda de capacidade**, logo devolve
vazio e a variante armada degrada-se silenciosamente para grep.

Consequências:

- **A família 1 (`implements-audit`) é impossível como escrita**, e com ela cai a
  justificação que eu próprio dei para o v3: *"testa a única coisa em que o serena
  não é simplesmente grep mais rápido"*. Para Python, essa coisa **não existe** nesta
  versão. A família 2 (`override-map`) cai pela mesma razão (não há caminho dedicado
  de hierarquia de tipos para Python; `JetBrainsTypeHierarchyTool` é só JetBrains).
- **O que sobrevive** é `find_referencing_symbols` (o pyright suporta), ou seja
  **grep melhor** — precisamente o que o v2 já mediu como vantagem modesta com
  economia plana.
- O `arming_probe.py` é insuficiente: prova que a ferramenta é *invocável*, não que
  *responde*. É preciso uma **sonda de capacidade por família** — chamar a ferramenta
  que a premissa exige contra um fixture verificado à mão e exigir resultado correcto
  e não-vazio.

Nota da síntese sobre o processo: *"quatro lentes aceitaram a família e criticaram a
sua estatística; uma leu a dependência fixada. Essa assimetria é o resultado mais
valioso deste painel."*

### 14.2 O corpus: a alavanca de escala nunca engatou

Medido: o fixture do v2 tem **441 ficheiros mas ~15 mil tokens** (60.834 bytes de
Python, ficheiro mediano ~138 bytes). Isso é **um quarto de uma janela de contexto** —
logo o v2 nunca testou escala, e 1.500 ficheiros da mesma forma dariam ~54 mil tokens,
ainda dentro de uma janela. Explica a saturação do v2 por completo e invalida a
minha leitura de "422 ficheiros = escala".

Corolário: **o baseline de $0,67/ensaio que registei não serve para orçamentar bancos
grandes** — foi medido num corpus ~100× menor em tokens. O intervalo honesto de
planeamento é **$2–4/ensaio**, e só um piloto o pode fixar.

### 14.3 Potência: desfechos binários tornam o gasto inútil

Fisher exacto, bilateral, α=0,05. Com n=5 vs n=5 só três tabelas em todo o espaço de
resultados são significativas; um fosso observado de 40pp (5/5 vs 3/5) dá **p=0,22**.
Potência no EMI pré-registado de 20pp: **1,9%**. Para 80% de potência a 20pp seriam
necessários **46–90 ensaios por variante** (≈$370–630 só no núcleo). E nas células
n=3 **nenhum resultado possível atinge significância** — os blocos haiku, `real-repo`
e `bystander` (~$32–47) não podiam devolver nada.

A correcção de forma: **desfecho graduado** (F1 contra o conjunto-verdade, com
contagens de omissão e falso-positivo ao lado) em vez de igualdade exacta binária.
Com dispersão emparelhada de 0,20–0,25, 80% de potência a Δ=0,20 exige **8–18
instâncias emparelhadas** — comprável. E a **unidade de replicação** muda de
*repetições do mesmo corpus* (n efectivo ≈ 1) para **instâncias semeadas
independentes, como task ids**.

### 14.4 O serena traz três tratamentos, não um

Verificado: `--context ide-assistant` resolve para `claude-code`
(`serena/config/context_mode.py:236`), cujo prompt diz *"Read → FORBIDDEN for
discovery"*, *"Edit → FORBIDDEN"* e traz duas directivas **CRITICAL**. Somando o meu
brief, a variante armada carrega **as ferramentas + o meu texto + o prompt do
serena**. Como o v2 mediu texto-sozinho a +28% tokens / +20% USD, **uma vitória do
serena não é atribuível ao language server** e as saídas A e C tornam-se
indistinguíveis.

Correcção: um **único brief neutro quanto ao mecanismo**, byte-idêntico nas duas
variantes tratadas (`bare` / `discipline` / `discipline+serena`), com os sha256
congelados neste documento.

### 14.5 Fugas e atalhos (todos gratuitos de corrigir, todos verificados)

- **Todas as variantes têm `Bash(python:*)`** — um script AST de ~20 linhas responde
  às famílias 1, 2 e 4 exactamente, de forma independente da variante. Correcção:
  remover Bash **simetricamente** das famílias de leitura, e adicionar **oráculos de
  atalho** (`cheat_grep.py`, `cheat_ast.py`, `cheat_runtime.py`) como portão: uma
  família cujo oráculo de atalho passe é cortada antes de gastar.
- **Fuga por `__pycache__`:** existem **57 ficheiros `.pyc` dentro de
  `tasks/serena-nav-v2/*/fixtures/`**, e `stage_task` copia `fixtures/` com
  `ignore_patterns('.git')` apenas — logo foram montados em todos os workspaces do
  v2. Um `ls __pycache__` revela que módulos foram importados. **É um defeito do
  arnês, não do banco**, e afecta qualquer banco futuro.
- `trial_timeout_s` em `task.toml` é **configuração morta** (o adapter usa só o do
  cenário); o `timeout_s` do verificador tem omissão de **60 s**, insuficiente à
  escala pretendida, e um verificador que estoure marca o ensaio `errored` — que não
  é chave de resume e por isso **é pago outra vez** em cada relançamento.
- O serena escreve `.serena/` no projecto activado, e a lista de exclusão de
  `extract_result_view` não a conhece — um critério "fontes intocadas" sobre a árvore
  inteira **falharia a variante armada pelo seu próprio artefacto**.

### 14.6 O conflito que decide o destino do desenho

Citando a síntese: *"esta é uma experiência de ~$150–250 que decide, ou uma
experiência de ~$100 que não decide."* A correcção do corpus e o tecto de $90–120
estão em **conflito directo** e só um sobrevive. Com o corpus correcto, o núcleo
sobrevivente (2 famílias × 3 variantes × 12 instâncias = 72 ensaios) custa
**$145–290**. Se esse valor não estiver disponível, a jogada honesta é **uma família
com potência adequada**, nunca duas sem nenhuma.

### 14.7 O que a síntese rejeitou (para o registo)

8 achados foram rejeitados, entre eles: a auditoria de transcrições pós-hoc (reintroduz
discricionariedade que o pré-registo existe para remover — a remoção simétrica do Bash
resolve o mesmo de graça), uma quarta variante `script-discipline` (é outra
experiência), o renomear de variantes para a vista de tiers (não compra nada depois de
o eixo haiku cair), e — com pena — a ideia mais forte do painel: **construir o corpus
plantando estruturas dentro de 3–4 pacotes reais vendorizados**. Essa fica como
**forma do v4**: subsume a família 6, elimina "corpus sintético" das ameaças, e dá
tamanhos e ambiguidade reais de graça, ao custo de semanas de autoria.

### 14.8 Decisão sobre este documento

O desenho **não avança nesta forma**. As opções apresentadas ao autor são: (a)
reconstruir na forma sintetizada, a ~$150–250 mais autoria substancial; (b) tomar a
decisão barata que o §14.1 já habilita — o serena, em Python e nesta versão, é
"grep melhor", não uma capacidade nova — seguida do piloto de duas semanas em uso
real que o anel `pilot` do radar já autoriza; (c) uma família com potência adequada.
Este documento fica **congelado como pré-registo não executado**, e qualquer
reconstrução parte da forma do §14 e não do corpo original.

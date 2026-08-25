# Roadmap — `prumo`

Etapas de implementação, não releases formais. Cada etapa só começa quando a anterior
está de pé — ver [ARCHITECTURE.md §22](ARCHITECTURE.md#22-critério-de-reutilização)
sobre por que essa ordem importa: construir a HP Prime cedo demais é o jeito mais
fácil de acabar com uma `HPPrimeAutomator` disfarçada de `GUIAutomator`.

## Etapas

- [x] **Etapa 0 — Especificação.** Arquitetura, responsabilidades, nomenclatura,
  estados, exceptions, formato JSON, contrato das interfaces. **Sem código de HP
  Prime.** → [ARCHITECTURE.md](ARCHITECTURE.md)
- [x] **Etapa 1 — Core.** `Locator`, `WindowManager`, `InputDriver`, `GUIAutomator`,
  `Exceptions`. Critério: `automator.click("button")` funciona (`src/prumo/core/`,
  `src/prumo/drivers/`).
- [x] **Etapa 2 — Configuração.** JSON loader, schema, validator, mapper.
  `config/loader.py` rejeita chave duplicada; `config/schema.py` valida schema
  version, campos obrigatórios e cada locator; `tools/validate_config.py` e
  `tools/mapper.py` prontos como scripts de linha de comando.
- [x] **Etapa 3 — Estado.** `GUIState`, `StateManager`, `wait_until`, timeouts
  (`core/state.py`, `AutomationTimeoutError`).
- [x] **Etapa 4 — Interrupções.** `Interruption`, `InterruptionManager` (`core/events.py`),
  verificadas em `GUIAutomator.precheck()` antes de toda ação.
- [x] **Etapa 5 — Recuperação.** `RecoveryManager` (`core/recovery.py`) — `ensure_ready`
  só aciona recuperação se houver passos registrados; sem eles, propaga o timeout.
- [x] **Etapa 6 — Logging.** Cada ação loga com um `op=<id>` sequencial via
  `logging.getLogger("prumo")` (`core/automator.py`) — sem módulo de logging dedicado,
  como o próprio §18 descreve (é convenção de mensagem, não infraestrutura nova).
- [x] **Etapa 7 — Mock Driver.** `drivers/mock.py` + suíte em `tests/unit/` (39 testes,
  zero dependência de GUI real). **Cumprida antes de qualquer código de HP Prime.**
- [x] **Segunda aplicação.** `tests/unit/test_second_application.py` — uma
  `LegacyApplication(GUIAutomator)` fictícia, sem tocar em `core/`, `drivers/` ou
  `config/`. Prova mínima do critério — ver
  [ARCHITECTURE.md §22](ARCHITECTURE.md#22-critério-de-reutilização). Reforçada por um
  segundo consumidor real: a extração da Etapa 8 abaixo.
- [x] **Etapa 8 — HP Prime.** **Não entra neste repositório** — é
  [`HpPrimeCalculator`](https://github.com/matheusvivasr/hp-prime-automation/blob/main/core/calculadora.py)
  em `hp-prime-automation`, consumindo `prumo` como dependência editável. Os 51
  locators calibrados foram convertidos do formato antigo (`dx,dy` absoluto) para o
  schema relativo `[0,1]` do `prumo`; 6 testes offline com `MockDriver` provam a
  resolução de pixel sem abrir a HP Prime. `HpPrimeKeyboard`/`Result` como classes
  dedicadas não existiram — a legenda de tecla foi pra `core/keymap.py` (só
  metadado normal/shift/alpha, sem geometria).
- [ ] **Etapa 9 — API semântica.** `press_key(codigo)` e `color_matches()` existem;
  `ExpressionParser`/`type_expression()`/`get_result()`/`reset()` — que exigiriam ler o
  display da calculadora, não só clicar teclas — ainda não. Ver "O que ainda não foi
  migrado" no `README.md` do `hp-prime-automation`.
- [ ] **Etapa 10 — Transações.** `with calc.transaction(): ...` já existe em
  `GUIAutomator` (Etapa 1) e `HpPrimeCalculator` herda; nenhuma macro real usa ainda.
- [~] **Etapa 11 — End-to-end.** Geometria validada em 25/08/2026 contra a HP Prime
  real, em vários capítulos — vale o histórico completo porque cada um corrigiu um
  jeito diferente de "parecer certo" e estar errado:

  1. **Dois bugs de config**, só visíveis rodando contra a aplicação: título
     configurado (`"HP Prime Virtual Calculator"`) não batia com o real
     (`"HP Prime"`); locators são relativos ao **teclado**, não à janela inteira.
  2. **Calibração por offset fixo** — acertava uma tecla, errava outra (erro de
     escala disfarçado de deslocamento).
  3. **2 pontos** resolvem o sistema exato mas não expõem leitura ruim de mouse
     fora do centro — a reta "fecha" mesmo com um dos dois pontos errado.
  4. **4 pontos + mínimos quadrados**: qualquer leitura ruim vira resíduo alto
     contra os outros 3. Resolveu bem — só que só pra grade principal.
  5. O teclado **não é uma grade única**: o aglomerado de cima (Apps/Symb/Plot/
     Help/View/Menu/Home/Esc/CAS + disco de navegação) é separado por um espaço
     não-proporcional — precisou de calibração própria (4 pontos, mesma técnica).
  6. **O chão em si mudou**: a HP Prime tem pelo menos dois MODOS DE LAYOUT
     (retrato estreito vs. paisagem larga com teclado do lado do display) — não é
     escala do mesmo arranjo, é outra estrutura. Toda calibração por fração fixa
     relativa a `window.geometry()` (itens 2-5) morreu no mesmo dia em que a
     janela mudou de modo no meio da sessão.
  7. **Solução definitiva**: parar de calibrar frações fixas e **localizar 2
     âncoras por zona direto na tela**, a cada execução, por template matching
     (`pyautogui.locateOnScreen` + opencv, recortes em `config/templates/*.png`).
     Não depende de `window.geometry()` nem de nenhuma constante calibrada à mão
     — funciona em qualquer modo de layout porque acha os botões onde eles
     realmente estão, não onde uma fórmula prevê que deveriam estar. Cache por
     geometria de janela evita refazer a busca a cada tecla.
  8. De quebra, o processo de comparar âncoras vizinhas achou um **erro real na
     calibração original** (anterior a todo esse capítulo): SYMB/HELP/ARUP
     compartilhavam a fração y de APPS/ESCC mas ficam ~14px mais acima na tela de
     verdade — corrigido no JSON via a mesma técnica (`GetCursorPos`).

  Overlay das 51 teclas confirmado centralizado nos dois modos de layout
  testados. Ainda não houve um `press_key()` clicando de verdade contra a
  aplicação — só leitura de posição e overlay visual — próximo consumidor real
  que quiser confiar cegamente deve confirmar isso antes de rodar macro sem
  supervisão. O esquema de âncora-por-imagem é genérico o bastante pra virar
  capacidade do próprio `prumo` (hoje vive só em `hp-prime-automation`) — ver
  nota de migração acima.

## Nota de migração — `hp-prime-automation`

O repo [`hp-prime-automation`](https://github.com/matheusvivasr/hp-prime-automation)
(em `the-calc-project/hp-prime/`) não é absorvido inteiro. Ele **permanece como
consumidor externo** do `prumo` — é a prova viva do critério da Etapa 8. Extração
prevista, mapeando código existente → módulo novo:

| Origem (`hp-prime-automation/`) | Destino (`prumo/`) |
|---|---|
| `core/janela_utils.py` | `src/prumo/drivers/window.py` (`WindowManager`) |
| `core/acoes.py` | `src/prumo/drivers/pyautogui_driver.py` + ações do `automator.py` |
| `core/coordenadas.py` | `src/prumo/config/loader.py` + `src/prumo/core/locator.py` |
| `core/dpi_awareness.py` | driver |
| `core/logger.py` | logging estruturado (Etapa 6) |
| `core/macro_base.py` | `src/prumo/core/automator.py` / semente de `transaction.py` |
| `calibrate.py` + `pos_finder.py` | `tools/mapper.py` (Etapa 2) |

Fica no `hp-prime-automation`, sem migrar: `config/coordenadas_*.json` (mapa é da
aplicação, não do framework), `macros/`, `run_macro.py`. Ele passa a depender de
`prumo` como biblioteca em vez de reimplementar a camada de automação.

**Lição de processo (25/08/2026)**: `locate_on_screen`/`AnchorZone` (§9.2) nasceram
resolvendo um problema real no `hp-prime-automation` e ficaram lá, implementados
localmente, por um ciclo inteiro antes de serem promovidos pra cá — mesmo sendo
capacidade genérica desde o primeiro commit, sem nada de HP Prime. O critério certo
não é "isso é específico da aplicação?" no momento em que se escreve o código sob
pressão de resolver algo agora — é perguntar de novo *depois*, com a pressão
resolvida: "agora que existe, alguma outra aplicação usaria isso do jeito que
está?". Se sim, promove antes de acumular mais um consumidor em cima do lugar
errado.

## Versões (evolução futura)

```text
v0.1  Core funcional
v0.2  State Manager robusto
v0.3  Recovery
v0.4  Transactions
v0.5  Screenshot/OCR opcional
v0.6  Windows UI Automation driver
v0.7  Múltiplas aplicações
v0.8  API para agentes/LLMs
v0.9  Hardening
v1.0  Framework estável
```

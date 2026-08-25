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
  real, em duas rodadas. **Primeira rodada** (print + overlay das 51 teclas via
  `MockDriver`): encontrou e corrigiu dois bugs reais que só apareceriam rodando
  contra a aplicação — título configurado (`"HP Prime Virtual Calculator"`) não
  batia com o real (`"HP Prime"`), e os locators são relativos ao **teclado**, não à
  janela inteira. Mas o overlay saiu sistematicamente descentrado (offset fixo
  `(22,17)` acertava a Enter e errava a Apps — sinal de erro de **escala**, não só
  de deslocamento). **Segunda rodada**: leitura direta de `GetCursorPos` (só
  leitura, sem `computer-use`) sobre o centro real de duas teclas em cantos opostos
  (ENTR, APPS), resolvendo o sistema linear fração→pixel pros dois eixos —
  substituiu o offset fixo por 4 constantes calibradas
  (`KEYPAD_LEFT/TOP/WIDTH/HEIGHT_FRACTION`). **Terceira rodada**: a 1ª leitura de
  ENTR (1309,546) tinha o mouse levemente fora do centro — dava
  `KEYPAD_WIDTH_FRACTION > 1.0` (teclado "mais largo que a janela", estranho
  fisicamente). Releitura (1281,546) resolveu: teclado em ~96% da largura da
  janela, e o overlay final cai centralizado nas 51 teclas, incluindo a própria
  Enter. Lição registrada no docstring de `HpPrimeCalculator`: desconfiar de
  `WIDTH/HEIGHT_FRACTION > 1.0` como sinal de leitura imprecisa, não de bug.
  Ainda não houve um `press_key()` clicando de verdade (só leitura de posição e
  overlay visual) — próximo consumidor real que quiser confiar cegamente deve
  confirmar isso antes de rodar macro sem supervisão.

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

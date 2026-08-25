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
  [ARCHITECTURE.md §22](ARCHITECTURE.md#22-critério-de-reutilização). Vale reforçar
  com um segundo consumidor real quando a extração da Etapa 8 acontecer.
- [ ] **Etapa 8 — HP Prime.** `HpPrimeCalculator`, `HpPrimeKeyboard`,
  `ExpressionParser`, `Result`. **Não entra neste repositório** — é a extração para
  `hp-prime-automation` descrita na nota abaixo; falta fazer.
- [ ] **Etapa 9 — API semântica.** `calc.type_expression()`, `calc.press_enter()`,
  `calc.get_result()`, `calc.reset()` — em `hp-prime-automation`, sobre o `prumo`.
- [ ] **Etapa 10 — Transações.** `with calc.transaction(): ...` já existe em
  `GUIAutomator` (Etapa 1); falta o consumidor real usá-la.
- [ ] **Etapa 11 — End-to-end.** Cenários reais automatizados contra a HP Prime —
  depende das Etapas 8-10 em `hp-prime-automation`.

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

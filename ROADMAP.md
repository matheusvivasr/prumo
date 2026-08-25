# Roadmap — `prumo`

Etapas de implementação, não releases formais. Cada etapa só começa quando a anterior
está de pé — ver [ARCHITECTURE.md §22](ARCHITECTURE.md#22-critério-de-reutilização)
sobre por que essa ordem importa: construir a HP Prime cedo demais é o jeito mais
fácil de acabar com uma `HPPrimeAutomator` disfarçada de `GUIAutomator`.

## Etapas

- [x] **Etapa 0 — Especificação.** Arquitetura, responsabilidades, nomenclatura,
  estados, exceptions, formato JSON, contrato das interfaces. **Sem código de HP
  Prime.** → [ARCHITECTURE.md](ARCHITECTURE.md)
- [ ] **Etapa 1 — Core.** `Locator`, `WindowManager`, `InputDriver`, `GUIAutomator`,
  `Exceptions`. Critério: `automator.click("button")` funciona.
- [ ] **Etapa 2 — Configuração.** JSON loader, schema, validator, mapper. Critério:
  `GUI → mapper → config.json → GUIAutomator`.
- [ ] **Etapa 3 — Estado.** `GUIState`, `StateManager`, `wait_until`, timeouts.
  Critério: `automator.wait_ready()`.
- [ ] **Etapa 4 — Interrupções.** `Interruption`, `InterruptionManager`, popup
  handling, error handling.
- [ ] **Etapa 5 — Recuperação.** `RecoveryManager`, reset, retry, abort.
- [ ] **Etapa 6 — Logging.** operation ID, transições de estado, ações, erros,
  recuperação.
- [ ] **Etapa 7 — Mock Driver.** Testes completos sem GUI. **Obrigatória antes de
  crescer a API da HP Prime.**
- [ ] **Etapa 8 — HP Prime.** `HpPrimeCalculator`, `HpPrimeKeyboard`,
  `ExpressionParser`, `Result` em `applications/hp_prime/`. Primeiro consumidor real
  do framework — ver nota de migração abaixo.
- [ ] **Etapa 9 — API semântica.** `calc.type_expression()`, `calc.press_enter()`,
  `calc.get_result()`, `calc.reset()`.
- [ ] **Etapa 10 — Transações.** `with calc.transaction(): ...`.
- [ ] **Etapa 11 — End-to-end.** Cenários reais automatizados.
- [ ] **Segunda aplicação.** `FakeCalculator`/`LegacyApplication` fictícia
  implementada sem tocar em `core/`, `drivers/`, `state/`, `locator/` ou
  `transaction/`. Este é o teste arquitetural que decide se o framework é reutilizável
  de fato — ver [ARCHITECTURE.md §22](ARCHITECTURE.md#22-critério-de-reutilização).

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

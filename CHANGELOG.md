# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento: [SemVer](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Adicionado

- `InputDriver.drag(start, end, duration=0.5)` e `InputDriver.screen_size()` —
  faltavam no contrato original (§9); apareceram ao construir uma macro real no
  `hp-prime-automation` que precisa arrastar uma seleção de tela inteira. Implementados
  em `PyAutoGuiDriver` e `MockDriver`, com testes (`tests/unit/test_mock_driver.py`).
- `InputDriver.locate_on_screen(template_path, confidence=)` e `core.anchors.AnchorZone`
  (§9.2) — resolvem locator por 2 âncoras de imagem em vez de fração fixa de
  `window.geometry()`. Promovido do `hp-prime-automation`, onde nasceu resolvendo um
  problema real: a HP Prime tem mais de um modo de layout (não é o mesmo arranjo
  escalado), e toda calibração por fração fixa quebrava ao trocar de modo. Testado
  (`tests/unit/test_anchors.py`, `test_mock_driver.py`) sem precisar de tela real.
- `GUIAutomator.color_at`/`color_matches` (§9.3) — também promovidos do
  `hp-prime-automation`; usam `self.resolve()`, então uma subclasse que resolve
  locators de outro jeito (`AnchorZone`, por exemplo) herda de graça, só precisa
  sobrescrever `resolve()`.
- `core.state.color_based_detector` (§10.1) — fábrica de `state_detector` a partir de
  um mapa cor→estado, pra plugar direto no `GUIAutomator`. Ainda sem consumidor real
  (nenhuma aplicação tem indicador calibrado ainda) — testado isoladamente.
- `tools/mapper.py` ganha captura de âncora: um `POINT` pode virar template PNG
  (`templates/{nome}.png`) na hora, sem precisar montar o recorte na mão depois.

### Pendente

- Extração do `hp-prime-automation` (Etapas 8-11 do `ROADMAP.md`) — a HP Prime
  continua fora deste repositório por decisão de arquitetura.
- Testes de integração contra uma GUI real (Fase 3/4 de
  [ARCHITECTURE.md §20](ARCHITECTURE.md#20-testes)) — hoje só as Fases 1 e 2
  (unitário e mock) existem.

## [0.1.0] - 2026-08-25

### Adicionado

- Core funcional (Etapa 1): `PointLocator`/`RegionLocator` com validação de
  intervalo, `WindowManager`/`WindowGeometry`, `InputDriver` (contrato) +
  `PyAutoGuiDriver`, `GUIAutomator` orquestrando tudo.
- Configuração (Etapa 2): `config.loader`/`config.schema` — schema version, campos
  obrigatórios, tipo de locator e intervalo `[0,1]` validados; chave duplicada no
  JSON é rejeitada. `tools/validate_config.py` e `tools/mapper.py` como scripts de
  dev.
- Máquina de estados (Etapa 3): `GUIState`, `StateManager.wait_for`/`wait_until`
  com timeout (`AutomationTimeoutError`).
- Interrupções (Etapa 4): `Interruption`/`InterruptionManager`, verificadas em
  `GUIAutomator.precheck()` antes de toda ação.
- Recuperação (Etapa 5): `RecoveryManager` — `ensure_ready()` só tenta recuperar se
  houver passos registrados, senão propaga o timeout original.
- Logging estruturado (Etapa 6): cada ação loga com um `op=<id>` sequencial via
  `logging.getLogger("prumo")`.
- `MockDriver` (Etapa 7) e suíte de testes (39 casos) cobrindo locators, config,
  estado, interrupções, recuperação, transação e automator — nenhum deles abre uma
  aplicação real.
- Prova mínima do critério de reutilização (`tests/unit/test_second_application.py`):
  uma aplicação fictícia herda `GUIAutomator` sem tocar em `core/`, `drivers/` ou
  `config/`.

## [0.0.1] - 2026-08-25

### Adicionado

- Especificação da arquitetura (`ARCHITECTURE.md`): camadas, contratos, máquina de
  estados, regras de segurança e critério de reutilização.
- Roadmap com as 11 etapas de implementação e nota de migração do
  `hp-prime-automation`.
- Estrutura de diretórios do pacote (`src/prumo/core`, `drivers`, `config`,
  `applications`) — módulos ainda vazios, implementação começa na Etapa 1.

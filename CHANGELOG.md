# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento: [SemVer](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Corrigido (05/10/2026, auditoria semântica: configuração)

- `"x": true` no mapa era aceito como coordenada 1.0 (bool é int em Python) — o canto da janela, calado.
  Coordenada agora tem de ser número de verdade.
- `"x": "0.5"` estourava `TypeError` cru, sem dizer qual locator; agora é `LocatorError` com o nome.
- Mapa salvo pelo Bloco de Notas (UTF-8 com BOM) era recusado pelo `json`; agora carrega (`utf-8-sig`).
- JSON que não é objeto (ou locator que não é objeto) vira erro claro em vez de `AttributeError`.
- Os mapas reais conferidos com a validação nova: o da calculadora (51 locators) e o exemplo passam.

### Corrigido (05/10/2026, auditoria semântica: âncoras e seleção por nome)

- `ListSelector.select` só rolava para BAIXO com o alvo fora da parte visível: com a lista aberta no
  meio, apertava "baixo" no fim até esgotar os passos e dizia "não achei" de um item que existia
  (acima). Agora dá a volta quando a lista para de mudar (duas leituras iguais seguidas — uma só pode
  ser o app redesenhando) e, percorrida nos dois sentidos, falha na hora.
- `AnchorZone`: escala <= 0 (uma âncora casada do lado errado da outra) virava clique ESPELHADO; agora
  é `LocatorError`. Frações iguais nas duas âncoras são recusadas ao montar, não depois de duas buscas
  de imagem. Novo `invalidate()` para trocas de layout que não mexem na geometria da janela.

### Corrigido (05/10/2026, §12 e §9.14 regra 9: popup tratado tem de sair)

- `InterruptionManager.check_and_handle` chamava `handle()` e seguia sem conferir: um "OK" que não
  fechava o popup deixava a ação seguinte cair nele, sem erro; com dois popups empilhados, só o
  primeiro era tratado. Agora confere que cada um saiu da tela (`confirm_timeout`), trata todos os
  presentes e levanta `PopupError` — que existia e nada levantava — se um não fecha ou se reaparece
  além de `max_rounds`. Testes reescritos com popups que fecham de verdade.

### Corrigido (05/10/2026, tipos conferidos)

- `mypy` no extra `dev`, no `pyproject` e no CI. Achou 12 problemas; os que importam: `pacing` podendo
  ser `None` em três métodos do `PyAutoGuiDriver` — um `AttributeError` esperando o primeiro caminho
  novo. `_confirmar_soltura_mouse` passou a funcionar sem pacing; `_segura_e_solta` recebe o pacing como
  parâmetro obrigatório (o tipo garante). `Image.LANCZOS` → `Image.Resampling.LANCZOS`.

### Corrigido (05/10/2026, OCR — §9.11, §9.14)

- `ocr.normalize` APAGAVA a letra acentuada em vez de tirar o acento ("Função" virava `funo`): em
  pt-BR, o idioma padrão, "Funcao" lido pelo OCR contra "Função" da lista dava 0,8. Agora dobra o
  acento (NFKD): 1,0. Conferido com o OCR real do Windows.
- `read_lines` dentro de um loop assíncrono já rodando (Jupyter, app assíncrono) levantava
  `RuntimeError` do `asyncio.run`; agora roda numa thread própria.
- Sem o pacote de OCR do idioma, o `winocr` falhava num `assert` (e, com `python -O`, num
  `AttributeError` críptico); agora é `UnexpectedStateError` dizendo o que instalar.
- `test_ocr` (dublê do `winocr`) e um `win32_real` com o OCR de verdade, pulado sem o idioma
  (o runner do CI é em inglês). Cobertura do `ocr.py`: 55% → 100%; total 96,6%.

### Adicionado (05/10/2026, §9.12: todo gesto pelo automator)

- `GUIAutomator.move_to()` (hover) e `GUIAutomator.drag()` (gate de oclusão nas duas pontas;
  `occlusion_gate=False` declara um alvo fora da janela de propósito), ambos com a trava. Fecham a
  lacuna que obrigava o consumidor a ir ao driver — o que a docstring do automator proíbe (§1.2) e o
  que, com a trava ligada, pareceria a mão do usuário. O hp-prime-automation passou a usá-los e liga a
  trava por padrão.
- `MockDriver.probes`: as consultas da trava (`cursor_position`, `is_key_down`) saem de `calls`.
  Ligar a trava não muda a sequência de ações que os testes dos consumidores conferem.

### Corrigido (05/10/2026, ARCHITECTURE.md §9.14: hardening, marco v0.9)

- **Botão/tecla preso no SO:** Ctrl+C ou FAILSAFE no instante segurado do `click`, no meio de um
  `hotkey`/`press` ou no trajeto do `drag` saíam com o botão ou a tecla APERTADA no Windows inteiro.
  Agora soltam (sem mover o mouse; FAILSAFE desligado só na soltura) e a interrupção segue.
- **Recuperação disputando o mouse:** `RecoveryManager` repetia passos depois de `UserTakeoverError`
  e `InputReleaseError`. Agora esses sobem na hora; cada tentativa perdida vai pro log;
  `max_attempts < 1` é recusado.
- **`find()` escolhendo pela ordem do SO:** desempata pelo título exato (a instância original);
  sem desempate, `AmbiguousWindowError`. Novo `pid=` no `WindowManager`.
- **Gates calados:** fora do Windows ou com janela sem `_hWnd` continuam deixando passar, mas
  avisam no log uma vez por proteção. `owns_point`: PID 0 nunca vira "mesmo processo".
- **Erro real no lugar do sintoma:** template ausente/ilegível/em caminho com acento (o `cv2.imread`
  devolvia `None` calado) vira erro na leitura; o template é lido uma vez, por bytes. Cor com número
  errado de canais vira `ValueError`. Processo sem DPI awareness vira aviso no log.

### Adicionado (05/10/2026, qualidade verificável)

- Testes do `PyAutoGuiDriver` (0% → 92%) com dublês que gravam cada gesto; `owns_point` testado por
  dentro; testes `win32_real` (só leitura) contra o Windows de verdade. Cobertura total 79% → 95%.
- `[tool.ruff]` próprio (regras de bug: `E9`, `F`, `B`, `BLE`, `S110`), piso de cobertura de 90%,
  marcador `win32_real`, extra `dev` com `pytest-cov` e `ruff`, CI em Windows (Python 3.10–3.12).

### Adicionado (05/10/2026, ARCHITECTURE.md §9.13: primeira fatia do driver de UIA, marco v0.6)

- `drivers.uia.UiaWindow` (extra `[uia]`): janela de topo por título/classe, opcionalmente presa a um PID;
  `find`, `is_visible` (existe **e** tem área), `center`, `value`, `owns_point` (`ControlFromPoint` por
  processo, uma 2ª tentativa no `COMError`). Interseção do hp-prime-CK com o e2e da Tina; agir continua
  com o `InputDriver`. Validado ao vivo só lendo (Explorador e painel-nativo); o gate acertou um Windows
  Terminal por cima dos três pontos sondados.

### Adicionado (05/10/2026, ARCHITECTURE.md §9.12: o que os consumidores escreviam por fora)

- `WindowManager.owns_foreground()` / `ensure_foreground()`: a próxima tecla vai pro **processo** certo
  (popup do próprio app conta; falha fechado sem PID). Duplicado em ctypes no hp-prime-CK e no e2e da Tina.
- `core.guard.TakeoverGuard` + `UserTakeoverError`: ESC segurado ou mouse mexido entre dois gestos
  (> 8 px) param a automação. Opt-in no `GUIAutomator` (`guard=`), checado antes do `activate()`.
  `InputDriver` ganhou `cursor_position()` e `is_key_down()` (`MockDriver`: `cursor`, `keys_down`;
  o cursor do mock agora acompanha clique, movimento e arrasto).
- `core.wait.poll_until(cond, timeout=, what=, retry_on=)`: espera genérica com prazo. Duplicada
  (`esperar`/`_esperar`) nos dois consumidores.
- `drivers.release.confirm_released()` / `held_inputs()`: soltura confirmada para quem manda entrada
  sem o `PyAutoGuiDriver` (UIA, `SendKeys`). O `PyAutoGuiDriver` passou a usá-la.
- Fica para o driver de UIA (v0.6): o gate de ponto por `ControlFromPoint`, também duplicado.

### Corrigido (02/10/2026)

- `PyAutoGuiDriver.drag` agora confirma a soltura do botão do mouse e respeita a pausa pós-ação, como o `click`
  (§9.9) — era o único gesto de mouse sem a confirmação. Achado ao usá-lo no e2e do `painel-nativo` (Tina), onde
  *soltar* o mouse sobre o medidor de brilho é o que dispara o comando.

### Adicionado (02/10/2026): segundo consumidor externo

- O `the-me-project/Tina/painel-nativo/tests/e2e/` usa `WindowManager` (ativar com confirmação, gate `owns_point`) e
  `PyAutoGuiDriver` + `HumanPacing` para dirigir um app WPF com mouse e teclado reais; a UI Automation entra só para
  achar controles por `AutomationId` e ler estado (mesmo padrão do `hp-prime-CK`, §9.10). Sem código novo no prumo
  além da correção acima. Travas que o consumidor acrescentou e que valem como receita: gate de ponto antes de todo
  gesto, ESC aborta, e "o mouse saiu do lugar entre dois gestos" = o usuário assumiu, para.

### Adicionado (29/09/2026, ARCHITECTURE.md §9.10: UI Automation)

- Seção §9.10 com as regras genéricas achadas automatizando o Connectivity Kit
  por UIA (SetValue que não suja o modelo, Select ≠ clique, menus Qt por
  teclado, persistência = fechar e reabrir...). Sem código novo de driver: o
  único consumidor é o `hp-prime-CK` (§22).

### Adicionado (29/09/2026, ARCHITECTURE.md §9.11)

- `prumo.drivers.ocr` (extra `[ocr]`): `read_lines`, `TextLine`, `similarity`.
- `prumo.core.listsel.ListSelector`, `Row`, `AmbiguousItemError`,
  `ItemNotFoundError`: escolher item de lista por nome, relendo a cada passo.
  Testes em `tests/unit/test_listsel.py`.

### Corrigido (29/09/2026)

- `WindowManager.activate()` não levanta mais `PyGetWindowException` (1400)
  quando a janela em primeiro plano está em transição: `_esta_ativa` tenta de
  novo e só então responde "não está ativa".

### Adicionado (22/09/2026, ARCHITECTURE.md §9.9: passo confirmado)

- `drivers/pacing.HumanPacing`, ligado por padrão no `PyAutoGuiDriver`
  (`pacing=None` volta ao comportamento cru). Traz trajeto do mouse
  proporcional à distância, mira, tecla ou botão segurado por um instante,
  **soltura confirmada no SO** e pausa depois de cada ação.
- `InputReleaseError`: o SO não confirmou que o botão ou a tecla foi solto.
- `WindowManager.owns_point(x, y)` (`WindowFromPoint`) e
  `GUIAutomator.click_at(x, y)`: recusam clicar num ponto coberto por outra
  janela (`WindowOccludedError`). `click()` passou a usar `click_at`.
- `GUIAutomator.wait_for_template`, `wait_for_template_gone` e `is_on_screen`:
  o gate entre etapas. Ação, espera o estado visto na tela, e só então a
  próxima ação.

### Corrigido

- `PyAutoGuiDriver.locate_on_screen` só testava o tamanho exato do template —
  a mesma aplicação pode renderizar o mesmo botão em tamanhos diferentes entre
  modos de layout (achado real, HP Prime: confiança caiu de >0.85 pra 0.44 com
  o botão visível e correto na tela). Agora cai pra busca multi-escala
  (`drivers/_template_match.py`, ~10 escalas via OpenCV) antes de desistir.
  Extra `prumo[anchors]` (`opencv-python`+`numpy`). 4 testes com arrays
  sintéticos, sem precisar de tela real.

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
- `InputDriver.read_clipboard`/`write_clipboard` (§9.4) — ponte com o clipboard do SO
  via `win32clipboard` (`CF_UNICODETEXT`, não `CF_TEXT` — perde glifo fora do cp1252).
  Nasceu resolvendo a leitura do resultado calculado na HP Prime (não tem outro jeito
  de ler o valor sem OCR). Extra dependência `pywin32` (só Windows). Testado via
  `MockDriver` (`read_clipboard_return`, `write_clipboard` registrado em `calls`).
- `InputDriver.move_to(x, y, *, duration=0.0)` — parâmetro novo, opcional e
  retrocompatível. Achado real na HP Prime: um popup de menu nativo (Qt) só
  reconhece o item sob o cursor com movimento incremental de verdade; um salto
  instantâneo (`duration=0`, o padrão) não gera hover e o clique seguinte não
  executa o comando, mesmo fechando o popup normalmente.
- `InputDriver.write(text, *, delay=0.0)` — parâmetro novo, opcional e
  retrocompatível. Achado real: um diálogo nativo da HP Prime derrubou caractere
  (`"TESTEXX"` chegou como `"TEXX"`) com `write()` de uma vez; `delay > 0` escreve
  um caractere por vez.
- `GUIAutomator.wait_for_color_change` (§9.6) — espera um `color_at()` sair de uma
  cor de origem, com timeout (`AutomationTimeoutError` se esgotar). Achado real:
  o popup de "Verif." da HP Prime pode levar minutos pra aparecer num programa
  grande (~3500 linhas, CPU do processo perto de 100% o tempo todo); um sleep
  fixo curto clicava no botão de fechar antes do popup existir, reiniciando a
  verificação em vez de fechar o resultado.
- `core.softkeys.SoftkeyRow` (§9.7) — grade de N fatias horizontais iguais numa
  fileira de altura fixa (F1-F6 de uma calculadora, ou qualquer barra de botões
  de largura igual). Promovido do `hp-prime-automation`. Não usa casamento de
  imagem como `AnchorZone` — é aritmética pura (pixel fixo em y, proporcional
  em x). Testado (`tests/unit/test_softkeys.py`) sem tela real.

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

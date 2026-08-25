# Arquitetura — `prumo`

Este documento é a especificação técnica completa do projeto. Descreve as camadas,
seus contratos e as regras que nenhuma implementação pode violar. Para objetivo,
instalação e exemplo de uso, veja o [README](README.md).

---

## 1. Princípios fundamentais

### 1.1. Separação de responsabilidades

```text
API semântica
      ↓
Estado
      ↓
Automação
      ↓
Driver
      ↓
Sistema operacional
      ↓
Aplicação
```

Nenhuma camada deve assumir responsabilidades pertencentes a outra.

### 1.2. O LLM nunca manipula coordenadas

O código de alto nível deve ser capaz de fazer:

```python
calc.press_enter()
```

mas nunca:

```python
pyautogui.click(1374, 812)
```

As coordenadas são detalhes internos da implementação.

### 1.3. Coordenadas não são estado

Uma coordenada como `(1200, 800)` significa apenas "um determinado ponto da tela" —
nunca "a aplicação está pronta". Estado e localização são conceitos independentes.

### 1.4. Toda ação deve possuir pré-condição e pós-condição

```text
PRECONDITION → INTERRUPTION CHECK → ACTION → WAIT → VERIFICATION → POSTCONDITION
```

Uma ação que não consegue verificar seu resultado deve ser considerada de menor
confiabilidade.

### 1.5. Falha segura

A automação nunca deve continuar silenciosamente quando o estado da aplicação é
desconhecido. Preferir `raise AutomationStateError(...)` a `pass`. O sistema deve
falhar de forma explícita e diagnosticável.

---

## 2. Objetivos da primeira versão

* descoberta da janela; identificação; ativação
* locators relativos; regiões relativas
* ações de mouse e teclado
* espera por estado; detecção de interrupções; tratamento de popups
* máquina de estados; timeout global; recuperação
* logging; configuração externa; validação do mapa
* API específica de aplicação; testes unitários da camada abstrata

## 3. Não objetivos (por ora)

visão computacional completa · reconhecimento universal de elementos · OCR perfeito ·
entendimento semântico arbitrário da GUI · automação de qualquer aplicação sem
configuração · detecção automática de todos os popups · adaptação automática a
qualquer DPI · interação direta do LLM com screenshots.

---

## 4. Arquitetura geral

```text
┌──────────────────────────────────────────┐
│           AGENTE / LLM / API              │
└─────────────────────┬────────────────────┘
                       │ API semântica
                       ▼
┌──────────────────────────────────────────┐
│             Application API               │
│  HpPrimeCalculator · LegacyERP · CAD...   │
└─────────────────────┬────────────────────┘
                       ▼
┌──────────────────────────────────────────┐
│              State Manager                │
│   UNKNOWN / READY / BUSY / ERROR / POPUP  │
└─────────────────────┬────────────────────┘
                       ▼
┌──────────────────────────────────────────┐
│               GUIAutomator                │
│  locators · actions · synchronization ·   │
│  interruptions · recovery                 │
└─────────────────────┬────────────────────┘
                       ▼
┌──────────────────────────────────────────┐
│                  Driver                   │
│  mouse · keyboard · screenshot · window   │
└─────────────────────┬────────────────────┘
                       ▼
┌──────────────────────────────────────────┐
│              Sistema operacional          │
└─────────────────────┬────────────────────┘
                       ▼
                   Aplicação
```

Regra de ouro:

```text
O LLM conhece INTENÇÕES.
A aplicação conhece OPERAÇÕES.
O automator conhece AÇÕES.
O driver conhece PIXELS.
```

Cada camada conhece **somente o nível imediatamente abaixo dela**.

---

## 5. Estrutura de diretórios

```text
prumo/
│
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── CHANGELOG.md
├── LICENSE
│
├── src/
│   └── prumo/
│       ├── __init__.py
│       │
│       ├── core/
│       │   ├── automator.py      # GUIAutomator
│       │   ├── locator.py        # PointLocator, RegionLocator
│       │   ├── state.py          # GUIState, StateManager
│       │   ├── exceptions.py
│       │   ├── events.py         # Interruption, InterruptionManager
│       │   └── transaction.py
│       │
│       ├── drivers/
│       │   ├── base.py           # InputDriver (contrato)
│       │   ├── pyautogui_driver.py
│       │   └── window.py         # WindowManager
│       │
│       ├── config/
│       │   ├── loader.py
│       │   └── schema.py
│       │
│       └── applications/
│           └── hp_prime/         # só nasce na Etapa 8 — ver ROADMAP.md
│
├── configs/
│   └── hp_prime.json
│
├── tools/
│   └── mapper.py                 # ferramenta de dev, fora da lib principal
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

**Regra:** tudo que puder ser reutilizado por outro projeto fica em `core/` ou
`drivers/`. Tudo que souber que existe uma HP Prime fica em `applications/hp_prime/`.

---

## 6. Camada `Locator`

O locator representa uma localização lógica da interface e não deve saber nada sobre
a aplicação-alvo.

```python
@dataclass(frozen=True)
class PointLocator:
    x: float
    y: float

@dataclass(frozen=True)
class RegionLocator:
    x: float
    y: float
    width: float
    height: float
```

Valores são relativos à janela (0.0–1.0). Regras: imutável, não conhece pixels
absolutos, não executa ações, é validável e serializável.

---

## 7. Arquivo de configuração

O mapa de locators fica fora do código:

```json
{
    "schema_version": 1,
    "application": "HP Prime",
    "window": { "title": "HP Prime" },
    "locators": {
        "enter_key": { "type": "point", "x": 0.50, "y": 0.82 },
        "display": { "type": "region", "x": 0.10, "y": 0.05, "width": 0.80, "height": 0.30 }
    }
}
```

O código nunca contém `ENTER_X = 1234`.

---

## 8. `WindowManager`

Responsável exclusivamente pela janela: localizar, validar existência, obter posição
e tamanho, ativar, detectar mudança de tamanho, detectar janela desaparecida.

```python
class WindowManager:
    def find(self): ...
    def activate(self): ...
    def geometry(self): ...
    def is_alive(self): ...
```

O `GUIAutomator` não conhece detalhes de `pygetwindow` (ou equivalente).

---

## 9. Driver

Camada responsável pela interação física:

```python
class InputDriver:
    def click(self, x, y): ...
    def press(self, key): ...
    def hotkey(self, *keys): ...
    def write(self, text): ...
    def drag(self, start, end, *, duration=0.5): ...
    def screenshot(self, region=None): ...
    def screen_size(self): ...
    def move_to(self, x, y): ...
    def locate_on_screen(self, template_path, *, confidence=0.85): ...
```

Implementação inicial: PyAutoGUI. Futuras: `WindowsUIDriver`, `LinuxUIDriver`,
`MacOSUIDriver`, `MockDriver`.

### 9.1. Por que `MockDriver`

Sem um driver falso, os testes precisam abrir a aplicação real — ruim para CI e para
iteração rápida. `calc.press_enter()` deve rodar em ambiente sem GUI. O mock registra
a sequência produzida (`[("click", "enter_key"), ("wait", 0.2)]`) para verificação sem
clique físico.

### 9.2. `locate_on_screen` e `AnchorZone` — resolução por âncora de imagem

Coordenadas relativas à janela (§1.3, §21) pressupõem que a aplicação inteira escala e
move como um retângulo rígido a partir de `window.geometry()`. Duas coisas quebram essa
suposição na prática (achado em produção, ver `hp-prime-automation`):

1. `window.geometry()` pode não bater com o conteúdo renderizado de verdade — retângulo
   "lógico" divergindo dos pixels reais (observado com DPI: um teclado calibrado por
   fração de `window.geometry()` precisava de uma largura ~4-9% maior que a janela
   reportava pra fechar a conta).
2. A aplicação pode ter mais de um **modo de layout** — uma janela redimensionada
   reorganiza a interface (não só escala). Coordenadas calibradas num modo não
   generalizam pro outro nem multiplicando por uma razão de escala.

`InputDriver.locate_on_screen(template_path, confidence=)` acha um recorte de imagem
direto na tela (via casamento de template) e devolve o pixel central, ou `None` se não
achar. `core.anchors.AnchorZone` usa isso pra resolver qualquer `Locator`: dadas 2
**âncoras** (`Anchor` = um `PointLocator` + o caminho do template que a representa) em
cantos opostos, localiza as duas na tela e resolve exato o sistema escala+translação por
eixo — o mínimo matemático quando só escala e posição podem variar (sem rotação nem
cisalhamento). Nunca depende de `window.geometry()` pra calcular posição, só para saber
quando o cache expirou (`geometry_key()` mudou — a janela pode ter mudado de lugar,
tamanho ou *modo*; não dá pra saber qual sem medir de novo).

```python
zone = AnchorZone(
    Anchor(locator=PointLocator(x=0.06, y=0.25), template_path="config/templates/A.png"),
    Anchor(locator=PointLocator(x=0.89, y=0.90), template_path="config/templates/B.png"),
    locate=driver.locate_on_screen,
    geometry_key=window.geometry,
)
x, y = zone.resolve(algum_outro_locator)
```

Âncora não encontrada levanta `LocatorError` — nunca clica às cegas quando o template
para de bater (tema mudou, fonte mudou, layout mudou o suficiente).

### 9.3. `GUIAutomator.color_at` / `color_matches`

Leitura de pixel (decisão simples: indicador verde/vermelho, luz acesa/apagada) é
comum o bastante pra estar no `GUIAutomator` em vez de cada aplicação reimplementar:

```python
r, g, b = automator.color_at("indicador_status")
automator.color_matches("indicador_status", (0, 255, 0), tolerance=10)  # -> bool
```

Os dois chamam `self.resolve(name)` — uma subclasse que resolve locators de outro
jeito (§9.2, `AnchorZone` por exemplo) herda `color_at`/`color_matches` de graça, só
precisa sobrescrever `resolve()`.

---

## 10. Máquina de estados

```python
class GUIState(Enum):
    UNKNOWN = auto()
    READY = auto()
    BUSY = auto()
    ERROR = auto()
    POPUP = auto()
    CLOSED = auto()
```

Futuramente: `STARTING`, `LOADING`, `RECOVERING`, `DISCONNECTED`.

```python
class StateManager:
    def detect(self) -> GUIState: ...
    def wait_for(self, state: GUIState, timeout: float): ...
```

### 10.1. `color_based_detector` — detecção de estado por indicador visual

A forma mais comum de detectar estado numa GUI real é olhar um indicador (uma bolinha
verde/vermelha, um ícone que muda). `core.state.color_based_detector` fabrica um
`state_detector` pronto pra plugar no `GUIAutomator` a partir de um mapa cor→estado:

```python
detector = color_based_detector(
    color_at=lambda: automator.color_at("indicador_status"),
    color_states={(0, 255, 0): GUIState.READY, (255, 0, 0): GUIState.ERROR},
    tolerance=10,
    default=GUIState.UNKNOWN,
)
```

`color_at` é qualquer callable sem argumento — normalmente
`automator.color_at(locator)` (§9.3), passado como referência depois que o automator
já existe (evita depender de `self` dentro do próprio `__init__`). Nenhuma cor bate
dentro da tolerância → `default` (nunca inventa READY quando o estado é desconhecido —
§1.5).

---

## 11. Sincronização

Não usar `time.sleep(2)` como mecanismo principal. Preferir:

```python
wait_until(lambda: state.detect() == GUIState.READY, timeout=5)
```

`time.sleep()` continua permitido como debounce, nunca como única forma de descobrir
se uma operação terminou.

---

## 12. Interruption Manager

Popups são interrupções do fluxo normal:

```python
@dataclass
class Interruption:
    name: str
    detection_locator: Locator
    expected_state: object
    action: str
```

Fluxo: `invalid_input → detect_popup → click_ok → return_to_previous_state`.
Interrupções são processadas **antes** das operações.

### 12.1. Regra de segurança

Toda ação começa com:

```text
1. janela existe?
2. janela está ativa?
3. existe popup?
4. existe erro?
5. aplicação está pronta?
6. executar ação
```

Nunca `click(); click(); click();` sem verificar o estado entre cada uma.

---

## 13. Exceptions

```python
class AutomationError(Exception): pass
class WindowNotFoundError(AutomationError): pass
class LocatorError(AutomationError): pass
class TimeoutError(AutomationError): pass
class UnexpectedStateError(AutomationError): pass
class PopupError(AutomationError): pass
class RecoveryError(AutomationError): pass
```

Isso permite que a aplicação consumidora saiba exatamente o que aconteceu.

---

## 14. Logging

```text
INFO  window found: HP Prime
INFO  state: UNKNOWN -> READY
INFO  action: click(enter_key)
INFO  state: READY -> BUSY
INFO  state: BUSY -> READY
INFO  verification: SUCCESS
```

Em erro:

```text
ERROR action failed
ERROR state: UNKNOWN
ERROR operation: press_enter
ERROR timeout: 5.0s
```

---

## 15. Sistema de recuperação

```text
normal → erro → diagnóstico → tentativa de recuperação → verificação → READY
```

Se falhar: `RECOVERY_FAILED`, execução termina. Nunca `except Exception: pass` para
erros críticos.

---

## 16. API da aplicação

Só nesta camada aparecem conceitos específicos da aplicação-alvo. Exemplo (HP Prime):

```python
class HpPrimeCalculator(GUIAutomator):
    def reset(self): ...
    def type_expression(self, expression): ...
    def press_enter(self): ...
    def get_result(self): ...
    def open_program(self, name): ...
    def compile(self): ...
    def run(self): ...
```

Essa classe nunca chama `pyautogui.click(...)` diretamente — sempre passa pela
infraestrutura de `core/` e `drivers/`.

### 16.1. Parser de expressão

Camada separada (`expression.py`): texto → tokenização → tokens da aplicação →
sequência de teclas. Ex.: `SIN(45)` → `[SIN, LEFT_PAREN, 4, 5, RIGHT_PAREN]` → ações
de GUI. Evita que `type_expression()` vire um conjunto gigante de `if`.

---

## 17. Transaction Manager

```python
with calc.transaction():
    calc.type_expression("SIN(45)")
    calc.press_enter()
    result = calc.get_result()
```

Uma transação: (1) verifica estado inicial, (2) executa operações, (3) valida estado
final, (4) registra operações, (5) tenta recuperação se permitido, (6) aborta se o
estado ficar desconhecido.

---

## 18. Mapper

`tools/mapper.py` **não** faz parte da biblioteca principal — é ferramenta de
desenvolvimento.

```text
abrir aplicação → localizar janela → selecionar locator → usuário posiciona mouse
  → capturar posição → converter para relativo → validar → salvar JSON
```

Mapeia `POINT` e `REGION` hoje; futuramente `STATE INDICATOR`, `POPUP`, `BUTTON`,
`DISPLAY`. Um `POINT` pode opcionalmente virar **âncora**: recorta um PNG (~32×32px em
torno do ponto) em `templates/{nome}.png`, ao lado do JSON de saída — pronto pra usar
em `Anchor`/`AnchorZone` (§9.2) sem precisar montar o recorte na mão.

## 19. Validador do mapa

`tools/validate_config.py` verifica: coordenadas entre 0 e 1, regiões dentro da
janela, nomes duplicados, tipos válidos, schema correto, versão compatível, locators
obrigatórios. Um mapa inválido é rejeitado **antes** de iniciar a automação.

---

## 20. Testes

**Fase 1 — Unitários** (sem GUI): `Locator`, `Config`, `State`, parser de expressão,
mapeamento de teclas, exceptions, transactions.

**Fase 2 — Mock**: click, keypress, sequências, recuperação, timeouts via
`MockDriver`.

**Fase 3 — Integração**: abre a aplicação real. Testa `WindowManager`, `Locator`,
`Driver`, `StateManager`.

**Fase 4 — End-to-end**: abrir → reset → digitar expressão → ENTER → esperar
resultado → obter resultado.

---

## 21. Critério de conclusão da v0.1

* janela pode ser movida e mudar de posição sem quebrar o mapa;
* coordenadas absolutas não existem no código;
* popups conhecidos são tratados; timeouts existem;
* estado desconhecido gera erro; recuperação é limitada;
* logs permitem reconstruir uma falha;
* testes unitários não precisam da aplicação real;
* testes de integração validam a GUI real;
* a API da aplicação não expõe o driver bruto (`pyautogui` etc.);
* o driver pode ser substituído por um mock.

## 22. Critério de reutilização

Antes de declarar o framework reutilizável, implementar uma segunda aplicação
(ex.: `FakeCalculator` ou `LegacyApplication`). Se for possível escrever
`class AnotherApplication(GUIAutomator): ...` sem modificar `core/`, `drivers/`,
`state/`, `locator/` ou `transaction/`, a arquitetura está de fato desacoplada. Esse
teste é mais importante que simplesmente fazer a HP Prime funcionar — ver
[ROADMAP.md](ROADMAP.md).

---

## 23. Resultado arquitetural desejado

```python
calc = HpPrimeCalculator()
calc.reset()
calc.type_expression("SIN(45)")
calc.press_enter()
result = calc.get_result()
print(result)
```

Sem que o código acima saiba onde está a janela, qual é a resolução, onde está o
botão, qual é o DPI, qual driver está sendo usado, como popups são detectados, como a
aplicação informa que terminou, ou como uma falha é recuperada. Essa é a fronteira
que define a abstração.

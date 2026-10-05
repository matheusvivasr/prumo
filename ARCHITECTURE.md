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
│       │   ├── listsel.py        # ListSelector (§9.11)
│       │   ├── events.py         # Interruption, InterruptionManager
│       │   └── transaction.py
│       │
│       ├── drivers/
│       │   ├── base.py           # InputDriver (contrato)
│       │   ├── pyautogui_driver.py
│       │   ├── ocr.py            # leitura de texto opcional (§9.11)
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
    def write(self, text, *, delay=0.0): ...
    def drag(self, start, end, *, duration=0.5): ...
    def screenshot(self, region=None): ...
    def screen_size(self): ...
    def move_to(self, x, y, *, duration=0.0): ...
    def locate_on_screen(self, template_path, *, confidence=0.85): ...
    def read_clipboard(self): ...
    def write_clipboard(self, text): ...
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

`PyAutoGuiDriver.locate_on_screen` tenta o tamanho exato primeiro (rápido) e, se
falhar, cai pra busca **multi-escala** (`drivers/_template_match.py`, testa o
template em ~10 escalas via OpenCV) antes de desistir. Achado real (25/08/2026, HP
Prime): a mesma aplicação pode renderizar o mesmo botão em **tamanhos diferentes**
entre modos de layout, não só posições diferentes — escala única derrubou a
confiança de >0.85 pra 0.44 mesmo com o botão visível e correto na tela. Exige
`opencv-python`+`numpy` (extra `prumo[anchors]`).

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

### 9.4. `read_clipboard` / `write_clipboard`

Muitas aplicações não expõem o próprio estado (resultado calculado, texto processado)
de nenhum outro jeito além de "selecionar e copiar" — ler pixel por pixel (OCR) é o
último recurso, não o primeiro. `read_clipboard`/`write_clipboard` fecham essa ponte
com o clipboard do sistema operacional:

```python
driver.write_clipboard("texto")   # escreve
texto = driver.read_clipboard()   # lê
```

Implementação Windows via `win32clipboard`, sempre com `CF_UNICODETEXT` — `CF_TEXT`
(ANSI/cp1252) descarta qualquer glifo fora da code page, e aplicações têm motivo real
pra usar Unicode fora do ASCII básico (achado ao integrar a HP Prime: notação
científica usa U+1D07, não "e" ASCII — normalizar esse tipo de glifo específico da
aplicação é responsabilidade de quem consome, não deste driver).

**Cuidado documentado, não uma limitação do driver**: nem todo caminho que parece
"copiar" de fato escreve no clipboard do SO. Um item de menu clicado via automação
pode fechar e devolver a interface a um estado consistente sem chamar a API de
clipboard de verdade (achado real: um clique instantâneo ou diagonal num popup Qt não
registrava a cópia, mesmo fechando o menu normalmente — só `move_to(..., duration>0)`
em linha reta, sem trocar de eixo no meio do caminho, gerava os eventos de hover que o
popup exige antes de aceitar o clique). Quem constrói a sequência de clique deve
confirmar a escrita de verdade (ex.: sequência de clipboard antes/depois) antes de
assumir que "o menu fechou" significa "a ação rodou".

### 9.5. `write(text, *, delay=0.0)`

Algumas aplicações derrubam caractere quando `write()` digita rápido demais (achado
real: um campo de diálogo nativo da HP Prime recebeu `"TESTEXX"` como `"TEXX"` — o
`keyboard.write()` por trás não deu conta). `delay=0` (padrão) mantém o comportamento
rápido de sempre — escreve tudo de uma vez; `delay > 0` escreve um caractere por vez,
com pausa entre eles. Não tem como saber de antemão se uma aplicação precisa disso —
é um parâmetro pra quando o sintoma aparecer, não uma mudança de comportamento padrão.

### 9.6. `GUIAutomator.wait_for_color_change`

```python
cor_nova = automator.wait_for_color_change(
    color_at, from_color=(255, 255, 255), timeout=300.0, poll_interval=1.0
)
```

Generaliza um padrão que `color_based_detector` (§10.1) já usa pra decidir *o quê* uma
cor significa, mas resolvido aqui pro problema de *esperar* uma cor mudar antes de
agir. Nasceu de um achado real: o popup de verificação de sintaxe da HP Prime pode
levar minutos pra aparecer num programa grande (CPU do processo perto de 100% o tempo
todo via `IsHungAppWindow`/tempo de CPU — ocupado de verdade, não travado). Um sleep
fixo curto clica no botão de fechar o popup antes dele existir — na prática clica de
novo no botão que ABRE a verificação, reiniciando-a em vez de fechar o resultado.
Levanta `AutomationTimeoutError` se `timeout` esgotar sem mudança — nunca clica às
cegas nesse caso.

`color_at` é qualquer callable sem argumento que devolve (r, g, b) — não precisa ser
`self.color_at(locator_name)`; útil quando o pixel de interesse não é um locator do
mapa (ex.: chrome nativo do app, fora do teclado virtual — mesmo caso de uso do menu
em §9.4). Uma aplicação que precisa vigiar **mais de um** ponto ao mesmo tempo (ex.:
ícone de sucesso E ícone de erro em posições diferentes, porque a caixa do popup
centraliza pelo tamanho da mensagem) combina os dois numa única `color_at` que devolve
o primeiro que sair do zero (fundo) — a espera em si continua sendo um só ponto.

### 9.7. `SoftkeyRow`

```python
from prumo.core.softkeys import SoftkeyRow

softkeys = SoftkeyRow(count=6, y_offset=298, geometry_key=window.geometry)
x, y = softkeys.resolve(1)  # 2ª de 6 fatias iguais
```

Padrão comum o bastante (calculadoras, POS, kiosks — qualquer barra de N botões de
largura igual num rodapé de altura fixa) pra não ficar preso a uma aplicação. Não é
`AnchorZone` (§9.2): não precisa de casamento de imagem porque a geometria é pura
aritmética — a fileira fica sempre no mesmo pixel em y (chrome do app) e cada fatia
tem largura igual, proporcional à largura da janela. **Achado real** que motivou o
parâmetro `y_offset` ser pixel fixo, não fração: um erro de 10px nesse valor fez um
clique cair fora do botão sem erro nenhum — o app simplesmente ignorou o clique.
Sempre que uma sequência de softkey "não fizer nada visível", suspeitar do offset
antes de qualquer outra coisa.

### 9.8. Combo de modificador (Shift/Ctrl/Alt) + tecla — sempre confirmar o latch antes de agir

Achado real (HP Prime, 22/09/2026): uma primeira tentativa de usar `Shift+Esc` pra
limpar o editor de programa concluiu, errado, que a combinação "não fazia nada" —
clicar Shift e Esc em sequência rápida (sem esperar) fez o Esc ser interpretado
**sozinho** (fechou o editor, comportamento de Esc normal) em vez de disparar a função
de Shift (que de fato limpa o conteúdo, com diálogo de confirmação). O erro só foi
percebido quando o usuário pediu pra **verificar visualmente** o indicador de Shift
ativo (`⬆S`, canto superior esquerdo da tela da HP Prime — a maioria dos apps
touch/embarcados tem um indicador equivalente) antes de clicar a segunda tecla; com
esse delay + confirmação, a combinação funcionou na primeira tentativa.

**Regra geral, não específica da HP Prime:** ao automatizar qualquer combo
modificador+tecla numa aplicação onde o modificador é "clique pra ativar, clique na
próxima tecla pra usar" (em vez de "segurar" — comum em apps touch/embarcados, que não
distinguem tecla-pressionada-e-solta de tecla-segurada), **nunca** encadeie os dois
cliques sem uma pausa nem confirme que o combo "não funciona" sem antes checar o
indicador visual de estado. Um "não funciona" observado sem essa checagem é
indistinguível de "funciona, mas o timing do teste estava errado" — a conclusão errada
custa caro (pode levar a manter um workaround pior, tipo loop de backspace em vez de um
comando de limpar-tudo). Delay mínimo seguro: o mesmo `_ACTION_DELAY`/pausa já usado
entre os dois cliques de qualquer sequência Shift+tecla que já funciona na aplicação
(ex.: `create_program` na HP Prime já usava esse delay entre Shift e a tecla seguinte,
só não tinha sido testado pra Esc especificamente).

**Ressalva (não confirmada — rebaixada no mesmo dia):** confirmar o combo funcionando
sob clique manual pausado **pode não** garantir que ele é seguro sob a cadência de uma
automação rodando vários ciclos em sequência rápida (`write_program()` chamado várias
vezes seguidas numa macro, por exemplo). Chegou a ser observado o `Shift+Esc` corromper
conteúdo dentro da macro (sobrou texto do programa anterior colado antes do novo) —
**mas a observação está contaminada:** o usuário estava mexendo nas janelas durante a
rodada, o que dessincronizou foco e travou teclas (mesma causa do nome digitado
corrompido e do falso-negativo do `verify_syntax` naquela sessão). Não há, portanto,
evidência limpa de que o combo falhe sob cadência. Status: **hipótese a testar** —
próxima rodada ao vivo roda `write_program()` várias vezes seguidas, sem intervenção
humana, e confirma ou descarta. (O fallback por backspace que existia em `clear_editor()`
foi **removido** no mesmo dia: ele próprio corrompia o fluxo entre programas. Ver §9.9.)

**Lição que sobra, essa sim confirmada:** teste ao vivo de automação de GUI exige mãos
fora do teclado/mouse durante a macro — intervenção manual "pra ajudar" produz sintomas
indistinguíveis de bug (foco roubado, tecla travada, texto corrompido) e contamina
qualquer conclusão tirada daquela rodada.

### 9.9. Passo confirmado: ritmo humano, soltura confirmada, estado visto antes de agir

Achado real (hp-prime-automation, 22/09/2026). Uma macro rodou "com sucesso" e
reportou 4 de 5 programas com FALHOU. Nenhuma das falhas era do programa:

1. **Foco não é visibilidade.** A HP Prime estava ativa (`isActive` verdadeiro),
   mas a janela do app do Claude cobria a mesma região. Os cliques caíram nela, e
   a cor "lida" do indicador de Shift, (16,16,16), era a da barra lateral do
   Claude.
2. **Pixel fixo apodrece.** O offset do indicador de Shift tinha sido calibrado
   com a janela em outro tamanho e passou a apontar pra borda.
3. **O fallback "segue em frente" transformou uma falha pequena em corrupção.**
   Sem o indicador, `clear_editor` caía pra "150 backspaces e continua". Isso
   funcionava no editor em branco, mas entre um programa e outro deixava o
   código antigo e colava o novo por cima.
4. **Digitação crua corrompe texto.** No emulador, número digitado depois de
   letra sai como a letra alfa da mesma tecla ("2"→"Z", "8"→"R"). Colar pela
   área de transferência chega exato.

**Regra geral (vale pra qualquer aplicação):**

- **Nenhuma ação depende só de a anterior "não ter dado erro".** Depois de cada
  ação, espere o estado que ela deveria produzir
  (`GUIAutomator.wait_for_template`, `wait_for_template_gone`). Só então vem a
  próxima. Se o estado não aparecer, **pare**, salve uma foto da janela e
  relate. Nada de fallback que continue a partir de um estado desconhecido.
- **Cheque a ausência do que não deveria estar lá** (`is_on_screen`), por
  exemplo um popup de erro, logo depois da espera.
- **Antes de clicar, pergunte ao SO de quem é o pixel**
  (`WindowManager.owns_point` via `WindowFromPoint`). Se for de outra janela,
  `GUIAutomator.click_at` levanta `WindowOccludedError`.
- **Ritmo humano** (`drivers/pacing.HumanPacing`, padrão do `PyAutoGuiDriver`):
  - trajeto do mouse proporcional à distância, com easing;
  - mira antes de apertar;
  - botão ou tecla segurado por um instante;
  - **soltura confirmada no SO** (`GetAsyncKeyState` / `keyboard.is_pressed`,
    senão `InputReleaseError`);
  - pausa depois de cada ação.

  O ritmo é o piso de tempo. Quem autoriza a próxima ação é o estado visto na
  tela.
- **App pesado** (emulador, software de engenharia): timeouts de estado
  generosos (padrão de 15 s). Errar pelo lado da paciência custa segundos; errar
  pelo lado da pressa corrompe a sessão.
- **Estado por template, não por pixel fixo**, sempre que o estado tiver algo
  visual único: um recorte PNG casa em qualquer posição e escala.

### 9.10. Aplicação com árvore de acessibilidade (UI Automation): prefira-a a pixel

Achado real (`hp-prime-CK`, 29/09/2026). O HP Connectivity Kit (Qt5) expõe
menus, árvores, diálogos e editores por UIA; o emulador da mesma calculadora
expõe as teclas como botões, mas o display não devolve texto. Onde a árvore
existe, localizar por **classe/nome** elimina coordenada, template e a
sensibilidade a tema/escala. Onde não existe (display do emulador), continua
valendo §9.2/§9.9. Não há driver UIA no `prumo` ainda: o único consumidor é o
`hp-prime-CK` (`ck/kit.py`), e por §22 ele só sobe pra `drivers/` quando
aparecer um segundo. As regras abaixo, porém, são genéricas:

1. **`ValuePattern.SetValue` pode mudar só a tela.** Se o modelo do app não
   registrar a edição, "salvar" não grava e fechar descarta o texto **sem
   perguntar**. Faça uma edição real (uma tecla inócua) depois do SetValue e
   confirme relendo.
2. **Conferir persistência = fechar e reabrir.** Ler com o editor aberto devolve
   a memória, não o que foi gravado.
3. **`SelectionItemPattern.Select` não é clique.** Pode mover a seleção da lista
   sem o painel associado trocar. Clique e confira qual item ficou **ativo**.
4. **Item novo pode nascer somente-leitura** (visto: aba criada na sessão do
   editor). Cheque `IsReadOnly` antes de escrever; a falha silenciosa perde texto.
5. **Menus de contexto do Qt não populam a árvore UIA de forma confiável**
   (intermitente, e sempre nos submenus). Navegue por teclado com posições
   fixas declaradas em UM lugar, e use como gate o **efeito** (diálogo esperado,
   item novo), nunca o rótulo lido.
6. **Diálogo modal pode ser filho da janela principal**, não janela de topo;
   e caixa de erro (`QMessageBox`) precisa ser lida e dispensada, senão trava a UI.
7. **Ação sem retorno visível** (ex.: "Enviar") só vale confirmada por um efeito
   observável em outro lugar; nome já existir não prova que o conteúdo mudou.
8. **`window.isActive` pode levantar** com a janela em primeiro plano em
   transição (erro 1400) — `WindowManager._esta_ativa` tenta de novo.
9. **Um funil só para entrada, com gate antes e soltura confirmada depois.** Clique
   só se o ponto pertence ao processo-alvo; tecla só com o alvo em primeiro plano; e o SO
   confirma que botão e modificadores foram soltos. No app lento (o emulador) isso é o
   `HumanPacing`/`InputReleaseError`; no app rápido (o Kit) o risco é o alvo errado — mas o
   custo é o mesmo: tecla presa no emulador só sai reiniciando-o.
10. **Uma alteração de estrutura só vale depois de fechar e reabrir o documento** (visto: aba
    nova/renomeada num editor; salvar sem reabrir descarta o conteúdo escrito nela). Estrutura
    e conteúdo nunca no mesmo save; confirme sempre reabrindo.
11. **Feche janela MDI por menu, não pelo botão da moldura**, que pode estar fora/coberto.
12. **Clique de mouse continua sujeito ao §9.9** (oclusão): mesmo com UIA, use o
   gate de "o ponto pertence ao processo-alvo" antes de clicar.

Detalhes e a lista completa de peculiaridades do Kit: `hp-prime-CK/CLAUDE.md`.

### 9.11. Ler texto e escolher item de lista por nome — `drivers/ocr.py` + `core/listsel.py`

Achado (hp-prime-automation, 29/09/2026). Rodar um programa pelo **Catálogo →
Execut.** (a UX real, e a que se mede) exige escolher a linha pelo NOME numa
lista que reordena por MRU. Foto velha e posição guardada erram de linha
(§9.9). Em vez de cada aplicação reinventar isso, a lógica ficou na
biblioteca, em duas peças que não sabem que existe uma HP Prime:

- **`prumo.drivers.ocr`** (extra `[ocr]`: `winocr` + `pillow`) — `read_lines(img)`
  → `TextLine` com caixa; `similarity(a, b)` tolerante a 0/O e pontuação. É
  instrumento de **leitura**, não interação. ~0,3 s por chamada: só onde ler é
  o objetivo; estado conhecido continua sendo template (§9.2) ou cor (§9.3).
- **`prumo.core.listsel.ListSelector`** — recebe `read_rows()`, `move_down()`,
  `move_up()` e faz o resto: relê a lista a **cada passo**, decide o sentido,
  rola se o alvo está fora da parte visível, **para em `AmbiguousItemError`**
  se dois itens casam igualmente (casamento exato vence um quase igual) e só
  termina quando o item DESTACADO é o pedido. Quem lê as linhas é plugável
  (OCR hoje; template/acessibilidade amanhã), então testa-se sem GUI com uma
  lista falsa (`tests/unit/test_listsel.py`).

O que sobra na aplicação é só o específico: a geometria da lista, a cor do
destaque, as teclas de mover. Custo a reduzir depois (não feito): cachear, por
nome, o recorte da linha depois da 1ª seleção conferida e trocar OCR por
template nas seguintes.

**Dois modos de teste** (regra do usuário, 29/09/2026), independentes da
biblioteca: *validar* ("o código funciona?") pode usar o atalho da interface do
emulador (copiar/colar); *UX* ("otimizar código quase pronto") usa **somente
cliques nos botões** da calculadora, com as limitações de uma real. Ver
`hp-prime-automation`, `HpPrimeCalculator.executar(nome, modo=...)`.

### 9.12. O que os consumidores tiveram de escrever por fora — e voltou pra cá

Achado de 05/10/2026, lendo os dois consumidores que usam o `prumo` **sem** o
`GUIAutomator`: o `hp-prime-CK` (`ck/kit.py`, entrada por UI Automation) e o
e2e do `painel-nativo` da Tina (`tests/e2e/operador.py`, driver direto). Os dois
desceram ao `ctypes` do Win32 para coisas que não são de app nenhum — é o sinal
de que o §22 ainda não fechava: escrever uma aplicação nova exigia sair do
framework. Quatro peças subiram:

- **Foco por processo — `WindowManager.owns_foreground()` / `ensure_foreground()`.**
  "A próxima tecla vai pro app certo?" é pergunta de **processo**, não de
  janela: um menu ou diálogo do próprio app em primeiro plano é outra janela
  top-level, mas a tecla é dele (o mesmo critério do `owns_point`). Falha
  fechado (sem janela na frente, ou sem PID da janela-alvo → `False`).
  `ensure_foreground()` ativa uma vez e reconfere; se outro processo segue na
  frente, `WindowOccludedError`. O `GUIAutomator` não precisa: o `precheck()`
  já ativa antes de toda tecla.
- **"O usuário assumiu" — `core.guard.TakeoverGuard`.** A automação toma o
  mouse de quem está na máquina e não pode ser teimosa: `check()` antes de cada
  gesto levanta `UserTakeoverError` se a tecla de abortar (padrão: ESC) está
  apertada ou se o cursor andou mais que `tolerance_px` (padrão: 8) desde o
  `mark()` feito depois do gesto anterior. No `GUIAutomator` é **opt-in**
  (`guard=TakeoverGuard(driver)`), e a checagem vem **antes** do `activate()`
  — quem acabou de pegar o mouse não pode ter o foco roubado de volta. Dois
  limites declarados: (1) a tecla é lida no instante da checagem — abortar é
  **segurar** ESC, um toque entre dois gestos passa despercebido; (2) todo
  gesto precisa passar pelo caminho guardado ou chamar `mark()` depois — um
  `driver.move_to` solto parece, para a trava, a mão do usuário. Exige do
  driver `cursor_position()` e `is_key_down()` (contrato do §9).
- **Espera genérica — `core.wait.poll_until(cond, timeout=, what=)`.** O
  `StateManager.wait_until` espera um `GUIState` e os `wait_for_template*`
  esperam imagem; faltava "chame isto até dar verdadeiro". Exceção dentro de
  `cond` sobe na hora, salvo as listadas em `retry_on` (ex.: "o controle ainda
  não existe"), que viram nova tentativa e aparecem na mensagem do timeout.
  Engolir erro por padrão seria falha calada.
- **Soltura confirmada para qualquer caminho de entrada —
  `drivers.release.confirm_released()`.** A regra do §9.9 valia só dentro do
  `PyAutoGuiDriver`; quem manda entrada por UIA/`SendKeys` não tinha de onde
  importá-la. Padrão: botões esquerdo e direito + Shift/Ctrl/Alt. O
  `PyAutoGuiDriver` passou a usar a mesma função.

Ficou de fora, de propósito: o gate de ponto **pela UI Automation**
(`ControlFromPoint` com nova tentativa no `COMError`), que também está
duplicado nos dois. Ele depende do `uiautomation` e é a primeira peça de um
driver de UIA (marco v0.6 do [ROADMAP.md](ROADMAP.md)) — sobe junto com ele,
não sozinho. A migração dos consumidores para estas peças é trabalho de cada
um deles, não deste repositório.

### 9.13. `drivers/uia.UiaWindow` — achar, ler e conferir ponto por UI Automation

Primeira fatia do driver de UIA (marco v0.6). O gatilho foi escrito pelo
próprio hp-prime-CK: *o driver sobe quando a UIA tiver um segundo
consumidor* — e o e2e do painel-nativo da Tina virou esse segundo em
02/10/2026. Pelo §22, subiu só a interseção dos dois:

| | hp-prime-CK | e2e da Tina | `UiaWindow` |
|---|---|---|---|
| janela de topo | por classe, PID descoberto | por título, PID fixo (foi ele quem abriu) | `name=` / `class_name=` / `pid=` |
| achar controle com espera | classe/nome | `AutomationId` | `find(timeout=, **props)` |
| "visível" | centro do retângulo | existe **e** tem área | `is_visible(**props)`, `center(control)` |
| ler | `ValuePattern` | `ValuePattern` (+ `RangeValue`) | `value(control)` |
| de quem é o pixel | `ControlFromPoint`, 2ª tentativa no `COMError` | idem | `owns_point(x, y)` |

**Agir não é daqui.** O gesto continua saindo pelo `InputDriver` (ritmo humano,
soltura confirmada, `TakeoverGuard`); a UIA acha o ponto e confere o resultado
(§9.10). Ficaram com o consumidor: `RangeValue` (só a Tina usa) e `Invoke`,
`ExpandCollapse`, `LegacyIAccessible` e os cliques por UIA (só o Kit).

Regras que o desenho guarda:

- **Com `pid` fixo, não há troca silenciosa de instância.** Se a janela some e
  outra igual aparece noutro processo, `root` levanta `WindowNotFoundError` em
  vez de seguir na janela nova.
- **"Existe" não é "visível".** Um elemento `Collapsed` do WPF continua na
  árvore com área zero; `is_visible` e `center` exigem área.
- **`owns_point` é por processo** e só tenta de novo uma vez: um `COMError`
  persistente sobe.

Validado ao vivo em 05/10/2026, só leitura (nenhum clique), contra o Explorador
(pelo caminho do Kit) e o painel-nativo aberto (pelo caminho do e2e: achou
`btn-acionar-luz-abajur` por `AutomationId`, área e centro). Dois achados:

1. **`WindowControl` só casa janela do tipo `Window`.** A barra de tarefas é
   `Pane` e não conecta. Vale para os dois consumidores (os apps deles são
   `Window`); um alvo `Pane` exigiria outra busca.
2. **O gate pegou o caso real:** os três pontos sondados (barra de tarefas,
   centro do Explorador, botão da Tina) eram do Windows Terminal aberto por
   cima, e `owns_point` respondeu `False` nos três. Um clique ali teria caído no
   terminal.

### 9.14. À prova de falhas (v0.9) — as regras que o hardening deixou

Auditoria de 05/10/2026: cada `except`, cada `return True` de gate, cada laço e
cada gesto do driver real, lidos como "como isto falha calado?". As regras
abaixo valem para código NOVO, não só para o que foi consertado.

1. **Nenhuma interrupção deixa botão ou tecla preso no SO.** Entre apertar e
   soltar, qualquer exceção (Ctrl+C, FAILSAFE, `dragTo` interrompido) solta o que
   foi apertado e deixa a exceção seguir. A soltura de emergência não move o
   mouse (quem interrompeu pode ter assumido) e desliga o FAILSAFE só nela (senão
   o próprio FAILSAFE impediria a soltura). Um Shift preso vale para a máquina
   inteira, não só para o app.
2. **Gate que não consegue checar avisa.** Fora do Windows, ou com uma janela
   sem handle Win32, os gates deixam passar — mas dizem no log, uma vez por
   proteção, que ela está desligada (`drivers/_plataforma`). Levantar ali
   quebraria consumidores sem proteger nada em produção (o `pygetwindow` real
   sempre tem handle); calar é o que não pode.
3. **Falhar fechado no que dá para checar.** PID 0 (janela destruída) nunca vira
   "mesmo processo"; sem janela em primeiro plano, "não é dela".
4. **Nada escolhe por sorte.** `WindowManager.find()` com mais de uma candidata
   desempata pelo título exato e, sem desempate, levanta
   `AmbiguousWindowError` (que não herda de `WindowNotFoundError`: quem trata "não
   achei" abrindo o app abriria mais uma instância).
5. **A recuperação não insiste no que piora.** `UserTakeoverError` e
   `InputReleaseError` sobem na hora, sem nova tentativa; as outras falhas
   contam como tentativa perdida e vão pro log uma a uma.
6. **O erro real aparece no lugar do sintoma.** Template ausente, ilegível ou em
   caminho com acento vira erro na leitura, não "timeout esperando aparecer";
   cor com número errado de canais vira `ValueError` (`zip(strict=True)`), não
   uma comparação de menos canais; processo sem DPI awareness vira aviso no log,
   não clique fora do lugar.
7. **`except Exception` só com motivo escrito** (`# noqa: BLE001 - ...`), e nunca
   `except: pass`. O `ruff` do projeto cobra as duas coisas.
8. **Toda espera tem prazo** em `time.monotonic()` — conferido laço a laço.

Como se verifica: `ruff check src tests` (regras de bug, não de estilo), `mypy src`,
`pytest --cov=prumo` com piso de 90%, os testes `win32_real` (só leitura, contra
o Windows de verdade: um `restype` errado truncaria handles em 64 bits sem erro)
e o CI em Windows com Python 3.10–3.12. Um teste de conserto só vale se falhar
contra o código antigo: os 8 do driver real foram rodados contra a versão
anterior e falharam, os 19 de comportamento passaram nas duas.

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

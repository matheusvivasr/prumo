# prumo

Camada de abstração reutilizável para automação determinística de interfaces
gráficas. Permite que um agente — incluindo um LLM — controle uma aplicação através
de uma API semântica estável, sem conhecer coordenadas de tela, posição da janela,
resolução, DPI, widgets, popups ou tempos de resposta.

> O consumidor da API descreve **o que** deseja fazer; `prumo` decide **como**
> executar isso na GUI.

## Por que "prumo"

Um fio de prumo dá referência confiável independente de onde você está — não importa
se a janela mudou de monitor, de posição ou de escala, a leitura continua válida.
Essa é a garantia central do projeto: coordenadas são relativas e recalculadas a cada
execução, nunca gravadas como absolutas.

## Uso pretendido

```python
calc = HpPrimeCalculator()

calc.reset()
calc.type_expression("SIN(45)")
calc.press_enter()

result = calc.get_result()
print(result)
```

O código acima não sabe onde está a janela, qual é a resolução, qual driver está em
uso, como popups são detectados ou como uma falha é recuperada. Essa fronteira é o
que o projeto entrega — detalhes em [ARCHITECTURE.md](ARCHITECTURE.md).

## Estado do projeto

Versão declarada `0.1.0` (as versões marcam etapas do [ROADMAP.md](ROADMAP.md),
não releases). Além do core (locators, janela, driver, estados, interrupções,
recuperação, logging, `MockDriver`), já existem: passo confirmado com ritmo
humano e soltura confirmada no SO, gate de oclusão e de primeiro plano por
processo, trava de "o usuário assumiu" (ESC / mouse mexido), OCR opcional e a
primeira fatia do driver de UI Automation.

Três aplicações consomem o framework, nenhuma delas dentro deste repositório: o
emulador da HP Prime
([`hp-prime-automation`](https://github.com/matheusvivasr/hp-prime-automation)), o HP
Connectivity Kit e um painel desktop WPF (testes ponta a ponta com mouse e
teclado reais).

**À prova de falhas (v0.9, ARCHITECTURE.md §9.14):** nenhum gate "deixa passar"
calado, nenhuma interrupção deixa botão ou tecla preso no SO, nenhuma busca de
janela escolhe por sorte. Lint focado em bug, piso de 90% de cobertura e CI em
Windows (Python 3.10–3.12).

```bash
pip install -e ".[dev,anchors,ocr,uia]"
ruff check src tests
pytest --cov=prumo          # falha abaixo de 90% de cobertura
```

## Documentação

- [ARCHITECTURE.md](ARCHITECTURE.md) — especificação técnica completa: camadas,
  contratos, máquina de estados, regras de segurança.
- [ROADMAP.md](ROADMAP.md) — etapas de implementação e critério de conclusão.
- [CHANGELOG.md](CHANGELOG.md) — histórico de versões.

## Licença

MIT — ver [LICENSE](LICENSE).

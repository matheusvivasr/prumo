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

Core funcional (v0.1.0): locators, janela, driver, máquina de estados,
interrupções, recuperação, logging estruturado e `MockDriver` — testados sem
nenhuma GUI real (39 testes, `pytest`). Ver [ROADMAP.md](ROADMAP.md) para o detalhe
de cada etapa e o que falta.

A HP Prime (via
[`hp-prime-automation`](https://github.com/matheusvivasr/hp-prime-automation)) é a
primeira aplicação-alvo e, mais adiante, o primeiro consumidor externo real do
framework — não faz parte deste repositório.

```bash
pip install -e ".[dev]"
pytest
```

## Documentação

- [ARCHITECTURE.md](ARCHITECTURE.md) — especificação técnica completa: camadas,
  contratos, máquina de estados, regras de segurança.
- [ROADMAP.md](ROADMAP.md) — etapas de implementação e critério de conclusão.
- [CHANGELOG.md](CHANGELOG.md) — histórico de versões.

## Licença

MIT — ver [LICENSE](LICENSE).

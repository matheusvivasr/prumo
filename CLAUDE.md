# CLAUDE.md — prumo

<!-- heranca:raiz -->
> **Herda [`../CLAUDE.md`](../CLAUDE.md)** — convenções do espaço de trabalho: idioma
> pt-BR, SemVer, commits de arrumação sem co-autoria, serviços de logon em
> `matheusvivasr-com\inic\` e a regra de classificação de pastas. **Não repita nada
> disso aqui** — este arquivo guarda só o que é específico de `prumo`.

Camada de abstração reutilizável para automação determinística de GUI. Projeto solto
na raiz (sem guarda-chuva): não compartilha âncora com nenhum outro — é biblioteca
pura, testável sem hardware nem aplicação instalada, e não sobe no `inic/`.

## Regra central: nunca implementar a aplicação-alvo antes do core

O risco declarado em [ARCHITECTURE.md §22](ARCHITECTURE.md#22-critério-de-reutilização)
é construir uma `HPPrimeAutomator` sofisticada disfarçada de `GUIAutomator` genérica.
Por isso a ordem do [ROADMAP.md](ROADMAP.md) é rígida: `applications/hp_prime/` só
nasce na Etapa 8, depois que `core/`, `drivers/`, `config/` e o `MockDriver` (Etapa 7)
já estão testados sem GUI nenhuma. Se uma mudança em `core/` ou `drivers/` só faz
sentido pensando na HP Prime, é sinal de vazamento de abstração — pare e reavalie.

## Fonte de verdade

- Especificação técnica completa (camadas, contratos, máquina de estados, regras de
  segurança): [ARCHITECTURE.md](ARCHITECTURE.md). Não duplique essas regras em código
  — comentário deve apontar para a seção do doc, não reexplicar.
- Progresso e ordem de implementação: [ROADMAP.md](ROADMAP.md).

## Relação com `hp-prime-automation`

`the-calc-project/hp-prime/hp-prime-automation` **não é absorvido** por este repo —
ele é o primeiro consumidor externo real do framework, e essa separação é
intencional (é o teste do §22 acima). A tabela de extração código-a-código está no
[ROADMAP.md](ROADMAP.md#nota-de-migração--hp-prime-automation). Ao portar algo de lá,
mova o código, não copie: o original deve passar a depender de `prumo` como
biblioteca, não manter uma segunda cópia da lógica.

## Convenções específicas

- **Versionamento:** segue o esquema do `pyproject.toml` (`version = "0.0.1"` hoje).
  As versões `v0.1`–`v1.0` do [ROADMAP.md](ROADMAP.md) marcam etapas de
  desenvolvimento, não são releases automáticas — só bump quando o critério de
  conclusão da etapa (ARCHITECTURE.md §21) estiver satisfeito.
- **Testes:** todo o `core/` e `drivers/` (exceto o driver real de PyAutoGUI) deve
  ser testável via `MockDriver`, sem abrir nenhuma aplicação. Um PR que só passa com
  GUI real aberta está testando a camada errada.
- **Nomenclatura:** `prumo/core` e `prumo/drivers` não podem importar nada de
  `prumo/applications` — a dependência é sempre de cima para baixo.

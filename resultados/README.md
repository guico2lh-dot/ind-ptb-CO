# Resultados da varredura semanal

Esta pasta guarda os relatórios gerados a cada execução da routine semanal de
varredura de editais. Cada execução produz **um arquivo** com a data da
varredura.

## Padrão de nomenclatura

```
editais_YYYY-MM-DD.md
```

- `YYYY-MM-DD` = data (ISO 8601) em que a varredura foi executada.
- Exemplo: `editais_2026-07-06.md`
- Um arquivo por semana; não sobrescrever execuções anteriores (o histórico é
  parte do valor do radar).

## Estrutura de cada relatório

Cada `editais_YYYY-MM-DD.md` deve listar as chamadas encontradas, ordenadas por
aderência (Alta → Média → Baixa). Para cada edital, registrar:

| Campo | Descrição |
|-------|-----------|
| **Título** | Nome do edital/chamada |
| **Fonte** | Agência/organização (FAPESP, CNPq, Finep, …) |
| **Aderência** | `Alta` · `Média` · `Baixa` (ver critérios em `../perfil.md`) |
| **Prazo** | Data-limite de submissão |
| **Valor** | Valor/teto do financiamento (ou "não informado") |
| **Elegibilidade** | Adequação ao perfil (doutorando / 2SLH / UNICAMP) |
| **Link** | URL direta para o edital |

### Modelo de entrada

```markdown
## Alta aderência

### [Título do edital]
- **Fonte:** FAPESP — PIPE
- **Aderência:** Alta
- **Prazo:** 2026-08-15
- **Valor:** até R$ 1.500.000 (Fase 2)
- **Elegibilidade:** 2SLH Tech LTDA (pequena empresa) — elegível
- **Link:** https://…
- **Observações:** alinhado à linha de saúde digital / IA em saúde.
```

Repetir os blocos por nível de aderência (`## Alta`, `## Média`, `## Baixa`).
Editais sem correspondência ao perfil podem ser omitidos ou listados em
`## Baixa` apenas para memória.

## Convenções

- Ordenar sempre da maior para a menor aderência.
- Datas em ISO 8601 (`YYYY-MM-DD`).
- Manter os relatórios versionados (não apagar históricos): a evolução das
  chamadas ao longo das semanas é informação útil.

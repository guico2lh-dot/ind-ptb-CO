# CLAUDE.md — ind-ptb-CO

Instruções permanentes para qualquer sessão do Claude Code neste repositório.

---

## ⚠️ Regra de contas: SEMPRE confirmar antes de mexer em login

Guilherme mantém **duas contas do GitHub separadas**, e trocá-las por engano
suja o histórico, vaza contexto entre mundos e pode empurrar commit para o
lugar errado.

| Conta | Escopo |
|---|---|
| **Empresarial** (2SLH Tech) | Desglosa, TriaPrev, AuditCare — produto e cliente |
| **Acadêmica** (login UNICAMP) | Pesquisa: CliMaterna, este repositório, manuscritos |

**Regra, sem exceção:** antes de qualquer ação que envolva autenticação,
credencial, vínculo de conta ou identidade de autoria — `git config
user.email`, login do `gh`, token, chave SSH, ligar um serviço externo ao
GitHub, criar repositório, abrir PR num repositório novo — **pergunte a
Guilherme qual das duas contas usar e espere a resposta.** Não infira pelo
nome do repositório, pelo diretório, pelo que já está configurado na máquina,
nem pelo que foi usado na tarefa anterior.

Se a resposta não vier, **pare** — não é caso de escolher um padrão razoável.

### Decisões já registradas

- **Overleaf** liga-se à conta **acadêmica (UNICAMP)**.
- Este repositório (`ind-ptb-CO`) é **acadêmico**.

> Nota de escopo: este arquivo só é lido em sessões **neste** repositório.
> Para valer nos repositórios empresariais, copie esta seção para o
> `CLAUDE.md` de cada um, ou para o `CLAUDE.md` de usuário
> (`~/.claude/CLAUDE.md`) da máquina local.

---

## O que é este repositório

Código analítico do **RSP-2026-7625** — desigualdades raciais em prematuridade
(PTB <37 semanas) no Centro-Oeste, 2015–2024, com microdados SINASC/DATASUS.
Modelos logísticos progressivos (M1→M8), razões de prevalência por Poisson
modificado com EP clusterizado por município, padronização marginal e análises
de heterogeneidade/sensibilidade.

Serve também de base para a **routine semanal de varredura de editais**
(`perfil.md`, `fontes.md`, `resultados/`).

## Regras invioláveis de dados

- **Microdado do SINASC nunca entra no repositório.** Só código. O `.gitignore`
  já bloqueia `data/`, `*.parquet`, `*.dbc`, `outputs/`.
- **Microdado e dado de beneficiário não vão para ferramenta SaaS de IA.**
  O que circula em serviço externo é texto de manuscrito e metadado
  bibliográfico.
- `ref_clarimar/` é material inédito de colaborador — **não publicar**.
- Raw é **somente leitura**. `DATA_ROOT` aponta para fora do repositório.

## Reprodutibilidade

- `seed = 42` em todo o pipeline.
- Resultados publicados dependem de versões fixadas em `requirements.txt`.
- **Antes de confiar no motor DuckDB para números do artigo**, rodar
  `python 01_code/10_parity_check.py` sobre os Parquet reais. Ele sai com
  código 0 apenas se DuckDB e pandas produzirem dataframes idênticos.
  Em caso de divergência, `PTB_ENGINE=pandas` restaura o caminho original.
- A suíte `tests/` roda sobre microdados **sintéticos** e não precisa de
  `DATA_ROOT`: `python -m pytest tests/ -q`.

## Variáveis de ambiente

| Variável | Padrão | Efeito |
|---|---|---|
| `DATA_ROOT` | `data/sinasc` | Pasta dos `sinasc_YYYY.parquet` |
| `PTB_ENGINE` | `duckdb` | `pandas` volta à leitura original |
| `PTB_VALIDATE` | `1` | `0` desliga a validação de esquema |

## Convenções

- Comentários e documentação em **português**; nomes de código e mensagens de
  commit sem acento.
- Figuras em 300 dpi ou mais, com nome versionado e datado
  (`fig01_tema_v1_YYYYMMDD.png`).
- Resultados estatísticos no padrão Vancouver: efeito estimado sempre
  acompanhado de IC 95% e p-valor.
- `.mcp.json` preenchido **nunca** é versionado — só o `.mcp.json.example`,
  que lê segredos do ambiente via `${VAR}`.

## Documentação de apoio

| Arquivo | Assunto |
|---|---|
| `docs/frente-b-literatura-escrita.md` | Critério: qual ferramenta em qual etapa |
| `docs/setup-zotero-overleaf.md` | Runbook de montagem Zotero + Overleaf |
| `README.md` | Pipeline, reprodução e motor de leitura |

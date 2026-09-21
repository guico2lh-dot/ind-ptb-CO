# Runbook — Zotero, Overleaf e o trilho duplo

Passo a passo de montagem. O documento irmão
[`frente-b-literatura-escrita.md`](frente-b-literatura-escrita.md) explica
**por que** cada ferramenta; este aqui é **como** montar, na ordem.

---

## A decisão de arquitetura

Alguns coautores não escrevem LaTeX e alguns periódicos não aceitam LaTeX.
Logo, dois trilhos de redação — isso é restrição do mundo, não preferência.

O que **não** se duplica é a bibliografia:

```
                 ZOTERO  (biblioteca única, fonte da verdade)
                 Better BibTeX · Retraction Watch · grupos
                            │
            ┌───────────────┴───────────────┐
            │                               │
   TRILHO LaTeX                      TRILHO DOCS/WORD
   .bib sincronizado                 plugin do Zotero cita
   → Overleaf → git → Claude         direto no documento
            │                               │
     manuscrito .tex                 manuscrito .docx
```

Uma biblioteca, dois destinos. Todo o restante deste runbook existe para
manter essa biblioteca confiável.

**O detalhe que faz o trilho Docs funcionar:** no Google Docs, você e seus
coautores podem inserir e editar citações no mesmo documento compartilhado
**sem precisar estar num grupo do Zotero** — basta cada um ter o conector do
Zotero instalado no navegador. O grupo continua valendo para curar o acervo
em conjunto, mas não é pré-requisito para coescrever.

---

## Parte 1 — Conta Zotero com arcabouço de qualidade

### 1.1 Instalação

1. Zotero 7 (desktop) + **Zotero Connector** no navegador.
2. Conta em <https://www.zotero.org/user/register>. Use o e-mail
   institucional — a conta vai carregar os grupos do projeto.
3. **Settings → Sync**: entrar com a conta e ligar a sincronização.

### 1.2 Armazenamento: decida antes de encher

O plano gratuito dá **300 MB**. Uma biblioteca de saúde com PDFs anexados
estoura isso rápido. Planos pagos: **2 GB por US$ 20/ano**, **6 GB por
US$ 60/ano**, **ilimitado por US$ 120/ano**.

Regra que importa para o grupo: **o armazenamento de arquivos de um grupo sai
da cota do dono do grupo**, não da de cada membro. Entrar num grupo e
adicionar itens não exige plano pago.

> Consequência prática: **você** deve ser o dono dos grupos dos seus projetos,
> e o plano pago é seu. Coautor nenhum precisa pagar nada. Comece no 2 GB.

### 1.3 Grupos — um por projeto

Crie em <https://www.zotero.org/groups> como **Private Group**, com edição de
arquivos habilitada:

| Grupo | Escopo |
|---|---|
| `climaterna` | Clima e saúde materno-perinatal (DLNM, SINASC/SIM) |
| `ptb-desigualdades` | RSP-2026-7625 e derivados |
| `idpt` | Educação médica digital |

Minha Biblioteca pessoal fica para leitura exploratória. **Referência que vai
entrar em manuscrito mora no grupo do projeto** — é o que permite ao coautor
ver e citar o mesmo registro.

### 1.4 Coleções dentro do grupo

Uma coleção por manuscrito, mais duas transversais:

```
climaterna/
  00_metodo/            DLNM, séries temporais, validação de exposição
  01_ms_temperatura/    manuscrito 1
  02_ms_umidade/        manuscrito 2
  99_descartados/       lido e rejeitado — com a nota do porquê
```

A pasta `99_descartados` não é burocracia: sem ela você relê o mesmo artigo
ruim três vezes ao longo do doutorado.

### 1.5 Tags — taxonomia curta e obrigatória

Tag demais é o mesmo que tag nenhuma. Duas camadas, só:

**Estágio (tags coloridas, atalho de teclado 1–6):**

| Cor | Tag | Significado |
|---|---|---|
| 🔴 | `x-ler` | Entrou, não foi lido |
| 🟡 | `x-lido` | Lido, ainda não classificado |
| 🟢 | `x-citavel` | Lido, validado, pode citar |
| 🔵 | `x-citado` | Já está em algum manuscrito |
| ⚫ | `x-excluido` | Rejeitado — exige nota com o motivo |

**Conteúdo (livre, mas curto):** `dlnm`, `sinasc`, `prematuridade`,
`raca-cor`, `calor`, `revisao-sistematica`.

Regra de ouro: **nada entra em manuscrito sem `x-citavel`**. Isso transforma
"eu acho que li" em estado verificável.

### 1.6 A regra que sustenta tudo: DOI ou PMID sempre

A verificação de retratação do Zotero **só funciona para itens com DOI ou
PMID** — o que cobre cerca de 3/4 da base do Retraction Watch. Item sem
identificador é ponto cego.

Portanto:

1. Ao capturar pelo conector, confira se o campo **DOI** veio preenchido.
2. Sem DOI, preencha o PMID no campo **Extra** como `PMID: 12345678`.
3. Crie uma **busca salva** chamada `!sem-identificador`:
   *Match all* → `DOI` — *does not contain* — `10.` **e**
   `Extra` — *does not contain* — `PMID`.

Essa busca salva é a sua lista de risco. Mantenha-a vazia.

### 1.7 Retraction Watch

Já vem ligado no Zotero 7 e roda sozinho: item retratado aparece sinalizado
na lista, com aviso e link para o motivo no painel do item.

**Duas proteções, e uma delas você perde no LaTeX:**

| Proteção | Trilho Docs/Word | Trilho LaTeX |
|---|---|---|
| Marcação na biblioteca | ✅ | ✅ |
| Aviso ao inserir a citação | ✅ (plugin) | ❌ — você cita via `.bib` |
| Aviso quando algo já citado é retratado depois | ✅ (ao atualizar citações) | ❌ |

No trilho LaTeX a rede de proteção some. Compense com a rotina da Parte 4.

### 1.8 Better BibTeX — chaves de citação estáveis

Instale o **Better BibTeX (BBT)**. Em *Settings → Better BibTeX → Citation
keys*, defina a fórmula:

```
auth.lower + year + shorttitle(1,0)
```

Gera `coelho2026preterm`. Estável, legível e não colide.

Três cuidados:

1. **Mudar a fórmula não renomeia chaves existentes.** Ela vale para itens
   alterados dali em diante. Para aplicar ao acervo: selecionar os itens →
   botão direito → *Better BibTeX → Refresh*.
2. **Pin as chaves** dos itens já citados em manuscrito ativo (botão direito
   → *Better BibTeX → Pin citation key*). Chave pinada nunca muda — e chave
   que muda sozinha quebra `\cite{}` no meio da revisão.
3. Faça o *Refresh* **antes** de começar a escrever, nunca durante.

---

## Parte 2 — Conector do Zotero no Claude

Já vem no molde `.mcp.json.example` da raiz do repositório.

```bash
cp .mcp.json.example .mcp.json     # .mcp.json é git-ignored
```

**Modo local (recomendado):** em *Settings → Advanced*, marque
**"Allow other applications on this computer to communicate with Zotero"**.
Deixe o Zotero aberto. A entrada já vem com `ZOTERO_LOCAL=true` e não precisa
de chave de API — a biblioteca não sai da sua máquina.

**Modo Web API** (para alcançar um grupo de outra máquina): gere a chave em
<https://www.zotero.org/settings/keys> e preencha `ZOTERO_API_KEY`,
`ZOTERO_LIBRARY_ID` e `ZOTERO_LIBRARY_TYPE=group` com o ID do grupo.

Ferramentas expostas: `zotero_search_items`, `zotero_item_metadata`,
`zotero_item_fulltext`. **Somente leitura** — é a propriedade que interessa:
eu leio e cito o que você validou, e não escrevo nada na sua biblioteca.

Teste de fumaça, depois de configurar:

```
claude mcp list          # zotero deve aparecer conectado
```

e então me peça: *"busca no Zotero o que eu tenho sobre DLNM e temperatura"*.
Se vier vazio com a biblioteca cheia, o Zotero está fechado ou a API local
está desligada.

---

## Parte 3 — Overleaf e o acesso por git

### 3.1 Confirme o acesso institucional primeiro

A UNICAMP assinou o **Overleaf Commons** (vigência de 36 meses a partir de
jan/2026). Entre em <https://www.overleaf.com> com o e-mail `@unicamp.br` e
confirme que a conta aparece como institucional — é o que libera git,
integração com gerenciador de referências, track changes e histórico
completo, sem custo. **Não assine plano individual antes de checar isso.**

### 3.2 Token e clone

1. Overleaf → **Account Settings → Git Integration → Create Token**.
   Copie na hora: o token não é exibido de novo.
2. Pegue o `PROJECT_ID` na URL: `overleaf.com/project/<PROJECT_ID>`.
3. Clone:

   ```bash
   git clone https://git.overleaf.com/<PROJECT_ID> manuscrito
   cd manuscrito
   ```

   Usuário: `git`. Senha: **o token**. Autenticação por usuário/senha da
   conta foi descontinuada — token é o único método.

4. Guarde o token fora do repositório:

   ```bash
   git config --global credential.helper store   # ou use o keychain do SO
   ```

   Nunca commite o token. Nunca o cole no `.mcp.json` versionado.

### 3.3 Rotina de trabalho

```bash
git pull          # SEMPRE antes de editar — coautor pode ter mexido na web
# ... Claude edita o .tex ...
git add -A && git commit -m "Methods: cascata de exclusão"
git push
```

`git pull` antes de tudo é inegociável: o Overleaf é editado pela web em
paralelo, e conflito de merge em `.tex` com dois autores é trabalhoso.
Para operações menos triviais, a documentação do Overleaf tem uma página de
*Advanced Git operations* — vale ler antes de inventar.

### 3.4 Bibliografia dentro do Overleaf

Duas formas de levar o Zotero para o `.tex`:

| Forma | Como | Quando |
|---|---|---|
| **Integração nativa** | Overleaf → *Upload → From Zotero*, gera `.bib` somente-leitura sincronizável (recurso premium, que o Commons cobre) | Padrão |
| **Auto-export do BBT** | No Zotero, exportar a coleção em formato *Better BibTeX* com *Keep updated* ligado, apontando para o `.bib` do repositório clonado | Quando você quer o `.bib` versionado no git junto do `.tex` |

A segunda combina melhor com o fluxo deste repositório: o `.bib` vira arquivo
versionado, e o diff de bibliografia aparece no histórico como qualquer outra
mudança.

**Nunca** exporte um `.bib` à mão e deixe rodando por meses. `.bib` congelado
não recebe aviso de retratação nenhum, e esse é exatamente o cenário do
pesquisador que cita em 2026 um artigo retratado em 2025.

### 3.5 Trilho Docs/Word, para os coautores

1. Cada coautor instala o **Zotero Connector** no navegador (e o Zotero
   desktop, se for usar Word).
2. No Google Docs, aparece o menu **Zotero**. Citam direto, buscando na
   própria biblioteca ou no grupo compartilhado.
3. Coescrita funciona sem grupo do Zotero — mas compartilhe o grupo mesmo
   assim, para que todos citem o **mesmo registro** e não três variantes do
   mesmo artigo.

Ao fim, o documento do Docs sai com bibliografia formatada, pronto para o
periódico que não aceita LaTeX.

---

## Parte 4 — Rotinas de manutenção

**Semanal (5 min)**

- [ ] Busca salva `!sem-identificador` está vazia?
- [ ] Nada parado em `x-lido` há mais de duas semanas?

**Antes de começar a escrever um manuscrito**

- [ ] *Duplicate Items* revisado e mesclado
- [ ] *Better BibTeX → Refresh* na coleção
- [ ] Chaves dos itens centrais **pinadas**

**Antes de submeter — o checklist que fecha o buraco do LaTeX**

- [ ] Reabrir a biblioteca e varrer os sinalizadores de retratação
- [ ] Conferir que toda referência citada está com `x-citavel`
- [ ] Rodar uma auditoria de referências do manuscrito (ver
      `frente-b-literatura-escrita.md`, seção de análise de referências)
- [ ] Conferir o estilo de citação exigido pelo periódico (Vancouver/ICMJE
      por padrão)

---

## Ordem de execução

| # | Passo | Depende de |
|---|---|---|
| 1 | Zotero instalado + conta + sync | — |
| 2 | Plano de armazenamento decidido | 1 |
| 3 | Grupos criados, você como dono | 2 |
| 4 | Coleções e tags aplicadas | 3 |
| 5 | Busca salva `!sem-identificador` criada e zerada | 4 |
| 6 | Better BibTeX instalado e fórmula definida | 1 |
| 7 | API local ligada + `.mcp.json` + teste de fumaça | 1 |
| 8 | Overleaf institucional confirmado | — |
| 9 | Token git + clone | 8 |
| 10 | `.bib` sincronizado no projeto | 6, 9 |
| 11 | Coautores com o conector instalado | 3 |

Os passos 1–7 e 8–9 são independentes: dá para tocar os dois em paralelo.

---

## Fontes

- [Zotero — usando com Google Docs](https://www.zotero.org/support/google_docs)
- [Zotero — FAQ de armazenamento](https://www.zotero.org/support/storage_faq)
- [Zotero — planos de armazenamento](https://www.zotero.org/storage)
- [Zotero — notificações de retratação (Retraction Watch)](https://www.zotero.org/blog/retracted-item-notifications/)
- [Better BibTeX — chaves de citação](https://retorque.re/zotero-better-bibtex/citing/)
- [Overleaf — integração Git](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration)
- [Overleaf — tokens de autenticação do Git](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration/git-integration-authentication-tokens)
- [Overleaf — operações avançadas de Git](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration/advanced-git-operations)
- [Overleaf — integração com Zotero](https://docs.overleaf.com/integrations-and-add-ons/reference-manager-integrations/zotero)
- [Overleaf Commons — o que a assinatura institucional entrega](https://docs.overleaf.com/commons)
- [UNICAMP/DETIC — Overleaf Commons liberado](https://www.detic.unicamp.br/2026/02/06/unicamp-libera-acesso-a-plataforma-overleaf-commons-para-toda-a-comunidade-universitaria/)
- [zotero-mcp (kujenga)](https://github.com/kujenga/zotero-mcp)

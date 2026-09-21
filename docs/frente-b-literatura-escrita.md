# Frente B — literatura, escrita e submissão

Critério: **qual** ferramenta usar em cada etapa e por quê. O passo a passo
de montagem está no runbook irmão,
[`setup-zotero-overleaf.md`](setup-zotero-overleaf.md).

Escopo: os artigos do CliMaterna
e o RSP-2026-7625 deste repositório.

Nada aqui toca nos microdados. A regra que vale para tudo neste documento:
**microdado do SINASC e dado de beneficiário não entram em ferramenta SaaS**.
O que circula é texto do manuscrito e metadado bibliográfico.

---

## 1. Overleaf ligado ao Claude

Duas formas, que se complementam. A primeira é obrigatória — a segunda depende
dela.

### 1.0 A UNICAMP já paga por isso

A integração Git é recurso premium do Overleaf — e **a UNICAMP assinou o
Overleaf Commons**, que entrega o conjunto premium a toda a comunidade com
vínculo ativo. A documentação do Overleaf é explícita: a integração Git está
disponível para participantes do Commons, membros de assinaturas de grupo e
assinantes individuais.

- **Elegibilidade:** e-mail `@unicamp.br` ou subdomínio, vínculo ativo.
- **Vigência:** 36 meses a partir de janeiro de 2026 (disponível desde
  2026-02-09).
- **Como ativar:** entrar no Overleaf com as credenciais institucionais.

Ou seja: para o doutorado na FCM, o git bridge, os 10+ colaboradores, o
track changes e o histórico completo saem de graça. Antes de assinar
qualquer plano individual, confirme que sua conta está reconhecida como
institucional — o portal da DETIC/SBU tem as instruções.

### 1.1 Git bridge (a base)

A integração Git expõe o projeto como um repositório Git comum.

1. Overleaf → **Account Settings → Git Integration → Create Token**.
   Guarde o token: ele não é exibido de novo.
2. O `PROJECT_ID` está na URL do projeto:
   `https://www.overleaf.com/project/<PROJECT_ID>`.
3. Clone:

   ```bash
   git clone https://git.overleaf.com/<PROJECT_ID> manuscrito
   ```

   Usuário: `git`. Senha: **o token** — autenticação por usuário/senha da conta
   foi descontinuada; token é o único método hoje.

Com isso o Claude Code já lê e edita o `.tex` como qualquer arquivo do
repositório, e `git push` devolve para o Overleaf. Para sessões longas de
escrita, esse caminho basta e é o mais previsível: o diff é o de sempre.

### 1.2 Servidor MCP (edição por seção)

Por cima do git bridge, o MCP dá ao Claude as operações que interessam num
manuscrito — listar seções, ler uma seção isolada, reescrever só a Discussion
sem carregar o documento inteiro no contexto.

```bash
export OVERLEAF_PROJECT_ID=...      # da URL do projeto
export OVERLEAF_GIT_TOKEN=...       # o token do passo 1.1
cp .mcp.json.example .mcp.json      # .mcp.json é git-ignored
```

Ferramentas expostas: `list_files`, `read_file`, `get_sections`,
`get_section_content`, `status_summary`, `write_file`, `write_section`
(esta última já faz o commit no git do Overleaf).

**Antes de aceitar escrita automática**, trave o hábito: compile no Overleaf
depois de cada `write_section`. Um `\cite{}` quebrado ou um ambiente `table`
mal fechado só aparece na compilação, e o MCP não compila.

> Existem várias implementações de MCP para Overleaf, com escopos diferentes
> (só leitura, CRUD completo, verificação de citações). O molde em
> `.mcp.json.example` usa a de edição por seção via git. Nenhuma é oficial do
> Overleaf — são projetos de terceiros, avalie antes de dar acesso de escrita
> a um manuscrito em revisão.

---

## 2. Zotero ligado ao Claude

Objetivo específico: **o Claude só cita o que você já leu e validou**. Isso
ataca diretamente o risco de referência inventada, porque a busca passa a ser
na sua biblioteca, não na memória do modelo.

Modo local (recomendado — a biblioteca não sai da máquina):

1. Zotero → **Settings → Advanced → Allow other applications on this computer
   to communicate with Zotero** (API local).
2. Deixe o Zotero aberto. A entrada `zotero` do `.mcp.json.example` já vem
   configurada com `ZOTERO_LOCAL=true` e não precisa de chave de API.

Ferramentas: `zotero_search_items`, `zotero_item_metadata`,
`zotero_item_fulltext` (lê o PDF anexado). Somente leitura — o servidor não
escreve na sua biblioteca, o que é a propriedade que você quer aqui.

Modo Web API (biblioteca de grupo, ou várias máquinas): gere a chave em
<https://www.zotero.org/settings/keys> e preencha `ZOTERO_API_KEY` e
`ZOTERO_LIBRARY_ID`. Nesse modo os metadados trafegam pela API do Zotero.

---

## 3. Qual corretor em qual etapa

O erro comum é usar uma ferramenta só para tudo. As três abaixo não competem
entre si — atuam em camadas diferentes do texto.

| Etapa | Ferramenta | O que ela resolve |
|---|---|---|
| Rascunho, e-mail, texto não acadêmico | **Grammarly** | Gramática e tom geral. Não conhece registro acadêmico: sugere simplificações que um revisor de periódico lê como imprecisão. |
| Manuscrito em LaTeX/Word | **Writefull** | Compara o seu fraseado com um corpus de artigos publicados. Integrado **nativamente** ao Overleaf — Writefull e Overleaf são empresas irmãs no grupo Digital Science, e a integração dispensa extensão. Lê através do markup sem corromper fórmula nem `\cite{}`. Também tem add-in de Word. |
| Polimento final e verificação | **Paperpal** | Feedback de estrutura no documento inteiro e checagem de plágio antes da submissão. |

**Recomendação para o seu fluxo:** Writefull dentro do Overleaf. Grammarly não
cobre o que o Writefull cobre — se for para manter só um para o manuscrito, é
o Writefull.

**Antes de pagar os ~US$ 150/ano do Writefull Premium**, pergunte à DETIC/SBU
se a UNICAMP também licencia o Writefull. A licença institucional dele cobre
Writefull for Overleaf, for Word, Revise e Cite para toda a comunidade, e é
contratada à parte do Overleaf Commons — não vem junto automaticamente, mas
instituições que já assinam o Overleaf são o público natural dela. Vale o
e-mail antes de gastar.

**Paperpal** (~US$ 139/ano) só entra se aparecer uma destas necessidades:
escrever em **Google Docs** (o Writefull não cobre), **tradução PT→EN**, ou os
**pre-submission checks** — cuja lista de periódicos cobertos vale confirmar
antes, já que é o recurso que justificaria a assinatura.

Nenhum dos três decide AE vs BE por você. Isso continua sendo regra de
projeto:

| Periódico-alvo | Variante | Detalhes operacionais |
|---|---|---|
| JESEE (Nature Portfolio), PLOS Climate, AJOG, AJPH | **American English** | `-ize`, "data is", `1,234,567`, `Dr` sem ponto |
| The Lancet Planetary Health, BMJ, BJOG | **British English** | `-ise`, "data are", ponto médio (`1·234·567`, `p<0·0001`), `Dr.` com ponto |

Configure a variante **no Writefull, por projeto** — ele checa contra o corpus
da variante escolhida, e trocar no meio do manuscrito produz inconsistência
que revisor nota.

---

## 4. Triagem de revisão (quando houver revisão sistemática)

- **Rayyan** — gratuito, colaborativo, triagem cega, deduplicação e diagrama
  PRISMA no plano Essential. É o padrão quando há mais de um revisor.
- **Elicit** — melhor para volume alto e apoio à extração de dados.

**Limite conhecido, e ele é grande:** um estudo comparativo publicado em
*Systematic Reviews* (2026) avaliou as ferramentas gratuitas de triagem e
nenhuma identificou mais de 50% dos estudos incluídos nos primeiros 25% da
triagem. Ou seja: aceleram a ordenação, **não substituem dupla revisão
independente**, e o método da sua revisão continua tendo que dizer isso.

---

## 5. Análise e integridade de referências

Três camadas, e só a última custa dinheiro.

**Zotero + Retraction Watch (grátis, contínuo).** A verificação é automática:
item retratado aparece sinalizado na biblioteca, com o motivo no painel. Pelo
plugin de Word/Docs, ele ainda avisa no momento de citar e quando algo já
citado é retratado depois. **Funciona apenas para itens com DOI ou PMID** —
cerca de 3/4 da base do Retraction Watch. Daí a regra de identificador
obrigatória do runbook.

**A lacuna do trilho LaTeX.** Citando via `.bib`, o aviso no momento da
citação não existe — só a marcação na biblioteca. Quem escreve em Overleaf
perde a rede e precisa da varredura manual antes de submeter.

**scite Reference Check (pontual).** Sobe o manuscrito e audita as
referências contra retratações, erratas e avisos editoriais. Junto vem o
Smart Citations: para cada artigo, quantas citações o **apoiam**, quantas o
**contrastam** e quantas apenas o **mencionam**, com o trecho exato — citar
um achado já contrariado é erro de argumento, não de formatação. ~US$ 12/mês
no anual, com trial de 7 dias.

> Não assine no anual. Use o trial no próximo manuscrito e, se provar valor,
> pague por mês nos ciclos de submissão. Há desconto acadêmico ao recomendar
> à instituição — mande junto com a pergunta sobre o Writefull.

A classificação supporting/contrasting é automática e vem com percentual de
confiança: trate como triagem, não como veredito. A base metodológica está
publicada em *Quantitative Science Studies*.

---

## 6. Checklist de instalação

- [ ] Token Git do Overleaf criado e guardado (não versionar)
- [ ] `git clone https://git.overleaf.com/<PROJECT_ID>` funciona
- [ ] `cp .mcp.json.example .mcp.json` com `OVERLEAF_*` exportados
- [ ] API local do Zotero habilitada, Zotero aberto
- [ ] `claude mcp list` mostra `overleaf` e `zotero` conectados
- [ ] Teste de fumaça: pedir `get_sections` do manuscrito e uma busca no Zotero
- [ ] Writefull instalado no Overleaf, com a variante AE/BE do periódico-alvo
- [ ] Hábito travado: compilar no Overleaf depois de toda escrita automática
- [ ] Busca salva `!sem-identificador` do Zotero criada e zerada (ver runbook)

---

## Fontes

- [Overleaf — Git integration](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration)
- [Overleaf — Git é premium, disponível a participantes do Commons](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git)
- [Overleaf Commons — o que a assinatura institucional entrega](https://docs.overleaf.com/commons)
- [UNICAMP/DETIC — Overleaf Commons liberado para a comunidade](https://www.detic.unicamp.br/2026/02/06/unicamp-libera-acesso-a-plataforma-overleaf-commons-para-toda-a-comunidade-universitaria/)
- [Overleaf — Writefull agora integrado, sem extensão](https://www.overleaf.com/blog/update-writefull-is-now-integrated-with-overleaf-no-extension-needed)
- [Writefull — licença institucional (Overleaf, Word, Revise, Cite)](https://www.writefull.com/for-institutions-overleaf)
- [Paperpal — preços oficiais](https://support.paperpal.com/support/solutions/articles/3000126443-what-is-the-price-for-paperpal-paid-subscriptions-)
- [Overleaf — Git integration authentication tokens](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration/git-integration-authentication-tokens)
- [OverleafMCP (mjyoo2)](https://github.com/mjyoo2/overleafmcp)
- [zotero-mcp (kujenga)](https://github.com/kujenga/zotero-mcp)
- [Evaluating the use of AI in systematic review abstract screening — *Systematic Reviews*, 2026](https://link.springer.com/article/10.1186/s13643-026-03313-8)
- [Rayyan](https://www.rayyan.ai/)
- [Zotero — notificações de retratação (Retraction Watch)](https://www.zotero.org/blog/retracted-item-notifications/)
- [scite — features e Reference Check](https://scite.ai/features)
- [scite — preços](https://scite.ai/pricing)
- [scite: a smart citation index — *Quantitative Science Studies*](https://direct.mit.edu/qss/article/2/3/882/102990/scite-A-smart-citation-index-that-displays-the)
- [Runbook de montagem](setup-zotero-overleaf.md)

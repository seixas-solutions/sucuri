# EXTERNAL — Ações externas, credenciais e downloads manuais

Itens que NÃO podem ser resolvidos automaticamente pelo código do projeto:
dependem de cadastro, download manual ou execução longa fora da sessão.
Salvar todo arquivo baixado manualmente em `dados/externos/` (criar a pasta),
com nome indicado abaixo, e nunca commitar dados brutos grandes nem credenciais.

## Credenciais

### C1. Chave da API do Portal da Transparência (já configurada)
- Cadastro: https://api.portaldatransparencia.gov.br/ (e-mail gov.br)
- Armazenada em `/Users/leseixas/.env` como `GOVBR_API_KEY`.
- **Nunca** commitar, imprimir em log ou copiar para o repositório.
- Limite: ~90 requisições/min (6h–24h) e ~300/min (0h–6h). Coletas da fase 3
  (contratos/licitações por ~115 órgãos × vários anos) podem levar horas —
  rodar fora do horário comercial quando possível.

## Comandos a executar externamente (longos ou com efeito em rede)

### X1. Recoleta dos dados de despesas
```bash
cd ~/Library/CloudStorage/Dropbox/Repositories/seixas-solutions/sucuri
uv run --with pandas,pyarrow,requests,python-dotenv python coletar_despesas.py
```
Duração típica: alguns minutos. Rodar ao virar o ano ou para atualizar o ano
corrente. Após a tarefa 0.1 do ROADMAP: apenas `uv run python coletar_despesas.py`.

### X2. Coletas da fase 3 (contratos, licitações, convênios, CPGF, emendas)
Cada coletor novo (ROADMAP 3.2–3.7) deve ser executado externamente pelo
usuário (tempo longo + rate limit), ex.:
```bash
uv run python -m sucuri.coletores.contratos --ano-inicio 2018
```
O modelo deve criar o coletor e um teste com 1 órgão × 1 ano; a coleta
completa fica a cargo do usuário.

## Downloads manuais / em lote

### E1. IPCA anual (pré-requisito da tarefa 1.2) — ✅ automatizado
- **Automatizado** em `analises/00_baixar_ipca.py`: baixa a série mensal do
  IPCA (Banco Central, SGS série 433 —
  `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json`,
  pública, sem cadastro, sem relação com `GOVBR_API_KEY`), calcula o
  acumulado por ano civil e salva `dados/externos/ipca_anual.csv`
  (`ano,ipca_acumulado_pct`) + `dados/externos/ipca_anual_detalhe.csv`
  (com `n_meses`/`ano_completo`, usado por `sucuri.deflacao` para achar o
  último ano completo). Reexecutar quando precisar atualizar:
  `uv run python analises/00_baixar_ipca.py`.
- Fonte alternativa (caso a API do BCB fique indisponível): SIDRA/IBGE,
  tabela 1737 (IPCA acumulado no ano) —
  https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidor-amplo.html
  — nesse caso, montar manualmente o CSV no mesmo formato
  (`ano,ipca_acumulado_pct`) e salvar em `dados/externos/ipca_anual.csv`.

### E2. Downloads em lote do Portal da Transparência
Para volumes grandes (despesas detalhadas por documento, CPGF completo), o
portal oferece arquivos mensais em CSV que evitam o rate limit da API:
- https://portaldatransparencia.gov.br/download-de-dados
- Conjuntos úteis: "Despesas — Execução", "Cartão de Pagamento (CPGF)",
  "Contratos", "Licitações", "Convênios", "Emendas parlamentares",
  "CEIS/CNEP".
- Salvar zips em `dados/externos/portal_lote/<conjunto>/` (manter nome original).

### E3. Censo da Educação Superior — INEP (pré-requisito da tarefa 4.1)
- Microdados: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior
- Basta a tabela de matrículas por IES (não precisa do microdado completo);
  a "Sinopse Estatística" (xlsx) por ano é suficiente.
- Salvar como: `dados/externos/inep/matriculas_ies_<ano>.xlsx` (ou csv extraído).

### E4. Dotação orçamentária — SIOP/LOA (pré-requisito da tarefa 4.2)
- Painel do Orçamento: https://www1.siop.planejamento.gov.br/paineldoorcamento/
- Exportar dotação atualizada por programa/ação, função 12, subfunção 364,
  2014–ano atual.
- Salvar como: `dados/externos/siop_dotacao.csv`.

### E5. Acórdãos TCU / relatórios CGU (pré-requisito da tarefa 4.3)
- TCU: https://pesquisa.apps.tcu.gov.br/ (buscar pelo nome da instituição)
- CGU: https://eaud.cgu.gov.br/ (relatórios de auditoria por órgão)
- Consulta manual caso a caso após a tarefa 2.5 gerar os top casos; salvar
  notas em `dados/externos/tcu_cgu_notas.md`.

## Higiene do repositório
- Adicionar ao `.gitignore` (se ainda não estiver): `dados/externos/`,
  `dados/raw/*.json` (grandes), `.env`, `relatorios/figuras/*.png` (opcional).
- Decidir política de versionamento dos parquets tratados (hoje os dados
  processados estão commitados; manter apenas se o tamanho continuar <10 MB).

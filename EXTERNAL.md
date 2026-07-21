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
uv run python coletar_despesas.py                # integral (2014..ano atual)
uv run python coletar_despesas.py --incremental  # só anos novos/em aberto (tarefa 5.3)
```
Duração: alguns minutos na coleta integral; segundos no modo incremental
(fora da virada de ano ele só recoleta o exercício corrente). O modo
incremental reaproveita o bruto mais recente de `dados/raw/` e recoleta
apenas os anos ausentes ou que estavam com exercício em aberto na última
coleta (regra em `src/sucuri/incremental.py`, testada em
`tests/test_incremental.py`); sem bruto anterior, cai na coleta integral.

### X1b. Rotina mensal de recoleta (tarefa 5.3)
Uma vez por mês (ex.: dia 1º), rodar em sequência:
```bash
cd ~/Library/CloudStorage/Dropbox/Repositories/seixas-solutions/sucuri
uv run python analises/00_baixar_ipca.py          # IPCA atualizado (BCB)
uv run python analises/00b_baixar_ibge.py         # população IBGE (sem chave)
uv run python coletar_despesas.py --incremental   # despesas: só anos em aberto
uv run python analises/01b_deflacionar.py         # regera *_real
uv run python analises/01c_ano_parcial_e_flags.py # regera *_v2 (base das análises)
uv run python analises/14_ibge_cruzamento.py      # per capita / emendas por UF
```
As análises da Fase 2 (02_eda a 06_casos) só precisam ser rodadas de novo
quando os `*_v2` mudarem de forma relevante (ano novo ou revisão da API).
Atenção: o pipeline continua assumindo o ano do carimbo mais recente de
`dados/raw/` como ano parcial — rodar a rotina completa, não etapas soltas.

### X2. Coletas da Fase 3 em escala (contratos, licitações, convênios, CPGF, emendas)
Os coletores (`src/sucuri/coletores/*.py`) estão prontos e testados
(mocks, sem rede, em `tests/`); os pilotos reais rodados nas tarefas
3.1–3.7 usaram uma amostra de 15 instituições (ou, no caso de convênios,
todo o MEC de uma vez via `codigoOrgao=26000`), não os ~115 órgãos do
Conjunto B. Para ampliar:

```bash
# Lista completa de códigos de órgão do Conjunto B:
uv run python -c "
import pandas as pd
df = pd.read_parquet('dados/despesas_por_instituicao_v2.parquet')
print(df[['codigoOrgao','orgao']].drop_duplicates().to_string(index=False))
"
```

- **`analises/08_contratos.py` / `09_licitacoes.py` / `12_cartoes.py`**:
  editar a lista `INSTITUICOES_PILOTO` no topo do script, trocando as 15
  instituições pela lista completa acima (ou um subconjunto maior).
  Volume observado no piloto: ~4.300 contratos, ~1.100 licitações
  (só 2024), ~16.400 transações CPGF para 15 instituições em 2–3 anos —
  rodar para ~115 órgãos e/ou período maior pode levar bem mais de 1 hora
  (`/licitacoes` em particular: 1 requisição por mês por órgão).
- **`analises/10_sancoes.py`**: editar `COBERTURA_VALOR_ALVO` (hoje 0,80)
  para consultar mais fornecedores, ou passar a lista completa de CNPJs de
  `contratos_mec.parquet` em vez do corte por valor.
- **`analises/11_convenios.py`**: já cobre MEC/FNDE/CAPES inteiro numa
  chamada (`codigoOrgao=26000`); para ampliar, só o intervalo de datas
  precisaria mudar (já é 2018–2025).
- **`analises/13_emendas.py`**: já cobre o país inteiro para a subfunção
  364 (o filtro é por função/subfunção, não por órgão); nada a ampliar
  aqui — a limitação é a ausência de instituição beneficiária no payload
  (ver E6).
- **`analises/07_despesas_documentos.py`**: exige um código de Unidade
  Gestora válido por instituição — ver item E6 abaixo antes de tentar
  rodar para outras instituições além do piloto (Ouro Preto, UG 154046).

## Downloads manuais / em lote

> **Guia detalhado:** `relatorios/coletas_finais/main.tex` (+ `main.pdf`)
> traz o passo a passo de cada coleta manual pendente (E3–E7): URLs,
> filtros, nome exato do arquivo de destino e qual tarefa cada uma
> destrava.

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

### E1b. Dados do IBGE via sidrapy (pré-requisito da tarefa 4.4) — ✅ automatizado
- **Automatizado** em `analises/00b_baixar_ibge.py`, usando a biblioteca
  `sidrapy` (API SIDRA do IBGE — pública, sem cadastro, sem relação com
  `GOVBR_API_KEY`): população residente estimada (tabela 6579, variável
  9324; Brasil e por UF) e PIB por UF a preços correntes (tabela 5938,
  variável 37, Contas Regionais — defasagem de ~2 anos). Saídas:
  `dados/externos/ibge_populacao_brasil.csv`, `ibge_populacao_uf.csv` e
  `ibge_pib_uf.csv`. Anos de população sem estimativa publicada (2022,
  2023) são interpolados linearmente e marcados em `interpolado`.
- Coletor genérico em `src/sucuri/ibge.py` (`coletar_tabela_sidra`) —
  outras tabelas da SIDRA (ex.: Censo 2022: 9514) podem ser consultadas
  sem código novo de rede.

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
  notas em `dados/externos/tcu_cgu_notas.md`. **Prioridade sugerida pela
  Fase 3:** a "Fundação Euclides da Cunha de Apoio Institucional à UFF"
  apareceu como caso atípico em 3 tarefas independentes (3.2, 3.3, 3.5) —
  ver `relatorios/RELATORIO.md`, Parte IV, introdução.

### E6. Mapeamento código de órgão → Unidade Gestora (pré-requisito para ampliar as tarefas 3.1 e 3.7)
- **Achado da Fase 3:** `/despesas/documentos` e `/emendas/documentos/{codigo}`
  filtram/identificam por **Unidade Gestora (UG)**, um código SIAFI de 6
  dígitos diferente do `codigoOrgao` de 5 dígitos usado em todo o resto do
  projeto — e esta API não tem endpoint público para converter um no
  outro (`/orgaos-siafi` só resolve `codigoOrgao`).
- Os arquivos de download em lote do portal (item E2 acima, conjunto
  "Despesas — Execução") trazem `codigoOrgao` e `codigoUg` na mesma linha
  — baixar um mês de qualquer ano, extrair os pares únicos
  (`codigoOrgao`, `codigoUg`) e montar uma tabela de referência salva em
  `dados/externos/mapa_orgao_ug.csv` (`codigoOrgao,codigoUg,nomeOrgao`).
- Com essa tabela, `analises/07_despesas_documentos.py` (tarefa 3.1) e uma
  eventual extensão de `analises/13_emendas.py` (tarefa 3.7, hoje só
  agregada nacionalmente) podem rodar por instituição do Conjunto B, não
  só o piloto de Ouro Preto.

### E7. Confirmação de truncamento no CPGF do EBSERH (opcional, tarefa 3.6)
- A coleta de `analises/12_cartoes.py` recebeu HTTP 400 ("Erro ao
  executar a consulta") na página 175 da consulta do EBSERH — o código
  atual trata isso como fim da paginação, então os 2.610 registros
  salvos podem estar incompletos.
- Para confirmar: rodar novamente só o EBSERH
  (`coletar_cartoes(sessao, "26443", 2023, 2025)`) e comparar a contagem;
  se ainda parar na mesma página, tentar dividir o intervalo em janelas
  menores (ex.: ano a ano) para contornar o erro pontual do servidor.

## Higiene do repositório
- Adicionar ao `.gitignore` (se ainda não estiver): `dados/externos/`,
  `dados/raw/*.json` (grandes), `.env`, `relatorios/figuras/*.png` (opcional).
- Decidir política de versionamento dos parquets tratados (hoje os dados
  processados estão commitados; manter apenas se o tamanho continuar <10 MB).

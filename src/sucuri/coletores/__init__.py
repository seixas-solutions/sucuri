"""Coletores da Fase 3 — enriquecimento com outros dados do Portal da Transparência.

Cada módulo aqui expõe uma função `coletar_<nome>(sessao, ...)` que reusa
`sucuri.api.coletar_paginado`/`coletar_intervalo` (mesma sessão, mesmo
rate-limit, mesmo backoff do coletor original). Nenhum módulo aqui lê ou
imprime `GOVBR_API_KEY` — a sessão autenticada é sempre recebida pronta de
quem chama (ver `sucuri.api.criar_sessao`).

Coletas em escala (todos os ~115 órgãos do Conjunto B × vários anos) são
de responsabilidade do usuário, não deste projeto rodando sozinho — ver
EXTERNAL.md, item X2. O que roda aqui são pilotos pequenos (1–3 órgãos)
para validar que cada coletor funciona contra a API real.
"""

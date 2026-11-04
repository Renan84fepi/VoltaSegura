# Prompt v4 — Etapas 8 a 10 (Pagamento simulado, avaliação, histórico e PWA)

> Pré-requisito: prompt v3 concluído e validado (ciclo da corrida com RN01–RN09, API REST, polling).

## Contexto
VoltaSegura: PWA em Django em que clientes pedem um motorista para conduzir o carro do cliente; o motorista chega com uma mini bicicleta elétrica dobrável. Estamos no **Marco 4 — Pagamento, avaliação e PWA**. Continue concentrando as regras no módulo de serviço (`corridas/regras.py`), com comentários citando a regra (RN##/RF##). As views só chamam as regras.

## Tarefa desta etapa
1. **Pagamento (RF19, RF20):** ao finalizar a corrida, gerar o pagamento **na mesma transação**: forma (Pix/cartão, a escolhida no pedido), valor total, % da plataforma, taxa da plataforma, repasse ao motorista e status, em campos separados. Usar o percentual guardado na corrida, não a configuração atual.
2. **Simulação (RF21):** status pendente → aprovado | recusado; recusado pode ser tentado de novo; só aprovado é estornado (pelo admin); estornado é final. Mapa de transições como o da corrida, e cada mudança gera um evento com data/hora e autor (RNF09). O cliente paga pela tela da corrida; com `DEBUG=True`, um botão permite simular a recusa.
3. **Regra da dupla:** cliente com pagamento pendente ou recusado não pede nova corrida (é levado à corrida em aberto).
4. **Recibo e ganhos (RF22):** recibo da corrida para as partes (o motorista vê também taxa e repasse). Tela de ganhos do motorista com períodos prontos (hoje, 7 dias, 30 dias, mês) e datas livres: recebido (aprovados), aguardando pagamento e estornados, separados.
5. **Avaliação (RF23, RN10):** nota de 1 a 5 e comentário opcional, só pelo cliente, só com a corrida finalizada, uma vez por corrida (garantir também no banco).
6. **Nota média (RF24):** média com 1 casa e quantidade; aparece para o cliente ao acompanhar o motorista, no painel do motorista, na tela de ganhos e no admin.
7. **Histórico (RF25):** cliente e motorista veem só as próprias corridas, paginadas, com valor (total para o cliente, repasse para o motorista), status do pagamento e nota.
8. **Admin (RF29):** pagamentos com filtros por status, forma e data, ação de estorno; avaliações com filtro por nota.
9. **PWA (RNF01):** manifesto com ícones 192/512 e maskable, `display: standalone`; service worker servido na raiz; botão "Instalar app" quando o navegador oferecer.
10. **Offline (RNF02):** página offline amigável. Páginas: rede primeiro, sem conexão mostra a página offline. Estáticos: cache atualizado em segundo plano. API, admin e documentos nunca vão para o cache. A página offline mostra o último estado da corrida ativa guardado no aparelho (status, código, contato) e recarrega sozinha quando a conexão volta.
11. **API:** pagar, avaliar, histórico, ganhos e nota do motorista.

## Restrições
- Dinheiro em `Decimal` com `ROUND_HALF_UP` explícito; a divisão sempre fecha o total (restrição no banco).
- Nenhum gateway real, nenhum formulário com dados de cartão.
- **Privacidade (RNF07):** corrida/recibo de outra pessoa → 404; o cliente não vê o repasse do motorista; o resumo guardado no aparelho é mínimo e apagado ao terminar a corrida ou ao sair.
- Corridas finalizadas antes desta etapa recebem pagamento pendente por migration de dados.
- Sem bibliotecas novas (o PWA é feito à mão).

## Critérios de aceite
- RN08 de ponta a ponta: corrida de R$ 85,00 finalizada gera taxa R$ 17,00 e repasse R$ 68,00.
- Mudar a comissão depois do pedido não altera o pagamento da corrida.
- Corrida não finalizada ou cancelada não tem pagamento; não paga duas vezes; estorno só de aprovado.
- RN10: avaliação recusada em cada status antes de finalizada, em cancelada, por outra pessoa e na segunda vez; nota fora de 1–5 recusada.
- Ganhos: só aprovados contam como recebido; pendente e estornado separados; fora do período e de outro motorista ficam de fora.
- Manifesto válido, ícones existentes, `/sw.js` com `no-cache`, página offline pública.
- `pytest` passa; listar arquivos alterados e roteiro de teste manual (inclusive modo avião).

## Formato da resposta
Plano curto → código por arquivo → roteiro de teste manual.

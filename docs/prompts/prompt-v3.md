# Prompt v3 — Etapas 4 a 7 (Disponibilidade, solicitação, despacho e ciclo da corrida)

> Pré-requisito: prompt v2 concluído (veículos, documentos, bicicleta, repasse, aprovação e `pode_ficar_online`).

## Contexto
VoltaSegura: PWA em Django em que clientes pedem um motorista para conduzir o carro do cliente; o motorista chega com uma mini bicicleta elétrica dobrável. Estamos no **Marco 3 — Solicitação e corrida**. O código será explicado por nós na apresentação: concentre as regras de negócio em um único módulo de serviço, com comentários citando a regra (RN##/RF##).

## Tarefa desta etapa
1. **Disponibilidade (RF06, RN01):** motorista alterna online/offline. Só fica online se `pode_ficar_online`; a resposta lista os motivos quando não pode. Não pode ficar offline com corrida ativa. Se perder a elegibilidade (CNH venceu, foi bloqueado), volta a offline sozinho.
2. **Localização (RF07, RNF04):** enquanto online ou em corrida, o navegador envia lat/long a cada ~10 s (Geolocation API, com tratamento de permissão negada, GPS indisponível e tempo esgotado). Posição com mais de 2 minutos não conta para ofertas.
3. **Configuração (RN06):** registro único editável no admin com tarifa base, valor por km, % da plataforma (padrão 20), raio de oferta (km) e quantos motoristas recebem cada oferta.
4. **Solicitação (RF08–RF10, RN06, RN09):** cliente informa coleta e destino (endereço → coordenadas com geopy; aceitar também "lat, long" digitado e a posição atual do aparelho), escolhe um veículo próprio e Pix/cartão. Antes de confirmar, vê distância (geodésica) e preço = tarifa base + valor/km × distância. O servidor recalcula tudo na confirmação e guarda uma cópia das tarifas usadas. Cliente com corrida ativa não pode pedir outra.
5. **Despacho (RF11, RF12):** a corrida é oferecida aos N motoristas elegíveis (RN01, online, posição recente, sem corrida ativa) mais próximos da coleta, dentro do raio. Quem recusa não vê mais a corrida e a oferta passa ao próximo da fila.
6. **Aceite (RN02, RN03, RNF06):** dentro de uma transação, travar (`select_for_update`) o motorista e depois a corrida. Garantir também no banco, com índices únicos parciais, no máximo uma corrida ativa por cliente e por motorista.
7. **Ciclo (RF13–RF16, RN04, RN05):** solicitada → aceita → motorista a caminho → chegou → em andamento → finalizada, por um mapa de transições permitidas; qualquer outro salto ou retorno é bloqueado. "Em andamento" exige o código de 4 dígitos do cliente (comparação em tempo constante, máximo 5 tentativas). Toda mudança gera um evento com data/hora e autor (RNF09).
8. **Cancelamento (RF17):** cliente cancela de "solicitada" até "chegou"; motorista de "aceita" até "chegou", com motivo obrigatório; ninguém cancela "em andamento" (o carro já está sendo conduzido).
9. **Acompanhamento (RF13, RF18, RNF05):** telas do cliente e do motorista atualizam por polling (Fetch, ~4 s) sem recarregar a página. O cliente vê nome, telefone e bicicleta do motorista, a distância dele até a coleta (ou até o destino, durante a corrida) e o código.
10. **API REST (RNF10):** DRF com sessão + CSRF; permissões por perfil; erros de regra em JSON com mensagem em pt-BR.
11. **Simulação de posição (desenvolvimento):** com `DEBUG=True`, o painel do motorista permite fixar a posição e "andar" em direção à coleta/destino.

## Restrições
- Valores em `Decimal`, nunca `float`; coordenadas em `DecimalField` comum (sem PostGIS, sem mapas).
- Dinheiro sempre arredondado aos centavos com `ROUND_HALF_UP` explícito (o padrão do Python é o arredondamento bancário), no código e nos testes.
- **Privacidade (RNF07):** antes do aceite, o motorista não vê nome, telefone nem placa do cliente. O código nunca vai para o motorista. Corrida de outra pessoa → 404.
- Não implementar pagamento, avaliação, histórico nem PWA (Marco 4).
- Testes de geocodificação não podem depender de internet.

## Critérios de aceite
- RN01: online recusado para pendente, rejeitado, CNH vencida, sem bicicleta aprovada ou bloqueado; aceito com CNH vencendo hoje.
- RN02/RN03: dois motoristas aceitando a mesma corrida **ao mesmo tempo** (threads) → exatamente um consegue; um motorista com corrida ativa não aceita outra.
- RN04: pular etapa, voltar etapa e agir em corrida finalizada são recusados; o fluxo completo gera 6 eventos.
- RN05: código errado não inicia e conta tentativa; após 5 erros nem o certo é aceito.
- RN06: preço confere com a fórmula; RN09: segunda solicitação ativa é recusada.
- RF11: só os N mais próximos dentro do raio recebem a oferta; offline, posição antiga, inelegível e quem recusou ficam de fora.
- `pytest` passa; listar arquivos alterados e roteiro de teste manual com dois navegadores.

## Formato da resposta
Plano curto → código por arquivo → roteiro de teste manual.

# Prompt v4.2 — Ajustes do Marco 4 (cadastro, localização e busca por motorista)

> Pré-requisito: prompt v4.1 concluído e validado (tema visual e PWA pelo túnel, com `pytest` passando).

## Contexto
VoltaSegura: PWA em Django em que clientes pedem um motorista para conduzir o carro do cliente; o motorista chega com uma mini bicicleta elétrica dobrável. Ainda estamos no **Marco 4**. Nos testes com dois aparelhos, apareceram quatro problemas:
- No cadastro, as opções "cliente" e "motorista" ficavam embaixo do botão Cadastrar e não dava para clicar nelas.
- "Usar minha localização" não pegava a posição atual.
- Um endereço de coleta perto do cliente resultava numa distância muito alta.
- A busca por motorista demorava, ou a oferta nunca chegava ao motorista.

Esta etapa corrige isso **sem mudar regras de negócio**: raio de oferta, motoristas por oferta e validade da posição continuam como estão (RF11).

## Tarefa desta etapa
1. **Cadastro:** o `RadioSelect` aplica `attrs["class"]` também na `<div>` do grupo, e o `form-check-input` do Bootstrap reduz essa `<div>` a 1em. Criar um widget que coloque a classe só em cada `<input type="radio">` e fazer o mixin do Bootstrap não aplicar classe a `RadioSelect`.
2. **Localização do cliente (RF09, RNF04):** ouvir o GPS com `watchPosition` (`maximumAge: 0`) por até 12 s e devolver a leitura mais precisa, parando ao chegar a 30 m. Mostrar a precisão (±m) e avisar quando ela passar de 200 m (localização estimada pela rede, comum em computador).
3. **Busca de endereço (RF08):**
   - Procurar primeiro perto de um ponto de referência (`viewbox` com `bounded`, em raios crescentes de ~11 km e ~55 km) e só depois no Brasil inteiro.
   - A referência da coleta é a posição do aparelho, obtida sem perguntar se a permissão já foi concedida. A do destino é a própria coleta.
   - A estimativa devolve o endereço que o serviço encontrou para coleta e destino.
4. **Transparência da busca por motorista (RF10, RF11):**
   - A estimativa e o acompanhamento informam quantos motoristas elegíveis estão no raio da coleta, sem contar quem recusou.
   - A confirmação do pedido mostra o endereço encontrado e avisa quando não há motorista no raio.
   - A tela de acompanhamento atualiza essa informação a cada polling.
5. **Posição do motorista (RF07):**
   - Usar `maximumAge: 0`.
   - Enquanto o motorista estiver online, manter a tela acesa com a Wake Lock API. Com a tela apagada, o navegador congela GPS e timers, e a posição passa dos 2 minutos de validade.
   - Ao voltar para o app (`visibilitychange`), enviar a posição e buscar as ofertas na hora.

## Restrições
- Não alterar raio, motoristas por oferta, validade da posição nem a fórmula de preço.
- A posição do aparelho usada como referência não é gravada no servidor: serve só para orientar a busca do endereço.
- Sem a Wake Lock API, ou com ela negada (economia de bateria), o painel segue funcionando como antes.
- Testes sem internet: a geocodificação é simulada com `monkeypatch`.
- Aumentar `VERSAO_CACHE` porque os JavaScripts mudaram.

## Critérios de aceite
- No cadastro, as duas opções aparecem como cartões clicáveis acima do botão.
- "Usar minha localização" mostra a precisão obtida.
- "Avenida Brasil, 500" com referência em Pouso Alegre não cai no Rio de Janeiro.
- A confirmação mostra a cidade encontrada e a quantidade de motoristas no raio.
- Com o motorista fora do raio, o cliente vê "Nenhum motorista disponível perto da coleta".
- `pytest` passa, com testes para a busca por região, para o destino procurado perto da coleta e para a contagem de motoristas no raio.

## Formato da resposta
Causa de cada problema → código por arquivo → roteiro de teste manual.

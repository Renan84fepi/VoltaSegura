---
name: voltasegura-requisitos
description: Requisitos oficiais do projeto VoltaSegura (PWA Django de motoristas que conduzem o carro do cliente e chegam de bicicleta elétrica dobrável). Use ao implementar, revisar ou testar qualquer funcionalidade, regra de negócio, modelo, API, tela ou marco do projeto, ou ao escrever prompts em docs/prompts/.
---

# VoltaSegura — Requisitos do projeto

PWA em Django que conecta clientes a motoristas que conduzem **o próprio carro do cliente** até o destino. O motorista chega numa **mini bicicleta elétrica dobrável**, que vai no porta-malas durante a corrida e sai no destino. O cliente solicita, acompanha a chegada, confirma a identidade do motorista com um código, paga pelo app e avalia. A plataforma fica com uma comissão sobre cada corrida.

## Escopo

**MVP (obrigatório):** cadastro/login/perfis; veículos do cliente e bicicleta do motorista; aprovação de motoristas pelo admin; motorista online/offline; solicitação com estimativa de preço; aceite → chegada → código → início → fim; localização por lat/long e cálculo de distância; pagamento simulado com divisão plataforma/motorista; avaliação do motorista; área administrativa; PWA instalável.

**Opcional (diferencial):** tempo real com WebSocket (Channels); agendamento; avaliação bilateral; compartilhar andamento por link; botão de emergência com localização; relatórios de ganhos/faturamento; cupons.

**Fora do escopo — não implementar:** mapas, rotas e navegação; PostGIS e consultas geográficas avançadas; gateway de pagamento real; validação real de documentos junto a órgãos oficiais.

## Perfis (todos com login)

| Perfil | Papel |
|---|---|
| Cliente | Cadastra veículos, solicita corridas, acompanha o motorista, paga e avalia |
| Motorista | Envia documentos, cadastra a bicicleta, fica online, aceita e conduz corridas, consulta ganhos |
| Administrador | Aprova motoristas e bicicletas, configura tarifas e comissão, acompanha corridas e pagamentos, bloqueia usuários |

## Requisitos funcionais

**Contas e cadastros**
- RF01 Cadastro, login, logout e recuperação de senha.
- RF02 Cliente cadastra, edita e remove veículos.
- RF03 Motorista envia documento de identidade e dados da CNH, incluindo a validade.
- RF04 Motorista cadastra a bicicleta elétrica dobrável, com foto.
- RF05 Motorista informa os dados para receber os repasses.

**Disponibilidade**
- RF06 Motorista alterna entre online e offline.
- RF07 Enquanto online, o sistema registra a localização periodicamente.

**Solicitação**
- RF08 Cliente informa coleta e destino, escolhe o veículo e a forma de pagamento.
- RF09 A coleta pode usar a localização atual do aparelho.
- RF10 Exibir a distância e a estimativa de preço antes da confirmação.
- RF11 Oferecer a solicitação aos motoristas elegíveis mais próximos.

**Corrida**
- RF12 Motorista vê a solicitação e aceita ou recusa.
- RF13 Cliente vê os dados do motorista e a distância dele até a coleta.
- RF14 Motorista informa que chegou.
- RF15 Cliente recebe um código de confirmação; o motorista só inicia a corrida depois de informá-lo.
- RF16 Motorista finaliza no destino.
- RF17 Cliente e motorista podem cancelar (as regras são definidas pela dupla).
- RF18 As duas partes acompanham o status sem recarregar a página.

**Pagamento simulado**
- RF19 Ao finalizar, gerar o pagamento simulado (Pix ou cartão).
- RF20 Registrar valor total, taxa da plataforma, repasse ao motorista e status.
- RF21 Simular pagamento aprovado, recusado e estornado.
- RF22 Cliente vê o recibo; motorista vê os ganhos por período.

**Avaliação e histórico**
- RF23 Cliente avalia o motorista com nota e comentário.
- RF24 A nota média aparece no perfil do motorista.
- RF25 Cliente e motorista consultam o histórico de corridas.

**Administração**
- RF26 Aprovar ou rejeitar motoristas e bicicletas.
- RF27 Configurar tarifas e o percentual da plataforma.
- RF28 Bloquear usuários.
- RF29 Consultar corridas e pagamentos com filtros.

## Requisitos não funcionais

- RNF01 PWA instalável: manifesto, ícones e service worker.
- RNF02 Offline: página amigável, sem perder o estado da corrida em andamento.
- RNF03 Mobile first: botões grandes e poucos passos.
- RNF04 Geolocation API do navegador, com pedido de permissão e tratamento de recusa ou falha do GPS.
- RNF05 Polling a cada poucos segundos para o status e a posição do motorista.
- RNF06 Uma solicitação só pode ser aceita por um motorista, mesmo com aceites simultâneos (usar transação + `select_for_update` ou update condicional).
- RNF07 Placa, telefone e documentos visíveis só para as partes da corrida e para o admin.
- RNF08 Senhas com hash, CSRF, permissão por perfil e nenhum segredo no repositório.
- RNF09 Valores financeiros gravados em campos separados; cada mudança de status registrada com data e hora.
- RNF10 O frontend consome uma API REST documentada.
- RNF11 Testes automatizados das regras de negócio críticas.
- RNF12 Variáveis sensíveis no `.env`, com `.env.example` versionado.
- RNF13 Qualquer pessoa sobe o projeto seguindo só o README.
- RNF14 Interface em pt-BR: datas, km e R$ no padrão brasileiro.

## Regras de negócio (verificadas na avaliação, inclusive casos-limite)

- **RN01** Motorista só fica online se estiver aprovado, com CNH válida (não vencida) e bicicleta aprovada.
- **RN02** Motorista não pode ter duas corridas ativas ao mesmo tempo.
- **RN03** Uma solicitação aceita por um motorista não pode ser aceita por outro.
- **RN04** Sequência obrigatória: `solicitada → aceita → motorista a caminho → chegou → em andamento → finalizada`. Bloquear saltos e retrocessos (o cancelamento é a única saída lateral, conforme RF17).
- **RN05** Só passa para "em andamento" com o código de confirmação correto.
- **RN06** Preço estimado = tarifa base + valor por km × distância (coleta → destino), com valores configuráveis.
- **RN07** Comissão padrão de 20%, configurável pelo admin.
- **RN08** Caso de referência: R$ 85,00 → plataforma R$ 17,00 → motorista R$ 68,00. Usar `Decimal`, nunca `float`.
- **RN09** Cliente não pode solicitar nova corrida enquanto tiver uma ativa.
- **RN10** Avaliação só depois da corrida finalizada, uma vez por corrida.

## Stack

**Obrigatório:** Python 3, Django, djangorestframework, PostgreSQL (nunca SQLite na entrega), psycopg v3, Pillow, django-environ ou python-decouple, Geolocation API, HTML + CSS + Bootstrap 5 + JS (Fetch API), manifest.json + Service Worker + Cache API, Git + GitHub.

**Recomendado:** geopy (distância/geocodificação), drf-spectacular (Swagger), django-filter, pytest-django, whitenoise, gunicorn, Docker + Compose.

**Só se fizer o tempo real:** channels + daphne, channels-redis + Redis.

Usar as versões estáveis mais recentes, fixadas no `requirements.txt`; justificar qualquer pacote extra no README.

**Infra:**
- Coordenadas em campos numéricos comuns (sem PostGIS).
- Banco, usuário e senha próprios do projeto, definidos no `.env`.
- Versionar as migrations e trazer um comando ou fixture que crie clientes e motoristas de exemplo em posições diferentes.
- Geolocalização e Service Worker exigem HTTPS ou localhost; usar túnel HTTPS para testar no celular.
- Prever uma forma de simular a posição do motorista em desenvolvimento.

## Uso de IA

- Prompts escritos pela dupla (não colar este documento), com contexto, escopo, stack, restrições e critérios de aceite.
- Trabalho dividido em etapas.
- Cada versão em `docs/prompts/`, com uma nota curta do que mudou e por quê.
- Quando a IA errar uma regra de negócio, registrar o erro e como o prompt foi corrigido.
- A dupla precisa saber explicar qualquer trecho de código.

## Marcos

1. **Planejamento:** repo, README inicial, divisão de tarefas, prompt v1, plano de etapas, esboço das telas.
2. **Base e cadastros:** Django + PostgreSQL + `.env`; RF01–RF05; RF26.
3. **Solicitação e corrida:** RF06–RF18; testes de RN01–RN05 (elegibilidade, aceite simultâneo, fluxo de status).
4. **Pagamento, avaliação e PWA:** RF19–RF25; RNF01–RNF02.
5. **Entrega final:** sistema completo + opcionais; README com instalação, dados de exemplo e usuários de teste; documentação da API; histórico de prompts; demo ao vivo com dois aparelhos (cliente solicita → motorista aceita → pagamento → avaliação).

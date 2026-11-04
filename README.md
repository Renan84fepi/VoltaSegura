# VoltaSegura

Projeto da disciplina de Backend, ministrada pelo professor Marcio.

PWA desenvolvido em Django que conecta clientes a motoristas que conduzem **o próprio carro do cliente** até o destino. O motorista chega ao local com uma **minibicicleta elétrica dobrável**, transportada no porta-malas durante a corrida e utilizada para deixar o local após a conclusão do serviço.

> **Status:** Marcos 1 a 4 concluídos. Próximo: Marco 5 — Entrega final.

## Equipe

| Integrante | Foco principal |
|---|---|
| Pedro | Backend, regras de negócio e API |
| Renan | Frontend, PWA e telas |

A divisão detalhada das responsabilidades está em [docs/divisao-tarefas.md](docs/divisao-tarefas.md).

## Escopo

### MVP (obrigatório)

- Cadastro, login e perfis de usuários.
- Cadastro de veículos dos clientes e bicicletas dos motoristas.
- Aprovação de motoristas.
- Controle de disponibilidade online/offline.
- Solicitação de corridas com estimativa de valor.
- Fluxo de corrida: aceite → chegada → código de confirmação → início → fim.
- Localização por latitude/longitude e cálculo de distância.
- Pagamento simulado com divisão de valores.
- Avaliações.
- Área administrativa.
- PWA instalável.

### Funcionalidades opcionais

Serão avaliadas após o Marco 2:

- Comunicação em tempo real via WebSocket.
- Agendamento de corridas.
- Avaliação bilateral.
- Link de acompanhamento.
- Botão de emergência.
- Relatórios.
- Cupons.

### Fora do escopo

- Mapas, rotas e navegação.
- PostGIS.
- Integração com gateway de pagamento real.
- Validação oficial de documentos.

## Progresso por marco

| Marco | Situação | Entregas |
|---|---|---|
| 1 — Planejamento | Concluído | README, divisão de tarefas, prompt v1, plano de etapas e esboço das telas |
| 2 — Base e cadastros | Concluído | Django + PostgreSQL + `.env`; contas (RF01); veículos (RF02); documentos, bicicleta e repasse do motorista (RF03–RF05); aprovação pelo administrador (RF26) |
| 3 — Solicitação e corrida | Concluído | Online/offline e localização (RF06–RF07); solicitação com estimativa e oferta aos mais próximos (RF08–RF11); ciclo da corrida com código (RF12–RF18); testes de RN01–RN05 |
| 4 — Pagamento, avaliação e PWA | Concluído | Pagamento simulado com divisão de valores (RF19–RF21); recibo e ganhos por período (RF22); avaliação e nota média (RF23–RF24, RN10); histórico (RF25); PWA instalável e página offline (RNF01–RNF02) |
| 5 — Entrega final | Pendente | Conforme o enunciado da disciplina |

### Já implementado no Marco 2

- Login por e-mail, perfis (cliente, motorista, administrador), cadastro, logout e recuperação de senha.
- Bloqueio de usuários (usuário bloqueado não entra).
- CRUD de veículos do cliente, com validação de placa (ABC1234 e ABC1D23).
- Envio de documento de identidade, CNH (com validade), bicicleta com foto e dados Pix para repasse.
- Aprovação ou rejeição de motoristas e bicicletas no Django Admin, com motivo e registro de quem avaliou.
- Documentos e fotos protegidos: sem URL pública, visíveis só ao dono e ao administrador.
- Testes automatizados com pytest-django para as regras acima.

### Já implementado no Marco 3

- Motorista fica online/offline só se atender à RN01; o painel mostra o motivo quando não pode.
- Localização do motorista enviada a cada 10 s pela Geolocation API, com tratamento de permissão negada e GPS indisponível.
- Solicitação com coleta (endereço ou posição atual), destino, veículo e Pix/cartão; distância e preço antes de confirmar (RN06), recalculados no servidor.
- Oferta aos motoristas elegíveis mais próximos, dentro de um raio configurável; quem recusa sai da fila.
- Aceite à prova de concorrência (`select_for_update` + índices únicos parciais no PostgreSQL).
- Sequência de status obrigatória (RN04), código de confirmação com limite de 5 tentativas (RN05) e registro de cada mudança com data, hora e autor (RNF09).
- Acompanhamento sem recarregar a página (polling a cada 4 s) para cliente e motorista.
- Tarifas, comissão, raio e motoristas por oferta editáveis no admin; corridas consultáveis com filtros.
- Simulador de posição do motorista (somente com `DEBUG=True`).

### Já implementado no Marco 4

- Ao finalizar, o pagamento simulado é gerado na mesma transação: total, % e taxa da plataforma e repasse ao motorista em campos separados, com a comissão guardada no pedido (RN07/RN08: R$ 85,00 → R$ 17,00 + R$ 68,00).
- Cliente paga pela tela da corrida (Pix ou cartão, simulados); o pagamento pode ser aprovado ou recusado (e tentado de novo) e o administrador estorna pelo admin. Cada mudança fica registrada com data, hora e autor.
- Recibo da corrida para as partes; tela de ganhos do motorista por período (hoje, 7 dias, 30 dias, mês ou datas livres).
- Avaliação de 1 a 5 com comentário, só depois de finalizada e uma vez por corrida (RN10); nota média no acompanhamento do cliente, no painel e nos ganhos do motorista e no admin.
- Histórico paginado para cliente e motorista.
- PWA: manifesto, ícones, service worker e botão "Instalar app"; sem conexão, página offline com o último estado da corrida ativa (status, código e contato), que recarrega sozinha quando a internet volta.

### Pagamento simulado (RF21, regras da dupla)

| De | Para | Quem |
|---|---|---|
| — | Aguardando pagamento | Sistema, ao finalizar a corrida |
| Aguardando / recusado | Aprovado ou recusado | Cliente (o "gateway" simulado decide; em `DEBUG` há um botão para forçar a recusa) |
| Aprovado | Estornado | Administrador (ação no admin) |

Cliente com pagamento aguardando ou recusado não pede nova corrida: é levado de volta à corrida em aberto. Só pagamentos aprovados contam como ganho do motorista.

### Regras de cancelamento (RF17, definidas pela dupla)

| Status | Cliente | Motorista |
|---|---|---|
| Solicitada | Pode | — (usa "Recusar") |
| Aceita, a caminho, chegou | Pode | Pode, informando o motivo |
| Em andamento | Não | Não (o carro já está sendo conduzido; só finaliza no destino) |
| Finalizada / cancelada | Não | Não |

### API REST (sessão + CSRF)

| Método | Rota | Quem | Uso |
|---|---|---|---|
| GET/POST | `/api/motorista/disponibilidade/` | Motorista | Situação; `{"online": true}` (RN01) |
| POST | `/api/motorista/localizacao/` | Motorista | `{"latitude", "longitude"}` (RF07) |
| GET | `/api/motorista/ofertas/` | Motorista | Solicitações oferecidas (RF11) |
| POST | `/api/corridas/estimativa/` | Cliente | Distância e preço (RF10) |
| POST | `/api/corridas/` | Cliente | Solicita a corrida (RF08) |
| GET | `/api/corridas/ativa/` e `/api/corridas/<id>/` | As partes | Acompanhamento por polling (RF18) |
| POST | `/api/corridas/<id>/aceitar/`, `recusar/`, `a-caminho/`, `chegou/`, `iniciar/` (`{"codigo"}`), `finalizar/` | Motorista | Ciclo da corrida (RN02–RN05) |
| POST | `/api/corridas/<id>/cancelar/` | As partes | `{"motivo"}` (RF17) |
| POST | `/api/corridas/<id>/pagar/` | Cliente | `{"resultado": "aprovado"\|"recusado"}`, padrão aprovado (RF21) |
| POST | `/api/corridas/<id>/avaliar/` | Cliente | `{"nota": 1-5, "comentario"}` (RF23, RN10) |
| GET | `/api/corridas/historico/?pagina=N` | As partes | Histórico, 20 por página (RF25) |
| GET | `/api/motorista/ganhos/?periodo=hoje\|7dias\|30dias\|mes` ou `?de=&ate=` | Motorista | Ganhos por período (RF22) |
| GET | `/api/motorista/nota/` | Motorista | Nota média e quantidade (RF24) |

Erros de regra voltam como `{"detail": "mensagem"}` com 400, 403, 404 ou 409. A documentação Swagger (drf-spectacular) fica para o Marco 5.

## Stack tecnológica

| Item | Versão / observação |
|---|---|
| Python | 3 (imagem Docker `python:3.13-slim`) |
| Django | 6.1.2 |
| Django REST Framework | 3.18.3 |
| PostgreSQL | 18 (imagem Docker `postgres:18`) |
| psycopg | 3.3.6 (`psycopg[binary]`) |
| Pillow | 13.0.0 |
| django-environ | 0.14.0 |
| Bootstrap | 5.3.8 (CDN) e JavaScript (Fetch API) |
| Service Worker e Cache API | sem biblioteca: `/sw.js`, `/manifest.webmanifest` e `/offline/` (app `pwa`) |
| Git e GitHub | versionamento |

As versões fixadas estão em [`requirements.txt`](requirements.txt).

### Pacotes extras (justificativa)

| Pacote | Versão | Motivo |
|---|---|---|
| whitenoise | 6.12.0 | Servir arquivos estáticos sem servidor adicional |
| gunicorn | 26.2.0 | Servidor de aplicação para execução fora do modo de desenvolvimento |
| pytest | 9.1.1 | Execução dos testes automatizados |
| pytest-django | 4.14.0 | Integração do pytest com o Django (banco de testes, fixtures) |
| geopy | 2.5.0 | Distância geodésica entre coordenadas e conversão de endereço em coordenadas (Nominatim/OpenStreetMap) |

### Ainda previstos para marcos seguintes
- drf-spectacular
- django-filter

Dependências adicionais deverão ser justificadas nesta documentação.

## Documentação do projeto

- [Como executar](docs/como-rodar.md)
- [Divisão de tarefas](docs/divisao-tarefas.md)
- [Plano de etapas](docs/plano-de-etapas.md)
- [Esboço das telas](docs/telas.md)
- [Atualizações do Marco 2](docs/marco-2-atualizacoes.md)
- [Prompts do agente de IA](docs/prompts/) (v1: [prompt-v1](docs/prompts/prompt-v1.md); v2: [prompt-v2](docs/prompts/prompt-v2.md); v3: [prompt-v3](docs/prompts/prompt-v3.md); v4: [prompt-v4](docs/prompts/prompt-v4.md))

Os prompts são versionados, com registros das alterações e justificativas em `docs/prompts/CHANGELOG.md`.

## Como executar

Resumo com Docker Compose:

```bash
cp .env.example .env          # edite SECRET_KEY e POSTGRES_PASSWORD
docker compose up --build     # http://localhost:8000
docker compose exec web python manage.py criar_dados_exemplo
docker compose exec web pytest
```

O passo a passo completo (inclusive sem Docker, usuários de exemplo e teste no celular com túnel HTTPS) está em [docs/como-rodar.md](docs/como-rodar.md).

## Uso de inteligência artificial

O projeto utiliza agentes de inteligência artificial a partir de prompts elaborados pela equipe e organizados por etapas.

Todo código gerado é revisado e testado pelos integrantes. Erros do agente relacionados às regras de negócio e outros problemas encontrados são documentados em `docs/prompts/CHANGELOG.md`.
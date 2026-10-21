# VoltaSegura

Projeto da disciplina de Backend, ministrada pelo professor Marcio.

PWA desenvolvido em Django que conecta clientes a motoristas que conduzem **o próprio carro do cliente** até o destino. O motorista chega ao local com uma **minibicicleta elétrica dobrável**, transportada no porta-malas durante a corrida e utilizada para deixar o local após a conclusão do serviço.

> **Status:** Marco 1 — Planejamento (em andamento).

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

## Stack tecnológica

- Python 3
- Django
- Django REST Framework
- PostgreSQL com psycopg 3
- Pillow
- django-environ
- Bootstrap 5 e JavaScript (Fetch API)
- Service Worker e Cache API
- Git e GitHub

### Tecnologias e ferramentas previstas

- geopy
- drf-spectacular
- django-filter
- pytest-django
- whitenoise
- gunicorn
- Docker Compose

As versões das dependências serão definidas e registradas no `requirements.txt` durante o Marco 2. Dependências adicionais deverão ser justificadas nesta documentação.

## Documentação do planejamento

- [Divisão de tarefas](docs/divisao-tarefas.md)
- [Plano de etapas](docs/plano-de-etapas.md)
- [Esboço das telas](docs/telas.md)
- [Prompts do agente de IA](docs/prompts/)

Os prompts serão versionados, com registros das alterações e justificativas em `docs/prompts/CHANGELOG.md`.

## Como executar

As instruções de instalação e execução serão adicionadas a partir do Marco 2, incluindo Docker Compose e o arquivo `.env.example`.

## Uso de inteligência artificial

O projeto utiliza agentes de inteligência artificial a partir de prompts elaborados pela equipe e organizados por etapas.

Todo código gerado será revisado e testado pelos integrantes. Erros do agente relacionados às regras de negócio serão documentados em `docs/prompts/CHANGELOG.md`.

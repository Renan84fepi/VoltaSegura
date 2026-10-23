# VoltaSegura

Projeto da disciplina de Backend, ministrada pelo professor Marcio.

PWA desenvolvido em Django que conecta clientes a motoristas que conduzem **o próprio carro do cliente** até o destino. O motorista chega ao local com uma **minibicicleta elétrica dobrável**, transportada no porta-malas durante a corrida e utilizada para deixar o local após a conclusão do serviço.

> **Status:** Marco 2 — Base e cadastros (em andamento). Marco 1 — Planejamento concluído.

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
| 2 — Base e cadastros | Em andamento | Django + PostgreSQL + `.env`; contas (RF01); veículos (RF02); documentos, bicicleta e repasse do motorista (RF03–RF05); aprovação pelo administrador (RF26) |
| 3 a 5 | Pendentes | Conforme o enunciado da disciplina |

### Já implementado no Marco 2

- Login por e-mail, perfis (cliente, motorista, administrador), cadastro, logout e recuperação de senha.
- Bloqueio de usuários (usuário bloqueado não entra).
- CRUD de veículos do cliente, com validação de placa (ABC1234 e ABC1D23).
- Envio de documento de identidade, CNH (com validade), bicicleta com foto e dados Pix para repasse.
- Aprovação ou rejeição de motoristas e bicicletas no Django Admin, com motivo e registro de quem avaliou.
- Documentos e fotos protegidos: sem URL pública, visíveis só ao dono e ao administrador.
- Testes automatizados com pytest-django para as regras acima.

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
| Service Worker e Cache API | a partir do marco do PWA |
| Git e GitHub | versionamento |

As versões fixadas estão em [`requirements.txt`](requirements.txt).

### Pacotes extras (justificativa)

| Pacote | Versão | Motivo |
|---|---|---|
| whitenoise | 6.12.0 | Servir arquivos estáticos sem servidor adicional |
| gunicorn | 26.2.0 | Servidor de aplicação para execução fora do modo de desenvolvimento |
| pytest | 9.1.1 | Execução dos testes automatizados |
| pytest-django | 4.14.0 | Integração do pytest com o Django (banco de testes, fixtures) |

### Ainda previstos para marcos seguintes

- geopy
- drf-spectacular
- django-filter

Dependências adicionais deverão ser justificadas nesta documentação.

## Documentação do projeto

- [Como executar](docs/como-rodar.md)
- [Divisão de tarefas](docs/divisao-tarefas.md)
- [Plano de etapas](docs/plano-de-etapas.md)
- [Esboço das telas](docs/telas.md)
- [Atualizações do Marco 2](docs/marco-2-atualizacoes.md)
- [Prompts do agente de IA](docs/prompts/) (v1: [prompt-v1](docs/prompts/prompt-v1.md); v2: [prompt-v2](docs/prompts/prompt-v2.md))

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
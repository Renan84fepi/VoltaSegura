# VoltaSegura

PWA em Django que conecta clientes a motoristas que conduzem **o próprio carro do cliente** até o destino. O motorista chega ao local com uma **mini bicicleta elétrica dobrável**, que viaja no porta-malas durante a corrida e é retirada no destino.

> Status: **Marco 1 — Planejamento** (em andamento)

## Equipe
| Integrante | Foco principal |
|Pedro|Renan|
| Pedro | Backend, regras de negócio, API |
| Renan | Frontend, PWA, telas |

Divisão detalhada em [docs/divisao-tarefas.md](docs/divisao-tarefas.md).

## Escopo
**MVP (obrigatório):** cadastro/login/perfis; veículos do cliente e bicicleta do motorista; aprovação de motoristas; online/offline; solicitação com estimativa; aceite → chegada → código → início → fim; localização por lat/long e distância; pagamento simulado com divisão; avaliação; área administrativa; PWA instalável.

**Opcionais (diferencial) que pretendemos tentar:** _a definir após o Marco 2_ (WebSocket, agendamento, avaliação bilateral, link de acompanhamento, botão de emergência, relatórios, cupons).

**Fora do escopo:** mapas/rotas/navegação, PostGIS, gateway real, validação oficial de documentos.

## Stack
Python 3 · Django · Django REST Framework · PostgreSQL (psycopg 3) · Pillow · django-environ · Bootstrap 5 + JavaScript (Fetch API) · Service Worker + Cache API · Git/GitHub.
Recomendados previstos: geopy, drf-spectacular, django-filter, pytest-django, whitenoise, gunicorn, Docker Compose.
Versões estáveis mais recentes, fixadas no `requirements.txt` (a ser criado no Marco 2).
Pacotes extras serão justificados nesta seção.

## Documentação do planejamento
- [Divisão de tarefas](docs/divisao-tarefas.md)
- [Plano de etapas](docs/plano-de-etapas.md)
- [Esboço das telas](docs/telas.md)
- [Prompts do agente de IA](docs/prompts/) — versionados, com nota do que mudou e por quê

## Como rodar
_Será preenchido a partir do Marco 2 (Docker Compose + `.env.example`)._

## Uso de IA
Usamos agente de IA com prompts escritos por nós, em etapas. Todo código gerado é revisado e testado pela dupla. Erros do agente em regras de negócio ficam registrados em `docs/prompts/CHANGELOG.md`.

# Prompt v1 — Etapa 0 e 1 (Setup + Contas e perfis)

## Contexto
Estamos desenvolvendo, em dupla, o **VoltaSegura**: um PWA em Django em que clientes pedem um motorista para conduzir o próprio carro até o destino. O motorista chega ao local com uma mini bicicleta elétrica dobrável, que viaja no porta-malas. Este é um trabalho acadêmico; o código será revisado e explicado por nós na apresentação, então prefira código simples, legível e comentado nos pontos não óbvios.

## Papel
Atue como desenvolvedor Django sênior, trabalhando **somente nesta etapa**. Não implemente funcionalidades das etapas seguintes.

## Stack (obrigatória)
Python 3, Django, djangorestframework, PostgreSQL com psycopg v3, Pillow, django-environ, HTML/CSS/Bootstrap 5/JavaScript (Fetch API). Versões estáveis mais recentes, fixadas em `requirements.txt`. **Proibido** SQLite, PostGIS, mapas e gateway de pagamento real.

## Tarefa desta etapa
1. Estrutura do projeto Django com apps separados por domínio (começar com `contas`).
2. `docker-compose.yml` com Django e PostgreSQL; `.env` lido via django-environ; `.env.example` versionado; `.env` no `.gitignore`.
3. Modelo de usuário customizado com perfil: `cliente`, `motorista`, `administrador`.
4. Cadastro (escolhendo cliente ou motorista), login, logout e recuperação de senha por e-mail (backend de console em desenvolvimento).
5. Usuário bloqueado não consegue entrar.
6. Templates mobile first em Bootstrap 5, em português do Brasil, botões grandes.
7. README com passo a passo para subir o projeto do zero.

## Restrições
- Senhas com hash, CSRF ativo, nenhum segredo no código.
- Interface e mensagens em pt-BR; fuso `America/Sao_Paulo`.
- Não criar pacotes extras sem justificar.
- Não alterar nada fora do escopo pedido; se algo estiver ambíguo, pergunte antes de supor.

## Critérios de aceite
- `docker compose up` sobe app e banco; migrations aplicam sem erro.
- É possível cadastrar cliente e motorista, entrar, sair e recuperar senha.
- Perfil do usuário é identificável no código (ex.: `user.perfil`).
- Usuário bloqueado é impedido de logar, com mensagem clara.
- Testes automatizados (pytest-django) para cadastro, login e bloqueio passam.
- Ao final, liste os arquivos criados/alterados e como testar manualmente.

## Formato da resposta
Primeiro um plano curto; depois o código por arquivo; por fim o roteiro de teste.

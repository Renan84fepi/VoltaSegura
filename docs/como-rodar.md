# Como rodar o VoltaSegura

## Opção A — Docker Compose (recomendada)
```bash
cp .env.example .env          # edite SECRET_KEY e POSTGRES_PASSWORD
docker compose up --build     # sobe PostgreSQL e Django em http://localhost:8000
```
Em outro terminal:
```bash
docker compose exec web python manage.py criar_dados_exemplo   # usuários de exemplo
docker compose exec web python manage.py createsuperuser       # (opcional) admin próprio
docker compose exec web pytest                                 # testes automatizados
```

## Opção B — Sem Docker
Pré-requisitos: Python 3, PostgreSQL rodando localmente.
```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # POSTGRES_HOST=localhost

# crie o banco e o usuário (o usuário precisa de CREATEDB para os testes)
psql -U postgres -c "CREATE USER voltasegura WITH PASSWORD 'sua-senha' CREATEDB;"
psql -U postgres -c "CREATE DATABASE voltasegura OWNER voltasegura;"

python manage.py migrate
python manage.py criar_dados_exemplo
python manage.py runserver
pytest
```

## Usuários de exemplo (senha: `voltasegura123`)
| E-mail | Perfil / situação |
|---|---|
| admin@exemplo.com | Administrador (acessa `/admin/`) |
| ana@exemplo.com, bruno@exemplo.com | Clientes, com um veículo cada |
| carlos@exemplo.com | Motorista totalmente aprovado (pode ficar online — RN01) |
| diana@exemplo.com | Motorista com documentos e bicicleta pendentes |
| eduardo@exemplo.com | Motorista com documentos rejeitados |
| fabio@exemplo.com | Motorista aprovado, mas com CNH vencida |

O comando recusa rodar com `DEBUG=False` (use `--forcar` se for de propósito).

## Testar no celular (HTTPS)
Use um túnel HTTPS (ex.: ngrok) e informe o endereço no `.env`:
```
ALLOWED_HOSTS=localhost,127.0.0.1,abc123.ngrok-free.app
CSRF_TRUSTED_ORIGINS=https://abc123.ngrok-free.app
```

## Pontos de atenção
- `.env` e a pasta `media/` (uploads) **não** vão para o Git.
- Documentos e fotos **não** têm URL pública: só são entregues pela view `/motorista/arquivo/...`, para o dono e o administrador (RNF07).
- Em desenvolvimento, e-mails (recuperação de senha) aparecem no terminal.

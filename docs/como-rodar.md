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
| gabriela@exemplo.com | Motorista aprovado, mais longe do Centro (para testar a oferta ao mais próximo) |

O comando recusa rodar com `DEBUG=False` (use `--forcar` se for de propósito).

## Demonstrar uma corrida (Marco 3)
Use dois navegadores (ou uma janela anônima), um para cada perfil.

1. **Motorista** `carlos@exemplo.com` → painel → **Ficar online**. Sem GPS, use o cartão "Simular posição" (só aparece com `DEBUG=True`) e clique em **Enviar posição**.
2. **Cliente** `ana@exemplo.com` → coleta `-22.2306, -45.9356` e destino `-22.2650, -45.9000` (ou endereços reais, com internet) → **Ver estimativa** → **Confirmar pedido**.
3. O motorista vê a oferta em até 4 s → **Aceitar** → **Estou a caminho** → (opcional: **Andar até o alvo** no simulador; a distância muda na tela do cliente) → **Cheguei ao local**.
4. O cliente vê o código de 4 dígitos; o motorista digita → **Iniciar corrida** → **Finalizar no destino**.

Tarifas, comissão, raio de oferta e motoristas por oferta ficam no admin, em **Corridas → Configuração de tarifas**.

Sem internet, defina `GEOCODIFICACAO_ATIVA=False` no `.env`: a coleta pode usar a posição do aparelho e os endereços podem ser digitados como `latitude, longitude`.

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

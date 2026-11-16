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

### Localização e endereços
- **Usar minha localização** ouve o GPS por até 12 s e mostra a precisão. Acima de ±200 m aparece um aviso: a posição foi estimada pela rede (Wi‑Fi/IP), o que é comum em computador sem GPS e pode errar por quilômetros, inclusive de cidade.
- O endereço digitado é procurado primeiro perto do aparelho (se a localização já foi liberada) e o destino perto da coleta; só depois no Brasil inteiro. Mesmo assim, uma rua que não existe no OpenStreetMap com aquele nome pode ser encontrada em outra cidade. Por isso a confirmação mostra **onde** a coleta e o destino foram encontrados: inclua bairro e cidade se estiver errado.
- A confirmação e o acompanhamento mostram quantos motoristas estão disponíveis no raio da coleta (padrão 10 km). Se não houver nenhum, confira o endereço de coleta e a posição do motorista.
- **Posição do motorista:** vem do GPS do aparelho do painel. Num computador, o navegador estima pela rede, e a posição costuma ficar fixa e em outro bairro ou cidade. Para testar a oferta, abra o painel no celular (HTTPS) ou use o simulador com as coordenadas certas.
- O painel do motorista mantém a tela acesa enquanto ele está online. Com a tela apagada, o navegador congela o GPS; sem posição nos últimos 2 minutos, o motorista não recebe ofertas. Ao voltar ao app, a posição é reenviada na hora.

Sem internet, defina `GEOCODIFICACAO_ATIVA=False` no `.env`: a coleta pode usar a posição do aparelho e os endereços podem ser digitados como `latitude, longitude`.

## Pagamento, avaliação e ganhos (Marco 4)
5. Com a corrida finalizada, o cliente vê **Pagar com Pix/Cartão** (simulado). Com `DEBUG=True` há também **Simular pagamento recusado**; depois de recusado, é possível pagar de novo.
6. O cliente dá a nota (1 a 5) e um comentário. O recibo fica em **Histórico → Recibo**.
7. O motorista vê os ganhos em **Ganhos** (hoje, 7 dias, 30 dias, mês ou datas) e a nota média no painel.
8. Estorno: admin → **Corridas → Pagamentos** → abra um pagamento **aprovado** → botão **Estornar (simulado)** no canto superior direito → informe o motivo e confirme. Também dá para estornar vários pela lista (marque as caixas → ação **Estornar**).

Enquanto o pagamento estiver aguardando ou recusado, o cliente não consegue pedir outra corrida.
O comando `criar_dados_exemplo` cria três corridas antigas de Carlos (pagas e avaliadas, uma estornada) para a tela de ganhos já ter dados.

## Instalar como app e testar offline (PWA)
- O botão **Instalar app** aparece na barra sempre que o site não está aberto como app instalado. Em `localhost` ou HTTPS, no Chrome/Edge, ele abre a instalação. Nos outros navegadores, ou quando o Chrome ainda não ofereceu a instalação, ele mostra como instalar (iPhone: Safari → Compartilhar → **Adicionar à Tela de Início**; o Firefox no computador não instala apps).
- Aberto por HTTP comum (ex.: IP da rede), o botão explica como criar um **atalho** na tela inicial. O atalho não é o app completo: GPS e modo offline continuam exigindo HTTPS.
- Para ver a página offline: abra uma corrida em andamento, depois DevTools → **Network → Offline** (ou modo avião no celular) e navegue/recarregue. Aparece o último estado da corrida (status, código e contato) e a página volta sozinha quando a conexão retorna.
- Ao mudar arquivos estáticos guardados pelo service worker, aumente `VERSAO_CACHE` em `pwa/views.py`. Em desenvolvimento, DevTools → **Application → Service workers → Update on reload** evita cache antigo.

## Testar no celular (HTTPS)
Abrir pelo IP da rede (ex.: `http://10.0.5.46:8000`) **não basta**: o navegador só instala o app, registra o service worker e libera o GPS em HTTPS ou `localhost`. Pelo IP o site abre, mas sem PWA e sem localização.

Use um túnel HTTPS. Com o [ngrok](https://ngrok.com/download) (conta gratuita):
```bash
ngrok http 8000          # mostra um endereço como https://abc123.ngrok-free.app
```
Informe o endereço no `.env`. Em `ALLOWED_HOSTS` vai **só o nome** (sem `https://`); em `CSRF_TRUSTED_ORIGINS`, **com** `https://`:
```
ALLOWED_HOSTS=localhost,127.0.0.1,abc123.ngrok-free.app
CSRF_TRUSTED_ORIGINS=https://abc123.ngrok-free.app
```
Depois recrie o container com `docker compose up -d` (o `docker compose restart` **não** relê o `.env`). O endereço do ngrok gratuito pode mudar a cada execução: atualize as duas linhas quando mudar.
O manifesto é carregado com `crossorigin="use-credentials"`. Sem isso, o navegador o buscaria sem o cookie do ngrok e receberia a página de aviso do ngrok no lugar dele, e o app não instalaria.
Alternativa sem conta: `cloudflared tunnel --url http://localhost:8000` (endereço `*.trycloudflare.com`, configurado do mesmo jeito).

Atalho só para testes no Android, sem túnel: no Chrome do celular, abra `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, informe `http://10.0.5.46:8000` (o IP do seu computador), ative e reinicie o Chrome.

## Pontos de atenção
- `.env` e a pasta `media/` (uploads) **não** vão para o Git.
- Documentos e fotos **não** têm URL pública: só são entregues pela view `/motorista/arquivo/...`, para o dono e o administrador (RNF07).
- Em desenvolvimento, e-mails (recuperação de senha) aparecem no terminal.

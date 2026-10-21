# Esboço das telas (mobile first)

Legenda: `[ botão ]` ação · `( )` campo · fluxo pensado para poucos passos e uso em deslocamento.

## Cliente

### C1 — Login / Cadastro
```
+--------------------+
|   VoltaSegura      |
| (E-mail)           |
| (Senha)            |
| [     Entrar     ] |
| Esqueci a senha    |
| Criar conta        |
+--------------------+
```

### C2 — Início / Solicitar corrida
```
+--------------------+
| Olá, Maria         |
| Coleta:            |
| (Endereço) [📍 usar|
|            minha   |
|            posição]|
| Destino:           |
| (Endereço)         |
| Veículo: (v Gol)   |
| Pagamento: (v Pix) |
| [ Ver estimativa ] |
+--------------------+
```

### C3 — Confirmação
```
+--------------------+
| Distância: 12,4 km |
| Estimativa: R$85,00|
| Veículo: Gol ABC.. |
| Pagamento: Pix     |
| [ Confirmar pedido]|
| [ Voltar ]         |
+--------------------+
```

### C4 — Acompanhamento (atualiza por polling)
```
+--------------------+
| Status: A caminho  |
| João • ★ 4,8       |
| Bicicleta dobrável |
| Distância: 1,2 km  |
| Seu código: 4 8 2 1|
| [ Cancelar corrida]|
+--------------------+
```

### C5 — Pagamento e recibo
```
+--------------------+
| Corrida finalizada |
| Total: R$ 85,00    |
| (Pix) (Cartão)     |
| [ Pagar ]          |
| → Recibo           |
+--------------------+
```

### C6 — Avaliação
```
+--------------------+
| Avalie o João      |
| ★ ★ ★ ★ ☆          |
| (Comentário)       |
| [ Enviar ]         |
+--------------------+
```

### C7 — Meus veículos / Histórico / Perfil
Lista com [ Adicionar ], editar e remover; histórico em cards (data, destino, valor, status).

## Motorista

### M1 — Cadastro / Documentos
Documento de identidade (foto), CNH (número e validade), bicicleta (modelo + foto), dados de repasse. Status: pendente / aprovado / rejeitado.

### M2 — Painel
```
+--------------------+
| Status: OFFLINE    |
| [  FICAR ONLINE  ] |
| Aprovação: ✔       |
| CNH válida: ✔      |
| Bicicleta: ✔       |
| Ganhos hoje: R$ 0  |
+--------------------+
```
Se algum requisito falhar (RN01), o botão fica desabilitado com o motivo.

### M3 — Nova solicitação
```
+--------------------+
| Nova corrida!      |
| Coleta a 1,2 km    |
| Destino: 12,4 km   |
| Você recebe R$68,00|
| [ Aceitar ][Recusar]|
+--------------------+
```

### M4 — Corrida em andamento
```
+--------------------+
| Status: A caminho  |
| Cliente: Maria     |
| Veículo: Gol ABC.. |
| [ Cheguei ]        |
| (Código do cliente)|
| [ Iniciar corrida ]|
| [ Finalizar ]      |
+--------------------+
```
Apenas o botão da próxima etapa válida fica ativo (RN04).

### M5 — Ganhos e histórico
Filtro por período; total bruto, taxa da plataforma e repasse por corrida.

## Administrador (Django Admin personalizado)
- Fila de motoristas e bicicletas pendentes: [ Aprovar ] [ Rejeitar ]
- Configuração de tarifa base, valor por km e % da plataforma
- Lista de corridas e pagamentos com filtros (status, data, motorista, cliente)
- Bloquear/desbloquear usuários

## Telas transversais
- Página offline amigável (service worker)
- Permissão de localização negada / GPS indisponível: mensagem + opção de digitar endereço

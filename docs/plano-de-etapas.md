# Plano de etapas

Cada etapa = um prompt (ou poucos), com critério de aceite e testes antes de seguir.

| # | Etapa | Entrega | Regras/RFs cobertos |
|---|---|---|---|
| 0 | Setup | Projeto Django, Postgres via Docker Compose, `.env`/`.env.example`, README de execução | RNF12, RNF13 |
| 1 | Contas e perfis | Usuário com perfil (cliente/motorista/admin), cadastro, login, logout, recuperação de senha | RF01, RNF08 |
| 2 | Veículos e bicicleta | CRUD de veículos; cadastro de bicicleta com foto; dados de CNH e documento; dados de repasse | RF02–RF05, RNF07 |
| 3 | Aprovação e bloqueio | Admin aprova/rejeita motoristas e bicicletas; bloqueia usuários | RF26, RF28 |
| 4 | Disponibilidade | Online/offline com validações; registro periódico de localização | RF06, RF07, RN01 |
| 5 | Solicitação e preço | Solicitação com coleta/destino, distância, estimativa configurável, RN09 | RF08–RF10, RN06, RN09 |
| 6 | Despacho | Oferta aos motoristas elegíveis mais próximos; aceite com lock (concorrência) | RF11, RF12, RN02, RN03, RNF06 |
| 7 | Ciclo da corrida | Estados, transições bloqueadas, chegada, código, início, fim, cancelamento, log de status | RF13–RF17, RN04, RN05, RNF09 |
| 8 | Pagamento simulado | Pix/cartão; aprovado/recusado/estornado; divisão 20%; recibo; ganhos | RF19–RF22, RN07, RN08 |
| 9 | Avaliação e histórico | Nota e comentário, uma vez por corrida, média no perfil, históricos | RF23–RF25, RN10 |
| 10 | Admin | Tarifas, comissão, listagens com filtros | RF27, RF29 |
| 11 | Frontend mobile first + polling | Telas, Fetch API, geolocalização com tratamento de erro | RF18, RNF03–RNF05 |
| 12 | PWA | Manifesto, ícones, Service Worker, página offline, estado da corrida preservado | RNF01, RNF02 |
| 13 | Fechamento | Testes, seed de exemplo, simulador de posição, documentação da API, README final | RNF10, RNF11 |

**Ordem de prioridade se faltar tempo:** 0 → 1 → 2/3 → 5/6/7 → 8 → 9 → 11/12

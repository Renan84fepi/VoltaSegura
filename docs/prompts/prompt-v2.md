# Prompt v2 — Etapas 2 e 3 (Cadastros do cliente e do motorista + aprovação)

> Pré-requisito: etapas 0 e 1 do prompt v1 concluídas (setup, Docker, usuário com perfil, login, recuperação de senha).

## Contexto
VoltaSegura: PWA em Django em que clientes pedem um motorista para conduzir o carro do cliente; o motorista chega com uma mini bicicleta elétrica dobrável. Estamos no **Marco 2 — Base e cadastros**. O código será revisado e explicado por nós na apresentação: prefira simplicidade e comentários onde a regra não for óbvia.

## Tarefa desta etapa
1. **Veículos do cliente (RF02):** app `veiculos` com marca, modelo, cor, ano e placa (formatos ABC1234 e ABC1D23, normalizada em maiúsculas, única por cliente). CRUD só para o próprio cliente; veículo de outro cliente → 404.
2. **Documentos do motorista (RF03):** app `motoristas` com foto do documento de identidade, número da CNH (11 dígitos) e validade. Rejeitar CNH já vencida no envio.
3. **Bicicleta (RF04):** marca, modelo, cor e foto, 1 por motorista.
4. **Dados de repasse (RF05):** titular e chave Pix (CPF, e-mail, telefone ou aleatória, validada conforme o tipo), com banco/agência/conta opcionais.
5. **Aprovação (RF26):** documentos e bicicleta têm situação pendente/aprovado/rejeitado, com motivo da rejeição, quem avaliou e quando. No Django Admin: filtros por situação, ações "aprovar" e "rejeitar", link para ver as imagens. Não aprovar motorista com CNH vencida.
6. **Reenvio:** se o motorista alterar dados já avaliados, a situação volta a "pendente".
7. **RN01 (preparação):** propriedade `pode_ficar_online` = usuário não bloqueado + motorista aprovado + CNH válida + bicicleta aprovada.
8. **Telas mobile first** (Bootstrap 5, pt-BR): lista/forma de veículos para o cliente; painel do motorista com 3 cartões (documentos, bicicleta, recebimento) e a situação de cada um.
9. **Dados de exemplo:** comando `criar_dados_exemplo` com admin, 2 clientes e 4 motoristas em situações diferentes (aprovado, pendente, rejeitado, CNH vencida).

## Restrições
- Stack e versões do prompt v1; PostgreSQL; nada de SQLite.
- **Privacidade (RNF07):** documentos e fotos não podem ter URL pública. Entregar por view que confere permissão (dono ou administrador). Sem `MEDIA_URL`.
- Validar uploads: só imagem (jpg, jpeg, png, webp), máximo 5 MB, nome aleatório (UUID).
- Perfil nunca vem do formulário de cadastro com valor "administrador".
- Campos com máscara (placa, telefone, CNH, CPF) devem aceitar a pontuação e normalizar antes de salvar; cuidado para que o `max_length` do modelo não rejeite a entrada mascarada.
- Usar as APIs atuais da versão instalada do Django (conferir avisos de depreciação).
- Não implementar nada de etapas futuras (online/offline, corridas, pagamento).

## Critérios de aceite
- Cliente cadastra, edita e remove só os próprios veículos; placa inválida ou repetida é recusada.
- Motorista envia documentos, bicicleta e dados de recebimento; CNH vencida e arquivo que não é imagem são recusados.
- Administrador aprova/rejeita pelo admin; CNH vencida não é aprovada; rejeição sempre tem motivo.
- Alterar dado aprovado volta para pendente.
- `pode_ficar_online` só é verdadeiro com todas as condições (inclusive CNH válida no último dia).
- Documento/foto: anônimo → login, outro usuário → 403, dono e administrador → 200; `/media/...` → 404.
- `pytest` passa, com testes para cada regra acima.
- Ao final, listar arquivos criados/alterados e como testar manualmente.

## Formato da resposta
Plano curto → código por arquivo → roteiro de teste manual.

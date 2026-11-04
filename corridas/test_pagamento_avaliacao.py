"""Marco 4: pagamento simulado (RF19–RF22), avaliação (RF23, RF24, RN10) e histórico (RF25)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from . import regras
from .models import Configuracao, Corrida, Pagamento
from .regras import RegraViolada
from .tests import ate, criar_cliente, criar_motorista, pedir

pytestmark = pytest.mark.django_db
Status = Corrida.Status
StatusPagamento = Pagamento.Status


def finalizada(**kwargs):
    corrida, cliente, motorista = ate(Status.FINALIZADA, **kwargs)
    return corrida, cliente, motorista, corrida.pagamento


# ---------------------------------------------------------------- RF19 / RF20 / RN07 / RN08

def test_finalizar_gera_pagamento_pendente_com_valores_separados():
    corrida, _, _, pagamento = finalizada()
    assert pagamento.status == StatusPagamento.PENDENTE
    assert pagamento.forma == corrida.forma_pagamento
    assert pagamento.valor_total == corrida.preco_estimado
    assert pagamento.taxa_plataforma + pagamento.valor_motorista == pagamento.valor_total
    assert list(pagamento.eventos.values_list("status_novo", flat=True)) == [StatusPagamento.PENDENTE]


def test_caso_de_referencia_85_reais():
    # RN08: R$ 85,00 → plataforma R$ 17,00 → motorista R$ 68,00
    corrida, cliente, motorista = ate(Status.EM_ANDAMENTO)
    Corrida.objects.filter(pk=corrida.pk).update(preco_estimado=Decimal("85.00"))
    regras.finalizar(corrida.pk, motorista)
    pagamento = Pagamento.objects.get(corrida=corrida)
    assert pagamento.valor_total == Decimal("85.00")
    assert pagamento.taxa_plataforma == Decimal("17.00")
    assert pagamento.valor_motorista == Decimal("68.00")


def test_pagamento_usa_a_comissao_da_epoca_do_pedido():
    # RN07: mudar a comissão depois do pedido não altera a corrida já pedida.
    corrida, _, motorista = ate(Status.EM_ANDAMENTO)
    config = Configuracao.atual()
    config.percentual_plataforma = Decimal("50.00")
    config.save()
    regras.finalizar(corrida.pk, motorista)
    pagamento = Pagamento.objects.get(corrida=corrida)
    assert pagamento.percentual_plataforma == Decimal("20.00")
    assert pagamento.taxa_plataforma == (corrida.preco_estimado * Decimal("0.20")).quantize(Decimal("0.01"))


@pytest.mark.parametrize("status", [Status.ACEITA, Status.CHEGOU, Status.EM_ANDAMENTO])
def test_corrida_nao_finalizada_nao_tem_pagamento(status):
    corrida, cliente, _ = ate(status)
    assert not Pagamento.objects.filter(corrida=corrida).exists()
    with pytest.raises(RegraViolada) as erro:
        regras.pagar(corrida.pk, cliente)
    assert erro.value.status_http == 409


def test_corrida_cancelada_nao_gera_pagamento():
    corrida, cliente, _ = ate(Status.ACEITA)
    regras.cancelar(corrida.pk, cliente)
    assert not Pagamento.objects.filter(corrida=corrida).exists()


# ---------------------------------------------------------------- RF21: aprovado, recusado, estornado

def test_pagamento_aprovado():
    corrida, cliente, _, _ = finalizada()
    pagamento = regras.pagar(corrida.pk, cliente)
    assert pagamento.status == StatusPagamento.APROVADO
    assert pagamento.pago_em is not None


def test_recusado_pode_tentar_de_novo():
    corrida, cliente, _, _ = finalizada()
    assert regras.pagar(corrida.pk, cliente, aprovar=False).status == StatusPagamento.RECUSADO
    assert regras.pagar(corrida.pk, cliente, aprovar=False).status == StatusPagamento.RECUSADO
    pagamento = regras.pagar(corrida.pk, cliente)
    assert pagamento.status == StatusPagamento.APROVADO
    assert pagamento.tentativas == 3
    assert list(pagamento.eventos.values_list("status_novo", flat=True)) == [
        StatusPagamento.PENDENTE, StatusPagamento.RECUSADO, StatusPagamento.RECUSADO,
        StatusPagamento.APROVADO,
    ]


def test_nao_paga_duas_vezes():
    corrida, cliente, _, _ = finalizada()
    regras.pagar(corrida.pk, cliente)
    with pytest.raises(RegraViolada) as erro:
        regras.pagar(corrida.pk, cliente)
    assert erro.value.status_http == 409


def test_estorno_so_de_pagamento_aprovado(admin_user):
    corrida, cliente, _, pagamento = finalizada()
    with pytest.raises(RegraViolada):
        regras.estornar(pagamento.pk, admin_user)  # ainda pendente
    regras.pagar(corrida.pk, cliente)
    pagamento = regras.estornar(pagamento.pk, admin_user)
    assert pagamento.status == StatusPagamento.ESTORNADO
    assert pagamento.estornado_em is not None
    with pytest.raises(RegraViolada):
        regras.estornar(pagamento.pk, admin_user)  # estornado é final
    with pytest.raises(RegraViolada):
        regras.pagar(corrida.pk, cliente)


def test_estorno_pela_acao_do_admin(client, admin_user):
    corrida, cliente, _, pagamento = finalizada()
    regras.pagar(corrida.pk, cliente)
    client.force_login(admin_user)
    client.post(
        reverse("admin:corridas_pagamento_changelist"),
        {"action": "estornar", "_selected_action": [pagamento.pk]},
    )
    pagamento.refresh_from_db()
    assert pagamento.status == StatusPagamento.ESTORNADO


def test_estorno_pelo_botao_da_pagina_do_pagamento(client, admin_user):
    corrida, cliente, _, pagamento = finalizada()
    pagina = reverse("admin:corridas_pagamento_change", args=[pagamento.pk])
    estornar = reverse("admin:corridas_pagamento_estornar", args=[pagamento.pk])
    client.force_login(admin_user)
    assert estornar not in client.get(pagina).text  # pendente: sem botão
    regras.pagar(corrida.pk, cliente)
    assert estornar in client.get(pagina).text
    assert client.get(estornar).status_code == 200  # confirmação
    client.post(estornar, {"motivo": "Cliente contestou"})
    pagamento.refresh_from_db()
    assert pagamento.status == StatusPagamento.ESTORNADO
    assert pagamento.eventos.last().observacao == "Cliente contestou"
    client.force_login(cliente)
    assert client.post(estornar).status_code == 302  # fora do admin: vai para o login do admin
    pagamento.refresh_from_db()
    assert pagamento.eventos.count() == 3


def test_so_o_cliente_da_corrida_paga(client):
    corrida, _, motorista, _ = finalizada()
    with pytest.raises(RegraViolada) as erro:
        regras.pagar(corrida.pk, criar_cliente())
    assert erro.value.status_http == 404
    client.force_login(motorista)
    assert client.post(reverse("api:pagar", args=[corrida.pk])).status_code == 403


def test_pagamento_em_aberto_impede_novo_pedido():
    corrida, cliente, _, _ = finalizada()
    with pytest.raises(RegraViolada) as erro:
        pedir(cliente)
    assert erro.value.status_http == 409
    regras.pagar(corrida.pk, cliente)
    assert pedir(cliente).status == Status.SOLICITADA


def test_api_de_pagamento(client):
    corrida, cliente, _, _ = finalizada()
    client.force_login(cliente)
    url = reverse("api:pagar", args=[corrida.pk])
    dados = client.get(reverse("api:corrida", args=[corrida.pk])).json()
    assert dados["pagamento"]["pode_pagar"] is True
    assert "valor_motorista" not in dados["pagamento"]  # repasse é do motorista
    assert client.post(url, {"resultado": "talvez"}, content_type="application/json").status_code == 400
    recusado = client.post(url, {"resultado": "recusado"}, content_type="application/json").json()
    assert recusado["pagamento"]["status"] == StatusPagamento.RECUSADO
    aprovado = client.post(url, {}, content_type="application/json").json()
    assert aprovado["pagamento"]["status"] == StatusPagamento.APROVADO
    assert aprovado["pagamento"]["pode_pagar"] is False
    assert client.post(url, {}, content_type="application/json").status_code == 409


def test_solicitar_leva_ao_pagamento_pendente(client):
    corrida, cliente, _, _ = finalizada()
    client.force_login(cliente)
    assert client.get(reverse("corridas:solicitar")).url == reverse("corridas:acompanhar", args=[corrida.pk])


# ---------------------------------------------------------------- RF22: recibo e ganhos

def test_recibo_so_para_as_partes(client):
    corrida, cliente, motorista, _ = finalizada()
    url = reverse("corridas:recibo", args=[corrida.pk])
    client.force_login(cliente)
    resposta = client.get(url)
    assert resposta.status_code == 200
    assert "Seu repasse" not in resposta.text
    client.force_login(motorista)
    assert "Seu repasse" in client.get(url).text
    client.force_login(criar_cliente())
    assert client.get(url).status_code == 404


def test_corrida_sem_pagamento_nao_tem_recibo(client):
    corrida, cliente, _ = ate(Status.ACEITA)
    client.force_login(cliente)
    assert client.get(reverse("corridas:recibo", args=[corrida.pk])).status_code == 404


def _pagamento_em(dias_atras, status, motorista):
    corrida, cliente, _, pagamento = finalizada(motorista=motorista)
    if status != StatusPagamento.PENDENTE:
        regras.pagar(corrida.pk, cliente, aprovar=status != StatusPagamento.RECUSADO)
    if status == StatusPagamento.ESTORNADO:
        regras.estornar(pagamento.pk, None)
    Pagamento.objects.filter(pk=pagamento.pk).update(
        criado_em=timezone.now() - timedelta(days=dias_atras)
    )
    pagamento.refresh_from_db()
    return pagamento


def test_ganhos_por_periodo():
    motorista = criar_motorista()
    hoje_ok = _pagamento_em(0, StatusPagamento.APROVADO, motorista)
    semana_ok = _pagamento_em(3, StatusPagamento.APROVADO, motorista)
    _pagamento_em(40, StatusPagamento.APROVADO, motorista)  # fora dos 30 dias
    pendente = _pagamento_em(1, StatusPagamento.PENDENTE, motorista)
    estornado = _pagamento_em(2, StatusPagamento.ESTORNADO, motorista)
    _pagamento_em(0, StatusPagamento.APROVADO, criar_motorista())  # de outro motorista

    semana = regras.ganhos(motorista, *regras.periodo("7dias"))
    assert semana["recebido"] == hoje_ok.valor_motorista + semana_ok.valor_motorista
    assert semana["corridas_pagas"] == 2
    assert semana["em_aberto"] == pendente.valor_motorista
    assert semana["estornado"] == estornado.valor_motorista
    assert len(semana["pagamentos"]) == 4

    assert regras.ganhos(motorista, *regras.periodo("hoje"))["recebido"] == hoje_ok.valor_motorista
    assert regras.ganhos(motorista, *regras.periodo("30dias"))["corridas_pagas"] == 2


def test_periodo_invertido_e_recusado():
    hoje = timezone.localdate()
    with pytest.raises(RegraViolada):
        regras.ganhos(criar_motorista(), hoje, hoje - timedelta(days=1))


def test_api_e_pagina_de_ganhos(client):
    motorista = criar_motorista()
    pago = _pagamento_em(0, StatusPagamento.APROVADO, motorista)
    client.force_login(motorista)
    dados = client.get(reverse("api:ganhos"), {"periodo": "hoje"}).json()
    assert dados["recebido"] == str(pago.valor_motorista)
    hoje = timezone.localdate().isoformat()
    assert client.get(reverse("api:ganhos"), {"de": hoje, "ate": hoje}).json()["corridas_pagas"] == 1
    assert client.get(reverse("api:ganhos"), {"de": "ontem"}).status_code == 400
    assert client.get(reverse("corridas:ganhos"), {"periodo": "mes"}).status_code == 200
    client.force_login(criar_cliente())
    assert client.get(reverse("api:ganhos")).status_code == 403
    assert client.get(reverse("corridas:ganhos")).status_code == 403


# ---------------------------------------------------------------- RF23 / RN10: avaliação

@pytest.mark.parametrize("status", [Status.SOLICITADA, Status.ACEITA, Status.CHEGOU, Status.EM_ANDAMENTO])
def test_nao_avalia_antes_de_finalizar(status):
    corrida, cliente, _ = ate(status)
    with pytest.raises(RegraViolada) as erro:
        regras.avaliar(corrida.pk, cliente, 5)
    assert erro.value.status_http == 409


def test_nao_avalia_corrida_cancelada():
    corrida, cliente, _ = ate(Status.ACEITA)
    regras.cancelar(corrida.pk, cliente)
    with pytest.raises(RegraViolada):
        regras.avaliar(corrida.pk, cliente, 5)


def test_avalia_uma_vez_por_corrida():
    corrida, cliente, motorista, _ = finalizada()
    avaliacao = regras.avaliar(corrida.pk, cliente, 4, "  Educado e pontual.  ")
    assert avaliacao.motorista == motorista
    assert avaliacao.comentario == "Educado e pontual."
    with pytest.raises(RegraViolada) as erro:
        regras.avaliar(corrida.pk, cliente, 5)
    assert erro.value.status_http == 409


@pytest.mark.parametrize("nota", [0, 6, -1])
def test_nota_fora_de_1_a_5(nota):
    corrida, cliente, _, _ = finalizada()
    with pytest.raises(RegraViolada):
        regras.avaliar(corrida.pk, cliente, nota)


def test_so_o_cliente_da_corrida_avalia(client):
    corrida, _, motorista, _ = finalizada()
    with pytest.raises(RegraViolada) as erro:
        regras.avaliar(corrida.pk, criar_cliente(), 5)
    assert erro.value.status_http == 404
    client.force_login(motorista)
    assert client.post(reverse("api:avaliar", args=[corrida.pk]), {"nota": 1}, content_type="application/json").status_code == 403


def test_api_de_avaliacao(client):
    corrida, cliente, _, _ = finalizada()
    client.force_login(cliente)
    url = reverse("api:avaliar", args=[corrida.pk])
    assert client.get(reverse("api:corrida", args=[corrida.pk])).json()["pode_avaliar"] is True
    assert client.post(url, {"nota": 9}, content_type="application/json").status_code == 400
    resposta = client.post(url, {"nota": 5, "comentario": "Ótimo"}, content_type="application/json")
    assert resposta.status_code == 201
    assert resposta.json()["avaliacao"]["nota"] == 5
    assert resposta.json()["pode_avaliar"] is False
    assert client.post(url, {"nota": 5}, content_type="application/json").status_code == 409


# ---------------------------------------------------------------- RF24: nota média

def test_nota_media_do_motorista(client):
    motorista = criar_motorista()
    assert regras.nota_do_motorista(motorista) == {"media": None, "total": 0}
    for nota in (5, 4, 4):
        corrida, cliente, _, _ = finalizada(motorista=motorista)
        regras.avaliar(corrida.pk, cliente, nota)
    assert regras.nota_do_motorista(motorista) == {"media": Decimal("4.3"), "total": 3}

    # Aparece para o cliente da próxima corrida e no painel do motorista.
    corrida, cliente, _ = ate(Status.ACEITA, motorista=motorista)
    client.force_login(cliente)
    dados = client.get(reverse("api:corrida", args=[corrida.pk])).json()
    assert dados["motorista"]["nota"] == {"media": "4.3", "total": 3}
    client.force_login(motorista)
    assert "4,3" in client.get(reverse("motoristas:painel")).text
    assert client.get(reverse("api:nota")).json() == {"media": "4.3", "total": 3}


# ---------------------------------------------------------------- RF25: histórico

def test_historico_mostra_so_as_proprias_corridas(client):
    corrida, cliente, motorista, _ = finalizada()
    outra, _, _ = ate(Status.ACEITA)
    client.force_login(cliente)
    ids = [c["id"] for c in client.get(reverse("api:historico")).json()["corridas"]]
    assert ids == [corrida.pk]
    assert f"#{corrida.pk}" in client.get(reverse("corridas:historico")).text
    client.force_login(motorista)
    item = client.get(reverse("api:historico")).json()["corridas"][0]
    assert item["id"] == corrida.pk
    assert item["valor"] == str(corrida.pagamento.valor_motorista)  # motorista vê o repasse
    assert outra.pk not in [c["id"] for c in client.get(reverse("api:historico")).json()["corridas"]]


def test_historico_paginado(client):
    cliente = criar_cliente()
    for _ in range(21):
        corrida = pedir(cliente)
        regras.cancelar(corrida.pk, cliente)
    client.force_login(cliente)
    primeira = client.get(reverse("api:historico")).json()
    assert len(primeira["corridas"]) == 20 and primeira["tem_proxima"] is True
    segunda = client.get(reverse("api:historico"), {"pagina": 2}).json()
    assert len(segunda["corridas"]) == 1 and segunda["tem_proxima"] is False
    assert client.get(reverse("corridas:historico"), {"page": 2}).status_code == 200


def test_admin_nao_usa_o_historico_de_parte(client, admin_user):
    client.force_login(admin_user)
    assert client.get(reverse("corridas:historico")).status_code == 403

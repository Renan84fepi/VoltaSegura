import pytest
from django.urls import reverse

from contas.models import Usuario

from .models import Veiculo

pytestmark = pytest.mark.django_db

DADOS = {"marca": "Fiat", "modelo": "Argo", "cor": "Prata", "ano": 2021, "placa": "abc-1d23"}


def test_cliente_cadastra_veiculo_com_placa_normalizada(client, cliente):
    client.force_login(cliente)
    resposta = client.post(reverse("veiculos:novo"), DADOS)
    assert resposta.status_code == 302
    veiculo = Veiculo.objects.get()
    assert veiculo.placa == "ABC1D23" and veiculo.cliente == cliente


@pytest.mark.parametrize("placa", ["AB1234", "1234ABC", "ABCDEFG", "ABC12345"])
def test_placa_invalida(client, cliente, placa):
    client.force_login(cliente)
    resposta = client.post(reverse("veiculos:novo"), {**DADOS, "placa": placa})
    assert resposta.status_code == 200
    assert not Veiculo.objects.exists()


def test_placa_repetida_para_o_mesmo_cliente(client, cliente):
    client.force_login(cliente)
    client.post(reverse("veiculos:novo"), DADOS)
    resposta = client.post(reverse("veiculos:novo"), DADOS)
    assert resposta.status_code == 200
    assert Veiculo.objects.count() == 1


def test_ano_invalido(client, cliente):
    client.force_login(cliente)
    assert client.post(reverse("veiculos:novo"), {**DADOS, "ano": 1950}).status_code == 200


def test_editar_e_remover(client, cliente):
    client.force_login(cliente)
    client.post(reverse("veiculos:novo"), DADOS)
    veiculo = Veiculo.objects.get()
    client.post(reverse("veiculos:editar", args=[veiculo.pk]), {**DADOS, "cor": "Azul"})
    veiculo.refresh_from_db()
    assert veiculo.cor == "Azul"
    client.post(reverse("veiculos:remover", args=[veiculo.pk]))
    assert not Veiculo.objects.exists()


def test_cliente_nao_acessa_veiculo_de_outro(client, cliente):
    outro = Usuario.objects.create_user("outro@t.com", "x", nome="Outro", telefone="35999990009")
    veiculo = Veiculo.objects.create(cliente=outro, **{**DADOS, "placa": "ABC1D23"})
    client.force_login(cliente)
    assert client.get(reverse("veiculos:editar", args=[veiculo.pk])).status_code == 404
    assert client.post(reverse("veiculos:remover", args=[veiculo.pk])).status_code == 404
    assert Veiculo.objects.filter(pk=veiculo.pk).exists()


def test_motorista_nao_acessa_veiculos(client, motorista):
    client.force_login(motorista)
    assert client.get(reverse("veiculos:lista")).status_code == 403


def test_anonimo_vai_para_login(client):
    resposta = client.get(reverse("veiculos:lista"))
    assert resposta.status_code == 302 and "/entrar/" in resposta["Location"]

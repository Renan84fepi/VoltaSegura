import pytest
from django.core import mail
from django.urls import reverse

from .models import Usuario

pytestmark = pytest.mark.django_db

DADOS = {
    "nome": "Maria Silva",
    "email": "Maria@Exemplo.com",
    "telefone": "(35) 99999-1234",
    "perfil": "cliente",
    "password1": "Senha-forte-123",
    "password2": "Senha-forte-123",
}


def test_cadastro_cliente_normaliza_dados_e_loga(client):
    resposta = client.post(reverse("cadastro"), DADOS)
    assert resposta.status_code == 302
    usuario = Usuario.objects.get(email="maria@exemplo.com")
    assert usuario.perfil == "cliente"
    assert usuario.telefone == "35999991234"
    assert usuario.check_password("Senha-forte-123")  # senha com hash
    assert "_auth_user_id" in client.session


def test_cadastro_motorista(client):
    client.post(reverse("cadastro"), {**DADOS, "perfil": "motorista"})
    assert Usuario.objects.get(email="maria@exemplo.com").perfil == "motorista"


def test_cadastro_nao_permite_virar_administrador(client):
    resposta = client.post(reverse("cadastro"), {**DADOS, "perfil": "administrador"})
    assert resposta.status_code == 200
    assert not Usuario.objects.exists()


def test_email_duplicado_rejeitado(client, cliente):
    resposta = client.post(reverse("cadastro"), {**DADOS, "email": "CLIENTE@t.com"})
    assert resposta.status_code == 200
    assert Usuario.objects.count() == 1


def test_login_e_logout(client, cliente):
    resposta = client.post(reverse("login"), {"username": "cliente@t.com", "password": "Senha-forte-123"})
    assert resposta.status_code == 302
    client.post(reverse("logout"))
    assert "_auth_user_id" not in client.session


def test_login_com_senha_errada(client, cliente):
    resposta = client.post(reverse("login"), {"username": "cliente@t.com", "password": "errada"})
    assert resposta.status_code == 200
    assert "_auth_user_id" not in client.session


def test_usuario_bloqueado_nao_entra(client, cliente):
    cliente.bloqueado = True
    cliente.save()
    resposta = client.post(reverse("login"), {"username": "cliente@t.com", "password": "Senha-forte-123"})
    assert resposta.status_code == 200
    assert "bloqueada" in resposta.content.decode()
    assert "_auth_user_id" not in client.session


def test_sessao_de_usuario_bloqueado_depois_do_login_e_derrubada(client, cliente):
    client.force_login(cliente)
    Usuario.objects.filter(pk=cliente.pk).update(bloqueado=True)
    assert client.get(reverse("home")).status_code == 302
    assert "/entrar/" in client.get(reverse("home"))["Location"]


@pytest.mark.parametrize(
    "fixture, destino",
    [("cliente", "/corridas/nova/"), ("motorista", "/motorista/"), ("admin_user", "/admin/")],
)
def test_home_redireciona_por_perfil(client, request, fixture, destino):
    client.force_login(request.getfixturevalue(fixture))
    assert client.get(reverse("home"))["Location"] == destino


def test_superusuario_recebe_perfil_administrador(admin_user):
    assert admin_user.perfil == Usuario.Perfil.ADMINISTRADOR
    assert admin_user.is_staff


def test_recuperacao_de_senha_envia_email(client, cliente):
    client.post(reverse("password_reset"), {"email": "cliente@t.com"})
    assert len(mail.outbox) == 1
    assert "/senha/redefinir/" in mail.outbox[0].body


def test_telas_exigem_login(client):
    assert client.get(reverse("home")).status_code == 302

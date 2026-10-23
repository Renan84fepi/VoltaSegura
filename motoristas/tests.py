from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from conftest import gerar_imagem

from .models import Bicicleta, DadosRepasse, PerfilMotorista

pytestmark = pytest.mark.django_db
Status = PerfilMotorista.Status


def enviar_documentos(client, validade, **extra):
    return client.post(
        reverse("motoristas:documentos"),
        {
            "documento_identidade": gerar_imagem("rg.png"),
            "cnh_numero": "012.345.678-90",
            "cnh_validade": validade.isoformat(),
            **extra,
        },
    )


def enviar_bicicleta(client):
    return client.post(
        reverse("motoristas:bicicleta"),
        {"marca": "Dobrix", "modelo": "Mini E1", "cor": "Cinza", "foto": gerar_imagem("bike.png")},
    )


def test_envio_de_documentos(client, motorista, validade_futura):
    client.force_login(motorista)
    assert enviar_documentos(client, validade_futura).status_code == 302
    perfil = PerfilMotorista.objects.get()
    assert perfil.cnh_numero == "01234567890"
    assert perfil.status_aprovacao == Status.PENDENTE
    assert perfil.documento_identidade.name.startswith("documentos/")


def test_cnh_vencida_e_recusada_no_envio(client, motorista):
    client.force_login(motorista)
    ontem = timezone.localdate() - timedelta(days=1)
    assert enviar_documentos(client, ontem).status_code == 200
    assert not PerfilMotorista.objects.exists()


def test_arquivo_que_nao_e_imagem_e_recusado(client, motorista, validade_futura):
    from django.core.files.uploadedfile import SimpleUploadedFile

    client.force_login(motorista)
    falso = SimpleUploadedFile("rg.png", b"nao sou imagem", content_type="image/png")
    resposta = client.post(
        reverse("motoristas:documentos"),
        {"documento_identidade": falso, "cnh_numero": "01234567890", "cnh_validade": validade_futura.isoformat()},
    )
    assert resposta.status_code == 200
    assert not PerfilMotorista.objects.exists()


def test_cadastro_de_bicicleta(client, motorista):
    client.force_login(motorista)
    assert enviar_bicicleta(client).status_code == 302
    assert Bicicleta.objects.get().usuario == motorista


def test_cliente_nao_acessa_area_do_motorista(client, cliente):
    client.force_login(cliente)
    assert client.get(reverse("motoristas:painel")).status_code == 403
    assert client.get(reverse("motoristas:documentos")).status_code == 403


def test_editar_dado_aprovado_volta_para_pendente(client, motorista, admin_user, validade_futura):
    client.force_login(motorista)
    enviar_documentos(client, validade_futura)
    PerfilMotorista.objects.get().aprovar(admin_user)
    # reenvio sem mudanças: continua aprovado
    client.post(
        reverse("motoristas:documentos"),
        {"cnh_numero": "01234567890", "cnh_validade": validade_futura.isoformat()},
    )
    assert PerfilMotorista.objects.get().status_aprovacao == Status.APROVADO
    # mudança na CNH: volta a pendente
    client.post(
        reverse("motoristas:documentos"),
        {"cnh_numero": "99999999999", "cnh_validade": validade_futura.isoformat()},
    )
    perfil = PerfilMotorista.objects.get()
    assert perfil.status_aprovacao == Status.PENDENTE and perfil.avaliado_por is None


@pytest.mark.parametrize(
    "tipo, chave, ok",
    [
        ("cpf", "529.982.247-25", True),
        ("cpf", "111.111.111-11", False),
        ("cpf", "123.456.789-00", False),
        ("email", "Motorista@Exemplo.com", True),
        ("email", "sem-arroba", False),
        ("telefone", "(35) 99999-1234", True),
        ("telefone", "123", False),
        ("aleatoria", "123e4567-e89b-12d3-a456-426614174000", True),
        ("aleatoria", "abc", False),
    ],
)
def test_validacao_da_chave_pix(client, motorista, tipo, chave, ok):
    client.force_login(motorista)
    resposta = client.post(
        reverse("motoristas:repasse"),
        {"titular": "Motorista", "tipo_chave_pix": tipo, "chave_pix": chave},
    )
    assert DadosRepasse.objects.exists() is ok
    assert (resposta.status_code == 302) is ok


def test_chave_pix_e_normalizada(client, motorista):
    client.force_login(motorista)
    client.post(
        reverse("motoristas:repasse"),
        {"titular": "M", "tipo_chave_pix": "cpf", "chave_pix": "529.982.247-25"},
    )
    assert DadosRepasse.objects.get().chave_pix == "52998224725"


# ---- RN01: pré-condições para ficar online ----
def montar_motorista_completo(motorista, admin_user, validade, bike_aprovada=True, docs_aprovados=True):
    perfil = PerfilMotorista.objects.create(
        usuario=motorista, documento_identidade=gerar_imagem(), cnh_numero="01234567890", cnh_validade=validade
    )
    bike = Bicicleta.objects.create(usuario=motorista, marca="D", modelo="M", cor="C", foto=gerar_imagem())
    if docs_aprovados:
        perfil.aprovar(admin_user)
    if bike_aprovada:
        bike.aprovar(admin_user)
    return perfil


def test_pode_ficar_online_quando_tudo_ok(motorista, admin_user, validade_futura):
    assert montar_motorista_completo(motorista, admin_user, validade_futura).pode_ficar_online


def test_nao_fica_online_sem_bicicleta_aprovada(motorista, admin_user, validade_futura):
    perfil = montar_motorista_completo(motorista, admin_user, validade_futura, bike_aprovada=False)
    assert not perfil.pode_ficar_online


def test_nao_fica_online_sem_documentos_aprovados(motorista, admin_user, validade_futura):
    perfil = montar_motorista_completo(motorista, admin_user, validade_futura, docs_aprovados=False)
    assert not perfil.pode_ficar_online


def test_nao_fica_online_com_cnh_vencida(motorista, admin_user):
    vencida = timezone.localdate() - timedelta(days=1)
    perfil = montar_motorista_completo(motorista, admin_user, vencida)
    assert not perfil.cnh_valida and not perfil.pode_ficar_online


def test_cnh_valida_no_ultimo_dia(motorista, admin_user):
    perfil = montar_motorista_completo(motorista, admin_user, timezone.localdate())
    assert perfil.cnh_valida


def test_nao_fica_online_se_bloqueado(motorista, admin_user, validade_futura):
    perfil = montar_motorista_completo(motorista, admin_user, validade_futura)
    motorista.bloqueado = True
    assert not perfil.pode_ficar_online


# ---- RF26: aprovação pelo administrador ----
def test_admin_aprova_motorista_pela_acao(client, motorista, admin_user, validade_futura):
    montar_motorista_completo(motorista, admin_user, validade_futura, docs_aprovados=False)
    client.force_login(admin_user)
    client.post(
        reverse("admin:motoristas_perfilmotorista_changelist"),
        {"action": "aprovar", "_selected_action": [PerfilMotorista.objects.get().pk]},
    )
    perfil = PerfilMotorista.objects.get()
    assert perfil.status_aprovacao == Status.APROVADO
    assert perfil.avaliado_por == admin_user and perfil.avaliado_em


def test_admin_nao_aprova_cnh_vencida(client, motorista, admin_user):
    vencida = timezone.localdate() - timedelta(days=1)
    montar_motorista_completo(motorista, admin_user, vencida, docs_aprovados=False)
    client.force_login(admin_user)
    client.post(
        reverse("admin:motoristas_perfilmotorista_changelist"),
        {"action": "aprovar", "_selected_action": [PerfilMotorista.objects.get().pk]},
    )
    assert PerfilMotorista.objects.get().status_aprovacao == Status.PENDENTE


def test_admin_rejeita_bicicleta_com_motivo_padrao(client, motorista, admin_user, validade_futura):
    montar_motorista_completo(motorista, admin_user, validade_futura, bike_aprovada=False)
    client.force_login(admin_user)
    client.post(
        reverse("admin:motoristas_bicicleta_changelist"),
        {"action": "rejeitar", "_selected_action": [Bicicleta.objects.get().pk]},
    )
    bike = Bicicleta.objects.get()
    assert bike.status_aprovacao == Status.REJEITADO and bike.motivo_rejeicao


def test_rejeicao_exige_motivo_no_modelo(motorista, validade_futura):
    from django.core.exceptions import ValidationError

    perfil = PerfilMotorista(
        usuario=motorista, cnh_numero="01234567890", cnh_validade=validade_futura,
        status_aprovacao=Status.REJEITADO, motivo_rejeicao=" ",
    )
    with pytest.raises(ValidationError):
        perfil.clean()


def test_motorista_nao_acessa_admin(client, motorista):
    client.force_login(motorista)
    resposta = client.get(reverse("admin:index"))
    assert resposta.status_code == 302 and "login" in resposta["Location"]


def test_admin_bloqueia_usuario_pela_acao(client, cliente, admin_user):
    client.force_login(admin_user)
    client.post(
        reverse("admin:contas_usuario_changelist"),
        {"action": "bloquear", "_selected_action": [cliente.pk, admin_user.pk]},
    )
    cliente.refresh_from_db(); admin_user.refresh_from_db()
    assert cliente.bloqueado and not admin_user.bloqueado


# ---- RNF07: privacidade dos arquivos ----
def test_documento_so_para_dono_e_admin(client, motorista, cliente, admin_user, validade_futura):
    montar_motorista_completo(motorista, admin_user, validade_futura)
    url = reverse("motoristas:arquivo", args=["documento", motorista.pk])

    assert client.get(url).status_code == 302  # anônimo => login

    client.force_login(cliente)
    assert client.get(url).status_code == 403

    client.force_login(motorista)
    resposta = client.get(url)
    assert resposta.status_code == 200 and resposta["Cache-Control"] == "private, no-store"

    client.force_login(admin_user)
    assert client.get(url).status_code == 200


def test_midia_nao_e_servida_por_url_publica(client, motorista, admin_user, validade_futura):
    perfil = montar_motorista_completo(motorista, admin_user, validade_futura)
    assert client.get("/media/" + perfil.documento_identidade.name).status_code == 404

import io
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from contas.models import Usuario


@pytest.fixture(autouse=True)
def media_temporaria(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture(autouse=True)
def sem_geocodificacao_real(settings):
    settings.GEOCODIFICACAO_ATIVA = False  # testes não dependem de internet


def gerar_imagem(nome="foto.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (60, 40), "#336699").save(buffer, "PNG")
    return SimpleUploadedFile(nome, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def imagem():
    return gerar_imagem


@pytest.fixture
def cliente(db):
    return Usuario.objects.create_user(
        "cliente@t.com", "Senha-forte-123", nome="Cliente", telefone="35999990001",
        perfil=Usuario.Perfil.CLIENTE,
    )


@pytest.fixture
def motorista(db):
    return Usuario.objects.create_user(
        "motorista@t.com", "Senha-forte-123", nome="Motorista", telefone="35999990002",
        perfil=Usuario.Perfil.MOTORISTA,
    )


@pytest.fixture
def admin_user(db):
    return Usuario.objects.create_superuser(
        "admin@t.com", "Senha-forte-123", nome="Admin", telefone="35999990003"
    )


@pytest.fixture
def validade_futura():
    return timezone.localdate() + timedelta(days=365)

import uuid
from pathlib import Path

from django.conf import settings
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.utils import timezone

from .validators import validar_tamanho_imagem

EXTENSOES_IMAGEM = ["jpg", "jpeg", "png", "webp"]


def upload_documento(instance, filename):
    return f"documentos/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def upload_bicicleta(instance, filename):
    return f"bicicletas/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class AprovacaoMixin(models.Model):
    """Campos e ações de aprovação feita pelo administrador (RF26)."""

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        APROVADO = "aprovado", "Aprovado"
        REJEITADO = "rejeitado", "Rejeitado"

    status_aprovacao = models.CharField(
        "situação", max_length=10, choices=Status.choices, default=Status.PENDENTE
    )
    motivo_rejeicao = models.TextField("motivo da rejeição", blank=True)
    avaliado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="avaliado por",
    )
    avaliado_em = models.DateTimeField("avaliado em", null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def aprovado(self):
        return self.status_aprovacao == self.Status.APROVADO

    def clean(self):
        super().clean()
        if self.status_aprovacao == self.Status.REJEITADO and not self.motivo_rejeicao.strip():
            from django.core.exceptions import ValidationError

            raise ValidationError({"motivo_rejeicao": "Informe o motivo da rejeição."})

    def aprovar(self, administrador):
        self.status_aprovacao = self.Status.APROVADO
        self.motivo_rejeicao = ""
        self.avaliado_por = administrador
        self.avaliado_em = timezone.now()
        self.save()

    def rejeitar(self, administrador, motivo=""):
        self.status_aprovacao = self.Status.REJEITADO
        self.motivo_rejeicao = motivo.strip() or "Dados rejeitados pela administração. Revise e reenvie."
        self.avaliado_por = administrador
        self.avaliado_em = timezone.now()
        self.save()

    def resetar_aprovacao(self):
        """Quando o motorista altera os dados, a aprovação volta a ser pendente."""
        self.status_aprovacao = self.Status.PENDENTE
        self.motivo_rejeicao = ""
        self.avaliado_por = None
        self.avaliado_em = None


class PerfilMotorista(AprovacaoMixin):
    """Documentos do motorista: identidade e CNH (RF03)."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_motorista",
        verbose_name="motorista",
    )
    documento_identidade = models.ImageField(
        "foto do documento de identidade",
        upload_to=upload_documento,
        validators=[FileExtensionValidator(EXTENSOES_IMAGEM), validar_tamanho_imagem],
    )
    cnh_numero = models.CharField(
        "número da CNH",
        max_length=11,
        validators=[RegexValidator(r"^\d{11}$", "A CNH tem 11 dígitos.")],
    )
    cnh_validade = models.DateField("validade da CNH")
    enviado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "motorista (documentos)"
        verbose_name_plural = "motoristas (documentos)"
        ordering = ["usuario__nome"]

    def __str__(self):
        return f"Motorista {self.usuario.nome}"

    @property
    def cnh_valida(self):
        return self.cnh_validade >= timezone.localdate()

    @property
    def bicicleta_aprovada(self):
        bicicleta = getattr(self.usuario, "bicicleta", None)
        return bool(bicicleta and bicicleta.aprovado)

    @property
    def pode_ficar_online(self):
        """RN01: aprovado, CNH válida e bicicleta aprovada (e não bloqueado)."""
        return (
            not self.usuario.bloqueado
            and self.aprovado
            and self.cnh_valida
            and self.bicicleta_aprovada
        )


class Bicicleta(AprovacaoMixin):
    """Mini bicicleta elétrica dobrável do motorista (RF04)."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bicicleta",
        verbose_name="motorista",
    )
    marca = models.CharField("marca", max_length=50)
    modelo = models.CharField("modelo", max_length=60)
    cor = models.CharField("cor", max_length=30)
    foto = models.ImageField(
        "foto da bicicleta",
        upload_to=upload_bicicleta,
        validators=[FileExtensionValidator(EXTENSOES_IMAGEM), validar_tamanho_imagem],
    )

    class Meta:
        verbose_name = "bicicleta"
        verbose_name_plural = "bicicletas"
        ordering = ["usuario__nome"]

    def __str__(self):
        return f"{self.marca} {self.modelo} — {self.usuario.nome}"


class DadosRepasse(models.Model):
    """Dados para recebimento dos repasses (RF05). Visíveis só ao dono e ao admin."""

    class TipoChave(models.TextChoices):
        CPF = "cpf", "CPF"
        EMAIL = "email", "E-mail"
        TELEFONE = "telefone", "Telefone"
        ALEATORIA = "aleatoria", "Chave aleatória"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dados_repasse",
        verbose_name="motorista",
    )
    titular = models.CharField("nome do titular", max_length=150)
    tipo_chave_pix = models.CharField(
        "tipo da chave Pix", max_length=10, choices=TipoChave.choices
    )
    chave_pix = models.CharField("chave Pix", max_length=100)
    banco = models.CharField("banco", max_length=60, blank=True)
    agencia = models.CharField("agência", max_length=10, blank=True)
    conta = models.CharField("conta", max_length=20, blank=True)

    class Meta:
        verbose_name = "dados de repasse"
        verbose_name_plural = "dados de repasse"
        ordering = ["usuario__nome"]

    def __str__(self):
        return f"Repasse de {self.usuario.nome}"

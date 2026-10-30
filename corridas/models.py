from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StatusCorrida(models.TextChoices):
    """Etapas da corrida, na ordem obrigatória (RN04)."""

    SOLICITADA = "solicitada", "Solicitada"
    ACEITA = "aceita", "Aceita"
    A_CAMINHO = "a_caminho", "Motorista a caminho"
    CHEGOU = "chegou", "Motorista chegou"
    EM_ANDAMENTO = "em_andamento", "Em andamento"
    FINALIZADA = "finalizada", "Finalizada"
    CANCELADA = "cancelada", "Cancelada"


# Corrida "ativa" = ainda não terminou. Usado por RN02 e RN09.
STATUS_ATIVOS = [
    StatusCorrida.SOLICITADA,
    StatusCorrida.ACEITA,
    StatusCorrida.A_CAMINHO,
    StatusCorrida.CHEGOU,
    StatusCorrida.EM_ANDAMENTO,
]

LATITUDE = [MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))]
LONGITUDE = [MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))]
NAO_NEGATIVO = [MinValueValidator(Decimal("0"))]


class Configuracao(models.Model):
    """Tarifas e parâmetros de despacho configuráveis pelo administrador. Registro único."""

    tarifa_base = models.DecimalField(
        "tarifa base (R$)", max_digits=8, decimal_places=2, default=Decimal("10.00"),
        validators=NAO_NEGATIVO,
    )
    valor_km = models.DecimalField(
        "valor por km (R$)", max_digits=8, decimal_places=2, default=Decimal("3.00"),
        validators=NAO_NEGATIVO,
    )
    percentual_plataforma = models.DecimalField(
        "comissão da plataforma (%)", max_digits=5, decimal_places=2, default=Decimal("20.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    raio_oferta_km = models.DecimalField(
        "raio de oferta (km)", max_digits=5, decimal_places=1, default=Decimal("10.0"),
        validators=[MinValueValidator(Decimal("0.1"))],
        help_text="Motoristas mais longe que isso da coleta não recebem a oferta.",
    )
    motoristas_por_oferta = models.PositiveSmallIntegerField(
        "motoristas por oferta", default=3, validators=[MinValueValidator(1)],
        help_text="Quantos motoristas mais próximos veem cada solicitação ao mesmo tempo.",
    )
    atualizada_em = models.DateTimeField("atualizada em", auto_now=True)

    class Meta:
        verbose_name = "configuração de tarifas"
        verbose_name_plural = "configuração de tarifas"

    def __str__(self):
        return "Configuração de tarifas"

    def save(self, *args, **kwargs):
        self.pk = 1  # sempre o mesmo registro
        super().save(*args, **kwargs)

    @classmethod
    def atual(cls):
        return cls.objects.get_or_create(pk=1)[0]


class Corrida(models.Model):
    Status = StatusCorrida

    class FormaPagamento(models.TextChoices):
        PIX = "pix", "Pix"
        CARTAO = "cartao", "Cartão"

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="corridas_como_cliente", verbose_name="cliente",
    )
    motorista = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="corridas_como_motorista", verbose_name="motorista",
    )
    # O veículo pode ser removido depois; a descrição e a placa ficam guardadas.
    veiculo = models.ForeignKey(
        "veiculos.Veiculo", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="corridas", verbose_name="veículo",
    )
    veiculo_descricao = models.CharField("veículo", max_length=150)
    veiculo_placa = models.CharField("placa", max_length=7)

    origem_endereco = models.CharField("coleta", max_length=255)
    origem_latitude = models.DecimalField(max_digits=9, decimal_places=6, validators=LATITUDE)
    origem_longitude = models.DecimalField(max_digits=9, decimal_places=6, validators=LONGITUDE)
    destino_endereco = models.CharField("destino", max_length=255)
    destino_latitude = models.DecimalField(max_digits=9, decimal_places=6, validators=LATITUDE)
    destino_longitude = models.DecimalField(max_digits=9, decimal_places=6, validators=LONGITUDE)

    # Valores usados no cálculo, gravados separadamente (RNF09): mudar a
    # configuração depois não altera corridas já pedidas.
    distancia_km = models.DecimalField("distância (km)", max_digits=7, decimal_places=2)
    tarifa_base = models.DecimalField("tarifa base (R$)", max_digits=8, decimal_places=2)
    valor_km = models.DecimalField("valor por km (R$)", max_digits=8, decimal_places=2)
    percentual_plataforma = models.DecimalField(
        "comissão da plataforma (%)", max_digits=5, decimal_places=2
    )
    preco_estimado = models.DecimalField("preço estimado (R$)", max_digits=10, decimal_places=2)
    forma_pagamento = models.CharField(
        "forma de pagamento", max_length=10, choices=FormaPagamento.choices
    )

    status = models.CharField(
        "status", max_length=15, choices=Status.choices, default=Status.SOLICITADA
    )
    codigo_confirmacao = models.CharField("código de confirmação", max_length=4)
    tentativas_codigo = models.PositiveSmallIntegerField("tentativas erradas do código", default=0)
    cancelada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="cancelada por",
    )
    motivo_cancelamento = models.TextField("motivo do cancelamento", blank=True)
    criada_em = models.DateTimeField("solicitada em", default=timezone.now)
    atualizada_em = models.DateTimeField("atualizada em", auto_now=True)

    class Meta:
        verbose_name = "corrida"
        verbose_name_plural = "corridas"
        ordering = ["-criada_em"]
        constraints = [
            # Última barreira, no próprio banco, mesmo sob concorrência:
            models.UniqueConstraint(  # RN09
                fields=["cliente"], condition=Q(status__in=STATUS_ATIVOS),
                name="uma_corrida_ativa_por_cliente",
            ),
            models.UniqueConstraint(  # RN02
                fields=["motorista"], condition=Q(status__in=STATUS_ATIVOS),
                name="uma_corrida_ativa_por_motorista",
            ),
        ]

    def __str__(self):
        return f"Corrida #{self.pk} — {self.get_status_display()}"

    @property
    def ativa(self):
        return self.status in STATUS_ATIVOS


class EventoCorrida(models.Model):
    """Registro de cada mudança de status, com data, hora e autor (RNF09)."""

    corrida = models.ForeignKey(Corrida, on_delete=models.CASCADE, related_name="eventos")
    status_anterior = models.CharField(
        "de", max_length=15, choices=StatusCorrida.choices, blank=True
    )
    status_novo = models.CharField("para", max_length=15, choices=StatusCorrida.choices)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+",
        verbose_name="autor",
    )
    observacao = models.TextField("observação", blank=True)
    criado_em = models.DateTimeField("em", default=timezone.now)

    class Meta:
        verbose_name = "evento da corrida"
        verbose_name_plural = "eventos da corrida"
        ordering = ["criado_em", "id"]

    def __str__(self):
        return f"{self.get_status_anterior_display() or '—'} → {self.get_status_novo_display()}"


class RecusaCorrida(models.Model):
    """Motorista que recusou a oferta: não a vê mais, e ela passa ao próximo (RF12)."""

    corrida = models.ForeignKey(Corrida, on_delete=models.CASCADE, related_name="recusas")
    motorista = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    criada_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "recusa"
        verbose_name_plural = "recusas"
        constraints = [
            models.UniqueConstraint(fields=["corrida", "motorista"], name="recusa_unica")
        ]

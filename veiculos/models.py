from datetime import date

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models


def _ano_maximo():
    return date.today().year + 1


class Veiculo(models.Model):
    """Carro do cliente que será conduzido pelo motorista (RF02)."""

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="veiculos",
        verbose_name="cliente",
    )
    marca = models.CharField("marca", max_length=50)
    modelo = models.CharField("modelo", max_length=60)
    cor = models.CharField("cor", max_length=30)
    ano = models.PositiveSmallIntegerField(
        "ano",
        validators=[MinValueValidator(1980), MaxValueValidator(_ano_maximo())],
    )
    placa = models.CharField(
        "placa",
        max_length=7,
        validators=[
            RegexValidator(
                r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$",
                "Placa inválida. Use o formato ABC1234 ou ABC1D23.",
            )
        ],
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "veículo"
        verbose_name_plural = "veículos"
        ordering = ["marca", "modelo"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "placa"], name="veiculo_placa_unica_por_cliente"
            )
        ]

    def __str__(self):
        return f"{self.marca} {self.modelo} ({self.placa})"

    def save(self, *args, **kwargs):
        self.placa = self.placa.upper()
        super().save(*args, **kwargs)

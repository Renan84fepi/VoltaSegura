from django.contrib import admin

from .models import Veiculo


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("placa", "marca", "modelo", "cor", "ano", "cliente")
    search_fields = ("placa", "marca", "modelo", "cliente__nome", "cliente__email")
    list_select_related = ("cliente",)

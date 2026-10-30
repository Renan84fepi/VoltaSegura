from django.contrib import admin

from .models import Configuracao, Corrida, EventoCorrida


@admin.register(Configuracao)
class ConfiguracaoAdmin(admin.ModelAdmin):
    list_display = (
        "__str__", "tarifa_base", "valor_km", "percentual_plataforma",
        "raio_oferta_km", "motoristas_por_oferta", "atualizada_em",
    )

    def has_add_permission(self, request):
        return not Configuracao.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class EventoInline(admin.TabularInline):
    model = EventoCorrida
    extra = 0
    can_delete = False
    fields = ("criado_em", "status_anterior", "status_novo", "autor", "observacao")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Corrida)
class CorridaAdmin(admin.ModelAdmin):
    """Somente consulta: o status só muda pelas regras do sistema (RN04)."""

    list_display = (
        "id", "criada_em", "cliente", "motorista", "status", "distancia_km", "preco_estimado",
        "forma_pagamento",
    )
    list_filter = ("status", "forma_pagamento", "criada_em")
    search_fields = (
        "cliente__nome", "cliente__email", "motorista__nome", "motorista__email", "veiculo_placa",
    )
    list_select_related = ("cliente", "motorista")
    date_hierarchy = "criada_em"
    inlines = [EventoInline]

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

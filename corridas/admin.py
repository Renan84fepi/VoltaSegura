from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from . import regras
from .models import Avaliacao, Configuracao, Corrida, EventoCorrida, EventoPagamento, Pagamento


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

    @admin.display(description="pagamento")
    def ver_pagamento(self, obj):
        pagamento = getattr(obj, "pagamento", None)
        if pagamento is None:
            return "—"
        url = reverse("admin:corridas_pagamento_change", args=[pagamento.pk])
        return format_html('<a href="{}">{}</a>', url, pagamento.get_status_display())

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields] + ["ver_pagamento"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False



class EventoPagamentoInline(admin.TabularInline):
    model = EventoPagamento
    extra = 0
    can_delete = False
    fields = ("criado_em", "status_anterior", "status_novo", "autor", "observacao")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    """RF29: consulta com filtros. O status só muda pelas regras.

    Estorno (RF21): botão "Estornar" na página de um pagamento aprovado, ou a
    ação em lote na lista.
    """

    change_form_template = "admin/corridas/pagamento/change_form.html"

    list_display = (
        "corrida", "criado_em", "cliente", "motorista", "forma", "valor_total",
        "taxa_plataforma", "valor_motorista", "status",
    )
    list_filter = ("status", "forma", "criado_em")
    search_fields = (
        "corrida__id", "transacao", "corrida__cliente__nome", "corrida__cliente__email",
        "corrida__motorista__nome", "corrida__motorista__email",
    )
    list_select_related = ("corrida__cliente", "corrida__motorista")
    date_hierarchy = "criado_em"
    inlines = [EventoPagamentoInline]
    actions = ["estornar"]

    @admin.display(description="cliente", ordering="corrida__cliente__nome")
    def cliente(self, obj):
        return obj.corrida.cliente.nome

    @admin.display(description="motorista", ordering="corrida__motorista__nome")
    def motorista(self, obj):
        return obj.corrida.motorista.nome if obj.corrida.motorista_id else "—"

    def get_urls(self):
        rota = path(
            "<int:pk>/estornar/", self.admin_site.admin_view(self.estornar_view),
            name="corridas_pagamento_estornar",
        )
        return [rota, *super().get_urls()]

    def estornar_view(self, request, pk):
        """Confirmação com motivo; o POST chama a mesma regra da ação em lote."""
        if not self.has_change_permission(request):
            raise PermissionDenied
        pagamento = get_object_or_404(Pagamento.objects.select_related("corrida"), pk=pk)
        voltar = reverse("admin:corridas_pagamento_change", args=[pk])
        if request.method == "POST":
            motivo = request.POST.get("motivo", "").strip() or "Estorno pela administração"
            try:
                regras.estornar(pk, request.user, motivo)
                self.message_user(request, "Pagamento estornado (simulado).", messages.SUCCESS)
            except regras.RegraViolada as erro:
                self.message_user(request, erro.mensagem, messages.ERROR)
            return redirect(voltar)
        contexto = {
            **self.admin_site.each_context(request),
            "title": f"Estornar o pagamento da corrida #{pagamento.corrida_id}",
            "pagamento": pagamento,
            "opts": self.model._meta,
            "voltar": voltar,
        }
        return TemplateResponse(request, "admin/corridas/pagamento/estornar.html", contexto)

    @admin.action(description="Estornar pagamentos aprovados selecionados (simulado)")
    def estornar(self, request, queryset):
        estornados = 0
        for pagamento in queryset:
            try:
                regras.estornar(pagamento.pk, request.user)
                estornados += 1
            except regras.RegraViolada as erro:
                self.message_user(
                    request, f"Corrida #{pagamento.corrida_id}: {erro.mensagem}", messages.WARNING
                )
        if estornados:
            self.message_user(request, f"{estornados} pagamento(s) estornado(s).", messages.SUCCESS)

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("corrida", "motorista", "nota", "comentario", "criada_em")
    list_filter = ("nota", "criada_em")
    search_fields = ("motorista__nome", "motorista__email", "comentario")
    list_select_related = ("motorista",)

    def get_readonly_fields(self, request, obj=None):
        return [campo.name for campo in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

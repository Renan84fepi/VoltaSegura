from django.contrib import admin, messages
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import AprovacaoMixin, Bicicleta, DadosRepasse, PerfilMotorista

Status = AprovacaoMixin.Status


class AvaliacaoAdminMixin:
    """Registra quem aprovou/rejeitou ao salvar pelo formulário do admin."""

    def save_model(self, request, obj, form, change):
        if "status_aprovacao" in form.changed_data and obj.status_aprovacao != Status.PENDENTE:
            obj.avaliado_por = request.user
            obj.avaliado_em = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(PerfilMotorista)
class PerfilMotoristaAdmin(AvaliacaoAdminMixin, admin.ModelAdmin):
    list_display = (
        "usuario",
        "cnh_numero",
        "cnh_validade",
        "cnh_ok",
        "status_aprovacao",
        "bicicleta_situacao",
        "enviado_em",
    )
    list_filter = ("status_aprovacao",)
    search_fields = ("usuario__nome", "usuario__email", "cnh_numero")
    list_select_related = ("usuario",)
    readonly_fields = ("ver_documento", "avaliado_por", "avaliado_em", "enviado_em", "atualizado_em")
    actions = ["aprovar", "rejeitar"]

    @admin.display(boolean=True, description="CNH válida")
    def cnh_ok(self, obj):
        return obj.cnh_valida

    @admin.display(description="Bicicleta")
    def bicicleta_situacao(self, obj):
        bicicleta = getattr(obj.usuario, "bicicleta", None)
        return bicicleta.get_status_aprovacao_display() if bicicleta else "Não cadastrada"

    @admin.display(description="Documento de identidade")
    def ver_documento(self, obj):
        if not obj.pk or not obj.documento_identidade:
            return "—"
        url = reverse("motoristas:arquivo", args=["documento", obj.usuario_id])
        return format_html('<a href="{}" target="_blank" rel="noopener">Abrir imagem</a>', url)

    @admin.action(description="Aprovar motoristas selecionados")
    def aprovar(self, request, queryset):
        aprovados = 0
        for perfil in queryset.select_related("usuario"):
            if not perfil.cnh_valida:
                self.message_user(
                    request,
                    f"{perfil.usuario.nome}: CNH vencida — não aprovado.",
                    messages.ERROR,
                )
                continue
            perfil.aprovar(request.user)
            aprovados += 1
        if aprovados:
            self.message_user(request, f"{aprovados} motorista(s) aprovado(s).", messages.SUCCESS)

    @admin.action(description="Rejeitar motoristas selecionados")
    def rejeitar(self, request, queryset):
        for perfil in queryset:
            perfil.rejeitar(request.user)
        self.message_user(
            request,
            f"{queryset.count()} motorista(s) rejeitado(s). Edite o registro para detalhar o motivo.",
            messages.WARNING,
        )


@admin.register(Bicicleta)
class BicicletaAdmin(AvaliacaoAdminMixin, admin.ModelAdmin):
    list_display = ("usuario", "marca", "modelo", "cor", "status_aprovacao")
    list_filter = ("status_aprovacao",)
    search_fields = ("usuario__nome", "usuario__email", "marca", "modelo")
    list_select_related = ("usuario",)
    readonly_fields = ("ver_foto", "avaliado_por", "avaliado_em")
    actions = ["aprovar", "rejeitar"]

    @admin.display(description="Foto")
    def ver_foto(self, obj):
        if not obj.pk or not obj.foto:
            return "—"
        url = reverse("motoristas:arquivo", args=["bicicleta", obj.usuario_id])
        return format_html('<a href="{}" target="_blank" rel="noopener">Abrir imagem</a>', url)

    @admin.action(description="Aprovar bicicletas selecionadas")
    def aprovar(self, request, queryset):
        for bicicleta in queryset:
            bicicleta.aprovar(request.user)
        self.message_user(request, f"{queryset.count()} bicicleta(s) aprovada(s).", messages.SUCCESS)

    @admin.action(description="Rejeitar bicicletas selecionadas")
    def rejeitar(self, request, queryset):
        for bicicleta in queryset:
            bicicleta.rejeitar(request.user)
        self.message_user(
            request,
            f"{queryset.count()} bicicleta(s) rejeitada(s). Edite o registro para detalhar o motivo.",
            messages.WARNING,
        )


@admin.register(DadosRepasse)
class DadosRepasseAdmin(admin.ModelAdmin):
    list_display = ("usuario", "titular", "tipo_chave_pix", "banco")
    search_fields = ("usuario__nome", "usuario__email", "titular")
    list_select_related = ("usuario",)

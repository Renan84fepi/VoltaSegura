from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm

from .models import Usuario


class UsuarioCriacaoAdminForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("email", "nome", "telefone", "perfil")


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    add_form = UsuarioCriacaoAdminForm
    ordering = ("nome",)
    list_display = ("nome", "email", "telefone", "perfil", "bloqueado", "is_active")
    list_filter = ("perfil", "bloqueado", "is_active")
    search_fields = ("nome", "email", "telefone")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados pessoais", {"fields": ("nome", "telefone", "perfil")}),
        (
            "Acesso",
            {
                "fields": (
                    "bloqueado",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nome", "telefone", "perfil", "password1", "password2"),
            },
        ),
    )
    actions = ["bloquear", "desbloquear"]

    @admin.action(description="Bloquear usuários selecionados")
    def bloquear(self, request, queryset):
        queryset = queryset.exclude(pk=request.user.pk)  # não bloquear a si mesmo
        total = queryset.update(bloqueado=True)
        self.message_user(request, f"{total} usuário(s) bloqueado(s).", messages.SUCCESS)

    @admin.action(description="Desbloquear usuários selecionados")
    def desbloquear(self, request, queryset):
        total = queryset.update(bloqueado=False)
        self.message_user(request, f"{total} usuário(s) desbloqueado(s).", messages.SUCCESS)

from django.contrib.auth.backends import ModelBackend


class BackendSemBloqueados(ModelBackend):
    """Impede login (e sessões já abertas) de usuários bloqueados."""

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and not user.bloqueado

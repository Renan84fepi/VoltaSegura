from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms


class PerfilRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restringe a view a um perfil. Anônimo vai ao login; outro perfil recebe 403."""

    perfil_requerido = None

    def test_func(self):
        return self.request.user.perfil == self.perfil_requerido


class BootstrapFormMixin:
    """Aplica classes do Bootstrap 5 a todos os campos do formulário."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                classe = "form-check-input"
            elif isinstance(widget, forms.Select):
                classe = "form-select"
            else:
                classe = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {classe}".strip()

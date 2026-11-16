from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms


class PerfilRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restringe a view a um perfil. Anônimo vai ao login; outro perfil recebe 403."""

    perfil_requerido = None

    def test_func(self):
        return self.request.user.perfil == self.perfil_requerido


class RadioCartoes(forms.RadioSelect):
    """RadioSelect com a classe só nos inputs; em attrs ela iria também para a div do grupo."""

    def create_option(self, *args, **kwargs):
        opcao = super().create_option(*args, **kwargs)
        opcao["attrs"]["class"] = "form-check-input"
        return opcao


class BootstrapFormMixin:
    """Aplica classes do Bootstrap 5 a todos os campos do formulário."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, forms.RadioSelect):
                continue  # use RadioCartoes
            if isinstance(widget, forms.CheckboxInput):
                classe = "form-check-input"
            elif isinstance(widget, forms.Select):
                classe = "form-select"
            else:
                classe = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {classe}".strip()

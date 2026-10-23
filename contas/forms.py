import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .mixins import BootstrapFormMixin
from .models import Usuario


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()

    def clean(self):
        email = self.cleaned_data.get("username")
        senha = self.cleaned_data.get("password")
        if email and senha:
            usuario = Usuario.objects.filter(email=email).first()
            # Só revela o bloqueio a quem acertou a senha.
            if usuario and usuario.bloqueado and usuario.check_password(senha):
                raise forms.ValidationError(
                    "Sua conta está bloqueada. Entre em contato com a administração.",
                    code="bloqueado",
                )
        return super().clean()


class CadastroForm(BootstrapFormMixin, UserCreationForm):
    perfil = forms.ChoiceField(
        label="Como você vai usar o VoltaSegura?",
        choices=[
            (Usuario.Perfil.CLIENTE, "Quero pedir corridas (cliente)"),
            (Usuario.Perfil.MOTORISTA, "Quero dirigir (motorista)"),
        ],
        widget=forms.RadioSelect,
        initial=Usuario.Perfil.CLIENTE,
    )

    # Sobrescrito para aceitar máscara "(35) 99999-1234"; os dígitos são extraídos em clean_telefone.
    telefone = forms.CharField(
        label="Telefone", max_length=20, help_text="Com DDD.",
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel"}),
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("nome", "email", "telefone")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_telefone(self):
        return re.sub(r"\D", "", self.cleaned_data["telefone"])

    def save(self, commit=True):
        usuario = super().save(commit=False)
        # Nunca confiar em perfil administrativo vindo do formulário.
        usuario.perfil = self.cleaned_data["perfil"]
        if commit:
            usuario.save()
        return usuario

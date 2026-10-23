import re
import uuid

from django import forms
from django.core.validators import EmailValidator
from django.utils import timezone

from contas.mixins import BootstrapFormMixin

from .models import Bicicleta, DadosRepasse, PerfilMotorista
from .validators import validar_cpf


class ReenvioResetaAprovacaoMixin:
    """Se um cadastro já avaliado for alterado, volta para 'pendente'."""

    def save(self, commit=True):
        if self.instance.pk and self.has_changed():
            self.instance.resetar_aprovacao()
        return super().save(commit)


class DocumentosForm(ReenvioResetaAprovacaoMixin, BootstrapFormMixin, forms.ModelForm):
    # Aceita pontuação; os dígitos são extraídos em clean_cnh_numero.
    cnh_numero = forms.CharField(
        label="Número da CNH", max_length=20, widget=forms.TextInput(attrs={"inputmode": "numeric"})
    )

    class Meta:
        model = PerfilMotorista
        fields = ("documento_identidade", "cnh_numero", "cnh_validade")
        widgets = {
            "documento_identidade": forms.FileInput(attrs={"accept": "image/*"}),
            "cnh_validade": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean_cnh_numero(self):
        return re.sub(r"\D", "", self.cleaned_data["cnh_numero"])

    def clean_cnh_validade(self):
        validade = self.cleaned_data["cnh_validade"]
        if validade < timezone.localdate():
            raise forms.ValidationError("A CNH está vencida. Envie uma CNH válida.")
        return validade


class BicicletaForm(ReenvioResetaAprovacaoMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Bicicleta
        fields = ("marca", "modelo", "cor", "foto")
        widgets = {"foto": forms.FileInput(attrs={"accept": "image/*"})}


class RepasseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DadosRepasse
        fields = ("titular", "tipo_chave_pix", "chave_pix", "banco", "agencia", "conta")

    def clean(self):
        dados = super().clean()
        tipo = dados.get("tipo_chave_pix")
        chave = (dados.get("chave_pix") or "").strip()
        if not tipo or not chave:
            return dados
        try:
            if tipo == DadosRepasse.TipoChave.CPF:
                chave = re.sub(r"\D", "", chave)
                validar_cpf(chave)
            elif tipo == DadosRepasse.TipoChave.EMAIL:
                chave = chave.lower()
                EmailValidator()(chave)
            elif tipo == DadosRepasse.TipoChave.TELEFONE:
                chave = re.sub(r"\D", "", chave)
                if not re.fullmatch(r"\d{10,11}", chave):
                    raise forms.ValidationError("Informe DDD + número.")
            else:
                chave = str(uuid.UUID(chave))
        except forms.ValidationError as erro:
            self.add_error("chave_pix", erro.messages[0])
            return dados
        except ValueError:
            self.add_error("chave_pix", "Chave aleatória inválida (esperado um UUID).")
            return dados
        dados["chave_pix"] = chave
        return dados

import re

from django import forms

from contas.mixins import BootstrapFormMixin

from .models import Veiculo


class VeiculoForm(BootstrapFormMixin, forms.ModelForm):
    # Aceita "ABC-1234"; o hífen é removido em clean_placa.
    placa = forms.CharField(
        label="Placa", max_length=8, widget=forms.TextInput(attrs={"placeholder": "ABC1D23"})
    )

    class Meta:
        model = Veiculo
        fields = ("marca", "modelo", "cor", "ano", "placa")

    def __init__(self, *args, cliente, **kwargs):
        super().__init__(*args, **kwargs)
        self.cliente = cliente

    def clean_placa(self):
        placa = re.sub(r"[\s-]", "", self.cleaned_data["placa"]).upper()
        repetida = Veiculo.objects.filter(cliente=self.cliente, placa=placa)
        if self.instance.pk:
            repetida = repetida.exclude(pk=self.instance.pk)
        if repetida.exists():
            raise forms.ValidationError("Você já cadastrou um veículo com esta placa.")
        return placa

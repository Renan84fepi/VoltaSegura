from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from contas.mixins import PerfilRequeridoMixin
from contas.models import Usuario

from . import regras
from .models import Corrida


class ClienteMixin(PerfilRequeridoMixin):
    perfil_requerido = Usuario.Perfil.CLIENTE


class Solicitar(ClienteMixin, TemplateView):
    """Tela C2/C3: coleta, destino, veículo, pagamento e estimativa."""

    template_name = "corridas/solicitar.html"

    def get(self, request, *args, **kwargs):
        ativa = regras.corrida_ativa_do_cliente(request.user)
        if ativa:  # RN09: com corrida ativa, o cliente vai direto acompanhá-la
            return redirect("corridas:acompanhar", ativa.pk)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["veiculos"] = self.request.user.veiculos.all()
        contexto["formas_pagamento"] = Corrida.FormaPagamento.choices
        return contexto


class Acompanhar(ClienteMixin, TemplateView):
    """Tela C4: os dados vêm da API por polling (RF18)."""

    template_name = "corridas/acompanhar.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["corrida"] = get_object_or_404(
            Corrida, pk=self.kwargs["pk"], cliente=self.request.user
        )
        return contexto

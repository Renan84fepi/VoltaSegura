from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView, TemplateView

from contas.mixins import PerfilRequeridoMixin
from contas.models import Usuario

from . import regras
from .models import Corrida
from .serializers import PeriodoSerializer


class ClienteMixin(PerfilRequeridoMixin):
    perfil_requerido = Usuario.Perfil.CLIENTE


class MotoristaMixin(PerfilRequeridoMixin):
    perfil_requerido = Usuario.Perfil.MOTORISTA


class ParteMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Cliente ou motorista (o administrador consulta tudo pelo admin)."""

    def test_func(self):
        usuario = self.request.user
        return usuario.eh_cliente or usuario.eh_motorista


class Solicitar(ClienteMixin, TemplateView):
    """Tela C2/C3: coleta, destino, veículo, pagamento e estimativa."""

    template_name = "corridas/solicitar.html"

    def get(self, request, *args, **kwargs):
        ativa = regras.corrida_ativa_do_cliente(request.user)
        if ativa:  # RN09: com corrida ativa, o cliente vai direto acompanhá-la
            return redirect("corridas:acompanhar", ativa.pk)
        em_aberto = regras.pagamento_em_aberto_do_cliente(request.user)
        if em_aberto:  # paga a corrida anterior antes de pedir outra
            messages.warning(request, "Pague a corrida anterior antes de pedir outra.")
            return redirect("corridas:acompanhar", em_aberto.corrida_id)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["veiculos"] = self.request.user.veiculos.all()
        contexto["formas_pagamento"] = Corrida.FormaPagamento.choices
        return contexto


class Acompanhar(ClienteMixin, TemplateView):
    """Tela C4: os dados vêm da API por polling (RF18). Depois de finalizada,
    a mesma tela mostra o pagamento (RF21) e a avaliação (RF23)."""

    template_name = "corridas/acompanhar.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["corrida"] = get_object_or_404(
            Corrida, pk=self.kwargs["pk"], cliente=self.request.user
        )
        contexto["simulador"] = settings.DEBUG  # botão de simular pagamento recusado
        return contexto


class Historico(ParteMixin, ListView):
    """RF25: corridas do cliente ou do motorista logado."""

    template_name = "corridas/historico.html"
    context_object_name = "corridas"
    paginate_by = 20

    def get_queryset(self):
        return regras.historico(self.request.user)


class Recibo(ParteMixin, DetailView):
    """RF22: recibo da corrida finalizada. Corrida de outra pessoa → 404 (RNF07)."""

    template_name = "corridas/recibo.html"
    context_object_name = "corrida"

    def get_object(self, queryset=None):
        corrida = get_object_or_404(regras.historico(self.request.user), pk=self.kwargs["pk"])
        if not hasattr(corrida, "pagamento"):
            raise Http404("Esta corrida não tem recibo.")
        return corrida

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        corrida = self.object
        contexto["pagamento"] = corrida.pagamento
        contexto["eventos_pagamento"] = corrida.pagamento.eventos.all()
        contexto["valor_km_total"] = corrida.preco_estimado - corrida.tarifa_base
        contexto["eh_motorista"] = self.request.user.pk == corrida.motorista_id
        return contexto


class Ganhos(MotoristaMixin, TemplateView):
    """RF22: ganhos do motorista por período."""

    template_name = "corridas/ganhos.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        filtro = PeriodoSerializer(data=self.request.GET)
        if filtro.is_valid():
            inicio, fim = filtro.datas()
        else:
            contexto["erro_filtro"] = "Datas inválidas. Use o calendário para escolher."
            inicio, fim = regras.periodo("7dias")
        try:
            contexto["ganhos"] = regras.ganhos(self.request.user, inicio, fim)
        except regras.RegraViolada as erro:
            contexto["erro_filtro"] = erro.mensagem
            contexto["ganhos"] = regras.ganhos(self.request.user, *regras.periodo("7dias"))
        contexto["periodo"] = self.request.GET.get("periodo", "" if self.request.GET.get("de") else "7dias")
        contexto["periodos"] = [("hoje", "Hoje"), ("7dias", "7 dias"), ("30dias", "30 dias"), ("mes", "Este mês")]
        contexto["nota"] = regras.nota_do_motorista(self.request.user)
        return contexto

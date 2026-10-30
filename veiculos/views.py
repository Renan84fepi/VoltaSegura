from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from contas.mixins import PerfilRequeridoMixin
from contas.models import Usuario

from .forms import VeiculoForm


class ClienteMixin(PerfilRequeridoMixin):
    perfil_requerido = Usuario.Perfil.CLIENTE
    success_url = reverse_lazy("veiculos:lista")

    def get_queryset(self):
        # Cada cliente só enxerga os próprios veículos (RNF07): de outro => 404.
        return self.request.user.veiculos.all()


class VeiculoLista(ClienteMixin, ListView):
    template_name = "veiculos/lista.html"
    context_object_name = "veiculos"


class VeiculoFormMixin(ClienteMixin):
    form_class = VeiculoForm
    template_name = "veiculos/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cliente"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.cliente = self.request.user
        resposta = super().form_valid(form)
        messages.success(self.request, "Veículo salvo com sucesso.")
        return resposta


class VeiculoCriar(VeiculoFormMixin, CreateView):
    pass


class VeiculoEditar(VeiculoFormMixin, UpdateView):
    pass


class VeiculoRemover(ClienteMixin, DeleteView):
    template_name = "veiculos/confirmar_remocao.html"

    def form_valid(self, form):
        from corridas.models import STATUS_ATIVOS

        if self.object.corridas.filter(status__in=STATUS_ATIVOS).exists():
            messages.error(self.request, "Este veículo está em uma corrida ativa e não pode ser removido.")
            return redirect("veiculos:lista")
        resposta = super().form_valid(form)
        messages.success(self.request, "Veículo removido.")
        return resposta

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from contas.mixins import PerfilRequeridoMixin
from contas.models import Usuario

from .forms import BicicletaForm, DocumentosForm, RepasseForm
from .models import Bicicleta, DadosRepasse, PerfilMotorista


class MotoristaMixin(PerfilRequeridoMixin):
    perfil_requerido = Usuario.Perfil.MOTORISTA


class Painel(MotoristaMixin, TemplateView):
    template_name = "motoristas/painel.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        contexto["perfil"] = PerfilMotorista.objects.filter(usuario=usuario).first()
        contexto["bicicleta"] = Bicicleta.objects.filter(usuario=usuario).first()
        contexto["repasse"] = DadosRepasse.objects.filter(usuario=usuario).first()
        return contexto


class EditarRegistroUnico(MotoristaMixin, UpdateView):
    """Cria ou edita o registro único (1 por motorista) de um modelo."""

    template_name = "motoristas/form.html"
    success_url = reverse_lazy("motoristas:painel")
    titulo = ""
    mensagem_sucesso = "Dados salvos."

    def get_object(self, queryset=None):
        modelo = self.model
        return modelo.objects.filter(usuario=self.request.user).first() or modelo(
            usuario=self.request.user
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = self.titulo
        return contexto

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, self.mensagem_sucesso)
        return resposta


class Documentos(EditarRegistroUnico):
    model = PerfilMotorista
    form_class = DocumentosForm
    titulo = "Documentos (identidade e CNH)"
    mensagem_sucesso = "Documentos enviados. Aguarde a aprovação da administração."


class BicicletaEditar(EditarRegistroUnico):
    model = Bicicleta
    form_class = BicicletaForm
    titulo = "Minha bicicleta elétrica dobrável"
    mensagem_sucesso = "Bicicleta enviada. Aguarde a aprovação da administração."


class Repasse(EditarRegistroUnico):
    model = DadosRepasse
    form_class = RepasseForm
    titulo = "Dados para recebimento (repasses)"
    mensagem_sucesso = "Dados de recebimento salvos."


@login_required
def arquivo_protegido(request, tipo, usuario_id):
    """Entrega documento/foto só ao dono e ao administrador (RNF07).

    Nas próximas etapas, as partes de uma corrida também poderão ver a foto
    da bicicleta do motorista.
    """
    usuario = request.user
    if not (usuario.pk == usuario_id or usuario.perfil == Usuario.Perfil.ADMINISTRADOR):
        raise PermissionDenied
    if tipo == "documento":
        campo = get_object_or_404(PerfilMotorista, usuario_id=usuario_id).documento_identidade
    elif tipo == "bicicleta":
        campo = get_object_or_404(Bicicleta, usuario_id=usuario_id).foto
    else:
        return redirect("home")
    resposta = FileResponse(campo.open("rb"))
    resposta["Cache-Control"] = "private, no-store"
    return resposta

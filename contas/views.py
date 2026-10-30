from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import CadastroForm
from .models import Usuario


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, "Conta criada com sucesso! Bem-vindo(a) ao VoltaSegura.")
        return redirect("home")
    return render(request, "contas/cadastro.html", {"form": form})


@login_required
def home(request):
    """Leva cada perfil para a sua tela inicial."""
    perfil = request.user.perfil
    if perfil == Usuario.Perfil.MOTORISTA:
        return redirect("motoristas:painel")
    if perfil == Usuario.Perfil.CLIENTE:
        return redirect("corridas:solicitar")
    return redirect("admin:index")

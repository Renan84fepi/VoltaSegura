"""API REST consumida pelo frontend (RNF10). Autenticação por sessão, com CSRF."""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import exception_handler

from . import regras
from . import serializers as s
from .models import Corrida
from .regras import RegraViolada


def tratar_excecao(exc, contexto):
    """Regra de negócio violada vira JSON {"detail": "..."} com o status adequado."""
    if isinstance(exc, RegraViolada):
        return Response({"detail": exc.mensagem}, status=exc.status_http)
    return exception_handler(exc, contexto)


class EhCliente(BasePermission):
    message = "Disponível apenas para clientes."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.eh_cliente


class EhMotorista(BasePermission):
    message = "Disponível apenas para motoristas."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.eh_motorista


class EhParte(BasePermission):
    message = "Disponível apenas para clientes e motoristas."

    def has_permission(self, request, view):
        usuario = request.user
        return usuario.is_authenticated and (usuario.eh_cliente or usuario.eh_motorista)


def _da_parte(request, pk):
    """Corrida de outra pessoa → 404, sem revelar que existe (RNF07)."""
    usuario = request.user
    return get_object_or_404(Corrida.objects.filter(Q(cliente=usuario) | Q(motorista=usuario)), pk=pk)


# ---------------------------------------------------------------- motorista

@api_view(["GET", "POST"])
@permission_classes([EhMotorista])
def disponibilidade(request):
    """GET: situação do motorista. POST {"online": true|false}: RF06 + RN01."""
    if request.method == "POST":
        entrada = s.DisponibilidadeSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        regras.alterar_disponibilidade(request.user, entrada.validated_data["online"])
    return Response(s.situacao_motorista(regras.situacao_motorista(request.user)))


@api_view(["POST"])
@permission_classes([EhMotorista])
def localizacao(request):
    """POST {"latitude", "longitude"}: RF07."""
    entrada = s.LocalizacaoSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    regras.registrar_localizacao(
        request.user,
        s.coordenada(entrada.validated_data["latitude"]),
        s.coordenada(entrada.validated_data["longitude"]),
    )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([EhMotorista])
def ofertas(request):
    """Solicitações oferecidas a este motorista, da mais antiga para a mais nova (RF11)."""
    return Response([s.oferta(c, d) for c, d in regras.ofertas_para(request.user)])


# ---------------------------------------------------------------- cliente

@api_view(["POST"])
@permission_classes([EhCliente])
def estimativa(request):
    """RF10: distância e preço antes de confirmar. Devolve as coordenadas resolvidas."""
    entrada = s.EstimativaSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    origem, destino = entrada.pontos()
    distancia, preco, _ = regras.estimar(origem[1], origem[2], destino[1], destino[2])
    return Response({
        "distancia_km": str(distancia),
        "preco_estimado": str(preco),
        "origem_latitude": str(origem[1]),
        "origem_longitude": str(origem[2]),
        "destino_latitude": str(destino[1]),
        "destino_longitude": str(destino[2]),
    })


@api_view(["POST"])
@permission_classes([EhCliente])
def solicitar(request):
    """RF08: cria a corrida (o preço é recalculado no servidor)."""
    entrada = s.SolicitacaoSerializer(data=request.data, cliente=request.user)
    entrada.is_valid(raise_exception=True)
    origem, destino = entrada.pontos()
    corrida = regras.solicitar(
        request.user,
        entrada.validated_data["veiculo"],
        origem,
        destino,
        entrada.validated_data["forma_pagamento"],
    )
    return Response(s.corrida(corrida, request.user), status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------- as duas partes

@api_view(["GET"])
@permission_classes([EhParte])
def corrida_ativa(request):
    usuario = request.user
    if usuario.eh_cliente:
        corrida = regras.corrida_ativa_do_cliente(usuario)
    else:
        corrida = regras.corrida_ativa_do_motorista(usuario)
    return Response({"corrida": s.corrida(corrida, usuario) if corrida else None})


@api_view(["GET"])
@permission_classes([EhParte])
def detalhe(request, pk):
    """Consultado por polling para acompanhar o status (RF18, RNF05)."""
    return Response(s.corrida(_da_parte(request, pk), request.user))


@api_view(["POST"])
@permission_classes([EhParte])
def cancelar(request, pk):
    entrada = s.CancelamentoSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    corrida = regras.cancelar(pk, request.user, entrada.validated_data["motivo"])
    return Response(s.corrida(corrida, request.user))


# ---------------------------------------------------------------- ações do motorista

@api_view(["POST"])
@permission_classes([EhMotorista])
def aceitar(request, pk):
    return Response(s.corrida(regras.aceitar(pk, request.user), request.user))


@api_view(["POST"])
@permission_classes([EhMotorista])
def recusar(request, pk):
    regras.recusar(pk, request.user)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([EhMotorista])
def iniciar(request, pk):
    """RN05: corpo {"codigo": "1234"}."""
    entrada = s.CodigoSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    corrida = regras.iniciar(pk, request.user, entrada.validated_data["codigo"])
    return Response(s.corrida(corrida, request.user))


def _acao_do_motorista(funcao):
    @api_view(["POST"])
    @permission_classes([EhMotorista])
    def view(request, pk):
        return Response(s.corrida(funcao(pk, request.user), request.user))

    return view


a_caminho = _acao_do_motorista(regras.ir_a_caminho)
chegou = _acao_do_motorista(regras.informar_chegada)
finalizar = _acao_do_motorista(regras.finalizar)

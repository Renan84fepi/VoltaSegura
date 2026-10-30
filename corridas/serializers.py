"""Entrada (validação) e saída (JSON) da API. A saída depende de quem pede (RNF07)."""
from decimal import Decimal

from django.urls import reverse
from rest_framework import serializers

from veiculos.models import Veiculo

from . import regras
from .geocodificacao import EnderecoNaoEncontrado, geocodificar
from .models import Corrida

Status = Corrida.Status


def coordenada(valor):
    """O GPS manda muitas casas; o banco guarda 6 (≈ 10 cm)."""
    return Decimal(str(round(valor, 6)))


# ---------------------------------------------------------------- entrada

class LocalizacaoSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class DisponibilidadeSerializer(serializers.Serializer):
    online = serializers.BooleanField()


class EstimativaSerializer(serializers.Serializer):
    """Coleta e destino. Sem coordenadas, o endereço é convertido (geopy)."""

    origem_endereco = serializers.CharField(max_length=255)
    origem_latitude = serializers.FloatField(min_value=-90, max_value=90, required=False, allow_null=True)
    origem_longitude = serializers.FloatField(min_value=-180, max_value=180, required=False, allow_null=True)
    destino_endereco = serializers.CharField(max_length=255)
    destino_latitude = serializers.FloatField(min_value=-90, max_value=90, required=False, allow_null=True)
    destino_longitude = serializers.FloatField(min_value=-180, max_value=180, required=False, allow_null=True)

    def validate(self, dados):
        for ponto in ("origem", "destino"):
            lat, lng = dados.get(f"{ponto}_latitude"), dados.get(f"{ponto}_longitude")
            if lat is None or lng is None:
                try:
                    lat, lng = geocodificar(dados[f"{ponto}_endereco"])
                except EnderecoNaoEncontrado as erro:
                    raise serializers.ValidationError({f"{ponto}_endereco": str(erro)})
            dados[f"{ponto}_latitude"] = coordenada(float(lat))
            dados[f"{ponto}_longitude"] = coordenada(float(lng))
        return dados

    def pontos(self):
        d = self.validated_data
        return (
            (d["origem_endereco"], d["origem_latitude"], d["origem_longitude"]),
            (d["destino_endereco"], d["destino_latitude"], d["destino_longitude"]),
        )


class SolicitacaoSerializer(EstimativaSerializer):
    veiculo = serializers.PrimaryKeyRelatedField(queryset=Veiculo.objects.none())
    forma_pagamento = serializers.ChoiceField(choices=Corrida.FormaPagamento.choices)

    def __init__(self, *args, cliente, **kwargs):
        super().__init__(*args, **kwargs)
        # Só aceita veículos do próprio cliente.
        self.fields["veiculo"].queryset = cliente.veiculos.all()


class CodigoSerializer(serializers.Serializer):
    codigo = serializers.RegexField(
        r"^\d{4}$", error_messages={"invalid": "Informe os 4 dígitos do código."}
    )


class CancelamentoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


# ---------------------------------------------------------------- saída

def _texto(valor):
    return None if valor is None else str(valor)


def situacao_motorista(dados):
    return {
        **dados,
        "latitude": _texto(dados["latitude"]),
        "longitude": _texto(dados["longitude"]),
        "localizacao_em": dados["localizacao_em"].isoformat() if dados["localizacao_em"] else None,
    }


def oferta(corrida, distancia_ate_coleta):
    """O que o motorista vê ANTES de aceitar: sem nome, telefone nem placa (RNF07)."""
    _, repasse = regras.dividir_valor(corrida.preco_estimado, corrida.percentual_plataforma)
    return {
        "id": corrida.pk,
        "origem_endereco": corrida.origem_endereco,
        "destino_endereco": corrida.destino_endereco,
        "distancia_km": str(corrida.distancia_km),
        "distancia_ate_coleta_km": str(distancia_ate_coleta),
        "valor_motorista": str(repasse),
        "forma_pagamento": corrida.get_forma_pagamento_display(),
        "veiculo": corrida.veiculo_descricao,
        "criada_em": corrida.criada_em.isoformat(),
    }


def corrida(corrida, usuario):
    """Corrida vista por uma das partes. O código só vai para o cliente."""
    posicao = regras.posicao_do_motorista(corrida)
    dados = {
        "id": corrida.pk,
        "status": corrida.status,
        "status_texto": corrida.get_status_display(),
        "origem_endereco": corrida.origem_endereco,
        "destino_endereco": corrida.destino_endereco,
        "distancia_km": str(corrida.distancia_km),
        "preco_estimado": str(corrida.preco_estimado),
        "forma_pagamento": corrida.get_forma_pagamento_display(),
        "veiculo": f"{corrida.veiculo_descricao} • {corrida.veiculo_placa}",
        "criada_em": corrida.criada_em.isoformat(),
        "motivo_cancelamento": corrida.motivo_cancelamento,
        "pode_cancelar": regras.pode_cancelar(corrida, usuario),
        "posicao_motorista": posicao and {
            "alvo": posicao["alvo"],
            "distancia_km": str(posicao["distancia_km"]),
            "atualizada_em": posicao["atualizada_em"].isoformat() if posicao["atualizada_em"] else None,
        },
        "eventos": [
            {"status": e.status_novo, "texto": e.get_status_novo_display(), "em": e.criado_em.isoformat()}
            for e in corrida.eventos.all()
        ],
    }
    if usuario.pk == corrida.cliente_id:
        mostra_codigo = corrida.status in (Status.ACEITA, Status.A_CAMINHO, Status.CHEGOU)
        dados["codigo_confirmacao"] = corrida.codigo_confirmacao if mostra_codigo else None
        dados["motorista"] = _motorista(corrida) if corrida.motorista_id else None
    else:
        _, repasse = regras.dividir_valor(corrida.preco_estimado, corrida.percentual_plataforma)
        dados["valor_motorista"] = str(repasse)
        dados["cliente"] = {"nome": corrida.cliente.nome, "telefone": corrida.cliente.telefone}
        dados["tentativas_restantes"] = regras.MAX_TENTATIVAS_CODIGO - corrida.tentativas_codigo
        # Coordenadas do alvo, usadas pelo simulador de posição em desenvolvimento.
        dados["origem"] = [str(corrida.origem_latitude), str(corrida.origem_longitude)]
        dados["destino"] = [str(corrida.destino_latitude), str(corrida.destino_longitude)]
    return dados


def _motorista(corrida):
    motorista = corrida.motorista
    bicicleta = getattr(motorista, "bicicleta", None)
    return {
        "nome": motorista.nome,
        "telefone": motorista.telefone,
        "bicicleta": f"{bicicleta.marca} {bicicleta.modelo} ({bicicleta.cor})" if bicicleta else None,
        "foto_bicicleta": (
            reverse("motoristas:arquivo", args=["bicicleta", motorista.pk]) if bicicleta else None
        ),
    }

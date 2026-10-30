"""Regras de negócio da disponibilidade e das corridas.

As views (páginas e API) só chamam estas funções; nenhuma regra fica na view.
Toda mudança de status passa por `_mudar_status`, que valida a sequência (RN04)
e registra o evento (RNF09).
"""
import secrets
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from geopy.distance import geodesic

from motoristas.models import AprovacaoMixin, PerfilMotorista, impedimentos_online

from .models import STATUS_ATIVOS, Configuracao, Corrida, EventoCorrida, RecusaCorrida

Status = Corrida.Status
Aprovacao = AprovacaoMixin.Status

CENTAVO = Decimal("0.01")
VALIDADE_LOCALIZACAO = timedelta(minutes=2)  # posição mais antiga não conta para ofertas
MAX_TENTATIVAS_CODIGO = 5
DISTANCIA_MINIMA_KM = Decimal("0.10")
DISTANCIA_MAXIMA_KM = Decimal("300")

# RN04: de cada status, para onde a corrida pode ir. Qualquer outra mudança
# (pular ou voltar etapa) é recusada. Finalizada e cancelada são estados finais.
TRANSICOES = {
    Status.SOLICITADA: {Status.ACEITA, Status.CANCELADA},
    Status.ACEITA: {Status.A_CAMINHO, Status.CANCELADA},
    Status.A_CAMINHO: {Status.CHEGOU, Status.CANCELADA},
    Status.CHEGOU: {Status.EM_ANDAMENTO, Status.CANCELADA},
    Status.EM_ANDAMENTO: {Status.FINALIZADA},
}

# RF17 (regra da dupla): ninguém cancela "em andamento", pois o carro já está
# sendo conduzido; o motorista só cancela depois de aceitar, e com motivo.
CANCELAVEL_PELO_CLIENTE = {Status.SOLICITADA, Status.ACEITA, Status.A_CAMINHO, Status.CHEGOU}
CANCELAVEL_PELO_MOTORISTA = {Status.ACEITA, Status.A_CAMINHO, Status.CHEGOU}


class RegraViolada(Exception):
    """Ação recusada por regra de negócio. A API devolve `mensagem` com `status_http`."""

    def __init__(self, mensagem, status_http=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status_http = status_http


# ---------------------------------------------------------------- cálculos

def distancia_km(lat1, lng1, lat2, lng2):
    """Distância geodésica (em linha reta sobre a Terra) em km, com 2 casas."""
    km = geodesic((float(lat1), float(lng1)), (float(lat2), float(lng2))).km
    return Decimal(str(km)).quantize(CENTAVO, ROUND_HALF_UP)


def estimar_preco(distancia, tarifa_base, valor_km):
    """RN06: tarifa base + valor por km × distância."""
    return (tarifa_base + valor_km * distancia).quantize(CENTAVO, ROUND_HALF_UP)


def dividir_valor(total, percentual):
    """RN07/RN08: (plataforma, motorista). O motorista fica com a diferença,
    então a soma sempre fecha o total. Ex.: 85,00 a 20% → 17,00 + 68,00."""
    plataforma = (total * percentual / 100).quantize(CENTAVO, ROUND_HALF_UP)
    return plataforma, total - plataforma


def estimar(origem_lat, origem_lng, destino_lat, destino_lng):
    distancia = distancia_km(origem_lat, origem_lng, destino_lat, destino_lng)
    if distancia < DISTANCIA_MINIMA_KM:
        raise RegraViolada("Coleta e destino estão muito próximos.")
    if distancia > DISTANCIA_MAXIMA_KM:
        raise RegraViolada("Distância acima do limite atendido. Confira os endereços.")
    config = Configuracao.atual()
    preco = estimar_preco(distancia, config.tarifa_base, config.valor_km)
    return distancia, preco, config


# ---------------------------------------------------------------- consultas

def corrida_ativa_do_cliente(cliente):
    return Corrida.objects.filter(cliente=cliente, status__in=STATUS_ATIVOS).first()


def corrida_ativa_do_motorista(motorista):
    return Corrida.objects.filter(motorista=motorista, status__in=STATUS_ATIVOS).first()


def pode_cancelar(corrida, usuario):
    if usuario.pk == corrida.cliente_id:
        return corrida.status in CANCELAVEL_PELO_CLIENTE
    if usuario.pk == corrida.motorista_id:
        return corrida.status in CANCELAVEL_PELO_MOTORISTA
    return False


def posicao_do_motorista(corrida):
    """Distância do motorista até a coleta (antes de iniciar) ou até o destino (RF13)."""
    if corrida.status in (Status.ACEITA, Status.A_CAMINHO, Status.CHEGOU):
        alvo, lat, lng = "coleta", corrida.origem_latitude, corrida.origem_longitude
    elif corrida.status == Status.EM_ANDAMENTO:
        alvo, lat, lng = "destino", corrida.destino_latitude, corrida.destino_longitude
    else:
        return None
    perfil = PerfilMotorista.objects.filter(usuario_id=corrida.motorista_id).first()
    if perfil is None or perfil.latitude is None:
        return None
    return {
        "alvo": alvo,
        "distancia_km": distancia_km(perfil.latitude, perfil.longitude, lat, lng),
        "atualizada_em": perfil.localizacao_em,
    }


# ---------------------------------------------------------------- disponibilidade

def situacao_motorista(motorista):
    """Online, motivos de impedimento (RN01) e corrida ativa do motorista."""
    perfil = PerfilMotorista.objects.filter(usuario=motorista).first()
    impedimentos = impedimentos_online(motorista, perfil)
    if perfil and perfil.online and impedimentos:
        # Perdeu a elegibilidade estando online (ex.: CNH venceu, foi rejeitado).
        perfil.online = False
        perfil.save(update_fields=["online"])
    corrida = corrida_ativa_do_motorista(motorista)
    return {
        "online": bool(perfil and perfil.online),
        "pode_ficar_online": not impedimentos,
        "impedimentos": impedimentos,
        "latitude": perfil.latitude if perfil else None,
        "longitude": perfil.longitude if perfil else None,
        "localizacao_em": perfil.localizacao_em if perfil else None,
        "corrida_ativa": corrida.pk if corrida else None,
    }


@transaction.atomic
def alterar_disponibilidade(motorista, online):
    """RF06 + RN01."""
    perfil = PerfilMotorista.objects.select_for_update().filter(usuario=motorista).first()
    if online:
        impedimentos = impedimentos_online(motorista, perfil)
        if impedimentos:
            raise RegraViolada(" ".join(impedimentos), 403)
    elif corrida_ativa_do_motorista(motorista):
        raise RegraViolada("Finalize ou cancele a corrida atual antes de ficar offline.", 409)
    if perfil is not None:
        perfil.online = online
        perfil.save(update_fields=["online"])


def registrar_localizacao(motorista, latitude, longitude):
    """RF07: só registra enquanto online ou em corrida (privacidade fora do expediente)."""
    perfil = PerfilMotorista.objects.filter(usuario=motorista).first()
    if perfil is None or not (perfil.online or corrida_ativa_do_motorista(motorista)):
        raise RegraViolada("Fique online para compartilhar sua localização.", 409)
    perfil.latitude = latitude
    perfil.longitude = longitude
    perfil.localizacao_em = timezone.now()
    perfil.save(update_fields=["latitude", "longitude", "localizacao_em"])


# ---------------------------------------------------------------- despacho

def motoristas_elegiveis():
    """Quem pode receber ofertas agora: RN01 + online + posição recente + sem corrida ativa (RN02)."""
    return (
        PerfilMotorista.objects.filter(
            online=True,
            status_aprovacao=Aprovacao.APROVADO,
            cnh_validade__gte=timezone.localdate(),
            usuario__bicicleta__status_aprovacao=Aprovacao.APROVADO,
            usuario__bloqueado=False,
            usuario__is_active=True,
            latitude__isnull=False,
            localizacao_em__gte=timezone.now() - VALIDADE_LOCALIZACAO,
        )
        .exclude(usuario__corridas_como_motorista__status__in=STATUS_ATIVOS)
        .select_related("usuario")
    )


def _mais_proximos(corrida, elegiveis, config):
    """RF11: os N elegíveis mais próximos da coleta, dentro do raio, sem quem recusou."""
    recusaram = {recusa.motorista_id for recusa in corrida.recusas.all()}
    candidatos = []
    for perfil in elegiveis:
        if perfil.usuario_id in recusaram:
            continue
        distancia = distancia_km(
            perfil.latitude, perfil.longitude, corrida.origem_latitude, corrida.origem_longitude
        )
        if distancia <= config.raio_oferta_km:
            candidatos.append((distancia, perfil.usuario_id))
    candidatos.sort()
    return candidatos[: config.motoristas_por_oferta]


def ofertas_para(motorista):
    """Corridas solicitadas oferecidas a este motorista: [(corrida, distância até a coleta)]."""
    elegiveis = list(motoristas_elegiveis())
    if motorista.pk not in {perfil.usuario_id for perfil in elegiveis}:
        return []
    config = Configuracao.atual()
    pendentes = (
        Corrida.objects.filter(status=Status.SOLICITADA)
        .exclude(recusas__motorista=motorista)
        .prefetch_related("recusas")
        .order_by("criada_em")
    )
    ofertas = []
    for corrida in pendentes:
        for distancia, usuario_id in _mais_proximos(corrida, elegiveis, config):
            if usuario_id == motorista.pk:
                ofertas.append((corrida, distancia))
                break
    return ofertas


# ---------------------------------------------------------------- ciclo da corrida

def _travar(corrida_id):
    """Lê a corrida com SELECT ... FOR UPDATE: quem chegar depois espera na fila."""
    corrida = Corrida.objects.select_for_update().filter(pk=corrida_id).first()
    if corrida is None:
        raise RegraViolada("Corrida não encontrada.", 404)
    return corrida


def _mudar_status(corrida, novo, autor, observacao=""):
    """Única forma de mudar o status (RN04), sempre registrando o evento (RNF09)."""
    if novo not in TRANSICOES.get(corrida.status, set()):
        raise RegraViolada(
            f"Não é possível passar de “{corrida.get_status_display()}” "
            f"para “{Status(novo).label}”.",
            409,
        )
    anterior = corrida.status
    corrida.status = novo
    corrida.save()
    EventoCorrida.objects.create(
        corrida=corrida, status_anterior=anterior, status_novo=novo,
        autor=autor, observacao=observacao,
    )


def solicitar(cliente, veiculo, origem, destino, forma_pagamento):
    """RF08–RF10. `origem`/`destino` = (endereço, latitude, longitude).

    O preço é recalculado aqui: o valor mostrado no navegador nunca é confiado.
    """
    if veiculo.cliente_id != cliente.pk:
        raise RegraViolada("Escolha um dos seus veículos.")
    if corrida_ativa_do_cliente(cliente):
        raise RegraViolada("Você já tem uma corrida ativa.", 409)  # RN09
    distancia, preco, config = estimar(origem[1], origem[2], destino[1], destino[2])
    try:
        with transaction.atomic():
            corrida = Corrida.objects.create(
                cliente=cliente,
                veiculo=veiculo,
                veiculo_descricao=f"{veiculo.marca} {veiculo.modelo} {veiculo.cor}",
                veiculo_placa=veiculo.placa,
                origem_endereco=origem[0],
                origem_latitude=origem[1],
                origem_longitude=origem[2],
                destino_endereco=destino[0],
                destino_latitude=destino[1],
                destino_longitude=destino[2],
                distancia_km=distancia,
                tarifa_base=config.tarifa_base,
                valor_km=config.valor_km,
                percentual_plataforma=config.percentual_plataforma,
                preco_estimado=preco,
                forma_pagamento=forma_pagamento,
                codigo_confirmacao=f"{secrets.randbelow(10000):04d}",  # RF15
            )
            EventoCorrida.objects.create(
                corrida=corrida, status_novo=Status.SOLICITADA, autor=cliente
            )
    except IntegrityError:
        # Dois pedidos simultâneos do mesmo cliente: o índice único barrou (RN09).
        raise RegraViolada("Você já tem uma corrida ativa.", 409)
    return corrida


def aceitar(corrida_id, motorista):
    """RF12 + RN02 + RN03/RNF06."""
    with transaction.atomic():
        # 1º trava o motorista: dois aceites dele ao mesmo tempo ficam em fila (RN02).
        perfil = PerfilMotorista.objects.select_for_update().filter(usuario=motorista).first()
        if perfil is None or not perfil.online or impedimentos_online(motorista, perfil):
            raise RegraViolada("Fique online para aceitar corridas.", 403)
        if corrida_ativa_do_motorista(motorista):
            raise RegraViolada("Você já tem uma corrida ativa.", 409)
        # 2º trava a corrida: o segundo motorista espera o primeiro terminar e
        # então lê o status já atualizado (RN03).
        corrida = _travar(corrida_id)
        if corrida.status != Status.SOLICITADA:
            raise RegraViolada("Esta corrida já foi aceita por outro motorista ou cancelada.", 409)
        if corrida.pk not in {c.pk for c, _ in ofertas_para(motorista)}:
            raise RegraViolada("Esta corrida não está disponível para você.", 403)
        corrida.motorista = motorista
        _mudar_status(corrida, Status.ACEITA, motorista)
    return corrida


def recusar(corrida_id, motorista):
    corrida = Corrida.objects.filter(pk=corrida_id, status=Status.SOLICITADA).first()
    if corrida is None:
        raise RegraViolada("Esta corrida não está mais disponível.", 409)
    RecusaCorrida.objects.get_or_create(corrida=corrida, motorista=motorista)


def _acao_do_motorista(corrida_id, motorista, novo):
    with transaction.atomic():
        corrida = _travar(corrida_id)
        if corrida.motorista_id != motorista.pk:
            raise RegraViolada("Corrida não encontrada.", 404)
        _mudar_status(corrida, novo, motorista)
    return corrida


def ir_a_caminho(corrida_id, motorista):
    return _acao_do_motorista(corrida_id, motorista, Status.A_CAMINHO)


def informar_chegada(corrida_id, motorista):  # RF14
    return _acao_do_motorista(corrida_id, motorista, Status.CHEGOU)


def finalizar(corrida_id, motorista):  # RF16
    return _acao_do_motorista(corrida_id, motorista, Status.FINALIZADA)


def iniciar(corrida_id, motorista, codigo):
    """RN05: só passa para "em andamento" com o código correto do cliente."""
    with transaction.atomic():
        corrida = _travar(corrida_id)
        if corrida.motorista_id != motorista.pk:
            raise RegraViolada("Corrida não encontrada.", 404)
        if corrida.status != Status.CHEGOU:
            _mudar_status(corrida, Status.EM_ANDAMENTO, motorista)  # levanta o erro de sequência
        if corrida.tentativas_codigo >= MAX_TENTATIVAS_CODIGO:
            raise RegraViolada(
                "Limite de tentativas do código atingido. Confirme com o cliente ou cancele.", 403
            )
        if secrets.compare_digest(codigo, corrida.codigo_confirmacao):
            _mudar_status(corrida, Status.EM_ANDAMENTO, motorista)
            return corrida
        corrida.tentativas_codigo += 1
        corrida.save(update_fields=["tentativas_codigo", "atualizada_em"])
        restantes = MAX_TENTATIVAS_CODIGO - corrida.tentativas_codigo
    # Fora do bloco atômico: a tentativa errada fica gravada mesmo com o erro.
    raise RegraViolada(f"Código incorreto. Restam {restantes} tentativa(s).")


def cancelar(corrida_id, usuario, motivo=""):
    """RF17, com as regras de CANCELAVEL_PELO_CLIENTE / CANCELAVEL_PELO_MOTORISTA."""
    motivo = motivo.strip()
    with transaction.atomic():
        corrida = _travar(corrida_id)
        if usuario.pk not in (corrida.cliente_id, corrida.motorista_id):
            raise RegraViolada("Corrida não encontrada.", 404)
        if usuario.pk == corrida.motorista_id and not motivo:
            raise RegraViolada("Informe o motivo do cancelamento.")
        if not pode_cancelar(corrida, usuario):
            if corrida.status == Status.EM_ANDAMENTO:
                raise RegraViolada("A corrida já começou: ela só pode ser finalizada no destino.", 409)
            raise RegraViolada("Esta corrida não pode ser cancelada agora.", 409)
        corrida.cancelada_por = usuario
        corrida.motivo_cancelamento = motivo
        _mudar_status(corrida, Status.CANCELADA, usuario, motivo)
    return corrida

import threading
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import count

import pytest
from django.db import IntegrityError, connection
from django.urls import reverse
from django.utils import timezone

from conftest import gerar_imagem
from contas.models import Usuario
from motoristas.models import Bicicleta, PerfilMotorista
from veiculos.models import Veiculo

from . import regras
from .geocodificacao import EnderecoNaoEncontrado, geocodificar
from .models import Configuracao, Corrida, EventoCorrida
from .regras import RegraViolada

pytestmark = pytest.mark.django_db
Status = Corrida.Status

CENTRO = (Decimal("-22.230600"), Decimal("-45.935600"))  # coleta padrão
DESTINO = (Decimal("-22.265000"), Decimal("-45.900000"))
_seq = count(1)


# ---------------------------------------------------------------- fábricas

def criar_motorista(
    posicao=CENTRO, online=True, aprovado=True, bicicleta=True, bike_aprovada=True,
    validade=None, minutos_atras=0,
):
    n = next(_seq)
    usuario = Usuario.objects.create_user(
        f"mot{n}@t.com", "Senha-forte-123", nome=f"Motorista {n}", telefone="35988880000",
        perfil=Usuario.Perfil.MOTORISTA,
    )
    status = PerfilMotorista.Status.APROVADO if aprovado else PerfilMotorista.Status.PENDENTE
    PerfilMotorista.objects.create(
        usuario=usuario, documento_identidade=gerar_imagem(), cnh_numero="01234567890",
        cnh_validade=validade or timezone.localdate() + timedelta(days=365),
        status_aprovacao=status, online=online,
        latitude=posicao[0], longitude=posicao[1],
        localizacao_em=timezone.now() - timedelta(minutes=minutos_atras),
    )
    if bicicleta:
        Bicicleta.objects.create(
            usuario=usuario, marca="Dobrix", modelo="Mini", cor="Cinza", foto=gerar_imagem(),
            status_aprovacao=Bicicleta.Status.APROVADO if bike_aprovada else Bicicleta.Status.PENDENTE,
        )
    return usuario


def criar_cliente():
    n = next(_seq)
    usuario = Usuario.objects.create_user(
        f"cli{n}@t.com", "Senha-forte-123", nome=f"Cliente {n}", telefone="35977770000",
        perfil=Usuario.Perfil.CLIENTE,
    )
    Veiculo.objects.create(
        cliente=usuario, marca="VW", modelo="Gol", cor="Preto", ano=2018, placa=f"ABC{1000 + n}"
    )
    return usuario


def pedir(cliente, origem=CENTRO, destino=DESTINO):
    return regras.solicitar(
        cliente, cliente.veiculos.first(), ("Centro", *origem), ("Destino", *destino), "pix"
    )


def ate(status_final, cliente=None, motorista=None):
    """Leva uma corrida nova até `status_final` pelo caminho válido."""
    cliente = cliente or criar_cliente()
    motorista = motorista or criar_motorista()
    corrida = pedir(cliente)
    passos = [
        (Status.ACEITA, lambda: regras.aceitar(corrida.pk, motorista)),
        (Status.A_CAMINHO, lambda: regras.ir_a_caminho(corrida.pk, motorista)),
        (Status.CHEGOU, lambda: regras.informar_chegada(corrida.pk, motorista)),
        (Status.EM_ANDAMENTO, lambda: regras.iniciar(corrida.pk, motorista, corrida.codigo_confirmacao)),
        (Status.FINALIZADA, lambda: regras.finalizar(corrida.pk, motorista)),
    ]
    if status_final != Status.SOLICITADA:
        for status, passo in passos:
            passo()
            if status == status_final:
                break
    corrida.refresh_from_db()
    return corrida, cliente, motorista


# ---------------------------------------------------------------- RN06 / RN08: valores

def test_preco_segue_a_formula_configuravel():
    config = Configuracao.atual()
    config.tarifa_base, config.valor_km = Decimal("5.00"), Decimal("2.50")
    config.save()
    distancia, preco, _ = regras.estimar(*CENTRO, *DESTINO)
    assert preco == (Decimal("5.00") + Decimal("2.50") * distancia).quantize(Decimal("0.01"), ROUND_HALF_UP)
    assert Decimal("5") < distancia < Decimal("6")  # ≈ 5,2 km em linha reta


def test_distancia_geodesica():
    # 1 grau de longitude no equador ≈ 111,32 km
    assert regras.distancia_km(0, 0, 0, 1) == Decimal("111.32")


def test_divisao_do_exemplo_de_referencia():
    assert regras.dividir_valor(Decimal("85.00"), Decimal("20")) == (Decimal("17.00"), Decimal("68.00"))


def test_divisao_sempre_fecha_o_total():
    plataforma, motorista = regras.dividir_valor(Decimal("33.33"), Decimal("20"))
    assert plataforma + motorista == Decimal("33.33")


def test_corrida_guarda_copia_das_tarifas():
    corrida = pedir(criar_cliente())
    config = Configuracao.atual()
    config.valor_km = Decimal("99.00")
    config.save()
    corrida.refresh_from_db()
    assert corrida.valor_km == Decimal("3.00")


def test_coleta_e_destino_iguais_sao_recusados():
    with pytest.raises(RegraViolada):
        pedir(criar_cliente(), destino=CENTRO)


# ---------------------------------------------------------------- RN09

def test_cliente_nao_pede_segunda_corrida_ativa():
    cliente = criar_cliente()
    pedir(cliente)
    with pytest.raises(RegraViolada) as erro:
        pedir(cliente)
    assert erro.value.status_http == 409


def test_cliente_pode_pedir_de_novo_apos_cancelar():
    corrida, cliente, _ = ate(Status.SOLICITADA)
    regras.cancelar(corrida.pk, cliente)
    assert pedir(cliente).status == Status.SOLICITADA


def test_banco_tambem_impede_duas_corridas_ativas():
    corrida = pedir(criar_cliente())
    corrida.pk = None
    with pytest.raises(IntegrityError):
        corrida.save()


# ---------------------------------------------------------------- RN01: online

@pytest.mark.parametrize(
    "dados",
    [
        {"aprovado": False},
        {"bicicleta": False},
        {"bike_aprovada": False},
        {"validade": timezone.localdate() - timedelta(days=1)},
    ],
)
def test_online_recusado_sem_requisitos(dados):
    motorista = criar_motorista(online=False, **dados)
    with pytest.raises(RegraViolada):
        regras.alterar_disponibilidade(motorista, True)
    assert not PerfilMotorista.objects.get(usuario=motorista).online


def test_online_recusado_para_bloqueado():
    motorista = criar_motorista(online=False)
    motorista.bloqueado = True
    motorista.save()
    with pytest.raises(RegraViolada):
        regras.alterar_disponibilidade(motorista, True)


def test_online_aceito_com_cnh_vencendo_hoje():
    motorista = criar_motorista(online=False, validade=timezone.localdate())
    regras.alterar_disponibilidade(motorista, True)
    assert PerfilMotorista.objects.get(usuario=motorista).online


def test_api_lista_motivos_do_impedimento(client):
    motorista = criar_motorista(online=False, aprovado=False)
    client.force_login(motorista)
    resposta = client.post(
        reverse("api:disponibilidade"), {"online": True}, content_type="application/json"
    )
    assert resposta.status_code == 403
    assert "aprovação" in resposta.json()["detail"]
    situacao = client.get(reverse("api:disponibilidade")).json()
    assert situacao["online"] is False
    assert situacao["impedimentos"] == ["Seus documentos aguardam aprovação."]


def test_perde_online_quando_cnh_vence():
    motorista = criar_motorista()
    PerfilMotorista.objects.filter(usuario=motorista).update(
        cnh_validade=timezone.localdate() - timedelta(days=1)
    )
    assert regras.situacao_motorista(motorista)["online"] is False


def test_nao_fica_offline_com_corrida_ativa():
    _, _, motorista = ate(Status.ACEITA)
    with pytest.raises(RegraViolada):
        regras.alterar_disponibilidade(motorista, False)


def test_localizacao_so_e_registrada_online():
    motorista = criar_motorista(online=False)
    with pytest.raises(RegraViolada):
        regras.registrar_localizacao(motorista, Decimal("-22.1"), Decimal("-45.1"))


def test_api_registra_localizacao(client):
    motorista = criar_motorista()
    client.force_login(motorista)
    resposta = client.post(
        reverse("api:localizacao"),
        {"latitude": -22.123456789, "longitude": -45.987654321},
        content_type="application/json",
    )
    assert resposta.status_code == 204
    perfil = PerfilMotorista.objects.get(usuario=motorista)
    assert perfil.latitude == Decimal("-22.123457")


# ---------------------------------------------------------------- RF11: despacho

def ofertados(motorista):
    return [c.pk for c, _ in regras.ofertas_para(motorista)]


def test_oferta_vai_aos_mais_proximos_dentro_do_raio():
    config = Configuracao.atual()
    config.motoristas_por_oferta = 2
    config.save()
    perto = criar_motorista(posicao=(Decimal("-22.2310"), Decimal("-45.9360")))
    medio = criar_motorista(posicao=(Decimal("-22.2400"), Decimal("-45.9400")))
    terceiro = criar_motorista(posicao=(Decimal("-22.2500"), Decimal("-45.9500")))
    longe = criar_motorista(posicao=(Decimal("-22.5000"), Decimal("-45.9356")))  # ~30 km
    corrida = pedir(criar_cliente())
    assert ofertados(perto) == [corrida.pk]
    assert ofertados(medio) == [corrida.pk]
    assert ofertados(terceiro) == []  # fora dos 2 mais próximos
    assert ofertados(longe) == []  # fora do raio

    # Quem recusa sai da fila e a oferta passa ao próximo.
    regras.recusar(corrida.pk, perto)
    assert ofertados(perto) == []
    assert ofertados(terceiro) == [corrida.pk]


@pytest.mark.parametrize(
    "dados",
    [{"online": False}, {"minutos_atras": 5}, {"aprovado": False}, {"bike_aprovada": False}],
)
def test_inelegiveis_nao_recebem_oferta(dados):
    motorista = criar_motorista(**dados)
    pedir(criar_cliente())
    assert ofertados(motorista) == []


def test_motorista_em_corrida_nao_recebe_oferta():
    _, _, motorista = ate(Status.ACEITA)
    pedir(criar_cliente())
    assert ofertados(motorista) == []


def test_motorista_nao_aceita_corrida_que_nao_foi_oferecida():
    longe = criar_motorista(posicao=(Decimal("-22.5000"), Decimal("-45.9356")))
    corrida = pedir(criar_cliente())
    with pytest.raises(RegraViolada) as erro:
        regras.aceitar(corrida.pk, longe)
    assert erro.value.status_http == 403


def test_oferta_nao_expoe_dados_do_cliente(client):
    motorista = criar_motorista()
    corrida = pedir(criar_cliente())
    client.force_login(motorista)
    ofertas = client.get(reverse("api:ofertas")).json()
    assert [o["id"] for o in ofertas] == [corrida.pk]
    texto = str(ofertas)
    assert corrida.veiculo_placa not in texto
    assert corrida.cliente.telefone not in texto
    assert corrida.cliente.nome not in texto
    assert ofertas[0]["valor_motorista"] == str(regras.dividir_valor(corrida.preco_estimado, Decimal("20"))[1])


# ---------------------------------------------------------------- RN02 / RN03

def test_corrida_aceita_nao_pode_ser_aceita_por_outro():
    corrida, _, _ = ate(Status.ACEITA)
    outro = criar_motorista()
    with pytest.raises(RegraViolada) as erro:
        regras.aceitar(corrida.pk, outro)
    assert erro.value.status_http == 409


def test_motorista_com_corrida_ativa_nao_aceita_outra():
    _, _, motorista = ate(Status.ACEITA)
    nova = pedir(criar_cliente())
    with pytest.raises(RegraViolada):
        regras.aceitar(nova.pk, motorista)


def _ao_mesmo_tempo(*tarefas):
    """Roda as tarefas em threads liberadas juntas; devolve quantas deram certo."""
    barreira = threading.Barrier(len(tarefas))
    resultados = []

    def rodar(tarefa):
        try:
            barreira.wait()
            tarefa()
            resultados.append("ok")
        except RegraViolada:
            resultados.append("recusado")
        finally:
            connection.close()

    threads = [threading.Thread(target=rodar, args=(t,)) for t in tarefas]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return resultados


@pytest.mark.django_db(transaction=True)
def test_aceite_simultaneo_por_dois_motoristas():
    """RN03/RNF06: dois motoristas aceitam a mesma corrida no mesmo instante."""
    a, b = criar_motorista(), criar_motorista()
    corrida = pedir(criar_cliente())
    resultados = _ao_mesmo_tempo(
        lambda: regras.aceitar(corrida.pk, a), lambda: regras.aceitar(corrida.pk, b)
    )
    assert sorted(resultados) == ["ok", "recusado"]
    corrida.refresh_from_db()
    assert corrida.status == Status.ACEITA
    assert corrida.motorista in (a, b)
    assert corrida.eventos.filter(status_novo=Status.ACEITA).count() == 1


@pytest.mark.django_db(transaction=True)
def test_mesmo_motorista_aceitando_duas_corridas_ao_mesmo_tempo():
    """RN02: o motorista tenta pegar duas corridas no mesmo instante."""
    motorista = criar_motorista()
    c1, c2 = pedir(criar_cliente()), pedir(criar_cliente())
    resultados = _ao_mesmo_tempo(
        lambda: regras.aceitar(c1.pk, motorista), lambda: regras.aceitar(c2.pk, motorista)
    )
    assert sorted(resultados) == ["ok", "recusado"]
    assert Corrida.objects.filter(motorista=motorista).count() == 1


# ---------------------------------------------------------------- RN04: sequência

def test_fluxo_completo_registra_cada_etapa():
    corrida, _, _ = ate(Status.FINALIZADA)
    assert list(corrida.eventos.values_list("status_novo", flat=True)) == [
        Status.SOLICITADA, Status.ACEITA, Status.A_CAMINHO, Status.CHEGOU,
        Status.EM_ANDAMENTO, Status.FINALIZADA,
    ]
    assert all(e.criado_em for e in corrida.eventos.all())


def test_pular_etapa_e_bloqueado():
    corrida, _, motorista = ate(Status.ACEITA)
    with pytest.raises(RegraViolada):
        regras.informar_chegada(corrida.pk, motorista)  # aceita → chegou
    with pytest.raises(RegraViolada):
        regras.finalizar(corrida.pk, motorista)  # aceita → finalizada
    with pytest.raises(RegraViolada):
        regras.iniciar(corrida.pk, motorista, corrida.codigo_confirmacao)  # aceita → em andamento
    corrida.refresh_from_db()
    assert corrida.status == Status.ACEITA


def test_voltar_etapa_e_bloqueado():
    corrida, _, motorista = ate(Status.CHEGOU)
    with pytest.raises(RegraViolada):
        regras.ir_a_caminho(corrida.pk, motorista)
    corrida.refresh_from_db()
    assert corrida.status == Status.CHEGOU


def test_nada_muda_apos_finalizada():
    corrida, cliente, motorista = ate(Status.FINALIZADA)
    with pytest.raises(RegraViolada):
        regras.finalizar(corrida.pk, motorista)
    with pytest.raises(RegraViolada):
        regras.cancelar(corrida.pk, cliente)


def test_so_o_motorista_da_corrida_avanca():
    corrida, _, _ = ate(Status.ACEITA)
    with pytest.raises(RegraViolada) as erro:
        regras.ir_a_caminho(corrida.pk, criar_motorista())
    assert erro.value.status_http == 404


# ---------------------------------------------------------------- RN05: código

def test_codigo_errado_nao_inicia_e_conta_tentativa():
    corrida, _, motorista = ate(Status.CHEGOU)
    errado = "0000" if corrida.codigo_confirmacao != "0000" else "1111"
    with pytest.raises(RegraViolada) as erro:
        regras.iniciar(corrida.pk, motorista, errado)
    assert "Restam 4" in erro.value.mensagem
    corrida.refresh_from_db()
    assert corrida.status == Status.CHEGOU
    assert corrida.tentativas_codigo == 1


def test_codigo_correto_inicia():
    corrida, _, motorista = ate(Status.CHEGOU)
    regras.iniciar(corrida.pk, motorista, corrida.codigo_confirmacao)
    corrida.refresh_from_db()
    assert corrida.status == Status.EM_ANDAMENTO


def test_limite_de_tentativas_bloqueia_ate_o_codigo_certo():
    corrida, _, motorista = ate(Status.CHEGOU)
    errado = "0000" if corrida.codigo_confirmacao != "0000" else "1111"
    for _ in range(regras.MAX_TENTATIVAS_CODIGO):
        with pytest.raises(RegraViolada):
            regras.iniciar(corrida.pk, motorista, errado)
    with pytest.raises(RegraViolada):
        regras.iniciar(corrida.pk, motorista, corrida.codigo_confirmacao)
    corrida.refresh_from_db()
    assert corrida.status == Status.CHEGOU


def test_codigo_so_aparece_para_o_cliente(client):
    corrida, cliente, motorista = ate(Status.CHEGOU)
    url = reverse("api:corrida", args=[corrida.pk])
    client.force_login(motorista)
    assert "codigo_confirmacao" not in client.get(url).json()
    client.force_login(cliente)
    assert client.get(url).json()["codigo_confirmacao"] == corrida.codigo_confirmacao


# ---------------------------------------------------------------- RF17: cancelamento

def test_cliente_cancela_antes_de_iniciar():
    corrida, cliente, _ = ate(Status.CHEGOU)
    regras.cancelar(corrida.pk, cliente)
    corrida.refresh_from_db()
    assert corrida.status == Status.CANCELADA
    assert corrida.cancelada_por == cliente


def test_ninguem_cancela_corrida_em_andamento():
    corrida, cliente, motorista = ate(Status.EM_ANDAMENTO)
    with pytest.raises(RegraViolada):
        regras.cancelar(corrida.pk, cliente)
    with pytest.raises(RegraViolada):
        regras.cancelar(corrida.pk, motorista, "pneu furou")


def test_motorista_precisa_informar_motivo():
    corrida, _, motorista = ate(Status.ACEITA)
    with pytest.raises(RegraViolada):
        regras.cancelar(corrida.pk, motorista)
    regras.cancelar(corrida.pk, motorista, "Imprevisto")
    assert EventoCorrida.objects.get(corrida=corrida, status_novo=Status.CANCELADA).observacao == "Imprevisto"


def test_estranho_nao_cancela():
    corrida, _, _ = ate(Status.SOLICITADA)
    with pytest.raises(RegraViolada) as erro:
        regras.cancelar(corrida.pk, criar_cliente())
    assert erro.value.status_http == 404


# ---------------------------------------------------------------- API do cliente

def test_estimativa_e_solicitacao_pela_api(client):
    cliente = criar_cliente()
    client.force_login(cliente)
    pontos = {"origem_endereco": "-22.2306, -45.9356", "destino_endereco": "-22.2650, -45.9000"}
    estimativa = client.post(reverse("api:estimativa"), pontos, content_type="application/json")
    assert estimativa.status_code == 200
    assert estimativa.json()["preco_estimado"]

    pedido = client.post(
        reverse("api:solicitar"),
        {**pontos, "veiculo": cliente.veiculos.first().pk, "forma_pagamento": "pix",
         "preco_estimado": "0.01"},  # campo ignorado: o servidor recalcula
        content_type="application/json",
    )
    assert pedido.status_code == 201
    corrida = Corrida.objects.get()
    assert str(corrida.preco_estimado) == estimativa.json()["preco_estimado"]
    assert corrida.eventos.count() == 1


def test_solicitacao_com_veiculo_de_outro_cliente_e_recusada(client):
    cliente, outro = criar_cliente(), criar_cliente()
    client.force_login(cliente)
    resposta = client.post(
        reverse("api:solicitar"),
        {"origem_endereco": "-22.2306, -45.9356", "destino_endereco": "-22.2650, -45.9000",
         "veiculo": outro.veiculos.first().pk, "forma_pagamento": "pix"},
        content_type="application/json",
    )
    assert resposta.status_code == 400
    assert not Corrida.objects.exists()


def test_endereco_sem_geocodificacao_da_mensagem_clara(client):
    client.force_login(criar_cliente())
    resposta = client.post(
        reverse("api:estimativa"),
        {"origem_endereco": "Rua A, 10", "destino_endereco": "-22.2650, -45.9000"},
        content_type="application/json",
    )
    assert resposta.status_code == 400
    assert "origem_endereco" in resposta.json()


def test_geocodificacao_usa_o_geopy(settings, monkeypatch):
    settings.GEOCODIFICACAO_ATIVA = True

    class Local:
        latitude, longitude = -22.23, -45.93

    monkeypatch.setattr(
        "corridas.geocodificacao.Nominatim.geocode", lambda self, endereco, **kw: Local()
    )
    assert geocodificar("Praça Senador José Bento, Pouso Alegre") == (Decimal("-22.23"), Decimal("-45.93"))
    monkeypatch.setattr("corridas.geocodificacao.Nominatim.geocode", lambda self, endereco, **kw: None)
    with pytest.raises(EnderecoNaoEncontrado):
        geocodificar("Lugar que não existe")


def test_cliente_ve_dados_e_distancia_do_motorista(client):
    corrida, cliente, motorista = ate(Status.A_CAMINHO)
    client.force_login(cliente)
    dados = client.get(reverse("api:corrida", args=[corrida.pk])).json()
    assert dados["motorista"]["nome"] == motorista.nome
    assert dados["motorista"]["telefone"] == motorista.telefone
    assert dados["posicao_motorista"]["alvo"] == "coleta"
    assert dados["posicao_motorista"]["distancia_km"] == "0.00"


def test_corrida_de_outra_pessoa_retorna_404(client):
    corrida, _, _ = ate(Status.ACEITA)
    client.force_login(criar_cliente())
    assert client.get(reverse("api:corrida", args=[corrida.pk])).status_code == 404


def test_api_exige_perfil_certo(client):
    client.force_login(criar_cliente())
    assert client.get(reverse("api:ofertas")).status_code == 403
    client.force_login(criar_motorista())
    assert client.post(reverse("api:estimativa"), {}, content_type="application/json").status_code == 403


def test_api_exige_csrf():
    from django.test import Client

    cliente = criar_cliente()
    navegador = Client(enforce_csrf_checks=True)
    navegador.force_login(cliente)
    resposta = navegador.post(reverse("api:estimativa"), {}, content_type="application/json")
    assert resposta.status_code == 403


def test_api_fluxo_do_motorista(client):
    corrida = pedir(criar_cliente())
    motorista = criar_motorista()
    client.force_login(motorista)
    post = lambda nome, dados=None: client.post(
        reverse(f"api:{nome}", args=[corrida.pk]), dados or {}, content_type="application/json"
    )
    assert post("aceitar").json()["status"] == Status.ACEITA
    assert post("a-caminho").status_code == 200
    assert post("finalizar").status_code == 409  # pular etapa
    assert post("chegou").status_code == 200
    assert post("iniciar", {"codigo": "abc"}).status_code == 400
    assert post("iniciar", {"codigo": corrida.codigo_confirmacao}).json()["status"] == Status.EM_ANDAMENTO
    assert post("finalizar").json()["status"] == Status.FINALIZADA


# ---------------------------------------------------------------- páginas

def test_cliente_vai_para_solicitar_ou_acompanhar(client):
    cliente = criar_cliente()
    client.force_login(cliente)
    assert client.get(reverse("home")).url == reverse("corridas:solicitar")
    assert client.get(reverse("corridas:solicitar")).status_code == 200
    corrida = pedir(cliente)
    assert client.get(reverse("corridas:solicitar")).url == reverse("corridas:acompanhar", args=[corrida.pk])
    assert client.get(reverse("corridas:acompanhar", args=[corrida.pk])).status_code == 200


def test_motorista_nao_acessa_telas_do_cliente(client):
    client.force_login(criar_motorista())
    assert client.get(reverse("corridas:solicitar")).status_code == 403


def test_veiculo_em_corrida_ativa_nao_pode_ser_removido(client):
    corrida, cliente, _ = ate(Status.ACEITA)
    client.force_login(cliente)
    client.post(reverse("veiculos:remover", args=[corrida.veiculo_id]))
    assert Veiculo.objects.filter(pk=corrida.veiculo_id).exists()


def test_cliente_da_corrida_ve_foto_da_bicicleta(client):
    corrida, cliente, motorista = ate(Status.ACEITA)
    url_bike = reverse("motoristas:arquivo", args=["bicicleta", motorista.pk])
    url_doc = reverse("motoristas:arquivo", args=["documento", motorista.pk])
    client.force_login(cliente)
    assert client.get(url_bike).status_code == 200
    assert client.get(url_doc).status_code == 403  # documento continua restrito
    client.force_login(criar_cliente())
    assert client.get(url_bike).status_code == 403

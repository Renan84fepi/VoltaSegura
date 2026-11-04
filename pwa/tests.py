"""RNF01 (instalável) e RNF02 (offline)."""
import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_manifesto_tem_o_necessario_para_instalar(client):
    resposta = client.get(reverse("pwa:manifesto"))
    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "application/manifest+json"
    dados = resposta.json()
    assert dados["display"] == "standalone"
    assert dados["start_url"].startswith("/")
    tamanhos = {i["sizes"] for i in dados["icons"]}
    assert {"192x192", "512x512"} <= tamanhos
    assert any(i["purpose"] == "maskable" for i in dados["icons"])
    for icone in dados["icons"]:
        nome = icone["src"].removeprefix("/static/")
        assert finders.find(nome), f"ícone ausente: {nome}"


def test_service_worker_na_raiz(client):
    resposta = client.get(reverse("pwa:service-worker"))
    assert reverse("pwa:service-worker") == "/sw.js"  # escopo = site inteiro
    assert resposta.status_code == 200
    assert resposta["Content-Type"].startswith("application/javascript")
    assert "no-cache" in resposta["Cache-Control"]
    corpo = resposta.content.decode()
    assert reverse("pwa:offline") in corpo
    assert '"/api/"' in corpo  # a API nunca vai para o cache


def test_pagina_offline_e_publica(client):
    resposta = client.get(reverse("pwa:offline"))
    assert resposta.status_code == 200
    assert "sem conexão" in resposta.text.lower()


def test_paginas_apontam_para_o_manifesto(client, cliente):
    client.force_login(cliente)
    html = client.get(reverse("veiculos:lista")).text
    assert reverse("pwa:manifesto") in html
    assert "pwa/pwa.js" in html

from django.urls import path

from . import api

app_name = "api"

urlpatterns = [
    path("motorista/disponibilidade/", api.disponibilidade, name="disponibilidade"),
    path("motorista/localizacao/", api.localizacao, name="localizacao"),
    path("motorista/ofertas/", api.ofertas, name="ofertas"),
    path("motorista/ganhos/", api.ganhos, name="ganhos"),
    path("motorista/nota/", api.minha_nota, name="nota"),
    path("corridas/", api.solicitar, name="solicitar"),
    path("corridas/estimativa/", api.estimativa, name="estimativa"),
    path("corridas/ativa/", api.corrida_ativa, name="corrida-ativa"),
    path("corridas/historico/", api.historico, name="historico"),
    path("corridas/<int:pk>/", api.detalhe, name="corrida"),
    path("corridas/<int:pk>/aceitar/", api.aceitar, name="aceitar"),
    path("corridas/<int:pk>/recusar/", api.recusar, name="recusar"),
    path("corridas/<int:pk>/a-caminho/", api.a_caminho, name="a-caminho"),
    path("corridas/<int:pk>/chegou/", api.chegou, name="chegou"),
    path("corridas/<int:pk>/iniciar/", api.iniciar, name="iniciar"),
    path("corridas/<int:pk>/finalizar/", api.finalizar, name="finalizar"),
    path("corridas/<int:pk>/cancelar/", api.cancelar, name="cancelar"),
    path("corridas/<int:pk>/pagar/", api.pagar, name="pagar"),
    path("corridas/<int:pk>/avaliar/", api.avaliar, name="avaliar"),
]

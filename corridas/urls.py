from django.urls import path

from . import views

app_name = "corridas"

urlpatterns = [
    path("nova/", views.Solicitar.as_view(), name="solicitar"),
    path("historico/", views.Historico.as_view(), name="historico"),
    path("ganhos/", views.Ganhos.as_view(), name="ganhos"),
    path("<int:pk>/", views.Acompanhar.as_view(), name="acompanhar"),
    path("<int:pk>/recibo/", views.Recibo.as_view(), name="recibo"),
]

from django.urls import path

from . import views

app_name = "motoristas"

urlpatterns = [
    path("", views.Painel.as_view(), name="painel"),
    path("documentos/", views.Documentos.as_view(), name="documentos"),
    path("bicicleta/", views.BicicletaEditar.as_view(), name="bicicleta"),
    path("repasse/", views.Repasse.as_view(), name="repasse"),
    path("arquivo/<str:tipo>/<int:usuario_id>/", views.arquivo_protegido, name="arquivo"),
]

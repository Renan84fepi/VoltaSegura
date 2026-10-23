from django.urls import path

from . import views

app_name = "veiculos"

urlpatterns = [
    path("", views.VeiculoLista.as_view(), name="lista"),
    path("novo/", views.VeiculoCriar.as_view(), name="novo"),
    path("<int:pk>/editar/", views.VeiculoEditar.as_view(), name="editar"),
    path("<int:pk>/remover/", views.VeiculoRemover.as_view(), name="remover"),
]

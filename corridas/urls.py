from django.urls import path

from . import views

app_name = "corridas"

urlpatterns = [
    path("nova/", views.Solicitar.as_view(), name="solicitar"),
    path("<int:pk>/", views.Acompanhar.as_view(), name="acompanhar"),
]

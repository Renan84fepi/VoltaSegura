from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "VoltaSegura — Administração"
admin.site.site_title = "VoltaSegura"
admin.site.index_title = "Painel administrativo"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("veiculos/", include("veiculos.urls")),
    path("motorista/", include("motoristas.urls")),
    path("corridas/", include("corridas.urls")),
    path("api/", include("corridas.api_urls")),
    path("", include("contas.urls")),
]

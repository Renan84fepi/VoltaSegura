"""PWA (RNF01, RNF02): manifesto, service worker e página offline.

O service worker é servido na raiz (/sw.js) para controlar o site inteiro;
servido em /static/ ele só alcançaria /static/.
"""
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control

# Mude ao alterar os arquivos guardados no cache: o navegador troca o cache antigo.
VERSAO_CACHE = "m4-5"


def manifesto(request):
    return JsonResponse(
        {
            "name": "VoltaSegura",
            "short_name": "VoltaSegura",
            "description": "Um motorista conduz o seu carro até o destino e volta de bicicleta elétrica.",
            "lang": "pt-BR",
            "start_url": reverse("home") + "?origem=app",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait",
            "background_color": "#f4f6fb",
            "theme_color": "#f4f6fb",
            "icons": [
                {"src": static("pwa/icone-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": static("pwa/icone-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
                {"src": static("pwa/icone-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
            ],
        },
        content_type="application/manifest+json",
        json_dumps_params={"ensure_ascii": False},
    )


@cache_control(no_cache=True)  # o navegador sempre confere se há versão nova do service worker
def service_worker(request):
    return render(
        request, "pwa/sw.js", {"versao": VERSAO_CACHE}, content_type="application/javascript"
    )


def offline(request):
    """Mostrada pelo service worker quando não há conexão. Não usa dados do usuário
    no servidor: o resumo da corrida vem do aparelho (localStorage)."""
    return render(request, "pwa/offline.html")

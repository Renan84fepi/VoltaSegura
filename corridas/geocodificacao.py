"""Conversão de endereço em coordenadas (RF08) com geopy + Nominatim (OpenStreetMap)."""
import re
from decimal import Decimal

from django.conf import settings
from geopy.exc import GeopyError
from geopy.geocoders import Nominatim

# "-22.2306, -45.9356": coordenadas digitadas direto (útil sem internet e na demonstração).
COORDENADAS = re.compile(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*[,;]\s*(-?\d{1,3}(?:\.\d+)?)\s*$")


class EnderecoNaoEncontrado(Exception):
    pass


def geocodificar(endereco):
    """Devolve (latitude, longitude) do endereço ou levanta EnderecoNaoEncontrado."""
    digitadas = COORDENADAS.match(endereco)
    if digitadas:
        latitude, longitude = (Decimal(v) for v in digitadas.groups())
        if abs(latitude) <= 90 and abs(longitude) <= 180:
            return latitude, longitude
        raise EnderecoNaoEncontrado("Coordenadas fora do intervalo válido.")

    if not settings.GEOCODIFICACAO_ATIVA:
        raise EnderecoNaoEncontrado(
            "Busca de endereço desativada. Use sua localização ou digite 'latitude, longitude'."
        )
    try:
        local = Nominatim(user_agent=settings.GEOCODIFICADOR_USER_AGENT, timeout=5).geocode(
            endereco, country_codes="br"
        )
    except GeopyError:
        raise EnderecoNaoEncontrado(
            "Serviço de endereços indisponível. Use sua localização ou tente de novo."
        )
    if local is None:
        raise EnderecoNaoEncontrado("Endereço não encontrado. Inclua número, bairro e cidade.")
    return Decimal(str(local.latitude)), Decimal(str(local.longitude))

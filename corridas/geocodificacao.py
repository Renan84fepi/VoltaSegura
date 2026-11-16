"""Conversão de endereço em coordenadas (RF08) com geopy + Nominatim (OpenStreetMap)."""
import re
from decimal import Decimal

from django.conf import settings
from geopy.exc import GeopyError
from geopy.geocoders import Nominatim

# "-22.2306, -45.9356": coordenadas digitadas direto (útil sem internet e na demonstração).
COORDENADAS = re.compile(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*[,;]\s*(-?\d{1,3}(?:\.\d+)?)\s*$")


# Regiões de busca em volta da referência, em graus de meia largura (~11 km e ~55 km).
# O Nominatim ordena por relevância, não por proximidade: começar pequeno evita a cidade vizinha.
RAIOS_BUSCA_GRAUS = (0.1, 0.5)


class EnderecoNaoEncontrado(Exception):
    pass


def geocodificar(endereco, perto=None):
    """Devolve (latitude, longitude) do endereço ou levanta EnderecoNaoEncontrado."""
    latitude, longitude, _ = localizar(endereco, perto)
    return latitude, longitude


def localizar(endereco, perto=None):
    """Como geocodificar, mais o endereço que o serviço encontrou (None se eram coordenadas).
    Mostrar esse nome ao cliente revela quando a busca caiu em outra cidade.

    perto=(lat, lng): procura primeiro nessa região. Sem isso, "Avenida Brasil, 500"
    cai no Rio de Janeiro mesmo com o cliente em outra cidade."""
    digitadas = COORDENADAS.match(endereco)
    if digitadas:
        latitude, longitude = (Decimal(v) for v in digitadas.groups())
        if abs(latitude) <= 90 and abs(longitude) <= 180:
            return latitude, longitude, None
        raise EnderecoNaoEncontrado("Coordenadas fora do intervalo válido.")

    if not settings.GEOCODIFICACAO_ATIVA:
        raise EnderecoNaoEncontrado(
            "Busca de endereço desativada. Use sua localização ou digite 'latitude, longitude'."
        )
    try:
        servico = Nominatim(user_agent=settings.GEOCODIFICADOR_USER_AGENT, timeout=5)
        local = None
        if perto is not None:
            lat, lng = float(perto[0]), float(perto[1])
            for raio in RAIOS_BUSCA_GRAUS:
                local = servico.geocode(
                    endereco, country_codes="br", bounded=True,
                    viewbox=[(lat - raio, lng - raio), (lat + raio, lng + raio)],
                )
                if local is not None:
                    break
        if local is None:
            local = servico.geocode(endereco, country_codes="br")
    except GeopyError:
        raise EnderecoNaoEncontrado(
            "Serviço de endereços indisponível. Use sua localização ou tente de novo."
        )
    if local is None:
        raise EnderecoNaoEncontrado("Endereço não encontrado. Inclua número, bairro e cidade.")
    return Decimal(str(local.latitude)), Decimal(str(local.longitude)), local.address

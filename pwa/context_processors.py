from .views import VERSAO_CACHE


def versao(request):
    """`?v=` nos scripts: ao mudar VERSAO_CACHE, o navegador baixa os arquivos novos."""
    return {"versao_estaticos": VERSAO_CACHE}

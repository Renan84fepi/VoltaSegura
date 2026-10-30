"""Configurações do VoltaSegura. Valores sensíveis vêm do arquivo .env."""
from pathlib import Path

import environ
from django.contrib.messages import constants as messages

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")  # obrigatória: sem valor padrão de propósito
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "contas",
    "veiculos",
    "motoristas",
    "corridas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "contas.Usuario"
AUTHENTICATION_BACKENDS = ["contas.backends.BackendSemBloqueados"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Uploads (documentos, fotos). NÃO há MEDIA_URL: os arquivos só são entregues
# por uma view que confere permissão (RNF07 - privacidade).
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MESSAGE_TAGS = {messages.ERROR: "danger"}

# Django 6.1: EMAIL_BACKEND foi descontinuado em favor de MAILERS.
# Em desenvolvimento o e-mail é impresso no terminal. Para SMTP real, troque o
# BACKEND no .env e acrescente as OPTIONS conforme a documentação do Django.
MAILERS = {
    "default": {
        "BACKEND": env(
            "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
        ),
    }
}
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="VoltaSegura <nao-responda@voltasegura.local>"
)

# API REST: sessão do Django (com CSRF) e permissão por perfil em cada view.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "corridas.api.tratar_excecao",
}

# Endereço -> coordenadas (geopy + Nominatim/OpenStreetMap). Desligue sem internet:
# o cliente ainda pode usar a posição do aparelho ou digitar "latitude, longitude".
GEOCODIFICACAO_ATIVA = env.bool("GEOCODIFICACAO_ATIVA", default=True)
GEOCODIFICADOR_USER_AGENT = env(
    "GEOCODIFICADOR_USER_AGENT", default="VoltaSegura/1.0 (projeto academico)"
)

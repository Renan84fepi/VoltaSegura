from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models


class UsuarioManager(BaseUserManager):
    """Gerenciador de usuários que autentica por e-mail (sem username)."""

    use_in_migrations = True

    def _criar(self, email, password, **extra):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        email = email.strip().lower()
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._criar(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("perfil", Usuario.Perfil.ADMINISTRADOR)
        if not extra["is_staff"] or not extra["is_superuser"]:
            raise ValueError("Superusuário precisa de is_staff e is_superuser.")
        return self._criar(email, password, **extra)


class Usuario(AbstractUser):
    """Usuário do sistema. O campo `perfil` define o papel (RNF08)."""

    class Perfil(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        MOTORISTA = "motorista", "Motorista"
        ADMINISTRADOR = "administrador", "Administrador"

    username = None
    first_name = None
    last_name = None

    email = models.EmailField(
        "e-mail",
        unique=True,
        error_messages={"unique": "Já existe uma conta com este e-mail."},
    )
    nome = models.CharField("nome completo", max_length=150)
    telefone = models.CharField(
        "telefone",
        max_length=11,
        validators=[
            RegexValidator(r"^\d{10,11}$", "Informe DDD + número (10 ou 11 dígitos).")
        ],
        help_text="Somente números, com DDD.",
    )
    perfil = models.CharField(
        "perfil", max_length=15, choices=Perfil.choices, default=Perfil.CLIENTE
    )
    bloqueado = models.BooleanField(
        "bloqueado",
        default=False,
        help_text="Usuário bloqueado não consegue entrar no sistema.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.email})"

    def get_full_name(self):
        return self.nome

    def get_short_name(self):
        return self.nome.split(" ")[0] if self.nome else self.email

    def save(self, *args, **kwargs):
        # Administrador do sistema = acesso total à área administrativa.
        if self.perfil == self.Perfil.ADMINISTRADOR:
            self.is_staff = True
            self.is_superuser = True
        elif self.is_superuser:
            self.perfil = self.Perfil.ADMINISTRADOR
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def eh_cliente(self):
        return self.perfil == self.Perfil.CLIENTE

    @property
    def eh_motorista(self):
        return self.perfil == self.Perfil.MOTORISTA

    @property
    def eh_administrador(self):
        return self.perfil == self.Perfil.ADMINISTRADOR

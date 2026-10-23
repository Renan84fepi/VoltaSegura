from django.core.exceptions import ValidationError

TAMANHO_MAXIMO_MB = 5


def validar_tamanho_imagem(arquivo):
    if arquivo.size > TAMANHO_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(f"A imagem deve ter no máximo {TAMANHO_MAXIMO_MB} MB.")


def validar_cpf(valor):
    """Valida CPF (somente dígitos) pelos dígitos verificadores."""
    cpf = "".join(c for c in str(valor) if c.isdigit())
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.")
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[tamanho]):
            raise ValidationError("CPF inválido.")

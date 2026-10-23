"""Cria usuários de exemplo para demonstração e testes manuais."""
import io
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image

from contas.models import Usuario
from motoristas.models import Bicicleta, DadosRepasse, PerfilMotorista
from veiculos.models import Veiculo

Status = PerfilMotorista.Status


def imagem_falsa(cor):
    buffer = io.BytesIO()
    Image.new("RGB", (320, 200), cor).save(buffer, "PNG")
    return ContentFile(buffer.getvalue(), name="exemplo.png")


class Command(BaseCommand):
    help = "Cria administrador, clientes e motoristas de exemplo (apenas em desenvolvimento)."

    def add_arguments(self, parser):
        parser.add_argument("--senha", default="voltasegura123", help="Senha dos usuários de exemplo.")
        parser.add_argument("--forcar", action="store_true", help="Permite rodar com DEBUG=False.")

    def handle(self, *args, **opcoes):
        if not settings.DEBUG and not opcoes["forcar"]:
            raise CommandError("Recusado: DEBUG=False. Use --forcar se tiver certeza.")
        senha = opcoes["senha"]
        hoje = timezone.localdate()

        def usuario(email, nome, perfil, telefone):
            obj, criado = Usuario.objects.get_or_create(
                email=email, defaults={"nome": nome, "perfil": perfil, "telefone": telefone}
            )
            if criado:
                obj.set_password(senha)
                obj.save()
            return obj

        admin = usuario("admin@exemplo.com", "Administrador", Usuario.Perfil.ADMINISTRADOR, "35999990000")

        clientes = {
            "ana@exemplo.com": ("Ana Souza", "35999990001", ("Fiat", "Argo", "Prata", 2021, "ABC1D23")),
            "bruno@exemplo.com": ("Bruno Lima", "35999990002", ("VW", "Gol", "Preto", 2018, "XYZ9876")),
        }
        for email, (nome, tel, (marca, modelo, cor, ano, placa)) in clientes.items():
            cliente = usuario(email, nome, Usuario.Perfil.CLIENTE, tel)
            Veiculo.objects.get_or_create(
                cliente=cliente,
                placa=placa,
                defaults={"marca": marca, "modelo": modelo, "cor": cor, "ano": ano},
            )

        # (email, nome, tel, situação docs, validade CNH, situação bicicleta, cor da imagem)
        motoristas = [
            ("carlos@exemplo.com", "Carlos Mota", "35999990011", Status.APROVADO, hoje + timedelta(days=700), Status.APROVADO, "#2d6a4f"),
            ("diana@exemplo.com", "Diana Reis", "35999990012", Status.PENDENTE, hoje + timedelta(days=500), Status.PENDENTE, "#264653"),
            ("eduardo@exemplo.com", "Eduardo Paz", "35999990013", Status.REJEITADO, hoje + timedelta(days=300), Status.APROVADO, "#9d0208"),
            ("fabio@exemplo.com", "Fábio Costa", "35999990014", Status.APROVADO, hoje - timedelta(days=30), Status.APROVADO, "#6c757d"),
        ]
        cpfs = ["52998224725", "11144477735", "39053344705", "16899535009"]
        for i, (email, nome, tel, st_docs, validade, st_bike, cor) in enumerate(motoristas):
            motorista = usuario(email, nome, Usuario.Perfil.MOTORISTA, tel)
            perfil, criado = PerfilMotorista.objects.get_or_create(
                usuario=motorista,
                defaults={
                    "documento_identidade": imagem_falsa(cor),
                    "cnh_numero": f"0123456789{i}",
                    "cnh_validade": validade,
                },
            )
            if criado:
                self._avaliar(perfil, st_docs, admin, "Foto do documento ilegível.")
            bicicleta, criada = Bicicleta.objects.get_or_create(
                usuario=motorista,
                defaults={"marca": "Dobrix", "modelo": f"Mini E{i + 1}", "cor": "Cinza", "foto": imagem_falsa(cor)},
            )
            if criada:
                self._avaliar(bicicleta, st_bike, admin, "Foto não mostra a bicicleta dobrada.")
            DadosRepasse.objects.get_or_create(
                usuario=motorista,
                defaults={"titular": nome, "tipo_chave_pix": "cpf", "chave_pix": cpfs[i]},
            )

        self.stdout.write(self.style.SUCCESS("Dados de exemplo prontos."))
        self.stdout.write(f"Senha de todos: {senha}")
        self.stdout.write(
            "admin@exemplo.com | ana@ e bruno@ (clientes) | carlos@ (aprovado) | "
            "diana@ (pendente) | eduardo@ (rejeitado) | fabio@ (CNH vencida) — todos @exemplo.com"
        )

    @staticmethod
    def _avaliar(obj, status, admin, motivo):
        if status == Status.APROVADO:
            obj.aprovar(admin)
        elif status == Status.REJEITADO:
            obj.rejeitar(admin, motivo)

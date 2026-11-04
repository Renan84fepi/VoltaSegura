"""Cria usuários de exemplo para demonstração e testes manuais."""
import io
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image

from contas.models import Usuario
from corridas import regras
from corridas.models import Configuracao, Corrida, Pagamento
from motoristas.models import Bicicleta, DadosRepasse, PerfilMotorista
from veiculos.models import Veiculo

Status = PerfilMotorista.Status
PREFIXO_EXEMPLO = "[exemplo]"


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

        # (email, nome, tel, situação docs, validade CNH, situação bicicleta, cor da imagem, posição)
        # Posições em Pouso Alegre/MG, a distâncias diferentes do Centro.
        motoristas = [
            ("carlos@exemplo.com", "Carlos Mota", "35999990011", Status.APROVADO, hoje + timedelta(days=700), Status.APROVADO, "#2d6a4f", ("-22.229800", "-45.934200")),
            ("diana@exemplo.com", "Diana Reis", "35999990012", Status.PENDENTE, hoje + timedelta(days=500), Status.PENDENTE, "#264653", ("-22.236000", "-45.928000")),
            ("eduardo@exemplo.com", "Eduardo Paz", "35999990013", Status.REJEITADO, hoje + timedelta(days=300), Status.APROVADO, "#9d0208", ("-22.221000", "-45.940000")),
            ("fabio@exemplo.com", "Fábio Costa", "35999990014", Status.APROVADO, hoje - timedelta(days=30), Status.APROVADO, "#6c757d", ("-22.240000", "-45.945000")),
            ("gabriela@exemplo.com", "Gabriela Nunes", "35999990015", Status.APROVADO, hoje + timedelta(days=900), Status.APROVADO, "#e76f51", ("-22.252000", "-45.912000")),
        ]
        cpfs = ["52998224725", "11144477735", "39053344705", "16899535009", "71428793860"]
        for i, (email, nome, tel, st_docs, validade, st_bike, cor, (lat, lng)) in enumerate(motoristas):
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
            if perfil.latitude is None:  # última posição conhecida; fica offline até o motorista entrar
                PerfilMotorista.objects.filter(pk=perfil.pk).update(latitude=lat, longitude=lng)
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

        Configuracao.atual()  # tarifas padrão (editáveis no admin)
        self._historico_exemplo()

        self.stdout.write(self.style.SUCCESS("Dados de exemplo prontos."))
        self.stdout.write(f"Senha de todos: {senha}")
        self.stdout.write(
            "admin@exemplo.com | ana@ e bruno@ (clientes) | carlos@ e gabriela@ (aprovados) | "
            "diana@ (pendente) | eduardo@ (rejeitado) | fabio@ (CNH vencida) — todos @exemplo.com"
        )
        self.stdout.write(
            "Corrida de teste: coleta '-22.2306, -45.9356' (Centro) e destino '-22.2650, -45.9000'."
        )

    def _historico_exemplo(self):
        """Corridas antigas de Carlos (finalizadas, pagas e avaliadas) para a tela de
        ganhos (RF22), o histórico (RF25) e a nota média (RF24). Passam pelas regras."""
        if Corrida.objects.filter(origem_endereco__startswith=PREFIXO_EXEMPLO).exists():
            return
        carlos = Usuario.objects.get(email="carlos@exemplo.com")
        perfil = carlos.perfil_motorista
        # (cliente, dias atrás, destino, nota, comentário, resultado do pagamento)
        corridas = [
            ("ana@exemplo.com", 1, ("-22.2650", "-45.9000"), 5, "Muito educado e pontual.", "aprovado"),
            ("bruno@exemplo.com", 3, ("-22.2500", "-45.9200"), 4, "", "aprovado"),
            ("ana@exemplo.com", 12, ("-22.2100", "-45.9500"), 5, "Cuidou bem do carro.", "estornado"),
        ]
        for email, dias, (lat, lng), nota, comentario, resultado in corridas:
            cliente = Usuario.objects.get(email=email)
            if regras.corrida_ativa_do_cliente(cliente) or regras.pagamento_em_aberto_do_cliente(cliente):
                self.stdout.write(self.style.WARNING(
                    f"{email} tem corrida ativa ou pagamento em aberto: corrida antiga de exemplo não criada."
                ))
                continue
            # Deixa Carlos online e no Centro só para receber a oferta.
            PerfilMotorista.objects.filter(pk=perfil.pk).update(
                online=True, latitude="-22.230600", longitude="-45.935600",
                localizacao_em=timezone.now(),
            )
            corrida = regras.solicitar(
                cliente, cliente.veiculos.first(),
                (f"{PREFIXO_EXEMPLO} Centro", Decimal("-22.230600"), Decimal("-45.935600")),
                (f"{PREFIXO_EXEMPLO} Destino", Decimal(lat), Decimal(lng)), "pix",
            )
            regras.aceitar(corrida.pk, carlos)
            regras.ir_a_caminho(corrida.pk, carlos)
            regras.informar_chegada(corrida.pk, carlos)
            regras.iniciar(corrida.pk, carlos, corrida.codigo_confirmacao)
            regras.finalizar(corrida.pk, carlos)
            regras.pagar(corrida.pk, cliente)
            if resultado == "estornado":
                regras.estornar(corrida.pagamento.pk, None, "Exemplo de estorno")
            regras.avaliar(corrida.pk, cliente, nota, comentario)
            quando = timezone.now() - timedelta(days=dias)
            Corrida.objects.filter(pk=corrida.pk).update(criada_em=quando)
            Pagamento.objects.filter(corrida=corrida).update(criado_em=quando)
        PerfilMotorista.objects.filter(pk=perfil.pk).update(online=False)

    @staticmethod
    def _avaliar(obj, status, admin, motivo):
        if status == Status.APROVADO:
            obj.aprovar(admin)
        elif status == Status.REJEITADO:
            obj.rejeitar(admin, motivo)

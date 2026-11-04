"""Corridas finalizadas antes do Marco 4 ganham o pagamento pendente (RF19),
para que toda corrida finalizada tenha um pagamento."""
import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations


def gerar(apps, schema_editor):
    Corrida = apps.get_model("corridas", "Corrida")
    Pagamento = apps.get_model("corridas", "Pagamento")
    EventoPagamento = apps.get_model("corridas", "EventoPagamento")
    for corrida in Corrida.objects.filter(status="finalizada", pagamento__isnull=True):
        # Mesma conta de regras.dividir_valor (a migration não importa código da app).
        taxa = (corrida.preco_estimado * corrida.percentual_plataforma / 100).quantize(
            Decimal("0.01"), ROUND_HALF_UP
        )
        pagamento = Pagamento.objects.create(
            corrida=corrida, forma=corrida.forma_pagamento, valor_total=corrida.preco_estimado,
            percentual_plataforma=corrida.percentual_plataforma, taxa_plataforma=taxa,
            valor_motorista=corrida.preco_estimado - taxa, transacao=uuid.uuid4().hex,
            criado_em=corrida.atualizada_em,
        )
        EventoPagamento.objects.create(
            pagamento=pagamento, status_novo="pendente",
            observacao="Gerado na migração do Marco 4",
        )


class Migration(migrations.Migration):
    dependencies = [("corridas", "0002_pagamento_avaliacao")]

    operations = [migrations.RunPython(gerar, migrations.RunPython.noop)]

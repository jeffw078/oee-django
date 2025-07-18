# Generated by Django 4.2.7 on 2025-07-09 13:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "soldagem",
            "0002_componente_modulo_alter_componente_formula_calculo_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="componente",
            name="formula_calculo",
            field=models.TextField(
                blank=True, help_text="Fórmula para calcular tempo com diâmetro"
            ),
        ),
        migrations.AlterField(
            model_name="componente",
            name="tempo_padrao",
            field=models.DecimalField(
                decimal_places=2, help_text="Em minutos", max_digits=6
            ),
        ),
    ]

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('soldagem', '0001_initial'),
    ]

    operations = [
        # Adicionar campo modulo ao modelo Componente
        migrations.AddField(
            model_name='componente',
            name='modulo',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, 
                related_name='componentes', 
                to='soldagem.modulo',
                null=True,
                blank=True
            ),
        ),
        
        # Associar componentes existentes ao primeiro módulo disponível
        migrations.RunSQL(
            """
            UPDATE componente 
            SET modulo_id = (
                SELECT id FROM modulo 
                WHERE ativo = true 
                ORDER BY id 
                LIMIT 1
            ) 
            WHERE modulo_id IS NULL;
            """,
            reverse_sql="UPDATE componente SET modulo_id = NULL;"
        ),
        
        # Tornar o campo obrigatório após popular os dados
        migrations.AlterField(
            model_name='componente',
            name='modulo',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='componentes',
                to='soldagem.modulo'
            ),
        ),
    ]
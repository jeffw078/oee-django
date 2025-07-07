from django.db import models
from django.utils import timezone
from core.models import Usuario, Soldador
from soldagem.models import Apontamento
from decimal import Decimal
import math

class TipoDefeito(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    cor_exibicao = models.CharField(max_length=7, default='#ffc107')  # Cor hexadecimal
    
    class Meta:
        db_table = 'tipo_defeito'
        ordering = ['nome']
        verbose_name_plural = 'Tipos de Defeito'
        
    def __str__(self):
        return self.nome

class Defeito(models.Model):
    tipo_defeito = models.ForeignKey(TipoDefeito, on_delete=models.CASCADE)
    apontamento = models.ForeignKey(Apontamento, on_delete=models.CASCADE)
    soldador = models.ForeignKey(Soldador, on_delete=models.CASCADE)
    tamanho_mm = models.DecimalField(max_digits=8, decimal_places=2, help_text="Tamanho do defeito em mm")
    area_defeito = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Área calculada em mm²")
    data_deteccao = models.DateTimeField(auto_now_add=True)
    usuario_qualidade = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='defeitos_detectados')
    observacoes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'defeito'
        ordering = ['-data_deteccao']
        
    def __str__(self):
        return f"{self.tipo_defeito} - {self.apontamento} - {self.tamanho_mm}mm"
    
    def save(self, *args, **kwargs):
        # Calcular área do defeito (assumindo forma circular)
        if self.tamanho_mm:
            raio = self.tamanho_mm / 2
            self.area_defeito = Decimal(str(math.pi * (float(raio) ** 2)))
        
        super().save(*args, **kwargs)
    
    def calcular_percentual_qualidade(self):
        """Calcula o percentual de qualidade baseado na área do defeito"""
        if self.area_defeito and self.apontamento.diametro:
            # Área total do tubo (assumindo comprimento padrão ou área de soldagem)
            raio_tubo = self.apontamento.diametro / 2
            area_total_soldagem = Decimal(str(math.pi * float(raio_tubo) * 100))  # Assumindo 100mm de comprimento de soldagem
            
            percentual_defeito = (self.area_defeito / area_total_soldagem) * 100
            percentual_qualidade = 100 - percentual_defeito
            
            return max(Decimal('0'), min(Decimal('100'), percentual_qualidade))
        
        return Decimal('100')  # Se não há dados suficientes, assume qualidade perfeita

# Modelo para cache de cálculos OEE - usado nos relatórios
class CalculoOEE(models.Model):
    soldador = models.ForeignKey(Soldador, on_delete=models.CASCADE, null=True, blank=True)
    modulo = models.ForeignKey('soldagem.Modulo', on_delete=models.CASCADE, null=True, blank=True)
    data_calculo = models.DateField()
    periodo_inicio = models.DateTimeField()
    periodo_fim = models.DateTimeField()
    
    # Métricas principais
    utilizacao = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # %
    eficiencia = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # %
    qualidade = models.DecimalField(max_digits=5, decimal_places=2, default=100)  # %
    oee_final = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # %
    
    # Dados auxiliares
    horas_trabalhadas = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    horas_disponiveis = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    tempo_paradas = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    tempo_produtivo = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    tempo_padrao_total = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Contadores
    total_pecas = models.IntegerField(default=0)
    pecas_com_defeito = models.IntegerField(default=0)
    total_defeitos_mm = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    timestamp_calculo = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'calculo_oee'
        ordering = ['-data_calculo', '-timestamp_calculo']
        unique_together = ['soldador', 'modulo', 'data_calculo', 'periodo_inicio']
        
    def __str__(self):
        soldador_nome = self.soldador.usuario.nome_completo if self.soldador else "Geral"
        modulo_nome = self.modulo.nome if self.modulo else "Todos"
        return f"OEE {soldador_nome} - {modulo_nome} - {self.data_calculo}"
    
    def calcular_metricas(self):
        """Recalcula todas as métricas OEE"""
        from soldagem.models import Apontamento, Parada
        
        # Filtrar apontamentos do período
        apontamentos = Apontamento.objects.filter(
            inicio_processo__gte=self.periodo_inicio,
            inicio_processo__lte=self.periodo_fim
        )
        
        if self.soldador:
            apontamentos = apontamentos.filter(soldador=self.soldador)
        
        if self.modulo:
            apontamentos = apontamentos.filter(modulo=self.modulo)
        
        # 1. UTILIZAÇÃO = horas trabalhadas / horas disponíveis
        paradas = Parada.objects.filter(
            inicio__gte=self.periodo_inicio,
            inicio__lte=self.periodo_fim,
            soldador=self.soldador if self.soldador else None
        )
        
        # Calcular tempo total de paradas (apenas as que penalizam OEE)
        tempo_paradas_penalizantes = sum([
            p.duracao_minutos or 0 for p in paradas 
            if p.tipo_parada.penaliza_oee and p.duracao_minutos
        ]) / 60  # Converter para horas
        
        self.tempo_paradas = Decimal(str(tempo_paradas_penalizantes))
        self.horas_trabalhadas = self.horas_disponiveis - self.tempo_paradas
        
        if self.horas_disponiveis > 0:
            self.utilizacao = (self.horas_trabalhadas / self.horas_disponiveis) * 100
        
        # 2. EFICIÊNCIA = tempo padrão / tempo real
        tempo_real_total = sum([
            float(a.tempo_real or 0) for a in apontamentos if a.tempo_real
        ]) / 60  # Converter para horas
        
        tempo_padrao_total = sum([
            float(a.tempo_padrao or 0) for a in apontamentos
        ]) / 60  # Converter para horas
        
        self.tempo_produtivo = Decimal(str(tempo_real_total))
        self.tempo_padrao_total = Decimal(str(tempo_padrao_total))
        
        if tempo_real_total > 0:
            self.eficiencia = (Decimal(str(tempo_padrao_total)) / Decimal(str(tempo_real_total))) * 100
        
        # 3. QUALIDADE = (100 - % defeitos)
        defeitos = Defeito.objects.filter(
            data_deteccao__gte=self.periodo_inicio,
            data_deteccao__lte=self.periodo_fim
        )
        
        if self.soldador:
            defeitos = defeitos.filter(soldador=self.soldador)
        
        total_area_defeitos = sum([float(d.area_defeito or 0) for d in defeitos])
        self.total_defeitos_mm = Decimal(str(total_area_defeitos))
        
        # Calcular qualidade baseada na área total de soldagem vs defeitos
        area_total_soldagem = 0
        for apontamento in apontamentos:
            if apontamento.diametro:
                # Área aproximada de soldagem por peça
                area_peca = math.pi * float(apontamento.diametro) * 50  # 50mm de comprimento médio
                area_total_soldagem += area_peca
        
        if area_total_soldagem > 0:
            percentual_defeito = (total_area_defeitos / area_total_soldagem) * 100
            self.qualidade = max(Decimal('0'), 100 - Decimal(str(percentual_defeito)))
        
        # Contadores
        self.total_pecas = apontamentos.count()
        self.pecas_com_defeito = defeitos.values('apontamento').distinct().count()
        
        # 4. OEE FINAL = utilização × eficiência × qualidade / 10000
        self.oee_final = (self.utilizacao * self.eficiencia * self.qualidade) / 10000
        
        self.save()
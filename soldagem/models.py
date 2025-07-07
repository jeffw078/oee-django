from django.db import models
from django.utils import timezone
from core.models import Usuario, Soldador
from decimal import Decimal

class Modulo(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    ordem_exibicao = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'modulo'
        ordering = ['ordem_exibicao', 'nome']
        
    def __str__(self):
        return self.nome

class Componente(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    tempo_padrao = models.DecimalField(max_digits=6, decimal_places=2, help_text="Tempo em minutos")
    considera_diametro = models.BooleanField(default=False)
    formula_calculo = models.TextField(blank=True, help_text="Fórmula para calcular tempo baseado no diâmetro")
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'componente'
        ordering = ['nome']
        
    def __str__(self):
        return self.nome
    
    def calcular_tempo_padrao(self, diametro=None):
        """Calcula o tempo padrão baseado no diâmetro se necessário"""
        if self.considera_diametro and diametro and self.formula_calculo:
            try:
                # Fórmula simples: tempo_base * (diametro / 100)
                # Pode ser expandida para fórmulas mais complexas
                tempo_calculado = eval(self.formula_calculo.replace('diametro', str(diametro)))
                return Decimal(str(tempo_calculado))
            except:
                return self.tempo_padrao
        return self.tempo_padrao

class Pedido(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    
    numero = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_prevista = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    observacoes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pedido'
        ordering = ['-data_criacao']
        
    def __str__(self):
        return f"Pedido {self.numero}"

class Turno(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('finalizado', 'Finalizado'),
    ]
    
    soldador = models.ForeignKey(Soldador, on_delete=models.CASCADE)
    data_turno = models.DateField()
    inicio_turno = models.DateTimeField()
    fim_turno = models.DateTimeField(null=True, blank=True)
    horas_disponiveis = models.DecimalField(max_digits=4, decimal_places=2, default=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    
    class Meta:
        db_table = 'turno'
        ordering = ['-data_turno', '-inicio_turno']
        unique_together = ['soldador', 'data_turno', 'inicio_turno']
        
    def __str__(self):
        return f"{self.soldador} - {self.data_turno}"
    
    def calcular_horas_trabalhadas(self):
        """Calcula as horas efetivamente trabalhadas"""
        if self.fim_turno:
            delta = self.fim_turno - self.inicio_turno
            return Decimal(str(delta.total_seconds() / 3600))
        elif self.status == 'ativo':
            delta = timezone.now() - self.inicio_turno
            return Decimal(str(delta.total_seconds() / 3600))
        return Decimal('0')

class Apontamento(models.Model):
    soldador = models.ForeignKey(Soldador, on_delete=models.CASCADE)
    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE)
    componente = models.ForeignKey(Componente, on_delete=models.CASCADE)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, null=True, blank=True)
    numero_poste_tubo = models.CharField(max_length=50)
    diametro = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    inicio_processo = models.DateTimeField()
    fim_processo = models.DateTimeField(null=True, blank=True)
    tempo_real = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Em minutos")
    tempo_padrao = models.DecimalField(max_digits=6, decimal_places=2, help_text="Em minutos")
    eficiencia_calculada = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'apontamento'
        ordering = ['-inicio_processo']
        
    def __str__(self):
        return f"{self.soldador} - {self.componente} - {self.inicio_processo}"
    
    def save(self, *args, **kwargs):
        # Calcular tempo padrão baseado no componente e diâmetro
        self.tempo_padrao = self.componente.calcular_tempo_padrao(self.diametro)
        
        # Calcular tempo real se o processo foi finalizado
        if self.fim_processo:
            delta = self.fim_processo - self.inicio_processo
            self.tempo_real = Decimal(str(delta.total_seconds() / 60))  # Converter para minutos
            
            # Calcular eficiência
            if self.tempo_real and self.tempo_real > 0:
                self.eficiencia_calculada = (self.tempo_padrao / self.tempo_real) * 100
        
        super().save(*args, **kwargs)
    
    def get_tempo_decorrido(self):
        """Retorna o tempo decorrido em minutos"""
        if self.fim_processo:
            delta = self.fim_processo - self.inicio_processo
        else:
            delta = timezone.now() - self.inicio_processo
        return delta.total_seconds() / 60

class TipoParada(models.Model):
    CATEGORIA_CHOICES = [
        ('geral', 'Geral'),
        ('manutencao', 'Manutenção'),
        ('qualidade', 'Qualidade'),
    ]
    
    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    penaliza_oee = models.BooleanField(default=True, help_text="Se deve ser considerado no cálculo OEE")
    requer_senha_especial = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    cor_exibicao = models.CharField(max_length=7, default='#dc3545')  # Cor hexadecimal
    
    class Meta:
        db_table = 'tipo_parada'
        ordering = ['categoria', 'nome']
        
    def __str__(self):
        return f"{self.nome} ({self.get_categoria_display()})"

class Parada(models.Model):
    tipo_parada = models.ForeignKey(TipoParada, on_delete=models.CASCADE)
    soldador = models.ForeignKey(Soldador, on_delete=models.CASCADE)
    apontamento = models.ForeignKey(Apontamento, on_delete=models.CASCADE, null=True, blank=True)
    turno = models.ForeignKey(Turno, on_delete=models.CASCADE, null=True, blank=True)
    inicio = models.DateTimeField()
    fim = models.DateTimeField(null=True, blank=True)
    duracao_minutos = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    motivo_detalhado = models.TextField(blank=True)
    usuario_autorizacao = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'parada'
        ordering = ['-inicio']
        
    def __str__(self):
        return f"{self.tipo_parada} - {self.soldador} - {self.inicio}"
    
    def save(self, *args, **kwargs):
        # Calcular duração se a parada foi finalizada
        if self.fim:
            delta = self.fim - self.inicio
            self.duracao_minutos = Decimal(str(delta.total_seconds() / 60))
        
        super().save(*args, **kwargs)
    
    def get_duracao_atual(self):
        """Retorna a duração atual em minutos"""
        if self.fim:
            delta = self.fim - self.inicio
        else:
            delta = timezone.now() - self.inicio
        return delta.total_seconds() / 60
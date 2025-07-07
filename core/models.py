from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import json

class Usuario(AbstractUser):
    TIPO_CHOICES = [
        ('admin', 'Administrador'),
        ('analista', 'Analista'),
        ('qualidade', 'Qualidade'),
        ('manutencao', 'Manutenção'),
        ('soldador', 'Soldador'),
    ]
    
    nome_completo = models.CharField(max_length=255)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_CHOICES)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    ultimo_login = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'usuario'
        
    def __str__(self):
        return f"{self.nome_completo} ({self.get_tipo_usuario_display()})"

class Soldador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='soldador_profile')
    senha_simplificada = models.CharField(max_length=20, help_text="Senha para login rápido")
    ativo = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'soldador'
        verbose_name_plural = 'Soldadores'
        
    def __str__(self):
        return self.usuario.nome_completo

class ConfiguracaoSistema(models.Model):
    TIPO_CHOICES = [
        ('string', 'Texto'),
        ('integer', 'Número Inteiro'),
        ('float', 'Número Decimal'),
        ('boolean', 'Verdadeiro/Falso'),
        ('json', 'JSON'),
    ]
    
    chave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descricao = models.TextField(blank=True)
    tipo_dado = models.CharField(max_length=20, choices=TIPO_CHOICES, default='string')
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'configuracao_sistema'
        verbose_name_plural = 'Configurações do Sistema'
        
    def __str__(self):
        return f"{self.chave}: {self.valor}"
    
    def get_valor_convertido(self):
        """Retorna o valor convertido para o tipo correto"""
        if self.tipo_dado == 'integer':
            return int(self.valor)
        elif self.tipo_dado == 'float':
            return float(self.valor)
        elif self.tipo_dado == 'boolean':
            return self.valor.lower() in ['true', '1', 'sim', 'yes']
        elif self.tipo_dado == 'json':
            return json.loads(self.valor)
        return self.valor

class HoraTrabalho(models.Model):
    nome = models.CharField(max_length=100)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    horas_disponiveis = models.DecimalField(max_digits=4, decimal_places=2)
    ativo = models.BooleanField(default=True)
    dias_semana = models.JSONField(default=list, help_text="Lista com dias da semana [0-6, 0=Segunda]")
    
    class Meta:
        db_table = 'hora_trabalho'
        verbose_name_plural = 'Horas de Trabalho'
        
    def __str__(self):
        return f"{self.nome}: {self.hora_inicio} às {self.hora_fim}"

class LogAuditoria(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=255)
    tabela_afetada = models.CharField(max_length=100, blank=True)
    registro_id = models.IntegerField(null=True, blank=True)
    dados_antes = models.JSONField(null=True, blank=True)
    dados_depois = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'log_auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.timestamp} - {self.acao} por {self.usuario}"

class LogSincronizacao(models.Model):
    STATUS_CHOICES = [
        ('sucesso', 'Sucesso'),
        ('erro', 'Erro'),
        ('pendente', 'Pendente'),
    ]
    
    OPERACAO_CHOICES = [
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('sync', 'Sincronização'),
    ]
    
    dispositivo_id = models.CharField(max_length=100)
    tipo_operacao = models.CharField(max_length=20, choices=OPERACAO_CHOICES)
    tabela = models.CharField(max_length=100)
    registros_afetados = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    mensagem_erro = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'log_sincronizacao'
        verbose_name_plural = 'Logs de Sincronização'
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.dispositivo_id} - {self.tipo_operacao} ({self.status})"

class SessaoOffline(models.Model):
    dispositivo_id = models.CharField(max_length=100, unique=True)
    soldador = models.ForeignKey(Soldador, on_delete=models.CASCADE)
    dados_cache = models.JSONField(default=dict)
    ultimo_sync = models.DateTimeField(auto_now=True)
    status_conexao = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'sessao_offline'
        verbose_name_plural = 'Sessões Offline'
        
    def __str__(self):
        return f"{self.dispositivo_id} - {self.soldador}"
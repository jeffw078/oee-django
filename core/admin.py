from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import Usuario, Soldador, ConfiguracaoSistema, HoraTrabalho, LogAuditoria, LogSincronizacao, SessaoOffline
from soldagem.models import Modulo, Componente, Pedido, Turno, Apontamento, TipoParada, Parada
from qualidade.models import TipoDefeito, Defeito, CalculoOEE

# Personalização do Admin
admin.site.site_header = 'Sistema OEE - Administração'
admin.site.site_title = 'Sistema OEE'
admin.site.index_title = 'Painel Administrativo'

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('username', 'nome_completo', 'email', 'tipo_usuario', 'ativo', 'data_criacao', 'ultimo_login')
    list_filter = ('tipo_usuario', 'ativo', 'data_criacao')
    search_fields = ('username', 'nome_completo', 'email')
    ordering = ('nome_completo',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('nome_completo', 'email')}),
        ('Permissões', {'fields': ('tipo_usuario', 'ativo', 'is_staff', 'is_superuser')}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'nome_completo', 'email', 'tipo_usuario', 'password1', 'password2'),
        }),
    )

@admin.register(Soldador)
class SoldadorAdmin(admin.ModelAdmin):
    list_display = ('get_nome', 'senha_simplificada', 'ativo', 'data_cadastro')
    list_filter = ('ativo', 'data_cadastro')
    search_fields = ('usuario__nome_completo', 'usuario__username')
    raw_id_fields = ('usuario',)
    
    def get_nome(self, obj):
        return obj.usuario.nome_completo
    get_nome.short_description = 'Nome Completo'

@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao', 'ordem_exibicao', 'ativo', 'data_criacao')
    list_filter = ('ativo', 'data_criacao')
    search_fields = ('nome', 'descricao')
    ordering = ('ordem_exibicao', 'nome')

@admin.register(Componente)
class ComponenteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tempo_padrao', 'considera_diametro', 'ativo', 'data_criacao')
    list_filter = ('considera_diametro', 'ativo', 'data_criacao')
    search_fields = ('nome', 'descricao')
    ordering = ('nome',)

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'descricao', 'status', 'data_criacao', 'data_prevista')
    list_filter = ('status', 'data_criacao')
    search_fields = ('numero', 'descricao')
    ordering = ('-data_criacao',)

@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ('get_soldador', 'data_turno', 'inicio_turno', 'fim_turno', 'horas_disponiveis', 'status')
    list_filter = ('status', 'data_turno')
    search_fields = ('soldador__usuario__nome_completo',)
    raw_id_fields = ('soldador',)
    date_hierarchy = 'data_turno'
    
    def get_soldador(self, obj):
        return obj.soldador.usuario.nome_completo
    get_soldador.short_description = 'Soldador'

@admin.register(Apontamento)
class ApontamentoAdmin(admin.ModelAdmin):
    list_display = ('get_soldador', 'get_modulo', 'get_componente', 'inicio_processo', 'fim_processo', 'tempo_real', 'eficiencia_calculada')
    list_filter = ('modulo', 'componente', 'inicio_processo')
    search_fields = ('soldador__usuario__nome_completo', 'pedido__numero', 'numero_poste_tubo')
    raw_id_fields = ('soldador', 'modulo', 'componente', 'pedido', 'turno')
    date_hierarchy = 'inicio_processo'
    readonly_fields = ('tempo_real', 'eficiencia_calculada', 'data_criacao')
    
    def get_soldador(self, obj):
        return obj.soldador.usuario.nome_completo
    get_soldador.short_description = 'Soldador'
    
    def get_modulo(self, obj):
        return obj.modulo.nome
    get_modulo.short_description = 'Módulo'
    
    def get_componente(self, obj):
        return obj.componente.nome
    get_componente.short_description = 'Componente'

@admin.register(TipoParada)
class TipoParadaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'penaliza_oee', 'requer_senha_especial', 'ativo', 'cor_badge')
    list_filter = ('categoria', 'penaliza_oee', 'requer_senha_especial', 'ativo')
    search_fields = ('nome',)
    ordering = ('categoria', 'nome')
    
    def cor_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            obj.cor_exibicao,
            obj.cor_exibicao
        )
    cor_badge.short_description = 'Cor'

@admin.register(Parada)
class ParadaAdmin(admin.ModelAdmin):
    list_display = ('get_soldador', 'tipo_parada', 'inicio', 'fim', 'duracao_minutos', 'get_usuario_autorizacao')
    list_filter = ('tipo_parada__categoria', 'tipo_parada', 'inicio')
    search_fields = ('soldador__usuario__nome_completo', 'motivo_detalhado')
    raw_id_fields = ('soldador', 'apontamento', 'turno', 'usuario_autorizacao')
    date_hierarchy = 'inicio'
    readonly_fields = ('duracao_minutos', 'data_criacao')
    
    def get_soldador(self, obj):
        return obj.soldador.usuario.nome_completo
    get_soldador.short_description = 'Soldador'
    
    def get_usuario_autorizacao(self, obj):
        return obj.usuario_autorizacao.nome_completo if obj.usuario_autorizacao else '-'
    get_usuario_autorizacao.short_description = 'Autorizado por'

@admin.register(TipoDefeito)
class TipoDefeitoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao', 'ativo', 'cor_badge')
    list_filter = ('ativo',)
    search_fields = ('nome', 'descricao')
    ordering = ('nome',)
    
    def cor_badge(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            obj.cor_exibicao,
            obj.cor_exibicao
        )
    cor_badge.short_description = 'Cor'

@admin.register(Defeito)
class DefeitoAdmin(admin.ModelAdmin):
    list_display = ('get_soldador', 'tipo_defeito', 'tamanho_mm', 'area_defeito', 'data_deteccao', 'get_usuario_qualidade')
    list_filter = ('tipo_defeito', 'data_deteccao')
    search_fields = ('soldador__usuario__nome_completo', 'observacoes')
    raw_id_fields = ('apontamento', 'soldador', 'usuario_qualidade')
    date_hierarchy = 'data_deteccao'
    readonly_fields = ('area_defeito',)
    
    def get_soldador(self, obj):
        return obj.soldador.usuario.nome_completo
    get_soldador.short_description = 'Soldador'
    
    def get_usuario_qualidade(self, obj):
        return obj.usuario_qualidade.nome_completo
    get_usuario_qualidade.short_description = 'Avaliado por'

@admin.register(CalculoOEE)
class CalculoOEEAdmin(admin.ModelAdmin):
    list_display = ('get_soldador', 'get_modulo', 'data_calculo', 'utilizacao', 'eficiencia', 'qualidade', 'oee_final')
    list_filter = ('data_calculo', 'soldador', 'modulo')
    search_fields = ('soldador__usuario__nome_completo',)
    raw_id_fields = ('soldador', 'modulo')
    date_hierarchy = 'data_calculo'
    readonly_fields = ('timestamp_calculo',)
    
    def get_soldador(self, obj):
        return obj.soldador.usuario.nome_completo if obj.soldador else 'Geral'
    get_soldador.short_description = 'Soldador'
    
    def get_modulo(self, obj):
        return obj.modulo.nome if obj.modulo else 'Todos'
    get_modulo.short_description = 'Módulo'

@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = ('chave', 'valor', 'tipo_dado', 'data_atualizacao')
    list_filter = ('tipo_dado', 'data_atualizacao')
    search_fields = ('chave', 'descricao')
    ordering = ('chave',)

@admin.register(HoraTrabalho)
class HoraTrabalhoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hora_inicio', 'hora_fim', 'horas_disponiveis', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    ordering = ('nome',)

@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'get_usuario', 'acao', 'tabela_afetada', 'registro_id', 'ip_address')
    list_filter = ('timestamp', 'tabela_afetada', 'usuario')
    search_fields = ('acao', 'tabela_afetada')
    raw_id_fields = ('usuario',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
    
    def get_usuario(self, obj):
        return obj.usuario.nome_completo if obj.usuario else 'Sistema'
    get_usuario.short_description = 'Usuário'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(LogSincronizacao)
class LogSincronizacaoAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'dispositivo_id', 'tipo_operacao', 'tabela', 'registros_afetados', 'status')
    list_filter = ('timestamp', 'tipo_operacao', 'status')
    search_fields = ('dispositivo_id', 'tabela', 'mensagem_erro')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(SessaoOffline)
class SessaoOfflineAdmin(admin.ModelAdmin):
    list_display = ('dispositivo_id', 'get_soldador', 'ultimo_sync', 'status_conexao')
    list_filter = ('ultimo_sync', 'status_conexao')
    search_fields = ('dispositivo_id', 'soldador__usuario__nome_completo')
    raw_id_fields = ('soldador',)
    readonly_fields = ('ultimo_sync',)
    
    def get_soldador(self, obj):
        return obj.soldador.usuario.nome_completo
    get_soldador.short_description = 'Soldador'
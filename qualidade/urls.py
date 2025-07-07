from django.urls import path
from . import views

app_name = 'qualidade'

urlpatterns = [
    # Painel principal
    path('', views.painel_qualidade, name='painel_qualidade'),
    
    # Avaliação de qualidade
    path('avaliacao/', views.avaliacao_qualidade, name='avaliacao'),
    path('avaliacao/<int:apontamento_id>/', views.avaliacao_qualidade, name='avaliacao_apontamento'),
    
    # Histórico e relatórios
    path('historico/', views.historico_defeitos, name='historico'),
    path('estatisticas/', views.estatisticas_qualidade, name='estatisticas'),
    
    # APIs
    path('api/apontamentos_soldador/', views.buscar_apontamentos_soldador, name='api_apontamentos_soldador'),
    path('api/registrar_defeito/', views.registrar_defeito, name='api_registrar_defeito'),
    path('api/dados_grafico/', views.dados_grafico_qualidade, name='api_dados_grafico'),
]
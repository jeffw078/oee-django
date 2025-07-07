from django.urls import path
from . import views

app_name = 'manutencao'

urlpatterns = [
    # Painel principal
    path('', views.painel_manutencao, name='painel'),
    
    # Paradas de manutenção
    path('iniciar/', views.iniciar_parada_manutencao, name='iniciar_parada'),
    path('iniciar/<int:apontamento_id>/', views.iniciar_parada_manutencao, name='iniciar_parada_apontamento'),
    path('finalizar/', views.finalizar_parada_manutencao, name='finalizar_parada'),
    
    # Histórico e relatórios
    path('historico/', views.historico_paradas_manutencao, name='historico'),
    path('estatisticas/', views.estatisticas_manutencao, name='estatisticas'),
    
    # APIs
    path('api/soldadores_ativos/', views.buscar_soldadores_ativos, name='api_soldadores_ativos'),
    path('api/dados_grafico/', views.dados_grafico_manutencao, name='api_dados_grafico'),
]
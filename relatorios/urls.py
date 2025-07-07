from django.urls import path
from . import views

app_name = 'relatorios'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_principal, name='dashboard'),
    
    # Relatórios detalhados
    path('oee/', views.relatorio_oee, name='oee'),
    path('pontos-melhoria/', views.pontos_melhoria, name='pontos_melhoria'),
    path('paradas/', views.relatorio_paradas, name='paradas'),
    
    # Gráficos especiais
    path('utilizacao/', views.grafico_utilizacao, name='utilizacao'),
    path('eficiencia/', views.grafico_eficiencia, name='eficiencia'),
    
    # APIs para dados dos gráficos
    path('api/dados-oee/', views.api_dados_oee, name='api_dados_oee'),
    path('api/dados-eficiencia/', views.api_dados_eficiencia_dispersao, name='api_dados_eficiencia'),
]
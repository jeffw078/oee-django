from django.urls import path
from . import views

app_name = 'soldagem'

urlpatterns = [
    # Telas principais
    path('', views.selecao_soldador, name='selecao_soldador'),
    path('login_soldador/', views.login_soldador, name='login_soldador'),
    path('apontamento/', views.tela_apontamento, name='apontamento'),
    path('finalizar_turno/', views.finalizar_turno, name='finalizar_turno'),
    
    # Processo de soldagem
    path('modulo/<int:modulo_id>/', views.selecionar_modulo, name='selecionar_modulo'),
    path('componente/', views.selecionar_componente, name='selecionar_componente'),
    path('iniciar/', views.iniciar_soldagem, name='iniciar_soldagem'),
    path('processo/<int:apontamento_id>/', views.processo_soldagem, name='processo_soldagem'),
    path('finalizar/<int:apontamento_id>/', views.finalizar_soldagem, name='finalizar_soldagem'),
    
    # APIs para funcionalidade offline
    path('api/status/', views.api_status_conexao, name='api_status'),
    path('api/sync/', views.api_sincronizar_dados, name='api_sync'),
]
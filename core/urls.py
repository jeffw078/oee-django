from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Painel administrativo
    path('admin/', views.painel_admin, name='admin'),
    
    # Cadastros
    path('admin/usuarios/', views.gerenciar_usuarios, name='usuarios'),
    path('admin/soldadores/', views.gerenciar_soldadores, name='soldadores'),
    path('admin/componentes/', views.gerenciar_componentes, name='componentes'),
    path('admin/modulos/', views.gerenciar_modulos, name='modulos'),
    path('admin/paradas/', views.gerenciar_tipos_parada, name='tipos_parada'),
    path('admin/defeitos/', views.gerenciar_tipos_defeito, name='tipos_defeito'),
    path('admin/horas-trabalho/', views.gerenciar_horas_trabalho, name='horas_trabalho'),
    path('admin/apontamentos/', views.gerenciar_apontamentos, name='apontamentos'),
    
    # APIs para cadastros
    path('api/salvar-usuario/', views.api_salvar_usuario, name='api_salvar_usuario'),
    path('api/salvar-soldador/', views.api_salvar_soldador, name='api_salvar_soldador'),
    path('api/salvar-componente/', views.api_salvar_componente, name='api_salvar_componente'),
    path('api/excluir-item/', views.api_excluir_item, name='api_excluir_item'),
]
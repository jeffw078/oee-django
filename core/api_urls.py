from django.urls import path
from . import api_views

app_name = 'api'

urlpatterns = [
    # Status e conexão
    path('status/', api_views.api_status, name='status'),
    path('heartbeat/', api_views.api_heartbeat, name='heartbeat'),
    
    # Sincronização offline
    path('sync/upload/', api_views.api_sync_upload, name='sync_upload'),
    path('sync/download/', api_views.api_sync_download, name='sync_download'),
    path('sync/status/', api_views.api_sync_status, name='sync_status'),
    
    # Cache de dados essenciais
    path('cache/soldadores/', api_views.api_cache_soldadores, name='cache_soldadores'),
    path('cache/componentes/', api_views.api_cache_componentes, name='cache_componentes'),
    path('cache/modulos/', api_views.api_cache_modulos, name='cache_modulos'),
    path('cache/tipos-parada/', api_views.api_cache_tipos_parada, name='cache_tipos_parada'),
    
    # Sessão offline
    path('session/create/', api_views.api_create_offline_session, name='create_offline_session'),
    path('session/update/', api_views.api_update_offline_session, name='update_offline_session'),
    path('session/close/', api_views.api_close_offline_session, name='close_offline_session'),
]
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/soldagem/', permanent=False)),
    path('soldagem/', include('soldagem.urls')),
    path('qualidade/', include('qualidade.urls')),
    path('manutencao/', include('manutencao.urls')),
    path('relatorios/', include('relatorios.urls')),
    path('core/', include('core.urls')),
    path('api/', include('core.api_urls')),  # Para funcionalidade offline
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
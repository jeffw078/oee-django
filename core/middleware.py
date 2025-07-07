import json
import os
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from core.models import LogAuditoria

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Processar antes da view
        request_data = self.capture_request_data(request)
        
        response = self.get_response(request)
        
        # Processar depois da view (se necessário)
        if hasattr(request, '_audit_action'):
            self.log_action(
                request, 
                request._audit_action, 
                getattr(request, '_audit_table', ''),
                getattr(request, '_audit_record_id', None),
                getattr(request, '_audit_data_before', None),
                getattr(request, '_audit_data_after', None)
            )
        
        return response

    def capture_request_data(self, request):
        """Captura dados da requisição para auditoria"""
        return {
            'method': request.method,
            'path': request.path,
            'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
            'ip': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')
        }

    def get_client_ip(self, request):
        """Obtém o IP real do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def log_action(self, request, acao, tabela='', registro_id=None, dados_antes=None, dados_depois=None):
        """Registra ação de auditoria"""
        try:
            # Salvar no banco
            usuario = request.user if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) else None
            
            LogAuditoria.objects.create(
                usuario=usuario,
                acao=acao,
                tabela_afetada=tabela,
                registro_id=registro_id,
                dados_antes=dados_antes,
                dados_depois=dados_depois,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Salvar em arquivo txt
            self.log_to_file(request, acao, tabela, registro_id, dados_antes, dados_depois)
            
        except Exception as e:
            # Em caso de erro, pelo menos tenta salvar no arquivo
            self.log_to_file(request, f"ERRO_AUDITORIA: {acao} - {str(e)}")

    def log_to_file(self, request, acao, tabela='', registro_id=None, dados_antes=None, dados_depois=None):
        """Salva log de auditoria em arquivo txt"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'usuario': str(request.user) if hasattr(request, 'user') else 'Anonymous',
                'ip': self.get_client_ip(request),
                'acao': acao,
                'tabela': tabela,
                'registro_id': registro_id,
                'dados_antes': dados_antes,
                'dados_depois': dados_depois,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }
            
            log_line = json.dumps(log_entry, ensure_ascii=False, default=str) + '\n'
            
            # Garantir que o diretório existe
            os.makedirs(os.path.dirname(settings.AUDIT_LOG_FILE), exist_ok=True)
            
            with open(settings.AUDIT_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_line)
                
        except Exception as e:
            print(f"Erro ao salvar log de auditoria: {e}")

# Função helper para marcar ações para auditoria
def mark_for_audit(request, action, table='', record_id=None, data_before=None, data_after=None):
    """Marca uma ação para ser auditada pelo middleware"""
    request._audit_action = action
    request._audit_table = table
    request._audit_record_id = record_id
    request._audit_data_before = data_before
    request._audit_data_after = data_after
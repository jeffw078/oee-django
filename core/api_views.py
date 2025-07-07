from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
import json
import uuid

from .models import SessaoOffline, LogSincronizacao, Soldador
from soldagem.models import Modulo, Componente, TipoParada, Apontamento, Parada
from qualidade.models import TipoDefeito, Defeito

@csrf_exempt
def api_status(request):
    """API para verificar status do servidor"""
    return JsonResponse({
        'status': 'online',
        'timestamp': timezone.now().isoformat(),
        'servidor_ativo': True,
        'versao': '1.0.0'
    })

@csrf_exempt
def api_heartbeat(request):
    """API de heartbeat para monitoramento de conexão"""
    return JsonResponse({
        'heartbeat': 'ok',
        'timestamp': timezone.now().isoformat()
    })

@csrf_exempt
def api_sync_upload(request):
    """API para upload de dados offline para o servidor"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                dispositivo_id = data.get('dispositivo_id', str(uuid.uuid4()))
                dados_offline = data.get('dados', [])
                
                resultados = []
                registros_processados = 0
                
                for item in dados_offline:
                    try:
                        tipo_dado = item.get('tipo')
                        dados_item = item.get('dados')
                        id_local = item.get('id_local')
                        timestamp_local = item.get('timestamp')
                        
                        id_servidor = None
                        
                        # Processar baseado no tipo de dado
                        if tipo_dado == 'apontamento_inicio':
                            id_servidor = processar_apontamento_inicio(dados_item, timestamp_local)
                        elif tipo_dado == 'apontamento_fim':
                            id_servidor = processar_apontamento_fim(dados_item, timestamp_local)
                        elif tipo_dado == 'parada_inicio':
                            id_servidor = processar_parada_inicio(dados_item, timestamp_local)
                        elif tipo_dado == 'parada_fim':
                            id_servidor = processar_parada_fim(dados_item, timestamp_local)
                        elif tipo_dado == 'defeito':
                            id_servidor = processar_defeito(dados_item, timestamp_local)
                        
                        resultados.append({
                            'id_local': id_local,
                            'id_servidor': id_servidor,
                            'status': 'sucesso',
                            'tipo': tipo_dado
                        })
                        
                        registros_processados += 1
                        
                    except Exception as e:
                        resultados.append({
                            'id_local': item.get('id_local'),
                            'status': 'erro',
                            'erro': str(e),
                            'tipo': item.get('tipo')
                        })
                
                # Log de sincronização
                LogSincronizacao.objects.create(
                    dispositivo_id=dispositivo_id,
                    tipo_operacao='upload',
                    tabela='multiplas',
                    registros_afetados=registros_processados,
                    status='sucesso' if registros_processados > 0 else 'erro',
                    mensagem_erro='' if registros_processados > 0 else 'Nenhum registro processado'
                )
                
                return JsonResponse({
                    'success': True,
                    'registros_processados': registros_processados,
                    'resultados': resultados,
                    'timestamp_servidor': timezone.now().isoformat()
                })
                
        except Exception as e:
            # Log de erro
            LogSincronizacao.objects.create(
                dispositivo_id=data.get('dispositivo_id', 'unknown'),
                tipo_operacao='upload',
                tabela='erro',
                registros_afetados=0,
                status='erro',
                mensagem_erro=str(e)
            )
            
            return JsonResponse({
                'success': False,
                'message': f'Erro na sincronização: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@csrf_exempt
def api_sync_download(request):
    """API para download de dados do servidor para cache offline"""
    if request.method == 'GET':
        try:
            ultimo_sync = request.GET.get('ultimo_sync')
            dispositivo_id = request.GET.get('dispositivo_id')
            
            dados = {
                'soldadores': [],
                'modulos': [],
                'componentes': [],
                'tipos_parada': [],
                'tipos_defeito': [],
                'timestamp': timezone.now().isoformat()
            }
            
            # Cache de soldadores
            for soldador in Soldador.objects.filter(ativo=True):
                dados['soldadores'].append({
                    'id': soldador.id,
                    'nome': soldador.usuario.nome_completo,
                    'username': soldador.usuario.username,
                    'senha_simplificada': soldador.senha_simplificada,
                    'ativo': soldador.ativo
                })
            
            # Cache de módulos
            for modulo in Modulo.objects.filter(ativo=True):
                dados['modulos'].append({
                    'id': modulo.id,
                    'nome': modulo.nome,
                    'descricao': modulo.descricao,
                    'ordem_exibicao': modulo.ordem_exibicao
                })
            
            # Cache de componentes
            for componente in Componente.objects.filter(ativo=True):
                dados['componentes'].append({
                    'id': componente.id,
                    'nome': componente.nome,
                    'descricao': componente.descricao,
                    'tempo_padrao': float(componente.tempo_padrao),
                    'considera_diametro': componente.considera_diametro,
                    'formula_calculo': componente.formula_calculo
                })
            
            # Cache de tipos de parada
            for tipo_parada in TipoParada.objects.filter(ativo=True):
                dados['tipos_parada'].append({
                    'id': tipo_parada.id,
                    'nome': tipo_parada.nome,
                    'categoria': tipo_parada.categoria,
                    'penaliza_oee': tipo_parada.penaliza_oee,
                    'requer_senha_especial': tipo_parada.requer_senha_especial,
                    'cor_exibicao': tipo_parada.cor_exibicao
                })
            
            # Cache de tipos de defeito
            for tipo_defeito in TipoDefeito.objects.filter(ativo=True):
                dados['tipos_defeito'].append({
                    'id': tipo_defeito.id,
                    'nome': tipo_defeito.nome,
                    'descricao': tipo_defeito.descricao,
                    'cor_exibicao': tipo_defeito.cor_exibicao
                })
            
            # Log de sincronização
            LogSincronizacao.objects.create(
                dispositivo_id=dispositivo_id or 'unknown',
                tipo_operacao='download',
                tabela='cache_completo',
                registros_afetados=len(dados['soldadores']) + len(dados['modulos']) + len(dados['componentes']),
                status='sucesso'
            )
            
            return JsonResponse({
                'success': True,
                'dados': dados
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao baixar cache: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@csrf_exempt
def api_sync_status(request):
    """API para verificar status de sincronização"""
    dispositivo_id = request.GET.get('dispositivo_id')
    
    if dispositivo_id:
        logs_recentes = LogSincronizacao.objects.filter(
            dispositivo_id=dispositivo_id
        ).order_by('-timestamp')[:10]
        
        logs_data = []
        for log in logs_recentes:
            logs_data.append({
                'tipo_operacao': log.tipo_operacao,
                'tabela': log.tabela,
                'registros_afetados': log.registros_afetados,
                'status': log.status,
                'mensagem_erro': log.mensagem_erro,
                'timestamp': log.timestamp.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'logs': logs_data
        })
    
    return JsonResponse({
        'success': False,
        'message': 'dispositivo_id necessário'
    })

# APIs específicas para cache
@csrf_exempt
def api_cache_soldadores(request):
    """Cache específico de soldadores"""
    soldadores = []
    for soldador in Soldador.objects.filter(ativo=True):
        soldadores.append({
            'id': soldador.id,
            'nome': soldador.usuario.nome_completo,
            'senha_simplificada': soldador.senha_simplificada
        })
    
    return JsonResponse({
        'success': True,
        'soldadores': soldadores,
        'timestamp': timezone.now().isoformat()
    })

@csrf_exempt
def api_cache_componentes(request):
    """Cache específico de componentes"""
    componentes = []
    for componente in Componente.objects.filter(ativo=True):
        componentes.append({
            'id': componente.id,
            'nome': componente.nome,
            'tempo_padrao': float(componente.tempo_padrao),
            'considera_diametro': componente.considera_diametro,
            'formula_calculo': componente.formula_calculo
        })
    
    return JsonResponse({
        'success': True,
        'componentes': componentes,
        'timestamp': timezone.now().isoformat()
    })

@csrf_exempt
def api_cache_modulos(request):
    """Cache específico de módulos"""
    modulos = []
    for modulo in Modulo.objects.filter(ativo=True):
        modulos.append({
            'id': modulo.id,
            'nome': modulo.nome,
            'ordem_exibicao': modulo.ordem_exibicao
        })
    
    return JsonResponse({
        'success': True,
        'modulos': modulos,
        'timestamp': timezone.now().isoformat()
    })

@csrf_exempt
def api_cache_tipos_parada(request):
    """Cache específico de tipos de parada"""
    tipos_parada = []
    for tipo in TipoParada.objects.filter(ativo=True):
        tipos_parada.append({
            'id': tipo.id,
            'nome': tipo.nome,
            'categoria': tipo.categoria,
            'requer_senha_especial': tipo.requer_senha_especial
        })
    
    return JsonResponse({
        'success': True,
        'tipos_parada': tipos_parada,
        'timestamp': timezone.now().isoformat()
    })

# Sessões offline
@csrf_exempt
def api_create_offline_session(request):
    """Criar sessão offline"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dispositivo_id = data.get('dispositivo_id', str(uuid.uuid4()))
            soldador_id = data.get('soldador_id')
            
            soldador = Soldador.objects.get(id=soldador_id)
            
            sessao, created = SessaoOffline.objects.get_or_create(
                dispositivo_id=dispositivo_id,
                defaults={
                    'soldador': soldador,
                    'dados_cache': {},
                    'status_conexao': False
                }
            )
            
            if not created:
                sessao.soldador = soldador
                sessao.ultimo_sync = timezone.now()
                sessao.save()
            
            return JsonResponse({
                'success': True,
                'sessao_id': sessao.id,
                'dispositivo_id': dispositivo_id
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@csrf_exempt
def api_update_offline_session(request):
    """Atualizar sessão offline"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dispositivo_id = data.get('dispositivo_id')
            dados_cache = data.get('dados_cache', {})
            
            sessao = SessaoOffline.objects.get(dispositivo_id=dispositivo_id)
            sessao.dados_cache = dados_cache
            sessao.ultimo_sync = timezone.now()
            sessao.status_conexao = True
            sessao.save()
            
            return JsonResponse({
                'success': True,
                'ultimo_sync': sessao.ultimo_sync.isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@csrf_exempt
def api_close_offline_session(request):
    """Fechar sessão offline"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dispositivo_id = data.get('dispositivo_id')
            
            SessaoOffline.objects.filter(dispositivo_id=dispositivo_id).delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Sessão offline fechada'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

# Funções auxiliares para processamento de dados offline
def processar_apontamento_inicio(dados, timestamp_local):
    """Processar início de apontamento vindo do offline"""
    # Implementar lógica para criar apontamento
    # Retornar ID do servidor
    pass

def processar_apontamento_fim(dados, timestamp_local):
    """Processar fim de apontamento vindo do offline"""
    # Implementar lógica para finalizar apontamento
    # Retornar ID do servidor
    pass

def processar_parada_inicio(dados, timestamp_local):
    """Processar início de parada vindo do offline"""
    # Implementar lógica para criar parada
    # Retornar ID do servidor
    pass

def processar_parada_fim(dados, timestamp_local):
    """Processar fim de parada vindo do offline"""
    # Implementar lógica para finalizar parada
    # Retornar ID do servidor
    pass

def processar_defeito(dados, timestamp_local):
    """Processar defeito vindo do offline"""
    # Implementar lógica para criar defeito
    # Retornar ID do servidor
    pass
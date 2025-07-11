from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from datetime import datetime, time, date
import json
from core.models import Soldador, Usuario
from core.middleware import mark_for_audit
from .models import (
    Modulo, Componente, Pedido, Turno, Apontamento, 
    TipoParada, Parada
)

def selecao_soldador(request):
    """Tela inicial de seleção de soldador"""
    soldadores = Soldador.objects.filter(ativo=True).order_by('usuario__nome_completo')
    
    context = {
        'soldadores': soldadores,
        'titulo': 'Sistema de Apontamento OEE',
    }
    
    return render(request, 'soldagem/selecao_soldador.html', context)

@csrf_exempt
def login_soldador(request):
    """Login simplificado para soldador"""
    if request.method == 'POST':
        data = json.loads(request.body)
        soldador_id = data.get('soldador_id')
        senha = data.get('senha')
        
        try:
            soldador = Soldador.objects.get(id=soldador_id, ativo=True)
            
            if soldador.senha_simplificada == senha:
                # Fazer login do usuário
                user = soldador.usuario
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                
                # Atualizar último login
                user.ultimo_login = timezone.now()
                user.save()
                
                # Criar ou ativar turno
                turno_ativo = Turno.objects.filter(
                    soldador=soldador,
                    data_turno=timezone.now().date(),
                    status='ativo'
                ).first()
                
                if not turno_ativo:
                    turno_ativo = Turno.objects.create(
                        soldador=soldador,
                        data_turno=timezone.now().date(),
                        inicio_turno=timezone.now(),
                        horas_disponiveis=8  # Padrão, pode ser configurável
                    )
                
                # Auditoria
                mark_for_audit(
                    request, 
                    f"Login soldador: {soldador.usuario.nome_completo}",
                    'soldador',
                    soldador.id
                )
                
                return JsonResponse({
                    'success': True,
                    'redirect_url': '/soldagem/apontamento/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Senha incorreta'
                })
                
        except Soldador.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Soldador não encontrado'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@login_required
def tela_apontamento(request):
    """Tela principal de apontamento"""
    if not hasattr(request.user, 'soldador_profile'):
        messages.error(request, 'Usuário não é um soldador válido')
        return redirect('soldagem:selecao_soldador')
    
    soldador = request.user.soldador_profile
    
    # Buscar turno ativo
    turno_ativo = Turno.objects.filter(
        soldador=soldador,
        data_turno=timezone.now().date(),
        status='ativo'
    ).first()
    
    # Buscar módulos ativos
    modulos = Modulo.objects.filter(ativo=True).order_by('ordem_exibicao')
    
    # Buscar apontamento em andamento
    apontamento_ativo = Apontamento.objects.filter(
        soldador=soldador,
        fim_processo__isnull=True
    ).first()
    
    # Buscar parada ativa
    parada_ativa = Parada.objects.filter(
        soldador=soldador,
        fim__isnull=True
    ).first()
    
    # Obter saudação
    hora_atual = timezone.now().hour
    if hora_atual < 12:
        saudacao = "Bom dia"
    elif hora_atual < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"
    
    context = {
        'soldador': soldador,
        'turno_ativo': turno_ativo,
        'modulos': modulos,
        'apontamento_ativo': apontamento_ativo,
        'parada_ativa': parada_ativa,
        'saudacao': saudacao,
    }
    
    return render(request, 'soldagem/tela_apontamento.html', context)

@login_required
def selecionar_modulo(request, modulo_id):
    """Iniciar processo de seleção de componente"""
    modulo = get_object_or_404(Modulo, id=modulo_id, ativo=True)
    soldador = request.user.soldador_profile
    
    if request.method == 'POST':
        numero_pedido = request.POST.get('numero_pedido')
        numero_poste_tubo = request.POST.get('numero_poste_tubo')
        
        # Buscar ou criar pedido
        pedido, created = Pedido.objects.get_or_create(
            numero=numero_pedido,
            defaults={'descricao': f'Pedido {numero_pedido}'}
        )
        
        # Salvar na sessão para usar na seleção do componente
        request.session['modulo_id'] = modulo.id
        request.session['pedido_id'] = pedido.id
        request.session['numero_poste_tubo'] = numero_poste_tubo
        
        return redirect('soldagem:selecionar_componente')
    
    context = {
        'modulo': modulo,
        'soldador': soldador,
    }
    
    return render(request, 'soldagem/selecionar_modulo.html', context)

@login_required
def selecionar_componente(request):
    """Selecionar componente para soldagem"""
    soldador = request.user.soldador_profile
    
    # Recuperar dados da sessão
    modulo_id = request.session.get('modulo_id')
    if not modulo_id:
        return redirect('soldagem:apontamento')
    
    modulo = get_object_or_404(Modulo, id=modulo_id)
    
    # ALTERAR ESTA LINHA: filtrar componentes pelo módulo
    componentes = Componente.objects.filter(modulo=modulo, ativo=True).order_by('nome')
    
    context = {
        'modulo': modulo,
        'componentes': componentes,
        'soldador': soldador,
    }
    
    return render(request, 'soldagem/selecionar_componente.html', context)

# Também adicione esta importação no início do arquivo se não existir:
from django.contrib.auth import logout
@login_required
@csrf_exempt
def iniciar_soldagem(request):
    """Iniciar processo de soldagem"""
    if request.method == 'POST':
        data = json.loads(request.body)
        componente_id = data.get('componente_id')
        diametro = data.get('diametro')
        
        try:
            with transaction.atomic():
                soldador = request.user.soldador_profile
                componente = Componente.objects.get(id=componente_id)
                
                # Recuperar dados da sessão
                modulo_id = request.session.get('modulo_id')
                pedido_id = request.session.get('pedido_id')
                numero_poste_tubo = request.session.get('numero_poste_tubo')
                
                modulo = Modulo.objects.get(id=modulo_id)
                pedido = Pedido.objects.get(id=pedido_id)
                
                # Buscar turno ativo
                turno_ativo = Turno.objects.filter(
                    soldador=soldador,
                    data_turno=timezone.now().date(),
                    status='ativo'
                ).first()
                
                # Criar apontamento
                apontamento = Apontamento.objects.create(
                    soldador=soldador,
                    modulo=modulo,
                    componente=componente,
                    pedido=pedido,
                    turno=turno_ativo,
                    numero_poste_tubo=numero_poste_tubo,
                    diametro=diametro if componente.considera_diametro else None,
                    inicio_processo=timezone.now(),
                    tempo_padrao=componente.calcular_tempo_padrao(diametro)
                )
                
                # Auditoria
                mark_for_audit(
                    request,
                    f"Iniciou soldagem: {componente.nome}",
                    'apontamento',
                    apontamento.id,
                    None,
                    {
                        'componente': componente.nome,
                        'modulo': modulo.nome,
                        'pedido': pedido.numero,
                        'poste_tubo': numero_poste_tubo
                    }
                )
                
                # Limpar sessão
                for key in ['modulo_id', 'pedido_id', 'numero_poste_tubo']:
                    if key in request.session:
                        del request.session[key]
                
                return JsonResponse({
                    'success': True,
                    'apontamento_id': apontamento.id,
                    'redirect_url': f'/soldagem/processo/{apontamento.id}/'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao iniciar soldagem: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@login_required
def processo_soldagem(request, apontamento_id):
    """Tela do processo de soldagem em andamento"""
    apontamento = get_object_or_404(
        Apontamento, 
        id=apontamento_id, 
        soldador=request.user.soldador_profile,
        fim_processo__isnull=True
    )
    
    # Buscar tipos de parada
    tipos_parada_geral = TipoParada.objects.filter(
        categoria='geral', 
        ativo=True
    ).order_by('nome')
    
    context = {
        'apontamento': apontamento,
        'tipos_parada_geral': tipos_parada_geral,
    }
    
    return render(request, 'soldagem/processo_soldagem.html', context)

@login_required
@csrf_exempt
def finalizar_soldagem(request, apontamento_id):
    """Finalizar processo de soldagem"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                apontamento = get_object_or_404(
                    Apontamento,
                    id=apontamento_id,
                    soldador=request.user.soldador_profile,
                    fim_processo__isnull=True
                )
                
                dados_antes = {
                    'componente': apontamento.componente.nome,
                    'inicio': str(apontamento.inicio_processo),
                    'status': 'em_andamento'
                }
                
                # Finalizar apontamento
                apontamento.fim_processo = timezone.now()
                apontamento.save()  # O save() calculará automaticamente tempo_real e eficiência
                
                dados_depois = {
                    'componente': apontamento.componente.nome,
                    'inicio': str(apontamento.inicio_processo),
                    'fim': str(apontamento.fim_processo),
                    'tempo_real': str(apontamento.tempo_real),
                    'eficiencia': str(apontamento.eficiencia_calculada),
                    'status': 'finalizado'
                }
                
                # Auditoria
                mark_for_audit(
                    request,
                    f"Finalizou soldagem: {apontamento.componente.nome}",
                    'apontamento',
                    apontamento.id,
                    dados_antes,
                    dados_depois
                )
                
                return JsonResponse({
                    'success': True,
                    'tempo_real': float(apontamento.tempo_real or 0),
                    'eficiencia': float(apontamento.eficiencia_calculada or 0),
                    'redirect_url': '/soldagem/apontamento/'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao finalizar soldagem: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

from django.contrib.auth import logout

@login_required
@csrf_exempt
def finalizar_turno(request):
    """Finalizar turno do soldador"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                soldador = request.user.soldador_profile
                
                # Finalizar turno ativo
                turno_ativo = Turno.objects.filter(
                    soldador=soldador,
                    data_turno=timezone.now().date(),
                    status='ativo'
                ).first()
                
                if turno_ativo:
                    turno_ativo.fim_turno = timezone.now()
                    turno_ativo.status = 'finalizado'
                    turno_ativo.save()
                
                # Auditoria
                mark_for_audit(
                    request,
                    f"Finalizou turno: {soldador.usuario.nome_completo}",
                    'turno',
                    turno_ativo.id if turno_ativo else None
                )
                
                # Logout
                logout(request)
                
                return JsonResponse({
                    'success': True,
                    'redirect_url': '/soldagem/'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao finalizar turno: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})
# APIs para funcionalidade offline
@csrf_exempt
def api_status_conexao(request):
    """API para verificar status da conexão"""
    return JsonResponse({
        'status': 'online',
        'timestamp': timezone.now().isoformat(),
        'servidor_ativo': True
    })

@csrf_exempt
def api_sincronizar_dados(request):
    """API para sincronizar dados offline"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dados_offline = data.get('dados', [])
            
            resultados = []
            
            for item in dados_offline:
                try:
                    # Processar cada item de dados offline
                    # Implementar lógica de sincronização aqui
                    resultados.append({
                        'id_local': item.get('id_local'),
                        'status': 'sucesso',
                        'id_servidor': None  # ID gerado no servidor
                    })
                except Exception as e:
                    resultados.append({
                        'id_local': item.get('id_local'),
                        'status': 'erro',
                        'erro': str(e)
                    })
            
            return JsonResponse({
                'success': True,
                'resultados': resultados
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})
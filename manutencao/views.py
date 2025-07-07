from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from datetime import datetime, date, timedelta
import json

from core.models import Usuario
from core.middleware import mark_for_audit
from soldagem.models import Apontamento, Soldador, TipoParada, Parada

@login_required
def painel_manutencao(request):
    """Painel principal da manutenção"""
    if request.user.tipo_usuario not in ['admin', 'manutencao']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    # Buscar paradas de manutenção ativas
    paradas_ativas = Parada.objects.filter(
        tipo_parada__categoria='manutencao',
        fim__isnull=True
    ).select_related('soldador', 'tipo_parada').order_by('-inicio')
    
    # Buscar tipos de parada de manutenção
    tipos_parada_manutencao = TipoParada.objects.filter(
        categoria='manutencao',
        ativo=True
    ).order_by('nome')
    
    # Estatísticas do dia
    hoje = timezone.now().date()
    paradas_hoje = Parada.objects.filter(
        tipo_parada__categoria='manutencao',
        inicio__date=hoje
    )
    
    total_paradas_hoje = paradas_hoje.count()
    tempo_total_paradas = sum([
        p.duracao_minutos or 0 for p in paradas_hoje if p.duracao_minutos
    ])
    
    context = {
        'paradas_ativas': paradas_ativas,
        'tipos_parada_manutencao': tipos_parada_manutencao,
        'estatisticas': {
            'total_paradas_hoje': total_paradas_hoje,
            'tempo_total_paradas': tempo_total_paradas,
            'media_tempo_parada': (tempo_total_paradas / total_paradas_hoje) if total_paradas_hoje > 0 else 0
        },
        'usuario': request.user,
    }
    
    return render(request, 'manutencao/painel_manutencao.html', context)

@login_required
def iniciar_parada_manutencao(request, apontamento_id=None):
    """Iniciar parada de manutenção"""
    if request.user.tipo_usuario not in ['admin', 'manutencao']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    apontamento = None
    if apontamento_id:
        apontamento = get_object_or_404(Apontamento, id=apontamento_id)
    
    # Buscar soldadores ativos
    soldadores = Soldador.objects.filter(ativo=True).order_by('usuario__nome_completo')
    
    # Buscar tipos de parada de manutenção
    tipos_parada_manutencao = TipoParada.objects.filter(
        categoria='manutencao',
        ativo=True
    ).order_by('nome')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                soldador_id = request.POST.get('soldador_id')
                tipo_parada_id = request.POST.get('tipo_parada_id')
                motivo_detalhado = request.POST.get('motivo_detalhado', '')
                
                soldador = Soldador.objects.get(id=soldador_id)
                tipo_parada = TipoParada.objects.get(id=tipo_parada_id)
                
                # Verificar se já existe parada ativa para este soldador
                parada_existente = Parada.objects.filter(
                    soldador=soldador,
                    fim__isnull=True
                ).first()
                
                if parada_existente:
                    messages.error(request, f'Soldador {soldador.usuario.nome_completo} já possui uma parada ativa.')
                    return redirect('manutencao:painel')
                
                # Criar parada de manutenção
                parada = Parada.objects.create(
                    tipo_parada=tipo_parada,
                    soldador=soldador,
                    apontamento=apontamento,
                    inicio=timezone.now(),
                    motivo_detalhado=motivo_detalhado,
                    usuario_autorizacao=request.user
                )
                
                # Auditoria
                mark_for_audit(
                    request,
                    f"Iniciou parada de manutenção: {tipo_parada.nome} para {soldador.usuario.nome_completo}",
                    'parada',
                    parada.id,
                    None,
                    {
                        'tipo_parada': tipo_parada.nome,
                        'soldador': soldador.usuario.nome_completo,
                        'motivo': motivo_detalhado,
                        'autorizado_por': request.user.nome_completo
                    }
                )
                
                messages.success(request, f'Parada de manutenção iniciada para {soldador.usuario.nome_completo}')
                return redirect('manutencao:painel')
                
        except Exception as e:
            messages.error(request, f'Erro ao iniciar parada: {str(e)}')
    
    context = {
        'apontamento': apontamento,
        'soldadores': soldadores,
        'tipos_parada_manutencao': tipos_parada_manutencao,
        'usuario': request.user,
    }
    
    return render(request, 'manutencao/iniciar_parada.html', context)

@csrf_exempt
@login_required
def finalizar_parada_manutencao(request):
    """Finalizar parada de manutenção"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                parada_id = data.get('parada_id')
                observacoes_finalizacao = data.get('observacoes', '')
                
                parada = Parada.objects.get(
                    id=parada_id,
                    tipo_parada__categoria='manutencao',
                    fim__isnull=True
                )
                
                dados_antes = {
                    'soldador': parada.soldador.usuario.nome_completo,
                    'tipo_parada': parada.tipo_parada.nome,
                    'inicio': str(parada.inicio),
                    'status': 'ativa'
                }
                
                # Finalizar parada
                parada.fim = timezone.now()
                parada.motivo_detalhado += f"\n\nObservações de finalização: {observacoes_finalizacao}"
                parada.save()  # O save() calculará automaticamente a duração
                
                dados_depois = {
                    'soldador': parada.soldador.usuario.nome_completo,
                    'tipo_parada': parada.tipo_parada.nome,
                    'inicio': str(parada.inicio),
                    'fim': str(parada.fim),
                    'duracao_minutos': float(parada.duracao_minutos),
                    'status': 'finalizada'
                }
                
                # Auditoria
                mark_for_audit(
                    request,
                    f"Finalizou parada de manutenção: {parada.tipo_parada.nome} - {parada.soldador.usuario.nome_completo}",
                    'parada',
                    parada.id,
                    dados_antes,
                    dados_depois
                )
                
                return JsonResponse({
                    'success': True,
                    'duracao_minutos': float(parada.duracao_minutos),
                    'message': 'Parada de manutenção finalizada com sucesso'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao finalizar parada: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@login_required
def historico_paradas_manutencao(request):
    """Histórico de paradas de manutenção"""
    if request.user.tipo_usuario not in ['admin', 'manutencao', 'analista']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    # Filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    soldador_id = request.GET.get('soldador')
    tipo_parada_id = request.GET.get('tipo_parada')
    
    # Query base
    paradas = Parada.objects.filter(
        tipo_parada__categoria='manutencao'
    ).select_related(
        'tipo_parada', 'soldador', 'usuario_autorizacao'
    ).order_by('-inicio')
    
    # Aplicar filtros
    if data_inicio:
        paradas = paradas.filter(inicio__date__gte=data_inicio)
    
    if data_fim:
        paradas = paradas.filter(inicio__date__lte=data_fim)
    
    if soldador_id:
        paradas = paradas.filter(soldador_id=soldador_id)
    
    if tipo_parada_id:
        paradas = paradas.filter(tipo_parada_id=tipo_parada_id)
    
    # Paginação (opcional)
    paradas = paradas[:100]  # Limitar a 100 registros por enquanto
    
    # Dados para filtros
    soldadores = Soldador.objects.filter(ativo=True).order_by('usuario__nome_completo')
    tipos_parada = TipoParada.objects.filter(
        categoria='manutencao',
        ativo=True
    ).order_by('nome')
    
    context = {
        'paradas': paradas,
        'soldadores': soldadores,
        'tipos_parada': tipos_parada,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'soldador_id': soldador_id,
            'tipo_parada_id': tipo_parada_id,
        }
    }
    
    return render(request, 'manutencao/historico_paradas.html', context)

@login_required
def estatisticas_manutencao(request):
    """Estatísticas de manutenção"""
    if request.user.tipo_usuario not in ['admin', 'manutencao', 'analista']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    hoje = timezone.now().date()
    
    # Paradas dos últimos 7 dias
    data_inicio = hoje - timedelta(days=6)
    paradas_periodo = Parada.objects.filter(
        tipo_parada__categoria='manutencao',
        inicio__date__gte=data_inicio,
        inicio__date__lte=hoje
    )
    
    # Estatísticas gerais
    total_paradas = paradas_periodo.count()
    tempo_total = sum([p.duracao_minutos or 0 for p in paradas_periodo if p.duracao_minutos])
    tempo_medio = tempo_total / total_paradas if total_paradas > 0 else 0
    
    # Paradas por tipo
    paradas_por_tipo = {}
    for parada in paradas_periodo:
        tipo_nome = parada.tipo_parada.nome
        if tipo_nome not in paradas_por_tipo:
            paradas_por_tipo[tipo_nome] = {
                'count': 0,
                'tempo_total': 0,
                'cor': parada.tipo_parada.cor_exibicao
            }
        paradas_por_tipo[tipo_nome]['count'] += 1
        paradas_por_tipo[tipo_nome]['tempo_total'] += float(parada.duracao_minutos or 0)
    
    # Paradas por soldador
    paradas_por_soldador = {}
    for parada in paradas_periodo:
        soldador_nome = parada.soldador.usuario.nome_completo
        if soldador_nome not in paradas_por_soldador:
            paradas_por_soldador[soldador_nome] = {
                'count': 0,
                'tempo_total': 0
            }
        paradas_por_soldador[soldador_nome]['count'] += 1
        paradas_por_soldador[soldador_nome]['tempo_total'] += float(parada.duracao_minutos or 0)
    
    # Paradas por dia
    paradas_por_dia = {}
    for i in range(7):
        data = hoje - timedelta(days=i)
        paradas_dia = paradas_periodo.filter(inicio__date=data)
        
        paradas_por_dia[data.strftime('%d/%m')] = {
            'count': paradas_dia.count(),
            'tempo_total': sum([p.duracao_minutos or 0 for p in paradas_dia if p.duracao_minutos])
        }
    
    context = {
        'estatisticas': {
            'total_paradas': total_paradas,
            'tempo_total': tempo_total,
            'tempo_medio': round(tempo_medio, 1),
            'paradas_por_tipo': paradas_por_tipo,
            'paradas_por_soldador': paradas_por_soldador,
            'paradas_por_dia': paradas_por_dia,
        },
        'periodo': f"{data_inicio.strftime('%d/%m/%Y')} - {hoje.strftime('%d/%m/%Y')}",
    }
    
    return render(request, 'manutencao/estatisticas_manutencao.html', context)

@csrf_exempt
@login_required
def buscar_soldadores_ativos(request):
    """API para buscar soldadores com turno ativo"""
    if request.method == 'GET':
        try:
            soldadores_ativos = []
            
            # Buscar soldadores com turno ativo hoje
            from soldagem.models import Turno
            
            turnos_ativos = Turno.objects.filter(
                data_turno=timezone.now().date(),
                status='ativo'
            ).select_related('soldador')
            
            for turno in turnos_ativos:
                soldador = turno.soldador
                
                # Verificar se não tem parada ativa
                parada_ativa = Parada.objects.filter(
                    soldador=soldador,
                    fim__isnull=True
                ).first()
                
                soldadores_ativos.append({
                    'id': soldador.id,
                    'nome': soldador.usuario.nome_completo,
                    'tem_parada_ativa': parada_ativa is not None,
                    'inicio_turno': turno.inicio_turno.strftime('%H:%M')
                })
            
            return JsonResponse({
                'success': True,
                'soldadores': soldadores_ativos
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@csrf_exempt
@login_required
def dados_grafico_manutencao(request):
    """API para dados do gráfico de manutenção"""
    if request.method == 'GET':
        try:
            periodo = int(request.GET.get('periodo', '7'))  # 7 dias por padrão
            
            dados = []
            
            for i in range(periodo):
                data = timezone.now().date() - timedelta(days=i)
                
                paradas_dia = Parada.objects.filter(
                    tipo_parada__categoria='manutencao',
                    inicio__date=data
                )
                
                total_paradas = paradas_dia.count()
                tempo_total = sum([p.duracao_minutos or 0 for p in paradas_dia if p.duracao_minutos])
                tempo_medio = tempo_total / total_paradas if total_paradas > 0 else 0
                
                dados.append({
                    'data': data.strftime('%d/%m'),
                    'total_paradas': total_paradas,
                    'tempo_total': round(tempo_total, 1),
                    'tempo_medio': round(tempo_medio, 1)
                })
            
            # Inverter para ordem cronológica
            dados.reverse()
            
            return JsonResponse({
                'success': True,
                'dados': dados
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})
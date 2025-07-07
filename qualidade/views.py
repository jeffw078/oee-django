from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from datetime import datetime, date
import json

from core.models import Usuario
from core.middleware import mark_for_audit
from soldagem.models import Apontamento, Soldador
from .models import TipoDefeito, Defeito

@login_required
def painel_qualidade(request):
    """Painel principal da qualidade"""
    if request.user.tipo_usuario not in ['admin', 'qualidade']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    # Buscar tipos de defeito ativos
    tipos_defeito = TipoDefeito.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'tipos_defeito': tipos_defeito,
        'usuario': request.user,
    }
    
    return render(request, 'qualidade/painel_qualidade.html', context)

@login_required
def avaliacao_qualidade(request, apontamento_id=None):
    """Tela de avaliação de qualidade durante soldagem"""
    if request.user.tipo_usuario not in ['admin', 'qualidade']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    apontamento = None
    if apontamento_id:
        apontamento = get_object_or_404(Apontamento, id=apontamento_id)
    
    # Buscar soldadores para o dropdown
    soldadores = Soldador.objects.filter(ativo=True).order_by('usuario__nome_completo')
    
    # Buscar tipos de defeito
    tipos_defeito = TipoDefeito.objects.filter(ativo=True).order_by('nome')
    
    # Buscar apontamentos do dia atual para o soldador
    apontamentos_hoje = []
    if apontamento and apontamento.soldador:
        apontamentos_hoje = Apontamento.objects.filter(
            soldador=apontamento.soldador,
            inicio_processo__date=timezone.now().date(),
            fim_processo__isnull=False  # Apenas apontamentos finalizados
        ).order_by('-inicio_processo')
    
    context = {
        'apontamento': apontamento,
        'soldadores': soldadores,
        'tipos_defeito': tipos_defeito,
        'apontamentos_hoje': apontamentos_hoje,
        'usuario': request.user,
    }
    
    return render(request, 'qualidade/avaliacao_qualidade.html', context)

@csrf_exempt
@login_required
def buscar_apontamentos_soldador(request):
    """API para buscar apontamentos de um soldador"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            soldador_id = data.get('soldador_id')
            data_filtro = data.get('data', timezone.now().date().isoformat())
            
            soldador = Soldador.objects.get(id=soldador_id)
            
            # Buscar apontamentos finalizados do soldador na data especificada
            apontamentos = Apontamento.objects.filter(
                soldador=soldador,
                inicio_processo__date=data_filtro,
                fim_processo__isnull=False
            ).order_by('-inicio_processo')
            
            resultados = []
            for apontamento in apontamentos:
                resultados.append({
                    'id': apontamento.id,
                    'componente': apontamento.componente.nome,
                    'modulo': apontamento.modulo.nome,
                    'pedido': apontamento.pedido.numero,
                    'poste_tubo': apontamento.numero_poste_tubo,
                    'inicio': apontamento.inicio_processo.strftime('%H:%M:%S'),
                    'fim': apontamento.fim_processo.strftime('%H:%M:%S') if apontamento.fim_processo else '',
                    'tempo_real': float(apontamento.tempo_real or 0),
                    'eficiencia': float(apontamento.eficiencia_calculada or 0),
                    'diametro': float(apontamento.diametro or 0) if apontamento.diametro else None
                })
            
            return JsonResponse({
                'success': True,
                'apontamentos': resultados,
                'soldador_nome': soldador.usuario.nome_completo
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@csrf_exempt
@login_required
def registrar_defeito(request):
    """Registrar defeito de qualidade"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                
                apontamento_id = data.get('apontamento_id')
                tipo_defeito_id = data.get('tipo_defeito_id')
                tamanho_mm = data.get('tamanho_mm')
                observacoes = data.get('observacoes', '')
                
                apontamento = Apontamento.objects.get(id=apontamento_id)
                tipo_defeito = TipoDefeito.objects.get(id=tipo_defeito_id)
                
                # Criar registro de defeito
                defeito = Defeito.objects.create(
                    tipo_defeito=tipo_defeito,
                    apontamento=apontamento,
                    soldador=apontamento.soldador,
                    tamanho_mm=tamanho_mm,
                    usuario_qualidade=request.user,
                    observacoes=observacoes
                )
                
                # Calcular percentual de qualidade
                percentual_qualidade = defeito.calcular_percentual_qualidade()
                
                # Auditoria
                mark_for_audit(
                    request,
                    f"Registrou defeito: {tipo_defeito.nome} - {tamanho_mm}mm",
                    'defeito',
                    defeito.id,
                    None,
                    {
                        'tipo_defeito': tipo_defeito.nome,
                        'apontamento': apontamento.id,
                        'soldador': apontamento.soldador.usuario.nome_completo,
                        'tamanho_mm': float(tamanho_mm),
                        'area_defeito': float(defeito.area_defeito),
                        'percentual_qualidade': float(percentual_qualidade)
                    }
                )
                
                return JsonResponse({
                    'success': True,
                    'defeito_id': defeito.id,
                    'area_defeito': float(defeito.area_defeito),
                    'percentual_qualidade': float(percentual_qualidade),
                    'message': 'Defeito registrado com sucesso'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao registrar defeito: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@login_required
def historico_defeitos(request):
    """Histórico de defeitos registrados"""
    if request.user.tipo_usuario not in ['admin', 'qualidade', 'analista']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    # Filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    soldador_id = request.GET.get('soldador')
    tipo_defeito_id = request.GET.get('tipo_defeito')
    
    # Query base
    defeitos = Defeito.objects.select_related(
        'tipo_defeito', 'apontamento', 'soldador', 'usuario_qualidade'
    ).order_by('-data_deteccao')
    
    # Aplicar filtros
    if data_inicio:
        defeitos = defeitos.filter(data_deteccao__date__gte=data_inicio)
    
    if data_fim:
        defeitos = defeitos.filter(data_deteccao__date__lte=data_fim)
    
    if soldador_id:
        defeitos = defeitos.filter(soldador_id=soldador_id)
    
    if tipo_defeito_id:
        defeitos = defeitos.filter(tipo_defeito_id=tipo_defeito_id)
    
    # Paginação (opcional)
    defeitos = defeitos[:100]  # Limitar a 100 registros por enquanto
    
    # Dados para filtros
    soldadores = Soldador.objects.filter(ativo=True).order_by('usuario__nome_completo')
    tipos_defeito = TipoDefeito.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'defeitos': defeitos,
        'soldadores': soldadores,
        'tipos_defeito': tipos_defeito,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'soldador_id': soldador_id,
            'tipo_defeito_id': tipo_defeito_id,
        }
    }
    
    return render(request, 'qualidade/historico_defeitos.html', context)

@login_required
def estatisticas_qualidade(request):
    """Estatísticas gerais de qualidade"""
    if request.user.tipo_usuario not in ['admin', 'qualidade', 'analista']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    hoje = timezone.now().date()
    
    # Estatísticas do dia
    defeitos_hoje = Defeito.objects.filter(data_deteccao__date=hoje)
    apontamentos_hoje = Apontamento.objects.filter(
        inicio_processo__date=hoje,
        fim_processo__isnull=False
    )
    
    # Estatísticas gerais
    total_defeitos_hoje = defeitos_hoje.count()
    total_apontamentos_hoje = apontamentos_hoje.count()
    taxa_defeito_hoje = (total_defeitos_hoje / total_apontamentos_hoje * 100) if total_apontamentos_hoje > 0 else 0
    
    # Defeitos por tipo
    defeitos_por_tipo = {}
    for defeito in defeitos_hoje:
        tipo_nome = defeito.tipo_defeito.nome
        if tipo_nome not in defeitos_por_tipo:
            defeitos_por_tipo[tipo_nome] = {
                'count': 0,
                'area_total': 0,
                'cor': defeito.tipo_defeito.cor_exibicao
            }
        defeitos_por_tipo[tipo_nome]['count'] += 1
        defeitos_por_tipo[tipo_nome]['area_total'] += float(defeito.area_defeito or 0)
    
    # Defeitos por soldador
    defeitos_por_soldador = {}
    for defeito in defeitos_hoje:
        soldador_nome = defeito.soldador.usuario.nome_completo
        if soldador_nome not in defeitos_por_soldador:
            defeitos_por_soldador[soldador_nome] = {
                'count': 0,
                'area_total': 0
            }
        defeitos_por_soldador[soldador_nome]['count'] += 1
        defeitos_por_soldador[soldador_nome]['area_total'] += float(defeito.area_defeito or 0)
    
    context = {
        'estatisticas': {
            'total_defeitos_hoje': total_defeitos_hoje,
            'total_apontamentos_hoje': total_apontamentos_hoje,
            'taxa_defeito_hoje': round(taxa_defeito_hoje, 2),
            'defeitos_por_tipo': defeitos_por_tipo,
            'defeitos_por_soldador': defeitos_por_soldador,
        },
        'data_referencia': hoje,
    }
    
    return render(request, 'qualidade/estatisticas_qualidade.html', context)

@csrf_exempt
@login_required
def dados_grafico_qualidade(request):
    """API para dados do gráfico de qualidade"""
    if request.method == 'GET':
        try:
            periodo = request.GET.get('periodo', '7')  # 7 dias por padrão
            
            # Calcular dados para o período
            dados = []
            
            for i in range(int(periodo)):
                data = timezone.now().date() - timezone.timedelta(days=i)
                
                defeitos_dia = Defeito.objects.filter(data_deteccao__date=data)
                apontamentos_dia = Apontamento.objects.filter(
                    inicio_processo__date=data,
                    fim_processo__isnull=False
                )
                
                total_defeitos = defeitos_dia.count()
                total_apontamentos = apontamentos_dia.count()
                taxa_defeito = (total_defeitos / total_apontamentos * 100) if total_apontamentos > 0 else 0
                
                dados.append({
                    'data': data.strftime('%d/%m'),
                    'total_apontamentos': total_apontamentos,
                    'total_defeitos': total_defeitos,
                    'taxa_defeito': round(taxa_defeito, 2),
                    'percentual_qualidade': round(100 - taxa_defeito, 2)
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
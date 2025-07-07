from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from django.db.models import Sum, Avg, Count, Q
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from core.models import Soldador
from soldagem.models import Apontamento, Parada, TipoParada, Modulo, Componente, Turno
from qualidade.models import Defeito, CalculoOEE

@login_required
def dashboard_principal(request):
    """Dashboard principal com indicadores OEE"""
    if request.user.tipo_usuario not in ['admin', 'analista', 'qualidade', 'manutencao']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    hoje = timezone.now().date()
    
    # Calcular OEE do dia atual
    oee_hoje = calcular_oee_periodo(hoje, hoje)
    
    # Indicadores rápidos
    apontamentos_hoje = Apontamento.objects.filter(
        inicio_processo__date=hoje,
        fim_processo__isnull=False
    )
    
    defeitos_hoje = Defeito.objects.filter(data_deteccao__date=hoje)
    paradas_hoje = Parada.objects.filter(inicio__date=hoje)
    
    # Soldadores ativos
    soldadores_ativos = Turno.objects.filter(
        data_turno=hoje,
        status='ativo'
    ).count()
    
    context = {
        'oee_hoje': oee_hoje,
        'indicadores': {
            'total_apontamentos': apontamentos_hoje.count(),
            'total_defeitos': defeitos_hoje.count(),
            'total_paradas': paradas_hoje.count(),
            'soldadores_ativos': soldadores_ativos,
        },
        'data_referencia': hoje,
    }
    
    return render(request, 'relatorios/dashboard_principal.html', context)

@login_required
def relatorio_oee(request):
    """Relatório detalhado de OEE"""
    if request.user.tipo_usuario not in ['admin', 'analista']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    # Filtros
    data_inicio = request.GET.get('data_inicio', timezone.now().date().isoformat())
    data_fim = request.GET.get('data_fim', timezone.now().date().isoformat())
    soldador_id = request.GET.get('soldador')
    modulo_id = request.GET.get('modulo')
    
    # Converter datas
    data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    # Calcular OEE para o período
    oee_resultado = calcular_oee_periodo(
        data_inicio, data_fim, soldador_id, modulo_id
    )
    
    # Buscar dados detalhados
    apontamentos = Apontamento.objects.filter(
        inicio_processo__date__gte=data_inicio,
        inicio_processo__date__lte=data_fim,
        fim_processo__isnull=False
    ).select_related('soldador', 'modulo', 'componente')
    
    if soldador_id:
        apontamentos = apontamentos.filter(soldador_id=soldador_id)
    
    if modulo_id:
        apontamentos = apontamentos.filter(modulo_id=modulo_id)
    
    # Dados para filtros
    soldadores = Soldador.objects.filter(ativo=True).order_by('usuario__nome_completo')
    modulos = Modulo.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'oee_resultado': oee_resultado,
        'apontamentos': apontamentos[:50],  # Limitar exibição
        'soldadores': soldadores,
        'modulos': modulos,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'soldador_id': soldador_id,
            'modulo_id': modulo_id,
        }
    }
    
    return render(request, 'relatorios/relatorio_oee.html', context)

@login_required
def pontos_melhoria(request):
    """Relatório de pontos de melhoria"""
    if request.user.tipo_usuario not in ['admin', 'analista']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    data_inicio = request.GET.get('data_inicio', (timezone.now().date() - timedelta(days=7)).isoformat())
    data_fim = request.GET.get('data_fim', timezone.now().date().isoformat())
    soldador_ids = request.GET.getlist('soldadores')
    
    # Converter datas
    data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    # Query base
    apontamentos = Apontamento.objects.filter(
        inicio_processo__date__gte=data_inicio,
        inicio_processo__date__lte=data_fim,
        fim_processo__isnull=False,
        tempo_real__isnull=False
    ).select_related('soldador', 'componente')
    
    if soldador_ids:
        apontamentos = apontamentos.filter(soldador_id__in=soldador_ids)
    
    # Processos que demoraram mais que o padrão
    processos_lentos = apontamentos.filter(
        eficiencia_calculada__lt=100
    ).order_by('eficiencia_calculada')
    
    # Agrupar por componente para análise
    analise_componentes = {}
    for apontamento in apontamentos:
        componente = apontamento.componente.nome
        if componente not in analise_componentes:
            analise_componentes[componente] = {
                'total_apontamentos': 0,
                'tempo_real_total': 0,
                'tempo_padrao_total': 0,
                'eficiencia_media': 0,
                'soldadores': set()
            }
        
        analise_componentes[componente]['total_apontamentos'] += 1
        analise_componentes[componente]['tempo_real_total'] += float(apontamento.tempo_real)
        analise_componentes[componente]['tempo_padrao_total'] += float(apontamento.tempo_padrao)
        analise_componentes[componente]['soldadores'].add(apontamento.soldador.usuario.nome_completo)
    
    # Calcular eficiências médias
    for componente, dados in analise_componentes.items():
        if dados['tempo_real_total'] > 0:
            dados['eficiencia_media'] = (dados['tempo_padrao_total'] / dados['tempo_real_total']) * 100
        dados['soldadores'] = list(dados['soldadores'])
    
    # Dados para filtros
    soldadores = Soldador.objects.filter(ativo=True).order_by('usuario__nome_completo')
    
    context = {
        'processos_lentos': processos_lentos[:20],  # Top 20 piores
        'analise_componentes': analise_componentes,
        'soldadores': soldadores,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'soldador_ids': soldador_ids,
        }
    }
    
    return render(request, 'relatorios/pontos_melhoria.html', context)

@login_required
def relatorio_paradas(request):
    """Relatório de paradas"""
    if request.user.tipo_usuario not in ['admin', 'analista', 'manutencao']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    data_inicio = request.GET.get('data_inicio', (timezone.now().date() - timedelta(days=7)).isoformat())
    data_fim = request.GET.get('data_fim', timezone.now().date().isoformat())
    soldador_ids = request.GET.getlist('soldadores')
    
    # Converter datas
    data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    # Query base
    paradas = Parada.objects.filter(
        inicio__date__gte=data_inicio,
        inicio__date__lte=data_fim,
        duracao_minutos__isnull=False
    ).select_related('tipo_parada', 'soldador').order_by('-duracao_minutos')
    
    if soldador_ids:
        paradas = paradas.filter(soldador_id__in=soldador_ids)
    
    # Análise por tipo de parada
    analise_tipos = {}
    for parada in paradas:
        tipo = parada.tipo_parada.nome
        if tipo not in analise_tipos:
            analise_tipos[tipo] = {
                'total_paradas': 0,
                'tempo_total': 0,
                'tempo_medio': 0,
                'categoria': parada.tipo_parada.categoria,
                'penaliza_oee': parada.tipo_parada.penaliza_oee
            }
        
        analise_tipos[tipo]['total_paradas'] += 1
        analise_tipos[tipo]['tempo_total'] += float(parada.duracao_minutos)
    
    # Calcular tempos médios
    for tipo, dados in analise_tipos.items():
        if dados['total_paradas'] > 0:
            dados['tempo_medio'] = dados['tempo_total'] / dados['total_paradas']
    
    # Análise por soldador
    analise_soldadores = {}
    for parada in paradas:
        soldador = parada.soldador.usuario.nome_completo
        if soldador not in analise_soldadores:
            analise_soldadores[soldador] = {
                'total_paradas': 0,
                'tempo_total': 0,
                'tempo_medio': 0
            }
        
        analise_soldadores[soldador]['total_paradas'] += 1
        analise_soldadores[soldador]['tempo_total'] += float(parada.duracao_minutos)
    
    # Calcular tempos médios por soldador
    for soldador, dados in analise_soldadores.items():
        if dados['total_paradas'] > 0:
            dados['tempo_medio'] = dados['tempo_total'] / dados['total_paradas']
    
    # Dados para filtros
    soldadores = Soldador.objects.filter(ativo=True).order_by('usuario__nome_completo')
    
    context = {
        'paradas': paradas[:50],  # Limitar exibição
        'analise_tipos': analise_tipos,
        'analise_soldadores': analise_soldadores,
        'soldadores': soldadores,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'soldador_ids': soldador_ids,
        }
    }
    
    return render(request, 'relatorios/relatorio_paradas.html', context)

@login_required
def grafico_utilizacao(request):
    """Gráfico de utilização considerando múltiplos turnos"""
    if request.user.tipo_usuario not in ['admin', 'analista']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    # Dados fictícios para demonstração - em produção, calcular baseado em dados reais
    utilizacao_atual = 75.5  # % atual com 1 turno
    utilizacao_2_turnos = 87.2  # % potencial com 2 turnos
    utilizacao_3_turnos = 92.8  # % potencial com 3 turnos
    
    context = {
        'utilizacao_dados': {
            '1_turno': utilizacao_atual,
            '2_turnos': utilizacao_2_turnos,
            '3_turnos': utilizacao_3_turnos,
        }
    }
    
    return render(request, 'relatorios/grafico_utilizacao.html', context)

@login_required
def grafico_eficiencia(request):
    """Gráfico de eficiência por dias e horários"""
    if request.user.tipo_usuario not in ['admin', 'analista']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    componente_id = request.GET.get('componente')
    periodo_dias = int(request.GET.get('periodo', '7'))
    
    # Buscar componentes para filtro
    componentes = Componente.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'componentes': componentes,
        'componente_selecionado': componente_id,
        'periodo_dias': periodo_dias,
    }
    
    return render(request, 'relatorios/grafico_eficiencia.html', context)

# APIs para dados dos gráficos

@csrf_exempt
@login_required
def api_dados_oee(request):
    """API para dados do gráfico OEE"""
    if request.method == 'GET':
        try:
            periodo = int(request.GET.get('periodo', '7'))
            soldador_id = request.GET.get('soldador')
            
            dados = []
            
            for i in range(periodo):
                data = timezone.now().date() - timedelta(days=i)
                oee_dia = calcular_oee_periodo(data, data, soldador_id)
                
                dados.append({
                    'data': data.strftime('%d/%m'),
                    'utilizacao': float(oee_dia['utilizacao']),
                    'eficiencia': float(oee_dia['eficiencia']),
                    'qualidade': float(oee_dia['qualidade']),
                    'oee': float(oee_dia['oee'])
                })
            
            dados.reverse()  # Ordem cronológica
            
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

@csrf_exempt
@login_required
def api_dados_eficiencia_dispersao(request):
    """API para dados do gráfico de dispersão de eficiência"""
    if request.method == 'GET':
        try:
            componente_id = request.GET.get('componente')
            periodo = int(request.GET.get('periodo', '7'))
            
            data_inicio = timezone.now().date() - timedelta(days=periodo-1)
            data_fim = timezone.now().date()
            
            apontamentos = Apontamento.objects.filter(
                inicio_processo__date__gte=data_inicio,
                inicio_processo__date__lte=data_fim,
                fim_processo__isnull=False,
                eficiencia_calculada__isnull=False
            )
            
            if componente_id:
                apontamentos = apontamentos.filter(componente_id=componente_id)
            
            dados = []
            for apontamento in apontamentos:
                hora_inicio = apontamento.inicio_processo.hour + (apontamento.inicio_processo.minute / 60)
                
                dados.append({
                    'hora': hora_inicio,
                    'eficiencia': float(apontamento.eficiencia_calculada),
                    'dia_semana': apontamento.inicio_processo.weekday(),
                    'soldador': apontamento.soldador.usuario.nome_completo,
                    'componente': apontamento.componente.nome,
                    'tempo_real': float(apontamento.tempo_real),
                    'tempo_padrao': float(apontamento.tempo_padrao)
                })
            
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

# Função auxiliar para cálculo de OEE
def calcular_oee_periodo(data_inicio, data_fim, soldador_id=None, modulo_id=None):
    """Calcula OEE para um período específico"""
    
    # Query base para apontamentos
    apontamentos = Apontamento.objects.filter(
        inicio_processo__date__gte=data_inicio,
        inicio_processo__date__lte=data_fim,
        fim_processo__isnull=False
    )
    
    if soldador_id:
        apontamentos = apontamentos.filter(soldador_id=soldador_id)
    
    if modulo_id:
        apontamentos = apontamentos.filter(modulo_id=modulo_id)
    
    # Query para paradas
    paradas = Parada.objects.filter(
        inicio__date__gte=data_inicio,
        inicio__date__lte=data_fim,
        duracao_minutos__isnull=False
    )
    
    if soldador_id:
        paradas = paradas.filter(soldador_id=soldador_id)
    
    # Query para defeitos
    defeitos = Defeito.objects.filter(
        data_deteccao__date__gte=data_inicio,
        data_deteccao__date__lte=data_fim
    )
    
    if soldador_id:
        defeitos = defeitos.filter(soldador_id=soldador_id)
    
    # Calcular métricas
    total_apontamentos = apontamentos.count()
    
    if total_apontamentos == 0:
        return {
            'utilizacao': Decimal('0'),
            'eficiencia': Decimal('0'),
            'qualidade': Decimal('100'),
            'oee': Decimal('0'),
            'detalhes': {
                'horas_disponiveis': Decimal('0'),
                'horas_trabalhadas': Decimal('0'),
                'tempo_produtivo': Decimal('0'),
                'tempo_padrao_total': Decimal('0'),
                'total_apontamentos': 0,
                'total_defeitos': 0,
                'total_paradas': 0
            }
        }
    
    # 1. UTILIZAÇÃO
    # Assumir 8 horas por dia como padrão
    dias_periodo = (data_fim - data_inicio).days + 1
    horas_disponiveis = Decimal(str(dias_periodo * 8))
    
    # Tempo total de paradas que penalizam OEE
    tempo_paradas_penalizantes = sum([
        p.duracao_minutos for p in paradas 
        if p.tipo_parada.penaliza_oee and p.duracao_minutos
    ]) / 60  # Converter para horas
    
    horas_trabalhadas = horas_disponiveis - Decimal(str(tempo_paradas_penalizantes))
    utilizacao = (horas_trabalhadas / horas_disponiveis * 100) if horas_disponiveis > 0 else Decimal('0')
    
    # 2. EFICIÊNCIA
    tempo_real_total = sum([
        float(a.tempo_real) for a in apontamentos if a.tempo_real
    ]) / 60  # Converter para horas
    
    tempo_padrao_total = sum([
        float(a.tempo_padrao) for a in apontamentos
    ]) / 60  # Converter para horas
    
    eficiencia = (Decimal(str(tempo_padrao_total)) / Decimal(str(tempo_real_total)) * 100) if tempo_real_total > 0 else Decimal('0')
    
    # 3. QUALIDADE
    total_defeitos = defeitos.count()
    total_area_defeitos = sum([float(d.area_defeito or 0) for d in defeitos])
    
    # Calcular área total de soldagem (simplificado)
    area_total_soldagem = 0
    for apontamento in apontamentos:
        if apontamento.diametro:
            # Área aproximada de soldagem por peça
            import math
            area_peca = math.pi * float(apontamento.diametro) * 50  # 50mm de comprimento médio
            area_total_soldagem += area_peca
    
    if area_total_soldagem > 0:
        percentual_defeito = (total_area_defeitos / area_total_soldagem) * 100
        qualidade = max(Decimal('0'), 100 - Decimal(str(percentual_defeito)))
    else:
        qualidade = Decimal('100')
    
    # 4. OEE FINAL
    oee = (utilizacao * eficiencia * qualidade) / 10000
    
    return {
        'utilizacao': round(utilizacao, 2),
        'eficiencia': round(eficiencia, 2),
        'qualidade': round(qualidade, 2),
        'oee': round(oee, 2),
        'detalhes': {
            'horas_disponiveis': round(horas_disponiveis, 2),
            'horas_trabalhadas': round(horas_trabalhadas, 2),
            'tempo_produtivo': round(Decimal(str(tempo_real_total)), 2),
            'tempo_padrao_total': round(Decimal(str(tempo_padrao_total)), 2),
            'total_apontamentos': total_apontamentos,
            'total_defeitos': total_defeitos,
            'total_paradas': paradas.count()
        }
    }
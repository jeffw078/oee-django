from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
import json

from .models import Usuario, Soldador, ConfiguracaoSistema, HoraTrabalho, LogAuditoria
from .middleware import mark_for_audit
from soldagem.models import Modulo, Componente, TipoParada, Apontamento
from qualidade.models import TipoDefeito

def login_view(request):
    """Login para usuários administrativos"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user and user.tipo_usuario in ['admin', 'analista', 'qualidade', 'manutencao']:
            login(request, user)
            user.ultimo_login = timezone.now()
            user.save()
            
            # Auditoria
            mark_for_audit(
                request,
                f"Login administrativo: {user.nome_completo}",
                'usuario',
                user.id
            )
            
            return redirect('core:admin')
        else:
            messages.error(request, 'Credenciais inválidas ou acesso negado')
    
    return render(request, 'core/login.html')

@login_required
def logout_view(request):
    """Logout"""
    mark_for_audit(
        request,
        f"Logout: {request.user.nome_completo}",
        'usuario',
        request.user.id
    )
    logout(request)
    return redirect('soldagem:selecao_soldador')

@login_required
def painel_admin(request):
    """Painel administrativo principal"""
    if request.user.tipo_usuario not in ['admin']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    # Estatísticas rápidas
    total_usuarios = Usuario.objects.count()
    total_soldadores = Soldador.objects.filter(ativo=True).count()
    total_apontamentos = Apontamento.objects.count()
    
    # Logs recentes
    logs_recentes = LogAuditoria.objects.order_by('-timestamp')[:10]
    
    context = {
        'estatisticas': {
            'total_usuarios': total_usuarios,
            'total_soldadores': total_soldadores,
            'total_apontamentos': total_apontamentos,
        },
        'logs_recentes': logs_recentes,
    }
    
    return render(request, 'core/painel_admin.html', context)

@login_required
def gerenciar_usuarios(request):
    """Gerenciar usuários do sistema"""
    if request.user.tipo_usuario not in ['admin']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    usuarios = Usuario.objects.all().order_by('nome_completo')
    
    context = {
        'usuarios': usuarios,
        'tipos_usuario': Usuario.TIPO_CHOICES,
    }
    
    return render(request, 'core/gerenciar_usuarios.html', context)

@login_required
def gerenciar_soldadores(request):
    """Gerenciar soldadores"""
    if request.user.tipo_usuario not in ['admin']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    soldadores = Soldador.objects.select_related('usuario').order_by('usuario__nome_completo')
    usuarios_soldadores = Usuario.objects.filter(tipo_usuario='soldador')
    
    context = {
        'soldadores': soldadores,
        'usuarios_soldadores': usuarios_soldadores,
    }
    
    return render(request, 'core/gerenciar_soldadores.html', context)

@login_required
def gerenciar_componentes(request):
    """Gerenciar componentes de soldagem"""
    if request.user.tipo_usuario not in ['admin']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    componentes = Componente.objects.all().order_by('nome')
    
    context = {
        'componentes': componentes,
    }
    
    return render(request, 'core/gerenciar_componentes.html', context)

@login_required
def gerenciar_modulos(request):
    """Gerenciar módulos"""
    if request.user.tipo_usuario not in ['admin']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    modulos = Modulo.objects.all().order_by('ordem_exibicao', 'nome')
    
    context = {
        'modulos': modulos,
    }
    
    return render(request, 'core/gerenciar_modulos.html', context)

@login_required
def gerenciar_tipos_parada(request):
    """Gerenciar tipos de parada"""
    if request.user.tipo_usuario not in ['admin']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    tipos_parada = TipoParada.objects.all().order_by('categoria', 'nome')
    
    context = {
        'tipos_parada': tipos_parada,
        'categorias': TipoParada.CATEGORIA_CHOICES,
    }
    
    return render(request, 'core/gerenciar_tipos_parada.html', context)

@login_required
def gerenciar_tipos_defeito(request):
    """Gerenciar tipos de defeito"""
    if request.user.tipo_usuario not in ['admin']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    tipos_defeito = TipoDefeito.objects.all().order_by('nome')
    
    context = {
        'tipos_defeito': tipos_defeito,
    }
    
    return render(request, 'core/gerenciar_tipos_defeito.html', context)

@login_required
def gerenciar_horas_trabalho(request):
    """Gerenciar horas de trabalho"""
    if request.user.tipo_usuario not in ['admin']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    horas_trabalho = HoraTrabalho.objects.all().order_by('nome')
    
    context = {
        'horas_trabalho': horas_trabalho,
    }
    
    return render(request, 'core/gerenciar_horas_trabalho.html', context)

@login_required
def gerenciar_apontamentos(request):
    """Gerenciar e editar apontamentos"""
    if request.user.tipo_usuario not in ['admin']:
        messages.error(request, 'Acesso negado')
        return redirect('soldagem:apontamento')
    
    # Filtros
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    soldador_id = request.GET.get('soldador')
    modulo_id = request.GET.get('modulo')
    
    # Query base
    apontamentos = Apontamento.objects.select_related(
        'soldador', 'modulo', 'componente', 'pedido'
    ).order_by('-inicio_processo')
    
    # Aplicar filtros
    if data_inicio:
        apontamentos = apontamentos.filter(inicio_processo__date__gte=data_inicio)
    
    if data_fim:
        apontamentos = apontamentos.filter(inicio_processo__date__lte=data_fim)
    
    if soldador_id:
        apontamentos = apontamentos.filter(soldador_id=soldador_id)
    
    if modulo_id:
        apontamentos = apontamentos.filter(modulo_id=modulo_id)
    
    # Paginação
    paginator = Paginator(apontamentos, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Dados para filtros
    soldadores = Soldador.objects.filter(ativo=True).order_by('usuario__nome_completo')
    modulos = Modulo.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'page_obj': page_obj,
        'soldadores': soldadores,
        'modulos': modulos,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'soldador_id': soldador_id,
            'modulo_id': modulo_id,
        }
    }
    
    return render(request, 'core/gerenciar_apontamentos.html', context)

# APIs para operações CRUD

@csrf_exempt
@login_required
def api_salvar_usuario(request):
    """API para salvar/editar usuário"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                
                usuario_id = data.get('id')
                username = data.get('username')
                nome_completo = data.get('nome_completo')
                email = data.get('email')
                tipo_usuario = data.get('tipo_usuario')
                password = data.get('password')
                ativo = data.get('ativo', True)
                
                if usuario_id:
                    # Editar usuário existente
                    usuario = Usuario.objects.get(id=usuario_id)
                    dados_antes = {
                        'username': usuario.username,
                        'nome_completo': usuario.nome_completo,
                        'email': usuario.email,
                        'tipo_usuario': usuario.tipo_usuario,
                        'ativo': usuario.ativo
                    }
                    
                    usuario.username = username
                    usuario.nome_completo = nome_completo
                    usuario.email = email
                    usuario.tipo_usuario = tipo_usuario
                    usuario.ativo = ativo
                    
                    if password:
                        usuario.set_password(password)
                    
                    usuario.save()
                    
                    dados_depois = {
                        'username': usuario.username,
                        'nome_completo': usuario.nome_completo,
                        'email': usuario.email,
                        'tipo_usuario': usuario.tipo_usuario,
                        'ativo': usuario.ativo
                    }
                    
                    # Auditoria
                    mark_for_audit(
                        request,
                        f"Editou usuário: {usuario.nome_completo}",
                        'usuario',
                        usuario.id,
                        dados_antes,
                        dados_depois
                    )
                    
                    mensagem = 'Usuário editado com sucesso'
                else:
                    # Criar novo usuário
                    usuario = Usuario.objects.create_user(
                        username=username,
                        password=password,
                        nome_completo=nome_completo,
                        email=email,
                        tipo_usuario=tipo_usuario,
                        ativo=ativo
                    )
                    
                    # Auditoria
                    mark_for_audit(
                        request,
                        f"Criou usuário: {usuario.nome_completo}",
                        'usuario',
                        usuario.id,
                        None,
                        {
                            'username': usuario.username,
                            'nome_completo': usuario.nome_completo,
                            'tipo_usuario': usuario.tipo_usuario
                        }
                    )
                    
                    mensagem = 'Usuário criado com sucesso'
                
                return JsonResponse({
                    'success': True,
                    'message': mensagem,
                    'usuario_id': usuario.id
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao salvar usuário: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@csrf_exempt
@login_required
def api_salvar_soldador(request):
    """API para salvar/editar soldador"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                
                soldador_id = data.get('id')
                usuario_id = data.get('usuario_id')
                senha_simplificada = data.get('senha_simplificada')
                ativo = data.get('ativo', True)
                
                usuario = Usuario.objects.get(id=usuario_id)
                
                if soldador_id:
                    # Editar soldador existente
                    soldador = Soldador.objects.get(id=soldador_id)
                    soldador.usuario = usuario
                    soldador.senha_simplificada = senha_simplificada
                    soldador.ativo = ativo
                    soldador.save()
                    
                    mensagem = 'Soldador editado com sucesso'
                else:
                    # Criar novo soldador
                    soldador = Soldador.objects.create(
                        usuario=usuario,
                        senha_simplificada=senha_simplificada,
                        ativo=ativo
                    )
                    
                    mensagem = 'Soldador criado com sucesso'
                
                # Auditoria
                mark_for_audit(
                    request,
                    f"{'Editou' if soldador_id else 'Criou'} soldador: {usuario.nome_completo}",
                    'soldador',
                    soldador.id
                )
                
                return JsonResponse({
                    'success': True,
                    'message': mensagem,
                    'soldador_id': soldador.id
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao salvar soldador: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@csrf_exempt
@login_required
def api_salvar_componente(request):
    """API para salvar/editar componente"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                
                componente_id = data.get('id')
                nome = data.get('nome')
                descricao = data.get('descricao', '')
                tempo_padrao = data.get('tempo_padrao')
                considera_diametro = data.get('considera_diametro', False)
                formula_calculo = data.get('formula_calculo', '')
                ativo = data.get('ativo', True)
                
                if componente_id:
                    # Editar componente existente
                    componente = Componente.objects.get(id=componente_id)
                    componente.nome = nome
                    componente.descricao = descricao
                    componente.tempo_padrao = tempo_padrao
                    componente.considera_diametro = considera_diametro
                    componente.formula_calculo = formula_calculo
                    componente.ativo = ativo
                    componente.save()
                    
                    mensagem = 'Componente editado com sucesso'
                else:
                    # Criar novo componente
                    componente = Componente.objects.create(
                        nome=nome,
                        descricao=descricao,
                        tempo_padrao=tempo_padrao,
                        considera_diametro=considera_diametro,
                        formula_calculo=formula_calculo,
                        ativo=ativo
                    )
                    
                    mensagem = 'Componente criado com sucesso'
                
                # Auditoria
                mark_for_audit(
                    request,
                    f"{'Editou' if componente_id else 'Criou'} componente: {nome}",
                    'componente',
                    componente.id
                )
                
                return JsonResponse({
                    'success': True,
                    'message': mensagem,
                    'componente_id': componente.id
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao salvar componente: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

@csrf_exempt
@login_required
def api_excluir_item(request):
    """API genérica para excluir itens"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            modelo = data.get('modelo')
            item_id = data.get('id')
            
            # Mapeamento de modelos
            modelos_map = {
                'usuario': Usuario,
                'soldador': Soldador,
                'componente': Componente,
                'modulo': Modulo,
                'tipo_parada': TipoParada,
                'tipo_defeito': TipoDefeito,
                'hora_trabalho': HoraTrabalho,
            }
            
            if modelo not in modelos_map:
                return JsonResponse({
                    'success': False,
                    'message': 'Modelo não encontrado'
                })
            
            ModelClass = modelos_map[modelo]
            item = ModelClass.objects.get(id=item_id)
            
            nome_item = str(item)
            item.delete()
            
            # Auditoria
            mark_for_audit(
                request,
                f"Excluiu {modelo}: {nome_item}",
                modelo,
                item_id
            )
            
            return JsonResponse({
                'success': True,
                'message': f'{modelo.title()} excluído com sucesso'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao excluir: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})
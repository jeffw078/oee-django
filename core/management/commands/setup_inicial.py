from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from core.models import Usuario, Soldador, ConfiguracaoSistema, HoraTrabalho
from soldagem.models import Modulo, Componente, TipoParada
from qualidade.models import TipoDefeito

class Command(BaseCommand):
    help = 'Configura dados iniciais para o sistema OEE'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Cria dados de demonstração',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando setup do sistema...'))
        
        with transaction.atomic():
            # 1. Criar usuário administrador
            self.criar_usuario_admin()
            
            # 2. Configurações do sistema
            self.criar_configuracoes_sistema()
            
            # 3. Horas de trabalho
            self.criar_horas_trabalho()
            
            # 4. Módulos
            self.criar_modulos()
            
            # 5. Componentes
            self.criar_componentes()
            
            # 6. Tipos de parada
            self.criar_tipos_parada()
            
            # 7. Tipos de defeito
            self.criar_tipos_defeito()
            
            if options['demo']:
                # 8. Dados de demonstração
                self.criar_dados_demo()
        
        self.stdout.write(self.style.SUCCESS('Setup concluído com sucesso!'))
        self.stdout.write('')
        self.stdout.write('Credenciais do administrador:')
        self.stdout.write('Usuário: admin')
        self.stdout.write('Senha: admin123')
        self.stdout.write('')
        self.stdout.write('Acesse: http://localhost:8000/core/login/')

    def criar_usuario_admin(self):
        """Criar usuário administrador"""
        if not Usuario.objects.filter(username='admin').exists():
            admin = Usuario.objects.create_superuser(
                username='admin',
                password='admin123',
                nome_completo='Administrador do Sistema',
                email='admin@steelmast.com',
                tipo_usuario='admin'
            )
            self.stdout.write(f'✓ Usuário administrador criado: {admin.username}')
        else:
            self.stdout.write('✓ Usuário administrador já existe')

    def criar_configuracoes_sistema(self):
        """Criar configurações básicas do sistema"""
        configuracoes = [
            ('HORAS_TRABALHO_PADRAO', '8', 'Horas de trabalho padrão por dia', 'integer'),
            ('SENHA_QUALIDADE', 'qualidade123', 'Senha de acesso à qualidade', 'string'),
            ('SENHA_MANUTENCAO', 'manutencao123', 'Senha de acesso à manutenção', 'string'),
            ('EFICIENCIA_MINIMA', '80', 'Eficiência mínima esperada (%)', 'integer'),
            ('BACKUP_AUTOMATICO', 'true', 'Backup automático ativo', 'boolean'),
            ('VERSAO_SISTEMA', '1.0.0', 'Versão atual do sistema', 'string'),
        ]
        
        for chave, valor, descricao, tipo_dado in configuracoes:
            config, created = ConfiguracaoSistema.objects.get_or_create(
                chave=chave,
                defaults={
                    'valor': valor,
                    'descricao': descricao,
                    'tipo_dado': tipo_dado
                }
            )
            if created:
                self.stdout.write(f'✓ Configuração criada: {chave}')

    def criar_horas_trabalho(self):
        """Criar configurações de horas de trabalho"""
        turnos = [
            ('Turno Diurno', '07:00', '15:00', 8, [0, 1, 2, 3, 4]),  # Segunda a sexta
            ('Turno Vespertino', '15:00', '23:00', 8, [0, 1, 2, 3, 4]),
            ('Turno Noturno', '23:00', '07:00', 8, [0, 1, 2, 3, 4]),
        ]
        
        for nome, hora_inicio, hora_fim, horas_disp, dias_semana in turnos:
            turno, created = HoraTrabalho.objects.get_or_create(
                nome=nome,
                defaults={
                    'hora_inicio': hora_inicio,
                    'hora_fim': hora_fim,
                    'horas_disponiveis': horas_disp,
                    'dias_semana': dias_semana,
                    'ativo': True
                }
            )
            if created:
                self.stdout.write(f'✓ Turno criado: {nome}')

    def criar_modulos(self):
        """Criar módulos padrão"""
        modulos = [
            ('Módulo A', 'Módulo principal tipo A', 1),
            ('Módulo T', 'Módulo tipo T', 2),
            ('Módulo B', 'Módulo tipo B', 3),
            ('Módulo C', 'Módulo tipo C', 4),
        ]
        
        for nome, descricao, ordem in modulos:
            modulo, created = Modulo.objects.get_or_create(
                nome=nome,
                defaults={
                    'descricao': descricao,
                    'ordem_exibicao': ordem,
                    'ativo': True
                }
            )
            if created:
                self.stdout.write(f'✓ Módulo criado: {nome}')

    def criar_componentes(self):
        """Criar componentes de soldagem"""
        componentes = [
            # Componentes com diâmetro
            ('FAIS', 'Solda FAIS', 0, True, 'diametro * 0.05'),
            ('FAIB', 'Solda FAIB', 0, True, 'diametro * 0.04'),
            ('CHAPA DA CRUZETA', 'Soldagem da chapa da cruzeta', 0, True, 'diametro * 0.03'),
            ('ANTIGIRIO', 'Soldagem antigirio', 60, False, ''),
            ('CHAPA DE SACRIFÍCIO', 'Chapa de sacrifício', 0, True, 'diametro * 0.02'),
            
            # Componentes fixos
            ('ATERRAMENTO', 'Aterramento do poste', 20, False, ''),
            ('OLHAL LINHA DE VIDA', 'Olhal para linha de vida', 18, False, ''),
            ('ESCADAS', 'Soldagem de escadas', 108, False, ''),
            ('FAIE', 'Solda FAIE', 25, False, ''),
            ('MÃO FRANCESA', 'Soldagem mão francesa', 40, False, ''),
            ('FAES', 'Solda FAES', 0, True, 'diametro * 0.035'),
            ('BASE ISOLADORA', 'Base isoladora', 95, False, ''),
            ('OLHAIS DE FASE', 'Olhais de fase', 33, False, ''),
            ('APOIO DE PÉ E MÃO', 'Apoio de pé e mão', 60, False, ''),
            ('OLHAL DE IÇAMENTO', 'Olhal de içamento', 25, False, ''),
            ('FAZER CORTE DE SEPARAÇÃO DO MÓDULO', 'Corte de separação', 30, False, ''),
            ('FAZER FURAÇÃO PARA GALV.', 'Furação para galvanização', 15, False, ''),
            ('APLICAR SILICONE ROSCAS', 'Aplicação de silicone', 10, False, ''),
            ('SOLDA UNIÃO DOS MÓDULOS', 'Solda de união entre módulos', 18, False, ''),
            ('PINTURA NÍVEL DE SOLO', 'Pintura ao nível do solo', 45, False, ''),
            ('GAVANIZAÇÃO A FRIO', 'Galvanização a frio', 30, False, ''),
            ('IDENTIFICAÇÃO DO POSTE', 'Identificação do poste', 15, False, ''),
            ('TEMPO DE ACABAMENTO DE SOLDA', 'Acabamento final', 25, False, ''),
            ('TEMPO DE INSPEÇÃO DA QUALIDADE', 'Inspeção de qualidade', 20, False, ''),
        ]
        
        for nome, descricao, tempo_padrao, considera_diametro, formula in componentes:
            componente, created = Componente.objects.get_or_create(
                nome=nome,
                defaults={
                    'descricao': descricao,
                    'tempo_padrao': Decimal(str(tempo_padrao)),
                    'considera_diametro': considera_diametro,
                    'formula_calculo': formula,
                    'ativo': True
                }
            )
            if created:
                self.stdout.write(f'✓ Componente criado: {nome}')

    def criar_tipos_parada(self):
        """Criar tipos de parada"""
        tipos_parada = [
            # Paradas gerais (soldador pode selecionar)
            ('Higiene Pessoal', 'geral', True, False, '#ffc107'),
            ('Troca de Consumíveis', 'geral', True, False, '#17a2b8'),
            ('Lanche/Café', 'geral', True, False, '#28a745'),
            ('Buscar Material', 'geral', True, False, '#6c757d'),
            ('Reunião/Instrução', 'geral', False, False, '#6f42c1'),
            ('Falta de Material', 'geral', False, False, '#dc3545'),
            
            # Paradas de manutenção (requer senha especial)
            ('Falha de Equipamento', 'manutencao', True, True, '#dc3545'),
            ('Manutenção Preventiva', 'manutencao', False, True, '#fd7e14'),
            ('Ajuste de Equipamento', 'manutencao', True, True, '#e83e8c'),
            ('Troca de Eletrodo', 'manutencao', True, False, '#20c997'),
            ('Regulagem de Soldagem', 'manutencao', True, True, '#6f42c1'),
            
            # Paradas de qualidade (requer senha especial)
            ('Avaliação de Qualidade', 'qualidade', False, True, '#007bff'),
            ('Retrabalho', 'qualidade', True, True, '#dc3545'),
            ('Inspeção Dimensional', 'qualidade', False, True, '#17a2b8'),
        ]
        
        for nome, categoria, penaliza_oee, requer_senha, cor in tipos_parada:
            tipo, created = TipoParada.objects.get_or_create(
                nome=nome,
                defaults={
                    'categoria': categoria,
                    'penaliza_oee': penaliza_oee,
                    'requer_senha_especial': requer_senha,
                    'cor_exibicao': cor,
                    'ativo': True
                }
            )
            if created:
                self.stdout.write(f'✓ Tipo de parada criado: {nome} ({categoria})')

    def criar_tipos_defeito(self):
        """Criar tipos de defeito"""
        tipos_defeito = [
            ('Porosidade', 'Poros na soldagem', '#ffc107'),
            ('Desalinhamento de Solda', 'Solda fora de posição', '#dc3545'),
            ('Falta de Penetração', 'Penetração insuficiente', '#e83e8c'),
            ('Respingo Excessivo', 'Excesso de respingos', '#fd7e14'),
            ('Mordedura', 'Mordedura na soldagem', '#6f42c1'),
            ('Trinca', 'Trinca na solda ou material', '#dc3545'),
            ('Inclusão de Escória', 'Escória incluída na soldagem', '#6c757d'),
            ('Sobreposição Inadequada', 'Sobreposição incorreta', '#17a2b8'),
            ('Dimensão Incorreta', 'Medidas fora do especificado', '#28a745'),
            ('Acabamento Superficial', 'Acabamento inadequado', '#20c997'),
        ]
        
        for nome, descricao, cor in tipos_defeito:
            tipo, created = TipoDefeito.objects.get_or_create(
                nome=nome,
                defaults={
                    'descricao': descricao,
                    'cor_exibicao': cor,
                    'ativo': True
                }
            )
            if created:
                self.stdout.write(f'✓ Tipo de defeito criado: {nome}')

    def criar_dados_demo(self):
        """Criar dados de demonstração"""
        self.stdout.write('\n--- Criando dados de demonstração ---')
        
        # Usuários de exemplo
        usuarios_demo = [
            ('jefferson', 'Jefferson Silva', 'jefferson@steelmast.com', 'analista'),
            ('qualidade01', 'Maria Qualidade', 'qualidade@steelmast.com', 'qualidade'),
            ('manutencao01', 'João Manutenção', 'manutencao@steelmast.com', 'manutencao'),
        ]
        
        for username, nome, email, tipo in usuarios_demo:
            if not Usuario.objects.filter(username=username).exists():
                usuario = Usuario.objects.create_user(
                    username=username,
                    password='123456',
                    nome_completo=nome,
                    email=email,
                    tipo_usuario=tipo
                )
                self.stdout.write(f'✓ Usuário demo criado: {username}')
        
        # Soldadores de exemplo
        soldadores_demo = [
            ('ALCIDES', 'Alcides Santos', 'alcides', '1234'),
            ('ANDRÉ', 'André Silva', 'andre', '5678'),
            ('JOSANIEL', 'Josaniel Oliveira', 'josaniel', '9012'),
            ('ADALBERTO', 'Adalberto Costa', 'adalberto', '3456'),
            ('THYERRY', 'Thyerry Lima', 'thyerry', '7890'),
            ('SULLIVAN', 'Sullivan Rocha', 'sullivan', '2468'),
        ]
        
        for nome_completo, nome_usuario, username, senha in soldadores_demo:
            if not Usuario.objects.filter(username=username).exists():
                # Criar usuário soldador
                usuario = Usuario.objects.create_user(
                    username=username,
                    password='123456',
                    nome_completo=nome_completo,
                    email=f'{username}@steelmast.com',
                    tipo_usuario='soldador'
                )
                
                # Criar perfil de soldador
                soldador = Soldador.objects.create(
                    usuario=usuario,
                    senha_simplificada=senha,
                    ativo=True
                )
                
                self.stdout.write(f'✓ Soldador demo criado: {nome_completo} (senha: {senha})')

        self.stdout.write('\n--- Dados de demonstração criados ---')
        self.stdout.write('\nSoldadores de teste:')
        for nome_completo, nome_usuario, username, senha in soldadores_demo:
            self.stdout.write(f'  {nome_completo}: senha {senha}')
        
        self.stdout.write('\nUsuários administrativos:')
        self.stdout.write('  jefferson/123456 (Analista)')
        self.stdout.write('  qualidade01/123456 (Qualidade)')
        self.stdout.write('  manutencao01/123456 (Manutenção)')
        self.stdout.write('  admin/admin123 (Administrador)')
        
        self.stdout.write('\nSenhas especiais:')
        self.stdout.write('  Qualidade: qualidade123')
        self.stdout.write('  Manutenção: manutencao123')
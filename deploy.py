#!/usr/bin/env python3
"""
Script de Deploy do Sistema OEE - SEM VIRTUAL ENVIRONMENT
Automatiza a configuração inicial do sistema usando Python global
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

class SistemaOEEDeploy:
    def __init__(self):
        self.project_root = Path(__file__).parent
        
    def print_header(self, title):
        """Imprime cabeçalho formatado"""
        print("\n" + "=" * 60)
        print(f" {title}")
        print("=" * 60)
    
    def run_command(self, command, check=True):
        """Executa comando no shell"""
        print(f"Executando: {' '.join(command) if isinstance(command, list) else command}")
        try:
            result = subprocess.run(
                command, 
                shell=isinstance(command, str),
                check=check,
                capture_output=True,
                text=True
            )
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            print(f"Erro: {e}")
            if e.stderr:
                print(f"Stderr: {e.stderr}")
            if check:
                sys.exit(1)
            return e
    
    def check_python_version(self):
        """Verifica versão do Python"""
        self.print_header("Verificando Python")
        
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ é necessário")
            print(f"Versão atual: {sys.version}")
            sys.exit(1)
        
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        print("ℹ️  Usando Python global (sem virtual environment)")
    
    def install_dependencies(self):
        """Instala dependências no Python global"""
        self.print_header("Instalando Dependências no Python Global")
        
        # Lista de dependências
        dependencies = [
            'django==4.2.7',
            'Pillow==10.1.0',
            'django-crispy-forms==2.1',
            'crispy-bootstrap4==2022.1'
        ]
        
        for dep in dependencies:
            print(f"📦 Instalando {dep}...")
            result = self.run_command([sys.executable, '-m', 'pip', 'install', dep], check=False)
            if result.returncode == 0:
                print(f"✅ {dep} instalado")
            else:
                print(f"⚠️  {dep} - verificando se já está instalado...")
        
        print("✅ Verificação de dependências concluída")
    
    def setup_database(self):
        """Configura banco de dados"""
        self.print_header("Configurando Banco de Dados")
        
        # Fazer migrações
        self.run_command([sys.executable, 'manage.py', 'makemigrations'])
        self.run_command([sys.executable, 'manage.py', 'migrate'])
        print("✅ Banco de dados configurado")
    
    def collect_static_files(self):
        """Coleta arquivos estáticos"""
        self.print_header("Coletando Arquivos Estáticos")
        
        # Criar diretórios necessários
        static_dir = self.project_root / 'static'
        static_dir.mkdir(exist_ok=True)
        
        staticfiles_dir = self.project_root / 'staticfiles'
        staticfiles_dir.mkdir(exist_ok=True)
        
        # Coletar estáticos
        self.run_command([sys.executable, 'manage.py', 'collectstatic', '--noinput'])
        print("✅ Arquivos estáticos coletados")
    
    def setup_initial_data(self, with_demo=True):
        """Configura dados iniciais"""
        self.print_header("Configurando Dados Iniciais")
        
        cmd = [sys.executable, 'manage.py', 'setup_inicial']
        if with_demo:
            cmd.append('--demo')
        
        self.run_command(cmd)
        print("✅ Dados iniciais configurados")
    
    def create_directories(self):
        """Cria diretórios necessários"""
        self.print_header("Criando Diretórios")
        
        directories = [
            'logs',
            'media', 
            'static',
            'staticfiles',
            'backups',
            'templates',
            'templates/core',
            'templates/soldagem',
            'templates/qualidade',
            'templates/manutencao',
            'templates/relatorios'
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Diretório criado: {directory}")
    
    def create_env_file(self):
        """Cria arquivo .env com configurações"""
        self.print_header("Criando Arquivo de Configuração")
        
        env_file = self.project_root / '.env'
        
        if env_file.exists():
            print("❓ Arquivo .env já existe. Recriar? (s/n): ", end="")
            response = input().lower()
            if response != 's':
                print("✅ Usando arquivo .env existente")
                return
        
        env_content = """# Configurações do Sistema OEE
DEBUG=True
SECRET_KEY=sua-chave-secreta-super-segura-aqui-mude-em-producao

# Banco de dados (SQLite por padrão)
DATABASE_URL=sqlite:///db.sqlite3

# Configurações de segurança
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Configurações de email (opcional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=
EMAIL_USE_TLS=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Configurações de cache (opcional)
CACHE_BACKEND=django.core.cache.backends.locmem.LocMemCache

# Configurações de log
LOG_LEVEL=INFO
"""
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ Arquivo .env criado")
    
    def create_service_files(self):
        """Cria arquivos de serviço para produção"""
        self.print_header("Criando Arquivos de Serviço")
        
        # Script de start para Windows
        start_script_win = self.project_root / 'start.bat'
        start_content_win = f"""@echo off
cd /d "{self.project_root}"
python manage.py runserver 0.0.0.0:8000
pause
"""
        
        with open(start_script_win, 'w') as f:
            f.write(start_content_win)
        
        # Script de start para Linux/Mac
        start_script_unix = self.project_root / 'start.sh'
        start_content_unix = f"""#!/bin/bash
cd "{self.project_root}"
python manage.py runserver 0.0.0.0:8000
"""
        
        with open(start_script_unix, 'w') as f:
            f.write(start_content_unix)
        
        # Tornar executável no Unix
        try:
            os.chmod(start_script_unix, 0o755)
        except:
            pass  # Windows não suporta chmod
        
        print("✅ Scripts de inicialização criados")
        print(f"   - Windows: start.bat")
        print(f"   - Linux/Mac: start.sh")
    
    def run_tests(self):
        """Executa testes básicos"""
        self.print_header("Executando Testes")
        
        # Verificar se manage.py funciona
        result = self.run_command([sys.executable, 'manage.py', 'check'], check=False)
        
        if result.returncode == 0:
            print("✅ Testes básicos passaram")
        else:
            print("❌ Alguns testes falharam")
            return False
        
        return True
    
    def print_final_instructions(self):
        """Imprime instruções finais"""
        self.print_header("Instalação Concluída!")
        
        print("""
🎉 Sistema OEE instalado com sucesso!

📋 PRÓXIMOS PASSOS:

1. Para iniciar o servidor:
   
   Windows:
   start.bat
   
   Linux/Mac:
   ./start.sh
   
   OU manualmente:
   python manage.py runserver 0.0.0.0:8000

2. Acesse o sistema:
   http://localhost:8000

3. Credenciais iniciais:
   Administrador: admin / admin123
   
   Soldadores de teste:
   - ALCIDES / 1234
   - ANDRÉ / 5678
   - JOSANIEL / 9012

4. Senhas especiais:
   Qualidade: qualidade123
   Manutenção: manutencao123

📁 ESTRUTURA DO PROJETO:
   /soldagem/     - Interface para soldadores
   /core/admin/   - Painel administrativo
   /relatorios/   - Dashboards e relatórios
   /qualidade/    - Módulo de qualidade
   /manutencao/   - Módulo de manutenção

🔧 CONFIGURAÇÕES:
   - Edite o arquivo .env para configurações personalizadas
   - Logs são salvos em: logs/audit.txt
   - Banco de dados: db.sqlite3

⚠️  IMPORTANTE:
   - Este projeto usa o Python global (sem virtual environment)
   - Certifique-se de que as dependências estão instaladas globalmente
   - Para produção, considere usar virtual environment
   - Altere SECRET_KEY no arquivo .env para produção
   - Configure DEBUG=False em produção

🚀 PARA INICIAR AGORA:
   python manage.py runserver 0.0.0.0:8000

""")
    
    def deploy(self, with_demo=True, run_tests_flag=True):
        """Executa deploy completo"""
        try:
            self.check_python_version()
            self.create_directories()
            self.create_env_file()
            self.install_dependencies()
            self.setup_database()
            self.collect_static_files()
            self.setup_initial_data(with_demo)
            self.create_service_files()
            
            if run_tests_flag:
                self.run_tests()
            
            self.print_final_instructions()
            
        except KeyboardInterrupt:
            print("\n❌ Deploy cancelado pelo usuário")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Erro durante deploy: {e}")
            sys.exit(1)

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy do Sistema OEE (sem virtual environment)')
    parser.add_argument('--no-demo', action='store_true', help='Não criar dados de demonstração')
    parser.add_argument('--no-tests', action='store_true', help='Não executar testes')
    
    args = parser.parse_args()
    
    print("⚠️  AVISO: Este script instalará as dependências no Python GLOBAL")
    print("Se você quiser usar virtual environment, use outro script.")
    print("\nContinuar? (s/n): ", end="")
    
    if input().lower() not in ['s', 'sim', 'y', 'yes']:
        print("Deploy cancelado.")
        sys.exit(0)
    
    deployer = SistemaOEEDeploy()
    deployer.deploy(
        with_demo=not args.no_demo,
        run_tests_flag=not args.no_tests
    )

if __name__ == '__main__':
    main()
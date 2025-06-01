#!/usr/bin/env python3
"""
Script de teste para os simuladores OCPP
Este script ajuda a executar e testar os simuladores de forma organizada
"""

import asyncio
import subprocess
import time
import sys
import os
import logging
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simulator_tester')


class SimulatorTester:
    def __init__(self):
        self.processes = []
        self.base_dir = Path.cwd()

    def check_dependencies(self):
        """Verifica se as dependências estão instaladas"""
        logger.info("🔍 Verificando dependências...")

        required_packages = [
            'websockets',
            'ocpp',
            'requests',
            'fastapi',
            'uvicorn'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
                logger.info(f"✅ {package} - OK")
            except ImportError:
                missing_packages.append(package)
                logger.error(f"❌ {package} - FALTANDO")

        if missing_packages:
            logger.error("📦 Instale os pacotes faltantes com:")
            logger.error(f"pip install {' '.join(missing_packages)}")
            return False

        logger.info("✅ Todas as dependências estão instaladas!")
        return True

    def check_files(self):
        """Verifica se os arquivos necessários existem"""
        logger.info("📁 Verificando arquivos...")

        required_files = [
            'D:\dev\SIGEC-VE\pythonProject\ev_charging_system\simulator\charge_point_simulator.py',
            'D:\dev\SIGEC-VE\pythonProject\ev_charging_system\simulator\ev_simulator.py',
            'D:\dev\SIGEC-VE\pythonProject\ev_charging_system\core\ocpp_server.py'
        ]

        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
                logger.error(f"❌ {file} - NÃO ENCONTRADO")
            else:
                logger.info(f"✅ {file} - OK")

        if missing_files:
            logger.error("🚫 Arquivos faltantes encontrados!")
            return False

        logger.info("✅ Todos os arquivos necessários encontrados!")
        return True

    def fix_charge_point_simulator(self):
        """Corrige imports faltantes no simulador de charge point"""
        logger.info("🔧 Corrigindo imports no charge_point_simulator.py...")

        file_path = 'D:\dev\SIGEC-VE\pythonProject\ev_charging_system\simulator\charge_point_simulator.py'

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Adiciona imports faltantes se não existirem
            imports_to_add = [
                "import random",
                "from datetime import datetime"
            ]

            content_modified = False
            for import_line in imports_to_add:
                if import_line not in content:
                    # Adiciona após os outros imports
                    lines = content.split('\n')
                    import_index = 0
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith('from '):
                            import_index = i

                    lines.insert(import_index + 1, import_line)
                    content = '\n'.join(lines)
                    content_modified = True
                    logger.info(f"✅ Adicionado: {import_line}")

            # Salva o arquivo corrigido apenas se foi modificado
            if content_modified:
                with open(file_path, 'w') as f:
                    f.write(content)
                logger.info("🔧 Correções aplicadas!")
            else:
                logger.info("✅ Arquivo já está correto!")

        except FileNotFoundError:
            logger.warning(f"⚠️ {file_path} não encontrado, pulando correções")
        except Exception as e:
            logger.error(f"❌ Erro ao corrigir arquivo: {e}")

    async def start_ocpp_server(self):
        """Inicia o servidor OCPP"""
        logger.info("🚀 Iniciando servidor OCPP...")

        try:
            # Executa o servidor OCPP em processo separado
            process = subprocess.Popen([
                sys.executable, '../core/ocpp_server.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            self.processes.append(('OCPP Server-->>', process))

            # Aguarda um pouco para o servidor inicializar
            await asyncio.sleep(3)

            # Verifica se o processo ainda está rodando
            if process.poll() is None:
                logger.info("✅ Servidor OCPP iniciado com sucesso!")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ Servidor OCPP falhou: {stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Erro ao iniciar servidor OCPP: {e}")
            return False

    async def start_charge_point_simulator(self):
        """Inicia o simulador de charge point"""
        logger.info("🔌 Iniciando simulador de Charge Point...")

        try:
            process = subprocess.Popen([
                sys.executable, './ev_charging_system/simulator/charge_point_simulator.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            self.processes.append(('Charge Point Simulator', process))

            # Aguarda um pouco para conectar
            await asyncio.sleep(5)

            if process.poll() is None:
                logger.info("✅ Simulador de Charge Point iniciado!")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ Simulador de CP falhou: {stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Erro ao iniciar simulador CP: {e}")
            return False

    async def run_ev_simulator(self):
        """Executa o simulador de EV"""
        logger.info("🚗 Executando simulador de Veículo Elétrico...")

        try:
            # Using asyncio subprocess for better output handling
            process = await asyncio.create_subprocess_exec(
                sys.executable, './ev_charging_system/simulator/ev_simulator.py',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if stdout:
                logger.info("📊 Saída do simulador EV:")
                logger.info(stdout.decode())

            if stderr:
                logger.warning("⚠️ Erros do simulador EV:")
                logger.warning(stderr.decode())

            logger.info("✅ Simulador de EV concluído!")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao executar simulador EV: {e}")
            return False

    def cleanup(self):
        """Limpa os processos iniciados"""
        logger.info("🧹 Finalizando processos...")

        for name, process in self.processes:
            try:
                if process.poll() is None:  # Processo ainda rodando
                    logger.info(f"🛑 Terminando {name}...")
                    process.terminate()

                    # Aguarda até 5 segundos para terminar graciosamente
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"⚠️ Forçando término de {name}...")
                        process.kill()
                        process.wait()

                    logger.info(f"✅ {name} finalizado")
            except Exception as e:
                logger.error(f"❌ Erro ao finalizar {name}: {e}")

        self.processes.clear()
        logger.info("🧹 Limpeza concluída!")

    async def run_full_test(self):
        """Executa o teste completo dos simuladores"""
        logger.info("🎯 Iniciando teste completo dos simuladores...")

        try:
            # 1. Verificações iniciais
            if not self.check_dependencies() or not self.check_files():
                return False

            # 2. Corrige arquivos se necessário
            self.fix_charge_point_simulator()

            # 3. Inicia servidor OCPP
            if not await self.start_ocpp_server():
                return False

            # 4. Inicia simulador de Charge Point
            if not await self.start_charge_point_simulator():
                return False

            # 5. Aguarda estabilização
            logger.info("⏳ Aguardando estabilização dos sistemas...")
            await asyncio.sleep(5)

            # 6. Executa simulador de EV
            await self.run_ev_simulator()

            # 7. Mantém sistemas rodando por um tempo para observação
            logger.info("👀 Sistemas rodando... Observe os logs por 30 segundos")
            await asyncio.sleep(30)

            logger.info("🎉 Teste completo finalizado com sucesso!")
            return True

        except KeyboardInterrupt:
            logger.info("⏹️ Teste interrompido pelo usuário")
            return False
        except Exception as e:
            logger.error(f"❌ Erro durante o teste: {e}")
            return False
        finally:
            self.cleanup()

    async def run_quick_test(self):
        """Executa um teste rápido apenas do simulador EV"""
        logger.info("⚡ Teste rápido - apenas simulador EV...")

        if not self.check_dependencies():
            return False

        await self.run_ev_simulator()
        logger.info("✅ Teste rápido concluído!")


# Função principal
async def main():
    print("🧪 TESTADOR DE SIMULADORES OCPP")
    print("=" * 50)
    print("Escolha uma opção:")
    print("1. Teste completo (servidor + CP + EV)")
    print("2. Teste rápido (apenas EV)")
    print("3. Verificar dependências")
    print("4. Sair")

    choice = input("\nDigite sua escolha (1-4): ").strip()

    tester = SimulatorTester()

    if choice == "1":
        await tester.run_full_test()
    elif choice == "2":
        await tester.run_quick_test()
    elif choice == "3":
        tester.check_dependencies()
        tester.check_files()
    elif choice == "4":
        print("👋 Até logo!")
        return
    else:
        print("❌ Opção inválida!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Teste interrompido!")
    except Exception as e:
        print(f"❌ Erro: {e}")
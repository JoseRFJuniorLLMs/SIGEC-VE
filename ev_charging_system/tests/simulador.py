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
            '../simulator/charge_point_simulator.py',
            '../simulator/ev_simulator.py',
            '../core/ocpp_server.py'
        ]

        missing_files = []
        for file_path_str in required_files:
            file_path = (self.base_dir / file_path_str).resolve()
            if not file_path.exists():
                missing_files.append(file_path_str)
                logger.error(f"❌ {file_path_str} - FALTANDO")
            else:
                logger.info(f"✅ {file_path_str} - OK")

        if missing_files:
            logger.error("Arquivos necessários faltando. Verifique o caminho.")
            return False
        logger.info("✅ Todos os arquivos necessários encontrados!")
        return True

    # Esta função fix_charge_point_simulator foi removida do fluxo de teste
    # pois estava causando problemas de indentação.
    # def fix_charge_point_simulator(self):
    #     """
    #     Corrige imports faltantes e incorretos no simulador de charge point.
    #     Isso é uma correção temporária para um problema de importação específico.
    #     """
    #     cp_sim_path = (self.base_dir / '../simulator/charge_point_simulator.py').resolve()
    #     logger.info(f"🔧 Corrigindo imports no {cp_sim_path.name}...")
    #     try:
    #         with open(cp_sim_path, 'r', encoding='utf-8') as f:
    #             content = f.readlines()

    #         new_content = []
    #         fixed = False
    #         for line in content:
    #             # A linha que causa o erro "cannot import name 'BootNotification' from 'ocpp.v201.call'"
    #             if "from ocpp.v201.call import BootNotification" in line:
    #                 line = "# " + line # Comenta a linha problemática
    #                 fixed = True
    #                 logger.info("Comentada linha 'from ocpp.v201.call import BootNotification'")
    #             new_content.append(line)

    #         if fixed:
    #             with open(cp_sim_path, 'w', encoding='utf-8') as f:
    #                 f.writelines(new_content)
    #             logger.info("✅ Arquivo corrigido com sucesso!")
    #         else:
    #             logger.info("✅ Arquivo já está correto! (Nenhuma correção necessária no momento)")

    #     except Exception as e:
    #         logger.error(f"❌ Erro ao corrigir {cp_sim_path.name}: {e}")
    #         logger.warning("Pode ser necessário corrigir manualmente os imports do Charge Point.")
    #         return False
    #     return True

    async def run_ocpp_server(self):
        """Inicia o servidor OCPP como um subprocesso"""
        logger.info("🚀 Iniciando servidor OCPP...")
        server_path = (self.base_dir / '../core/ocpp_server.py').resolve()

        # Certifica-se de que o python do venv está sendo usado
        python_executable = sys.executable

        try:
            # Captura a saída e o erro do subprocesso
            process = await asyncio.create_subprocess_exec(
                python_executable, str(server_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.processes.append(process)

            # Lê a saída inicial para verificar se o servidor iniciou com sucesso
            # Lê até a primeira linha que indica sucesso ou erro fatal
            output_lines = []

            # Timeout para esperar a inicialização do servidor
            timeout = 3  # segundos
            start_time = time.time()
            server_started = False

            while True:
                if process.stdout.at_eof() and process.stderr.at_eof():
                    break  # Processo terminou

                try:
                    # Tenta ler uma linha do stdout ou stderr
                    line = await asyncio.wait_for(process.stdout.readline(), 0.1)
                    if not line:
                        line = await asyncio.wait_for(process.stderr.readline(), 0.1)
                        if not line:
                            await asyncio.sleep(0.1)  # Pequena pausa se nada for lido
                            continue

                    decoded_line = line.decode().strip()
                    if decoded_line:
                        logger.info(decoded_line)  # Loga a saída do servidor
                        output_lines.append(decoded_line)
                        if "OCPP WebSocket Server started successfully" in decoded_line or "server listening on" in decoded_line:
                            server_started = True
                            break
                        if "Erro inesperado" in decoded_line or "error while attempting to bind" in decoded_line:
                            logger.error(f"❌ Servidor OCPP falhou: {decoded_line}")
                            # Tenta ler o restante do stderr para capturar o traceback completo
                            remaining_stderr = (await process.stderr.read()).decode().strip()
                            if remaining_stderr:
                                logger.error(remaining_stderr)
                            return False

                except asyncio.TimeoutError:
                    if time.time() - start_time > timeout:
                        logger.error("❌ Timeout ao esperar pelo servidor OCPP iniciar.")
                        return False
                    continue  # Continua tentando ler

            if not server_started:
                logger.error("❌ Servidor OCPP não indicou inicialização bem-sucedida.")
                return False

            return True
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao executar o servidor OCPP: {e}")
            return False

    async def run_charge_point_simulator(self):
        """Inicia o simulador de Charge Point como um subprocesso"""
        logger.info("🔌 Iniciando simulador de Charge Point...")
        cp_path = (self.base_dir / '../simulator/charge_point_simulator.py').resolve()
        python_executable = sys.executable
        try:
            process = await asyncio.create_subprocess_exec(
                python_executable, str(cp_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.processes.append(process)

            # Espera um pouco para o CP se conectar e enviar BootNotification
            await asyncio.sleep(5)  # Ajuste este tempo conforme necessário

            # Lê a saída e erros para log
            stdout, stderr = await process.communicate()
            if stdout:
                for line in stdout.decode().splitlines():
                    logger.info(f"CP: {line}")
            if stderr:
                for line in stderr.decode().splitlines():
                    logger.error(f"CP: {line}")
                # Não retornamos False aqui, apenas logamos o erro, pois o CP pode ter
                # tentado algo e falhado, mas o simulador em si pode não ter travado.
                # O retorno de código do processo será verificado abaixo.

            if process.returncode != 0:
                logger.error(f"❌ Simulador de CP terminou com código de erro: {process.returncode}")
                return False
            return True
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao executar o simulador de CP: {e}")
            return False

    async def run_ev_simulator(self):
        """Inicia o simulador de EV como um subprocesso"""
        logger.info("🚗 Iniciando simulador de EV...")
        ev_path = (self.base_dir / '../simulator/ev_simulator.py').resolve()
        python_executable = sys.executable
        try:
            process = await asyncio.create_subprocess_exec(
                python_executable, str(ev_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.processes.append(process)

            # Espera um pouco para o EV operar
            await asyncio.sleep(5)  # Ajuste este tempo conforme necessário

            stdout, stderr = await process.communicate()
            if stdout:
                for line in stdout.decode().splitlines():
                    logger.info(f"EV: {line}")
            if stderr:
                for line in stderr.decode().splitlines():
                    logger.error(f"EV: {line}")
                # Não retornamos False aqui, apenas logamos o erro, pois o EV pode ter
                # tentado algo e falhado, mas o simulador em si pode não ter travado.
                # O retorno de código do processo será verificado abaixo.

            if process.returncode != 0:
                logger.error(f"❌ Simulador de EV terminou com código de erro: {process.returncode}")
                return False
            return True
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao executar o simulador de EV: {e}")
            return False

    def cleanup(self):
        """Finaliza todos os subprocessos iniciados"""
        logger.info("🧹 Finalizando processos...")
        for process in self.processes:
            if process.returncode is None:  # Se o processo ainda estiver rodando
                logger.info(f"🛑 Terminando processo {process.pid}...")
                process.terminate()
                try:
                    process.wait(timeout=5)  # Espera 5 segundos para o processo terminar
                except subprocess.TimeoutExpired:
                    logger.warning(f"Processo {process.pid} não terminou, matando...")
                    process.kill()
        logger.info("🧹 Limpeza concluída!")

    async def run_full_test(self):
        """
        Executa um teste completo (CP + EV).
        O servidor OCPP principal DEVE estar rodando separadamente.
        """
        logger.info("🎯 Iniciando teste completo dos simuladores (CP + EV)...")

        if not self.check_dependencies():
            return False

        if not self.check_files():
            return False

        # As linhas abaixo foram comentadas/removidas porque o servidor OCPP
        # deve estar sendo executado externamente (por exemplo, via Uvicorn).
        # self.fix_charge_point_simulator() # Removido para evitar problemas de indentação.

        # if not await self.run_ocpp_server():
        #     logger.error("❌ Servidor OCPP falhou.")
        #     self.cleanup()
        #     return False
        # logger.info("✅ Servidor OCPP iniciado com sucesso!")

        logger.info("🔌 Iniciando simulador de Charge Point...")
        if not await self.run_charge_point_simulator():
            logger.error("❌ Simulador de CP falhou.")
            self.cleanup()
            return False
        logger.info("✅ Simulador de Charge Point iniciado com sucesso!")

        logger.info("🚗 Iniciando simulador de EV...")
        if not await self.run_ev_simulator():
            logger.error("❌ Simulador de EV falhou.")
            self.cleanup()
            return False
        logger.info("✅ Simulador de EV iniciado com sucesso!")

        logger.info("🎉 Teste completo concluído com sucesso!")
        return True

    async def run_test(self, test_func):
        try:
            await test_func()
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
    print("1. Teste completo (CP + EV - Servidor já em execução)")
    print("2. Teste rápido (apenas EV)")
    print("3. Verificar dependências")
    print("4. Sair")

    choice = input("\nDigite sua escolha (1-4): ").strip()

    tester = SimulatorTester()

    if choice == "1":
        await tester.run_test(tester.run_full_test)
    elif choice == "2":
        await tester.run_test(tester.run_quick_test)
    elif choice == "3":
        tester.check_dependencies()
        tester.check_files()
    elif choice == "4":
        print("👋 Até logo!")
    else:
        print("❌ Opção inválida. Por favor, digite um número entre 1 e 4.")


if __name__ == '__main__':
    asyncio.run(main())
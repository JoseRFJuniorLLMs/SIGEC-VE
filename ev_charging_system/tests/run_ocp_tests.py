#!/usr/bin/env python3
"""
Script para executar testes OCPP completos
"""

import asyncio
import subprocess
import sys
import time
import signal
import os
from pathlib import Path


class OCPPTestRunner:
    def __init__(self):
        self.server_process = None

    def start_server(self):
        """Inicia o servidor OCPP em um processo separado"""
        print("🚀 Iniciando servidor OCPP...")

        try:
            self.server_process = subprocess.Popen([
                sys.executable, "ocpp_test_server.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Aguardar um pouco para o servidor iniciar
            time.sleep(2)

            if self.server_process.poll() is None:
                print("✅ Servidor OCPP iniciado com sucesso!")
                return True
            else:
                stdout, stderr = self.server_process.communicate()
                print(f"❌ Erro ao iniciar servidor:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False

        except Exception as e:
            print(f"❌ Erro ao iniciar servidor: {e}")
            return False

    def stop_server(self):
        """Para o servidor OCPP"""
        if self.server_process and self.server_process.poll() is None:
            print("🛑 Parando servidor OCPP...")
            self.server_process.terminate()

            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️ Forçando término do servidor...")
                self.server_process.kill()
                self.server_process.wait()

            print("✅ Servidor OCPP parado")

    async def run_client_tests(self):
        """Executa os testes do cliente"""
        print("\n🧪 Executando testes do cliente OCPP...")

        try:
            # Importar e executar o teste
            from test_cp import test_complete_scenario
            await test_complete_scenario()

        except ImportError:
            print("❌ Não foi possível importar test_cp.py")
            print("Certifique-se de que o arquivo existe no diretório atual")
            return False
        except Exception as e:
            print(f"❌ Erro durante os testes: {e}")
            return False

        return True

    async def run_multiple_clients(self, num_clients: int = 3):
        """Executa múltiplos clientes para teste de carga"""
        print(f"\n🏃‍♂️ Executando teste com {num_clients} clientes simultâneos...")

        tasks = []
        for i in range(num_clients):
            async def run_client(client_id):
                from test_cp import OCPPTestClient

                client = OCPPTestClient(f"CP_LOAD_TEST_{client_id:03d}")

                try:
                    if await client.connect():
                        accepted, _ = await client.boot_notification()
                        if accepted:
                            await client.heartbeat()
                            await client.status_notification(1, "Available")
                            print(f"✅ Cliente {client_id} completou teste básico")
                        await client.disconnect()
                except Exception as e:
                    print(f"❌ Erro no cliente {client_id}: {e}")

            tasks.append(run_client(i + 1))

        await asyncio.gather(*tasks, return_exceptions=True)
        print(f"✅ Teste de carga com {num_clients} clientes concluído")

    def cleanup(self):
        """Limpeza final"""
        self.stop_server()


def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    required_modules = ['websockets', 'asyncio']
    missing = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if missing:
        print("❌ Módulos necessários não encontrados:")
        for module in missing:
            print(f"  - {module}")
        print("\nInstale com: pip install websockets")
        return False

    return True


def check_files():
    """Verifica se os arquivos necessários existem"""
    required_files = ['test_cp.py', 'ocpp_test_server.py']
    missing = []

    for file in required_files:
        if not Path(file).exists():
            missing.append(file)

    if missing:
        print("❌ Arquivos necessários não encontrados:")
        for file in missing:
            print(f"  - {file}")
        return False

    return True


async def main():
    """Função principal"""
    print("🔧 OCPP Test Suite")
    print("=" * 50)

    # Verificar pré-
import asyncio
import websockets
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_connection_only():
    """Testa apenas a conexão sem enviar mensagens, e então envia um BootNotification."""
    try:
        logger.info("🔄 Testando conexão OCPP 2.0 e enviando BootNotification imediato...")

        async with websockets.connect(
                "ws://localhost:9000/CP001",
                subprotocols=['ocpp2.0', 'ocpp2.0.1'],
                timeout=10
        ) as websocket:
            logger.info(f"✅ Conectado! Subprotocol: {websocket.subprotocol}")

            # --- Adição aqui: Enviar BootNotification imediatamente ---
            boot_msg = [2, "test_conn_boot", "BootNotification", {
                "chargingStation": {
                    "vendorName": "TestClient",
                    "model": "TestModel"
                },
                "reason": "PowerUp"
            }]
            await websocket.send(json.dumps(boot_msg))
            logger.info("📤 Enviado BootNotification após conexão.")

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0) # Aumente o timeout se necessário
                logger.info(f"📥 Servidor respondeu ao BootNotification: {response}")
                # Verifique se a resposta é um CallResult (tipo 3) para BootNotification
                resp_data = json.loads(response)
                if len(resp_data) >= 3 and resp_data[0] == 3 and resp_data[1] == "test_conn_boot":
                    logger.info("✅ BootNotification aceito. Conexão OK!")
                    await asyncio.sleep(3) # Keep connection alive for a bit
                    return True
                else:
                    logger.error(f"❌ Resposta inesperada ao BootNotification: {response}")
                    return False
            except asyncio.TimeoutError:
                logger.error("⏰ Timeout aguardando resposta ao BootNotification.")
                return False
            except Exception as e:
                logger.error(f"❌ Erro ao processar resposta do BootNotification: {e}")
                return False

    except Exception as e:
        logger.error(f"❌ Erro na conexão: {e}")
        return False


async def test_simple_messages():
    """Testa mensagens muito simples"""
    simple_messages = [
        # Mensagem vazia
        "{}",
        # Array vazio
        "[]",
        # Ping simples
        '["ping"]',
        # Mensagem OCPP 2.0 mais simples possível
        '[2, "test", "Heartbeat", {}]'
    ]

    for msg in simple_messages:
        try:
            logger.info(f"🔄 Testando mensagem: {msg}")

            async with websockets.connect(
                    "ws://localhost:9000/CP001",
                    subprotocols=['ocpp2.0', 'ocpp2.0.1'],
                    timeout=5
            ) as websocket:

                await websocket.send(msg)
                logger.info(f"📤 Enviado: {msg}")

                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    logger.info(f"📥 Resposta: {response}")
                    logger.info("✅ Mensagem aceita!")
                    return msg  # Retorna a primeira mensagem que funcionou

                except asyncio.TimeoutError:
                    logger.info("⏰ Timeout - mas não fechou conexão")

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"❌ Conexão fechada: {e.code} - {e.reason}")
        except Exception as e:
            logger.error(f"❌ Erro: {e}")

    return None


async def test_ocpp20_messages():
    """Testa mensagens OCPP 2.0 específicas"""

    # Diferentes formatos de BootNotification para OCPP 2.0
    boot_messages = [
        # Formato 1: OCPP 2.0 básico
        [2, "1", "BootNotification", {
            "chargingStation": {
                "vendorName": "TestVendor",
                "model": "TestModel"
            },
            "reason": "PowerUp"
        }],

        # Formato 2: OCPP 2.0 completo
        [2, "2", "BootNotification", {
            "chargingStation": {
                "vendorName": "TestVendor",
                "model": "TestModel",
                "serialNumber": "CS-001",
                "firmwareVersion": "1.0.0"
            },
            "reason": "PowerUp"
        }],

        # Formato 3: OCPP 2.0 com campos opcionais
        [2, "3", "BootNotification", {
            "chargingStation": {
                "vendorName": "TestVendor",
                "model": "TestModel",
                "serialNumber": "CS-001",
                "firmwareVersion": "1.0.0",
                "modem": {
                    "iccid": "89860000000000000000",
                    "imsi": "001010000000000"
                }
            },
            "reason": "PowerUp"
        }]
    ]

    for i, boot_msg in enumerate(boot_messages, 1):
        try:
            logger.info(f"🔄 Testando BootNotification OCPP 2.0 formato {i}...")

            async with websockets.connect(
                    "ws://localhost:9000",
                    subprotocols=['ocpp2.0', 'ocpp2.0.1'],
                    timeout=5
            ) as websocket:

                msg_str = json.dumps(boot_msg)
                logger.info(f"📤 Enviando: {msg_str}")
                await websocket.send(msg_str)

                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    logger.info(f"📥 Resposta: {response}")

                    # Tenta parsear a resposta
                    try:
                        resp_data = json.loads(response)
                        if len(resp_data) >= 3:
                            msg_type = resp_data[0]
                            msg_id = resp_data[1]
                            if msg_type == 3:  # CallResult
                                logger.info("✅ CallResult recebido - BootNotification aceito!")
                                return boot_msg
                            elif msg_type == 4:  # CallError
                                logger.info(f"❌ CallError: {resp_data[3]} - {resp_data[4]}")
                    except:
                        logger.info("📄 Resposta não é JSON válido")

                except asyncio.TimeoutError:
                    logger.info("⏰ Timeout aguardando resposta")

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"❌ Conexão fechada código {e.code}: {e.reason}")
        except Exception as e:
            logger.error(f"❌ Erro: {e}")

    return None


async def test_heartbeat_ocpp20():
    """Testa Heartbeat OCPP 2.0"""
    heartbeat_msg = [2, "hb1", "Heartbeat", {}]

    try:
        logger.info("🔄 Testando Heartbeat OCPP 2.0...")

        async with websockets.connect(
                "ws://localhost:9000",
                subprotocols=['ocpp2.0', 'ocpp2.0.1'],
                timeout=5
        ) as websocket:

            msg_str = json.dumps(heartbeat_msg)
            logger.info(f"📤 Enviando Heartbeat: {msg_str}")
            await websocket.send(msg_str)

            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                logger.info(f"📥 Resposta Heartbeat: {response}")
                return True
            except asyncio.TimeoutError:
                logger.info("⏰ Timeout no Heartbeat")

    except Exception as e:
        logger.error(f"❌ Erro no Heartbeat: {e}")

    return False


async def test_with_charger_id():
    """Testa com ID do carregador no path"""
    charger_paths = [
        "ws://localhost:9000/CP001",
        "ws://localhost:9000/charger1",
        "ws://localhost:9000/station1"
    ]

    boot_msg = [2, "1", "BootNotification", {
        "chargingStation": {
            "vendorName": "TestVendor",
            "model": "TestModel"
        },
        "reason": "PowerUp"
    }]

    for path in charger_paths:
        try:
            logger.info(f"🔄 Testando path: {path}")

            async with websockets.connect(
                    path,
                    subprotocols=['ocpp2.0', 'ocpp2.0.1'],
                    timeout=5
            ) as websocket:

                msg_str = json.dumps(boot_msg)
                await websocket.send(msg_str)
                logger.info(f"📤 Enviado para {path}")

                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    logger.info(f"📥 Resposta: {response}")
                    logger.info(f"✅ Path funcionou: {path}")
                    return path

                except asyncio.TimeoutError:
                    logger.info("⏰ Timeout")

        except Exception as e:
            logger.info(f"❌ Path {path} falhou: {str(e)[:50]}...")

    return None


async def monitor_server_behavior():
    """Monitora o comportamento do servidor"""
    try:
        logger.info("🔄 Monitorando comportamento do servidor OCPP 2.0...")

        async with websockets.connect(
                "ws://localhost:9000",
                subprotocols=['ocpp2.0', 'ocpp2.0.1'],
                timeout=10
        ) as websocket:

            logger.info("✅ Conectado - aguardando qualquer mensagem do servidor...")

            # Aguarda para ver se o servidor envia algo espontaneamente
            for i in range(5):
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    logger.info(f"📥 Servidor enviou espontaneamente: {msg}")
                except asyncio.TimeoutError:
                    logger.info(f"⏰ Tentativa {i + 1}/5 - nada recebido")

            # Envia uma mensagem inválida para ver o que acontece
            logger.info("📤 Enviando mensagem inválida para testar...")
            await websocket.send("mensagem_invalida")

            try:
                error_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                logger.info(f"📥 Resposta ao erro: {error_response}")
            except asyncio.TimeoutError:
                logger.info("⏰ Sem resposta ao erro")
            except websockets.exceptions.ConnectionClosed as e:
                logger.info(f"🔌 Servidor fechou conexão: {e.code} - {e.reason}")

    except Exception as e:
        logger.error(f"❌ Erro no monitoramento: {e}")


async def test_protocol_versions():
    """Testa diferentes versões do protocolo OCPP"""
    protocols = [
        ['ocpp2.0'],
        ['ocpp2.0.1'],
        ['ocpp2.1'],
        ['ocpp1.6'],  # Para comparação
        ['ocpp2.0', 'ocpp2.0.1'],
        ['ocpp2.0', 'ocpp1.6']
    ]

    for protocol_list in protocols:
        try:
            logger.info(f"🔄 Testando protocolo(s): {protocol_list}")

            async with websockets.connect(
                    "ws://localhost:9000",
                    subprotocols=protocol_list,
                    timeout=5
            ) as websocket:

                logger.info(f"✅ Conectado com: {websocket.subprotocol}")
                await asyncio.sleep(1)

        except Exception as e:
            logger.info(f"❌ Protocolo {protocol_list} falhou: {str(e)[:100]}...")


async def main():
    """Função principal de diagnóstico detalhado para OCPP 2.0"""
    logger.info("🔍 Diagnóstico Detalhado OCPP 2.0 Server")
    logger.info("=" * 50)

    # Teste 0: Diferentes protocolos
    logger.info("\n0️⃣ Testando versões de protocolo...")
    await test_protocol_versions()

    # Teste 1: Conexão pura
    logger.info("\n1️⃣ Teste de conexão pura OCPP 2.0...")
    connection_ok = await test_connection_only()

    if not connection_ok:
        logger.error("❌ Não conseguiu conectar com OCPP 2.0!")
        return

    # Teste 2: Monitorar comportamento
    logger.info("\n2️⃣ Monitorando comportamento do servidor...")
    await monitor_server_behavior()

    # Teste 3: Mensagens simples
    logger.info("\n3️⃣ Testando mensagens simples...")
    working_msg = await test_simple_messages()

    if working_msg:
        logger.info(f"✅ Mensagem que funcionou: {working_msg}")

    # Teste 4: Heartbeat OCPP 2.0
    logger.info("\n4️⃣ Testando Heartbeat OCPP 2.0...")
    heartbeat_ok = await test_heartbeat_ocpp20()

    # Teste 5: OCPP 2.0 BootNotification
    logger.info("\n5️⃣ Testando BootNotification OCPP 2.0...")
    working_boot = await test_ocpp20_messages()

    if working_boot:
        logger.info(f"✅ BootNotification que funcionou: {working_boot}")

    # Teste 6: Paths com charger ID
    logger.info("\n6️⃣ Testando paths com charger ID...")
    working_path = await test_with_charger_id()

    if working_path:
        logger.info(f"✅ Path que funcionou: {working_path}")

    # Resumo
    logger.info("\n" + "=" * 50)
    logger.info("📋 RESUMO DETALHADO OCPP 2.0:")
    logger.info("✅ Testando com subprotocols 'ocpp2.0' e 'ocpp2.0.1'")
    logger.info("✅ Mensagens BootNotification adaptadas para OCPP 2.0")
    logger.info("✅ Estrutura de dados OCPP 2.0 (chargingStation object)")
    logger.info("\n💡 PRINCIPAIS DIFERENÇAS OCPP 1.6 vs 2.0:")
    logger.info("• Subprotocol: 'ocpp1.6' → 'ocpp2.0'")
    logger.info("• BootNotification: campos diretos → objeto 'chargingStation'")
    logger.info("• Novos campos obrigatórios como 'reason'")
    logger.info("• Estrutura de dados mais hierárquica")


if __name__ == "__main__":
    asyncio.run(main())
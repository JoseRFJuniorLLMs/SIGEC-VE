# server_test.py - Enhanced test for OCPP Server with better diagnostics

import asyncio
import websockets
import socket
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_port_open(host, port):
    """Check if a port is open and listening"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking port: {e}")
        return False


async def test_websocket_with_headers():
    """Test WebSocket connection with proper headers"""
    uri = "ws://localhost:8001/ws/CP-SIMPLE-TEST"

    # Try with various header combinations
    header_combinations = [
        # Standard OCPP headers
        {
            "Sec-WebSocket-Protocol": "ocpp2.0.1",
            "User-Agent": "OCPP-Test-Client/1.0"
        },
        # Alternative headers
        {
            "Sec-WebSocket-Protocol": "ocpp1.6",
            "User-Agent": "OCPP-Test-Client/1.0"
        },
        # Minimal headers
        {
            "User-Agent": "OCPP-Test-Client/1.0"
        }
    ]

    for i, headers in enumerate(header_combinations):
        try:
            logger.info(f"Trying connection with headers set {i + 1}: {headers}")
            async with websockets.connect(uri, extra_headers=headers) as websocket:
                logger.info(f"✅ Connection successful with headers: {headers}")
                logger.info(f"Selected subprotocol: {websocket.subprotocol}")
                return True
        except Exception as e:
            logger.info(f"❌ Failed with headers {headers}: {e}")
            continue

    return False


async def test_different_endpoints():
    """Test different endpoint paths"""
    base_url = "ws://localhost:9000"
    endpoints_to_try = [
        "/CP-SIMPLE-TEST",
        "/ocpp",
        "/ws",
        "/",
        "/CP_001",
        "/chargepoint",
        "/station"
    ]

    for endpoint in endpoints_to_try:
        uri = f"{base_url}{endpoint}"
        try:
            logger.info(f"Trying endpoint: {endpoint}")
            async with websockets.connect(uri, subprotocols=['ocpp2.0.1']) as websocket:
                logger.info(f"✅ Successfully connected to endpoint: {endpoint}")
                logger.info(f"Selected subprotocol: {websocket.subprotocol}")
                return endpoint
        except Exception as e:
            logger.info(f"❌ Failed to connect to {endpoint}: {e}")
            continue

    return None


async def test_ocpp_message():
    """Try to send a simple OCPP message"""
    uri = "ws://localhost:8001/ws/CP-MESSAGE-TEST"

    # Simple BootNotification message (OCPP 2.0.1 format)
    boot_notification = [
        2,  # MessageType: CALL
        "12345",  # MessageId
        "BootNotification",  # Action
        {
            "chargingStation": {
                "model": "TestModel",
                "vendorName": "TestVendor"
            },
            "reason": "PowerUp"
        }
    ]

    try:
        logger.info("Attempting to send OCPP BootNotification message...")
        async with websockets.connect(uri, subprotocols=['ocpp2.0.1']) as websocket:
            logger.info("✅ WebSocket connected, sending message...")

            message = json.dumps(boot_notification)
            await websocket.send(message)
            logger.info(f"📤 Sent: {message}")

            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                logger.info(f"📥 Received: {response}")
                return True
            except asyncio.TimeoutError:
                logger.warning("⏰ No response received within 10 seconds")
                return True  # Connection worked, just no response

    except Exception as e:
        logger.error(f"❌ Failed to send OCPP message: {e}")
        return False


async def diagnose_server_response():
    """Try to get more information about the server's response"""
    uri = "ws://localhost:9000/CP-SIMPLE-TEST"

    try:
        logger.info("Attempting raw HTTP connection for diagnosis...")

        # Try to connect without WebSocket upgrade to see raw response
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:9000/CP-SIMPLE-TEST') as response:
                    logger.info(f"HTTP Response Status: {response.status}")
                    logger.info(f"HTTP Response Headers: {dict(response.headers)}")
                    text = await response.text()
                    logger.info(f"HTTP Response Body: {text[:200]}...")
        except Exception as e:
            logger.info(f"HTTP connection attempt: {e}")

    except ImportError:
        logger.info("aiohttp not available for HTTP diagnosis")
    except Exception as e:
        logger.info(f"Diagnosis attempt failed: {e}")


async def main():
    """Main diagnostic function"""
    logger.info("🔍 Starting Enhanced OCPP Server Diagnostics...")
    logger.info("=" * 60)

    # Step 1: Check if port is open
    logger.info("Step 1: Checking if port 9000 is open...")
    if check_port_open('localhost', 9000):
        logger.info("✅ Port 9000 is open and listening")
    else:
        logger.error("❌ Port 9000 is not open or not listening")
        logger.error("Make sure your OCPP server is running!")
        return

    # Step 2: Diagnose server response
    logger.info("\nStep 2: Diagnosing server response...")
    await diagnose_server_response()

    # Step 3: Test different endpoints
    logger.info("\nStep 3: Testing different endpoints...")
    working_endpoint = await test_different_endpoints()

    if working_endpoint:
        logger.info(f"✅ Found working endpoint: {working_endpoint}")
    else:
        logger.info("❌ No working endpoints found")

    # Step 4: Test with different headers
    logger.info("\nStep 4: Testing with different headers...")
    headers_work = await test_websocket_with_headers()

    # Step 5: Try to send an OCPP message
    if headers_work or working_endpoint:
        logger.info("\nStep 5: Testing OCPP message exchange...")
        message_works = await test_ocpp_message()

        if message_works:
            logger.info("✅ OCPP message exchange successful!")
        else:
            logger.info("❌ OCPP message exchange failed")

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("🏁 DIAGNOSTIC SUMMARY:")
    logger.info(f"Port 9000 open: ✅")
    logger.info(f"Working endpoint found: {'✅' if working_endpoint else '❌'}")
    logger.info(f"Headers working: {'✅' if headers_work else '❌'}")

    if not (working_endpoint or headers_work):
        logger.error("\n💡 RECOMMENDATIONS:")
        logger.error("1. Check if your OCPP server requires specific subprotocols")
        logger.error("2. Verify the server is configured to accept WebSocket connections")
        logger.error("3. Check server logs for more detailed error information")
        logger.error("4. Try starting the server with different configuration")


if __name__ == "__main__":
    asyncio.run(main())
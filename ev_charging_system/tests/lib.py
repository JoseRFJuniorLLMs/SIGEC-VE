#!/usr/bin/env python3
"""
OCPP Library Diagnostic Script
Quick check to diagnose OCPP library issues
"""

import sys
import subprocess


def check_ocpp_installation():
    """Check OCPP library installation and structure"""
    print("🔍 OCPP Library Diagnostic")
    print("=" * 40)

    # 1. Check if OCPP is installed
    try:
        import ocpp
        print(f"✅ OCPP library installed")
        print(f"📍 Version: {getattr(ocpp, '__version__', 'Unknown')}")
        print(f"📁 Location: {ocpp.__file__}")
    except ImportError:
        print("❌ OCPP library not installed")
        print("💡 Install with: pip install ocpp")
        return False

    # 2. Check available versions
    versions_available = []
    for version in ['v16', 'v201']:
        try:
            exec(f"import ocpp.{version}")
            versions_available.append(version)
            print(f"✅ OCPP {version} available")
        except ImportError:
            print(f"❌ OCPP {version} not available")

    if not versions_available:
        print("❌ No OCPP versions available")
        return False

    # 3. Check specific modules for each version
    for version in versions_available:
        print(f"\n📋 Checking OCPP {version} modules:")

        modules_to_check = ['call', 'call_result', 'enums', 'datatypes']
        for module in modules_to_check:
            try:
                exec(f"import ocpp.{version}.{module}")
                print(f"  ✅ {module}")
            except ImportError as e:
                print(f"  ❌ {module}: {e}")

        # Check for BootNotification specifically
        try:
            if version == 'v16':
                from ocpp.v16.call import BootNotification
                print(f"  ✅ BootNotification found in {version}.call")
            elif version == 'v201':
                try:
                    from ocpp.v201.call import BootNotification
                    print(f"  ✅ BootNotification found in {version}.call")
                except ImportError:
                    # Try alternative locations
                    try:
                        import ocpp.v201 as v201_module
                        if hasattr(v201_module, 'BootNotification'):
                            print(f"  ✅ BootNotification found in {version} root")
                        else:
                            print(f"  ❌ BootNotification not found in {version}")
                    except:
                        print(f"  ❌ BootNotification not accessible in {version}")
        except ImportError as e:
            print(f"  ❌ BootNotification: {e}")

    # 4. Show pip list for OCPP-related packages
    print(f"\n📦 Installed OCPP-related packages:")
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'],
                                capture_output=True, text=True)
        lines = result.stdout.split('\n')
        ocpp_packages = [line for line in lines if 'ocpp' in line.lower()]

        if ocpp_packages:
            for package in ocpp_packages:
                print(f"  📦 {package}")
        else:
            print("  ❌ No OCPP packages found in pip list")
    except Exception as e:
        print(f"  ❌ Could not check pip packages: {e}")

    return True


def provide_solutions():
    """Provide solutions based on diagnostic results"""
    print(f"\n🔧 RECOMMENDED SOLUTIONS")
    print("=" * 40)

    print("1. 📥 Update OCPP library:")
    print("   pip install --upgrade ocpp")
    print()
    print("2. 🔄 Reinstall OCPP library:")
    print("   pip uninstall ocpp")
    print("   pip install ocpp")
    print()
    print("3. 📚 Check library documentation:")
    print("   https://github.com/mobilityhouse/ocpp")
    print()
    print("4. 🐍 Check Python version compatibility:")
    print(f"   Current Python: {sys.version}")
    print("   OCPP library requires Python 3.7+")
    print()
    print("5. 🔍 Alternative import patterns to try:")
    print("   # For OCPP 1.6:")
    print("   from ocpp.v16.call import BootNotification")
    print("   ")
    print("   # For OCPP 2.0.1 (try these alternatives):")
    print("   from ocpp.v201.call import BootNotification")
    print("   # OR")
    print("   import ocpp.v201 as ocpp201")
    print("   # OR")
    print("   from ocpp.messages.v201 import BootNotification")


def test_basic_functionality():
    """Test basic OCPP functionality"""
    print(f"\n🧪 BASIC FUNCTIONALITY TEST")
    print("=" * 40)

    try:
        # Try to create a basic ChargePoint
        from ocpp.v16 import ChargePoint
        print("✅ Can import ChargePoint from v16")

        # Try to import basic enums
        from ocpp.v16 import enums
        print("✅ Can import enums from v16")

        print("🎯 OCPP 1.6 seems to be working correctly")
        return True

    except ImportError as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


if __name__ == "__main__":
    print("🩺 OCPP Library Health Check")
    print("=" * 50)

    if check_ocpp_installation():
        test_basic_functionality()
        provide_solutions()
    else:
        print("\n❌ OCPP library installation issues detected")
        provide_solutions()

    print(f"\n✅ Diagnostic complete!")
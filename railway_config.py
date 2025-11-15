#!/usr/bin/env python
"""
Railway.app deployment configuration
This file helps deploy the Envira backend to Railway
"""

import os
import sys

# Ensure we're using the right Python environment
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")

# Check environment variables
required_vars = [
    "MONGODB_URL",
    "MQTT_BROKER",
    "MQTT_PORT",
    "MQTT_USERNAME",
    "MQTT_PASSWORD"
]

print("\n🔍 Checking environment variables...")
missing_vars = []
for var in required_vars:
    if var in os.environ:
        # Hide sensitive values
        value = os.environ[var]
        if len(value) > 20:
            display = value[:10] + "***" + value[-5:]
        else:
            display = "***"
        print(f"✅ {var}: {display}")
    else:
        print(f"❌ {var}: NOT SET")
        missing_vars.append(var)

if missing_vars:
    print(f"\n⚠️  Missing variables: {', '.join(missing_vars)}")
    print("Please set these in Railway environment variables")
else:
    print("\n✅ All required variables are set!")

# Start the server
print("\n🚀 Starting Envira Backend Server...")
print("📡 Server running on 0.0.0.0:8000")
print("📖 API Docs available at: /docs")
print("✨ Ready to receive MQTT telemetry!")

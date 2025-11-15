import os

MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb+srv://farahhammami8_db_user:2003@envira-cluster.fuobdmy.mongodb.net/envira"
)
MQTT_BROKER = os.getenv("MQTT_BROKER", "y2b6df88.ala.eu-central-1.emqxsl.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "farah")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "2003")

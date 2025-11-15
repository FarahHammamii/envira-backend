# 🌿 Envira - IoT Environmental Quality Monitoring System

A comprehensive backend system for monitoring and improving indoor environmental quality using IoT sensors and intelligent recommendations.

## Architecture

ESP32 Sensors → MQTT Broker (EMQX) → FastAPI Backend → MongoDB → Mobile App

## Features

- **Real-time MQTT Integration**: Connects to EMQX cloud broker
- **RESTful API**: FastAPI with automatic documentation
- **WebSocket Support**: Real-time updates for mobile apps
- **MongoDB Storage**: Time-series and metadata storage
- **IEQ Scoring**: Calculates Indoor Environmental Quality scores
- **CORS Enabled**: Cross-origin requests for mobile apps

## Tech Stack

- **Framework**: FastAPI + Uvicorn
- **Database**: MongoDB Atlas
- **Message Broker**: EMQX Cloud
- **Deployment**: Railway
- **Authentication**: JWT (Ready for implementation)

## Installation

### Prerequisites

- Python 3.9+
- MongoDB Atlas account
- EMQX Cloud account

### Local Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/envira-backend.git
   cd envira-backend
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**
   Create `.env` file:

   ```env
   MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/envira
   MQTT_BROKER=your-broker.emqx.io
   MQTT_PORT=8883
   MQTT_USERNAME=your-username
   MQTT_PASSWORD=your-password
   ```

4. **Run the server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### Health & Info

- `GET /` - API information
- `GET /health` - Health check
- `GET /debug` - Debug information

### Sensor Data

- `GET /telemetry/{device_id}` - Historical data
- `GET /latest/{device_id}` - Latest reading
- `GET /stats/{device_id}` - Statistics

### Real-time

- `WebSocket /ws` - Real-time updates

## 📊 Data Model

**Telemetry Document**

```json
{
  "device_id": "esp32-001",
  "site_id": "home",
  "ts": 4225,
  "sensors": {
    "mq135": 785,
    "dht": { "t": 24.4, "h": 63.4 },
    "ldr": 1114,
    "sound_rms": 1056.826
  },
  "ieq_score": 72.5,
  "processed_at": "2024-01-01T10:00:00Z"
}
```

## Deployment

### Railway

1. Connect GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Automatic deployments on `git push`

**Environment Variables for Production**

```env
MONGODB_URL=your-production-mongodb-url
MQTT_BROKER=your-production-mqtt-broker
MQTT_PORT=8883
MQTT_USERNAME=your-production-username
MQTT_PASSWORD=your-production-password
```

## ESP32 Integration

ESP32 should publish to topic: `envira/{site_id}/{device_id}/telemetry`

**Example payload:**

```json
{
  "device_id": "esp32-001",
  "site_id": "home",
  "ts": 4225,
  "sensors": {
    "mq135": 785,
    "dht": { "t": 24.4, "h": 63.4 },
    "ldr": 1114,
    "sound_rms": 1056.826
  }
}
```

## 📈 IEQ Scoring

The backend calculates Indoor Environmental Quality score using:

- Air Quality (40%) - MQ135 sensor
- Thermal Comfort (30%) - DHT22 temperature
- Light Quality (20%) - LDR sensor
- Acoustic Comfort (10%) - Sound sensor

## Troubleshooting

### Common Issues

- **MQTT Connection Failed**: Check EMQX credentials and TLS configuration
- **MongoDB Connection**: Verify connection string and IP whitelist
- **No Data Received**: Check ESP32 is publishing to correct topic

### Logs

Check Railway logs for detailed error messages and connection status.

# ----------------------------------------------------------------
# file: vrpc.py
# Virtual device for testing thingsboard rule chain 'n' stuff.
# Humiditron & Gemini - 2026
# ----------------------------------------------------------------
import json
import random
import time
import uuid
from datetime import datetime
import paho.mqtt.client as mqtt

# Configuration
THINGSBOARD_HOST = "humid1.com"
PROVISION_KEY = "joz5hqceqbkzzft3qzaf"
PROVISION_SECRET = "d9xpuylns0pdlk2w70hc"

DEVICE_NAME = f"Test-Sensor-{uuid.uuid4().hex[:6]}"
SECRET_KEY = "mySecret123"

assigned_token = None
sleep_time = 10

# --- PHASE 1: Auto-Provisioning ---
def on_connect_prov(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe("/provision/response")
        payload = {
            "deviceName": DEVICE_NAME,
            "provisionDeviceKey": PROVISION_KEY,
            "provisionDeviceSecret": PROVISION_SECRET
        }
        client.publish("/provision/request", json.dumps(payload), 1)
        print(f"[1/3] Requesting auto-provisioning for: {DEVICE_NAME}")

def on_message_prov(client, userdata, msg):
    global assigned_token
    data = json.loads(msg.payload.decode())
    if data.get("status") == "SUCCESS":
        assigned_token = data.get("credentialsValue")
        print(f"[2/3] Provisioned successfully! Token received.")
    client.disconnect()

prov_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
prov_client.username_pw_set("provision")
prov_client.tls_set()
prov_client.on_connect = on_connect_prov
prov_client.on_message = on_message_prov
prov_client.connect(THINGSBOARD_HOST, 8883, 60)
prov_client.loop_start()

while not assigned_token:
    time.sleep(0.5)
prov_client.loop_stop()

# --- PHASE 2: Device Connection, Claiming, & Telemetry ---
def on_connect_device(client, userdata, flags, rc):
    if rc == 0:
        print(f"[3/3] Connected as '{DEVICE_NAME}'.")
        
        # Subscribe to shared attribute updates on the correct ThingsBoard topic
        client.subscribe("v1/devices/me/attributes")
        client.subscribe("v1/devices/me/attributes/response/+")
        client.subscribe("v1/devices/me/rpc/request/+")
        
        # Request existing shared attributes on startup
        req_payload = {"sharedKeys": "sleep_interval_sec,device_theme,sound_enabled,auto_update_enabled,manual_ota_trigger"}
        client.publish("v1/devices/me/attributes/request/1", json.dumps(req_payload), 1)
        print("Requested existing shared attributes from server...")
        
        # Send Claim Request
        claim_payload = {"secretKey": SECRET_KEY, "durationMs": 180000}
        client.publish("v1/devices/me/claim", json.dumps(claim_payload), 1)
        
        # Request Unix Epoch over RPC (hopfully NTP Epoch is not needed)
        # Topic format: v1/devices/me/rpc/request/{requestId}
        request_id = "1"
        payload = {"method": "getCurrentTime", "params": {}}
        device_client.publish(f"v1/devices/me/rpc/request/{request_id}", json.dumps(payload), 1)
        print(f"Published RPC Request: {payload}")
        
        # Publish Client Attributes
        client_attributes = {
            "fw_version": "v1.0.4",
            "device_name": DEVICE_NAME,
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "ssid": "Home-Network-5G",
            "ip_address": "192.168.1.150",
            "has_sd_card": True,
            "audio_synced": True
        }
        client.publish("v1/devices/me/attributes", json.dumps(client_attributes), 1)
        print(f"Published client attributes: {client_attributes}")
        
        print(f"\n >>> READY TO CLAIM IN UI! <<<")
        print(f" Name: {DEVICE_NAME}")
        print(f" Secret: {SECRET_KEY}\n")

# --- PHASE 3: Message Handling & Event Routing ---
# --- PHASE 3: Message Handling & Event Routing ---
def on_message_device(client, userdata, msg):
    global sleep_time  # Bind to global sleep_time
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
        
        # Handle live shared attribute updates
        if topic == "v1/devices/me/attributes":
            print(f"\n[Shared Attribute Updated Live]: {payload}")
            if "sleep_interval_sec" in payload:
                sleep_time = int(payload['sleep_interval_sec'])
                print(f"-> New sleep interval applied: {sleep_time}s")
            if "sound_enabled" in payload:
                print(f"-> Sound state updated: {payload['sound_enabled']}")
            if "manual_ota_trigger" in payload and payload["manual_ota_trigger"]:
                print("-> Manual OTA update triggered by dashboard!")
                
        # Handle initial response when requesting existing attributes
        elif topic.startswith("v1/devices/me/attributes/response/"):
            shared_values = payload.get("shared", {})
            if "sleep_interval_sec" in shared_values:
                sleep_time = int(shared_values['sleep_interval_sec'])
                print(f"-> Startup sleep_time set to: {sleep_time}s")
            print(f"\n[Initial Shared Attributes Loaded]: {shared_values}")
            
        # Handle incoming RPC commands
        elif topic.startswith("v1/devices/me/rpc/request/"):
            request_id = topic.split("/")[-1]
            method = payload.get("method")
            params = payload.get("params")
            
            print(f"\n[RPC Command Received] Method: '{method}' | Params: {params}")
            
            if method == "setStatus":
                new_status = params.get("status")
                print(f"-> Device state successfully changed to: {new_status}")
                response_data = {"status": "success", "currentState": new_status}
            elif method == "getCurrentTime":
                new_time = params.get("epoch_ms")                
                dt = datetime.fromtimestamp(new_time / 1000.0)                
                standard_time = dt.strftime("%Y-%m-%d %I:%M:%S %p")                
                print(f"-> Time successfully sync-ed to: {new_time} | {standard_time}")
                response_data = {"epoch_ms": new_time}
            else:
                response_data = {"status": "error", "message": "Unknown method"}

            response_topic = f"v1/devices/me/rpc/response/{request_id}"
            client.publish(response_topic, json.dumps(response_data), 1)
            print("[RPC Response Sent Back]\n")
            
    except Exception as e:
        print(f"Failed to process message: {e}")

device_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
device_client.username_pw_set(assigned_token)
device_client.tls_set()
device_client.on_connect = on_connect_device
device_client.on_message = on_message_device

device_client.connect(THINGSBOARD_HOST, 8883, 60)
device_client.loop_start()

try:
    while True:
        telemetry = {
            # Normal Mode Boundaries
            "rh": round(random.uniform(66.0, 72.0), 2),
            "temp": round(random.uniform(65.0, 71.0), 2),
            "battery": random.randint(26, 100),
            "rssi": random.randint(-65, -40)
        }
        device_client.publish("v1/devices/me/telemetry", json.dumps(telemetry), 1)
        print(f"Published telemetry (Next in {sleep_time}s): {telemetry}")
        
        # Responsive 1-second check loop
        elapsed = 0
        while elapsed < sleep_time:
            time.sleep(1)
            elapsed += 1

except KeyboardInterrupt:
    device_client.loop_stop()
    device_client.disconnect()
    print("Simulator stopped.")
#include <ESP8266WiFi.h>
#include <WebSocketsServer.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>
#include <HX711.h>

// WiFi credentials
const char* ssid = "OMKAR";
const char* password = "87654321";

// WebSocket server settings
const int wsPort = 81;

// RFID pins
#define RST_PIN 3
#define SS_PIN  4

// Load cell pins - using GPIO numbers for ESP8266
#define LOADCELL_DOUT_PIN 16  // GPIO16 (D0)
#define LOADCELL_SCK_PIN 15   // GPIO15 (D8)

MFRC522 rfid(SS_PIN, RST_PIN);
WebSocketsServer webSocket = WebSocketsServer(wsPort);
HX711 scale;

// Updated calibration factor based  on actual readings
float calibration_factor = 513.0;  // New calibration factor

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("Client disconnected");
            break;
        case WStype_CONNECTED:
            Serial.println("Client connected");
            break;
        case WStype_TEXT:
            break;
    }
}

void setup() {
    Serial.begin(115200);
    Serial.setDebugOutput(false);
    
    // Initialize RFID
    SPI.begin();
    rfid.PCD_Init();
    Serial.println("RFID Ready");
    
    // Initialize load cell
    Serial.println("Initializing HX711...");
    scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
    
    if (scale.wait_ready_timeout(1000)) {
        Serial.println("HX711 found!");
    } else {
        Serial.println("HX711 not found!");
        while (1) {
            delay(1000);
        }
    }
    
    // Reset the scale to 0
    Serial.println("Taring...");
    scale.set_scale(calibration_factor);
    scale.tare();  // Reset the scale to 0
    Serial.println("Scale tared. Ready for weight!");
    
    // Connect to WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi OK");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    
    // Start WebSocket server
    webSocket.begin();
    webSocket.onEvent(webSocketEvent);
    Serial.println("WebSocket server started");
}

void loop() {
    webSocket.loop();
    
    // Read weight every second
    static unsigned long lastWeightTime = 0;
    if (millis() - lastWeightTime >= 1000) {
        // Get multiple readings for stability
        float weight = scale.get_units(5);  // Average of 5 readings
        
        // Convert negative weight to positive
        weight = abs(weight);
        
        // Ensure small values are treated as zero
        if (weight < 0.1) {
            weight = 0;
        }
        
        // Print debug info
        Serial.print("Weight: ");
        Serial.print(weight);
        Serial.println(" grams");
        
        // Create JSON message for weight
        StaticJsonDocument<200> weightDoc;
        weightDoc["type"] = "weight";
        weightDoc["weight"] = weight;
        
        String weightJson;
        serializeJson(weightDoc, weightJson);
        webSocket.broadcastTXT(weightJson);
        
        lastWeightTime = millis();
        
        // Interactive calibration commands
        if (Serial.available()) {
            char temp = Serial.read();
            if (temp == '+' || temp == 'a')
                calibration_factor += 10;
            else if (temp == '-' || temp == 'z')
                calibration_factor -= 10;
            else if (temp == 't')
                scale.tare();
            
            scale.set_scale(calibration_factor);
            Serial.print("Calibration factor: ");
            Serial.println(calibration_factor);
        }
    }
    
    // Handle RFID scanning
    if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
        delay(100);
        return;
    }
    
    // Read card ID
    String cardID = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
        cardID += (rfid.uid.uidByte[i] < 0x10 ? "0" : "");
        cardID += String(rfid.uid.uidByte[i], HEX);
    }
    
    Serial.println(cardID);
    
    // Create JSON message for RFID
    StaticJsonDocument<200> rfidDoc;
    rfidDoc["type"] = "rfid";
    rfidDoc["card_id"] = cardID;
    
    String rfidJson;
    serializeJson(rfidDoc, rfidJson);
    
    // Broadcast to all connected clients
    webSocket.broadcastTXT(rfidJson);
    
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    delay(1000);
} 
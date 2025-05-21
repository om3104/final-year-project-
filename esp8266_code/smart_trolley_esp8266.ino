#include <ESP8266WiFi.h>
#include <WebSocketsServer.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "OMKAR";
const char* password = "87654321";

// WebSocket server settings
const int wsPort = 81;

// RFID pins
#define RST_PIN 3
#define SS_PIN  4

MFRC522 rfid(SS_PIN, RST_PIN);
WebSocketsServer webSocket = WebSocketsServer(wsPort);

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("Client disconnected");
            break;
        case WStype_CONNECTED:
            Serial.println("Client connected");
            break;
        case WStype_TEXT:
            // Handle any messages from client if needed
            break;
    }
}

void setup() {
    Serial.begin(115200);
    
    // Initialize RFID
    SPI.begin();
    rfid.PCD_Init();
    Serial.println("RFID Ready");
    
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
    
    // Create JSON message
    StaticJsonDocument<200> doc;
    doc["card_id"] = cardID;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    // Broadcast to all connected clients
    webSocket.broadcastTXT(jsonString);
    
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    delay(1000);
} 
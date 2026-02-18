/**
 * I2C Scanner - Debug Tool
 * Upload this to Arduino A to check if Arduino B is visible on I2C bus
 * 
 * This will scan all I2C addresses and report which devices are found.
 * Arduino B should appear at address 0x08 (decimal 8)
 */

#include <Wire.h>

void setup() {
  Wire.begin();
  Serial.begin(9600);
  while (!Serial);
  Serial.println("\n=== I2C Scanner ===");
}

void loop() {
  byte error, address;
  int nDevices;
  
  Serial.println("Scanning I2C bus...");
  
  nDevices = 0;
  for(address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("Device found at 0x");
      if (address < 16) Serial.print("0");
      Serial.print(address, HEX);
      Serial.print(" (decimal ");
      Serial.print(address);
      Serial.println(")");
      
      if (address == 0x08) {
        Serial.println("  ^-- This is Arduino B!");
      }
      
      nDevices++;
    }
    else if (error == 4) {
      Serial.print("Unknown error at 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
    }
  }
  
  if (nDevices == 0) {
    Serial.println("ERROR: No I2C devices found!");
    Serial.println("\nCheck:");
    Serial.println("1. Arduino B is powered");
    Serial.println("2. I2C wiring (A4-A4, A5-A5, GND-GND)");
    Serial.println("3. Arduino B has slave sketch uploaded");
  }
  else {
    Serial.print("\nTotal devices found: ");
    Serial.println(nDevices);
  }
  
  Serial.println("\n--- Scan complete. Waiting 5s before next scan ---\n");
  delay(5000);
}

/**
 * Arduino A - I2C Master Bridge (No Local Sensors)
 * Requests data from Arduino B sensors via I2C and outputs via Serial
 * Outputs CSV: Seconds,CO2_PPM_B1,CO2_PPM_B2,CO2_PPM_B3
 *
 * Protocol: Sends sensor number (1-3) to slave, receives float PPM value
 *
 * Board: Arduino UNO (primary - connected to PC via USB)
 * I2C: Master, communicates with slave at 0x08
 * Note: This Arduino only acts as a bridge - all sensors are on Arduino B
 * Author: Kurayi Chawatama
 */

#include <Wire.h>
#include <MQUnifiedsensor.h>

#define Board "Arduino UNO"
#define Pin A0
#define Type "MQ-135"
#define Voltage_Resolution 5
#define ADC_Bit_Resolution 10
#define RatioMQ135CleanAir 3.6
#define I2C_SLAVE_ADDRESS 0x08
#define NUM_SLAVE_SENSORS 3  // Number of sensors on Arduino B

// Function to request a specific sensor reading from slave
float requestSensorReading(byte sensor_number) {
  float ppm_value = 0.0;
  
  // Send sensor selection command
  Wire.beginTransmission(I2C_SLAVE_ADDRESS);
  Wire.write(sensor_number);
  Wire.endTransmission();
  
  // Small delay to let slave process
  delay(10);
  
  // Request the data
  Wire.requestFrom(I2C_SLAVE_ADDRESS, sizeof(float));
  
  if (Wire.available() >= sizeof(float)) {
    byte ppm_bytes[sizeof(float)];
    for (int i = 0; i < sizeof(float); i++) {
      ppm_bytes[i] = Wire.read();
    }
    memcpy(&ppm_value, ppm_bytes, sizeof(float));
  }
  
  return ppm_value;
}

void setup() {
  Serial.begin(9600);
  Wire.begin();  // Join I2C bus as master
  
  // Print CSV header (only Arduino B sensors)
  Serial.print("Seconds");
  for (int i = 1; i <= NUM_SLAVE_SENSORS; i++) {
    Serial.print(",CO2_PPM_B");
    Serial.print(i);
  }
  Serial.println();
}

void loop() {
  static unsigned long seconds = 0;
  
  // Output timestamp
  Serial.print(seconds);
  
  // Request data from each sensor on Arduino B
  for (int sensor = 1; sensor <= NUM_SLAVE_SENSORS; sensor++) {
    float co2_ppm_b = requestSensorReading(sensor);
    Serial.print(",");
    Serial.print(co2_ppm_b);
  }
  Serial.println();
  
  seconds += 2;
  delay(2000);
}

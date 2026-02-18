/**
 * Arduino B - I2C Slave with Multiple MQ-135 Sensors
 * Receives command to select sensor, responds with CO2 PPM reading
 *
 * Protocol:
 *   Master sends: 1 byte (sensor number: 1, 2, 3, etc.)
 *   Slave responds: 4 bytes (float CO2 PPM)
 *
 * Sensors: MQ-135 on A0, A1, A2 (add more as needed)
 * Board: Arduino UNO (secondary)
 * I2C Address: 0x08
 * Author: Kurayi Chawatama
 */

#include <Wire.h>
#include <MQUnifiedsensor.h>

#define Board "Arduino UNO"
#define Type "MQ-135"
#define Voltage_Resolution 5
#define ADC_Bit_Resolution 10
#define RatioMQ135CleanAir 3.6
#define I2C_SLAVE_ADDRESS 0x08
#define NUM_SENSORS 1  // Change this to match your number of sensors

// Create sensor objects for each MQ-135
MQUnifiedsensor MQ135_1(Board, Voltage_Resolution, ADC_Bit_Resolution, A0, Type);
// Uncomment additional sensors as needed:
// MQUnifiedsensor MQ135_2(Board, Voltage_Resolution, ADC_Bit_Resolution, A1, Type);
// MQUnifiedsensor MQ135_3(Board, Voltage_Resolution, ADC_Bit_Resolution, A2, Type);
// MQUnifiedsensor MQ135_4(Board, Voltage_Resolution, ADC_Bit_Resolution, A3, Type);

float co2_readings[NUM_SENSORS];
byte requested_sensor = 1;  // Default to sensor 1

void setup() {
  Wire.begin(I2C_SLAVE_ADDRESS);  // Join I2C bus as slave
  Wire.onReceive(receiveEvent);   // Register receive handler
  Wire.onRequest(requestEvent);    // Register request handler
  
  // Initialize and calibrate all sensors
  initializeSensor(MQ135_1, 0);
  // Uncomment additional sensors as needed:
  // initializeSensor(MQ135_2, 1);
  // initializeSensor(MQ135_3, 2);
  // initializeSensor(MQ135_4, 3);
}

void initializeSensor(MQUnifiedsensor &sensor, int index) {
  sensor.setRegressionMethod(1);
  sensor.setA(110.47);
  sensor.setB(-2.862);
  sensor.init();
  
  // Calibrate and calculate R0
  float calcR0 = 0;
  for (int i = 0; i < 10; i++) {
    sensor.update();
    calcR0 += sensor.calibrate(RatioMQ135CleanAir);
  }
  sensor.setR0(calcR0 / 10);
}

void loop() {
  // Update all sensor readings
  MQ135_1.update();
  co2_readings[0] = MQ135_1.readSensor();
  
  // Uncomment additional sensors as needed:
  // MQ135_2.update();
  // co2_readings[1] = MQ135_2.readSensor();
  
  // MQ135_3.update();
  // co2_readings[2] = MQ135_3.readSensor();
  
  // MQ135_4.update();
  // co2_readings[3] = MQ135_4.readSensor();
  
  delay(100);  // Update readings every 100ms
}

void receiveEvent(int bytes) {
  // Receive sensor selection command from master
  if (Wire.available()) {
    requested_sensor = Wire.read();
  }
}

void requestEvent() {
  // Send the requested sensor's CO2 PPM value
  float ppm_value = 0.0;
  
  if (requested_sensor >= 1 && requested_sensor <= NUM_SENSORS) {
    ppm_value = co2_readings[requested_sensor - 1];
  }
  
  byte* ppm_bytes = (byte*)&ppm_value;
  Wire.write(ppm_bytes, sizeof(float));
}

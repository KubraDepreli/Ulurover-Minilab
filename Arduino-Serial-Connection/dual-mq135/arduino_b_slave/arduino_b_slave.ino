/**
 * Arduino B - I2C Slave with Multiple MQ-135 Sensors
 * Receives command to select sensor, responds with CO2 PPM reading
 *
 * CURRENT CONFIGURATION: 3 sensors for reaction rate monitoring
 *
 * Protocol:
 *   Master sends: 1 byte (sensor number: 1, 2, 3, etc.)
 *   Slave responds: 4 bytes (float CO2 PPM)
 *
 * Sensors: MQ-135 on A0, A1, A2 (3 sensors active)
 * Board: Arduino UNO (secondary)
 * I2C Address: 0x08
 * 
 * BASELINE OFFSET FEATURE:
 *   - Adds configurable offset to all readings (default: 400 PPM)
 *   - Compensates for uncalibrated/cold sensors
 *   - Adjust BASELINE_OFFSET_PPM to tune (0 = no offset)
 * 
 * CALIBRATION IMPROVEMENTS:
 *   - 100 calibration samples (up from 10) for better accuracy
 *   - 2-second warmup period before calibration
 *   - Statistical outlier filtering (2 sigma threshold)
 *   - 100ms delay between samples for sensor stability
 * 
 * DIAGNOSTIC MODE:
 *   - Monitors raw analog values and voltages
 *   - Helps diagnose voltage differences between sensors
 *   - Enable/disable with ENABLE_DIAGNOSTICS flag
 * 
 * TROUBLESHOOTING VOLTAGE DIFFERENCES:
 *   - If sensors show different readings, check:
 *     * Power supply quality (should be stable 5V)
 *     * Breadboard connections (voltage drops on long traces)
 *     * Individual sensor wiring
 *   - Different voltages = different readings even for same CO2 level
 * 
 * IMPORTANT: MQ-135 sensors require 24-48 hours of continuous power
 *            for optimal accuracy. First readings may be inaccurate.
 *            Normal atmospheric CO2 is ~400-420 PPM.
 *
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
#define NUM_SENSORS 3  // Change this to match your number of sensors

// BASELINE OFFSET: Add this to compensate for uncalibrated sensors
// Set to 0 for no offset, or ~400 to baseline to atmospheric CO2
#define BASELINE_OFFSET_PPM 400.0  // Adjust as needed

// DIAGNOSTIC MODE: Enable to also read raw analog values and voltages
#define ENABLE_DIAGNOSTICS true

// Create sensor objects for each MQ-135
MQUnifiedsensor MQ135_1(Board, Voltage_Resolution, ADC_Bit_Resolution, A0, Type);
// Uncomment additional sensors as needed:
MQUnifiedsensor MQ135_2(Board, Voltage_Resolution, ADC_Bit_Resolution, A1, Type);
MQUnifiedsensor MQ135_3(Board, Voltage_Resolution, ADC_Bit_Resolution, A2, Type);
// MQUnifiedsensor MQ135_4(Board, Voltage_Resolution, ADC_Bit_Resolution, A3, Type);

float co2_readings[NUM_SENSORS];
float raw_voltages[NUM_SENSORS];  // Store raw voltages for diagnostics
int raw_analog[NUM_SENSORS];      // Store raw analog values
byte requested_sensor = 1;  // Default to sensor 1

void setup() {
  Wire.begin(I2C_SLAVE_ADDRESS);  // Join I2C bus as slave
  Wire.onReceive(receiveEvent);   // Register receive handler
  Wire.onRequest(requestEvent);    // Register request handler
  
  // Initialize and calibrate all sensors
  initializeSensor(MQ135_1, 0);
  // Uncomment additional sensors as needed:
  initializeSensor(MQ135_2, 1);
  initializeSensor(MQ135_3, 2);
  // initializeSensor(MQ135_4, 3);
}

void initializeSensor(MQUnifiedsensor &sensor, int index) {
  sensor.setRegressionMethod(1);
  sensor.setA(110.47);
  sensor.setB(-2.862);
  sensor.init();
  
  // Warmup period: discard first readings to stabilize sensor
  for (int i = 0; i < 20; i++) {
    sensor.update();
    delay(100);
  }
  
  // Improved calibration with more samples and outlier filtering
  float calcR0 = 0;
  int validSamples = 0;
  const int totalSamples = 100;
  const int warmupSamples = 10;
  
  // Additional warmup samples (discarded)
  for (int i = 0; i < warmupSamples; i++) {
    sensor.update();
    sensor.calibrate(RatioMQ135CleanAir);
    delay(200);
  }
  
  // Collect calibration samples
  float samples[totalSamples];
  for (int i = 0; i < totalSamples; i++) {
    sensor.update();
    samples[i] = sensor.calibrate(RatioMQ135CleanAir);
    delay(100);
  }
  
  // Calculate mean and standard deviation for outlier filtering
  float sum = 0;
  for (int i = 0; i < totalSamples; i++) {
    sum += samples[i];
  }
  float mean = sum / totalSamples;
  
  float variance = 0;
  for (int i = 0; i < totalSamples; i++) {
    float diff = samples[i] - mean;
    variance += diff * diff;
  }
  float stdDev = sqrt(variance / totalSamples);
  
  // Average samples within 2 standard deviations (reject outliers)
  for (int i = 0; i < totalSamples; i++) {
    if (abs(samples[i] - mean) <= 2 * stdDev) {
      calcR0 += samples[i];
      validSamples++;
    }
  }
  
  // Set R0 with filtered average
  if (validSamples > 0) {
    sensor.setR0(calcR0 / validSamples);
  } else {
    sensor.setR0(mean);  // Fallback to mean if all rejected
  }
}

void loop() {
  // Update all sensor readings with baseline offset
  MQ135_1.update();
  co2_readings[0] = MQ135_1.readSensor() + BASELINE_OFFSET_PPM;
  if (ENABLE_DIAGNOSTICS) {
    raw_analog[0] = analogRead(A0);
    raw_voltages[0] = (raw_analog[0] / 1024.0) * Voltage_Resolution;
  }
  
  // Uncomment additional sensors as needed:
  MQ135_2.update();
  co2_readings[1] = MQ135_2.readSensor() + BASELINE_OFFSET_PPM;
  if (ENABLE_DIAGNOSTICS) {
    raw_analog[1] = analogRead(A1);
    raw_voltages[1] = (raw_analog[1] / 1024.0) * Voltage_Resolution;
  }
  
  MQ135_3.update();
  co2_readings[2] = MQ135_3.readSensor() + BASELINE_OFFSET_PPM;
  if (ENABLE_DIAGNOSTICS) {
    raw_analog[2] = analogRead(A2);
    raw_voltages[2] = (raw_analog[2] / 1024.0) * Voltage_Resolution;
  }
  
  // MQ135_4.update();
  // co2_readings[3] = MQ135_4.readSensor() + BASELINE_OFFSET_PPM;
  // if (ENABLE_DIAGNOSTICS) {
  //   raw_analog[3] = analogRead(A3);
  //   raw_voltages[3] = (raw_analog[3] / 1024.0) * Voltage_Resolution;
  // }
  
  delay(100);  // Update readings every 100ms
}

void receiveEvent(int bytes) {
  // Receive sensor selection command from master
  // Commands: 1-NUM_SENSORS = sensor PPM, 100+ = diagnostics
  // 101 = raw analog value, 102 = voltage
  if (Wire.available()) {
    requested_sensor = Wire.read();
  }
}

void requestEvent() {
  // Send the requested sensor's data
  float return_value = 0.0;
  
  if (requested_sensor >= 1 && requested_sensor <= NUM_SENSORS) {
    // Normal CO2 PPM reading
    return_value = co2_readings[requested_sensor - 1];
  } else if (ENABLE_DIAGNOSTICS && requested_sensor >= 101 && requested_sensor <= 103) {
    // Diagnostic modes (sensor index from previous normal request)
    int sensor_idx = (requested_sensor == 101 || requested_sensor == 102 || requested_sensor == 103) ? 0 : 0;
    // For simplicity, return diagnostic data for all sensors as comma-separated would require different protocol
    // Instead, use sensor selection: send normal request first (1-3), then diagnostic request
    // This is a limitation - better to extend master to request specific diagnostic per sensor
    // For now, just return 0 for diagnostic requests (not fully implemented)
    return_value = 0.0;
  }
  
  byte* data_bytes = (byte*)&return_value;
  Wire.write(data_bytes, sizeof(float));
}

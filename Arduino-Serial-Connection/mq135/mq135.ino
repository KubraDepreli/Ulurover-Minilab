/**
 * MQ-135 CO2 Monitoring with MQUnifiedsensor
 * Outputs CSV: Seconds,CO2_PPM
 *
 * Sensor: MQ-135
 * Board: Arduino UNO
 * Author: Kurayi Chawatama (adapted)
 */

#include <MQUnifiedsensor.h>

#define Board "Arduino UNO"
#define Pin A0
#define Type "MQ-135"
#define Voltage_Resolution 5
#define ADC_Bit_Resolution 10
#define RatioMQ135CleanAir 3.6

MQUnifiedsensor MQ135(Board, Voltage_Resolution, ADC_Bit_Resolution, Pin, Type);

void setup() {
  Serial.begin(9600);
  Serial.println("Seconds,CO2_PPM");

  MQ135.setRegressionMethod(1); // Linear regression
  MQ135.setA(110.47);
  MQ135.setB(-2.862);
  MQ135.init();

  // Calibrate MQ-135 and calculate R0 value
  float calcR0 = 0;
  for (int i = 0; i < 10; i++) {
    MQ135.update();
    calcR0 += MQ135.calibrate(RatioMQ135CleanAir);
  }
  MQ135.setR0(calcR0 / 10);
}

void loop() {
  static unsigned long seconds = 0;
  MQ135.update();
  float co2_ppm = MQ135.readSensor();
  Serial.print(seconds);
  Serial.print(",");
  Serial.println(co2_ppm);
  seconds += 2;
  delay(2000);
}

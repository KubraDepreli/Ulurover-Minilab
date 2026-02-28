// Arduino Nano Blink Rate Control via Serial

const int ledPin = 13; // Built-in LED pin
unsigned long blinkInterval = 1000; // Default blink rate in ms
unsigned long lastBlink = 0;
String inputString = "";

void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  // Read serial input and update blinkInterval
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      unsigned long newInterval = inputString.toInt();
      if (newInterval > 0) {
        blinkInterval = newInterval;
      }
      inputString = "";
    } else {
      inputString += inChar;
    }
  }

  // Blink LED at the current interval
  if (millis() - lastBlink >= blinkInterval) {
    digitalWrite(ledPin, !digitalRead(ledPin));
    lastBlink = millis();
  }
}
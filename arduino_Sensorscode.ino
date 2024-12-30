


#include <dht.h>
#include <ArduinoJson.h>  // Include the ArduinoJson library

#define DHT11_PIN 6
#define ANALOG_IN_PIN A1  // Solar voltage
#define analogPin A4      // Analog pin connected to AOUT MQ
#define RL_VALUE 10       // Load resistance in kOhms
#define VCC 5.0           // Supply voltage
#define CLEAN_AIR_RATIO 3.6  // Rs/Ro ratio in clean air (per MQ-135 datasheet)
#define SensorPin A3      // Analog pin where the pH sensor is connected
#define Offset 0.00       // Adjust this offset for calibration
#define SamplingInterval 1000  // Sampling interval in milliseconds
#define AveragingSamples 10
#define LDR_PIN 5         // Digital pin where LDR is connected (DO pin)
const int turbidityPin = A5; // Analog pin connected to the turbidity sensor

dht DHT;

// Floats for ADC voltage & Input voltage
float adc_voltage = 0.0;
float in_voltage = 0.0;

// Floats for resistor values in the divider (in ohms)
float R1 = 30000.0;
float R2 = 7500.0;

// Float for Reference Voltage
float ref_voltage = 5.0;

// Integer for ADC value
int adc_value = 0;
int turbidityValue = 0;

float Ro = 10.0;  // Calibration value (to be calculated in clean air)

void setup() {
  Serial.begin(9600);  // Start serial communication
  pinMode(LDR_PIN, INPUT);  // Set the LDR pin as input
  Ro = calibrateSensor();  // Calibrate sensor in clean air
}

void loop() {
  static unsigned long lastTime = 0;
  static float pHArray[AveragingSamples];  // Array to store readings for averaging
  static int index = 0;
  float averagePH = 0.0;

  if (millis() - lastTime > SamplingInterval) {
    lastTime = millis();

    // Read sensor value and convert to voltage
    int sensorValue = analogRead(SensorPin);
    float voltage = sensorValue * 5.0 / 1023.0;

    // Convert voltage to pH value
    float pHValue = 3.5 * voltage + Offset;

    // Store pH value in the array
    pHArray[index++] = pHValue;
    if (index == AveragingSamples) {
      index = 0;
    }

    // Calculate average pH value
    for (int i = 0; i < AveragingSamples; i++) {
      averagePH += pHArray[i];
    }
    averagePH /= AveragingSamples;
  }

  // Collect sensor data
  float Rs = calculateRs(analogRead(A2));
  float ratio = Rs / Ro;  // Rs/Ro ratio
  float co2 = calculateConcentration(ratio, 0.7, -1.3);  // CO2

  int chk = DHT.read11(DHT11_PIN);  // Read DHT11 sensor
  adc_value = analogRead(ANALOG_IN_PIN);  // Read solar voltage

  // Calculate input voltage and sensor data
  adc_voltage  = (adc_value * ref_voltage) / 1024.0;
  in_voltage = adc_voltage / (R2 / (R1 + R2));  // Voltage divider calculation
  turbidityValue = analogRead(turbidityPin);  // Read turbidity sensor value

  // Read LDR state
  int ldrState = digitalRead(LDR_PIN);

  // Prepare JSON document
  StaticJsonDocument<512> doc;
  doc["temperature"] = DHT.temperature;
  doc["humidity"] = DHT.humidity;
  doc["co2_ppm"] = co2;
  doc["solar_voltage"] = in_voltage;
  doc["turbidity"] = turbidityValue;
  doc["ldr_state"] = (ldrState == HIGH) ? "1" : "0";
  doc["ph"] = averagePH;

  // Serialize and send JSON data over Serial
  serializeJson(doc, Serial);
  Serial.println();  // Newline for separation

  delay(3000);  // Wait for 3 seconds before the next reading
}

// Function to calculate Rs from the analog reading
float calculateRs(int raw_adc) {
  float Vout = (raw_adc / 1023.0) * VCC;
  return ((VCC - Vout) * RL_VALUE) / Vout;
}

// Calibration function to find Ro in clean air
float calibrateSensor() {
  int raw_adc = analogRead(analogPin);
  float Rs = calculateRs(raw_adc);
  return Rs / CLEAN_AIR_RATIO;
}

// Function to calculate gas concentration using power-law equation
float calculateConcentration(float ratio, float a, float b) {
  return pow(10, (log10(ratio) - b) / a);  // Curve equation
}

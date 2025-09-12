//Created on 19/01/2023
// Author: @dcupolillo (based on previous versions)

// Global variables and constants
const int TONE_1_PIN = 3;
const int TONE_2_PIN = 8;
const int PUMP_PIN = 5;
const int SHOCKER_PIN = 7;
const int RED_LED_PIN = 10;
const int GREEN_LED_PIN = 11;
const int LEFT_PROX = A4;
const int RIGHT_PROX = A5;
const int NOSE_PROX = A6;

// Serial messages of analog inputs
const int left_sensor_active = 5;
const int left_sensor_unactive = 15;
const int right_sensor_active = 6;
const int right_sensor_unactive = 16;
const int nosepoke_active = 7;
const int nosepoke_unactive = 17;

String serial_msg;

// Timing constants (ms)
const unsigned long EVENT_INTERVAL_THRESHOLD = 500; // Minimum time interval between sensor events
const unsigned long HARD_STOP_DURATION = 2000; // Duration after which the pump and shocker will be turned off automatically

// Sound frequency constants (Hz)
const int TONE_1_FREQUENCY = 3000;
const int TONE_2_FREQUENCY = 4000;
const int WHITE_NOISE_RANGE[] = {600, 1000};

// Thresholds for sensor detection, translating sensor's voltage to ADC value
const unsigned long DISTANCE_THRESHOLD = 100; // Threshold for proximity sensors
const unsigned long NOSEPOKE_DISTANCE_THRESHOLD = 500; // Threshold for nose sensor

// State variables to track the last known states (false = unactive)
bool is_left_sensor = false;
bool is_right_sensor = false;
bool is_nose_sensor = false;
bool is_pump_on = false;
bool is_shocker_on = false;
bool is_white_noise_on = false;

// Last time an event was triggered for debounce control
unsigned long last_pump_timestamp;
unsigned long last_shock_timestamp;
unsigned long last_left_sensor_timestamp = 0;
unsigned long last_right_sensor_timestamp = 0;
unsigned long last_nose_sensor_timestamp = 0;

void setup()
{
  // Initialize sensor and output pins
  pinMode(LEFT_PROX, INPUT);
  pinMode(RIGHT_PROX, INPUT);
  pinMode(NOSE_PROX, INPUT);
  pinMode(TONE_1_PIN, OUTPUT);
  pinMode(TONE_2_PIN, OUTPUT);
  pinMode(PUMP_PIN,OUTPUT);
  pinMode(SHOCKER_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);
  
  digitalWrite(SHOCKER_PIN, HIGH);                                                        // Set initial state of the shocker pin to HIGH (considered off)
  
  // Initialize serial communication
  Serial.begin(9600);
}

void loop()
{
  // Read sensors and compare against thresholds to determine proximity (generate sensor states)
  bool Leftsensor = (analogRead(LEFT_PROX) < DISTANCE_THRESHOLD);
  bool Rightsensor = (analogRead(RIGHT_PROX) < DISTANCE_THRESHOLD);
  bool Nosesensor = (analogRead(NOSE_PROX) < NOSEPOKE_DISTANCE_THRESHOLD);

  // Check for state changes in sensor detection and handle timing for debouncing
  // Left sensor
  if ((Leftsensor > is_left_sensor) &&                                                      // if it becomes active after it was not
      (millis() > last_left_sensor_timestamp + EVENT_INTERVAL_THRESHOLD)){                  // and certain time has passed since it was previously active
    last_left_sensor_timestamp = millis();
    Serial.println(left_sensor_active);                                                  // Detected object near left sensor
  }
  if (Leftsensor < is_left_sensor){                                                         // if it becomes inactive after it was active
    Serial.println(left_sensor_unactive);                                                // Object left proximity of left sensor
  }

  // Right sensor
  if ((Rightsensor > is_right_sensor) &&
      (millis() > last_right_sensor_timestamp+ EVENT_INTERVAL_THRESHOLD)){
    last_right_sensor_timestamp = millis();
    Serial.println(right_sensor_active);                                                 // Detected object near right sensor
  }
  if (Rightsensor < is_right_sensor) {
    Serial.println(right_sensor_unactive);                                               // Object left proximity of right sensor
  }

  // Nose sensor
  if ((Nosesensor > is_nose_sensor) &&
      (millis() > last_nose_sensor_timestamp + EVENT_INTERVAL_THRESHOLD)){
    last_nose_sensor_timestamp = millis();
    Serial.println(nosepoke_active);                                                     // Detected nosepoke
  }                
  if (Nosesensor < is_nose_sensor){
    Serial.println(nosepoke_unactive);                                                   // Nosepoke ended
  }

  // Update the last known states for each sensor
  is_left_sensor = Leftsensor;
  is_right_sensor = Rightsensor; 
  is_nose_sensor = Nosesensor;

  // serial communication TO the Arduino (Serial.read())
  if(Serial.available()>0){                                                               // return the number of bytes that are in the serial buffer
    char incoming_char = Serial.read();                                                   // return the first byte from the serial buffer
    if (incoming_char != '\r'){
      serial_msg += incoming_char;                                                        // concatenates character c to the end of the message (writing msg one char at a time)
    }                                                                                     // keeps doing it until a \r that indicates the end of message
    else{                                                                                 // once msg is ready, it checks the computer input with the task to perform
      if (serial_msg == "1"){                                                             // double brackets indicate string
        tone(TONE_1_PIN, TONE_1_FREQUENCY);                                               // Pure tone, 3kHz. tone() is a built-in Arduino function
      }
      else if (serial_msg == "2"){
        is_white_noise_on = true;                                                         // White Noise (the random sequence of freq. flag-on method: it has to be defined outside 
      }
      else if (serial_msg == "3"){
        PORTE|=_BV(PE3);
        last_pump_timestamp = millis();                                                   // millis() is a built-in Arduino function to start a timer
        is_pump_on = true;
      } 
      else if (serial_msg == "4"){
         tone(TONE_2_PIN, TONE_2_FREQUENCY);      
      }
      else if (serial_msg == "5"){
        digitalWrite(SHOCKER_PIN, LOW);
        last_shock_timestamp = millis();
        is_shocker_on = true;                               // flag to report shock status (useful for the hard-stop)
      }
      else if (serial_msg == "11"){
        noTone(TONE_1_PIN);                                 // noTone is a built-in Arduino function
      }
      else if (serial_msg == "12") {
        noTone(TONE_1_PIN);
        is_white_noise_on=false;
      } 
      else if (serial_msg == "13"){
        PORTE&=~_BV(PE3);
        last_pump_timestamp = 0;
        is_pump_on = false;
      }
      else if (serial_msg == "14"){
        noTone(TONE_2_PIN);
      }
      else if (serial_msg == "15"){                          // anticipate shock hard stop
        digitalWrite(SHOCKER_PIN, HIGH);
        last_shock_timestamp = 0;
        is_shocker_on = false;
      }
      else if (serial_msg == "8"){
        digitalWrite(GREEN_LED_PIN, HIGH);
      }
      else if (serial_msg == "18"){
        digitalWrite(GREEN_LED_PIN, LOW);
      }
      else if (serial_msg == "9"){
        digitalWrite(RED_LED_PIN, HIGH);
      }
      else if (serial_msg == "19"){
        digitalWrite(RED_LED_PIN, LOW);
      }
      serial_msg = "";                                       // re-initialize the message
    }
  }
  // Generate white noise if enabled
  if (is_white_noise_on) {
    tone(TONE_1_PIN, random(WHITE_NOISE_RANGE[0], WHITE_NOISE_RANGE[1]));
  }

  // Hard stops
  if ((is_pump_on == true) and (millis() - last_pump_timestamp > HARD_STOP_DURATION)){
        digitalWrite(PUMP_PIN,HIGH);
        last_pump_timestamp = 0;
        is_pump_on = false;
        }
  if ((is_shocker_on == true) and (millis() - last_shock_timestamp > HARD_STOP_DURATION)){
      digitalWrite(SHOCKER_PIN,HIGH);
      last_shock_timestamp =0;
      is_shocker_on = false;
      }
}

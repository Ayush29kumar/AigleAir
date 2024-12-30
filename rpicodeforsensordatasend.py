

import RPi.GPIO as GPIO
from flask import Flask, jsonify, render_template
from threading import Thread
from serial import Serial
import json
import time
from pymongo import MongoClient
from datetime import datetime

import geocoder
from geopy.geocoders import Nominatim
g = geocoder.ip('me')
geolocator = Nominatim(user_agent="GetLSystemsoc")
location = geolocator.reverse((g.latlng[0], g.latlng[1]))
city = None
address_components = location.raw.get("address", {})
if "city" in address_components:
    city = address_components["city"]
elif "town" in address_components:
    city = address_components["town"]
elif "village" in address_components:
    city = address_components["village"]
GPIO.setmode(GPIO.BCM)  # Use BCM GPIO numbering
servo_pin = 17 
# Set up the GPIO pin for PWM
GPIO.setup(servo_pin, GPIO.OUT)
pwm = GPIO.PWM(servo_pin, 50)  # 50Hz PWM frequency (standard for servos)

# Start PWM with a duty cycle of 0
pwm.start(0)

def set_angle(angle):
    """Set the servo to the specified angle (0-180 degrees)."""
    duty_cycle = 2 + (angle / 18)  # Map angle to duty cycle (2-12 for 0-180�)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)  # Wait for the servo to move
    pwm.ChangeDutyCycle(0)  # Turn off the PWM signal to avoid jitter


# GPIO setup
RELAY_PIN = 18  # Replace with the GPIO pin connected to the relay
GPIO.setup(RELAY_PIN, GPIO.OUT)  # Set relay pin as output
RELAY_PIN2 = 22  # Replace with the GPIO pin connected to the relay

GPIO.setup(RELAY_PIN2, GPIO.OUT)  
# Flask app setup
app = Flask(__name__)

# Shared variable to store the latest sensor data
sensor_data = {}

# Open the serial port where the Arduino is connected
try:
    ser = Serial('/dev/ttyACM0', 9600)  # Change '/dev/ttyUSB0' to your Arduino's serial port
except:
    ser = Serial('/dev/ttyACM1', 9600)

# MongoDB connection
MONGO_URI = "mongodb+srv://avin:avin@cluster0.fhxczjk.mongodb.net/aigleair?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['aigleair']
systems_collection = db['systems']

# Replace this with your system's MAC address
mac_address = 'e4:5f:01:bb:f8:96'

def send_data_to_mongodb(data):
    """Send sensor data to MongoDB."""
    if data.get("ldr_state") == "0":
        GPIO.output(RELAY_PIN, GPIO.LOW)
    else:
        GPIO.output(RELAY_PIN, GPIO.HIGH)
    if data.get("temperature") >= 28 :
        set_angle(180)
    else:
        set_angle(0)
    if data.get("temperature") >= 25 :
        GPIO.output(RELAY_PIN2, GPIO.HIGH)
    else:
        GPIO.output(RELAY_PIN2, GPIO.LOW)
    
    try:
        # Prepare the data to match the schema
        document = {
            "macAddress": mac_address,
            "name": "Aigle Air Unit 1",  # Replace with appropriate name
            "location": str(location),  # Replace with actual location
            "isOnline": True,
            "data": {
                "temperature": data.get("temperature"),
                "humidity": data.get("humidity"),
                "pHLevel": data.get("pHLevel"),
                "solarVolt": data.get("solar_voltage"),
                "co2_ppm": data.get("co2_ppm"),
                "turbidity": data.get("turbidity"),
                "ldr_state": data.get("ldr_state"),
            },
            "lastUpdated": datetime.utcnow()
        }

        # Update the document in MongoDB or insert if it doesn't exist
        systems_collection.update_one(
            {"macAddress": mac_address},  # Match by MAC address
            {"$set": document},          # Update or set the data
            upsert=True                  # Insert if the document doesn't exist
        )
        print("Data sent successfully to MongoDB")
    except Exception as e:
        print(f"Error sending data to MongoDB: {e}")

def read_sensor_data():
    global sensor_data
    while True:
        if ser.in_waiting > 0:  # Check if data is available to read
            line = ser.readline().decode('utf-8').strip()  # Read the line and decode
            try:
                # Assuming the Arduino sends data in JSON format
                sensor_data = json.loads(line)  # Parse the JSON data
                
                # Send the sensor data to MongoDB
                send_data_to_mongodb(sensor_data)
                
            except json.JSONDecodeError:
                print("Error decoding JSON data.")
        time.sleep(1)

@app.route("/")
def index():
    """Render the homepage."""
    return render_template("index.html")

@app.route("/data")
def get_data():
    """Endpoint to fetch the latest sensor data."""
    global sensor_data
    return jsonify(sensor_data)

if __name__ == "__main__":
    # Start the serial reading in a separate thread
    thread = Thread(target=read_sensor_data)
    thread.daemon = True
    thread.start()

    # Run the Flask app
    app.run(host="0.0.0.0", port=5000)




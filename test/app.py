# from serial import Serial

# import json
# import time

# # Open the serial port where the Arduino is connected
# ser = Serial('/dev/ttyACOM0', 9600)  # Change 'COM3' to your Arduino's port (e.g., 'COMx' for Windows or '/dev/ttyUSBx' for Linux)

# def read_sensor_data():
#     while True:
#         if ser.in_waiting > 0:  # Check if data is available to read
#             line = ser.readline().decode('utf-8').strip()  # Read the line and decode
#             try:
#                 sensor_data = json.loads(line)  # Parse the JSON data
#                 print("Sensor Data:", sensor_data)
#             except json.JSONDecodeError:
#                 print("Error decoding JSON data.")
#         time.sleep(1)

# if __name__ == "__main__":
#     print("Reading sensor data...")
#     read_sensor_data()


from flask import Flask, jsonify, render_template
from threading import Thread
from serial import Serial
import json
import time
from pymongo import MongoClient
from datetime import datetime

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
    try:
        # Prepare the data to match the schema
        document = {
            "macAddress": mac_address,
            "name": "Liquid Tree Unit 1",  # Replace with appropriate name
            "location": "Raspberry Pi Location",  # Replace with actual location
            "isOnline": True,
            "data": {
                "temperature": data.get("temperature"),
                "humidity": data.get("humidity"),
                "pHLevel": data.get("pHLevel")
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

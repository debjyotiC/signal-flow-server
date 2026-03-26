from flask import Flask, render_template, jsonify, request
from os import environ
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = environ.get('MONGO_URI')

db = MongoClient(MONGO_URI)

USERNAME = "debjyotichowdhury"

users = db["users"]
boards = db["newboards"]
sensors = db["sensors"]
saved_forecasts = db["analytics"]

def get_user_id(username):
    user = users.find_one({"username": username})
    return user.get("_id") if user else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/devices', methods=['GET'])
def get_metadata():
    # user_id = get_user_id()
    # if not user_id:
    #     return jsonify({"error": "User not found"}), 404

    metadata = {'Consentium-Mote': ['Temperature', 'Pressure', 'Light', 'Humidity', 'Resistance', 'Altitude'], 'testdevice': ['Temperature']}
    # for board in boards.find_one({"userId": user_id}, {"boardName": 1, "boardKey": 1}):
    #     board_name = board.get("boardName")
    #     board_key = board.get("boardKey")
    #     sensor_doc = sensors.find_one({"boardKey": board_key})
    #     sensor_list = sensor_doc.get("sensorData", []) if sensor_doc else []
    #     sensor_names = [s.get("info", "").split("/")[0] for s in sensor_list]
    #     metadata[board_name] = sensor_names
    #
    return jsonify(metadata)

if __name__ == "__main__":
    app.run(debug=True)
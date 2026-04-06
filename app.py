from flask import Flask, render_template, jsonify, request
from os import environ
from datetime import datetime, timezone
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = environ.get('MONGO_URI')

client = MongoClient(MONGO_URI)

USERNAME = "debjyotichowdhury"

db = client['consentiumWebApp']
users = db["users"]
boards = db["newboards"]
sensors = db["sensors"]
signal_flow = db["signalFlow"]

def get_user_id(username):
    user = users.find_one({"username": username})
    return user.get("_id") if user else None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/devices', methods=['GET'])
def get_metadata():
    user_id = get_user_id(USERNAME)

    if not user_id:
        return jsonify({"error": "User not found"}), 404

    metadata = {}
    for board in boards.find({"userId": user_id}, {"boardName": 1, "boardKey": 1}):
        board_name = board.get("boardName")
        board_key = board.get("boardKey")
        sensor_doc = sensors.find_one({"boardKey": board_key})
        sensor_list = sensor_doc.get("sensorData", []) if sensor_doc else []
        sensor_names = [s.get("info", "").split("/")[0] for s in sensor_list]
        metadata[board_name] = sensor_names

    return jsonify(metadata)

@app.route('/api/v1/pipelines', methods=['POST'])
def save_pipeline():
    try:
        data = request.get_json()

        user_id = get_user_id(USERNAME)

        if not user_id:
            return jsonify({"error": "User not found"}), 404

        # Extract payload
        nodes = data.get('nodes', [])
        topology = data.get('topology', [])

        if not nodes:
            return jsonify({"status": "error", "message": "Cannot save an empty pipeline."}), 400

        # Construct the document
        pipeline_doc = {
            "title": data.get('title', 'Untitled SignalFlow Graph'),
            "version": data.get('version', '1.0'),
            "platform": data.get('platform', 'Consentium EdgeNeuron'),
            "nodes": nodes,
            "topology": topology,
            "deployedAt": datetime.now(timezone.utc),
            "status": "active",
            "userId": user_id
        }

        # Insert into MongoDB
        result = signal_flow.insert_one(pipeline_doc)

        return jsonify({
            "status": "success",
            "message": "Pipeline deployed successfully",
            "pipeline_id": str(result.inserted_id)
        }), 201

    except Exception as e:
        print(f"Error saving pipeline: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5050)
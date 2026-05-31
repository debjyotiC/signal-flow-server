from flask import Flask, render_template, jsonify, request
from os import environ
from datetime import datetime, timezone
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

MONGO_URI = environ.get('MONGO_URI')

client = MongoClient(MONGO_URI)

USERNAME = "debjyotichowdhury"

db = client['consentiumWebApp']
users = db["users"]
boards = db["newboards"]
sensors = db["sensors"]
signal_flow = db["signalFlow"]
hardware_relay = db["hardwareRelay"]

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


# --- 2. API to get the LIST of saved flows (Populates the bottom drawer) ---
@app.route('/api/v1/pipelines', methods=['GET'])
def get_all_pipelines():
    try:
        user_id = get_user_id(USERNAME)
        
        # Fetch all user pipelines, but only grab the title and deployment date to save bandwidth
        cursor = signal_flow.find(
            {"userId": user_id},
            {"title": 1, "deployedAt": 1}
        ).sort("deployedAt", -1)  # Sort newest first

        formatted_data = []
        for doc in cursor:
            formatted_data.append({
                "id": str(doc["_id"]),
                "title": doc.get("title", "Untitled Pipeline"),
                # The frontend expects 'timestamp' to format the date correctly
                "timestamp": doc.get("deployedAt", datetime.now(timezone.utc)).isoformat()
            })

        # Return the exact JSON structure your frontend fetchSavedGraphs() expects
        return jsonify({
            "status": "success",
            "data": formatted_data
        }), 200

    except Exception as e:
        print(f"Error fetching pipelines: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


# --- 3. API to load a SPECIFIC flow (Draws the nodes and wires on canvas) ---
@app.route('/api/v1/pipelines/<pipeline_id>', methods=['GET'])
def get_single_pipeline(pipeline_id):
    try:
        # Search the database using the MongoDB ObjectId
        pipeline = signal_flow.find_one({"_id": ObjectId(pipeline_id)})

        if not pipeline:
            return jsonify({"status": "error", "message": "Pipeline not found"}), 404

        # Map the database document to the JSON structure your loadPipeline() function expects
        formatted_pipeline = {
            "id": str(pipeline["_id"]),
            "title": pipeline.get("title"),
            "version": pipeline.get("version"),
            "platform": pipeline.get("platform"),
            "nodes": pipeline.get("nodes", []),
            "topology": pipeline.get("topology", []),
            "timestamp": pipeline.get("deployedAt", datetime.now(timezone.utc)).isoformat()
        }

        print(formatted_pipeline)

        return jsonify({
            "status": "success",
            "pipeline": formatted_pipeline
        }), 200

    except Exception as e:
        print(f"Error fetching pipeline {pipeline_id}: {e}")
        return jsonify({"status": "error", "message": "Invalid ID or server error"}), 500


# --- 4. The Save Pipeline Route (From earlier) ---
@app.route('/api/v1/pipelines', methods=['POST'])
def save_pipeline():
    try:
        data = request.get_json()
        user_id = get_user_id(USERNAME)

        pipeline_doc = {
            "title": data.get('title', 'Untitled SignalFlow Graph'),
            "userId": user_id,
            "nodes": data.get('nodes', []),
            "topology": data.get('topology', []),
            "deployedAt": datetime.now(timezone.utc),
            "active": False
        }

        pipeline_id = data.get('pipeline_id')
        if pipeline_id:
            try:
                obj_id = ObjectId(pipeline_id)
            except Exception:
                return jsonify({"status": "error", "message": "Invalid pipeline ID"}), 400

            update_fields = {
                "nodes": data.get('nodes', []),
                "topology": data.get('topology', []),
                "deployedAt": datetime.now(timezone.utc)
            }
            if 'title' in data:
                update_fields['title'] = data['title']

            signal_flow.update_one(
                {"_id": obj_id},
                {"$set": update_fields}
            )
            return jsonify({
                "status": "success",
                "pipeline_id": pipeline_id
            }), 200
        else:
            result = signal_flow.insert_one(pipeline_doc)
            return jsonify({
                "status": "success",
                "pipeline_id": str(result.inserted_id)
            }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- 5. Run flow ---
@app.route('/api/v1/pipelines/run', methods=['POST'])
def run_pipeline():
    try:
        data = request.get_json()
        pipeline_id = data.get("pipeline_id")
        action = data.get("action")
        
        is_active = (action == "start")
        
        signal_flow.update_one(
            {"_id": ObjectId(pipeline_id)}, 
            {"$set": {"active": is_active}}
        )
        
        return jsonify({
            "status": "success",
            "pipeline_id": str(pipeline_id),
            "action": action
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Delete a Pipeline Route ---
@app.route('/api/v1/pipelines/<pipeline_id>', methods=['DELETE'])
def delete_pipeline(pipeline_id):
    try:
        result = signal_flow.delete_one({"_id": ObjectId(pipeline_id)})

        if result.deleted_count == 1:
            return jsonify({"status": "success", "message": "Pipeline deleted"}), 200
        else:
            return jsonify({"status": "error", "message": "Pipeline not found"}), 404

    except Exception as e:
        print(f"Error deleting pipeline {pipeline_id}: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/v1/hardware/channels', methods=['GET'])
def get_hardware_channel():
    try:
        board_key = request.args.get("board_key")
        if not board_key:
            return jsonify({"status": "error", "message": "board_key is required"}), 400
            
        doc = hardware_relay.find_one({"boardKey": board_key})
        if not doc:
            r = {
                "user_id": get_user_id(USERNAME),
                "boardKey" : board_key,
                "channel_values": [],
                "taken_channels": [0,0,0,0,0,0,0,0],
                "updatedAt": datetime.now(timezone.utc)
            }
            hardware_relay.insert_one(r)
            doc = r
            
        taken_channels = doc.get("taken_channels", [])
        # 0 denotes available, 1 denotes taken. Return indices of available channels.
        available_channels = [str(i) for i, is_taken in enumerate(taken_channels) if is_taken == 0]
        
        return jsonify(available_channels), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/v1/hardware/channels/take', methods=['POST'])
def take_hardware_channel():
    try:
        data = request.get_json()
        board_key = data.get("board_key")
        channel = data.get("channel")
        prev_channel = data.get("previous_channel")

        if not board_key or channel is None:
            return jsonify({"status": "error", "message": "board_key and channel are required"}), 400

        doc = hardware_relay.find_one({"boardKey": board_key})
        if doc:
            taken_channels = doc.get("taken_channels", [0]*8)
            
            # If the user changed channels, release the previous one
            if prev_channel is not None and 0 <= prev_channel < len(taken_channels):
                taken_channels[prev_channel] = 0
                
            # Take the new channel
            if 0 <= channel < len(taken_channels):
                taken_channels[channel] = 1
                
            hardware_relay.update_one(
                {"_id": doc["_id"]},
                {"$set": {"taken_channels": taken_channels, "updatedAt": datetime.now(timezone.utc)}}
            )
            return jsonify({"status": "success", "message": "Channel assignment updated"}), 200
        else:
            return jsonify({"status": "error", "message": "Device not found"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5050)
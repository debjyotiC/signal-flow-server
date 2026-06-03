require('dotenv').config();
const express = require('express');
const { MongoClient, ObjectId } = require('mongodb');
const cors = require('cors');
const path = require('path');

const app = express();
app.use(express.json());
app.use(cors());

// In Flask, render_template loads from templates/ folder. 
// In Express, we can serve the static files and serve index.html directly.
app.use('/static', express.static(path.join(__dirname, 'static')));

const MONGO_URI = process.env.MONGO_URI;
let client;
let db, users, boards, sensors, signal_flow, hardware_relay;

const USERNAME = "debjyotichowdhury";

async function connectDB() {
    client = new MongoClient(MONGO_URI);
    await client.connect();
    db = client.db('consentiumWebApp');
    users = db.collection('users');
    boards = db.collection('newboards');
    sensors = db.collection('sensors');
    signal_flow = db.collection('signalFlow');
    hardware_relay = db.collection('hardwareRelay');
    console.log("Connected to MongoDB");
}

async function getUserId(username) {
    const user = await users.findOne({ username: username });
    return user ? user._id : null;
}

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'templates', 'index.html'));
});

app.get('/api/devices', async (req, res) => {
    try {
        const userId = await getUserId(USERNAME);

        if (!userId) {
            return res.status(404).json({ error: "User not found" });
        }

        const metadata = {};
        const userBoards = await boards.find({ userId: userId }).project({ boardName: 1, boardKey: 1 }).toArray();
        
        for (const board of userBoards) {
            const boardName = board.boardName;
            const boardKey = board.boardKey;
            const sensorDoc = await sensors.findOne({ boardKey: boardKey });
            const sensorList = sensorDoc && sensorDoc.sensorData ? sensorDoc.sensorData : [];
            const sensorNames = sensorList.map(s => s.info ? s.info.split('/')[0] : "");
            metadata[boardName] = {
                key: boardKey,
                sensors: sensorNames
            };
        }

        res.json(metadata);
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.get('/api/v1/pipelines', async (req, res) => {
    try {
        const userId = await getUserId(USERNAME);
        
        const cursor = signal_flow.find(
            { userId: userId },
            { projection: { title: 1, deployedAt: 1 } }
        ).sort({ deployedAt: -1 });

        const formattedData = [];
        for await (const doc of cursor) {
            formattedData.push({
                id: doc._id.toString(),
                title: doc.title || "Untitled Pipeline",
                timestamp: (doc.deployedAt || new Date()).toISOString()
            });
        }

        res.status(200).json({
            status: "success",
            data: formattedData
        });
    } catch (e) {
        console.error("Error fetching pipelines:", e);
        res.status(500).json({ status: "error", message: "Internal server error" });
    }
});

app.get('/api/v1/pipelines/:pipeline_id', async (req, res) => {
    try {
        const pipelineId = req.params.pipeline_id;
        const pipeline = await signal_flow.findOne({ _id: new ObjectId(pipelineId) });

        if (!pipeline) {
            return res.status(404).json({ status: "error", message: "Pipeline not found" });
        }

        const formattedPipeline = {
            id: pipeline._id.toString(),
            title: pipeline.title,
            version: pipeline.version,
            platform: pipeline.platform,
            nodes: pipeline.nodes || [],
            topology: pipeline.topology || [],
            timestamp: (pipeline.deployedAt || new Date()).toISOString()
        };

        res.status(200).json({
            status: "success",
            pipeline: formattedPipeline
        });
    } catch (e) {
        console.error(`Error fetching pipeline ${req.params.pipeline_id}:`, e);
        res.status(500).json({ status: "error", message: "Invalid ID or server error" });
    }
});

app.post('/api/v1/pipelines', async (req, res) => {
    try {
        const data = req.body;
        const userId = await getUserId(USERNAME);

        const pipelineDoc = {
            title: data.title || 'Untitled SignalFlow Graph',
            userId: userId,
            nodes: data.nodes || [],
            topology: data.topology || [],
            deployedAt: new Date(),
            active: false
        };

        const pipelineId = data.pipeline_id;
        if (pipelineId) {
            let objId;
            try {
                objId = new ObjectId(pipelineId);
            } catch (e) {
                return res.status(400).json({ status: "error", message: "Invalid pipeline ID" });
            }

            const updateFields = {
                nodes: data.nodes || [],
                topology: data.topology || [],
                deployedAt: new Date()
            };
            if (data.title) {
                updateFields.title = data.title;
            }

            await signal_flow.updateOne(
                { _id: objId },
                { $set: updateFields }
            );
            res.status(200).json({
                status: "success",
                pipeline_id: pipelineId
            });
        } else {
            const result = await signal_flow.insertOne(pipelineDoc);
            res.status(201).json({
                status: "success",
                pipeline_id: result.insertedId.toString()
            });
        }
    } catch (e) {
        res.status(500).json({ status: "error", message: e.message });
    }
});

app.post('/api/v1/pipelines/run', async (req, res) => {
    try {
        const data = req.body;
        const pipelineId = data.pipeline_id;
        const action = data.action;
        
        const isActive = (action === "start");
        
        await signal_flow.updateOne(
            { _id: new ObjectId(pipelineId) }, 
            { $set: { active: isActive } }
        );
        
        res.status(200).json({
            status: "success",
            pipeline_id: String(pipelineId),
            action: action
        });
    } catch (e) {
        res.status(500).json({ status: "error", message: e.message });
    }
});

app.delete('/api/v1/pipelines/:pipeline_id', async (req, res) => {
    try {
        const pipelineId = req.params.pipeline_id;
        const result = await signal_flow.deleteOne({ _id: new ObjectId(pipelineId) });

        if (result.deletedCount === 1) {
            res.status(200).json({ status: "success", message: "Pipeline deleted" });
        } else {
            res.status(404).json({ status: "error", message: "Pipeline not found" });
        }
    } catch (e) {
        console.error(`Error deleting pipeline ${req.params.pipeline_id}:`, e);
        res.status(500).json({ status: "error", message: "Internal server error" });
    }
});

app.get('/api/v1/hardware/channels', async (req, res) => {
    try {
        const boardKey = req.query.board_key;
        if (!boardKey) {
            return res.status(400).json({ status: "error", message: "board_key is required" });
        }
            
        let doc = await hardware_relay.findOne({ boardKey: boardKey });
        if (!doc) {
            const userId = await getUserId(USERNAME);
            const r = {
                user_id: userId,
                boardKey: boardKey,
                channel_values: [],
                taken_channels: [0,0,0,0,0,0,0,0],
                updatedAt: new Date()
            };
            await hardware_relay.insertOne(r);
            doc = r;
        }
            
        const takenChannels = doc.taken_channels || [];
        // 0 denotes available, 1 denotes taken. Return indices of available channels.
        const availableChannels = [];
        takenChannels.forEach((isTaken, index) => {
            if (isTaken === 0) {
                availableChannels.push(String(index));
            }
        });
        
        res.status(200).json(availableChannels);
    } catch (e) {
        res.status(500).json({ status: "error", message: e.message });
    }
});

app.post('/api/v1/hardware/channels/take', async (req, res) => {
    try {
        const data = req.body;
        const boardKey = data.board_key;
        const channel = data.channel;
        const prevChannel = data.previous_channel;

        if (!boardKey || channel === undefined || channel === null) {
            return res.status(400).json({ status: "error", message: "board_key and channel are required" });
        }

        const doc = await hardware_relay.findOne({ boardKey: boardKey });
        if (doc) {
            const takenChannels = doc.taken_channels || [0,0,0,0,0,0,0,0];
            
            // If the user changed channels, release the previous one
            if (prevChannel !== undefined && prevChannel !== null && prevChannel >= 0 && prevChannel < takenChannels.length) {
                takenChannels[prevChannel] = 0;
            }
                
            // Take the new channel
            if (channel >= 0 && channel < takenChannels.length) {
                takenChannels[channel] = 1;
            }
                
            await hardware_relay.updateOne(
                { _id: doc._id },
                { $set: { taken_channels: takenChannels, updatedAt: new Date() } }
            );
            res.status(200).json({ status: "success", message: "Channel assignment updated" });
        } else {
            res.status(404).json({ status: "error", message: "Device not found" });
        }
    } catch (e) {
        res.status(500).json({ status: "error", message: e.message });
    }
});

const PORT = process.env.PORT || 5050;

connectDB().then(() => {
    app.listen(PORT, '0.0.0.0', () => {
        console.log(`Server is running on port ${PORT}`);
    });
}).catch(console.error);

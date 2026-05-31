# SignalFlow Server API Documentation

This document describes all available API endpoints, their allowed HTTP methods, and the expected request/response payloads for the SignalFlow backend server.

---

## 1. Device Metadata
**Endpoint:** `/api/devices`
**Method:** `GET`
**Description:** Retrieves a mapping of all hardware boards and their associated sensors for the authenticated user.

**Expected Payload:** None.
**Success Response (200):**
```json
{
  "BoardName_1": ["Sensor1", "Sensor2"],
  "BoardName_2": ["Sensor3"]
}
```

---

## 2. List All Pipelines
**Endpoint:** `/api/v1/pipelines`
**Method:** `GET`
**Description:** Returns a summary list of all saved pipelines (signal flows) for the authenticated user, sorted by most recently modified/deployed.

**Expected Payload:** None.
**Success Response (200):**
```json
{
  "status": "success",
  "data": [
    {
      "id": "60a8b9e8f1b2c3d4e5f6g7h8",
      "title": "My Flow 1",
      "timestamp": "2026-05-31T12:00:00.000000+00:00"
    }
  ]
}
```

---

## 3. Get Specific Pipeline
**Endpoint:** `/api/v1/pipelines/<pipeline_id>`
**Method:** `GET`
**Description:** Loads the complete data (nodes and topology) for a specific pipeline.

**Expected Payload:** None (URL Parameter: `pipeline_id`)
**Success Response (200):**
```json
{
  "status": "success",
  "pipeline": {
    "id": "60a8b9e8f1b2c3d4e5f6g7h8",
    "title": "My Flow 1",
    "version": 1.0,
    "platform": "web",
    "nodes": [ ... ],
    "topology": [ ... ],
    "timestamp": "2026-05-31T12:00:00.000000+00:00"
  }
}
```

---

## 4. Save / Create Pipeline
**Endpoint:** `/api/v1/pipelines`
**Method:** `POST`
**Description:** Creates a new pipeline or updates an existing one if a `pipeline_id` is provided in the payload.

**Expected Payload:**
```json
{
  "pipeline_id": "60a8b9e8f1b2c3d4e5f6g7h8", // Optional: Include to update, omit to create new
  "title": "My Flow 1",                     // Optional
  "nodes": [ ... ],                         // Array of node objects
  "topology": [ ... ]                       // Array of connection objects
}
```
**Success Response (200 for Update, 201 for Create):**
```json
{
  "status": "success",
  "pipeline_id": "60a8b9e8f1b2c3d4e5f6g7h8"
}
```

---

## 5. Run / Stop Pipeline
**Endpoint:** `/api/v1/pipelines/run`
**Method:** `POST`
**Description:** Marks a pipeline's state as active (`true`) or inactive (`false`) in the database. 

**Expected Payload:**
```json
{
  "pipeline_id": "60a8b9e8f1b2c3d4e5f6g7h8",
  "action": "start" // "start" or "stop"
}
```
**Success Response (200):**
```json
{
  "status": "success",
  "pipeline_id": "60a8b9e8f1b2c3d4e5f6g7h8",
  "action": "start"
}
```

---

## 6. Delete Pipeline
**Endpoint:** `/api/v1/pipelines/<pipeline_id>`
**Method:** `DELETE`
**Description:** Permanently deletes a specific pipeline from the database.

**Expected Payload:** None (URL Parameter: `pipeline_id`)
**Success Response (200):**
```json
{
  "status": "success",
  "message": "Pipeline deleted"
}
```

---

## 7. Get Available Hardware Channels
**Endpoint:** `/api/v1/hardware/channels`
**Method:** `GET`
**Description:** Retrieves a list of available channels (0-7) for a specific hardware relay board. Automatically provisions a database entry if it's the board's first interaction.

**Expected Payload:** None.
**URL Query Parameters:** `?board_key=<your_board_key>`
**Success Response (200):**
```json
["0", "1", "3", "4", "5", "6", "7"] // Returns string indices of channels that are free (0)
```

---

## 8. Take / Release Hardware Channel
**Endpoint:** `/api/v1/hardware/channels/take`
**Method:** `POST`
**Description:** Assigns a specific channel to a node. If the node previously held a different channel, it releases the old channel and takes the new one.

**Expected Payload:**
```json
{
  "board_key": "BOARD_12345",
  "channel": 2,               // Integer (0-7) indicating the new channel to take
  "previous_channel": 1       // Optional: Integer (0-7) indicating the channel to release
}
```
**Success Response (200):**
```json
{
  "status": "success",
  "message": "Channel assignment updated"
}
```

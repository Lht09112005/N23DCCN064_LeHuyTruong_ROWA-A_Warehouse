import os
import json
import time
import threading
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT & STATE
# ─────────────────────────────────────────────────────────────────────────────
PORT = int(os.environ.get("PORT", 5000))
NODE_URLS_RAW = os.environ.get("NODE_URLS", "A:http://node-a:5001,B:http://node-b:5002,C:http://node-c:5003")

# Parse nodes urls (e.g. {"A": "http://node-a:5001", ...})
NODES = {}
for item in NODE_URLS_RAW.split(","):
    if ":" in item:
        nid, url = item.split(":", 1)
        NODES[nid.strip()] = url.strip()

DATA_DIR = "/app/data"
STATE_FILE = os.path.join(DATA_DIR, "coordinator_state.json")

tx_counter = 0
recovery_log = [] # List of {"txId": int, "oldQty": int, "newQty": int, "missedBy": list, "appliedTo": list, "time": str}

lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING & PERSISTENCE
# ─────────────────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] [COORD] {msg}", flush=True)

def load_state():
    global tx_counter, recovery_log
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                tx_counter = data.get("tx_counter", 0)
                recovery_log = data.get("recovery_log", [])
                log(f"Coordinator state restored. Last TX: {tx_counter} | Recovery log size: {len(recovery_log)}")
        except Exception as e:
            log(f"Error loading state: {e}", "WARNING")
            save_state()
    else:
        save_state()

def save_state():
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({
                "tx_counter": tx_counter,
                "recovery_log": recovery_log
            }, f)
    except Exception as e:
        log(f"Error saving state: {e}", "ERROR")

# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND ROUTING
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

# ─────────────────────────────────────────────────────────────────────────────
# HTTP REST API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/status", methods=["GET"])
def get_system_status():
    global tx_counter, recovery_log
    
    # Ping all nodes to fetch their current status
    node_statuses = {}
    for nid, url in NODES.items():
        try:
            resp = requests.get(f"{url}/status", timeout=1.5)
            if resp.status_code == 200:
                node_statuses[nid] = resp.json()
            else:
                node_statuses[nid] = {"node_id": nid, "status": "DOWN", "quantity": 0, "lastTxId": 0}
        except Exception:
            # Connection error means container is DOWN (or stopped)
            node_statuses[nid] = {"node_id": nid, "status": "DOWN", "quantity": 0, "lastTxId": 0}
            
    with lock:
        return jsonify({
            "nodes": node_statuses,
            "txCounter": tx_counter,
            "recoveryLog": recovery_log
        })

@app.route("/api/write", methods=["POST"])
def write_transaction():
    global tx_counter, recovery_log
    
    data = request.json or {}
    sku = data.get("sku", "sku001")
    delta = data.get("delta")
    
    if delta is None:
        return jsonify({"error": "Missing delta"}), 400
        
    with lock:
        tx_counter += 1
        curr_tx = tx_counter
        
    log(f"📤 COORDINATOR: Bắt đầu Write Transaction TX-{curr_tx:03d} | {sku} delta: {delta:+}", "INFO")
    
    # 1. Identify which nodes are currently available (UP)
    available_nodes = []
    down_nodes = []
    
    for nid, url in NODES.items():
        try:
            resp = requests.get(f"{url}/status", timeout=1.0)
            # Must check if the node's internal state is UP
            if resp.status_code == 200 and resp.json().get("status") in ["UP", "SYNCED"]:
                available_nodes.append(nid)
            else:
                down_nodes.append(nid)
        except Exception:
            down_nodes.append(nid)
            
    if not available_nodes:
        log("❌ No nodes available! Transaction aborted.", "ERROR")
        with lock:
            tx_counter -= 1 # Revert tx index
        return jsonify({
            "status": "ABORTED",
            "error": "No nodes available to commit transaction"
        }), 503
        
    log(f"[ROWA-A §14.4] Available nodes to write: {available_nodes}", "INFO")
    if down_nodes:
        log(f"⚠️ Down nodes (will bypass & log): {down_nodes}", "WARNING")
        
    # 2. Write to all available nodes concurrently (or sequentially for simple reliable HTTP execution)
    committed_nodes = []
    failed_nodes = []
    
    committed_old_qty = None
    committed_new_qty = None
    
    for nid in available_nodes:
        url = NODES[nid]
        try:
            payload = {
                "tx_id": curr_tx,
                "sku": sku,
                "delta": delta
            }
            resp = requests.post(f"{url}/write", json=payload, timeout=2.0)
            if resp.status_code == 200 and resp.json().get("status") == "COMMITTED":
                committed_nodes.append(nid)
                if committed_new_qty is None:
                    # Lấy số lượng mới từ Node đầu tiên trả về thành công
                    committed_old_qty = resp.json().get("old_qty", 0)
                    committed_new_qty = resp.json().get("new_qty", 0)
            else:
                failed_nodes.append(nid)
        except Exception as e:
            log(f"Error writing to node {nid}: {e}", "WARNING")
            failed_nodes.append(nid)
            
    # Treat failed writes as down nodes for recovery log
    all_down_or_failed = list(set(down_nodes + failed_nodes))
    
    # 3. If there were down or failed nodes, record in the central recovery log
    with lock:
        if all_down_or_failed:
            log_entry = {
                "txId": curr_tx,
                "sku": sku,
                "oldQty": committed_old_qty,
                "newQty": committed_new_qty,
                "time": time.strftime("%H:%M:%S"),
                "missedBy": all_down_or_failed,
                "appliedTo": committed_nodes
            }
            recovery_log.append(log_entry)
            save_state()
            log(f"Recovery Log updated for TX-{curr_tx:03d} (missed by: {all_down_or_failed})", "WARNING")
        else:
            save_state()
            
    log(f"✅ TX-{curr_tx:03d} hoàn tất. Thành công: {committed_nodes}, Thất bại: {failed_nodes}", "SUCCESS")
    return jsonify({
        "status": "COMMITTED" if committed_nodes else "FAILED",
        "tx_id": curr_tx,
        "committed_to": committed_nodes,
        "failed_nodes": failed_nodes,
        "quantity": committed_new_qty
    })

@app.route("/api/read", methods=["GET"])
def read_transaction():
    node_id = request.args.get("node_id")
    sku = request.args.get("sku", "sku001")
    
    if not node_id or node_id not in NODES:
        return jsonify({"error": "Invalid node_id"}), 400
        
    url = NODES[node_id]
    log(f"📥 COORDINATOR: Reading {sku} from Node {node_id} [ROWA-A: Read One]", "INFO")
    
    try:
        resp = requests.get(f"{url}/read?sku={sku}", timeout=2.0)
        # Directly proxy the exact response from the node
        return (jsonify(resp.json()), resp.status_code)
    except Exception as e:
        log(f"Error reading from node {node_id}: {e}", "ERROR")
        return jsonify({
            "status": "ERROR",
            "error": "Node is unreachable / DOWN."
        }), 503

@app.route("/api/missed-txs", methods=["GET"])
def get_missed_txs():
    node_id = request.args.get("node_id")
    if not node_id:
        return jsonify({"error": "Missing node_id"}), 400
        
    with lock:
        # Find all log entries that this node missed
        missed = []
        for entry in recovery_log:
            if node_id in entry.get("missedBy", []):
                missed.append({
                    "txId": entry["txId"],
                    "sku": entry.get("sku", "sku001"),
                    "oldQty": entry["oldQty"],
                    "newQty": entry["newQty"]
                })
        return jsonify({"missed_txs": missed})

@app.route("/api/node/recovery-complete", methods=["POST"])
def node_recovery_complete():
    global recovery_log
    node_id = request.args.get("node_id")
    if not node_id:
        return jsonify({"error": "Missing node_id"}), 400
        
    with lock:
        # Remove this node from the missed list in all entries
        for entry in recovery_log:
            if node_id in entry.get("missedBy", []):
                entry["missedBy"] = [n for n in entry["missedBy"] if n != node_id]
                
        # Clean up recovery log entries that have no pending down nodes left
        recovery_log = [e for e in recovery_log if len(e.get("missedBy", [])) > 0]
        save_state()
        log(f"Cleaned up recovery logs for Node {node_id}", "SUCCESS")
        return jsonify({"status": "SUCCESS"})

@app.route("/api/node/crash", methods=["POST"])
def crash_node():
    node_id = request.args.get("node_id")
    if not node_id or node_id not in NODES:
        return jsonify({"error": "Invalid node_id"}), 400
        
    url = NODES[node_id]
    try:
        resp = requests.post(f"{url}/crash", timeout=2.0)
        return (jsonify(resp.json()), resp.status_code)
    except Exception as e:
        return jsonify({"error": f"Failed to reach node: {e}"}), 503

@app.route("/api/node/recover", methods=["POST"])
def recover_node():
    node_id = request.args.get("node_id")
    if not node_id or node_id not in NODES:
        return jsonify({"error": "Invalid node_id"}), 400
        
    url = NODES[node_id]
    try:
        resp = requests.post(f"{url}/recover", timeout=2.0)
        return (jsonify(resp.json()), resp.status_code)
    except Exception as e:
        return jsonify({"error": f"Failed to reach node: {e}"}), 503

@app.route("/api/reset", methods=["POST"])
def reset_system():
    global tx_counter, recovery_log
    log("🔄 Resetting Coordinator and all Database Nodes...", "INFO")
    
    with lock:
        tx_counter = 0
        recovery_log = []
        save_state()
        
    # Reset all node servers
    for nid, url in NODES.items():
        try:
            requests.post(f"{url}/reset", timeout=1.5)
        except Exception:
            pass # ignore nodes that are physically stopped
            
    return jsonify({"status": "RESET_SUCCESS"})

# ─────────────────────────────────────────────────────────────────────────────
# START COORDINATOR
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    load_state()
    log(f"Coordinator server starting on port {PORT}...")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)

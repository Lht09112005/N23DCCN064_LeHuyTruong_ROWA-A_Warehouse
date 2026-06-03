# Distributed Database System (ROWA)

This is a demonstration project for a Distributed Database System using the **ROWA (Read One Write All)** protocol. The system consists of a `Coordinator` and multiple distributed `Nodes` (A, B, and C). They communicate over a network using HTTP REST APIs built with Python and Flask.

## Architecture

- **Coordinator (Port 5000):** Manages requests from clients and coordinates transactions/syncs data across the nodes.
- **Node A (Port 5001):** Distributed database node A.
- **Node B (Port 5002):** Distributed database node B.
- **Node C (Port 5003):** Distributed database node C.

## Prerequisites

- **Docker** and **Docker Desktop** (Recommended)
- **Python 3.x** (If running without Docker)

## How to Run (Recommended)

The easiest and most reliable way to run this project is using Docker Compose. This automatically sets up the networking and environment variables for all 4 services.

1. Make sure Docker Desktop is running.
2. Open a terminal in the root directory of this project.
3. Run the following command:

```bash
docker-compose up --build
```

4. Once the containers are up and running, you can access the coordinator and nodes at:
   - Coordinator: `http://localhost:5000`
   - Node A: `http://localhost:5001`
   - Node B: `http://localhost:5002`
   - Node C: `http://localhost:5003`
5. You can also view the frontend UI by opening the `index.html` file in your browser.

## How to Run (Directly without Docker)

If you prefer to run the project natively, you will need to open 4 separate terminals.

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Node A:**
   ```bash
   cd node
   set PORT=5001
   set NODE_ID=A
   python app.py
   ```

3. **Run Node B:**
   ```bash
   cd node
   set PORT=5002
   set NODE_ID=B
   python app.py
   ```

4. **Run Node C:**
   ```bash
   cd node
   set PORT=5003
   set NODE_ID=C
   python app.py
   ```

5. **Run Coordinator:**
   ```bash
   cd coordinator
   set PORT=5000
   set NODE_URLS=A:http://localhost:5001,B:http://localhost:5002,C:http://localhost:5003
   python app.py
   ```

## Testing Concurrency

A test script is provided to simulate concurrent requests and test the system's consistency and lock mechanisms.

Make sure the system is running (either via Docker or natively), then open a new terminal and run:

```bash
python test_concurrency.py
```

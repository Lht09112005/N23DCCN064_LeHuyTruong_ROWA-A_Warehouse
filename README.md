# 🏭 ROWA-A Warehouse Inventory Simulator
### Hệ thống Mô phỏng Kho hàng Phân tán — Giao thức ROWA-Available

> **Đề tài #42 — Môn Cơ sở Dữ liệu Phân tán**  
> Mô phỏng giao thức **ROWA-A (Read-One Write-All Available)** trên hệ thống kho hàng 5 nút phân tán, kết hợp cơ chế WAL, Recovery Log và Stale Read Prevention.

---

## 📐 Kiến trúc hệ thống

```
                    ┌─────────────────────────────┐
   Client / UI ────►│   COORDINATOR  (:5000)       │
                    │   - Điều phối giao dịch       │
                    │   - Quản lý Recovery Log      │
                    │   - Mutex Lock toàn cục       │
                    └────────────┬────────────────┘
                                 │ ROWA-A Write
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
      ┌──────────────┐  ┌──────────────┐   ┌──────────────┐
      │ WHBDG :5001  │  │ WHDPS :5002  │   │ WHJKT :5003  │
      │ Kho Bandung  │  │ Kho Depok    │   │ Kho Jakarta  │
      │  stock.json  │  │  stock.json  │   │  stock.json  │
      │  wal.jsonl   │  │  wal.jsonl   │   │  wal.jsonl   │
      └──────────────┘  └──────────────┘   └──────────────┘
              ┌──────────────────┐
              ▼                  ▼
      ┌──────────────┐  ┌──────────────┐
      │ WHSBY :5004  │  │ WHMDN :5005  │
      │ Kho Surabaya │  │ Kho Medan    │
      │  stock.json  │  │  stock.json  │
      │  wal.jsonl   │  │  wal.jsonl   │
      └──────────────┘  └──────────────┘
```

### 5 Kho hàng (Nodes)

| Container | Node ID | Cổng | Kho |
|---|---|---|---|
| `rowa_coordinator` | — | **:5000** | Trạm điều phối trung tâm |
| `rowa_node_whbdg`  | WHBDG | **:5001** | Kho Bandung |
| `rowa_node_whdps`  | WHDPS | **:5002** | Kho Depok |
| `rowa_node_whjkt`  | WHJKT | **:5003** | Kho Jakarta |
| `rowa_node_whsby`  | WHSBY | **:5004** | Kho Surabaya |
| `rowa_node_whmdn`  | WHMDN | **:5005** | Kho Medan |

---

## 🗂️ Cấu trúc thư mục

```
ROWA-A_Project/
│
├── docker-compose.yml          # Định nghĩa và kết nối 6 container
├── requirements.txt            # Thư viện Python: Flask, requests, flask-cors
├── test_concurrency.py         # Script test đồng thời
│
├── coordinator/
│   ├── Dockerfile
│   ├── app.py                  # Backend Coordinator — ROWA-A, Recovery Log, Lock
│   └── static/
│       └── index.html          # Giao diện điều khiển toàn hệ thống (React)
│
└── node/
    ├── Dockerfile
    ├── app.py                  # Backend Node — WAL, State Machine, Stale Read Prevention
    ├── stock_levels.csv        # Dataset tồn kho khởi tạo
    └── static/
        └── index.html          # Giao diện từng kho hàng (React)
```

---

## ⚙️ Yêu cầu hệ thống

- **Docker Desktop** (khuyến nghị) — [Tải tại đây](https://www.docker.com/products/docker-desktop)
- **Python 3.11+** (nếu chạy không dùng Docker)

---

## 🚀 Khởi động (Khuyến nghị — Docker)

```bash
# 1. Clone repo
git clone https://github.com/Lht09112005/ROWA-A_Project.git
cd ROWA-A_Project

# 2. Khởi động toàn bộ hệ thống (6 container)
docker-compose up -d --build

# 3. Xem log realtime (tuỳ chọn)
docker-compose logs -f
```

Sau khi khởi động, truy cập:

| Giao diện | URL |
|---|---|
| 🖥️ **Coordinator** (Bảng điều khiển chính) | http://localhost:5000 |
| 📦 Kho WHBDG | http://localhost:5001 |
| 📦 Kho WHDPS | http://localhost:5002 |
| 📦 Kho WHJKT | http://localhost:5003 |
| 📦 Kho WHSBY | http://localhost:5004 |
| 📦 Kho WHMDN | http://localhost:5005 |

```bash
# Dừng hệ thống
docker-compose down

# Dừng và xóa toàn bộ dữ liệu
docker-compose down -v
```

---

## 🖥️ Khởi động thủ công (không dùng Docker)

Cài thư viện:
```bash
pip install -r requirements.txt
```

Mở **6 terminal riêng biệt** và chạy lần lượt:

```bash
# Terminal 1 — Kho WHBDG
cd node && set NODE_ID=WHBDG && set PORT=5001 && python app.py

# Terminal 2 — Kho WHDPS
cd node && set NODE_ID=WHDPS && set PORT=5002 && python app.py

# Terminal 3 — Kho WHJKT
cd node && set NODE_ID=WHJKT && set PORT=5003 && python app.py

# Terminal 4 — Kho WHSBY
cd node && set NODE_ID=WHSBY && set PORT=5004 && python app.py

# Terminal 5 — Kho WHMDN
cd node && set NODE_ID=WHMDN && set PORT=5005 && python app.py

# Terminal 6 — Coordinator (khởi động SAU các Node)
cd coordinator
set PORT=5000
set NODE_URLS=WHBDG:http://localhost:5001,WHDPS:http://localhost:5002,WHJKT:http://localhost:5003,WHSBY:http://localhost:5004,WHMDN:http://localhost:5005
python app.py
```

---

## 🔬 Các tính năng có thể demo

| Tính năng | Mô tả |
|---|---|
| **Giao dịch ghi ROWA-A** | Ghi đến tất cả Node UP, bỏ qua Node DOWN |
| **Giả lập sập Node** | Nhấn "Crash" trên giao diện để Node chuyển sang DOWN |
| **Phục hồi WAL** | Nhấn "Recover" — Node tự fetch missed TXs và replay WAL |
| **Stale Read Prevention** | Node RECOVERING từ chối đọc (HTTP 400) |
| **Recovery Log** | Coordinator lưu các TX bị lỡ, tự dọn sau khi Node phục hồi |
| **Proxy Write** | Ghi từ giao diện Node → forward tự động đến Coordinator |

---

## 📊 Tính sẵn sàng lý thuyết

| Giao thức | Công thức | n=5, p=0.9 |
|---|---|---|
| **ROWA chuẩn** | $A = p^n$ | **59.05%** |
| **ROWA-A** | $A = 1-(1-p)^n$ | **99.999% (Five Nines)** |

---

## 🧰 Công nghệ sử dụng

| Lớp | Công nghệ |
|---|---|
| **Backend** | Python 3.11 + Flask 3.0 |
| **Giao tiếp** | HTTP REST API (requests) |
| **Frontend** | React 18 (CDN) + Tailwind CSS |
| **Persistence** | JSON file (`stock.json`, `wal.jsonl`, `coordinator_state.json`) |
| **Containerization** | Docker + Docker Compose |
| **Concurrency** | `threading.Lock()` |

---

## 🧪 Test đồng thời

```bash
# Đảm bảo hệ thống đang chạy trước
python test_concurrency.py
```

Script gửi nhiều request ghi đồng thời để kiểm tra cơ chế Mutex Lock và tính nhất quán dữ liệu.

---

## 📚 Tham chiếu lý thuyết

- **ROWA-A Protocol** — Özsu & Valduriez, §6.3 / §14.4
- **Write-Ahead Logging** — Özsu & Valduriez, §5.4
- **Stale Read Prevention** — Özsu & Valduriez, §14.5.3
- **1-Copy Serializability** — Özsu & Valduriez, §6.1

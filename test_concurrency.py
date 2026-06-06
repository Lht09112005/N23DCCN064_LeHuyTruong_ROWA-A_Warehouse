import requests
import threading
import time

COORDINATOR_URL = "http://localhost:5000"

def get_current_sku_qty(sku):
    try:
        res = requests.get(f"{COORDINATOR_URL}/api/status")
        data = res.json()
        # Find quantity in node A's dataset
        dataset = data["nodes"]["WHBDG"].get("dataset", [])
        for item in dataset:
            if item["SKU"] == sku:
                return item["Quantity"]
    except Exception as e:
        print("Error fetching status:", e)
    return 0

def send_write_request(thread_name, sku, old_qty, increment):
    new_qty = old_qty + increment
    print(f"[{thread_name}] Đang gửi yêu cầu: old_qty={old_qty}, +{increment} => new_qty={new_qty}")
    
    payload = {
        "sku": sku,
        "delta": increment
    }
    
    start_time = time.time()
    res = requests.post(f"{COORDINATOR_URL}/api/write", json=payload)
    elapsed = time.time() - start_time
    
    if res.status_code == 200:
        print(f"[{thread_name}] THÀNH CÔNG (mất {elapsed:.3f}s)")
    else:
        print(f"[{thread_name}] THẤT BẠI: {res.text}")

if __name__ == "__main__":
    target_sku = "SKU0001"
    
    print("=== BÀI TEST LOST UPDATE (CONCURRENCY) ===")
    
    # 1. Lấy số lượng hiện tại
    current_qty = get_current_sku_qty(target_sku)
    print(f"\nSố lượng hiện tại của {target_sku} là: {current_qty}")
    print("Dự kiến:")
    print(f"  - Thread A muốn cộng +5  => Kì vọng: {current_qty + 5}")
    print(f"  - Thread B muốn cộng +10 => Kì vọng: {current_qty + 10}")
    print(f"  - Tổng kì vọng sau cùng  => PHẢI LÀ: {current_qty + 15}")
    
    print("\nBắn 2 request cùng LÚC (cách nhau 0.001s)...")
    
    # 2. Tạo 2 thread chạy song song
    thread_a = threading.Thread(target=send_write_request, args=("Thread A", target_sku, current_qty, 5))
    thread_b = threading.Thread(target=send_write_request, args=("Thread B", target_sku, current_qty, 10))
    
    thread_a.start()
    thread_b.start()
    
    thread_a.join()
    thread_b.join()
    
    # 3. Chờ đồng bộ và kiểm tra kết quả
    time.sleep(1)
    final_qty = get_current_sku_qty(target_sku)
    
    print("\n=== KẾT QUẢ ===")
    print(f"Số lượng thực tế sau cập nhật: {final_qty}")
    if final_qty == (current_qty + 15):
        print("=> Hệ thống an toàn (Không bị lỗi Lost Update).")
    else:
        print(f"=> CẢNH BÁO: Lỗi Lost Update đã xảy ra! Một trong hai giao dịch đã bị ghi đè.")

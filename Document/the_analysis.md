# THE ANALYSIS: A REPORT JUSTIFYING DESIGN CHOICES USING ÖZSU AND VALDURIEZ THEORY
**HỆ THỐNG MÔ PHỎNG KHO HÀNG PHÂN TÁN NHÂN BẢN ROWA-AVAILABLE (ROWA-A)**

* **Môn học:** Cơ sở Dữ liệu Phân tán (Distributed Database Systems)
* **Chủ đề nghiên cứu:** Phân tích học thuật và biện minh các quyết định thiết kế hệ thống cơ sở dữ liệu phân tán dựa trên khung lý thuyết của **M. Tamer Özsu và Patrick Valduriez** (*Principles of Distributed Database Systems*, 4th Edition, 2020).
* **Đề tài áp dụng:** Đề tài số 42 - Hệ thống Mô phỏng Quản lý Tồn kho Kho hàng Phân tán.

---

## MỤC LỤC (TABLE OF CONTENTS)
1. **CHƯƠNG 1: GIỚI THIỆU & TỔNG QUAN DỰ ÁN**
2. **CHƯƠNG 2: KIẾN TRÚC CƠ SỞ DỮ LIỆU PHÂN TÁN (DISTRIBUTED DBMS ARCHITECTURE)**
3. **CHƯƠNG 3: THIẾT KẾ PHÂN MẢNH & PHÂN BỔ DỮ LIỆU (FRAGMENTATION & DATA ALLOCATION)**
4. **CHƯƠNG 4: GIAO THỨC NHÂN BẢN DỮ LIỆU: STANDARD ROWA VS. ROWA-AVAILABLE (ROWA-A)**
5. **CHƯƠNG 5: ĐIỀU PHỐI GIAO DỊCH PHÂN TÁN & THUỘC TÍNH ACID**
6. **CHƯƠNG 6: ĐỘ TIN CẬY & GIAO THỨC KHÔI PHỤC PHÂN TRẠM (SITE RECOVERY PROTOCOL)**
7. **CHƯƠNG 7: NGĂN CHẶN ĐỌC DỮ LIỆU CŨ (STALE READ PREVENTION)**
8. **CHƯƠNG 8: KIỂM SOÁT ĐỒNG THỜI & AN TOÀN ĐA LUỒNG (CONCURRENCY CONTROL & THREAD SAFETY)**
9. **CHƯƠNG 9: PHÂN TÍCH HỆ THỐNG THEO ĐỊNH LÝ CAP (CAP THEOREM ANALYSIS)**
10. **CHƯƠNG 10: TỔNG KẾT ĐÁNH GIÁ THIẾT KẾ & BẢNG ĐỐI CHIẾU LÝ THUYẾT - THỰC TIỄN**
11. **TÀI LIỆU THAM KHẢO (REFERENCES)**

---

## CHƯƠNG 1: GIỚI THIỆU & TỔNG QUAN DỰ ÁN

### 1.1. Tóm tắt dự án (Executive Summary)
Báo cáo này trình bày phân tích học thuật chuyên sâu và biện minh kỹ thuật cho các quyết định thiết kế hệ thống trong **Hệ thống Mô phỏng Kho hàng Phân tán ROWA-A (Read-Once Write-All Available)**. Hệ thống được phát triển nhằm mô phỏng và giải quyết các thách thức thực tế trong việc quản lý tồn kho tại các chuỗi bán lẻ đa chi nhánh. 

Mục tiêu cốt lõi của hệ thống là cung cấp khả năng truy xuất dữ liệu tồn kho với độ trễ cực thấp tại địa phương, đồng thời đảm bảo tính sẵn sàng ghi cao khi mạng hoặc các phân trạm cục bộ gặp sự cố. Bằng cách áp dụng các nguyên lý phân tán kinh điển từ giáo trình của **M. Tamer Özsu và Patrick Valduriez**, chúng tôi đã xây dựng một nền tảng mô phỏng trực quan minh họa các cơ chế phức tạp như kiểm soát nhân bản, phục hồi lỗi trạm, đồng bộ hóa nhật ký và ngăn chặn hiện tượng đọc dữ liệu cũ (stale read).

### 1.2. Mô tả hệ thống & Kiến trúc tổng thể (System Description)
Hệ thống mô phỏng bao gồm hai thành phần phần mềm chính được container hóa hoàn toàn bằng Docker:
1. **Bộ điều phối trung tâm (Coordinator):** Đóng vai trò là cổng giao tiếp duy nhất (Single Entry Point) cho các giao dịch phân tán từ phía khách hàng. Coordinator chịu trách nhiệm định tuyến các yêu cầu đọc/ghi, theo dõi trạng thái sống sót của các phân trạm, duy trì nhật ký phục hồi tập trung và điều phối quá trình catch-up.
2. **Các Phân trạm Bản sao (Nodes A, B, C):** Đại diện cho 3 kho hàng vật lý phân tán địa lý độc lập. Mỗi phân trạm chạy một máy chủ độc lập lưu trữ bản sao dữ liệu của bảng tồn kho, tích hợp bộ ghi nhật ký WAL (Write-Ahead Logging) cục bộ và duy trì một máy trạng thái (State Machine) điều chỉnh khả năng phục vụ tùy theo trạng thái nội tại (`UP`, `DOWN`, `RECOVERING`).

Giao diện người dùng Web (Frontend) được thiết kế hiện đại, mô phỏng trực quan thời gian thực các luồng truyền thông điệp HTTP REST API giữa các thành phần, cho phép người dùng chủ động "đánh sập" (Crash) hoặc "phục hồi" (Recover) các phân trạm để quan sát hành vi của hệ thống dưới các kịch bản lỗi khác nhau.

```
                  ┌───────────────────────────────┐
                  │      Ứng dụng Client (Web)    │
                  └───────────────┬───────────────┘
                                  │ Yêu cầu API
                                  ▼
                  ┌───────────────────────────────┐
                  │     Bộ điều phối tập trung    │
                  │         (Coordinator)         │
                  └──────┬────────┬────────┬──────┘
            HTTP /read   │        │        │ HTTP /write
            HTTP /recover│        │        │ HTTP /status
                         ▼        ▼        ▼
                      ┌─────┐  ┌─────┐  ┌─────┐
                      │Node │  │Node │  │Node │
                      │  A  │  │  B  │  │  C  │
                      └─────┘  └─────┘  └─────┘
```

### 1.3. Lược đồ quan hệ và kiểu dữ liệu (Relational Schema)
Hệ thống lưu trữ và quản lý tập dữ liệu quan hệ của bảng tồn kho sản phẩm, được ký hiệu là $Stock\_Levels$. Lược đồ quan hệ chính thức của bảng được định nghĩa như sau:

$$\text{Stock\_Levels}(\underline{\text{SKU}}, \text{Quantity}, \text{WarehouseID})$$

Trong đó:
* $\text{SKU}$ (Stock Keeping Unit - String, Khóa chính): Mã định danh duy nhất cho từng mặt hàng (ví dụ: `sku001`, `sku002`, `sku003`).
* $\text{Quantity}$ (Integer): Số lượng tồn kho thực tế của mặt hàng đó (không được phép âm, $\ge 0$).
* $\text{WarehouseID}$ (String): Mã định danh kho hàng vật lý nơi mặt hàng đó được lưu trữ (tương ứng với ID của phân trạm bản sao: `A`, `B`, `C`).

Hệ thống lưu trữ tập dữ liệu này dưới dạng một mảng JSON có cấu trúc trong tệp tin cơ sở dữ liệu vật lý cục bộ `stock.json` tại thư mục `/app/data/` của mỗi container Node.

---

## CHƯƠNG 2: KIẾN TRÚC CƠ SỞ DỮ LIỆU PHÂN TÁN (DISTRIBUTED DBMS ARCHITECTURE)

### 2.1. Phân loại hệ thống theo Taxonomy của Özsu & Valduriez
Dựa trên phân loại hệ quản trị cơ sở dữ liệu phân tán (DDBMS) được trình bày trong **Chương 1 và Chương 4 (Özsu & Valduriez)**, hệ thống mô phỏng của chúng tôi được định danh chính xác là:
* **Hệ thống phân tán đồng nhất (Homogeneous Distributed Database System):** Tất cả các phân trạm hạ nguồn (Node A, B, C) đều sử dụng chung một mã nguồn chạy ứng dụng Flask Python, chia sẻ cùng một mô hình lưu trữ dữ liệu (JSON File Store) và tuân thủ các quy tắc xử lý cục bộ đồng nhất.
* **Hệ thống nhân bản hoàn toàn (Fully Replicated System):** Mỗi phân trạm lưu trữ một bản sao đầy đủ của toàn bộ quan hệ $Stock\_Levels$ đối với tất cả các SKU.
* **Hệ thống phân tán có kiểm soát tập trung (Client/Server with Centralized Coordinator):** Việc điều phối giao dịch toàn cục và duy trì trạng thái hệ thống được giao cho một bộ điều phối trung tâm chuyên biệt.

### 2.2. Các loại tính trong suốt (Transparency Layers)
Sách giáo khoa *Principles of Distributed Database Systems* định nghĩa tính trong suốt (Transparency) là sự che giấu các chi tiết thiết kế và vật lý của hệ thống phân tán đối với người dùng hoặc ứng dụng client. Trong dự án này, chúng tôi đã hiện thực hóa 3 lớp trong suốt quan trọng:

1. **Trong suốt mạng (Network/Distribution Transparency):** Người dùng khi tương tác thông qua giao diện Web hoặc ứng dụng khách chỉ cần gửi yêu cầu ghi/đọc đến một địa điểm duy nhất (Coordinator). Họ hoàn toàn không cần biết địa chỉ IP, cổng (port), hay giao thức mạng của từng phân trạm Node A, B, C. Coordinator tự động phân tích cú pháp và chuyển hướng các yêu cầu HTTP.
2. **Trong suốt nhân bản (Replication Transparency):** Khi thực hiện cập nhật tồn kho (ví dụ: cộng thêm 10 Laptop vào hệ thống), client không cần phát hành các lệnh cập nhật riêng lẻ đến từng phân trạm. Họ chỉ gửi một giao dịch cập nhật duy nhất, và hệ thống tự động đồng bộ hóa bản sao trên tất cả các phân trạm đang hoạt động mà client không hề nhận biết.
3. **Trong suốt phân mảnh (Fragmentation Transparency):** Dù dữ liệu được lưu trữ trên nhiều trạm vật lý độc lập dưới định danh `WarehouseID` tương ứng, client vẫn nhìn thấy một bảng dữ liệu logic thống nhất và tương tác với nó như một cơ sở dữ liệu tập trung.

### 2.3. Kiến trúc Client/Server và Biện minh mô hình Coordinator tập trung
Trong **Chương 4**, Özsu và Valduriez trình bày nhiều cấu trúc kiến trúc khác nhau, bao gồm Peer-to-Peer (P2P), Multi-DBMS và Client/Server. Hệ thống mô phỏng này lựa chọn kiến trúc **Client/Server với Coordinator tập trung**.

#### Biện minh cho quyết định thiết kế:
* **Đơn giản hóa việc quản lý đồng thuận:** Thay vì yêu cầu các phân trạm tự trao đổi chéo (Peer-to-Peer) để đạt được đồng thuận ghi - một cơ chế rất dễ phát sinh deadlock phân tán và trễ mạng cực cao, Coordinator đóng vai trò là trọng tài tối cao quyết định thứ tự tuần tự hóa (serialization order) của các giao dịch toàn cục.
* **Tránh Deadlock phân tán (Distributed Deadlock Prevention):** Mọi giao dịch ghi đều được Coordinator sắp hàng và khóa tuần tự thông qua một cơ chế Mutex Lock toàn cục (`threading.Lock()`). Điều này triệt tiêu hoàn toàn khả năng phát sinh chu trình đợi khóa chéo giữa các phân trạm khác nhau (ví dụ: Node A đợi Node B trong khi Node B đợi Node A).
* **Tối ưu hóa tài nguyên phần cứng trạm:** Các Node hạ nguồn không cần phải duy trì các tiến trình quản lý giao dịch toàn cục phức tạp hay lưu trữ thông tin cấu hình của các node khác, chúng chỉ cần tập trung thực thi các tác vụ đọc/ghi thô tại địa phương và báo cáo trạng thái.

---

## CHƯƠNG 3: THIẾT KẾ PHÂN MẢNH & PHÂN BỔ DỮ LIỆU (FRAGMENTATION & DATA ALLOCATION)

### 3.1. Nhân bản hoàn toàn (Full Replication) vs. Nhân bản từng phần (Partial Replication)
Dựa theo lý thuyết thiết kế cơ sở dữ liệu phân tán tại **Chương 2 (Özsu & Valduriez)**, có ba chiến lược phân bổ dữ liệu chính: Không nhân bản (Non-replicated), Nhân bản một phần (Partially Replicated), và Nhân bản hoàn toàn (Fully Replicated).

Hệ thống của chúng tôi lựa chọn **Nhân bản hoàn toàn (Full Replication)**. Mỗi phân trạm (Node A, B, C) lưu trữ toàn bộ dữ liệu của bảng $Stock\_Levels$ cho tất cả các kho hàng.

#### Biện minh khoa học cho sự lựa chọn này:
* **Tối đa hóa hiệu năng đọc (Read Performance Optimization):** Trong các hệ thống bán lẻ và quản lý kho hàng, tần suất các giao dịch truy vấn tồn kho (Read) thường vượt trội hơn nhiều so với tần suất giao dịch cập nhật (Write) (tỷ lệ ước tính khoảng 90:10). Với nhân bản hoàn toàn, bất kỳ yêu cầu đọc nào cũng có thể được đáp ứng ngay lập tức tại phân trạm cục bộ mà không cần truy cập qua đường truyền WAN liên mạng.
* **Tăng cường tính sẵn sàng và khả năng sống sót (Fault Tolerance):** Nếu hai trong ba phân trạm bị sập hoàn toàn do thảm họa vật lý hoặc sự cố mạng, phân trạm duy nhất còn lại vẫn chứa đầy đủ thông tin để phục vụ khách hàng tra cứu và cập nhật dữ liệu, đảm bảo tính liên tục của hoạt động kinh doanh.

### 3.2. Phân tích chiến lược phân bổ dữ liệu (Allocation Strategy) và Tính kinh tế
Định lượng phân bổ dữ liệu trong **Mục §2.2 (Özsu & Valduriez)** thường dựa trên việc tối thiểu hóa hàm chi phí truyền thông và tối đa hóa hiệu năng. 

Gọi $C_{\text{read}}(x)$ là chi phí truyền thông khi thực hiện một thao tác đọc trên dữ liệu $x$, và $C_{\text{write}}(x)$ là chi phí truyền thông khi ghi trên dữ liệu $x$. 
* Trong mô hình **Không nhân bản**, nếu dữ liệu lưu tại trạm $i$, một truy vấn từ trạm $j$ ($j \neq i$) sẽ tốn chi phí mạng:

  $$\text{Cost} = C_{\text{network}}(j \to i)$$

* Trong mô hình **Nhân bản hoàn toàn**, chi phí đọc tại chỗ (local read) giảm về 0:

  $$C_{\text{read, local}} \approx 0$$

  Tuy nhiên, chi phí ghi tăng lên vì phải cập nhật trên mọi phân trạm:

  $$C_{\text{write, global}} = \sum_{k=1}^{n} C_{\text{network}}(\text{origin} \to k)$$

Với mô hình kinh doanh kho hàng vật lý, các quản lý chi nhánh thường xuyên tra cứu tồn kho liên tục (độ trễ yêu cầu $< 50\text{ms}$). Do đó, việc chấp nhận chi phí mạng cao hơn cho tác vụ ghi để đổi lấy độ trễ đọc tối thiểu và tính độc lập của từng chi nhánh là hoàn toàn hợp lý về mặt kinh tế và trải nghiệm người dùng.

### 3.3. Sự đánh đổi (Trade-off) giữa Read Availability và Update Cost
Thiết kế này thể hiện một sự đánh đổi kinh điển trong phân tán dữ liệu:

| Chỉ số so sánh | Nhân bản hoàn toàn (Được lựa chọn) | Nhân bản một phần / Không nhân bản |
| :--- | :--- | :--- |
| **Read Availability** | **Cực cao ($O(1)$)**. Bất kỳ node nào hoạt động cũng đọc được ngay lập tức. | **Trung bình/Thấp**. Phải định tuyến yêu cầu đến node chứa mảnh dữ liệu. |
| **Read Latency** | **Cực thấp**. Truy xuất trực tiếp từ file JSON cục bộ. | **Cao**. Phụ thuộc độ trễ đường truyền mạng liên phân trạm. |
| **Update Cost** | **Cao ($O(n)$)**. Phải truyền lệnh ghi đến toàn bộ $n$ phân trạm trong mạng. | **Thấp**. Chỉ cần ghi trên một hoặc một nhóm nhỏ phân trạm. |
| **Storage Overhead** | **Cao**. Dữ liệu bị trùng lặp $n$ lần trên hệ thống. | **Thấp**. Dữ liệu được chia nhỏ và phân bổ tối ưu. |

Vì dung lượng dữ liệu tồn kho kho hàng là tương đối nhỏ (chỉ vài trăm nghìn SKU, dung lượng đĩa cứng tốn vài Megabyte), chi phí lưu trữ (Storage Overhead) là không đáng kể so với lợi ích to lớn về tốc độ truy xuất. Do đó, hệ thống chọn Nhân bản hoàn toàn để đạt tối đa hiệu năng đọc.

---

## CHƯƠNG 4: GIAO THỨC NHÂN BẢN DỮ LIỆU: STANDARD ROWA VS. ROWA-AVAILABLE (ROWA-A)

### 4.1. Giao thức ROWA truyền thống (Standard ROWA Protocol)
Theo lý thuyết quản lý nhân bản trong **Chương 6 (Özsu & Valduriez)**, giao thức **Read-One Write-All (ROWA)** quy định:
* **Tác vụ Đọc ($R(x)$):** Bộ điều phối chỉ cần chuyển yêu cầu đọc dữ liệu $x$ đến **một bản sao bất kỳ** khả dụng. Độ phức tạp thông điệp mạng là $O(1)$.
* **Tác vụ Ghi ($W(x)$):** Giao dịch phải cập nhật dữ liệu thành công trên **tất cả** các bản sao vật lý của $x$ trước khi được trả kết quả cam kết toàn cục. Độ phức tạp thông điệp mạng là $O(n)$.

#### Phân tích toán học về Tính sẵn sàng ghi (Write Availability) của ROWA chuẩn:
Giả sử hệ thống có $n$ phân trạm độc lập, mỗi phân trạm có xác suất hoạt động bình thường (UP) tại thời điểm bất kỳ là $p_i$ ($0 < p_i < 1$).
Tính sẵn sàng ghi của hệ thống ROWA chuẩn ($A_{\text{write, ROWA}}$) phụ thuộc vào sự sống sót của **tất cả** các trạm:

$$A_{\text{write, ROWA}} = \prod_{i=1}^{n} p_i$$

Nếu hệ thống có 3 phân trạm với độ tin cậy trung bình của mỗi phân trạm là $p_i = 0.90$ ($90\%$):

$$A_{\text{write, ROWA}} = 0.90 \times 0.90 \times 0.90 = 0.729 \quad (72.9\%)$$

Điều này chỉ ra rằng hệ thống sẽ bị **từ chối ghi** tới $27.1\%$ thời gian hoạt động, chỉ vì một trong các phân trạm gặp sự cố mất điện hoặc lỗi mạng tạm thời. Đây là điểm yếu chí tử của ROWA chuẩn trong môi trường mạng thực tế.

### 4.2. Giải pháp Thiết kế cải tiến: ROWA-Available (ROWA-A)
Để khắc phục nhược điểm nghiêm trọng trên mà vẫn giữ nguyên ưu điểm đọc tại chỗ cực nhanh của ROWA, hệ thống mô phỏng hiện thực hóa giao thức **ROWA-Available (ROWA-A)** (được thảo luận chi tiết trong giáo trình **Mục §6.3 / §14.4 cũ**).

#### Nguyên lý hoạt động của ROWA-A:
1. Khi nhận yêu cầu ghi, Coordinator tự động kiểm tra trạng thái hoạt động thực tế của tất cả các phân trạm trong mạng qua cơ chế ping.
2. Coordinator chia danh sách trạm thành hai tập hợp:
   * Tập hợp trạm khả dụng: $V = \{ \text{Node}_k \mid \text{Node}_k \text{ hoạt động bình thường (UP/SYNCED)} \}$
   * Tập hợp trạm không khả dụng: $D = \{ \text{Node}_m \mid \text{Node}_m \text{ đã sập (DOWN/RECOVERING)} \}$
3. Giao dịch ghi được gửi đi và thực thi đồng thời trên **tất cả các trạm thuộc tập hợp $V$**.
4. Nếu tất cả các trạm trong $V$ xác nhận ghi thành công (COMMITTED cục bộ), Coordinator sẽ xác nhận giao dịch **COMMITTED toàn cục** và trả kết quả thành công về cho khách hàng.
5. Đối với các trạm thuộc tập hợp $D$, Coordinator tạm thời bỏ qua (bypass), đồng thời ghi lại vết thay đổi dữ liệu vào nhật ký phục hồi tập trung để thực hiện đồng bộ lại sau khi các trạm này khởi động lại.

#### Phân tích toán học về Tính sẵn sàng ghi của ROWA-A:
Trong hệ thống ROWA-A, một giao dịch ghi chỉ bị hủy bỏ (ABORTED) khi và chỉ khi **tất cả** các phân trạm bản sao trong hệ thống đều bị sập đồng thời. Do đó, tính sẵn sàng ghi ($A_{\text{write, ROWA-A}}$) được tính bằng công thức:

$$A_{\text{write, ROWA-A}} = 1 - \prod_{i=1}^{n} (1 - p_i)$$

Với hệ thống 3 phân trạm có độ tin cậy $p_i = 0.90$:

$$A_{\text{write, ROWA-A}} = 1 - (1 - 0.90)^3 = 1 - (0.10)^3 = 1 - 0.001 = 0.999 \quad (99.9\%)$$

##### So sánh trực quan:
* Tính sẵn sàng ghi ROWA chuẩn: **$72.9\%$** (Hệ thống ngừng hoạt động ghi thường xuyên).
* Tính sẵn sàng ghi ROWA-A: **$99.9\%$** (Hệ thống gần như hoạt động ghi liên tục, khả năng chịu lỗi cực tốt).

### 4.3. Đối chiếu mã nguồn thực tế (Coordinator/app.py - /api/write)
Cơ chế động của ROWA-A được triển khai chính xác trong hàm `write_transaction()` của Coordinator tại tệp tin [app.py](file:///c:/Users/ACER/OneDrive/Documents/Máy tính/DEMO CSDLPT/coordinator/app.py#L103-L204):

```python
# 1. Xác định các node đang hoạt động thực tế (Tập hợp V)
available_nodes = []
down_nodes = []

for nid, url in NODES.items():
    try:
        resp = requests.get(f"{url}/status", timeout=1.0)
        # Chỉ chấp nhận ghi lên các Node có trạng thái UP hoặc SYNCED
        if resp.status_code == 200 and resp.json().get("status") in ["UP", "SYNCED"]:
            available_nodes.append(nid)
        else:
            down_nodes.append(nid)
    except Exception:
        down_nodes.append(nid)
        
# Nếu không còn bất kỳ node nào sống sót, giao dịch bắt buộc phải hủy
if not available_nodes:
    with lock:
        tx_counter -= 1 # Hoàn trả mã giao dịch
    return jsonify({"status": "ABORTED", "error": "No nodes available"}), 503

# 2. Thực hiện ghi đồng thời lên các node thuộc tập khả dụng (V)
committed_nodes = []
failed_nodes = []
for nid in available_nodes:
    try:
        resp = requests.post(f"{NODES[nid]}/write", json=payload, timeout=2.0)
        if resp.status_code == 200 and resp.json().get("status") == "COMMITTED":
            committed_nodes.append(nid)
        else:
            failed_nodes.append(nid)
    except Exception:
        failed_nodes.append(nid)
```

Đoạn code trên chứng minh sự tuân thủ tuyệt đối đối với giao thức ROWA-A: hệ thống tự thích ứng linh hoạt, không bị chặn đứng bởi bất kỳ node lỗi đơn lẻ nào, đảm bảo tính liên tục của luồng nghiệp vụ.

---

## CHƯƠNG 5: ĐIỀU PHỐI GIAO DỊCH PHÂN TÁN & THUỘC TÍNH ACID

### 5.1. Quản lý giao dịch tập trung (Centralized Transaction Management)
Trong hệ thống của chúng tôi, **Coordinator** đảm nhận vai trò của một **Bộ quản lý giao dịch tập trung (Centralized Transaction Manager)**. Dựa theo mô hình trừu tượng của Özsu & Valduriez (Fig 5.2), Coordinator chịu trách nhiệm:
1. Tiếp nhận yêu cầu giao dịch `Begin_transaction` (mô phỏng thông qua việc tự động tăng biến đếm `tx_counter` toàn cục).
2. Quyết định thứ tự thực thi toàn cục của giao dịch để đảm bảo tính khả tuần tự (Serializability).
3. Đóng vai trò là trung gian hòa giải thực thi giữa các Scheduler cục bộ tại từng Node.

### 5.2. Đảm bảo các thuộc tính ACID trong môi trường phân tán
Duy trì thuộc tính ACID (Atomicity, Consistency, Isolation, Durability) là thách thức lớn nhất của cơ sở dữ liệu phân tán. Hệ thống ROWA-A thực hiện điều này như sau:

* **Tính nguyên tố (Atomicity):** Trong ROWA-A, tính nguyên tố toàn cục được định nghĩa theo một cách linh hoạt (relaxed atomicity): một giao dịch ghi được coi là Atomicity nếu nó được thực thi trọn vẹn trên **tất cả các node đang hoạt động tại thời điểm đó (Tập hợp $V$)**. Đối với các node sập, tính nguyên tố được bù đắp thông qua cơ chế lưu vết Recovery Log tập trung và replay lại đầy đủ khi node khởi động lại.
* **Tính nhất quán (Consistency):** Hệ thống đảm bảo tính nhất quán Một Bản Sao (1-Copy Equivalence). Khi một giao dịch commit thành công, tất cả các phân trạm hoạt động đều có giá trị tồn kho hoàn toàn khớp nhau đối với sản phẩm đó.
* **Tính độc lập (Isolation):** Mỗi giao dịch ghi hoặc phục hồi đều được bảo vệ trong một phạm vi loại trừ tương hỗ cục bộ và toàn cục thông qua khóa `threading.Lock()`, ngăn chặn hiện tượng tranh chấp ghi chéo (Write-Write Conflict) hay đọc dữ liệu chưa commit.
* **Tính bền vững (Durability):** 
  * Tại **Coordinator**: Trạng thái phục hồi và biến đếm giao dịch được lưu bền vững vào file `coordinator_state.json` thông qua lệnh `save_state()` ngay sau mỗi giao dịch ghi.
  * Tại **Nodes**: Dữ liệu tồn kho được lưu trực tiếp vào ổ đĩa vật lý cục bộ qua tệp tin `stock.json` và log WAL bền vững `wal.jsonl`.

### 5.3. Giao thức cam kết nguyên tử (Atomic Commit Protocol): So sánh 1PC vs. 2PC
Giáo trình **Chương 5 (Mục §5.4.1)** phân tích sâu sắc về **Giao thức cam kết hai pha (Two-Phase Commit - 2PC)** bao gồm pha chuẩn bị (Prepare Phase) và pha cam kết (Commit Phase).

#### Tại sao chúng tôi không sử dụng 2PC chuẩn mà thiết kế cơ chế Cam kết Một Pha Phục hồi (1-Phase Commit with Recovery Log)?
Trong môi trường mạng phân tán có độ trễ cao hoặc các dịch vụ siêu nhẹ, 2PC chuẩn gặp phải các nhược điểm chí tử:
1. **Tính chất chặn (Blocking Protocol):** Nếu Coordinator bị sập ngay sau khi gửi thông điệp `Prepare` và trước khi gửi thông điệp `Commit`, tất cả các Node hạ nguồn sẽ bị rơi vào trạng thái lấp lửng (uncertain state). Chúng phải giữ nguyên các khóa ghi và tài nguyên hệ thống, gây tắc nghẽn toàn bộ cơ sở dữ liệu cho đến khi Coordinator sống lại.
2. **Chi phí truyền thông mạng cực kỳ lớn:** Một giao dịch 2PC chuẩn cần tối thiểu $3n$ thông điệp mạng trao đổi qua lại giữa Coordinator và các trạm:

   $$\text{Total Messages} = 3 \times n$$

   Điều này làm tăng đáng kể độ trễ giao dịch (Write Latency).

#### Giải pháp dung hòa được hiện thực hóa trong dự án:
Chúng tôi triển khai giao thức **Cam kết Một Pha kết hợp Nhật ký Phục hồi Tập trung (Centralized Recovery Log)**. 
Coordinator gửi lệnh ghi trực tiếp đến các node đang chạy. Nếu trạm phản hồi thành công, giao dịch commit ngay tại trạm đó. Nếu trạm gặp lỗi hoặc không phản hồi trong khoảng thời gian timeout ($1.0\text{s}$), Coordinator lập tức lưu cấu trúc nhật ký lỗi bền vững:

$$\text{Recovery\_Entry} = \langle \text{txId}, \text{sku}, \text{oldQty}, \text{newQty}, \text{missedBy}, \text{appliedTo} \rangle$$

Mã nguồn thực tế tại Coordinator ghi nhận tệp nhật ký phục hồi này thông qua [coordinator/app.py](file:///c:/Users/ACER/OneDrive/Documents/Máy tính/DEMO CSDLPT/coordinator/app.py#L180-L195):

```python
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
        save_state() # Ghi bền vững xuống coordinator_state.json
```

Cơ chế này giúp hệ thống **hoàn toàn phi chặn (non-blocking)**. Nếu một node bị sập, các node khác vẫn thực thi bình thường và giải phóng khóa ngay lập tức, tối ưu hóa tối đa hiệu năng hệ thống mà vẫn bảo toàn khả năng khôi phục toàn vẹn dữ liệu.

---

## CHƯƠNG 6: ĐỘ TIN CẬY & GIAO THỨC KHÔI PHỤC PHÂN TRẠM (SITE RECOVERY PROTOCOL)

### 6.1. Nguyên tắc Write-Ahead Logging (WAL) cục bộ tại Node
Theo lý thuyết về độ tin cậy cục bộ tại **Mục §5.4 / §14.2 cũ (Özsu & Valduriez)**, nguyên tắc **Write-Ahead Logging (WAL)** là nền tảng cốt lõi của tính bền vững hệ quản trị cơ sở dữ liệu.

> **Quy tắc WAL:** Nhật ký ghi nhận mọi thay đổi trạng thái dữ liệu (Log Entry) bắt buộc phải được ghi xuống thiết bị lưu trữ bền vững (Non-volatile Storage - ví dụ như SSD/HDD) trước khi trang dữ liệu thực tế trong file cơ sở dữ liệu chính được sửa đổi.

Trong mã nguồn [node/app.py](file:///c:/Users/ACER/OneDrive/Documents/Máy tính/DEMO CSDLPT/node/app.py#L248-L254), quy tắc WAL được tuân thủ nghiêm ngặt:

```python
# 1. Ghi vào tệp nhật ký WAL trước (wal.jsonl)
write_wal(tx_id, sku, old_qty, new_qty)

# 2. Sau đó mới cập nhật vào bộ nhớ RAM và ghi file database (stock.json)
update_stock_quantity(sku, new_qty)
last_tx_id = tx_id
save_stock()
```

#### Phân tích vai trò của WAL trong kịch bản lỗi sập trạm đột ngột:
Nếu trạm Node A bị sập nguồn đột ngột ngay tại thời điểm đang cập nhật file cơ sở dữ liệu `stock.json`, tệp tin này có thể bị hỏng (corruption) hoặc chứa dữ liệu không hoàn chỉnh. 

Khi Node A khởi động lại, quy trình khôi phục cục bộ của nó sẽ tự động đọc lại tệp tin nhật ký WAL `wal.jsonl` (vốn được đảm bảo ghi an toàn trước đó) để thực thi lại các giao dịch thành công (**REDO Phase**) và đưa cơ sở dữ liệu cục bộ về trạng thái nhất quán và an toàn gần nhất.

### 6.2. Quy trình Phục hồi Catch-up từ Coordinator (Reconciliation Phase)
Khi một phân trạm kết nối lại hệ thống sau sự cố và chuyển trạng thái từ `DOWN` sang `RECOVERING`, nó không thể lập tức phục vụ các yêu cầu của client vì dữ liệu của nó đang bị lệch pha (stale) so với toàn cục. Nó bắt buộc phải trải qua giao thức phục hồi phân tán gồm 3 bước:

#### Bước 1: Kéo giao dịch lỡ (Fetch Phase)
Node gửi yêu cầu GET lên Coordinator qua API `/api/missed-txs?node_id=NODE_ID`. Coordinator quét qua danh sách `recovery_log` lưu tại đĩa cứng, trích xuất tất cả các giao dịch mà Node đó đã bỏ lỡ trong thời gian nằm ở trạng thái DOWN (các entry chứa `NODE_ID` trong mảng `missedBy`).

#### Bước 2: Tái hiện tuần tự (Log Replay Phase)
Node nhận về danh sách các giao dịch lỡ dưới dạng mảng JSON. Trạm thực hiện duyệt qua mảng dữ liệu này tuần tự theo thứ tự tăng dần của chỉ số giao dịch `txId` (đảm bảo tính tuần tự nghiêm ngặt - FIFO). Tại mỗi giao dịch, Node ghi nhật ký WAL cục bộ và gọi hàm `update_stock_quantity()` để cập nhật dữ liệu tồn kho vật lý.

#### Bước 3: Xác nhận hoàn tất (Completion Phase)
Sau khi replay thành công toàn bộ các giao dịch lỡ, Node gửi một yêu cầu xác nhận POST lên Coordinator qua API `/api/node/recovery-complete?node_id=NODE_ID`. Coordinator tiến hành loại bỏ `NODE_ID` khỏi thuộc tính `missedBy` của tất cả các bản ghi nhật ký. Nếu một bản ghi nhật ký phục hồi không còn bất kỳ node nào lỡ dữ liệu, Coordinator sẽ xóa hẳn bản ghi đó để tối ưu hóa bộ nhớ. Cuối cùng, Node chuyển trạng thái từ `RECOVERING` sang `UP`.

### 6.3. Sơ đồ tuần tự phục hồi (Sequence Diagram)
Dưới đây là sơ đồ tuần tự Mermaid mô tả trực quan dòng thông điệp mạng trao đổi giữa Node đang phục hồi, Coordinator và tiến trình cập nhật trạng thái trong hệ thống:

```mermaid
sequenceDiagram
    autonumber
    participant Node as Phân trạm (Node)
    participant Coord as Bộ điều phối (Coordinator)
    participant DB as Tệp tin stock.json & WAL
    
    Note over Node: Node khởi động lại (Restart)<br/>Chuyển trạng thái sang RECOVERING
    
    rect rgb(28, 35, 51)
        Note over Node, Coord: Giai đoạn 1: Kéo giao dịch lỡ
        Node->>Coord: GET /api/missed-txs?node_id=NODE_ID
        Coord->>Coord: Quét recovery_log tìm node_id trong missedBy
        Coord-->>Node: Trả về danh sách missed_txs (JSON Array)
    end
    
    rect rgb(54, 54, 32)
        Note over Node, DB: Giai đoạn 2: Tái hiện nhật ký (Catch-up Phase)
        Note over Node: Node CHẶN hoàn toàn các yêu cầu READ từ client!
        loop Duyệt qua từng giao dịch lỡ (txId tăng dần)
            Node->>DB: Ghi log WAL cục bộ (wal.jsonl)
            Node->>DB: Cập nhật tồn kho vật lý (stock.json)
            Node->>Node: Cập nhật biến last_tx_id = tx_id
        end
    end
    
    rect rgb(26, 51, 26)
        Note over Node, Coord: Giai đoạn 3: Hoàn tất khôi phục
        Node->>Coord: POST /api/node/recovery-complete?node_id=NODE_ID
        Coord->>Coord: Xóa node_id khỏi missedBy trong recovery_log
        Coord->>Coord: Lưu trạng thái mới (coordinator_state.json)
        Coord-->>Node: Phản hồi SUCCESS
        Node->>Node: Chuyển trạng thái sang UP (Synced)
        Note over Node: Bắt đầu cho phép READ/WRITE bình thường
    end
```

Quy trình 3 bước này đảm bảo tính **Nhất quán hội tụ (Eventual Consistency)** cực kỳ bền vững: mọi phân trạm sau sự cố đều đạt tới trạng thái dữ liệu chính xác ngang bằng với các trạm luôn hoạt động.

---

## CHƯƠNG 7: NGĂN CHẶN ĐỌC DỮ LIỆU CŨ (STALE READ PREVENTION)

### 7.1. Lập luận Lý thuyết của Özsu & Valduriez
Đây là **quyết định thiết kế quan trọng nhất và mang tính học thuật cao nhất** của hệ thống, giúp bảo đảm tính chính xác tuyệt đối của cơ sở dữ liệu phân tán. 

Trong cuốn sách *Principles of Distributed Database Systems*, tại mục **§6.5 / §14.5.3 cũ (Recovery of a Replicated Database)**, hai tác giả Özsu và Valduriez đã thiết lập một nguyên lý phục hồi nghiêm ngặt đối với hệ thống cơ sở dữ liệu nhân bản phân tán:

> **Định lý phục hồi phân trạm nhân bản:** Một phân trạm đang nằm trong quá trình khôi phục (recovering site) **KHÔNG ĐƯỢC PHÉP** tham gia vào quá trình xử lý giao dịch thông thường và **BẮT BUỘC PHẢI CHẶN** các yêu cầu đọc dữ liệu (Read Operations) từ khách hàng cho đến khi nó hoàn thành việc replay toàn bộ các giao dịch bị lỡ trong Recovery Log và đạt trạng thái đồng bộ hóa hoàn toàn với các trạm khác trong mạng.

#### Tại sao nguyên lý này lại tối quan trọng?
Hãy phân tích một kịch bản lỗi thực tế xảy ra nếu **không** áp dụng Stale Read Prevention:
1. Trạng thái ban đầu tại $T_0$: `Node A`, `Node B`, `Node C` đều có số lượng tồn kho của `sku001` là `100`.
2. `Node A` bị sập nguồn đột ngột (DOWN).
3. Coordinator nhận yêu cầu ghi cập nhật delta $+50$ cho mặt hàng `sku001`. Do `Node A` đang DOWN, Coordinator áp dụng giao thức ROWA-A: cập nhật thành công trên `Node B` và `Node C` (lên giá trị `150`). `Node A` bị lỡ giao dịch này.
4. `Node A` khởi động lại và chuyển sang trạng thái `RECOVERING`. Quá trình catch-up và replay lại nhật ký giao dịch từ Coordinator tốn một khoảng thời gian vật lý thực tế (mô phỏng là `4.5` giây để replay các giao dịch).
5. **Kịch bản lỗi phát sinh:** Tại giây thứ 2 của quá trình phục hồi (khi Node A vẫn đang chạy ngầm replay log), một khách hàng gửi yêu cầu truy vấn đọc số lượng tồn kho của `sku001` đến `Node A`. Vì Node A chưa replay tới giao dịch lỡ đó, nó vẫn trả về giá trị tồn kho cũ là **`100`**.
6. **Hậu quả nghiêm trọng:** Khách hàng nhận được thông tin tồn kho lỗi thời (**Stale Read**). Nếu khách hàng là một ứng dụng bán hàng, họ sẽ hiển thị sai số lượng sản phẩm, dẫn đến việc bán quá hoặc hủy đơn hàng của khách. Hệ thống đã vi phạm nghiêm trọng thuộc tính **Nhất quán Một Bản Sao (1-Copy Serializability - 1SR)**.

### 7.2. Khái niệm Tính nhất quán Một Bản Sao (1-Copy Serializability - 1SR)
Tính nhất quán một bản sao (1SR) là tiêu chuẩn vàng của hệ cơ sở dữ liệu phân tán nhân bản. Nó yêu cầu rằng:
> Bất chấp việc dữ liệu được nhân bản ra hàng chục phân trạm vật lý khác nhau, các giao dịch đọc và ghi đồng thời tác động lên hệ thống phải được thực thi và mang lại kết quả chính xác tương đương như thể toàn bộ hệ thống chỉ là một **cơ sở dữ liệu duy nhất không nhân bản**.

Nếu một hệ thống cho phép đọc từ một node đang khôi phục dữ liệu cũ, tính nhất quán 1SR hoàn toàn bị phá vỡ vì người dùng có thể nhận được hai kết quả khác nhau cho cùng một truy vấn đọc tại cùng một thời điểm tùy thuộc vào node mà họ kết nối tới.

### 7.3. Kịch bản lỗi chi tiết và Cơ chế chặn Stale Read trong mã nguồn
Để ngăn chặn triệt để hiện tượng Stale Read, hệ thống thiết lập một máy trạng thái chặt chẽ cho từng Node hạ nguồn:

```
                  ┌───────────────┐
                  │      UP       │────────┐
                  └───────────────┘        │
                    ▲                      │ Sự cố sập trạm
   Đồng bộ hoàn tất │                      │ (Crash)
                    │                      ▼
                  ┌───────────────┐      ┌───────────────┐
                  │  RECOVERING   │◄─────│     DOWN      │
                  └───────────────┘      └───────────────┘
                                     Khởi động lại
                                     (Recover)
```

Khi ở trạng thái `RECOVERING`, Node chủ động chặn đứng mọi yêu cầu đọc dữ liệu gửi tới nó và trả về một mã lỗi HTTP đặc thù. Đoạn code thực thi chốt chặn này được viết trong hàm `read_data()` tại tệp tin [node/app.py](file:///c:/Users/ACER/OneDrive/Documents/Máy tính/DEMO CSDLPT/node/app.py#L203-L212):

```python
# ★ STALE READ PREVENTION ★
# Tham chiếu lý thuyết: Giáo trình Özsu & Valduriez Mục §14.5.3 (4th Edition)
if state == "RECOVERING":
    log("Read request REJECTED! Stale Read Prevented.", "ERROR")
    return jsonify({
        "status": "STALE_READ_PREVENTED",
        "error": "Stale Read Prevented",
        "reason": "Node is currently replaying WAL in RECOVERING state. Reads are disabled until catch-up is complete."
    }), 400 # Trả về HTTP 400 Bad Request để Frontend bắt lỗi và cảnh báo
```

#### Phản ánh trên giao diện mô phỏng:
Khi người dùng thực hiện mô phỏng kịch bản này trên trình duyệt, nếu họ nhấn nút **Read** trên một Node đang nhấp nháy màu vàng cục bộ (trạng thái `RECOVERING`), giao diện React lập tức hiển thị một bảng thông báo cảnh báo trực quan cực kỳ nổi bật màu đỏ:

> *"🚨 TỪ CHỐI ĐỌC: STALE READ PREVENTED - Node đang RECOVERING. Hệ thống đang đọc Recovery Log từ Coordinator. Phải chặn lại để tránh đọc dữ liệu cũ theo quy tắc nghiêm ngặt của Özsu §14.5.3!"*

Quyết định thiết kế này là minh chứng rõ nét nhất cho việc đặt tính nhất quán dữ liệu (Consistency) lên trên tính sẵn sàng đọc tạm thời của một node bị lỗi, đảm bảo hệ thống luôn hành xử chính xác theo tiêu chuẩn 1SR.

---

## CHƯƠNG 8: KIỂM SOÁT ĐỒNG THỜI & AN TOÀN ĐA LUỒNG (CONCURRENCY CONTROL & THREAD SAFETY)

### 8.1. Lý thuyết về Khả năng tuần tự hóa giao dịch (Serializability Theory)
**Chương 5 (Özsu & Valduriez)** định nghĩa lý thuyết khả tuần tự hóa (Serializability Theory) là nền tảng toán học để xác định tính đúng đắn của việc thực thi đồng thời các giao dịch. Một lịch trình thực thi đồng thời (history $H$) được coi là đúng đắn nếu nó tương đương với một lịch trình thực thi tuần tự (serial history) nào đó.

Trong môi trường phân tán:
* Mỗi phân trạm sinh ra một lịch trình thực thi cục bộ (Local History - $H_i$).
* Lịch trình thực thi toàn cục (Global History - $H_{\text{global}}$) là hợp của các lịch trình cục bộ:

  $$H_{\text{global}} = \bigcup_{i=1}^{n} H_i$$

* Hệ thống chỉ đạt tính khả tuần tự toàn cục khi và chỉ khi mọi lịch trình cục bộ $H_i$ đều khả tuần tự và có **cùng một thứ tự tuần tự hóa** đối với các giao dịch đồng thời.

### 8.2. Phương pháp kiểm soát đồng thời dựa trên Khóa (Lock-based) vs. Lạc quan (Optimistic)
Özsu & Valduriez phân loại các thuật toán kiểm soát đồng thời thành hai nhóm chính:
1. **Kiểm soát đồng thời dựa trên Khóa (Lock-based Concurrency Control - Pessimistic):** Sử dụng các khóa đọc (Shared Lock) và khóa ghi (Exclusive Lock) để ngăn chặn xung đột trước khi chúng xảy ra. Giao thức điển hình là Khóa hai pha (Two-Phase Locking - 2PL).
2. **Kiểm soát đồng thời Lạc quan (Optimistic Concurrency Control - OCC):** Cho phép các giao dịch thực thi tự do trên các vùng đệm cục bộ, sau đó thực hiện pha kiểm tra tính hợp lệ (Validation Phase) trước khi commit. Nếu phát hiện xung đột, giao dịch sẽ bị abort và restart từ đầu.

#### Biện minh lựa chọn thuật toán Khóa Pessimistic Mutex cho hệ thống mô phỏng:
Trong bài toán quản lý kho hàng, các giao dịch cập nhật số lượng tồn kho SKU diễn ra liên tục và tác động trực tiếp vào một tài nguyên số duy nhất. 
* Nếu sử dụng **OCC (Lạc quan)**, dưới điều kiện tải cao (nhiều khách hàng cùng mua một mặt hàng hot), tỷ lệ xung đột sẽ cực kỳ lớn. Các giao dịch ghi sẽ liên tục bị hủy và restart, gây lãng phí nghiêm trọng tài nguyên xử lý của CPU và làm giảm đột ngột trải nghiệm của khách hàng (độ trễ tăng cao do phải thử lại nhiều lần).
* Do đó, hệ thống lựa chọn giải pháp **Khóa Pessimistic (Mutex Lock)** để đảm bảo các yêu cầu ghi vào cùng một SKU được xếp hàng và xử lý tuần tự một cách tuyệt đối an toàn.

### 8.3. Mutex Lock implementation và Thread Safety trong Flask multi-threaded
Máy chủ Flask Python mặc định xử lý mỗi yêu cầu HTTP REST API đến trên một luồng xử lý riêng biệt (Thread) để tối ưu hóa hiệu năng đồng thời (`threaded=True`). Khi nhiều luồng cùng truy cập và sửa đổi các biến trạng thái toàn cục chung trong bộ nhớ (RAM) như mảng dữ liệu `stock` và biến trạng thái `state`, hiện tượng tranh chấp luồng (**Race Conditions**) chắc chắn sẽ xảy ra, dẫn đến hỏng cấu trúc bộ nhớ hoặc ghi đè dữ liệu lẫn nhau.

Để giải quyết triệt để bài toán an toàn đa luồng (Thread Safety), chúng tôi triển khai một cơ chế khóa tương hỗ **Mutex Lock (`threading.Lock()`)** bao bọc toàn bộ các vùng tranh chấp (Critical Sections) tại cả Coordinator và các phân trạm Node hạ nguồn.

#### Minh họa mã nguồn thực tế tại Node ([node/app.py](file:///c:/Users/ACER/OneDrive/Documents/Máy tính/DEMO CSDLPT/node/app.py#L224-L244)):
```python
lock = threading.Lock()

@app.route("/write", methods=["POST"])
def write_data():
    global state, stock, last_tx_id
    # Toàn bộ khối code bên dưới được bảo vệ bởi Mutex Lock
    with lock:
        if state == "DOWN":
            return jsonify({"error": "Service Unavailable. Node is DOWN."}), 503

        # Đọc số lượng hiện tại, tính toán delta và cập nhật
        old_qty = get_stock_quantity(sku)
        new_qty = old_qty + delta
        
        # Ghi WAL cục bộ
        write_wal(tx_id, sku, old_qty, new_qty)
        
        # Cập nhật tồn kho vật lý và ghi file stock.json
        update_stock_quantity(sku, new_qty)
        last_tx_id = tx_id
        save_stock()
```

Cơ chế khóa Mutex này đảm bảo rằng tại bất kỳ thời điểm nào, chỉ có duy nhất một luồng xử lý được quyền đọc và cập nhật dữ liệu tồn kho cục bộ của một SKU. Toàn bộ quá trình đọc $\to$ tính toán $\to$ ghi WAL $\to$ commit DB được thực hiện một cách nguyên tử tuyệt đối dưới góc nhìn đa luồng, loại bỏ hoàn toàn khả năng xảy ra lỗi sai lệch số liệu tồn kho.

---

## CHƯƠNG 9: PHÂN TÍCH HỆ THỐNG THEO ĐỊNH LÝ CAP (CAP THEOREM ANALYSIS)

### 9.1. Định lý CAP (Consistency, Availability, Partition Tolerance)
Định lý CAP của Eric Brewer là một nguyên lý nền tảng của hệ thống phân tán, phát biểu rằng một hệ thống lưu trữ dữ liệu phân tán chỉ có thể đảm bảo tối đa hai trong ba thuộc tính sau đồng thời:
* **Tính nhất quán (Consistency - C):** Mọi truy vấn đọc đều nhận được dữ liệu mới nhất hoặc trả về lỗi. Hệ thống hành xử như một cơ sở dữ liệu duy nhất.
* **Tính sẵn sàng (Availability - A):** Mọi yêu cầu không bị lỗi đều nhận được phản hồi không lỗi (không đảm bảo chứa dữ liệu mới nhất).
* **Khả năng chịu lỗi phân mảnh mạng (Partition Tolerance - P):** Hệ thống tiếp tục hoạt động bất chấp việc mạng truyền thông giữa các node bị mất kết nối hoặc trễ thông điệp.

```
                         Nhất quán (Consistency)
                                ╱      ╲
                               ╱   CP   ╲
                              ╱ (ROWA-A) ╲
                             ╱            ╲
      Khả năng chịu lỗi ────┴──────────────┴──── Tính sẵn sàng
      phân mảnh (P)                               (Availability)
```

### 9.2. Xác định vị trí của hệ thống ROWA-A trong tam giác CAP
Do chạy trong môi trường mạng thực tế nơi sự cố mất kết nối hoặc sập container hoàn toàn có thể xảy ra, hệ thống **bắt buộc phải hỗ trợ Khả năng chịu lỗi phân mảnh mạng (P)**. Do đó, sự lựa chọn thiết kế của hệ thống nằm ở việc chọn giữa **CP (Consistency & Partition Tolerance)** và **AP (Availability & Partition Tolerance)**.

Hệ thống ROWA-A của chúng tôi được định vị chính xác là một hệ thống **CP (Consistency & Partition Tolerance)**.

#### Biện minh khoa học:
1. **Ưu tiên Tính nhất quán (C) tuyệt đối trên trạm hoạt động:** Bằng cách áp dụng giao thức chặn đọc Stale Read Prevention khi một trạm ở trạng thái `RECOVERING`, hệ thống từ chối phục vụ yêu cầu đọc chứa dữ liệu cũ. Hệ thống thà trả về lỗi HTTP 400 còn hơn là cung cấp thông tin sai lệch cho khách hàng. Điều này tuân thủ định nghĩa nghiêm ngặt về thuộc tính Consistency của định lý CAP.
2. **Hy sinh một phần Tính sẵn sàng (A) để bảo toàn tính đúng đắn:** Khi một phân trạm đang trong tiến trình catch-up dữ liệu, tính sẵn sàng đọc của trạm đó tạm thời bị khóa. Dưới góc nhìn toàn cục, hệ thống chấp nhận giảm một phần khả năng đáp ứng tức thời của trạm lỗi để bảo toàn độ chính xác tuyệt đối của dữ liệu tồn kho.

### 9.3. Các quyết định đánh đổi thiết kế thực tế
Quyết định lựa chọn CP thay vì AP là hoàn toàn phù hợp và đúng đắn đối với các hệ thống quản lý tài chính, giao dịch ngân hàng và quản lý tồn kho kho hàng bán lẻ. 

Trong các hệ thống này, việc bán quá số lượng hàng thực tế trong kho (do đọc phải thông tin tồn kho cũ lỗi thời) sẽ mang lại hậu quả pháp lý và kinh tế nghiêm trọng cho doanh nghiệp (đền bù hợp đồng, mất uy tín thương hiệu). Ngược lại, trong các hệ thống mạng xã hội (như Facebook/Twitter), việc người dùng nhìn thấy một comment chậm vài giây là hoàn toàn chấp nhận được, do đó các hệ thống đó ưu tiên lựa chọn AP (Eventual Consistency lỏng).

---

## CHƯƠNG 10: TỔNG KẾT ĐÁNH GIÁ THIẾT KẾ & BẢNG ĐỐI CHIẾU LÝ THUYẾT - THỰC TIỄN

### 10.1. Bảng tổng hợp đối chiếu lý thuyết và thực tiễn mã nguồn
Để tổng kết toàn bộ các lập luận biện minh thiết kế, bảng dưới đây đối chiếu trực quan giữa các vấn đề kỹ thuật thực tế triển khai trong dự án và các chương lý thuyết tương ứng trong cuốn sách giáo khoa kinh điển của **Özsu & Valduriez (4th Edition, 2020)**:

| Vấn đề Kỹ thuật Dự án | Quyết định Thiết kế triển khai | Chương lý thuyết đối chiếu (Özsu & Valduriez) | Biện minh kỹ thuật & Ý nghĩa học thuật |
| :--- | :--- | :--- | :--- |
| **Nhân bản dữ liệu tồn kho** | Áp dụng giao thức nhân bản cải tiến **ROWA-Available (ROWA-A)** | *Chương 6 (Data Replication)* & *Mục §5.4 / §14.4 (Reliability)* | Đạt tốc độ truy vấn đọc tối ưu $O(1)$ từ phân trạm cục bộ, đồng thời nâng cao đột biến xác suất sẵn sàng ghi từ $\prod p_i$ lên $1 - \prod(1 - p_i)$. |
| **Sự cố sập phân trạm tạm thời** | Coordinator lưu vết giao dịch bị lỡ vào **Recovery Log** tập trung bền vững | *Chương 5 (Transaction Processing)* & *Mục §6.3 / §14.5 (Recovery)* | Đảm bảo hệ thống vẫn ghi được dữ liệu lên các trạm đang sống mà không bị chặn, đồng thời lưu vết cấu trúc dữ liệu để đồng bộ hóa bù sau khi trạm reboot. |
| **Mất điện/Sập nguồn cục bộ tại Node** | Node áp dụng nguyên tắc **Write-Ahead Logging (WAL)** cục bộ | *Chương 5 (Transaction Processing)* & *Mục §5.4 / §14.2 (Reliability)* | Đảm bảo nhật ký thay đổi trạng thái phải ghi xuống file `wal.jsonl` trên đĩa cứng trước khi cập nhật file dữ liệu chính `stock.json`, bảo vệ toàn vẹn dữ liệu khi sập nguồn đột ngột. |
| **Node kết nối lại hệ thống** | Tự động chạy tiến trình ngầm **Catch-up Phase** kéo log lỡ và tuần tự replay | *Mục §6.3 / §14.5 (Site Recovery Protocols)* | Đồng bộ hóa dữ liệu tự động cho các trạm sau sự cố mất kết nối, đưa cơ sở dữ liệu phân tán hội tụ về trạng thái nhất quán toàn cục. |
| **Client truy vấn trạm đang catch-up** | Chốt chặn trả về lỗi **STALE_READ_PREVENTED (HTTP 400)** | *Mục §6.5 / §14.5.3 (Recovery of a Replicated Database)* | **Ngăn chặn triệt để hiện tượng Stale Reads**. Đảm bảo tính nhất quán Một Bản Sao (1-Copy Serializability - 1SR) trong suốt quá trình đồng bộ hóa trạng thái. |
| **Môi trường Flask đa luồng** | Áp dụng khóa tương hỗ **`threading.Lock()`** tại các Critical Sections | *Chương 5 (Concurrency Control)* | Đảm bảo tính Độc lập (Isolation) của giao dịch cục bộ, triệt tiêu hoàn toàn Race Conditions trong các luồng xử lý API đồng thời. |
| **Phân mảnh mạng liên kết** | Định vị hệ thống là **CP (Consistency & Partition Tolerance)** | *Chương 6 (Consistency Models)* & *Định lý CAP* | Ưu tiên tính chính xác tuyệt đối của dữ liệu tồn kho kho hàng hơn tính sẵn sàng đọc tạm thời của trạm lỗi trong quá trình khôi phục. |

### 10.2. Kết luận cuối cùng
Hệ thống Mô phỏng Kho hàng Phân tán ROWA-A không chỉ là một ứng dụng phần mềm hoạt động trơn tru mà còn là một công cụ thực chứng học thuật chuẩn mực. Mọi quyết định thiết kế từ việc lựa chọn cấu trúc dữ liệu nhật ký phục hồi, quy tắc ghi file WAL, đến cơ chế chặn đọc nghiêm ngặt ngăn ngừa stale read đều được xây dựng trên nền tảng lý thuyết phân tán vững chắc của hai học giả Özsu và Valduriez. Sự kết hợp hài hòa giữa lý thuyết học thuật kinh điển và công nghệ container hóa hiện đại đã mang lại một giải pháp quản lý kho hàng phân tán có tính sẵn sàng cao, chịu lỗi tốt và đảm bảo tính nhất quán dữ liệu tuyệt đối.

---

## TÀI LIỆU THAM KHẢO (REFERENCES)

1. **Özsu, M. T., & Valduriez, P. (2020).** *Principles of Distributed Database Systems* (4th Edition). Springer.
   * **Chương 1:** Introduction to Distributed Database Systems.
   * **Chương 2:** Distributed and Parallel Database Design (Fragmentation & Allocation).
   * **Chương 5:** Distributed Transaction Processing, Concurrency Control, and Reliability Protocols.
   * **Chương 6:** Data Replication (Consistency Models, Update Strategies, ROWA/ROWA-A Protocols, and Site Recovery).
2. **Brewer, E. (2012).** *CAP theorem finally-faced: How the "rules" have changed*. Computer, 45(2), 23-29.
3. **Mã nguồn hệ thống mô phỏng:** 
   * Bộ điều phối trung tâm: [coordinator/app.py](file:///c:/Users/ACER/OneDrive/Documents/Máy tính/DEMO CSDLPT/coordinator/app.py).
   * Phân trạm bản sao: [node/app.py](file:///c:/Users/ACER/OneDrive/Documents/Máy tính/DEMO CSDLPT/node/app.py).
   * Giao diện mô phỏng trực quan: [index.html](file:///c:/Users/ACER/OneDrive/Documents/Máy tính/DEMO CSDLPT/index.html).

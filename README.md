# KienlongBank Robo-Advisor Cá Nhân

> Hệ thống tư vấn vay vốn tự động 24/7 dành cho KienlongBank PGD Hải Châu
> Gợi ý sản phẩm vay, tính DTI/LTV, điều chỉnh khoản vay và trả về lãi suất tham khảo thông qua mô hình **Random Forest** đạt độ chính xác **95.88%**.

---

## Mục lục

1. [Tổng quan hệ thống](#1-tổng-quan-hệ-thống)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Yêu cầu hệ thống](#3-yêu-cầu-hệ-thống)
4. [Hướng dẫn cài đặt & chạy nhanh](#4-hướng-dẫn-cài-đặt--chạy-nhanh)
5. [Mô hình Machine Learning](#5-mô-hình-machine-learning)
6. [API Backend (FastAPI)](#6-api-backend-fastapi)
7. [Giao diện Frontend](#7-giao-diện-frontend)
8. [Quy tắc nghiệp vụ](#8-quy-tắc-nghiệp-vụ)
9. [Bảng sản phẩm & lãi suất](#9-bảng-sản-phẩm--lãi-suất)
10. [Ví dụ API](#10-ví-dụ-api)

---

## 1. Tổng quan hệ thống

```
Khách hàng (Trình duyệt)
    │  5 bước nhập form
    ▼
Frontend  ─── POST /api/v1/assess ──►  FastAPI Backend
(frontend/index.html)                      │
                                     ┌─────┴───────────────┐
                                     │  Business Logic      │
                                     │  • Tính DTI / LTV    │
                                     │  • Giảm vay (LTV>80%)│
                                     │  • Map input → model │
                                     └─────┬───────────────┘
                                           │
                                     Random Forest Model
                                     (model/best_loan_recommender.pkl)
                                           │ Dự đoán sản phẩm
                                     ◄─────┘
                                  Trả kết quả JSON
```

**Luồng tư vấn gồm 5 bước:**

| Bước | Nội dung |
|------|----------|
| 1 | Chân dung khách hàng (tên, CCCD, giới tính, tuổi, nghề nghiệp) |
| 2 | Nhu cầu vay (hình thức, mục đích, kỳ hạn) |
| 3 | Tài chính (thu nhập, nợ hiện tại, số tiền vay, TSĐB) |
| 4 | Lịch sử tín dụng (nợ xấu, chậm thanh toán, nợ cần chú ý) |
| 5 | Kết quả (decision, sản phẩm gợi ý, DTI, LTV, lãi suất, trả góp) |

---

## 2. Cấu trúc thư mục

```
robot_chauanh/
├── data/
│   └── dl_KLB.xlsx              # Dữ liệu huấn luyện (2.000 mẫu, 17 cột)
│
├── model/
│   ├── train.py                 # Script huấn luyện mô hình
│   ├── best_loan_recommender.pkl  # Pipeline Random Forest đã huấn luyện
│   ├── feature_cols.pkl         # Danh sách tên cột đầu vào
│   └── model_comparison_results.pkl  # Bảng so sánh hiệu suất các mô hình
│
├── backend/
│   ├── main.py                  # FastAPI app (entry point)
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── predictor.py             # Business logic + ML prediction
│   └── requirements.txt        # Python dependencies
│
├── frontend/
│   └── index.html               # Single-page app (HTML/CSS/JS)
│
├── notebooks/
│   └── train_model.ipynb        # Jupyter Notebook gốc (EDA + training)
│
├── run.bat                      # Script khởi động nhanh (Windows)
└── README.md
```

---

## 3. Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu |
|------------|---------------------|
| Python | 3.10+ |
| FastAPI | 0.115+ |
| uvicorn | 0.32+ |
| scikit-learn | 1.5+ |
| pandas | 2.0+ |
| numpy | < 2.0 |
| openpyxl | 3.1+ |
| joblib | 1.4+ |
| pydantic | 2.0+ |

---

## 4. Hướng dẫn cài đặt & chạy nhanh

### Cách 1 — Script tự động (Windows)

```bat
cd robot_chauanh
run.bat
```

Script sẽ tự động cài thư viện, huấn luyện mô hình (nếu chưa có `.pkl`), rồi khởi động server.

---

### Cách 2 — Thủ công

**Bước 1: Cài thư viện**

```bash
pip install fastapi "uvicorn[standard]" scikit-learn pandas "numpy<2" openpyxl joblib pydantic python-multipart
```

**Bước 2: Huấn luyện mô hình** *(chỉ cần làm 1 lần)*

```bash
cd robot_chauanh
python -X utf8 model/train.py
```

Output sau khi train:
```
[save] Saved to E:\robot_chauanh\model
  ✓ best_loan_recommender.pkl
  ✓ feature_cols.pkl
  ✓ model_comparison_results.pkl
[done] Training complete.
```

**Bước 3: Khởi động backend**

```bash
cd robot_chauanh/backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
# nên chạy cái này
# python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

```

**Bước 4: Mở giao diện**

Truy cập trình duyệt: **http://127.0.0.1:8000**

- Giao diện tư vấn: `http://127.0.0.1:8000`
- API Interactive Docs: `http://127.0.0.1:8000/docs`
- API ReDoc: `http://127.0.0.1:8000/redoc`

---

## 5. Mô hình Machine Learning

### Dữ liệu

| Thuộc tính | Giá trị |
|------------|---------|
| Tổng mẫu | 2.000 |
| Mẫu huấn luyện | 1.700 (loại bỏ các hồ sơ **Từ chối**) |
| Train / Test | 1.360 / 340 (80/20, stratified) |
| Target | 10 sản phẩm vay |

### So sánh mô hình

| Mô hình | Accuracy | F1 Macro | Ghi chú |
|---------|----------|----------|---------|
| **Random Forest** | **95.88%** | **95.78%** | ✅ Được chọn |
| Decision Tree | 72.35% | 61.74% | Kém hơn đáng kể |

### 16 đặc trưng đầu vào

| Nhóm | Đặc trưng |
|------|-----------|
| Nhân khẩu học | Giới tính, Nhóm tuổi |
| Khoản vay | Có TSBĐ không?, Hình thức vay, Mục đích sử dụng, Thời gian vay (tháng) |
| Tài chính | Thu nhập, Số lượng khoản vay đang hoạt động, Tổng tiền trả nợ khác, Số tiền muốn vay, Giá trị BĐS |
| Tín dụng | Lịch sử nợ xấu 5 năm, Chậm thanh toán thẻ 3 năm, Nợ cần chú ý 12 tháng |
| Tính toán | Kết quả DTI, Kết quả LTV |

### 10 sản phẩm vay (nhãn dự đoán)

| Loại | Sản phẩm |
|------|----------|
| Thế chấp | Vay Thế chấp - SXKD |
| Thế chấp | Vay Thế chấp - BĐS |
| Thế chấp | Vay Thế chấp - Mua xe ô tô |
| Thế chấp | Vay Thế chấp - Phục vụ đời sống |
| Thế chấp | Vay Thế chấp - Xây sửa nhà |
| Tín chấp | Vay Tín chấp - Hành chính sự nghiệp |
| Tín chấp | Vay Tín chấp - Hội Phụ Nữ |
| Tín chấp | Vay Tín chấp - Trồng lúa |
| Tín chấp | Vay Tín chấp - Hội Nông dân |
| Tín chấp | Vay Tín chấp - Lương/Y/Trường học |

---

## 6. API Backend (FastAPI)

### Endpoint chính

```
POST /api/v1/assess
Content-Type: application/json
```

### Request body

```json
{
  "ho_ten":                "Nguyễn Văn A",
  "cccd":                  "079300012345",
  "tuoi":                  32,
  "gioi_tinh":             "Nam",
  "nghe_nghiep":           "kinh_doanh",

  "loai_vay":              "the_chap",
  "san_pham_vay":          "mua_xe",
  "ky_han_thang":          84,
  "so_khoan_vay_hien_tai": 1,

  "thu_nhap_thang":        25000000,
  "no_hien_tai_thang":     2000000,
  "so_tien_vay":           1200000000,
  "gia_tri_tsdb":          1300000000,
  "thoi_gian_uu_dai":      "3th",

  "co_no_xau":             false,
  "cham_thanh_toan":       false,
  "no_can_chu_y":          false
}
```

**Giá trị hợp lệ:**

| Trường | Giá trị cho phép |
|--------|-----------------|
| `gioi_tinh` | `"Nam"`, `"Nữ"` |
| `loai_vay` | `"tin_chap"`, `"the_chap"` |
| `san_pham_vay` (**tin_chap**) | `"hoi_phu_nu"`, `"hoi_nong_dan"`, `"trong_lua"`, `"hanh_chinh"`, `"luong_y_truong"` |
| `san_pham_vay` (**the_chap**) | `"sxkd"`, `"doi_song"`, `"mua_xe"`, `"xay_dung"`, `"bds"` |
| `thoi_gian_uu_dai` | `"3th"`, `"9th"`, `"18th"` |

### Response body

```json
{
  "khach_hang": "Nguyễn Văn A",
  "phan_tich": {
    "dti": {
      "dti_ratio": 8.0,
      "is_eligible": true,
      "max_dti": 70.0,
      "mo_ta": "Tỷ lệ nợ hiện tại / thu nhập hàng tháng."
    },
    "ltv": {
      "ltv_ratio": 80.0,
      "is_eligible": true,
      "max_ltv": 80.0,
      "mo_ta": "Tỷ lệ khoản vay / giá trị tài sản đảm bảo."
    },
    "toi_uu_khoan_vay": {
      "so_tien_goc": 1200000000,
      "vay_toi_da_an_toan": 1040000000,
      "ltv_da_dieu_chinh": true,
      "tra_gop_hang_thang": 16469945
    }
  },
  "san_pham": {
    "ten": "Vay Thế chấp - Mua xe ô tô",
    "ma_san_pham": "mua_xe",
    "lai_suat_nam": 8.5,
    "lai_suat_uu_dai": 6.5,
    "thoi_gian_uu_dai_thang": 3,
    "so_tien_vay": 1040000000,
    "tra_gop_hang_thang": 16469945
  },
  "ket_luan": {
    "quyet_dinh": "Chấp thuận",
    "ly_do": [
      "Số tiền vay đã được điều chỉnh xuống 1,040,000,000 VND để đảm bảo ngưỡng LTV 80%.",
      "Hồ sơ đáp ứng các tiêu chí xét duyệt.",
      "Sản phẩm gợi ý: Vay Thế chấp - Mua xe ô tô."
    ]
  }
}
```

### Các endpoint khác

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/` | Phục vụ giao diện frontend |
| GET | `/health` | Kiểm tra trạng thái server |
| GET | `/docs` | Swagger UI (tương tác API) |
| GET | `/redoc` | ReDoc documentation |

---

## 7. Giao diện Frontend

File: `frontend/index.html`

- **Ngôn ngữ:** Tiếng Việt hoàn toàn
- **Công nghệ:** Thuần HTML5 / CSS3 / JavaScript (không cần build)
- **Thiết kế:** KienlongBank branding (xanh `#0b3ea8` + cam `#f36a21`), glassmorphism, responsive
- **Wizard 5 bước:** Progress sidebar, fade animation giữa các bước
- **Live feedback:**
  - Tính DTI ngay khi nhập thu nhập / nợ
  - Cảnh báo LTV khi nhập số tiền vay / giá trị TSĐB
  - Tự động điều chỉnh khoản vay khi LTV > 80%
- **Kết quả:** 6 metric cards (quyết định, sản phẩm, lãi suất, DTI, LTV, khoản vay), bảng tóm tắt, trả góp ước tính

---

## 8. Quy tắc nghiệp vụ

| Quy tắc | Điều kiện | Hành động |
|---------|-----------|-----------|
| DTI | > 70% | **Từ chối** hồ sơ |
| LTV | > 80% (chỉ thế chấp) | **Tự động giảm** số tiền vay về 80% TSĐB |
| Nợ xấu 5 năm | Có | **Cần xem xét** (không tự động từ chối) |
| Chậm TT / Nợ chú ý | Có | **Cần xem xét** |
| Hồ sơ sạch | DTI ≤ 70%, không có lịch sử xấu | **Chấp thuận** |

**Công thức:**

```
DTI (%) = Tổng tiền trả nợ hàng tháng / Thu nhập hàng tháng × 100
LTV (%) = Số tiền muốn vay / Giá trị TSĐB × 100

Trả góp (PMT) = P × r × (1+r)^n / ((1+r)^n - 1)
  trong đó: P = gốc, r = lãi suất tháng, n = số tháng
```

---

## 9. Bảng sản phẩm & lãi suất

| Sản phẩm | Lãi suất/năm | Giảm ưu đãi 3th | Giảm ưu đãi 9th | Giảm ưu đãi 18th |
|----------|-------------|-----------------|-----------------|------------------|
| Vay Tín chấp - Trồng lúa | 6.5% | 4.5% | 5.0% | 5.5% |
| Vay Tín chấp - Hội Nông dân | 6.5% | 4.5% | 5.0% | 5.5% |
| Vay Tín chấp - Hội Phụ Nữ | 7.0% | 5.0% | 5.5% | 6.0% |
| Vay Tín chấp - Hành chính SN | 7.5% | 5.5% | 6.0% | 6.5% |
| Vay Tín chấp - Lương/Y/Trường | 8.0% | 6.0% | 6.5% | 7.0% |
| Vay Thế chấp - Mua xe ô tô | 8.5% | 6.5% | 7.0% | 7.5% |
| Vay Thế chấp - Xây sửa nhà | 8.5% | 6.5% | 7.0% | 7.5% |
| Vay Thế chấp - SXKD | 9.0% | 7.0% | 7.5% | 8.0% |
| Vay Thế chấp - Phục vụ đời sống | 9.0% | 7.0% | 7.5% | 8.0% |
| Vay Thế chấp - BĐS | 9.5% | 7.5% | 8.0% | 8.5% |

---

## 10. Ví dụ API

### Curl

```bash
curl -X POST http://127.0.0.1:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{
    "ho_ten": "Nguyễn Văn A",
    "cccd": "079300012345",
    "tuoi": 32,
    "gioi_tinh": "Nam",
    "nghe_nghiep": "kinh_doanh",
    "loai_vay": "the_chap",
    "san_pham_vay": "mua_xe",
    "ky_han_thang": 84,
    "so_khoan_vay_hien_tai": 1,
    "thu_nhap_thang": 25000000,
    "no_hien_tai_thang": 2000000,
    "so_tien_vay": 1200000000,
    "gia_tri_tsdb": 1300000000,
    "thoi_gian_uu_dai": "3th",
    "co_no_xau": false,
    "cham_thanh_toan": false,
    "no_can_chu_y": false
  }'
```

### Python

```python
import requests

payload = {
    "ho_ten": "Trần Thị B",
    "cccd": "048200098765",
    "tuoi": 35,
    "gioi_tinh": "Nữ",
    "nghe_nghiep": "hoi_doan",
    "loai_vay": "tin_chap",
    "san_pham_vay": "hoi_phu_nu",
    "ky_han_thang": 24,
    "so_khoan_vay_hien_tai": 0,
    "thu_nhap_thang": 10000000,
    "no_hien_tai_thang": 0,
    "so_tien_vay": 30000000,
    "gia_tri_tsdb": 0,
    "thoi_gian_uu_dai": "9th",
    "co_no_xau": False,
    "cham_thanh_toan": False,
    "no_can_chu_y": False,
}
r = requests.post("http://127.0.0.1:8000/api/v1/assess", json=payload)
print(r.json()["ket_luan"]["quyet_dinh"])
print(r.json()["san_pham"]["ten"])
```

---

## Ghi chú kỹ thuật

- Mô hình sử dụng **Pipeline scikit-learn** (OneHotEncoder + SimpleImputer + RandomForestClassifier) giúp xử lý dữ liệu mới mà không cần tiền xử lý thủ công.
- Backend **FastAPI** phục vụ cả API lẫn file tĩnh frontend từ cùng một cổng (8000), tránh lỗi CORS.
- Frontend thuần HTML/JS, không cần Node.js hay build tools — mở trực tiếp trong trình duyệt hoặc qua server.
- Tất cả văn bản hiển thị bằng **tiếng Việt** với encoding UTF-8.

---

*© 2026 KienlongBank — Robo-Advisor Demo | PGD Hải Châu*

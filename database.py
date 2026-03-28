"""
database.py — Module Quản lý Cơ sở Dữ liệu
---------------------------------------------
SQLite database cho hệ thống Robo-Advisor KienlongBank.

Bảng dữ liệu:
  - inquiry_history : Lịch sử truy vấn tư vấn
  - lending_rules   : Quy tắc cho vay theo sản phẩm

Tác giả : Phan Thị Châu Anh
Phiên bản: 1.0.0
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robo_advisor.db")


# ---------------------------------------------------------------------------
# Khởi tạo Database
# ---------------------------------------------------------------------------

def get_connection():
    """Tạo kết nối SQLite với row_factory để trả dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Tạo các bảng và seed dữ liệu quy tắc cho vay nếu chưa có."""
    conn = get_connection()
    cursor = conn.cursor()

    # --- Bảng lịch sử truy vấn ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inquiry_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ho_ten TEXT,
            cccd TEXT,
            thu_nhap REAL,
            so_tien_vay REAL,
            san_pham_vay TEXT,
            dti_ratio REAL,
            ltv_ratio REAL,
            credit_score INTEGER,
            xep_hang TEXT,
            quyet_dinh TEXT,
            chi_tiet_json TEXT
        )
    """)

    # --- Bảng quy tắc cho vay ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lending_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ma_san_pham TEXT NOT NULL UNIQUE,
            ten_san_pham TEXT NOT NULL,
            loai_vay TEXT NOT NULL,
            lai_suat_uu_dai REAL NOT NULL,
            thoi_gian_uu_dai_thang INTEGER NOT NULL,
            lai_suat_sau_uu_dai TEXT NOT NULL,
            ky_han_toi_da_thang INTEGER NOT NULL,
            dti_toi_da REAL NOT NULL,
            ltv_toi_da REAL,
            dieu_kien TEXT,
            ghi_chu TEXT
        )
    """)

    # Seed dữ liệu quy tắc cho vay KienlongBank (nếu chưa có)
    cursor.execute("SELECT COUNT(*) FROM lending_rules")
    if cursor.fetchone()[0] == 0:
        _seed_lending_rules(cursor)

    conn.commit()
    conn.close()


def _seed_lending_rules(cursor):
    """Seed bảng quy tắc cho vay với sản phẩm thực tế của KienlongBank."""
    rules = [
        # Vay thế chấp
        {
            "ma_san_pham": "TC_SXKD",
            "ten_san_pham": "Vay Sản xuất Kinh doanh (Thế chấp)",
            "loai_vay": "the_chap",
            "lai_suat_uu_dai": 5.5,
            "thoi_gian_uu_dai_thang": 6,
            "lai_suat_sau_uu_dai": "LS tiết kiệm 12 tháng + 3.5%/năm",
            "ky_han_toi_da_thang": 120,
            "dti_toi_da": 60.0,
            "ltv_toi_da": 75.0,
            "dieu_kien": "Có giấy phép kinh doanh, hoạt động ≥ 1 năm",
            "ghi_chu": "Áp dụng cho hộ kinh doanh và doanh nghiệp nhỏ"
        },
        {
            "ma_san_pham": "TC_DS",
            "ten_san_pham": "Vay Đời sống (Thế chấp)",
            "loai_vay": "the_chap",
            "lai_suat_uu_dai": 6.0,
            "thoi_gian_uu_dai_thang": 3,
            "lai_suat_sau_uu_dai": "LS tiết kiệm 12 tháng + 4.0%/năm",
            "ky_han_toi_da_thang": 240,
            "dti_toi_da": 55.0,
            "ltv_toi_da": 70.0,
            "dieu_kien": "Thu nhập ổn định, có tài sản đảm bảo",
            "ghi_chu": "Phục vụ nhu cầu tiêu dùng cá nhân"
        },
        {
            "ma_san_pham": "TC_OTO",
            "ten_san_pham": "Vay Mua xe Ô tô (Thế chấp)",
            "loai_vay": "the_chap",
            "lai_suat_uu_dai": 5.9,
            "thoi_gian_uu_dai_thang": 9,
            "lai_suat_sau_uu_dai": "LS tiết kiệm 12 tháng + 3.8%/năm",
            "ky_han_toi_da_thang": 96,
            "dti_toi_da": 55.0,
            "ltv_toi_da": 70.0,
            "dieu_kien": "Xe mới hoặc đã qua sử dụng ≤ 5 năm",
            "ghi_chu": "Tài trợ lên đến 70% giá trị xe"
        },
        {
            "ma_san_pham": "TC_XD",
            "ten_san_pham": "Vay Xây dựng / Sửa chữa nhà (Thế chấp)",
            "loai_vay": "the_chap",
            "lai_suat_uu_dai": 5.5,
            "thoi_gian_uu_dai_thang": 12,
            "lai_suat_sau_uu_dai": "LS tiết kiệm 12 tháng + 3.5%/năm",
            "ky_han_toi_da_thang": 300,
            "dti_toi_da": 55.0,
            "ltv_toi_da": 73.0,
            "dieu_kien": "Có giấy phép xây dựng hoặc dự toán thi công",
            "ghi_chu": "Giải ngân theo tiến độ thi công"
        },
        {
            "ma_san_pham": "TC_BDS",
            "ten_san_pham": "Vay Mua / Bán Bất động sản (Thế chấp)",
            "loai_vay": "the_chap",
            "lai_suat_uu_dai": 3.9,
            "thoi_gian_uu_dai_thang": 3,
            "lai_suat_sau_uu_dai": "LS tiết kiệm 12 tháng + 3.5%/năm",
            "ky_han_toi_da_thang": 420,
            "dti_toi_da": 50.0,
            "ltv_toi_da": 70.0,
            "dieu_kien": "Có hợp đồng mua bán / chuyển nhượng hợp lệ",
            "ghi_chu": "Thời hạn lên đến 35 năm, ưu đãi KH trẻ 25-40 tuổi"
        },
        # Vay tín chấp
        {
            "ma_san_pham": "TCHAP_TC",
            "ten_san_pham": "Vay Tín chấp Tổ chức đoàn thể",
            "loai_vay": "tin_chap",
            "lai_suat_uu_dai": 7.5,
            "thoi_gian_uu_dai_thang": 0,
            "lai_suat_sau_uu_dai": "Cố định 7.5%/năm trong suốt kỳ hạn",
            "ky_han_toi_da_thang": 60,
            "dti_toi_da": 50.0,
            "ltv_toi_da": None,
            "dieu_kien": "Là thành viên Hội Phụ nữ, Hội Nông dân, có xác nhận",
            "ghi_chu": "Hạn mức tối đa 100 triệu"
        },
        {
            "ma_san_pham": "TCHAP_DT",
            "ten_san_pham": "Vay Tín chấp Ngành nghề đặc thù",
            "loai_vay": "tin_chap",
            "lai_suat_uu_dai": 7.0,
            "thoi_gian_uu_dai_thang": 3,
            "lai_suat_sau_uu_dai": "LS tiết kiệm 12 tháng + 5.0%/năm",
            "ky_han_toi_da_thang": 60,
            "dti_toi_da": 50.0,
            "ltv_toi_da": None,
            "dieu_kien": "Cán bộ HCSN, Y tế, Giáo dục hoặc hộ trồng lúa có xác nhận",
            "ghi_chu": "Ưu đãi cho khối hành chính sự nghiệp"
        },
        {
            "ma_san_pham": "TCHAP_DT2",
            "ten_san_pham": "Vay Tín chấp Dòng tiền ổn định",
            "loai_vay": "tin_chap",
            "lai_suat_uu_dai": 6.8,
            "thoi_gian_uu_dai_thang": 6,
            "lai_suat_sau_uu_dai": "LS tiết kiệm 12 tháng + 4.5%/năm",
            "ky_han_toi_da_thang": 84,
            "dti_toi_da": 50.0,
            "ltv_toi_da": None,
            "dieu_kien": "Chi lương qua KienlongBank ≥ 6 tháng",
            "ghi_chu": "Ưu đãi đặc biệt cho khách hàng lương"
        },
    ]

    for rule in rules:
        cursor.execute("""
            INSERT INTO lending_rules 
            (ma_san_pham, ten_san_pham, loai_vay, lai_suat_uu_dai,
             thoi_gian_uu_dai_thang, lai_suat_sau_uu_dai, ky_han_toi_da_thang,
             dti_toi_da, ltv_toi_da, dieu_kien, ghi_chu)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule["ma_san_pham"], rule["ten_san_pham"], rule["loai_vay"],
            rule["lai_suat_uu_dai"], rule["thoi_gian_uu_dai_thang"],
            rule["lai_suat_sau_uu_dai"], rule["ky_han_toi_da_thang"],
            rule["dti_toi_da"], rule.get("ltv_toi_da"),
            rule["dieu_kien"], rule["ghi_chu"],
        ))


# ---------------------------------------------------------------------------
# Thao tác dữ liệu
# ---------------------------------------------------------------------------

def save_inquiry(data: dict):
    """Lưu một bản ghi truy vấn vào lịch sử."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inquiry_history 
        (timestamp, ho_ten, cccd, thu_nhap, so_tien_vay, san_pham_vay,
         dti_ratio, ltv_ratio, credit_score, xep_hang, quyet_dinh, chi_tiet_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        data.get("ho_ten", ""),
        data.get("cccd", ""),
        data.get("thu_nhap"),
        data.get("so_tien_vay"),
        data.get("san_pham_vay", ""),
        data.get("dti_ratio"),
        data.get("ltv_ratio"),
        data.get("credit_score"),
        data.get("xep_hang", ""),
        data.get("quyet_dinh", ""),
        json.dumps(data, ensure_ascii=False),
    ))
    conn.commit()
    conn.close()


def get_history(limit: int = 50) -> list[dict]:
    """Lấy lịch sử truy vấn gần nhất."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM inquiry_history ORDER BY id DESC LIMIT ?", (limit,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_lending_rules(loai_vay: str = None) -> list[dict]:
    """Lấy danh sách quy tắc cho vay, có thể lọc theo loại."""
    conn = get_connection()
    cursor = conn.cursor()
    if loai_vay:
        cursor.execute(
            "SELECT * FROM lending_rules WHERE loai_vay = ?", (loai_vay,)
        )
    else:
        cursor.execute("SELECT * FROM lending_rules")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_rule_by_product(ma_san_pham: str) -> dict | None:
    """Lấy quy tắc cho vay của một sản phẩm cụ thể."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM lending_rules WHERE ma_san_pham = ?", (ma_san_pham,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

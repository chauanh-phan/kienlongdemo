"""
mock_cic.py — Module Giả lập Tra cứu CIC
-------------------------------------------
Giả lập Trung tâm Thông tin Tín dụng Quốc gia Việt Nam (CIC).

Trong thực tế, ngân hàng sẽ gọi API đến CIC để kiểm tra lịch sử
tín dụng của khách hàng. Module này tạo dữ liệu giả lập nhất quán
(deterministic) dựa trên số CCCD để phục vụ demo và bảo vệ đồ án.

Phân nhóm nợ theo quy định NHNN:
  - Nhóm 1: Nợ đủ tiêu chuẩn (quá hạn ≤ 10 ngày)
  - Nhóm 2: Nợ cần chú ý (quá hạn 10-90 ngày)
  - Nhóm 3: Nợ dưới tiêu chuẩn (quá hạn 90-180 ngày)
  - Nhóm 4: Nợ nghi ngờ (quá hạn 180-360 ngày)
  - Nhóm 5: Nợ có khả năng mất vốn (quá hạn > 360 ngày)

Tác giả : Phan Thị Châu Anh
Phiên bản: 1.0.0
"""

import hashlib
from datetime import datetime, timedelta


def _hash_cccd(cccd: str) -> int:
    """Tạo giá trị hash deterministic từ số CCCD."""
    h = hashlib.sha256(cccd.encode()).hexdigest()
    return int(h, 16)


def tra_cuu_cic(cccd: str) -> dict:
    """
    Tra cứu lịch sử tín dụng giả lập từ CIC.

    Params:
        cccd: Số căn cước công dân (12 chữ số)

    Returns:
        dict chứa thông tin tín dụng giả lập:
        - trang_thai: "clean" | "warning" | "blacklist"
        - nhom_no_cao_nhat: 1-5
        - so_khoan_vay_hien_tai: int
        - tong_du_no: float (VND)
        - lich_su_tra_no: str mô tả
        - ngay_cap_nhat: str ISO date
        - ghi_chu: str
    """
    if not cccd or len(cccd) != 12 or not cccd.isdigit():
        return {
            "loi": True,
            "thong_bao": "Số CCCD không hợp lệ. Yêu cầu 12 chữ số.",
            "trang_thai": "error",
        }

    seed = _hash_cccd(cccd)

    # --- Xác định nhóm khách hàng dựa trên hash ---
    # ~60% clean, ~25% warning (nhóm 2), ~10% nhóm 3, ~5% nhóm 4-5
    pct = seed % 100

    if pct < 60:
        # Khách hàng tốt — không có nợ xấu
        nhom_no = 1
        trang_thai = "clean"
        so_khoan_vay = seed % 3  # 0-2 khoản
        tong_du_no = (seed % 500 + 50) * 1_000_000 if so_khoan_vay > 0 else 0
        lich_su = "Thanh toán đúng hạn, không phát sinh nợ quá hạn"
        ghi_chu = "Khách hàng có lịch sử tín dụng tốt"

    elif pct < 85:
        # Cảnh báo — có nợ nhóm 2
        nhom_no = 2
        trang_thai = "warning"
        so_khoan_vay = (seed % 3) + 1  # 1-3 khoản
        tong_du_no = (seed % 800 + 200) * 1_000_000
        lich_su = "Đã phát sinh chậm trả 1-2 kỳ trong 12 tháng gần nhất"
        ghi_chu = "Cần xem xét kỹ khả năng trả nợ"

    elif pct < 95:
        # Nợ dưới tiêu chuẩn — nhóm 3
        nhom_no = 3
        trang_thai = "warning"
        so_khoan_vay = (seed % 4) + 2  # 2-5 khoản
        tong_du_no = (seed % 1200 + 500) * 1_000_000
        lich_su = "Quá hạn 90-180 ngày ở 1 khoản vay, đã cơ cấu lại"
        ghi_chu = "Nợ dưới tiêu chuẩn — yêu cầu thẩm định bổ sung"

    else:
        # Nợ xấu — nhóm 4-5
        nhom_no = 4 + (seed % 2)
        trang_thai = "blacklist"
        so_khoan_vay = (seed % 5) + 3  # 3-7 khoản
        tong_du_no = (seed % 2000 + 1000) * 1_000_000
        lich_su = "Có khoản nợ quá hạn trên 180 ngày, chưa xử lý"
        ghi_chu = "Nợ xấu — khuyến nghị TỪ CHỐI cho vay mới"

    # Ngày cập nhật: deterministic, trong 30 ngày gần nhất
    ngay_offset = seed % 30
    ngay_cap_nhat = (datetime.now() - timedelta(days=ngay_offset)).strftime("%Y-%m-%d")

    return {
        "loi": False,
        "cccd": cccd,
        "trang_thai": trang_thai,
        "nhom_no_cao_nhat": nhom_no,
        "so_khoan_vay_hien_tai": so_khoan_vay,
        "tong_du_no": tong_du_no,
        "lich_su_tra_no": lich_su,
        "ngay_cap_nhat": ngay_cap_nhat,
        "ghi_chu": ghi_chu,
        "nguon": "Trung tâm Thông tin Tín dụng Quốc gia Việt Nam (CIC) — Dữ liệu giả lập",
    }

"""
main.py — FastAPI Robo-Advisor Service
---------------------------------------
REST API cho hệ thống Robo-Advisor tư vấn vay vốn cá nhân
KienlongBank — Phòng Giao dịch Hải Châu.

Endpoints:
  GET  /health                — Kiểm tra trạng thái dịch vụ
  POST /api/v1/assess         — Đánh giá hồ sơ tổng hợp (endpoint chính)
  POST /api/v1/cic/check      — Tra cứu CIC (giả lập)
  GET  /api/v1/lending-rules  — Bảng quy tắc cho vay
  GET  /api/v1/history        — Lịch sử truy vấn

Tác giả : Phan Thị Châu Anh
Phiên bản: 1.0.0
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from decision_engine import danh_gia_tong_hop, tinh_tra_gop_hang_thang
from mock_cic import tra_cuu_cic
from database import init_database, save_inquiry, get_history, get_lending_rules, get_rule_by_product

# Đường dẫn tới thư mục frontend (thư mục cha của backend/)
FRONTEND_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Khởi tạo ứng dụng
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KienlongBank — Hệ thống Robo-Advisor Tư vấn Vay vốn",
    description=(
        "## 🤖 Robo-Advisor API\n\n"
        "Hệ thống tư vấn vay vốn cá nhân tự động tích hợp:\n"
        "- **Decision Engine**: Tính toán DTI, LTV, Chấm điểm tín dụng\n"
        "- **Mock CIC**: Giả lập tra cứu lịch sử tín dụng\n"
        "- **Loan Optimizer**: Tối ưu hoá khoản vay\n\n"
        "### Tác giả\n"
        "**Phan Thị Châu Anh** — Đề tài thực tập tại KienlongBank PGD Hải Châu"
    ),
    version="1.0.0",
    contact={
        "name": "Phan Thị Châu Anh",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — cho phép frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo database khi server start
init_database()

_SERVICE_START = datetime.utcnow().isoformat() + "Z"

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

# Mapping sản phẩm vay frontend → mã sản phẩm database
PRODUCT_MAP = {
    # Thế chấp
    "sxkd": "TC_SXKD",
    "doi_song": "TC_DS",
    "mua_xe": "TC_OTO",
    "xay_dung": "TC_XD",
    "bds": "TC_BDS",
    # Tín chấp
    "to_chuc": "TCHAP_TC",
    "dac_thu": "TCHAP_DT",
    "dong_tien": "TCHAP_DT2",
}


class HoSoVayRequest(BaseModel):
    """Thông tin hồ sơ vay cần đánh giá."""

    # Thông tin cá nhân
    ho_ten: str = Field(
        default="", description="Họ tên khách hàng (không bắt buộc)"
    )
    cccd: str = Field(
        ..., min_length=12, max_length=12,
        description="Số căn cước công dân (12 chữ số)"
    )
    tuoi: int = Field(
        ..., ge=18, le=70,
        description="Tuổi khách hàng (18-70)"
    )
    gioi_tinh: str = Field(
        default="Nam", description="Giới tính: Nam / Nữ"
    )
    nghe_nghiep: str = Field(
        ..., description="Mã nghề nghiệp: hcsn | hoi_doan | kinh_doanh | khac"
    )
    loai_cu_tru: str = Field(
        ..., description="Loại cư trú: Owned | Rented | Mortgage"
    )

    # Thông tin vay
    loai_vay: str = Field(
        ..., description="Loại hình vay: the_chap | tin_chap"
    )
    san_pham_vay: str = Field(
        ..., description="Mã sản phẩm vay: sxkd | doi_song | mua_xe | xay_dung | bds | to_chuc | dac_thu | dong_tien"
    )
    so_tien_vay: float = Field(
        ..., gt=0, description="Số tiền đề nghị vay (VND)"
    )
    ky_han_thang: int = Field(
        ..., ge=3, le=420, description="Kỳ hạn vay (tháng, 3-420)"
    )

    # Thông tin tài chính
    thu_nhap_thang: float = Field(
        ..., gt=0, description="Thu nhập hàng tháng (VND)"
    )
    no_hien_tai_thang: float = Field(
        default=0, ge=0,
        description="Tổng nợ trả hàng tháng hiện tại (VND)"
    )
    gia_tri_tsdb: Optional[float] = Field(
        default=None, ge=0,
        description="Giá trị tài sản đảm bảo (VND, chỉ cần cho vay thế chấp)"
    )
    co_no_xau: bool = Field(
        default=False,
        description="Khách hàng tự khai có nợ xấu trong 2 năm gần nhất"
    )
    so_khoan_vay_hien_tai: int = Field(
        default=0, ge=0,
        description="Số khoản vay đang hoạt động"
    )

    # Lãi suất ưu đãi
    thoi_gian_uu_dai: str = Field(
        default="3th", description="Giai đoạn ưu đãi: 3th | 9th | 18th"
    )


class CICCheckRequest(BaseModel):
    """Request tra cứu CIC."""
    cccd: str = Field(
        ..., min_length=12, max_length=12,
        description="Số căn cước công dân"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    summary="Kiểm tra trạng thái dịch vụ",
    tags=["Hạ tầng"],
)
def health():
    """Kiểm tra dịch vụ có đang hoạt động không."""
    return {
        "status": "healthy",
        "service": "KienlongBank Robo-Advisor API",
        "version": "1.0.0",
        "uptime_since": _SERVICE_START,
    }


@app.post(
    "/api/v1/assess",
    summary="Đánh giá hồ sơ vay tổng hợp",
    tags=["Tư vấn"],
)
def assess(ho_so: HoSoVayRequest):
    """
    **Endpoint chính** — Nhận hồ sơ vay và trả về kết quả đánh giá tổng hợp.

    Flow xử lý:
    1. Tra cứu CIC (giả lập) → Kiểm tra lịch sử tín dụng
    2. Tra cứu quy tắc cho vay → Lấy lãi suất, ngưỡng DTI/LTV
    3. Tính DTI (Debt-to-Income)
    4. Tính LTV (Loan-to-Value) — nếu vay thế chấp
    5. Chấm điểm tín dụng (Weighted Scoring Matrix)
    6. Tối ưu hoá khoản vay
    7. Quyết định cuối cùng + Khuyến nghị
    """
    # 1. Tra cứu CIC
    cic_result = tra_cuu_cic(ho_so.cccd)

    nhom_no_cic = cic_result.get("nhom_no_cao_nhat", 1) if not cic_result.get("loi") else 1
    so_khoan_vay_cic = cic_result.get("so_khoan_vay_hien_tai", 0) if not cic_result.get("loi") else 0

    # 2. Tra cứu quy tắc cho vay
    ma_sp = PRODUCT_MAP.get(ho_so.san_pham_vay, ho_so.san_pham_vay)
    rule = get_rule_by_product(ma_sp)

    # Lấy lãi suất từ rule, fallback nếu không tìm thấy
    if rule:
        lai_suat_nam = rule["lai_suat_uu_dai"]
        dti_toi_da = rule["dti_toi_da"]
        ltv_toi_da = rule.get("ltv_toi_da") or 75.0
        ten_san_pham = rule["ten_san_pham"]
        thoi_gian_uu_dai = rule["thoi_gian_uu_dai_thang"]
        lai_suat_sau_uu_dai = rule["lai_suat_sau_uu_dai"]
    else:
        lai_suat_nam = 7.0
        dti_toi_da = 50.0
        ltv_toi_da = 75.0
        ten_san_pham = "Sản phẩm vay"
        thoi_gian_uu_dai = 3
        lai_suat_sau_uu_dai = "LS tiết kiệm 12 tháng + 4.0%/năm"

    # 3-6. Đánh giá tổng hợp
    gia_tri_tsdb = ho_so.gia_tri_tsdb if ho_so.loai_vay == "the_chap" else None

    ket_qua = danh_gia_tong_hop(
        tuoi=ho_so.tuoi,
        thu_nhap_thang=ho_so.thu_nhap_thang,
        nghe_nghiep=ho_so.nghe_nghiep,
        so_tien_vay=ho_so.so_tien_vay,
        ky_han_thang=ho_so.ky_han_thang,
        lai_suat_nam=lai_suat_nam,
        no_hien_tai_thang=ho_so.no_hien_tai_thang,
        gia_tri_tsdb=gia_tri_tsdb,
        loai_cu_tru=ho_so.loai_cu_tru,
        loai_vay=ho_so.loai_vay,
        co_no_xau=ho_so.co_no_xau,
        nhom_no_cic=nhom_no_cic,
        so_khoan_vay_cic=so_khoan_vay_cic,
        dti_toi_da_quy_dinh=dti_toi_da,
    )

    # 7. Lưu vào lịch sử
    save_inquiry({
        "ho_ten": ho_so.ho_ten,
        "cccd": ho_so.cccd,
        "thu_nhap": ho_so.thu_nhap_thang,
        "so_tien_vay": ho_so.so_tien_vay,
        "san_pham_vay": ten_san_pham,
        "dti_ratio": ket_qua["dti"]["dti_ratio"],
        "ltv_ratio": ket_qua["ltv"].get("ltv_ratio"),
        "credit_score": ket_qua["credit_scoring"]["credit_score"],
        "xep_hang": ket_qua["credit_scoring"]["xep_hang"],
        "quyet_dinh": ket_qua["quyet_dinh_cuoi_cung"],
    })

    # Response đầy đủ
    return {
        "ho_so": {
            "ho_ten": ho_so.ho_ten,
            "cccd": ho_so.cccd[-4:].rjust(12, "*"),  # Mask CCCD
            "tuoi": ho_so.tuoi,
            "nghe_nghiep": ho_so.nghe_nghiep,
            "thu_nhap_thang": ho_so.thu_nhap_thang,
        },
        "san_pham": {
            "ten": ten_san_pham,
            "lai_suat_uu_dai": lai_suat_nam,
            "thoi_gian_uu_dai_thang": thoi_gian_uu_dai,
            "lai_suat_sau_uu_dai": lai_suat_sau_uu_dai,
            "so_tien_vay": ho_so.so_tien_vay,
            "ky_han_thang": ho_so.ky_han_thang,
            "tra_gop_hang_thang": ket_qua["dti"]["tra_gop_hang_thang"],
        },
        "cic": cic_result,
        "phan_tich": {
            "dti": ket_qua["dti"],
            "ltv": ket_qua["ltv"],
            "credit_scoring": ket_qua["credit_scoring"],
            "toi_uu_khoan_vay": ket_qua["toi_uu_khoan_vay"],
        },
        "ket_luan": {
            "quyet_dinh": ket_qua["quyet_dinh_cuoi_cung"],
            "ly_do": ket_qua["ly_do"],
            "khuyen_nghi_bo_sung": ket_qua["khuyen_nghi_bo_sung"],
        },
        "timestamp": datetime.now().isoformat(),
    }


@app.post(
    "/api/v1/cic/check",
    summary="Tra cứu lịch sử tín dụng CIC",
    tags=["CIC"],
)
def cic_check(req: CICCheckRequest):
    """
    Tra cứu lịch sử tín dụng khách hàng qua Trung tâm Thông tin
    Tín dụng Quốc gia (CIC) — **Dữ liệu giả lập cho mục đích demo**.
    """
    return tra_cuu_cic(req.cccd)


@app.get(
    "/api/v1/lending-rules",
    summary="Bảng quy tắc cho vay",
    tags=["Tra cứu"],
)
def lending_rules(loai_vay: str = Query(default=None, description="Lọc theo loại: the_chap | tin_chap")):
    """Lấy danh sách quy tắc cho vay của KienlongBank."""
    rules = get_lending_rules(loai_vay)
    return {"count": len(rules), "rules": rules}


@app.get(
    "/api/v1/history",
    summary="Lịch sử truy vấn",
    tags=["Tra cứu"],
)
def history(limit: int = Query(default=20, ge=1, le=100)):
    """Lấy lịch sử các lần đánh giá hồ sơ gần nhất."""
    records = get_history(limit)
    return {"count": len(records), "records": records}


# ---------------------------------------------------------------------------
# Phục vụ Frontend (index.html + static files)
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def serve_frontend():
    """Trả về trang chủ frontend."""
    return FileResponse(FRONTEND_DIR / "index.html")


# Mount thư mục gốc dự án để phục vụ file tĩnh (logo, CSS, JS, ...)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

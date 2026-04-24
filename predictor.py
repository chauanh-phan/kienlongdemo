"""
Business logic: data mapping, DTI/LTV rules, ML prediction, rate lookup.
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Tuple

import joblib
import pandas as pd

from schemas import (
    AssessRequest, AssessResponse,
    DTIResult, LTVResult, LoanOptimization,
    PhanTich, SanPham, KetLuan,
)

# ---------------------------------------------------------------------------
# Paths & model loading
# ---------------------------------------------------------------------------
MODEL_DIR = Path(__file__).resolve().parent.parent / "model"

_pipeline     = joblib.load(MODEL_DIR / "best_loan_recommender.pkl")
_feature_cols = joblib.load(MODEL_DIR / "feature_cols.pkl")

# ---------------------------------------------------------------------------
# Mapping tables (frontend codes → training-data Vietnamese strings)
# ---------------------------------------------------------------------------
GIOI_TINH_MAP = {
    "Nam": "Nam", "nam": "Nam",
    "Nữ": "Nữ",  "nu": "Nữ", "Nu": "Nữ",
}

NHOM_TUOI_MAP = {
    "duoi25": "Dưới 25",
    "25_40":  "Từ 25 - 40",
    "tren40": "Trên 40",
}

LOAI_VAY_MAP = {          # → "Hình thức vay"
    "tin_chap": "Tín chấp",
    "the_chap": "Thế chấp",
}

CO_TSBD_MAP = {           # → "Có TSBĐ không?"
    "tin_chap": "Không",
    "the_chap": "Có",
}

# Maps frontend san_pham_vay codes → "Mục đích sử dụng" column values in training data
PURPOSE_MAP = {
    # Tín chấp
    "hoi_phu_nu":    "Hội Phụ Nữ",
    "hoi_nong_dan":  "Hội Nông dân",
    "trong_lua":     "Trồng lúa",
    "hanh_chinh":    "Hành chính sự nghiệp",
    "luong_y_truong":"Chi Lương / Y / Trường học",
    # Thế chấp
    "sxkd":          "Vay SXKD",
    "doi_song":      "Vay phục vụ đời sống",
    "mua_xe":        "Vay mua xe ô tô",
    "xay_dung":      "Vay xây dựng, sửa chữa nhà ở",
    "bds":           "Vay mua/ bán, chuyển nhượng BĐS",
    # Legacy codes kept for backward compatibility
    "to_chuc":       "Hội Phụ Nữ",
    "dac_thu":       "Hành chính sự nghiệp",
    "dong_tien":     "Chi Lương / Y / Trường học",
}

YN_MAP = {True: "Có", False: "Không", "co": "Có", "khong": "Không"}

# ---------------------------------------------------------------------------
# Reference interest rates by product  (annual %)
# ---------------------------------------------------------------------------
RATE_TABLE: dict[str, float] = {
    "Vay Tín chấp - Hội Phụ Nữ":              15.5,
    "Vay Tín chấp - Hội Nông dân":             14.0,
    "Vay Tín chấp - Trồng lúa":                14.0,
    "Vay Tín chấp - Hành chính sự nghiệp":     18.0,
    "Vay Tín chấp - Lương/Y/Trường học":        18.0,
    "Vay Thế chấp - SXKD":                     13.0,
    "Vay Thế chấp - Phục vụ đời sống":         13.0,
    "Vay Thế chấp - Mua xe ô tô":              13.0,
    "Vay Thế chấp - Xây sửa nhà":              13.0,
    "Vay Thế chấp - BĐS":                      13.0,
}
DEFAULT_RATE = 9.0

PROMO_DISCOUNT: dict[str, float] = {
    "3th":  2.0,
    "9th":  1.5,
    "18th": 1.0,
}
PROMO_MONTHS: dict[str, int] = {
    "3th": 3, "9th": 9, "18th": 18
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _age_to_group(age: int) -> str:
    if age < 25:
        return "Dưới 25"
    if age <= 40:
        return "Từ 25 - 40"
    return "Trên 40"


def _calculate_installment(principal: float, annual_rate_pct: float, months: int, method: str) -> float:
    """
    Calculate the first (highest) installment based on method.
    Returns monthly-equivalent value for DTI purposes.
    """
    if months <= 0 or principal <= 0:
        return 0.0
    
    r_annual = annual_rate_pct / 100
    
    # Method mappings:
    # 1. Monthly interest, equal principal: (P/n) + (P * r_monthly)
    if method == "lai_thang_goc_chia_deu":
        return (principal / months) + (principal * r_annual / 12)
    
    # 2. Quarterly interest, equal principal: (P/q) + (P * r_quarterly)
    # Then divide by 3 for monthly DTI
    if method == "lai_quy_goc_chia_deu":
        quarters = max(1, months // 3)
        return ((principal / quarters) + (principal * r_annual / 4)) / 3
    
    # 3. Monthly interest, principal at end: P * r_monthly
    if method == "lai_thang_goc_cuoi_ky":
        return principal * r_annual / 12
    
    # 4. Quarterly interest, principal at end: (P * r_quarterly) / 3
    if method == "lai_quy_goc_cuoi_ky":
        return (principal * r_annual / 4) / 3
    
    # Default (Fixed PMT):
    r = r_annual / 12
    if r == 0: return principal / months
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)


def _calc_dti(thu_nhap: float, no_hien_tai: float, no_moi: float = 0.0) -> float:
    """DTI = (existing + new monthly debt) / monthly income × 100"""
    if thu_nhap <= 0:
        return 0.0
    return round((no_hien_tai + no_moi) / thu_nhap * 100, 2)


def _calc_ltv(so_tien_vay: float, gia_tri_tsdb: float) -> float:
    """LTV = loan amount / collateral value × 100"""
    if gia_tri_tsdb <= 0:
        return 0.0
    return round(so_tien_vay / gia_tri_tsdb * 100, 2)


# ---------------------------------------------------------------------------
# Core assessment function
# ---------------------------------------------------------------------------
def assess(req: AssessRequest) -> AssessResponse:
    reasons: list[str] = []

    # ------------------------------------------------------------------
    # 1. LTV cap: auto-reduce loan to 80 % of collateral
    # ------------------------------------------------------------------
    so_tien_vay = req.so_tien_vay
    ltv_da_dieu_chinh = False

    if req.loai_vay == "the_chap" and req.gia_tri_tsdb > 0:
        max_safe = math.floor(req.gia_tri_tsdb * 0.80 / 1_000_000) * 1_000_000
        if so_tien_vay > max_safe:
            so_tien_vay = max_safe
            ltv_da_dieu_chinh = True
            reasons.append(
                f"Số tiền vay đã được điều chỉnh xuống {so_tien_vay:,.0f} VND "
                f"để đảm bảo ngưỡng LTV 80%."
            )

    # ------------------------------------------------------------------
    # 4. Determine expected product & rate (pre-ML or lookup)
    # ------------------------------------------------------------------
    # We briefly predict product to get the base rate for DTI inclusion
    # (Actual ML row build happens next)
    
    # Find matching product from PURPOSE_MAP to get a temporary predicted_product_str
    prod_str = PURPOSE_MAP.get(req.san_pham_vay, "Vay phục vụ đời sống")
    loai_str = LOAI_VAY_MAP.get(req.loai_vay, "Thế chấp")
    # Search for matching full name in RATE_TABLE
    predicted_product = "Vay Thế chấp - Phục vụ đời sống" # Default
    for k in RATE_TABLE.keys():
        if prod_str in k and loai_str in k:
            predicted_product = k
            break

    base_rate = RATE_TABLE.get(predicted_product, DEFAULT_RATE)
    
    # ------------------------------------------------------------------
    # 5. Calculate monthly installment and DTI
    # ------------------------------------------------------------------
    monthly_pay = round(_calculate_installment(
        so_tien_vay, base_rate, req.ky_han_thang, req.phuong_thuc_tra_no
    ), 0)
    
    dti_ratio = _calc_dti(req.thu_nhap_thang, req.no_hien_tai_thang, monthly_pay)
    ltv_ratio = _calc_ltv(so_tien_vay, req.gia_tri_tsdb)

    dti_ok = dti_ratio <= 80.0
    ltv_ok = ltv_ratio <= 80.0 or req.loai_vay == "tin_chap"

    # ------------------------------------------------------------------
    # 6. Build feature row for ML model
    # ------------------------------------------------------------------
    row = {
        "Giới tính":                              GIOI_TINH_MAP.get(req.gioi_tinh, req.gioi_tinh),
        "Nhóm tuổi":                              _age_to_group(req.tuoi),
        "Có TSBĐ không?":                         CO_TSBD_MAP.get(req.loai_vay, "Không"),
        "Hình thức vay":                          LOAI_VAY_MAP.get(req.loai_vay, req.loai_vay),
        "Mục đích sử dụng":                       PURPOSE_MAP.get(req.san_pham_vay, req.san_pham_vay),
        "Thu nhập":                               req.thu_nhap_thang,
        "Số lượng khoản vay đang hoạt động?":     req.so_khoan_vay_hien_tai,
        "Tổng số tiền trả nợ các khoản vay khác": req.no_hien_tai_thang,
        "Số tiền muốn vay":                       so_tien_vay,
        "Giá trị BĐS":                            req.gia_tri_tsdb,
        "Thời gian vay (tháng)":                  req.ky_han_thang,
        "Lịch sử nợ xấu tín dụng trong 05 năm gần nhất":                  YN_MAP[req.co_no_xau],
        "Lịch sử chậm thanh toán thẻ tín dụng trong 03 năm gần nhất":     YN_MAP[req.cham_thanh_toan],
        "Nợ cần chú ý trong vòng 12 tháng gần nhất":                      YN_MAP[req.no_can_chu_y],
        "Kết quả DTI":                            dti_ratio,
        "Kết quả LTV":                            ltv_ratio,
    }
    df_input = pd.DataFrame([row]).reindex(columns=_feature_cols)

    # ML prediction (Final decision on product)
    predicted_product = _pipeline.predict(df_input)[0]
    base_rate   = RATE_TABLE.get(predicted_product, DEFAULT_RATE)
    
    # ------------------------------------------------------------------
    # 7. Promo rates & Final Pay
    # ------------------------------------------------------------------
    discount    = PROMO_DISCOUNT.get(req.thoi_gian_uu_dai, 1.5)
    promo_rate  = round(max(base_rate - discount, 4.0), 2)
    promo_months = PROMO_MONTHS.get(req.thoi_gian_uu_dai, 3)
    # Re-calculate with final predicted product rate if different
    monthly_pay = round(_calculate_installment(
        so_tien_vay, base_rate, req.ky_han_thang, req.phuong_thuc_tra_no
    ), 0)

    # ------------------------------------------------------------------
    # 6. Decision logic
    # ------------------------------------------------------------------
    if dti_ratio > 80:
        quyet_dinh = "Từ chối"
        reasons.append(f"DTI {dti_ratio}% vượt ngưỡng 80% — không đủ điều kiện.")
    elif 70 < dti_ratio <= 80:
        if req.co_no_xau or req.cham_thanh_toan:
            quyet_dinh = "Từ chối"
            reasons.append(f"DTI {dti_ratio}% ở mức rủi ro (70-80%) và có lịch sử nợ xấu / chậm thanh toán.")
        else:
            quyet_dinh = "Cần xem xét"
            reasons.append(f"DTI {dti_ratio}% ở mức 70-80% — chuyển lên chuyên viên phán quyết.")
    else:
        # DTI <= 70: we still check credit history safety gates
        if req.co_no_xau:
            quyet_dinh = "Cần xem xét"
            reasons.append("Có lịch sử nợ xấu trong 5 năm gần nhất.")
        elif req.cham_thanh_toan or req.no_can_chu_y:
            quyet_dinh = "Cần xem xét"
            reasons.append("Có vấn đề về lịch sử thanh toán / nợ cần chú ý.")
        else:
            quyet_dinh = "Chấp thuận"
            reasons.append("Hồ sơ đáp ứng DTI <= 70% và các tiêu chí xét duyệt.")

    if not reasons or reasons[-1].startswith("Hồ sơ"):
        reasons.append(f"Sản phẩm gợi ý: {predicted_product}.")

    # ------------------------------------------------------------------
    # 7. Assemble response
    # ------------------------------------------------------------------
    return AssessResponse(
        khach_hang=req.ho_ten,
        phan_tich=PhanTich(
            dti=DTIResult(
                dti_ratio=dti_ratio,
                is_eligible=dti_ok,
                max_dti=80.0,
                mo_ta="Tỷ lệ nợ hiện tại / thu nhập hàng tháng.",
            ),
            ltv=LTVResult(
                ltv_ratio=ltv_ratio,
                is_eligible=ltv_ok,
                max_ltv=80.0,
                mo_ta="Tỷ lệ khoản vay / giá trị tài sản đảm bảo.",
            ),
            toi_uu_khoan_vay=LoanOptimization(
                so_tien_goc=req.so_tien_vay,
                vay_toi_da_an_toan=so_tien_vay,
                ltv_da_dieu_chinh=ltv_da_dieu_chinh,
                tra_gop_hang_thang=monthly_pay,
            ),
        ),
        san_pham=SanPham(
            ten=predicted_product,
            ma_san_pham=req.san_pham_vay,
            lai_suat_nam=base_rate,
            lai_suat_uu_dai=promo_rate,
            thoi_gian_uu_dai_thang=promo_months,
            so_tien_vay=so_tien_vay,
            tra_gop_hang_thang=monthly_pay,
        ),
        ket_luan=KetLuan(
            quyet_dinh=quyet_dinh,
            ly_do=reasons,
        ),
    )

"""
decision_engine.py — Lõi Hệ thống Ra quyết định Robo-Advisor
--------------------------------------------------------------
Module chứa toàn bộ logic nghiệp vụ tài chính cho hệ thống
tư vấn vay vốn tự động của KienlongBank.

Các công cụ phân tích:
  1. Tính toán DTI (Debt-to-Income Ratio)
  2. Tính toán LTV (Loan-to-Value Ratio)
  3. Chấm điểm tín dụng Rule-based (Credit Scoring 300-900)
  4. Tối ưu hoá khoản vay (Loan Optimizer)
  5. Đánh giá tổng hợp (Comprehensive Assessment)

Cơ sở nghiệp vụ:
  - Thông tư 39/2016/TT-NHNN về cho vay cá nhân
  - Quy định nội bộ KienlongBank về ngưỡng DTI, LTV
  - Hệ thống xếp hạng tín dụng nội bộ 10 bậc (AAA → D)

Tác giả : Phan Thị Châu Anh
Phiên bản: 1.0.0
"""


# ═══════════════════════════════════════════════════════════════
# 1. TÍNH TOÁN DTI (DEBT-TO-INCOME RATIO)
# ═══════════════════════════════════════════════════════════════

def tinh_tra_gop_hang_thang(so_tien_vay: float, lai_suat_nam: float,
                             ky_han_thang: int) -> float:
    """
    Tính số tiền trả góp hàng tháng theo phương pháp trả đều (PMT).

    Công thức: PMT = P × [r(1+r)^n] / [(1+r)^n - 1]
    Trong đó:
      P = Số tiền vay
      r = Lãi suất tháng = Lãi suất năm / 12
      n = Số kỳ trả (tháng)
    """
    if lai_suat_nam <= 0 or ky_han_thang <= 0:
        return so_tien_vay / max(ky_han_thang, 1)

    r = lai_suat_nam / 100 / 12  # Lãi suất tháng
    n = ky_han_thang

    # Công thức PMT chuẩn
    pmt = so_tien_vay * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    return round(pmt, 0)


def tinh_dti(thu_nhap_thang: float, no_hien_tai_thang: float,
             so_tien_vay: float, lai_suat_nam: float,
             ky_han_thang: int) -> dict:
    """
    Tính tỷ lệ DTI (Debt-to-Income Ratio).

    DTI = (Nợ hàng tháng hiện tại + Trả góp khoản vay mới) / Thu nhập tháng

    Ngưỡng theo quy định KienlongBank:
      ≤ 40%  : An toàn — Khách hàng có khả năng trả nợ tốt
      40-50% : Chấp nhận — Cần xem xét thêm nguồn thu nhập phụ
      50-60% : Cảnh báo — Rủi ro cao, cần TSĐB giá trị lớn
      > 60%  : Từ chối — Vượt ngưỡng an toàn cho vay

    Returns:
        dict chứa: dti_ratio, tra_gop_moi, tong_no_thang, danh_gia, muc_do
    """
    tra_gop_moi = tinh_tra_gop_hang_thang(so_tien_vay, lai_suat_nam, ky_han_thang)
    tong_no_thang = no_hien_tai_thang + tra_gop_moi

    if thu_nhap_thang <= 0:
        return {
            "dti_ratio": 100.0,
            "tra_gop_hang_thang": tra_gop_moi,
            "tong_no_hang_thang": tong_no_thang,
            "danh_gia": "Không xác định — Thu nhập bằng 0",
            "muc_do": "tu_choi",
        }

    dti = (tong_no_thang / thu_nhap_thang) * 100

    if dti <= 40:
        danh_gia = "AN TOÀN — Khách hàng có khả năng trả nợ tốt"
        muc_do = "an_toan"
    elif dti <= 50:
        danh_gia = "CHẤP NHẬN — Nên xem xét thêm nguồn thu nhập phụ"
        muc_do = "chap_nhan"
    elif dti <= 60:
        danh_gia = "CẢNH BÁO — Rủi ro cao, cần tài sản đảm bảo giá trị lớn"
        muc_do = "canh_bao"
    else:
        danh_gia = "VƯỢT NGƯỠNG — Tỷ lệ nợ / thu nhập quá cao, khuyến nghị từ chối"
        muc_do = "tu_choi"

    return {
        "dti_ratio": round(dti, 2),
        "tra_gop_hang_thang": tra_gop_moi,
        "tong_no_hang_thang": tong_no_thang,
        "danh_gia": danh_gia,
        "muc_do": muc_do,
    }


# ═══════════════════════════════════════════════════════════════
# 2. TÍNH TOÁN LTV (LOAN-TO-VALUE RATIO)
# ═══════════════════════════════════════════════════════════════

def tinh_ltv(so_tien_vay: float, gia_tri_tsdb: float) -> dict:
    """
    Tính tỷ lệ LTV (Loan-to-Value Ratio).

    LTV = Số tiền vay / Giá trị tài sản đảm bảo

    Ngưỡng theo quy định KienlongBank:
      ≤ 60%  : Rất tốt — Biên an toàn cao
      60-70% : Tốt — Trong ngưỡng cho phép
      70-75% : Chấp nhận — Gần ngưỡng tối đa
      > 75%  : Vượt quy định — Không đáp ứng yêu cầu

    Returns:
        dict chứa: ltv_ratio, danh_gia, muc_do
    """
    if gia_tri_tsdb is None or gia_tri_tsdb <= 0:
        return {
            "ltv_ratio": None,
            "danh_gia": "Không áp dụng — Vay tín chấp không yêu cầu TSĐB",
            "muc_do": "khong_ap_dung",
        }

    ltv = (so_tien_vay / gia_tri_tsdb) * 100

    if ltv <= 60:
        danh_gia = "RẤT TỐT — Biên an toàn cao, dư địa tài sản lớn"
        muc_do = "rat_tot"
    elif ltv <= 70:
        danh_gia = "TỐT — Trong ngưỡng cho phép của ngân hàng"
        muc_do = "tot"
    elif ltv <= 75:
        danh_gia = "CHẤP NHẬN — Gần ngưỡng tối đa, cần DTI thấp"
        muc_do = "chap_nhan"
    else:
        danh_gia = "VƯỢT QUY ĐỊNH — Số tiền vay vượt 75% giá trị TSĐB"
        muc_do = "tu_choi"

    return {
        "ltv_ratio": round(ltv, 2),
        "danh_gia": danh_gia,
        "muc_do": muc_do,
    }


# ═══════════════════════════════════════════════════════════════
# 3. CHẤM ĐIỂM TÍN DỤNG RULE-BASED (300 — 900)
# ═══════════════════════════════════════════════════════════════

# Bảng xếp hạng nội bộ KienlongBank
BANG_XEP_HANG = [
    (800, "AAA", "Xuất sắc — Rủi ro cực thấp"),
    (750, "AA",  "Rất tốt — Rủi ro rất thấp"),
    (700, "A",   "Tốt — Rủi ro thấp"),
    (650, "BBB", "Khá — Rủi ro chấp nhận được"),
    (600, "BB",  "Trung bình — Cần xem xét thêm"),
    (550, "B",   "Dưới trung bình — Rủi ro cao"),
    (500, "CCC", "Yếu — Rủi ro rất cao"),
    (450, "CC",  "Kém — Nguy cơ mất vốn"),
    (400, "C",   "Rất kém — Gần mất vốn"),
    (0,   "D",   "Mất vốn — Từ chối"),
]


def _xep_hang(diem: int) -> tuple:
    """Tra cứu xếp hạng từ bảng xếp hạng nội bộ."""
    for nguong, ma, mo_ta in BANG_XEP_HANG:
        if diem >= nguong:
            return ma, mo_ta
    return "D", "Mất vốn — Từ chối"


def cham_diem_tin_dung(
    tuoi: int,
    thu_nhap_thang: float,
    nghe_nghiep: str,
    dti_ratio: float,
    ltv_ratio: float | None,
    co_no_xau: bool,
    nhom_no_cic: int,
    so_khoan_vay_hien_tai: int,
    loai_cu_tru: str,
    ky_han_thang: int,
    loai_vay: str,
) -> dict:
    """
    Chấm điểm tín dụng theo hệ thống Rule-based đa tiêu chí.

    Phương pháp: Weighted Scoring Matrix
    ─────────────────────────────────────
    Mỗi tiêu chí được chấm điểm thành phần (0-100), sau đó nhân
    với trọng số tương ứng. Tổng điểm thành phần được quy đổi
    sang thang 300-900.

    Bảng trọng số:
    ┌──────────────────────┬──────────┬───────────────────────────┐
    │ Tiêu chí             │ Trọng số │ Cơ sở                     │
    ├──────────────────────┼──────────┼───────────────────────────┤
    │ Lịch sử tín dụng CIC│   25%    │ Yếu tố rủi ro hàng đầu   │
    │ Tỷ lệ DTI            │   20%    │ Khả năng trả nợ thực tế   │
    │ Thu nhập              │   15%    │ Năng lực tài chính        │
    │ Tỷ lệ LTV            │   10%    │ Biên an toàn tài sản      │
    │ Nghề nghiệp          │   10%    │ Ổn định nguồn thu nhập    │
    │ Tuổi                 │   8%     │ Kinh nghiệm tài chính     │
    │ Loại cư trú          │   7%     │ Ổn định đời sống          │
    │ Số khoản vay hiện tại│   5%     │ Mức độ tập trung nợ       │
    └──────────────────────┴──────────┴───────────────────────────┘

    Returns:
        dict chứa: credit_score, xep_hang, mo_ta, chi_tiet_diem, quyet_dinh
    """
    chi_tiet = {}

    # --- 1. Lịch sử tín dụng CIC (25%) ---
    if nhom_no_cic <= 1:
        diem_cic = 100  # Sạch
    elif nhom_no_cic == 2:
        diem_cic = 60   # Cần chú ý
    elif nhom_no_cic == 3:
        diem_cic = 30   # Dưới tiêu chuẩn
    else:
        diem_cic = 0    # Nợ xấu (nhóm 4-5)
    chi_tiet["lich_su_tin_dung_cic"] = {"diem": diem_cic, "trong_so": 25}

    # --- 2. Tỷ lệ DTI (20%) ---
    if dti_ratio <= 30:
        diem_dti = 100
    elif dti_ratio <= 40:
        diem_dti = 80
    elif dti_ratio <= 50:
        diem_dti = 60
    elif dti_ratio <= 60:
        diem_dti = 30
    else:
        diem_dti = 0
    chi_tiet["ty_le_dti"] = {"diem": diem_dti, "trong_so": 20}

    # --- 3. Thu nhập (15%) ---
    if thu_nhap_thang >= 30_000_000:
        diem_tn = 100
    elif thu_nhap_thang >= 20_000_000:
        diem_tn = 85
    elif thu_nhap_thang >= 15_000_000:
        diem_tn = 70
    elif thu_nhap_thang >= 10_000_000:
        diem_tn = 55
    elif thu_nhap_thang >= 7_000_000:
        diem_tn = 40
    else:
        diem_tn = 20
    chi_tiet["thu_nhap"] = {"diem": diem_tn, "trong_so": 15}

    # --- 4. Tỷ lệ LTV (10%) ---
    if ltv_ratio is None:
        # Vay tín chấp — không có TSĐB → điểm trung bình
        diem_ltv = 50
    elif ltv_ratio <= 50:
        diem_ltv = 100
    elif ltv_ratio <= 60:
        diem_ltv = 85
    elif ltv_ratio <= 70:
        diem_ltv = 70
    elif ltv_ratio <= 75:
        diem_ltv = 40
    else:
        diem_ltv = 10
    chi_tiet["ty_le_ltv"] = {"diem": diem_ltv, "trong_so": 10}

    # --- 5. Nghề nghiệp (10%) ---
    diem_nn_map = {
        "hcsn": 90,            # Hành chính sự nghiệp — rất ổn định
        "hoi_doan": 75,        # Cán bộ đoàn thể — ổn định
        "kinh_doanh": 65,      # Kinh doanh — biến động vừa
        "khac": 45,            # Lao động tự do — biến động cao
    }
    diem_nn = diem_nn_map.get(nghe_nghiep, 45)
    chi_tiet["nghe_nghiep"] = {"diem": diem_nn, "trong_so": 10}

    # --- 6. Tuổi (8%) ---
    if 28 <= tuoi <= 50:
        diem_tuoi = 90         # Tuổi vàng — kinh nghiệm + sức lao động
    elif 25 <= tuoi <= 55:
        diem_tuoi = 75
    elif 22 <= tuoi <= 60:
        diem_tuoi = 55
    else:
        diem_tuoi = 35         # Quá trẻ hoặc gần hưu
    chi_tiet["do_tuoi"] = {"diem": diem_tuoi, "trong_so": 8}

    # --- 7. Loại cư trú (7%) ---
    diem_ct_map = {
        "Owned": 90,           # Sở hữu — ổn định nhất
        "Mortgage": 65,        # Trả góp — có tài sản nhưng đang nợ
        "Rented": 40,          # Thuê — ít ổn định
    }
    diem_ct = diem_ct_map.get(loai_cu_tru, 40)
    chi_tiet["loai_cu_tru"] = {"diem": diem_ct, "trong_so": 7}

    # --- 8. Số khoản vay hiện tại (5%) ---
    if so_khoan_vay_hien_tai == 0:
        diem_kv = 100
    elif so_khoan_vay_hien_tai <= 1:
        diem_kv = 80
    elif so_khoan_vay_hien_tai <= 3:
        diem_kv = 50
    else:
        diem_kv = 20
    chi_tiet["so_khoan_vay"] = {"diem": diem_kv, "trong_so": 5}

    # --- Tổng hợp điểm ---
    tong_trong_so = 0
    for key, info in chi_tiet.items():
        tong_trong_so += info["diem"] * info["trong_so"] / 100

    # Quy đổi sang thang 300-900
    # tong_trong_so ∈ [0, 100] → credit_score ∈ [300, 900]
    credit_score = int(300 + (tong_trong_so / 100) * 600)
    credit_score = max(300, min(900, credit_score))

    # Phạt nặng nếu có nợ xấu nhóm 4-5
    if nhom_no_cic >= 4:
        credit_score = min(credit_score, 450)

    # Phạt nếu tự khai có nợ xấu nhưng CIC sạch (inconsistency)
    if co_no_xau and nhom_no_cic <= 1:
        credit_score = min(credit_score, 600)

    xep_hang, mo_ta = _xep_hang(credit_score)

    # --- Quyết định ---
    if credit_score >= 700 and dti_ratio <= 50:
        quyet_dinh = "PHÊ DUYỆT — Hồ sơ đạt tiêu chuẩn cho vay"
    elif credit_score >= 600 and dti_ratio <= 60:
        quyet_dinh = "PHÊ DUYỆT CÓ ĐIỀU KIỆN — Cần thẩm định bổ sung"
    elif credit_score >= 500:
        quyet_dinh = "THẨM ĐỊNH KỸ — Rủi ro cao, cần phê duyệt cấp trên"
    else:
        quyet_dinh = "TỪ CHỐI — Không đáp ứng tiêu chuẩn cho vay"

    return {
        "credit_score": credit_score,
        "xep_hang": xep_hang,
        "mo_ta_xep_hang": mo_ta,
        "quyet_dinh": quyet_dinh,
        "chi_tiet_diem": chi_tiet,
    }


# ═══════════════════════════════════════════════════════════════
# 4. TỐI ƯU HOÁ KHOẢN VAY (LOAN OPTIMIZER)
# ═══════════════════════════════════════════════════════════════

def toi_uu_khoan_vay(
    thu_nhap_thang: float,
    no_hien_tai_thang: float,
    lai_suat_nam: float,
    ky_han_thang: int,
    dti_toi_da: float = 50.0,
) -> dict:
    """
    Tính khoản vay tối đa an toàn dựa trên ngưỡng DTI.

    Logic: Từ DTI_max → tính ngược ra PMT_max → tính P_max
      PMT_max = (thu_nhap × DTI_max / 100) - nợ hiện tại
      P_max   = PMT_max × [(1+r)^n - 1] / [r × (1+r)^n]

    Returns:
        dict: vay_toi_da_an_toan, tra_gop_toi_da, khuyen_nghi
    """
    # Trả góp tối đa cho phép
    tra_gop_toi_da = (thu_nhap_thang * dti_toi_da / 100) - no_hien_tai_thang

    if tra_gop_toi_da <= 0:
        return {
            "vay_toi_da_an_toan": 0,
            "tra_gop_toi_da_thang": 0,
            "khuyen_nghi": (
                "Nợ hiện tại đã chiếm hết hạn mức DTI cho phép. "
                "Khuyến nghị thanh toán bớt nợ cũ trước khi vay mới."
            ),
        }

    # Tính ngược số tiền vay tối đa từ PMT
    r = lai_suat_nam / 100 / 12
    n = ky_han_thang

    if r <= 0:
        vay_toi_da = tra_gop_toi_da * n
    else:
        vay_toi_da = tra_gop_toi_da * ((1 + r) ** n - 1) / (r * (1 + r) ** n)

    vay_toi_da = round(vay_toi_da / 1_000_000) * 1_000_000  # Làm tròn triệu

    khuyen_nghi = (
        f"Với mức thu nhập {thu_nhap_thang/1_000_000:.0f} triệu/tháng "
        f"và nợ hiện tại {no_hien_tai_thang/1_000_000:.0f} triệu/tháng, "
        f"khoản vay tối đa an toàn (DTI ≤ {dti_toi_da:.0f}%) là "
        f"{vay_toi_da/1_000_000_000:.2f} tỷ VNĐ với kỳ hạn {ky_han_thang} tháng."
    )

    return {
        "vay_toi_da_an_toan": vay_toi_da,
        "tra_gop_toi_da_thang": round(tra_gop_toi_da, 0),
        "khuyen_nghi": khuyen_nghi,
    }


# ═══════════════════════════════════════════════════════════════
# 5. ĐÁNH GIÁ TỔNG HỢP (COMPREHENSIVE ASSESSMENT)
# ═══════════════════════════════════════════════════════════════

def danh_gia_tong_hop(
    tuoi: int,
    thu_nhap_thang: float,
    nghe_nghiep: str,
    so_tien_vay: float,
    ky_han_thang: int,
    lai_suat_nam: float,
    no_hien_tai_thang: float,
    gia_tri_tsdb: float | None,
    loai_cu_tru: str,
    loai_vay: str,
    co_no_xau: bool,
    nhom_no_cic: int,
    so_khoan_vay_cic: int,
    dti_toi_da_quy_dinh: float = 50.0,
) -> dict:
    """
    Đánh giá tổng hợp — kết hợp tất cả các module phân tích.

    Flow: DTI → LTV → Credit Scoring → Loan Optimization → Quyết định cuối cùng

    Returns:
        dict tổng hợp tất cả kết quả phân tích
    """
    # 1. Tính DTI
    ket_qua_dti = tinh_dti(
        thu_nhap_thang, no_hien_tai_thang,
        so_tien_vay, lai_suat_nam, ky_han_thang,
    )

    # 2. Tính LTV (chỉ áp dụng cho vay thế chấp)
    ket_qua_ltv = tinh_ltv(so_tien_vay, gia_tri_tsdb)

    # 3. Chấm điểm tín dụng
    ket_qua_scoring = cham_diem_tin_dung(
        tuoi=tuoi,
        thu_nhap_thang=thu_nhap_thang,
        nghe_nghiep=nghe_nghiep,
        dti_ratio=ket_qua_dti["dti_ratio"],
        ltv_ratio=ket_qua_ltv.get("ltv_ratio"),
        co_no_xau=co_no_xau,
        nhom_no_cic=nhom_no_cic,
        so_khoan_vay_hien_tai=so_khoan_vay_cic,
        loai_cu_tru=loai_cu_tru,
        ky_han_thang=ky_han_thang,
        loai_vay=loai_vay,
    )

    # 4. Tối ưu hoá khoản vay
    ket_qua_toi_uu = toi_uu_khoan_vay(
        thu_nhap_thang, no_hien_tai_thang,
        lai_suat_nam, ky_han_thang, dti_toi_da_quy_dinh,
    )

    # 5. Quyết định cuối cùng (kết hợp tất cả yếu tố)
    reasons = []

    # Check từ chối tuyệt đối
    if nhom_no_cic >= 4:
        quyet_dinh_cuoi = "TỪ CHỐI"
        reasons.append("Khách hàng thuộc nhóm nợ xấu (nhóm 4-5) trên CIC")
    elif ket_qua_dti["muc_do"] == "tu_choi":
        quyet_dinh_cuoi = "TỪ CHỐI"
        reasons.append(f"Tỷ lệ DTI = {ket_qua_dti['dti_ratio']:.1f}% vượt ngưỡng 60%")
    elif ket_qua_ltv.get("muc_do") == "tu_choi":
        quyet_dinh_cuoi = "TỪ CHỐI"
        reasons.append(f"Tỷ lệ LTV = {ket_qua_ltv['ltv_ratio']:.1f}% vượt ngưỡng 75%")
    elif ket_qua_scoring["credit_score"] < 500:
        quyet_dinh_cuoi = "TỪ CHỐI"
        reasons.append(f"Điểm tín dụng {ket_qua_scoring['credit_score']} < 500")
    elif ket_qua_scoring["credit_score"] >= 700 and ket_qua_dti["muc_do"] in ("an_toan", "chap_nhan"):
        quyet_dinh_cuoi = "PHÊ DUYỆT"
        reasons.append("Điểm tín dụng tốt, DTI trong ngưỡng an toàn")
    elif ket_qua_scoring["credit_score"] >= 600:
        quyet_dinh_cuoi = "PHÊ DUYỆT CÓ ĐIỀU KIỆN"
        reasons.append("Cần thẩm định bổ sung nguồn thu nhập và TSĐB")
    else:
        quyet_dinh_cuoi = "THẨM ĐỊNH KỸ"
        reasons.append("Hồ sơ thuộc vùng rủi ro trung bình-cao")

    # Khuyến nghị bổ sung
    khuyen_nghi_bo_sung = []
    vay_toi_da = ket_qua_toi_uu["vay_toi_da_an_toan"]

    if so_tien_vay > vay_toi_da > 0:
        khuyen_nghi_bo_sung.append(
            f"Số tiền vay ({so_tien_vay/1_000_000_000:.2f} tỷ) vượt mức an toàn. "
            f"Đề xuất giảm xuống {vay_toi_da/1_000_000_000:.2f} tỷ VNĐ."
        )

    if ket_qua_dti["muc_do"] == "canh_bao":
        khuyen_nghi_bo_sung.append(
            "DTI ở vùng cảnh báo. Nên tăng kỳ hạn vay để giảm trả góp hàng tháng."
        )

    if nhom_no_cic == 2 or nhom_no_cic == 3:
        khuyen_nghi_bo_sung.append(
            "Lịch sử CIC có ghi nhận chậm trả. Cần cung cấp giải trình và bằng chứng đã xử lý."
        )

    return {
        "dti": ket_qua_dti,
        "ltv": ket_qua_ltv,
        "credit_scoring": ket_qua_scoring,
        "toi_uu_khoan_vay": ket_qua_toi_uu,
        "quyet_dinh_cuoi_cung": quyet_dinh_cuoi,
        "ly_do": reasons,
        "khuyen_nghi_bo_sung": khuyen_nghi_bo_sung,
    }

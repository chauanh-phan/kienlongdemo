"""
Pydantic request / response schemas for the Robo-Advisor API.
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------
class AssessRequest(BaseModel):
    # Step 1 – Customer profile
    ho_ten:             str   = Field("Khách hàng", description="Full name")
    cccd:               str   = Field(...,           description="12-digit national ID")
    tuoi:               int   = Field(32,            description="Age (years)")
    gioi_tinh:          str   = Field("Nam",         description="Nam | Nữ")
    nghe_nghiep:        str   = Field("kinh_doanh",  description="Occupation code")

    # Step 2 – Loan needs
    loai_vay:           str   = Field("tin_chap",    description="tin_chap | the_chap")
    san_pham_vay:       str   = Field("hoi_phu_nu",  description="Purpose code (see PURPOSE_MAP)")
    ky_han_thang:       int   = Field(60,            description="Loan term in months")
    phuong_thuc_tra_no:  str   = Field("lai_thang_goc_chia_deu", description="Repayment method code")
    so_khoan_vay_hien_tai: int = Field(0,            description="Number of active loans")

    # Step 3 – Financials
    thu_nhap_thang:     float = Field(...,           description="Monthly income (VND)")
    no_hien_tai_thang:  float = Field(0,             description="Existing monthly debt payments (VND)")
    so_tien_vay:        float = Field(...,           description="Desired loan amount (VND)")
    gia_tri_tsdb:       float = Field(0,             description="Collateral value (VND)")
    chi_phi_sinh_hoat:  float = Field(0,             description="Monthly living expenses (VND)")
    thoi_gian_uu_dai:   str   = Field("3th",         description="Promo period: 3th | 9th | 18th")

    # Step 4 – Credit history
    co_no_xau:          bool  = Field(False,         description="Bad debt in last 5 years")
    cham_thanh_toan:    bool  = Field(False,         description="Late credit-card payment in last 3 years")
    no_can_chu_y:       bool  = Field(False,         description="Watch-list debt in last 12 months")

    # Legacy field kept for compatibility
    loai_cu_tru:        Optional[str] = Field(None,  description="(unused)")


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------
class DTIResult(BaseModel):
    dti_ratio:         float
    is_eligible:       bool
    max_dti:           float = 70.0
    mo_ta:             str

class LTVResult(BaseModel):
    ltv_ratio:         float
    is_eligible:       bool
    max_ltv:           float = 80.0
    mo_ta:             str

class LoanOptimization(BaseModel):
    so_tien_goc:       float
    vay_toi_da_an_toan: float
    ltv_da_dieu_chinh: bool
    tra_gop_hang_thang: float

class PhanTich(BaseModel):
    dti:               DTIResult
    ltv:               LTVResult
    toi_uu_khoan_vay:  LoanOptimization

class SanPham(BaseModel):
    ten:               str
    ma_san_pham:       str
    lai_suat_nam:      float
    lai_suat_uu_dai:   float
    thoi_gian_uu_dai_thang: int
    so_tien_vay:       float
    tra_gop_hang_thang: float

class KetLuan(BaseModel):
    quyet_dinh:        str   # Chấp thuận | Cần xem xét | Từ chối
    ly_do:             List[str]

class AssessResponse(BaseModel):
    phan_tich:         PhanTich
    san_pham:          SanPham
    ket_luan:          KetLuan
    khach_hang:        str

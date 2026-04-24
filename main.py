"""
KienlongBank Robo-Advisor API
FastAPI application — run with:
    uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from schemas import AssessRequest, AssessResponse
from predictor import assess

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="KienlongBank Robo-Advisor API",
    description="Hệ thống tư vấn vay vốn tự động — Random Forest (Accuracy 95.88%)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root():
    """Serve the frontend HTML."""
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "KienlongBank Robo-Advisor API. See /docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "robo-advisor"}


@app.post("/api/v1/assess", response_model=AssessResponse)
def assess_endpoint(req: AssessRequest):
    """
    Submit a loan application profile and receive:
    - DTI / LTV analysis
    - Recommended loan product (ML-predicted)
    - Reference interest rate
    - Decision: Chấp thuận / Cần xem xét / Từ chối
    """
    try:
        return assess(req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

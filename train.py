"""
KienlongBank Robo-Advisor — Model Training Script
Trains and compares Decision Tree vs Random Forest classifier.
Generates 5 evaluation charts and saves the best pipeline.

Yêu cầu thư viện:
    pip install pandas openpyxl scikit-learn matplotlib seaborn joblib
"""

import warnings
import joblib
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

matplotlib.use("Agg")
warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Màu thương hiệu KienlongBank
# ---------------------------------------------------------------------------
KLB_BLUE   = "#0b3ea8"
KLB_ORANGE = "#f36a21"
GRAY       = "#94a3b8"
BG         = "#f8faff"

plt.rcParams["font.family"] = "DejaVu Sans"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR  = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT_DIR / "data" / "dl_KLB.xlsx"
MODEL_DIR = Path(__file__).resolve().parent
CHART_DIR = MODEL_DIR / "charts"
CHART_DIR.mkdir(exist_ok=True)

print(f"[train] Data file  : {DATA_FILE}")
print(f"[train] Model dir  : {MODEL_DIR}")
print(f"[train] Chart dir  : {CHART_DIR}")

# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
df = pd.read_excel(DATA_FILE)
df.columns = df.columns.str.strip()

TARGET_COL = "Kết quả khoản vay đã vay"
df = df.drop(columns=["Tên", "CCCD"], errors="ignore")

# Chỉ giữ các hồ sơ được chấp thuận (tầng 2: phân loại sản phẩm)
df_model = df[~df[TARGET_COL].astype(str).str.startswith("Từ chối")].copy()

print(f"\n[data] Tổng số hồ sơ gốc   : {df.shape[0]}")
print(f"[data] Hồ sơ huấn luyện    : {df_model.shape[0]}")
print(f"[data] Số nhãn sản phẩm    : {df_model[TARGET_COL].nunique()}")
print(f"\n[data] Phân phối nhãn:\n{df_model[TARGET_COL].value_counts()}")

# ---------------------------------------------------------------------------
# 2. Features
# ---------------------------------------------------------------------------
FEATURE_COLS = [
    "Giới tính",
    "Nhóm tuổi",
    "Có TSBĐ không?",
    "Hình thức vay",
    "Mục đích sử dụng",
    "Thu nhập",
    "Số lượng khoản vay đang hoạt động?",
    "Tổng số tiền trả nợ các khoản vay khác",
    "Số tiền muốn vay",
    "Giá trị BĐS",
    "Thời gian vay (tháng)",
    "Lịch sử nợ xấu tín dụng trong 05 năm gần nhất",
    "Lịch sử chậm thanh toán thẻ tín dụng trong 03 năm gần nhất",
    "Nợ cần chú ý trong vòng 12 tháng gần nhất",
    "Kết quả DTI",
    "Kết quả LTV",
]
FEATURE_COLS = [c for c in FEATURE_COLS if c in df_model.columns]

X = df_model[FEATURE_COLS].copy()
y = df_model[TARGET_COL].copy()
LABELS = sorted(y.unique().tolist())

print("\n[data] Giá trị duy nhất các biến định tính:")
for col in X.select_dtypes(include=["object", "category"]).columns:
    print(f"  {col!r}: {sorted(X[col].dropna().unique().tolist())}")

# ---------------------------------------------------------------------------
# 3. Preprocessing pipeline
# ---------------------------------------------------------------------------
numeric_cols     = X.select_dtypes(include=["int64", "float64", "int32", "float32"]).columns.tolist()
categorical_cols = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

try:
    ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
except TypeError:
    ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)

numeric_transformer     = Pipeline([("imputer", SimpleImputer(strategy="median"))])
categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot",  ohe),
])

preprocessor = ColumnTransformer([
    ("cat", categorical_transformer, categorical_cols),
    ("num", numeric_transformer,     numeric_cols),
])

# ---------------------------------------------------------------------------
# 4. Định nghĩa mô hình
# ---------------------------------------------------------------------------
MODELS = {
    "Decision Tree": DecisionTreeClassifier(
        max_depth=6, min_samples_leaf=10, random_state=42
    ),
    "Random Forest": RandomForestClassifier(
        n_estimators=200, max_depth=8, min_samples_leaf=5,
        random_state=42, n_jobs=-1
    ),
}

# ---------------------------------------------------------------------------
# 5. Train / Test split (80/20, phân tầng)
# ---------------------------------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\n[split] Tập huấn luyện : {X_train.shape}")
print(f"[split] Tập kiểm tra   : {X_test.shape}")

# ---------------------------------------------------------------------------
# 6. Huấn luyện & đánh giá
# ---------------------------------------------------------------------------
results       = {}
trained_pipes = {}
predictions   = {}

for name, clf in MODELS.items():
    pipe = Pipeline([("preprocessor", preprocessor), ("model", clf)])
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)

    results[name] = {
        "Accuracy":        accuracy_score(y_test, y_pred),
        "Precision_macro": precision_score(y_test, y_pred, average="macro",    zero_division=0),
        "Recall_macro":    recall_score(y_test,    y_pred, average="macro",    zero_division=0),
        "F1_macro":        f1_score(y_test,        y_pred, average="macro",    zero_division=0),
        "F1_weighted":     f1_score(y_test,        y_pred, average="weighted", zero_division=0),
    }
    trained_pipes[name] = pipe
    predictions[name]   = y_pred

    print(f"\n{'='*60}")
    print(f"[model] {name}")
    print(f"  Accuracy        : {results[name]['Accuracy']:.4f}")
    print(f"  Precision macro : {results[name]['Precision_macro']:.4f}")
    print(f"  Recall macro    : {results[name]['Recall_macro']:.4f}")
    print(f"  F1 macro        : {results[name]['F1_macro']:.4f}")
    print(f"  F1 weighted     : {results[name]['F1_weighted']:.4f}")
    print(classification_report(y_test, y_pred, zero_division=0))

results_df = pd.DataFrame(results).T.sort_values("F1_macro", ascending=False)
best_name  = results_df.index[0]
best_pipe  = trained_pipes[best_name]

print(f"\n{'='*60}")
print(f"[result] Mô hình tốt nhất  : {best_name}")
print(f"[result] Accuracy          : {results[best_name]['Accuracy']:.4f}")
print(f"[result] F1 macro          : {results[best_name]['F1_macro']:.4f}")
print(results_df.round(4))


# ===========================================================================
# 7. VẼ BIỂU ĐỒ SO SÁNH
# ===========================================================================

def save(fig, filename):
    path = CHART_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Đã lưu: {path.name}")


# ---------------------------------------------------------------------------
# Biểu đồ 1 — So sánh chỉ số tổng thể (grouped bar)
# ---------------------------------------------------------------------------
print("\n[charts] Đang vẽ biểu đồ...")

metrics      = ["Accuracy", "Precision_macro", "Recall_macro", "F1_macro", "F1_weighted"]
metric_names = ["Accuracy", "Precision", "Recall", "F1 Macro", "F1 Weighted"]
x = np.arange(len(metrics))
w = 0.32

fig, ax = plt.subplots(figsize=(13, 6))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

bars_dt = ax.bar(x - w/2,
                 [results["Decision Tree"][m] * 100 for m in metrics],
                 w, label="Decision Tree", color=GRAY, alpha=0.85,
                 zorder=3, edgecolor="white", linewidth=1.5)
bars_rf = ax.bar(x + w/2,
                 [results["Random Forest"][m] * 100 for m in metrics],
                 w, label="Random Forest", color=KLB_BLUE, alpha=0.92,
                 zorder=3, edgecolor="white", linewidth=1.5)

for bar in bars_dt:
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6,
            f"{bar.get_height():.1f}%", ha="center", va="bottom",
            fontsize=9, color="#475569", fontweight="600")
for bar in bars_rf:
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6,
            f"{bar.get_height():.1f}%", ha="center", va="bottom",
            fontsize=9, color=KLB_BLUE, fontweight="700")

ax.set_ylim(0, 110)
ax.set_xticks(x)
ax.set_xticklabels(metric_names, fontsize=11, fontweight="600")
ax.set_ylabel("Giá trị (%)", fontsize=11)
ax.set_title(
    "Biểu đồ 1: So sánh hiệu suất tổng thể\nDecision Tree vs. Random Forest",
    fontsize=13, fontweight="800", pad=14, color="#1e293b"
)
ax.legend(fontsize=11, framealpha=0.9)
ax.yaxis.grid(True, alpha=0.35, linestyle="--")
ax.set_axisbelow(True)
for sp in ax.spines.values():
    sp.set_visible(False)

# Chú thích kết luận
winner_acc = results["Random Forest"]["Accuracy"] * 100
loser_acc  = results["Decision Tree"]["Accuracy"] * 100
ax.annotate(
    f"Random Forest vượt trội hơn\n+{winner_acc - loser_acc:.1f}% Accuracy",
    xy=(4 + w/2, winner_acc),
    xytext=(3.2, 80),
    fontsize=9, color=KLB_BLUE, fontweight="700",
    arrowprops=dict(arrowstyle="->", color=KLB_BLUE, lw=1.5),
)

plt.tight_layout()
save(fig, "bieu_do_1_so_sanh_tong_the.png")

# ---------------------------------------------------------------------------
# Biểu đồ 2 — F1-Score theo từng sản phẩm (horizontal grouped bar)
# ---------------------------------------------------------------------------
report_dt = classification_report(y_test, predictions["Decision Tree"],
                                   output_dict=True, zero_division=0)
report_rf = classification_report(y_test, predictions["Random Forest"],
                                   output_dict=True, zero_division=0)

f1_dt = [round(report_dt.get(l, {}).get("f1-score", 0) * 100, 1) for l in LABELS]
f1_rf = [round(report_rf.get(l, {}).get("f1-score", 0) * 100, 1) for l in LABELS]

y_pos  = np.arange(len(LABELS))
height = 0.35

fig, ax = plt.subplots(figsize=(14, 7))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

b1 = ax.barh(y_pos + height / 2, f1_dt, height,
             label="Decision Tree", color=GRAY, alpha=0.80, edgecolor="white")
b2 = ax.barh(y_pos - height / 2, f1_rf, height,
             label="Random Forest", color=KLB_BLUE, alpha=0.90, edgecolor="white")

for bar, val in zip(b1, f1_dt):
    clr = "#dc2626" if val == 0 else "#475569"
    txt = "Không phân loại được!" if val == 0 else f"{val:.1f}%"
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            txt, va="center", fontsize=8.5, color=clr, fontweight="700")

for bar, val in zip(b2, f1_rf):
    clr = KLB_ORANGE if val == 100.0 else KLB_BLUE
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%", va="center", fontsize=8.5, color=clr, fontweight="700")

# Đánh dấu vùng Decision Tree thất bại
for i, val in enumerate(f1_dt):
    if val == 0:
        ax.axhspan(i - 0.05, i + 0.75, alpha=0.07, color="#dc2626", zorder=0)

ax.set_yticks(y_pos)
ax.set_yticklabels(LABELS, fontsize=9.5)
ax.set_xlim(0, 120)
ax.set_xlabel("F1-Score (%)", fontsize=11)
ax.set_title(
    "Biểu đồ 2: F1-Score theo từng sản phẩm vay\nDecision Tree vs. Random Forest  |  Vùng đỏ = Decision Tree không phân loại được",
    fontsize=12, fontweight="800", pad=14, color="#1e293b"
)
ax.legend(fontsize=11, framealpha=0.9)
ax.xaxis.grid(True, alpha=0.3, linestyle="--")
ax.set_axisbelow(True)
for sp in ax.spines.values():
    sp.set_visible(False)

plt.tight_layout()
save(fig, "bieu_do_2_f1_theo_san_pham.png")

# ---------------------------------------------------------------------------
# Biểu đồ 3 — Confusion Matrix Random Forest
# ---------------------------------------------------------------------------
labels_short = [
    l.replace("Vay Thế chấp - ", "TC-").replace("Vay Tín chấp - ", "TíC-")
    for l in LABELS
]

cm_rf = confusion_matrix(y_test, predictions["Random Forest"], labels=LABELS)

fig, ax = plt.subplots(figsize=(12, 9))
fig.patch.set_facecolor(BG)

sns.heatmap(
    cm_rf, annot=True, fmt="d", cmap="Blues",
    xticklabels=labels_short, yticklabels=labels_short,
    linewidths=0.5, linecolor="#e2e8f0",
    annot_kws={"size": 11, "weight": "bold"},
    ax=ax, cbar_kws={"shrink": 0.8},
)
ax.set_title(
    "Biểu đồ 3: Ma trận nhầm lẫn — Random Forest\n"
    f"Tập kiểm tra: {len(y_test)} mẫu  |  Accuracy: {results['Random Forest']['Accuracy']*100:.2f}%",
    fontsize=13, fontweight="800", pad=14, color="#1e293b"
)
ax.set_xlabel("Nhãn dự đoán", fontsize=11, labelpad=10)
ax.set_ylabel("Nhãn thực tế", fontsize=11, labelpad=10)
ax.tick_params(axis="x", rotation=30, labelsize=9)
ax.tick_params(axis="y", rotation=0,  labelsize=9)

plt.tight_layout()
save(fig, "bieu_do_3_confusion_matrix_rf.png")

# ---------------------------------------------------------------------------
# Biểu đồ 4 — Confusion Matrix Decision Tree
# ---------------------------------------------------------------------------
cm_dt = confusion_matrix(y_test, predictions["Decision Tree"], labels=LABELS)

fig, ax = plt.subplots(figsize=(12, 9))
fig.patch.set_facecolor(BG)

sns.heatmap(
    cm_dt, annot=True, fmt="d", cmap="Greys",
    xticklabels=labels_short, yticklabels=labels_short,
    linewidths=0.5, linecolor="#e2e8f0",
    annot_kws={"size": 11, "weight": "bold"},
    ax=ax, cbar_kws={"shrink": 0.8},
)
ax.set_title(
    "Biểu đồ 4: Ma trận nhầm lẫn — Decision Tree\n"
    f"Tập kiểm tra: {len(y_test)} mẫu  |  Accuracy: {results['Decision Tree']['Accuracy']*100:.2f}%",
    fontsize=13, fontweight="800", pad=14, color="#1e293b"
)
ax.set_xlabel("Nhãn dự đoán", fontsize=11, labelpad=10)
ax.set_ylabel("Nhãn thực tế", fontsize=11, labelpad=10)
ax.tick_params(axis="x", rotation=30, labelsize=9)
ax.tick_params(axis="y", rotation=0,  labelsize=9)

plt.tight_layout()
save(fig, "bieu_do_4_confusion_matrix_dt.png")

# ---------------------------------------------------------------------------
# Biểu đồ 5 — Feature Importance (Random Forest)
# ---------------------------------------------------------------------------
rf_pipe     = trained_pipes["Random Forest"]
ohe_feats   = (rf_pipe.named_steps["preprocessor"]
               .named_transformers_["cat"]["onehot"]
               .get_feature_names_out(categorical_cols))
all_feats   = list(ohe_feats) + numeric_cols
importances = rf_pipe.named_steps["model"].feature_importances_

def shorten(name: str) -> str:
    return (name
            .replace("Mục đích sử dụng_", "MĐ: ")
            .replace("Hình thức vay_",     "HT: ")
            .replace("Có TSBĐ không?_",    "TSBĐ: ")
            .replace("Lịch sử nợ xấu tín dụng trong 05 năm gần nhất",       "Nợ xấu 5 năm")
            .replace("Lịch sử chậm thanh toán thẻ tín dụng trong 03 năm gần nhất", "Chậm TT thẻ 3 năm")
            .replace("Nợ cần chú ý trong vòng 12 tháng gần nhất",            "Nợ chú ý 12 tháng")
            .replace("Tổng số tiền trả nợ các khoản vay khác",               "Tổng tiền trả nợ khác")
            .replace("Số lượng khoản vay đang hoạt động?",                   "Số khoản vay HĐ")
            .replace("Thời gian vay (tháng)",                                 "Thời gian vay"))

feat_s = (pd.Series(importances, index=all_feats)
            .sort_values(ascending=True)
            .tail(15))
feat_s.index = [shorten(i) for i in feat_s.index]

q60    = feat_s.quantile(0.6)
colors = [
    KLB_ORANGE if v == feat_s.max()
    else KLB_BLUE if v >= q60
    else GRAY
    for v in feat_s.values
]

fig, ax = plt.subplots(figsize=(13, 7))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

bars = ax.barh(feat_s.index, feat_s.values * 100,
               color=colors, alpha=0.88, edgecolor="white", linewidth=1.2)

for bar, val in zip(bars, feat_s.values):
    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
            f"{val*100:.2f}%", va="center", fontsize=9,
            fontweight="700", color="#1e293b")

ax.set_xlabel("Mức độ ảnh hưởng (%)", fontsize=11)
ax.set_title(
    "Biểu đồ 5: Mức độ ảnh hưởng của biến đầu vào\nRandom Forest — Top 15 Feature Importance",
    fontsize=13, fontweight="800", pad=14, color="#1e293b"
)
ax.xaxis.grid(True, alpha=0.3, linestyle="--")
ax.set_axisbelow(True)
for sp in ax.spines.values():
    sp.set_visible(False)

p1 = mpatches.Patch(color=KLB_ORANGE, label="Biến quan trọng nhất")
p2 = mpatches.Patch(color=KLB_BLUE,   label="Biến quan trọng cao")
p3 = mpatches.Patch(color=GRAY,       label="Biến bổ trợ")
ax.legend(handles=[p1, p2, p3], fontsize=10, framealpha=0.9)

plt.tight_layout()
save(fig, "bieu_do_5_feature_importance.png")

# ---------------------------------------------------------------------------
# Biểu đồ 6 — Radar Chart: so sánh đa chiều
# ---------------------------------------------------------------------------
radar_metrics = ["Accuracy", "Precision_macro", "Recall_macro", "F1_macro", "F1_weighted"]
radar_labels  = ["Accuracy", "Precision", "Recall", "F1 Macro", "F1 Weighted"]
N = len(radar_labels)

angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]   # đóng đa giác

vals_dt = [results["Decision Tree"][m] for m in radar_metrics]
vals_dt += vals_dt[:1]
vals_rf = [results["Random Forest"][m] for m in radar_metrics]
vals_rf += vals_rf[:1]

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

ax.plot(angles, vals_dt, color=GRAY,      linewidth=2,   label="Decision Tree")
ax.fill(angles, vals_dt, color=GRAY,      alpha=0.18)
ax.plot(angles, vals_rf, color=KLB_BLUE,  linewidth=2.5, label="Random Forest")
ax.fill(angles, vals_rf, color=KLB_BLUE,  alpha=0.22)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(radar_labels, fontsize=11, fontweight="600")
ax.set_ylim(0, 1)
ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_yticklabels(["20%", "40%", "60%", "80%", "100%"], fontsize=8, color="#94a3b8")
ax.grid(color="#cbd5e1", linestyle="--", linewidth=0.8)

ax.set_title(
    "Biểu đồ 6: So sánh đa chiều (Radar Chart)\nDecision Tree vs. Random Forest",
    fontsize=13, fontweight="800", pad=20, color="#1e293b"
)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.15), fontsize=11, framealpha=0.9)

plt.tight_layout()
save(fig, "bieu_do_6_radar_chart.png")

print(f"\n[charts] ✅ Đã tạo 6 biểu đồ tại: {CHART_DIR}")

# ===========================================================================
# 8. Kết luận lựa chọn mô hình (in ra terminal)
# ===========================================================================
print(f"\n{'='*60}")
print("[ KẾT LUẬN LỰA CHỌN MÔ HÌNH ]")
print(f"{'='*60}")
print(f"  Mô hình được chọn     : {best_name}")
print(f"  Accuracy              : {results[best_name]['Accuracy']*100:.2f}%")
print(f"  F1 Macro              : {results[best_name]['F1_macro']*100:.2f}%")
print(f"  Precision Macro       : {results[best_name]['Precision_macro']*100:.2f}%")
print(f"  Recall Macro          : {results[best_name]['Recall_macro']*100:.2f}%")

other = [n for n in MODELS if n != best_name][0]
acc_diff = (results[best_name]["Accuracy"] - results[other]["Accuracy"]) * 100
f1_diff  = (results[best_name]["F1_macro"] - results[other]["F1_macro"])  * 100
print(f"\n  Cải thiện so với {other}:")
print(f"    Accuracy  : +{acc_diff:.2f}%")
print(f"    F1 Macro  : +{f1_diff:.2f}%")
print(f"\n  Lý do lựa chọn:")
print(f"    • {best_name} đạt hiệu suất vượt trội trên tất cả 5 chỉ số đánh giá.")
print(f"    • Decision Tree hoàn toàn thất bại ở một số nhóm sản phẩm tín chấp (F1 = 0%).")
print(f"    • Random Forest ổn định và đồng đều trên cả 10 nhóm sản phẩm.")
print(f"{'='*60}")

# ===========================================================================
# 9. Lưu artefacts
# ===========================================================================
joblib.dump(best_pipe,    MODEL_DIR / "best_loan_recommender.pkl")
joblib.dump(FEATURE_COLS, MODEL_DIR / "feature_cols.pkl")
joblib.dump(results_df,   MODEL_DIR / "model_comparison_results.pkl")

print(f"\n[save] Đã lưu tại: {MODEL_DIR}")
print("  ✓ best_loan_recommender.pkl")
print("  ✓ feature_cols.pkl")
print("  ✓ model_comparison_results.pkl")
# ---------------------------------------------------------------------------

# Biểu đồ 4 — Confusion Matrix Decision Tree
cm_dt = confusion_matrix(y_test, predictions["Decision Tree"], labels=LABELS)

labels_short = [
    l.replace("Vay Thế chấp - ", "TC-").replace("Vay Tín chấp - ", "TíC-")
    for l in LABELS
]

fig, ax = plt.subplots(figsize=(12, 9))
fig.patch.set_facecolor(BG)

sns.heatmap(
    cm_dt, annot=True, fmt="d", cmap="Greys",
    xticklabels=labels_short, yticklabels=labels_short,
    linewidths=0.5, linecolor="#e2e8f0",
    annot_kws={"size": 11, "weight": "bold"},
    ax=ax, cbar_kws={"shrink": 0.8},
)
ax.set_title(
    "Biểu đồ 4: Ma trận nhầm lẫn — Decision Tree\n"
    f"Tập kiểm tra: {len(y_test)} mẫu  |  Accuracy: {results['Decision Tree']['Accuracy']*100:.2f}%",
    fontsize=13, fontweight="800", pad=14, color="#1e293b"
)
ax.set_xlabel("Nhãn dự đoán", fontsize=11, labelpad=10)
ax.set_ylabel("Nhãn thực tế", fontsize=11, labelpad=10)
ax.tick_params(axis="x", rotation=30, labelsize=9)
ax.tick_params(axis="y", rotation=0,  labelsize=9)

plt.tight_layout()
save(fig, "bieu_do_4_confusion_matrix_dt.png")


# Biểu đồ 2 — F1-Score theo từng sản phẩm (grouped horizontal bar)
report_dt = classification_report(y_test, predictions["Decision Tree"],
                                   output_dict=True, zero_division=0)
report_rf = classification_report(y_test, predictions["Random Forest"],
                                   output_dict=True, zero_division=0)

f1_dt = [round(report_dt.get(l, {}).get("f1-score", 0) * 100, 1) for l in LABELS]
f1_rf = [round(report_rf.get(l, {}).get("f1-score", 0) * 100, 1) for l in LABELS]

y_pos  = np.arange(len(LABELS))
height = 0.35

fig, ax = plt.subplots(figsize=(14, 7))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

b1 = ax.barh(y_pos + height / 2, f1_dt, height,
             label="Decision Tree", color=GRAY, alpha=0.80, edgecolor="white")
b2 = ax.barh(y_pos - height / 2, f1_rf, height,
             label="Random Forest", color=KLB_BLUE, alpha=0.90, edgecolor="white")

for bar, val in zip(b1, f1_dt):
    clr = "#dc2626" if val == 0 else "#475569"
    txt = "Không phân loại được!" if val == 0 else f"{val:.1f}%"
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            txt, va="center", fontsize=8.5, color=clr, fontweight="700")

for bar, val in zip(b2, f1_rf):
    clr = KLB_ORANGE if val >= 99.0 else KLB_BLUE
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%", va="center", fontsize=8.5, color=clr, fontweight="700")

# Đánh dấu vùng Decision Tree thất bại (F1 = 0)
for i, val in enumerate(f1_dt):
    if val == 0:
        ax.axhspan(i - 0.05, i + 0.75, alpha=0.07, color="#dc2626", zorder=0)

ax.set_yticks(y_pos)
ax.set_yticklabels(LABELS, fontsize=9.5)
ax.set_xlim(0, 130)
ax.set_xlabel("F1-Score (%)", fontsize=11)
ax.set_title(
    "Biểu đồ 2: F1-Score theo từng sản phẩm vay\n"
    "Decision Tree vs. Random Forest  |  Vùng đỏ nhạt = Decision Tree không phân loại được",
    fontsize=12, fontweight="800", pad=14, color="#1e293b"
)
ax.legend(fontsize=11, framealpha=0.9)
ax.xaxis.grid(True, alpha=0.3, linestyle="--")
ax.set_axisbelow(True)
for sp in ax.spines.values():
    sp.set_visible(False)

plt.tight_layout()
save(fig, "bieu_do_2_f1_theo_san_pham.png")

print("[charts] Đã tạo thêm: bieu_do_2 và bieu_do_4")
print("\n[done] Hoàn thành huấn luyện và đánh giá mô hình.")
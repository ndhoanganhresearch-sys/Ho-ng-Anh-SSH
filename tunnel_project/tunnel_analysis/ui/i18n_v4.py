"""Phrase-based translations for the TunnelApp v4.0 main window.

English is the base language. Each entry maps an English source phrase to its
Vietnamese and Korean equivalents. Any phrase not present here falls back to
the original English text, so the UI never breaks on a missing translation.
"""

from translations import get_available_languages

PHRASES = {
    # --- Sidebar header ---
    "TUNNEL ANALYSIS": {"vi": "PHÂN TÍCH HẦM", "ko": "터널 분석"},
    "v4.0 r1 - CBNU Smart Structure Lab": {
        "vi": "v4.0 r1 - Phòng Thí Nghiệm Kết Cấu Thông Minh CBNU",
        "ko": "v4.0 r1 - CBNU 스마트 구조 연구실",
    },
    "Tunnel Profile Type": {"vi": "Loại Mặt Cắt Hầm", "ko": "터널 단면 유형"},
    "Vehicle Clearance Limit (m)": {"vi": "Giới Hạn Tĩnh Không Xe (m)", "ko": "차량 한계 (m)"},
    "Half clear width W:": {"vi": "Nửa chiều rộng thông W:", "ko": "유효 반폭 W:"},
    "Clear height H:": {"vi": "Chiều cao thông H:", "ko": "유효 높이 H:"},
    "Circular clearance radius R:": {"vi": "Bán kính tĩnh không tròn R:", "ko": "원형 한계 반경 R:"},
    "AUTO PIPELINE  (1-click full analysis)": {
        "vi": "TỰ ĐỘNG  (phân tích 1 chạm)", "ko": "자동 파이프라인  (원클릭 전체 분석)",
    },
    "Reset Pipeline": {"vi": "Đặt Lại Quy Trình", "ko": "파이프라인 초기화"},
    "Step": {"vi": "Bước", "ko": "단계"},
    "Points: --": {"vi": "Điểm: --", "ko": "포인트: --"},
    "RMSE: --": {"vi": "RMSE: --", "ko": "RMSE: --"},

    # --- Header ---
    "Tunnel Analysis v4.0": {"vi": "Phân Tích Hầm v4.0", "ko": "터널 분석 v4.0"},
    "Select a structural analysis workflow from the sidebar.": {
        "vi": "Chọn một quy trình phân tích kết cấu từ thanh bên.",
        "ko": "사이드바에서 구조 분석 워크플로를 선택하세요.",
    },

    # --- Right-panel tab titles ---
    "Results Log": {"vi": "Nhật Ký Kết Quả", "ko": "결과 로그"},
    "Scan Database": {"vi": "CSDL Quét", "ko": "스캔 데이터베이스"},
    "Stations": {"vi": "Trạm Quét", "ko": "스테이션"},
    "Targets": {"vi": "Mục Tiêu", "ko": "타겟"},
    "Time-Series Plot": {"vi": "Biểu Đồ Chuỗi Thời Gian", "ko": "시계열 그래프"},
    "2D Cross-Section": {"vi": "Mặt Cắt 2D", "ko": "2D 단면"},
    "Polar Deformation": {"vi": "Biến Dạng Cực", "ko": "극좌표 변형"},
    "AI Engineering Assistant": {"vi": "Trợ Lý Kỹ Sư AI", "ko": "AI 엔지니어링 도우미"},

    # --- Section titles ---
    "LiDAR data acquisition": {"vi": "Thu thập dữ liệu LiDAR", "ko": "LiDAR 데이터 수집"},
    "Preprocessing and noise filtering": {"vi": "Tiền xử lý và lọc nhiễu", "ko": "전처리 및 노이즈 필터링"},
    "Registration and synchronization": {"vi": "Đăng ký và đồng bộ", "ko": "정합 및 동기화"},
    "Geometric coordinate system": {"vi": "Hệ tọa độ hình học", "ko": "기하 좌표계"},
    "Parameter extraction": {"vi": "Trích xuất tham số", "ko": "파라미터 추출"},
    "Time-series analysis": {"vi": "Phân tích chuỗi thời gian", "ko": "시계열 분석"},
    "BIM and AI": {"vi": "BIM và AI", "ko": "BIM 및 AI"},
}

def tr(text: str, lang: str = "en") -> str:
    """Translate an English source phrase; fall back to English if missing."""
    if lang == "en" or lang not in get_available_languages():
        return text
    entry = PHRASES.get(text)
    if entry is None:
        return text
    return entry.get(lang, text)

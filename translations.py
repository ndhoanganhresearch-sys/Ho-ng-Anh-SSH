"""
SSL Smart Tunnel Monitoring System - Multilingual Translations (English/Vietnamese/Korean)

This module provides all UI text in English, Vietnamese, and Korean.
"""

TRANSLATIONS = {
    "en": {
        # Window title
        "window_title": "SSL Smart Tunnel Monitoring System - Osong Tunnel 4D LiDAR",
        
        # Sidebar
        "sidebar_title": "SSL 4D-LiDAR",
        "sidebar_subtitle": "Osong Tunnel Monitoring",
        "import_btn": "Import LAS / PLY",
        "register_btn": "Sequential Register",
        "deformation_btn": "Tn vs T0 Heatmap",
        "language_btn": "🌐 English",
        
        # Import Settings
        "import_settings": "Import Settings",
        "timestamp_label": "Timestamp",
        "auto_target_check": "Auto detect intensity targets",
        
        # Viewer Layers
        "viewer_layers": "Viewer Layers",
        "centerline_check": "Centerline",
        "heatmap_check": "Heatmap",
        "ai_check": "AI Detections",
        
        # View Controls
        "view_box": "View",
        "reset_camera_btn": "Reset Camera",
        "screenshot_btn": "Screenshot",
        
        # Status Labels
        "points_label": "Points: -",
        "rmse_label": "RMSE: -",
        "ready_status": "Ready",
        
        # Tab Names
        "tab_overview": "Overview",
        "tab_registration": "Registration",
        "tab_ransac": "RANSAC",
        "tab_centerline": "Centerline",
        "tab_section": "Section",
        "tab_rings": "Rings",
        "tab_timeseries": "Time-Series",
        "tab_frenet": "Frenet",
        "tab_heatmap": "Heatmap",
        "tab_results": "Results",
        "tab_ai_chat": "AI Chat",
        
        # Tab Content
        "overview_label": "3D PyVista viewport for full tunnel visualization with LOD management.",
        "registration_label": "Station manager and target matching workspace.",
        "ransac_label": "RANSAC segmentation controls will use tunnel_utils.py.",
        "centerline_label": "Centerline layer is previewed in the Overview PyVista viewer.",
        "section_label": "Cross-section slicing workspace.",
        "rings_label": "Concrete segment ring analysis workspace.",
        "timeseries_label": "4D time-series settlement and convergence charts.",
        "frenet_label": "Frenet frame analysis is rendered as a PyVista overlay in Overview.",
        "heatmap_label": "Heatmap layer is previewed in the Overview PyVista viewer.",
        "ai_chat_placeholder": "AI tunnel-data assistant workspace.",
        
        # Registration Tab
        "station_table_headers": ["Station", "Timestamp", "Points", "Targets", "File"],
        
        # Dialog Messages
        "import_dialog_title": "Import Faro Focus Point Clouds",
        "import_dialog_filter": "Point Clouds (*.las *.laz *.ply);;All Files (*.*)",
        "loading_status": "Loading raw point cloud with laspy / vertex-only parser...",
        "rendering_status": "Rendering vertex-only PyVista overview...",
        "registration_status": "Running sequential SVD/ICP stitching...",
        
        # Error Messages
        "no_stations_error": "No stations were imported.",
        "pyvista_error": "PyVista widget was not initialized.",
        
        # Menu Items
        "file_menu": "File",
        "edit_menu": "Edit",
        "view_menu": "View",
        "tools_menu": "Tools",
        "help_menu": "Help",
        "open_project": "Open Project",
        "save_project": "Save Project",
        "export_results": "Export Results",
        "preferences": "Preferences",
        "exit": "Exit",
        # Dynamic runtime messages
        "no_files_selected": "No point-cloud files selected.",
        "loading_station": "Loading station {index}/{count}: {name}",
        "detecting_targets": "Detecting intensity targets for {station}...",
        "target_detection_skipped": "{station}: target detection skipped ({error})",
        "no_intensity_channel": "{station}: no intensity channel for target detection.",
        "station_imported": "{station} imported.",
        "import_failed_title": "Import LAS failed",
        "registration_failed_title": "Registration failed",
        "imported_n_stations": "Imported {count} station(s) as timestamp {timestamp}",
        "station_log_entry": "{station}: {filename}, {points} points, {targets} targets",
        "rendered_latest": "Rendered latest station: {points} points",
        "import_complete": "Import complete: {count} station(s) loaded",
        "points_label_loaded": "Points: {raw} raw / {rendered} rendered",
        "registration_dialog_title": "Registration",
        "registration_need_two": "Load at least two stations before stitching.",
        "registration_link_log": "{source} -> {target}: {method}, RMSE {rmse} mm",
        "registered_cloud_title": "Registered Global Cloud",
        "rmse_label_value": "RMSE: {rmse} mm",
        "registration_complete": "Registration complete",
        "deformation_dialog_title": "Deformation Heatmap",
        "deformation_need_two_ts": "Load at least two timestamps, for example T0 and T1.",
        "deformation_no_current": "No current timestamp is available for comparison.",
        "computing_heatmap_vs": "Computing {current} vs {reference} deformation heatmap...",
        "computing_heatmap_progress": "Computing deformation heatmap...",
        "no_deformation_result": "No deformation result was produced.",
        "deformation_title": "Deformation Heatmap - {current} vs {reference}",
        "heatmap_points_label": "Heatmap: {points} pts, warning {pct}%",
        "p95_label": "P95 delta: {p95} mm",
        "deformation_log_stats": "Deformation {current} vs {reference}: mean {mean} mm, p95 {p95} mm, max {max} mm, warning {warning}%",
        "threshold_bands_log": "Threshold bands: stable {stable}%, caution {caution}%, warning {warning}%",
        "deformation_complete": "Deformation heatmap complete",
        "deformation_failed_title": "Deformation heatmap failed",
        "screenshot_dialog_title": "Save PyVista Screenshot",
        "screenshot_filter": "PNG Image (*.png)",
        "screenshot_failed_title": "Screenshot failed",
        "screenshot_saved": "Screenshot saved: {path}",
    },
    
    "vi": {
        # Window title
        "window_title": "Hệ Thống Giám Sát Hầm Thông Minh SSL - Hầm Osong 4D LiDAR",
        
        # Sidebar
        "sidebar_title": "SSL 4D-LiDAR",
        "sidebar_subtitle": "Giám Sát Hầm Osong",
        "import_btn": "Nhập LAS / PLY",
        "register_btn": "Đăng Ký Tuần Tự",
        "deformation_btn": "Bản Đồ Nhiệt Tn vs T0",
        "language_btn": "🌐 Tiếng Việt",
        
        # Import Settings
        "import_settings": "Cài Đặt Nhập",
        "timestamp_label": "Dấu Thời Gian",
        "auto_target_check": "Tự động phát hiện mục tiêu cường độ",
        
        # Viewer Layers
        "viewer_layers": "Lớp Hiển Thị",
        "centerline_check": "Đường Tâm",
        "heatmap_check": "Bản Đồ Nhiệt",
        "ai_check": "Phát Hiện AI",
        
        # View Controls
        "view_box": "Xem",
        "reset_camera_btn": "Đặt Lại Camera",
        "screenshot_btn": "Chụp Màn Hình",
        
        # Status Labels
        "points_label": "Điểm: -",
        "rmse_label": "RMSE: -",
        "ready_status": "Sẵn Sàng",
        
        # Tab Names
        "tab_overview": "Tổng Quan",
        "tab_registration": "Đăng Ký",
        "tab_ransac": "RANSAC",
        "tab_centerline": "Đường Tâm",
        "tab_section": "Mặt Cắt",
        "tab_rings": "Vòng",
        "tab_timeseries": "Chuỗi Thời Gian",
        "tab_frenet": "Frenet",
        "tab_heatmap": "Bản Đồ Nhiệt",
        "tab_results": "Kết Quả",
        "tab_ai_chat": "Trò Chuyện AI",
        
        # Tab Content
        "overview_label": "Khung nhìn 3D PyVista để hiển thị toàn bộ hầm với quản lý LOD.",
        "registration_label": "Không gian làm việc quản lý trạm và khớp mục tiêu.",
        "ransac_label": "Điều khiển phân đoạn RANSAC sẽ sử dụng tunnel_utils.py.",
        "centerline_label": "Lớp đường tâm được xem trước trong trình xem PyVista Tổng Quan.",
        "section_label": "Không gian làm việc cắt mặt cắt ngang.",
        "rings_label": "Không gian làm việc phân tích vòng đoạn bê tông.",
        "timeseries_label": "Biểu đồ lún và hội tụ chuỗi thời gian 4D.",
        "frenet_label": "Phân tích khung Frenet được hiển thị dưới dạng lớp phủ PyVista trong Tổng Quan.",
        "heatmap_label": "Lớp bản đồ nhiệt được xem trước trong trình xem PyVista Tổng Quan.",
        "ai_chat_placeholder": "Không gian làm việc trợ lý dữ liệu hầm AI.",
        
        # Registration Tab
        "station_table_headers": ["Trạm", "Dấu Thời Gian", "Điểm", "Mục Tiêu", "Tệp"],
        
        # Dialog Messages
        "import_dialog_title": "Nhập Đám Mây Điểm Faro Focus",
        "import_dialog_filter": "Đám Mây Điểm (*.las *.laz *.ply);;Tất Cả Tệp (*.*)",
        "loading_status": "Đang tải đám mây điểm thô với laspy / trình phân tích chỉ đỉnh...",
        "rendering_status": "Đang hiển thị tổng quan PyVista chỉ đỉnh...",
        "registration_status": "Đang chạy ghép nối SVD/ICP tuần tự...",
        
        # Error Messages
        "no_stations_error": "Không có trạm nào được nhập.",
        "pyvista_error": "Widget PyVista không được khởi tạo.",
        
        # Menu Items
        "file_menu": "Tệp",
        "edit_menu": "Chỉnh Sửa",
        "view_menu": "Xem",
        "tools_menu": "Công Cụ",
        "help_menu": "Trợ Giúp",
        "open_project": "Mở Dự Án",
        "save_project": "Lưu Dự Án",
        "export_results": "Xuất Kết Quả",
        "preferences": "Tùy Chọn",
        "exit": "Thoát",
        # Dynamic runtime messages
        "no_files_selected": "Chưa chọn tệp đám mây điểm nào.",
        "loading_station": "Đang tải trạm {index}/{count}: {name}",
        "detecting_targets": "Đang phát hiện mục tiêu cường độ cho {station}...",
        "target_detection_skipped": "{station}: bỏ qua phát hiện mục tiêu ({error})",
        "no_intensity_channel": "{station}: không có kênh cường độ để phát hiện mục tiêu.",
        "station_imported": "Đã nhập {station}.",
        "import_failed_title": "Nhập LAS thất bại",
        "registration_failed_title": "Đăng ký thất bại",
        "imported_n_stations": "Đã nhập {count} trạm với dấu thời gian {timestamp}",
        "station_log_entry": "{station}: {filename}, {points} điểm, {targets} mục tiêu",
        "rendered_latest": "Đã hiển thị trạm mới nhất: {points} điểm",
        "import_complete": "Hoàn tất nhập: đã tải {count} trạm",
        "points_label_loaded": "Điểm: {raw} thô / {rendered} hiển thị",
        "registration_dialog_title": "Đăng Ký",
        "registration_need_two": "Hãy tải ít nhất hai trạm trước khi ghép.",
        "registration_link_log": "{source} -> {target}: {method}, RMSE {rmse} mm",
        "registered_cloud_title": "Đám Mây Toàn Cục Đã Đăng Ký",
        "rmse_label_value": "RMSE: {rmse} mm",
        "registration_complete": "Đăng ký hoàn tất",
        "deformation_dialog_title": "Bản Đồ Nhiệt Biến Dạng",
        "deformation_need_two_ts": "Hãy tải ít nhất hai dấu thời gian, ví dụ T0 và T1.",
        "deformation_no_current": "Không có dấu thời gian hiện tại để so sánh.",
        "computing_heatmap_vs": "Đang tính bản đồ nhiệt biến dạng {current} vs {reference}...",
        "computing_heatmap_progress": "Đang tính bản đồ nhiệt biến dạng...",
        "no_deformation_result": "Không tạo được kết quả biến dạng.",
        "deformation_title": "Bản Đồ Nhiệt Biến Dạng - {current} vs {reference}",
        "heatmap_points_label": "Bản đồ nhiệt: {points} điểm, cảnh báo {pct}%",
        "p95_label": "Delta P95: {p95} mm",
        "deformation_log_stats": "Biến dạng {current} vs {reference}: trung bình {mean} mm, p95 {p95} mm, tối đa {max} mm, cảnh báo {warning}%",
        "threshold_bands_log": "Dải ngưỡng: ổn định {stable}%, thận trọng {caution}%, cảnh báo {warning}%",
        "deformation_complete": "Hoàn tất bản đồ nhiệt biến dạng",
        "deformation_failed_title": "Bản đồ nhiệt biến dạng thất bại",
        "screenshot_dialog_title": "Lưu Ảnh Chụp PyVista",
        "screenshot_filter": "Ảnh PNG (*.png)",
        "screenshot_failed_title": "Chụp màn hình thất bại",
        "screenshot_saved": "Đã lưu ảnh chụp: {path}",
    },
    
    "ko": {
        # Window title
        "window_title": "SSL 스마트 터널 모니터링 시스템 - 오송터널 4D LiDAR",
        
        # Sidebar
        "sidebar_title": "SSL 4D-LiDAR",
        "sidebar_subtitle": "오송터널 모니터링",
        "import_btn": "LAS / PLY 가져오기",
        "register_btn": "순차 정합",
        "deformation_btn": "Tn vs T0 히트맵",
        "language_btn": "🌐 한국어",
        
        # Import Settings
        "import_settings": "가져오기 설정",
        "timestamp_label": "타임스탬프",
        "auto_target_check": "강도 타겟 자동 감지",
        
        # Viewer Layers
        "viewer_layers": "뷰어 레이어",
        "centerline_check": "중심선",
        "heatmap_check": "히트맵",
        "ai_check": "AI 감지",
        
        # View Controls
        "view_box": "보기",
        "reset_camera_btn": "카메라 재설정",
        "screenshot_btn": "스크린샷",
        
        # Status Labels
        "points_label": "포인트: -",
        "rmse_label": "RMSE: -",
        "ready_status": "준비",
        
        # Tab Names
        "tab_overview": "개요",
        "tab_registration": "정합",
        "tab_ransac": "RANSAC",
        "tab_centerline": "중심선",
        "tab_section": "단면",
        "tab_rings": "링",
        "tab_timeseries": "시계열",
        "tab_frenet": "Frenet",
        "tab_heatmap": "히트맵",
        "tab_results": "결과",
        "tab_ai_chat": "AI 채팅",
        
        # Tab Content
        "overview_label": "LOD 관리를 통한 전체 터널 시각화를 위한 3D PyVista 뷰포트.",
        "registration_label": "스테이션 관리자 및 타겟 매칭 작업 공간.",
        "ransac_label": "RANSAC 세그먼테이션 제어는 tunnel_utils.py를 사용합니다.",
        "centerline_label": "중심선 레이어는 개요 PyVista 뷰어에서 미리 볼 수 있습니다.",
        "section_label": "단면 슬라이싱 작업 공간.",
        "rings_label": "콘크리트 세그먼트 링 분석 작업 공간.",
        "timeseries_label": "4D 시계열 침하 및 수렴 차트.",
        "frenet_label": "Frenet 프레임 분석은 개요에서 PyVista 오버레이로 렌더링됩니다.",
        "heatmap_label": "히트맵 레이어는 개요 PyVista 뷰어에서 미리 볼 수 있습니다.",
        "ai_chat_placeholder": "AI 터널 데이터 어시스턴트 작업 공간.",
        
        # Registration Tab
        "station_table_headers": ["스테이션", "타임스탬프", "포인트", "타겟", "파일"],
        
        # Dialog Messages
        "import_dialog_title": "Faro Focus 포인트 클라우드 가져오기",
        "import_dialog_filter": "포인트 클라우드 (*.las *.laz *.ply);;모든 파일 (*.*)",
        "loading_status": "laspy / 버텍스 전용 파서로 원시 포인트 클라우드 로딩 중...",
        "rendering_status": "버텍스 전용 PyVista 개요 렌더링 중...",
        "registration_status": "순차 SVD/ICP 스티칭 실행 중...",
        
        # Error Messages
        "no_stations_error": "가져온 스테이션이 없습니다.",
        "pyvista_error": "PyVista 위젯이 초기화되지 않았습니다.",
        
        # Menu Items
        "file_menu": "파일",
        "edit_menu": "편집",
        "view_menu": "보기",
        "tools_menu": "도구",
        "help_menu": "도움말",
        "open_project": "프로젝트 열기",
        "save_project": "프로젝트 저장",
        "export_results": "결과 내보내기",
        "preferences": "환경설정",
        "exit": "종료",
        # Dynamic runtime messages
        "no_files_selected": "선택된 포인트 클라우드 파일이 없습니다.",
        "loading_station": "스테이션 로딩 중 {index}/{count}: {name}",
        "detecting_targets": "{station}의 강도 타겟 감지 중...",
        "target_detection_skipped": "{station}: 타겟 감지 건너뜀 ({error})",
        "no_intensity_channel": "{station}: 타겟 감지를 위한 강도 채널이 없습니다.",
        "station_imported": "{station} 가져옴.",
        "import_failed_title": "LAS 가져오기 실패",
        "registration_failed_title": "정합 실패",
        "imported_n_stations": "{count}개 스테이션을 타임스탬프 {timestamp}(으)로 가져왔습니다",
        "station_log_entry": "{station}: {filename}, {points} 포인트, {targets} 타겟",
        "rendered_latest": "최신 스테이션 렌더링: {points} 포인트",
        "import_complete": "가져오기 완료: {count}개 스테이션 로드됨",
        "points_label_loaded": "포인트: {raw} 원본 / {rendered} 렌더링",
        "registration_dialog_title": "정합",
        "registration_need_two": "스티칭 전에 최소 두 개의 스테이션을 로드하세요.",
        "registration_link_log": "{source} -> {target}: {method}, RMSE {rmse} mm",
        "registered_cloud_title": "정합된 전역 클라우드",
        "rmse_label_value": "RMSE: {rmse} mm",
        "registration_complete": "정합 완료",
        "deformation_dialog_title": "변형 히트맵",
        "deformation_need_two_ts": "최소 두 개의 타임스탬프를 로드하세요. 예: T0 및 T1.",
        "deformation_no_current": "비교할 현재 타임스탬프가 없습니다.",
        "computing_heatmap_vs": "{current} vs {reference} 변형 히트맵 계산 중...",
        "computing_heatmap_progress": "변형 히트맵 계산 중...",
        "no_deformation_result": "변형 결과가 생성되지 않았습니다.",
        "deformation_title": "변형 히트맵 - {current} vs {reference}",
        "heatmap_points_label": "히트맵: {points} 포인트, 경고 {pct}%",
        "p95_label": "P95 델타: {p95} mm",
        "deformation_log_stats": "변형 {current} vs {reference}: 평균 {mean} mm, p95 {p95} mm, 최대 {max} mm, 경고 {warning}%",
        "threshold_bands_log": "임계 구간: 안정 {stable}%, 주의 {caution}%, 경고 {warning}%",
        "deformation_complete": "변형 히트맵 완료",
        "deformation_failed_title": "변형 히트맵 실패",
        "screenshot_dialog_title": "PyVista 스크린샷 저장",
        "screenshot_filter": "PNG 이미지 (*.png)",
        "screenshot_failed_title": "스크린샷 실패",
        "screenshot_saved": "스크린샷 저장됨: {path}",
    }
}

# Language metadata
LANGUAGE_INFO = {
    "en": {"name": "English", "flag": "🇺🇸", "code": "en"},
    "vi": {"name": "Tiếng Việt", "flag": "🇻🇳", "code": "vi"},
    "ko": {"name": "한국어", "flag": "🇰🇷", "code": "ko"},
}

def get_text(key: str, language: str = "en") -> str:
    """Get translated text for a given key and language."""
    if language not in TRANSLATIONS:
        language = "en"
    return TRANSLATIONS[language].get(key, key)

def get_all_texts(language: str = "en") -> dict:
    """Get all translations for a given language."""
    if language not in TRANSLATIONS:
        language = "en"
    return TRANSLATIONS[language]

def get_available_languages() -> list:
    """Get list of available language codes."""
    return list(TRANSLATIONS.keys())

def get_language_name(code: str) -> str:
    """Get the display name for a language code."""
    return LANGUAGE_INFO.get(code, {}).get("name", code)

def get_language_flag(code: str) -> str:
    """Get the flag emoji for a language code."""
    return LANGUAGE_INFO.get(code, {}).get("flag", "🌐")

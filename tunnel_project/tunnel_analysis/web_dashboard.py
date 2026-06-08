"""
web_dashboard.py - Web-based visualization dashboard using Dash + Plotly.
Per PDF section 3.7 / Phase 4: web-based 3D model rotation, zoom, data query.
Run: python -m tunnel_analysis.web_dashboard
"""
from .common import *
from .models import PipelineContext
import threading
import webbrowser


def build_app(context: PipelineContext):
    """Build and return Dash app from current pipeline context."""
    try:
        import dash
        from dash import dcc, html, Input, Output, callback
        import plotly.graph_objects as go
        import plotly.express as px
    except ImportError:
        raise RuntimeError("dash + plotly required: pip install dash plotly")

    app = dash.Dash(__name__, title="Tunnel Analysis Dashboard - CBNU")

    # ── Prepare data ──────────────────────────────────────────────────────
    sections = context.sections
    params   = context.parameters or {}
    cl       = context.centerline
    pts      = context.working_points

    # Section table data
    sec_data = []
    if sections:
        for s in sections:
            sec_data.append({
                "Chainage (m)":    round(s.chainage, 3),
                "H1 (m)":          round(s.H1, 3) if np.isfinite(s.H1) else None,
                "W1 (m)":          round(s.W1, 3) if np.isfinite(s.W1) else None,
                "Ovality (%)":     round(s.ovality, 3) if np.isfinite(s.ovality) else None,
                "Ecc (mm)":        round(s.eccentricity, 2) if np.isfinite(s.eccentricity) else None,
                "R_fit (m)":       round(s.radius_fit, 3) if np.isfinite(s.radius_fit) else None,
                "Clearance":       "⚠ VIOLATION" if s.clearance_violation else "OK",
            })

    chainages    = [s["Chainage (m)"] for s in sec_data]
    settlements  = [s["H1 (m)"] for s in sec_data]
    convergences = [s["W1 (m)"] for s in sec_data]
    ovalities    = [s["Ovality (%)"] for s in sec_data]

    # ── Layout ────────────────────────────────────────────────────────────
    BLUE  = "#0F4C81"
    LGRAY = "#F1F5F9"

    app.layout = html.Div([
        # Header
        html.Div([
            html.H1("TUNNEL STRUCTURAL HEALTH MONITORING",
                    style={"color": "white", "margin": "0", "fontSize": "20px",
                           "fontWeight": "bold", "fontFamily": "Arial"}),
            html.P("LiDAR Point Cloud Analysis Dashboard · CBNU Smart Structure Lab",
                   style={"color": "#CBD5E1", "margin": "4px 0 0 0", "fontSize": "12px"}),
        ], style={"background": BLUE, "padding": "16px 24px"}),

        # Summary cards
        html.Div([
            _card("Total Sections", str(len(sections))),
            _card("Crown Settlement", f"{params.get('crown_settlement_mm', float('nan')):.1f} mm"),
            _card("Convergence", f"{params.get('lateral_convergence_mm', float('nan')):.1f} mm"),
            _card("Ovality (mean)", f"{params.get('ovality_mean_pct', float('nan')):.2f} %"),
            _card("Eccentricity", f"{params.get('eccentricity_mean_mm', float('nan')):.1f} mm"),
            _card("Profile", context.tunnel_profile),
        ], style={"display": "flex", "gap": "12px", "padding": "16px 24px",
                  "background": LGRAY, "flexWrap": "wrap"}),

        # Tabs
        dcc.Tabs([
            # Tab 1: 3D Point Cloud
            dcc.Tab(label="3D Point Cloud", children=[
                html.Div([
                    dcc.Graph(id="graph-3d", figure=_fig_3d(pts, cl),
                              style={"height": "600px"})
                ], style={"padding": "12px"})
            ]),

            # Tab 2: Deformation Charts
            dcc.Tab(label="Deformation Charts", children=[
                html.Div([
                    html.P("Tip: click any point on a chart to inspect that section.",
                           style={"color": "#64748B", "fontSize": "12px",
                                  "margin": "0 0 8px 4px"}),
                    dcc.Graph(id="trend-settlement", figure=_fig_trend(chainages, settlements,
                        "Crown Height H1 (m)", "#1D4ED8", 10.0, 25.0)),
                    dcc.Graph(id="trend-convergence", figure=_fig_trend(chainages, convergences,
                        "Clear Width W1 (m)", "#047857", 15.0, 30.0)),
                    dcc.Graph(id="trend-ovality", figure=_fig_trend(chainages, ovalities,
                        "Ovality ε (%)", "#C2410C", 0.5, 1.0)),
                    html.Div(id="section-detail",
                             children=_section_detail_panel(None),
                             style={"marginTop": "12px"}),
                ], style={"padding": "12px"})
            ]),

            # Tab 3: Section Table
            dcc.Tab(label="Section Data", children=[
                html.Div([
                    html.Div([
                        html.Label("Filter: ", style={"fontSize": "12px",
                                   "color": "#475569", "marginRight": "8px"}),
                        dcc.Dropdown(id="table-filter",
                            options=[{"label": "All sections", "value": "all"},
                                     {"label": "Warnings only", "value": "warnings"},
                                     {"label": "Clearance violations only", "value": "violations"}],
                            value="all", clearable=False,
                            style={"width": "280px", "fontSize": "12px"}),
                    ], style={"display": "flex", "alignItems": "center",
                              "marginBottom": "10px"}),
                    html.Div(id="section-table-wrap", children=_data_table(sec_data)),
                ], style={"padding": "12px", "overflowX": "auto"})
            ]),

            # Tab 4: Warnings
            dcc.Tab(label="Warnings", children=[
                html.Div([
                    _warnings_panel(sections)
                ], style={"padding": "12px"})
            ]),
        ], style={"fontFamily": "Arial", "fontSize": "13px"}),

        # Footer
        html.Div([
            html.P("Tunnel Analysis v4.0 · CBNU Smart Structure Lab · "
                   "LiDAR-based Structural Health Monitoring",
                   style={"color": "#64748B", "fontSize": "11px", "margin": "0"})
        ], style={"background": LGRAY, "padding": "10px 24px",
                  "borderTop": "1px solid #E2E8F0", "textAlign": "center"}),
    ], style={"fontFamily": "Arial, sans-serif", "background": "white", "minHeight": "100vh"})

    # ── Interactivity ─────────────────────────────────────────────────────
    # Click any deformation chart point -> show that section's full detail.
    @app.callback(
        Output("section-detail", "children"),
        Input("trend-settlement", "clickData"),
        Input("trend-convergence", "clickData"),
        Input("trend-ovality", "clickData"),
    )
    def _on_chart_click(c_set, c_con, c_ov):
        for cd in (c_set, c_con, c_ov):
            row = _pick_section(sec_data, cd)
            if row is not None:
                return _section_detail_panel(row)
        return _section_detail_panel(None)

    # Filter the section table by status.
    @app.callback(
        Output("section-table-wrap", "children"),
        Input("table-filter", "value"),
    )
    def _on_filter(mode):
        return _data_table(_filter_sections(sec_data, mode))

    return app


def _pick_section(sec_data, click_data):
    """Resolve a clicked chart point to its section row dict (or None).

    Prefers the Plotly point index; falls back to nearest chainage on the x
    axis so it stays robust if the index is absent.
    """
    if not sec_data or not click_data:
        return None
    points = click_data.get("points") or []
    if not points:
        return None
    p = points[0]
    idx = p.get("pointIndex", p.get("pointNumber"))
    if idx is None:
        x = p.get("x")
        if x is None:
            return None
        chainages = [r["Chainage (m)"] for r in sec_data]
        idx = int(np.argmin([abs(float(c) - float(x)) for c in chainages]))
    if 0 <= idx < len(sec_data):
        return sec_data[idx]
    return None


def _filter_sections(sec_data, mode):
    """Filter prepared section rows by status: all / warnings / violations."""
    rows = sec_data or []
    if mode == "violations":
        return [r for r in rows if "VIOLATION" in str(r.get("Clearance", ""))]
    if mode == "warnings":
        out = []
        for r in rows:
            ov = r.get("Ovality (%)")
            ec = r.get("Ecc (mm)")
            viol = "VIOLATION" in str(r.get("Clearance", ""))
            if viol or (ov is not None and ov >= 0.5) or (ec is not None and ec >= 10.0):
                out.append(r)
        return out
    return rows


def _section_detail_panel(row):
    """Render a clicked section's parameters as a detail card."""
    from dash import html
    if not row:
        return html.P("Click a point on a chart above to inspect that section.",
                      style={"color": "#64748B", "fontSize": "12px",
                             "fontStyle": "italic"})
    body = []
    for k, v in row.items():
        color = "#DC2626" if "VIOLATION" in str(v) else "#111827"
        body.append(html.Tr([
            html.Td(k, style={"padding": "5px 12px", "color": "#475569",
                              "fontSize": "12px", "fontWeight": "600",
                              "borderBottom": "1px solid #F1F5F9"}),
            html.Td(str(v) if v is not None else "-",
                    style={"padding": "5px 12px", "color": color,
                           "fontSize": "12px",
                           "borderBottom": "1px solid #F1F5F9"}),
        ]))
    return html.Div([
        html.H4(f"Section @ Chainage {row.get('Chainage (m)')} m",
                style={"color": "#0F4C81", "fontSize": "14px",
                       "margin": "0 0 8px 0"}),
        html.Table(html.Tbody(body),
                   style={"borderCollapse": "collapse", "minWidth": "320px",
                          "border": "1px solid #E2E8F0", "borderRadius": "6px"}),
    ], style={"background": "#F8FAFC", "padding": "12px 16px",
              "borderRadius": "8px", "border": "1px solid #E2E8F0"})


def _card(title, value):
    from dash import html
    color = "#DC2626" if "VIOLATION" in str(value) else "#0F172A"
    return html.Div([
        html.P(title, style={"color": "#64748B", "fontSize": "11px",
                              "margin": "0 0 4px 0", "fontWeight": "600"}),
        html.P(value, style={"color": color, "fontSize": "18px",
                              "margin": "0", "fontWeight": "bold"}),
    ], style={"background": "white", "padding": "12px 16px", "borderRadius": "8px",
              "border": "1px solid #E2E8F0", "minWidth": "130px",
              "boxShadow": "0 1px 3px rgba(0,0,0,0.08)"})


def _fig_3d(pts, cl):
    import plotly.graph_objects as go
    fig = go.Figure()
    if pts is not None and len(pts):
        step = max(1, len(pts) // 50000)
        p = pts[::step]
        fig.add_trace(go.Scatter3d(
            x=p[:, 0], y=p[:, 1], z=p[:, 2],
            mode="markers",
            marker=dict(size=1.5, color=p[:, 2], colorscale="Viridis",
                        opacity=0.7, showscale=True,
                        colorbar=dict(title="Z (m)", thickness=12)),
            name="Point Cloud"))
    if cl is not None and len(cl):
        fig.add_trace(go.Scatter3d(
            x=cl[:, 0], y=cl[:, 1], z=cl[:, 2],
            mode="lines+markers",
            line=dict(color="#EF4444", width=4),
            marker=dict(size=3, color="#EF4444"),
            name="Centerline"))
    fig.update_layout(
        scene=dict(
            xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)",
            bgcolor="white",
            xaxis=dict(backgroundcolor="#F8FAFC", gridcolor="#E2E8F0"),
            yaxis=dict(backgroundcolor="#F8FAFC", gridcolor="#E2E8F0"),
            zaxis=dict(backgroundcolor="#F8FAFC", gridcolor="#E2E8F0"),
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        title="3D Point Cloud + Centerline",
        paper_bgcolor="white",
        legend=dict(x=0.01, y=0.99))
    return fig


def _fig_trend(chainages, values, ylabel, color, thr_c, thr_r):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=chainages, y=values, mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=5), name=ylabel))
    if chainages:
        fig.add_hline(y=thr_c, line_dash="dash", line_color="#D97706",
                      annotation_text=f"Caution {thr_c}", annotation_position="right")
        fig.add_hline(y=thr_r, line_dash="dash", line_color="#DC2626",
                      annotation_text=f"Critical {thr_r}", annotation_position="right")
    fig.update_layout(
        title=ylabel, xaxis_title="Chainage (m)", yaxis_title=ylabel,
        paper_bgcolor="white", plot_bgcolor="#F8FAFC",
        margin=dict(l=60, r=60, t=40, b=40), height=280,
        xaxis=dict(gridcolor="#E2E8F0"), yaxis=dict(gridcolor="#E2E8F0"))
    return fig


def _data_table(sec_data):
    from dash import html
    if not sec_data:
        return html.P("No section data available. Run Step 6.3 first.",
                      style={"color": "#64748B"})
    headers = list(sec_data[0].keys())
    rows = []
    for row in sec_data:
        cells = []
        for h in headers:
            val = row.get(h, "")
            color = "#DC2626" if "VIOLATION" in str(val) else "#111827"
            cells.append(html.Td(str(val) if val is not None else "-",
                                  style={"padding": "6px 10px", "color": color,
                                         "borderBottom": "1px solid #E2E8F0",
                                         "fontSize": "12px"}))
        rows.append(html.Tr(cells))
    return html.Table([
        html.Thead(html.Tr([
            html.Th(h, style={"padding": "8px 10px", "background": "#0F4C81",
                               "color": "white", "fontSize": "12px",
                               "fontWeight": "600", "textAlign": "left"})
            for h in headers])),
        html.Tbody(rows)
    ], style={"borderCollapse": "collapse", "width": "100%",
              "border": "1px solid #E2E8F0", "borderRadius": "6px"})


def _warnings_panel(sections):
    from dash import html
    THRESHOLDS = {
        "ovality":     {"caution": 0.5,  "critical": 1.0},
        "eccentricity":{"caution": 10.0, "critical": 25.0},
    }
    warnings = []
    for s in (sections or []):
        if s.clearance_violation:
            warnings.append(("CRITICAL", f"Ch {s.chainage:.2f}m",
                             "Clearance Violation", f"{s.min_clearance_dist:.3f}m"))
        for attr, thr in THRESHOLDS.items():
            val = getattr(s, attr, float("nan"))
            if not np.isfinite(val): continue
            if val >= thr["critical"]:
                warnings.append(("CRITICAL", f"Ch {s.chainage:.2f}m",
                                 attr, f"{val:.3f}"))
            elif val >= thr["caution"]:
                warnings.append(("CAUTION", f"Ch {s.chainage:.2f}m",
                                 attr, f"{val:.3f}"))
    if not warnings:
        return html.Div([
            html.H3("✓ No structural warnings detected",
                    style={"color": "#047857", "textAlign": "center"}),
            html.P("All parameters within acceptable limits.",
                   style={"color": "#64748B", "textAlign": "center"})
        ], style={"padding": "40px"})
    items = []
    for status, ch, param, val in warnings:
        bg = "#FEE2E2" if status == "CRITICAL" else "#FEF3C7"
        bc = "#DC2626" if status == "CRITICAL" else "#D97706"
        items.append(html.Div([
            html.Span(status, style={"background": bc, "color": "white",
                                      "padding": "2px 8px", "borderRadius": "4px",
                                      "fontSize": "11px", "fontWeight": "bold",
                                      "marginRight": "10px"}),
            html.Span(f"{ch}  |  {param}  =  {val}",
                      style={"fontSize": "13px", "color": "#111827"}),
        ], style={"background": bg, "padding": "10px 14px", "borderRadius": "6px",
                  "border": f"1px solid {bc}", "marginBottom": "8px"}))
    return html.Div(items)


def launch_dashboard(context: PipelineContext, port: int = 8050,
                     open_browser: bool = True) -> None:
    """Launch web dashboard in a background thread."""
    app = build_app(context)
    url = f"http://127.0.0.1:{port}"
    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"Dashboard running at {url}")
    # SECURITY: bind to loopback only. The dashboard has no authentication and
    # runs Dash's development server, so it must NOT be exposed on 0.0.0.0 or a
    # public interface. Keep debug=False (avoids the Werkzeug debugger RCE).
    app.run(host="127.0.0.1", port=port, debug=False)

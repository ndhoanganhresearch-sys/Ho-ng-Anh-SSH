// Step 6 explainer deck (Vietnamese) for SSL Tunnel Analysis.
// Run: NODE_PATH=<global node_modules> node build_step6_deck.js
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.author = "SSL Tunnel Analysis";
pres.title = "Step 6 — Phan tich bien dang T0->Tn";

// ---- Palette (engineering / monitoring theme) ----
const NAVY = "0F2A43";   // dominant dark
const NAVY2 = "163B5C";
const TEAL = "14B8A6";   // accent
const TEAL_D = "0E8C80";
const ICE = "CFE8F2";
const INK = "1E293B";
const MUTED = "64748B";
const LIGHT = "F4F7FA";
const WHITE = "FFFFFF";
const OK = "2EA86A";
const CAUT = "E0A100";
const CRIT = "D7263D";

const W = 13.33, H = 7.5, M = 0.7;
const HF = "Georgia";   // headers
const BF = "Calibri";   // body

const shadow = () => ({ type: "outer", color: "000000", blur: 7, offset: 3, angle: 135, opacity: 0.18 });

// ---- REAL measured values (render_step6_figures.py on time_series_deformation T0..T5) ----
const REAL = {
  labels: ["T0","T1","T2","T3","T4","T5"],
  max:   [0, 6.3, 12.6, 19.9, 29.7, 44.5],
  p95:   [0, 0.6, 3.4, 7.5, 12.9, 20.4],
  median:[0, 0, 0, 0, 0, 0],
  rate: 14.94, r2: 1.00,
  fig_map: "step6_figures/m3c2_map.png",
  fig_3d: "step6_figures/m3c2_3d.png",
};

function bgLight(s){ s.background = { color: LIGHT }; }
function bgDark(s){ s.background = { color: NAVY }; }

// header used on content slides
function header(s, kicker, title){
  s.addText(kicker.toUpperCase(), { x: M, y: 0.42, w: W-2*M, h: 0.3, fontFace: BF, fontSize: 12, bold: true, color: TEAL_D, charSpacing: 2, margin: 0 });
  s.addText(title, { x: M, y: 0.7, w: W-2*M, h: 0.7, fontFace: HF, fontSize: 28, bold: true, color: NAVY, margin: 0 });
}
function pageNum(s, n){
  s.addText(String(n), { x: W-1.0, y: H-0.5, w: 0.5, h: 0.3, fontFace: BF, fontSize: 10, color: MUTED, align: "right", margin: 0 });
}
// rounded card
function card(s, x, y, w, h, fill){
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill||WHITE }, line: { color: "E2E8F0", width: 1 }, rectRadius: 0.08, shadow: shadow() });
}

// ============================================================ Slide 1 — Title
let s = pres.addSlide(); bgDark(s);
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.28, h: H, fill: { color: TEAL } });
// faux tunnel rings motif (concentric ovals, right side)
[3.2, 2.5, 1.8, 1.1].forEach((r, i) => {
  s.addShape(pres.shapes.OVAL, { x: 10.4 - r, y: H/2 - r*0.8, w: r*2, h: r*1.6,
    fill: { color: NAVY }, line: { color: i===3?TEAL:NAVY2, width: i===3?3:2 } });
});
s.addText("SSL TUNNEL ANALYSIS", { x: 0.9, y: 1.5, w: 8.5, h: 0.4, fontFace: BF, fontSize: 14, bold: true, color: TEAL, charSpacing: 3, margin: 0 });
s.addText("Step 6 — Phân tích biến dạng\ntheo thời gian (T0 → Tn)", { x: 0.9, y: 2.0, w: 9.0, h: 1.8, fontFace: HF, fontSize: 40, bold: true, color: WHITE, lineSpacingMultiple: 1.05, margin: 0 });
s.addText("Tool hoạt động thế nào và kết quả nghĩa là gì", { x: 0.9, y: 3.95, w: 9.0, h: 0.5, fontFace: BF, fontSize: 18, color: ICE, italic: true, margin: 0 });
s.addText([
  { text: "M3C2 displacement", options: { color: ICE } },
  { text: "   •   ", options: { color: TEAL } },
  { text: "trend & forecast", options: { color: ICE } },
  { text: "   •   ", options: { color: TEAL } },
  { text: "cảnh báo theo section", options: { color: ICE } },
], { x: 0.9, y: 5.3, w: 10, h: 0.4, fontFace: BF, fontSize: 14, margin: 0 });

// ============================================================ Slide 2 — Step6 in workflow + purpose
s = pres.addSlide(); bgLight(s);
header(s, "Bối cảnh", "Step 6 nằm ở đâu & giải quyết điều gì");
const steps = ["1 Load","2 Làm sạch","3 Đăng ký T0/Tn","4 Tìm tuyến","5 Mặt cắt 2D","6 Biến dạng","7 Cảnh báo"];
const sw = (W-2*M-0.0)/steps.length;
steps.forEach((t,i)=>{
  const on = i===5;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M+i*sw, y: 1.65, w: sw-0.12, h: 0.7, fill: { color: on?TEAL:WHITE }, line: { color: on?TEAL:"D8E0E8", width: 1 }, rectRadius: 0.06, shadow: on?shadow():undefined });
  s.addText(t, { x: M+i*sw, y: 1.65, w: sw-0.12, h: 0.7, align: "center", valign: "middle", fontFace: BF, fontSize: 12, bold: on, color: on?WHITE:INK, margin: 0 });
});
s.addText("Step 6 chỉ chạy khi đã có T0 + Tn (đã làm sạch & đăng ký về cùng hệ toạ độ).", { x: M, y: 2.5, w: W-2*M, h: 0.4, fontFace: BF, fontSize: 13, italic: true, color: MUTED, margin: 0 });

const purpose = [
  ["Đo chuyển vị bề mặt", "So sánh đám mây Tn với mốc T0 để biết mỗi điểm/section đã dịch chuyển bao nhiêu mm."],
  ["Theo dõi xu hướng", "Nhiều epoch (T0…Tn) → đường biến dạng theo thời gian, thấy được tốc độ tăng."],
  ["Dự báo ngưỡng", "Ngoại suy xu hướng để ước tính khi nào chạm CAUTION / CRITICAL."],
  ["Khoanh vùng cảnh báo", "Phân loại từng mặt cắt OK / CAUTION / CRITICAL, gắn đúng chainage cục bộ."],
];
const cw = (W-2*M-0.6)/2, ch = 1.5;
purpose.forEach((p,i)=>{
  const x = M + (i%2)*(cw+0.6), y = 3.15 + Math.floor(i/2)*(ch+0.35);
  card(s, x, y, cw, ch);
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.1, h: ch, fill: { color: TEAL } });
  s.addText(p[0], { x: x+0.3, y: y+0.18, w: cw-0.5, h: 0.4, fontFace: HF, fontSize: 17, bold: true, color: NAVY, margin: 0 });
  s.addText(p[1], { x: x+0.3, y: y+0.62, w: cw-0.5, h: ch-0.7, fontFace: BF, fontSize: 13.5, color: INK, margin: 0 });
});
pageNum(s,2);

// ============================================================ Slide 3 — T0 vs Tn + registration
s = pres.addSlide(); bgLight(s);
header(s, "Khái niệm nền tảng", "T0, Tn và vì sao phải đăng ký trước");
const colw = (W-2*M-0.6)/2;
// T0 card
card(s, M, 1.7, colw, 2.0, NAVY);
s.addText("T0 — MỐC THAM CHIẾU", { x: M+0.35, y: 1.95, w: colw-0.7, h: 0.4, fontFace: BF, fontSize: 13, bold: true, color: TEAL, charSpacing: 1.5, margin: 0 });
s.addText("Lần quét gốc, coi là tunnel “sạch / chưa biến dạng”. Mọi chuyển vị được đo TƯƠNG ĐỐI so với T0.", { x: M+0.35, y: 2.4, w: colw-0.7, h: 1.1, fontFace: BF, fontSize: 14.5, color: WHITE, margin: 0 });
// Tn card
card(s, M+colw+0.6, 1.7, colw, 2.0, TEAL);
s.addText("Tn — EPOCH GIÁM SÁT", { x: M+colw+0.95, y: 1.95, w: colw-0.7, h: 0.4, fontFace: BF, fontSize: 13, bold: true, color: NAVY, charSpacing: 1.5, margin: 0 });
s.addText("Lần quét sau (tháng/quý). So với T0 để lấy lún đỉnh, hội tụ, ô-van, lệch tâm tại thời điểm n.", { x: M+colw+0.95, y: 2.4, w: colw-0.7, h: 1.1, fontFace: BF, fontSize: 14.5, color: NAVY, margin: 0 });

s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 3.95, w: W-2*M, h: 2.35, fill: { color: WHITE }, line: { color: "E2E8F0", width: 1 }, rectRadius: 0.06, shadow: shadow() });
s.addText("⚠  Đăng ký (registration) phải làm TRƯỚC Step 6", { x: M+0.35, y: 4.15, w: W-2*M-0.7, h: 0.4, fontFace: HF, fontSize: 18, bold: true, color: CRIT, margin: 0 });
s.addText([
  { text: "Hai lần quét thường ở hệ toạ độ khác nhau (đặt máy khác). Nếu không đưa Tn về đúng khung của T0, hiệu số sẽ là sai số đặt máy chứ không phải biến dạng.", options: { breakLine: true, color: INK } },
  { text: "Quan trọng: registration dùng trimmed-ICP / target cố định để căn theo phần ỔN ĐỊNH, KHÔNG được triệt tiêu biến dạng cục bộ.", options: { breakLine: true, color: INK, bold: true } },
  { text: "Kiểm chứng: test register_epochs giữ lún cục bộ 32.6 mm / GT 60 mm (không bị “nuốt” về 0).", options: { color: TEAL_D, italic: true } },
], { x: M+0.35, y: 4.6, w: W-2*M-0.7, h: 1.6, fontFace: BF, fontSize: 14, lineSpacingMultiple: 1.15, paraSpaceAfter: 6, margin: 0 });
pageNum(s,3);

// ============================================================ Slide 4 — sub-steps flow 6.1-6.5
s = pres.addSlide(); bgLight(s);
header(s, "Quy trình con", "Các bước trong Step 6: 6.1 → 6.5");
const subs = [
  ["6.1","Load epochs","Nạp T0 (tham chiếu) và Tn (giám sát). Có thể nạp cả chuỗi T0…T5."],
  ["6.2","Trend chart","Vẽ xu hướng biến dạng theo từng epoch (p95 và đỉnh max_abs)."],
  ["6.3","M3C2 map","Bản đồ chuyển vị có dấu T0→Tn theo pháp tuyến bề mặt + ngưỡng phát hiện (LoD)."],
  ["6.5","Forecast","Ngoại suy xu hướng → dự báo thời điểm chạm CAUTION / CRITICAL."],
];
const bw = (W-2*M-3*0.4)/4;
subs.forEach((p,i)=>{
  const x = M + i*(bw+0.4), y = 1.85;
  card(s, x, y, bw, 3.6);
  s.addShape(pres.shapes.OVAL, { x: x+bw/2-0.45, y: y+0.35, w: 0.9, h: 0.9, fill: { color: NAVY } });
  s.addText(p[0], { x: x+bw/2-0.45, y: y+0.35, w: 0.9, h: 0.9, align: "center", valign: "middle", fontFace: HF, fontSize: 18, bold: true, color: TEAL, margin: 0 });
  s.addText(p[1], { x: x+0.2, y: y+1.45, w: bw-0.4, h: 0.5, align: "center", fontFace: HF, fontSize: 16, bold: true, color: NAVY, margin: 0 });
  s.addText(p[2], { x: x+0.22, y: y+2.0, w: bw-0.44, h: 1.45, align: "center", fontFace: BF, fontSize: 12.5, color: INK, margin: 0 });
  if(i<3) s.addText("→", { x: x+bw+0.04, y: y+1.4, w: 0.34, h: 0.6, align: "center", valign:"middle", fontFace: BF, fontSize: 22, bold:true, color: TEAL, margin: 0 });
});
s.addText("Mẹo: với 2 scan (T0/Tn), 6.2 tự thêm baseline T0 = 0 mm rồi nối tới Tn để đường trend có ≥ 2 điểm.", { x: M, y: 5.75, w: W-2*M, h: 0.5, fontFace: BF, fontSize: 13, italic: true, color: MUTED, margin: 0 });
pageNum(s,4);

// ============================================================ Slide 5 — M3C2 detail
s = pres.addSlide(); bgLight(s);
header(s, "6.3 — Cách tính", "M3C2: chuyển vị có dấu + ngưỡng phát hiện");
const m3 = [
  ["Pháp tuyến bề mặt", "Tại mỗi corepoint, ước lượng pháp tuyến cục bộ trong bán kính normal_radius."],
  ["Khoảng cách có dấu", "Chiếu sai khác T0→Tn lên pháp tuyến trong hình trụ cyl_radius → distance_mm (âm = lún vào)."],
  ["LoD (mức phát hiện)", "lod_mm = độ bất định do nhám/nhiễu. Chỉ |distance| > LoD mới coi là biến dạng THẬT."],
  ["significant mask", "Đánh dấu các điểm vượt LoD → loại nhiễu, tránh báo động giả."],
];
m3.forEach((p,i)=>{
  const y = 1.85 + i*1.18;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y, w: 7.4, h: 1.0, fill: { color: WHITE }, line: { color: "E2E8F0", width: 1 }, rectRadius: 0.06 });
  s.addShape(pres.shapes.OVAL, { x: M+0.2, y: y+0.22, w: 0.56, h: 0.56, fill: { color: TEAL } });
  s.addText(String(i+1), { x: M+0.2, y: y+0.22, w: 0.56, h: 0.56, align:"center", valign:"middle", fontFace: HF, fontSize: 15, bold:true, color: WHITE, margin: 0 });
  s.addText(p[0], { x: M+0.95, y: y+0.12, w: 6.3, h: 0.35, fontFace: HF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
  s.addText(p[1], { x: M+0.95, y: y+0.46, w: 6.3, h: 0.5, fontFace: BF, fontSize: 12.5, color: INK, margin: 0 });
});
// formula / interpretation panel
card(s, 8.5, 1.85, W-M-8.5, 4.0, NAVY);
s.addText("Ý nghĩa con số", { x: 8.8, y: 2.05, w: 3.6, h: 0.4, fontFace: BF, fontSize: 13, bold: true, color: TEAL, charSpacing: 1.5, margin: 0 });
s.addText([
  { text: "distance_mm < 0", options: { bold: true, color: WHITE, breakLine: true } },
  { text: "bề mặt dịch VÀO trong (lún/hội tụ).", options: { color: ICE, breakLine: true } },
  { text: "", options: { breakLine: true, fontSize: 6 } },
  { text: "|distance| ≤ LoD", options: { bold: true, color: WHITE, breakLine: true } },
  { text: "trong vùng nhiễu → KHÔNG kết luận.", options: { color: ICE, breakLine: true } },
  { text: "", options: { breakLine: true, fontSize: 6 } },
  { text: "quality_warning", options: { bold: true, color: CAUT, breakLine: true } },
  { text: "nếu >50% corepoint không có điểm Tn lân cận (quét thiếu) → cảnh báo độ phủ.", options: { color: ICE } },
], { x: 8.8, y: 2.5, w: W-M-8.5-0.6, h: 3.2, fontFace: BF, fontSize: 13.5, lineSpacingMultiple: 1.1, margin: 0 });
pageNum(s,5);

// ============================================================ Slide 6 — REAL M3C2 output images
s = pres.addSlide(); bgLight(s);
header(s, "Kết quả thật — dữ liệu test", "Bản đồ biến dạng M3C2: T0 → T5");
// 3D off-screen render (left)
s.addImage({ path: REAL.fig_3d, x: 0.6, y: 1.75, w: 7.0, h: 3.62 });
s.addText("Đám mây 3D tô màu theo chuyển vị (PyVista off-screen)", { x: 0.6, y: 5.42, w: 7.0, h: 0.35, align: "center", fontFace: BF, fontSize: 11, italic: true, color: MUTED, margin: 0 });
// unrolled 2D map (right top)
s.addImage({ path: REAL.fig_map, x: 7.85, y: 1.75, w: 5.0, h: 1.98 });
// zones card (right bottom)
card(s, 7.85, 4.0, 5.0, 1.45);
s.addText([
  { text: "3 vùng hư hỏng cục bộ (đúng ground truth):", options: { bold: true, color: NAVY, breakLine: true } },
  { text: "• Lún đỉnh @ chainage ~20 m  (xanh, đỉnh)", options: { color: INK, breakLine: true } },
  { text: "• Hội tụ vách @ ~45 m", options: { color: INK, breakLine: true } },
  { text: "• Hư hỏng cục bộ @ ~65 m (từ T3)", options: { color: INK } },
], { x: 8.1, y: 4.15, w: 4.6, h: 1.2, fontFace: BF, fontSize: 12, lineSpacingMultiple: 1.12, margin: 0 });
s.addText("15.456 corepoint · method = M3C2 · đỉnh chuyển vị thật −44.5 mm. Không phải minh hoạ — chạy từ dataset time_series_deformation.",
  { x: 0.6, y: 5.85, w: W-1.2, h: 0.5, fontFace: BF, fontSize: 12, color: TEAL_D, italic: true, margin: 0 });
pageNum(s,6);

// ============================================================ Slide 7 — 4 deformation parameters
s = pres.addSlide(); bgLight(s);
header(s, "Đầu ra chính", "4 tham số biến dạng & ngưỡng cảnh báo");
const params = [
  ["Crown settlement", "Lún đỉnh", "Hạ thấp của đỉnh hầm so với T0.", "> 10 mm", "> 25 mm"],
  ["Lateral convergence", "Hội tụ ngang (dW)", "Thu hẹp bề rộng giữa hai vách.", "> 10 mm", "> 25 mm"],
  ["Ovality", "Độ ô-van", "Mức méo khỏi hình tròn lý tưởng.", "> 0.5 %", "> 1.0 %"],
  ["Eccentricity", "Lệch tâm", "Dịch tâm mặt cắt so với trục.", "> 10 mm", "> 25 mm"],
];
const pcw = (W-2*M-0.6)/2, pch = 1.95;
params.forEach((p,i)=>{
  const x = M + (i%2)*(pcw+0.6), y = 1.8 + Math.floor(i/2)*(pch+0.35);
  card(s, x, y, pcw, pch);
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.12, h: pch, fill: { color: TEAL } });
  s.addText(p[0], { x: x+0.35, y: y+0.2, w: pcw-0.6, h: 0.4, fontFace: HF, fontSize: 18, bold: true, color: NAVY, margin: 0 });
  s.addText(p[1] + " — " + p[2], { x: x+0.35, y: y+0.66, w: pcw-0.6, h: 0.6, fontFace: BF, fontSize: 13, color: INK, margin: 0 });
  // threshold chips
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x+0.35, y: y+1.33, w: 1.9, h: 0.46, fill: { color: "FBF1D2" }, line:{color:CAUT,width:1}, rectRadius: 0.06 });
  s.addText([{text:"CAUTION  ",options:{bold:true,color:CAUT}},{text:p[3],options:{color:INK}}], { x: x+0.35, y: y+1.33, w: 1.9, h: 0.46, align:"center", valign:"middle", fontFace: BF, fontSize: 11.5, margin: 0 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x+2.4, y: y+1.33, w: 1.9, h: 0.46, fill: { color: "F7D7DC" }, line:{color:CRIT,width:1}, rectRadius: 0.06 });
  s.addText([{text:"CRITICAL  ",options:{bold:true,color:CRIT}},{text:p[4],options:{color:INK}}], { x: x+2.4, y: y+1.33, w: 1.9, h: 0.46, align:"center", valign:"middle", fontFace: BF, fontSize: 11.5, margin: 0 });
});
pageNum(s,7);

// ============================================================ Slide 8 — Trend chart p95 vs max
s = pres.addSlide(); bgLight(s);
header(s, "6.2 — Đồ thị xu hướng (số đo thật)", "median vs p95 vs đỉnh max_abs");
s.addChart(pres.charts.LINE, [
  { name: "max_abs_mm (đỉnh)", labels: REAL.labels, values: REAL.max },
  { name: "p95_abs_mm (toàn cloud)", labels: REAL.labels, values: REAL.p95 },
  { name: "median_mm (toàn cloud)", labels: REAL.labels, values: REAL.median },
], {
  x: M, y: 1.8, w: 7.6, h: 4.6, lineSize: 3, lineSmooth: true,
  chartColors: [CRIT, MUTED, "B6C2CE"], showLegend: true, legendPos: "b", legendColor: INK, legendFontSize: 11,
  catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
  valAxisTitle: "displacement (mm)", showValAxisTitle: true, valAxisTitleColor: MUTED, valAxisTitleFontSize: 11,
});
card(s, 8.5, 1.8, W-M-8.5, 4.6, WHITE);
s.addText("Vì sao theo dõi max_abs?", { x: 8.75, y: 2.0, w: W-M-8.5-0.5, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: NAVY, margin: 0 });
s.addText([
  { text: "Biến dạng thường CỤC BỘ (một section). ", options: { breakLine: true, color: INK } },
  { text: "p95 toàn cloud bị pha loãng → có thể không bao giờ vượt ngưỡng dù section đó đã nguy hiểm.", options: { breakLine: true, color: INK } },
  { text: "", options: { breakLine: true, fontSize: 7 } },
  { text: "max_abs (đỉnh) bám đúng điểm xấu nhất → cảnh báo sớm.", options: { breakLine: true, color: TEAL_D, bold: true } },
  { text: "", options: { breakLine: true, fontSize: 7 } },
  { text: "Số đo THẬT (T5): max_abs = 44.5 mm, p95 = 20.4 mm, nhưng median ≈ 0 mm. ", options: { breakLine: true, color: INK } },
  { text: "Median toàn cloud không nhúc nhích dù đỉnh đã 44.5 mm — minh chứng vì sao không dùng median.", options: { color: MUTED, italic: true, fontSize: 11.5 } },
], { x: 8.75, y: 2.5, w: W-M-8.5-0.5, h: 3.7, fontFace: BF, fontSize: 13.5, lineSpacingMultiple: 1.12, margin: 0 });
pageNum(s,7);

// ============================================================ Slide 9 — Forecast
s = pres.addSlide(); bgLight(s);
header(s, "6.5 — Dự báo (trên số đo thật)", "Ngoại suy max_abs tới ngưỡng an toàn");
s.addChart(pres.charts.LINE, [
  { name: "Đo được (max_abs)", labels: ["T0","T1","T2","T3","T4","T5","T6"], values: [0, 6.3, 12.6, 19.9, 29.7, 44.5, null] },
  { name: "Ngoại suy", labels: ["T0","T1","T2","T3","T4","T5","T6"], values: [null,null,null,null,null,44.5, 59.4] },
  { name: "CAUTION 10mm", labels: ["T0","T1","T2","T3","T4","T5","T6"], values: [10,10,10,10,10,10,10] },
  { name: "CRITICAL 25mm", labels: ["T0","T1","T2","T3","T4","T5","T6"], values: [25,25,25,25,25,25,25] },
], {
  x: M, y: 1.8, w: 7.6, h: 4.6, lineSize: 3,
  chartColors: [NAVY, TEAL, CAUT, CRIT],
  lineDataSymbol: ["circle","none","none","none"],
  lineDash: ["solid","dash","sysDot","sysDot"],
  showLegend: true, legendPos: "b", legendColor: INK, legendFontSize: 10,
  catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
  valAxisTitle: "displacement (mm)", showValAxisTitle: true, valAxisTitleColor: MUTED, valAxisTitleFontSize: 11,
});
card(s, 8.5, 1.8, W-M-8.5, 4.6, NAVY);
s.addText("Forecast trả về (số THẬT)", { x: 8.75, y: 2.0, w: W-M-8.5-0.5, h: 0.4, fontFace: BF, fontSize: 13, bold:true, color: TEAL, charSpacing: 1, margin: 0 });
s.addText([
  { text: "rate = +14.94 mm/đơn vị", options: { bold:true, color: WHITE, breakLine:true } },
  { text: "tốc độ tăng tức thời tại T5.", options: { color: ICE, breakLine:true } },
  { text: "", options:{breakLine:true,fontSize:6} },
  { text: "R² = 1.00", options: { bold:true, color: WHITE, breakLine:true } },
  { text: "xu hướng rất khớp → đáng tin (R²<0.5 sẽ gắn cờ low_confidence).", options: { color: ICE, breakLine:true } },
  { text: "", options:{breakLine:true,fontSize:6} },
  { text: "Đã vượt CAUTION & CRITICAL tại T5", options: { bold:true, color: CAUT, breakLine:true } },
  { text: "ngoại suy T6 ≈ 59 mm nếu giữ tốc độ.", options: { color: ICE } },
], { x: 8.75, y: 2.5, w: W-M-8.5-0.5, h: 3.7, fontFace: BF, fontSize: 13, lineSpacingMultiple: 1.1, margin: 0 });
pageNum(s,9);

// ============================================================ Slide 10 — section warning thresholds + local gate
s = pres.addSlide(); bgLight(s);
header(s, "Phân loại cảnh báo", "Ngưỡng theo mặt cắt (so với T0)");
const tbl = [
  [
    { text: "Chỉ số", options: { fill:{color:NAVY}, color: WHITE, bold:true, fontFace:BF, fontSize:13 } },
    { text: "Ý nghĩa", options: { fill:{color:NAVY}, color: WHITE, bold:true, fontFace:BF, fontSize:13 } },
    { text: "CAUTION", options: { fill:{color:NAVY}, color: CAUT, bold:true, fontFace:BF, fontSize:13, align:"center" } },
    { text: "CRITICAL", options: { fill:{color:NAVY}, color: "FF8A95", bold:true, fontFace:BF, fontSize:13, align:"center" } },
  ],
  ["dW / dH / dR", "Thay đổi rộng / cao / bán kính vs T0", "≥ 10 mm", "≥ 25 mm"],
  ["dOval", "Thay đổi độ ô-van vs T0", "≥ 0.5 %", "≥ 1.0 %"],
  ["dEcc", "Thay đổi lệch tâm vs T0", "≥ 10 mm", "≥ 25 mm"],
  ["clearance", "Xâm phạm giới hạn tĩnh không", "—", "vi phạm = CRITICAL"],
];
s.addTable(tbl, {
  x: M, y: 1.8, w: 7.5, colW: [1.7, 3.1, 1.35, 1.35], rowH: [0.5,0.62,0.62,0.62,0.62],
  border: { pt: 0.5, color: "D8E0E8" }, align: "left", valign: "middle",
  fontFace: BF, fontSize: 12.5, color: INK,
  fill: { color: WHITE },
});
card(s, 8.55, 1.8, W-M-8.55, 4.3, WHITE);
s.addText("“Local gate” — chống báo tràn lan", { x: 8.8, y: 2.0, w: W-M-8.55-0.5, h: 0.45, fontFace: HF, fontSize: 15.5, bold: true, color: NAVY, margin: 0 });
s.addText([
  { text: "dOval, dEcc, đơn-scan: ", options:{bold:true,color:INK,breakLine:true} },
  { text: "chỉ báo khi vừa vượt ngưỡng VỪA là dị thường cục bộ (v ≥ trung vị + 3·MAD). Loại bỏ lệch hệ thống do registration sơn đỏ cả hầm.", options:{color:INK,breakLine:true} },
  { text: "", options:{breakLine:true,fontSize:7} },
  { text: "dW, dH, dR: ", options:{bold:true,color:INK,breakLine:true} },
  { text: "báo theo ngưỡng tuyệt đối (không local gate) — thay đổi kích thước thật là biến dạng thật, dù trải rộng.", options:{color:INK,breakLine:true} },
  { text: "", options:{breakLine:true,fontSize:7} },
  { text: "Cùng một bộ phân loại dùng chung cho 2D / ruler / 3D / dashboard → mọi view nhất quán.", options:{color:TEAL_D,italic:true} },
], { x: 8.8, y: 2.5, w: W-M-8.55-0.5, h: 3.5, fontFace: BF, fontSize: 12.5, lineSpacingMultiple: 1.1, margin: 0 });
pageNum(s,10);

// ============================================================ Slide 10 — real result example
s = pres.addSlide(); bgLight(s);
header(s, "Đọc kết quả — ví dụ thật", "Dataset complex_warning (80 mặt cắt)");
s.addChart(pres.charts.BAR, [
  { name: "Số mặt cắt", labels: ["OK","CAUTION","CRITICAL"], values: [33, 9, 38] },
], {
  x: M, y: 1.9, w: 6.4, h: 4.3, barDir: "col",
  chartColors: [OK, CAUT, CRIT], showLegend: false, showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 13, dataLabelFontBold: true,
  catAxisLabelColor: INK, catAxisLabelFontSize: 13, valAxisLabelColor: MUTED, valGridLine: { color: "E2E8F0", size: 0.5 },
});
// stat callouts
const stats = [
  ["92.0 mm", "crown_max đo được", "GT ≈ 90 mm — khớp", OK],
  ["100 %", "recall dải biến dạng", "17/17 section trong dải GT bị flag", TEAL_D],
  ["38", "mặt cắt CRITICAL", "khoanh đúng vùng hư hỏng cục bộ", CRIT],
];
stats.forEach((p,i)=>{
  const y = 1.9 + i*1.45;
  card(s, 7.4, y, W-M-7.4, 1.28);
  s.addText(p[0], { x: 7.65, y: y+0.12, w: 2.2, h: 0.7, fontFace: HF, fontSize: 30, bold: true, color: p[3], margin: 0 });
  s.addText(p[1], { x: 9.95, y: y+0.2, w: W-M-9.95-0.2, h: 0.4, fontFace: BF, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  s.addText(p[2], { x: 9.95, y: y+0.62, w: W-M-9.95-0.2, h: 0.5, fontFace: BF, fontSize: 11.5, color: MUTED, margin: 0 });
});
pageNum(s,11);

// ============================================================ Slide 11 — meaning & cautions
s = pres.addSlide(); bgLight(s);
header(s, "Ý nghĩa & lưu ý", "Đọc kết quả cho đúng");
const notes = [
  ["Dấu của chuyển vị", "Âm = vào trong (lún/hội tụ), dương = ra ngoài. Luôn đọc kèm chainage để biết VỊ TRÍ.", TEAL],
  ["LoD là bộ lọc", "Giá trị dưới LoD nằm trong nhiễu — đừng kết luận biến dạng từ chúng.", NAVY],
  ["Cảnh báo độ phủ", "quality_warning báo khi Tn quét thiếu (>50% không có lân cận) — số liệu khi đó không đáng tin.", CAUT],
  ["Registration giữ biến dạng", "Đăng ký căn theo phần ổn định; biến dạng cục bộ KHÔNG bị triệt tiêu (đã kiểm chứng).", TEAL],
  ["Cục bộ > toàn cục", "Theo dõi đỉnh max_abs và cảnh báo theo section, không dựa percentile toàn cloud.", NAVY],
  ["Forecast cần R²", "Chỉ tin dự báo ngưỡng khi R² ≥ 0.5 và đủ ≥ 3 epoch.", CAUT],
];
const ncw = (W-2*M-0.8)/3, nch = 2.0;
notes.forEach((p,i)=>{
  const x = M + (i%3)*(ncw+0.4), y = 1.9 + Math.floor(i/3)*(nch+0.3);
  card(s, x, y, ncw, nch);
  s.addShape(pres.shapes.OVAL, { x: x+0.25, y: y+0.25, w: 0.4, h: 0.4, fill: { color: p[2] } });
  s.addText(p[0], { x: x+0.8, y: y+0.22, w: ncw-1.0, h: 0.7, fontFace: HF, fontSize: 15, bold: true, color: NAVY, valign:"middle", margin: 0 });
  s.addText(p[1], { x: x+0.3, y: y+0.95, w: ncw-0.6, h: nch-1.1, fontFace: BF, fontSize: 12.5, color: INK, margin: 0 });
});
pageNum(s,12);

// ============================================================ Slide 12 — summary / checklist
s = pres.addSlide(); bgDark(s);
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.28, h: H, fill: { color: TEAL } });
s.addText("TÓM TẮT", { x: 0.9, y: 0.8, w: 8, h: 0.4, fontFace: BF, fontSize: 14, bold: true, color: TEAL, charSpacing: 3, margin: 0 });
s.addText("Step 6 trong một câu", { x: 0.9, y: 1.2, w: 11, h: 0.7, fontFace: HF, fontSize: 30, bold: true, color: WHITE, margin: 0 });
s.addText("So Tn với mốc T0 để đo chuyển vị bề mặt (M3C2 + LoD), dựng xu hướng & dự báo theo thời gian, rồi khoanh CAUTION/CRITICAL theo từng mặt cắt cục bộ.", { x: 0.9, y: 2.0, w: 11.6, h: 0.9, fontFace: BF, fontSize: 16, color: ICE, lineSpacingMultiple: 1.15, margin: 0 });
const chk = [
  "Làm sạch + đăng ký T0/Tn trước khi chạy 6.x",
  "6.3 M3C2: chỉ tin điểm vượt LoD; xem quality_warning",
  "6.2 theo dõi đỉnh max_abs (bắt defect cục bộ)",
  "6.5 forecast: cần ≥ 3 epoch và R² ≥ 0.5",
  "Cảnh báo gắn đúng chainage; mọi view dùng chung bộ phân loại",
];
chk.forEach((t,i)=>{
  const y = 3.25 + i*0.72;
  s.addShape(pres.shapes.OVAL, { x: 0.95, y: y+0.04, w: 0.34, h: 0.34, fill: { color: TEAL } });
  s.addText("✓", { x: 0.95, y: y+0.04, w: 0.34, h: 0.34, align:"center", valign:"middle", fontFace: BF, fontSize: 14, bold:true, color: NAVY, margin: 0 });
  s.addText(t, { x: 1.45, y: y, w: 11, h: 0.45, fontFace: BF, fontSize: 15, color: WHITE, valign:"middle", margin: 0 });
});

pres.writeFile({ fileName: "Step6_Bien_dang_T0_Tn.pptx" }).then(f => console.log("WROTE", f));

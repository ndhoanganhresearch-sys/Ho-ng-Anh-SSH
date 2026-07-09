const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625"
pres.author = "SSL Tunnel Analysis";
pres.title = "Mo phong LiDAR bang Raycasting";

// ---- palette ----
const NAVY = "0F2A43", NAVY2 = "0A2036";
const TEAL = "0E7C86", TEALL = "1AA0AB";
const AMBER = "F2A516";
const INK = "1E2A33", MUTE = "5C6B75";
const WHITE = "FFFFFF", PANEL = "F2F5F7";
const HF = "Georgia", BF = "Calibri";
const W = 10, H = 5.625;
const sh = () => ({ type: "outer", color: "0A2036", blur: 7, offset: 3, angle: 135, opacity: 0.18 });
const path = require("path");
const IMG = path.join(__dirname, "img");
const img = (f) => path.join(IMG, f);

function eyebrow(slide, txt, color, x, y) {
  slide.addText(txt.toUpperCase(), { x, y, w: 6, h: 0.3, margin: 0, fontFace: BF, fontSize: 11, bold: true, color, charSpacing: 3 });
}
function title(slide, txt, color = INK, y = 0.45) {
  slide.addText(txt, { x: 0.55, y, w: 8.9, h: 0.95, margin: 0, fontFace: HF, fontSize: 28, bold: true, color, align: "left", valign: "top" });
}

// ============ SLIDE 1 — TITLE ============
let s = pres.addSlide(); s.background = { color: NAVY };
// hero render framed on the right
s.addShape(pres.shapes.RECTANGLE, { x: 5.74, y: 1.4, w: 3.9, h: 2.26, fill: { color: WHITE }, shadow: sh() });
s.addImage({ path: img("tunnel_interior.png"), x: 5.82, y: 1.48, w: 3.74, h: 2.1 });
s.addText("Mô hình hầm tròn Ø8.5 m dựng trong Blender", { x: 5.74, y: 3.72, w: 3.9, h: 0.4, margin: 0, fontFace: BF, fontSize: 10.5, italic: true, color: "9DB3BD", align: "center" });
eyebrow(s, "Phương pháp kiểm chứng  •  Validation", AMBER, 0.6, 0.92);
s.addText("Mô phỏng LiDAR bằng Raycasting", { x: 0.6, y: 1.5, w: 5.0, h: 1.85, margin: 0, fontFace: HF, fontSize: 35, bold: true, color: WHITE, valign: "top" });
s.addText("Chứng minh độ chính xác đo biến dạng hầm — tới từng milimet.", { x: 0.62, y: 3.45, w: 4.95, h: 0.9, margin: 0, fontFace: BF, fontSize: 15.5, color: "CFE0E6" });
s.addText("Biến dạng biết trước → quét laser ảo → đo lại → đối chiếu.", { x: 0.62, y: 4.62, w: 5.0, h: 0.6, margin: 0, fontFace: BF, fontSize: 12.5, italic: true, color: AMBER });

// ============ SLIDE 2 — THE PROBLEM ============
s = pres.addSlide(); s.background = { color: WHITE };
eyebrow(s, "Vấn đề", TEAL, 0.55, 0.4);
title(s, "Dữ liệu quét thật không có “đáp án”", INK, 0.72);
s.addText([
  { text: "Khách hàng cần tin con số biến dạng mm là đúng. Nhưng:", options: { fontSize: 15, color: INK, breakLine: true, paraSpaceAfter: 10, bold: true } },
  { text: "Một đường hầm quét ngoài hiện trường không kèm theo giá trị biến dạng thật để chấm điểm.", options: { fontSize: 14, color: MUTE, bullet: true, breakLine: true, paraSpaceAfter: 7 } },
  { text: "Muốn kiểm chứng tool đo đúng 45 mm, phải có hầm thật đã lún đúng 45 mm — không thể / quá tốn kém.", options: { fontSize: 14, color: MUTE, bullet: true, breakLine: true, paraSpaceAfter: 7 } },
  { text: "Không có “sự thật nền” (ground truth) ⇒ không thể đo độ chính xác.", options: { fontSize: 14, color: MUTE, bullet: true } },
], { x: 0.55, y: 1.75, w: 5.4, h: 3.3, valign: "top" });
// right card: the unknown
s.addShape(pres.shapes.RECTANGLE, { x: 6.35, y: 1.75, w: 3.1, h: 3.0, fill: { color: NAVY }, shadow: sh() });
s.addImage({ path: img("tunnel_track.png"), x: 6.35, y: 1.75, w: 3.1, h: 3.0, sizing: { type: "cover", w: 3.1, h: 3.0 } });
s.addShape(pres.shapes.RECTANGLE, { x: 6.35, y: 1.75, w: 3.1, h: 3.0, fill: { color: NAVY, transparency: 30 } });
s.addText("?", { x: 6.35, y: 1.9, w: 3.1, h: 1.3, margin: 0, fontFace: HF, fontSize: 72, bold: true, color: AMBER, align: "center" });
s.addText("Bản quét trông “đẹp” — nhưng biến dạng thật = ? mm", { x: 6.5, y: 3.35, w: 2.8, h: 1.2, margin: 0, fontFace: BF, fontSize: 13, bold: true, color: WHITE, align: "center" });

// ============ SLIDE 3 — SOLUTION ============
s = pres.addSlide(); s.background = { color: WHITE };
eyebrow(s, "Giải pháp", TEAL, 0.55, 0.4);
title(s, "Máy quét laser ảo (raycasting)", INK, 0.72);
s.addText([
  { text: "Trong Blender, từ vị trí “máy quét ảo”, phần mềm bắn hàng trăm nghìn tia laser ảo. Mỗi tia chạm bề mặt hầm và trả về một điểm — y hệt máy quét laser (TLS) thật ngoài hiện trường.", options: { fontSize: 14.5, color: INK, breakLine: true, paraSpaceAfter: 12 } },
], { x: 0.55, y: 1.7, w: 5.2, h: 1.7, valign: "top" });
// analogy box
s.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: 3.35, w: 5.2, h: 1.55, fill: { color: PANEL }, shadow: sh() });
s.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: 3.35, w: 0.09, h: 1.55, fill: { color: AMBER } });
s.addText([
  { text: "Ví von:  crash-test bằng hình nộm có cảm biến", options: { fontSize: 13.5, bold: true, color: INK, breakLine: true, paraSpaceAfter: 5 } },
  { text: "Ta biết chính xác lực tác động lên hình nộm, nên kiểm chứng được cảm biến đo đúng. Hầm ảo của chúng tôi chính là “hình nộm” đó.", options: { fontSize: 12.5, color: MUTE } },
], { x: 0.78, y: 3.5, w: 4.85, h: 1.3, valign: "middle" });
// illustration: scanner + rays hitting an arch (right)
const cx = 6.05, cy = 3.6;
s.addShape(pres.shapes.OVAL, { x: cx - 0.1, y: cy - 0.1, w: 0.2, h: 0.2, fill: { color: AMBER } });
const arc = [[8.9, 1.5], [9.2, 2.1], [9.35, 2.8], [9.35, 3.5], [9.2, 4.2], [8.9, 4.8]];
arc.forEach((p) => s.addShape(pres.shapes.LINE, { x: cx, y: cy, w: p[0] - cx, h: p[1] - cy, line: { color: TEALL, width: 1, transparency: 45 } }));
// arch wall (dots)
arc.forEach((p) => s.addShape(pres.shapes.OVAL, { x: p[0] - 0.05, y: p[1] - 0.05, w: 0.1, h: 0.1, fill: { color: NAVY } }));
s.addText("máy quét ảo", { x: cx - 0.7, y: cy + 0.18, w: 1.4, h: 0.3, margin: 0, fontFace: BF, fontSize: 10, italic: true, color: MUTE, align: "center" });
s.addText("vỏ hầm", { x: 8.7, y: 4.95, w: 1.2, h: 0.3, margin: 0, fontFace: BF, fontSize: 10, italic: true, color: MUTE, align: "center" });

// ============ SLIDE 4 — 5-STEP WORKFLOW ============
s = pres.addSlide(); s.background = { color: WHITE };
eyebrow(s, "Quy trình", TEAL, 0.55, 0.4);
title(s, "Năm bước, có “sự thật nền” từ đầu", INK, 0.72);
const steps = [
  ["1", "Hầm ảo đúng tỷ lệ", "Dựng theo kích thước thật đo từ dữ liệu LiDAR (bore ~8.5 m)."],
  ["2", "Biến dạng biết trước", "Lún đỉnh, hội tụ vách, hư hỏng cục bộ theo T0→T5."],
  ["3", "Raycasting", "Quét laser ảo → tạo point cloud như scan thật."],
  ["4", "Chạy công cụ", "Phân tích biến dạng trên chính point cloud đó."],
  ["5", "Đối chiếu", "So kết quả với số biết trước → ra độ chính xác thật."],
];
const cw = 1.74, gap = 0.165, x0 = 0.55, cy0 = 1.75, chh = 3.0;
steps.forEach((st, i) => {
  const x = x0 + i * (cw + gap);
  s.addShape(pres.shapes.RECTANGLE, { x, y: cy0, w: cw, h: chh, fill: { color: NAVY }, shadow: sh() });
  s.addShape(pres.shapes.OVAL, { x: x + cw / 2 - 0.32, y: cy0 + 0.28, w: 0.64, h: 0.64, fill: { color: AMBER } });
  s.addText(st[0], { x: x + cw / 2 - 0.32, y: cy0 + 0.28, w: 0.64, h: 0.64, margin: 0, fontFace: HF, fontSize: 26, bold: true, color: NAVY, align: "center", valign: "middle" });
  s.addText(st[1], { x: x + 0.12, y: cy0 + 1.1, w: cw - 0.24, h: 0.7, margin: 0, fontFace: BF, fontSize: 13.5, bold: true, color: WHITE, align: "center", valign: "top" });
  s.addText(st[2], { x: x + 0.12, y: cy0 + 1.78, w: cw - 0.24, h: 1.05, margin: 0, fontFace: BF, fontSize: 10.5, color: "CFE0E6", align: "center", valign: "top" });
  if (i < steps.length - 1) s.addText("›", { x: x + cw - 0.04, y: cy0 + chh / 2 - 0.3, w: 0.3, h: 0.6, margin: 0, fontFace: HF, fontSize: 24, bold: true, color: TEAL, align: "center", valign: "middle" });
});

// ============ SLIDE 5 — WHY RAYCASTING (not noise) ============
s = pres.addSlide(); s.background = { color: WHITE };
eyebrow(s, "Vì sao không chỉ “thêm nhiễu”", TEAL, 0.55, 0.4);
title(s, "Raycasting tái tạo đúng vật lý của scan thật", INK, 0.72);
const feats = [
  ["Che khuất (occlusion)", "Vùng tối thật sau cáp, đèn, người — không bịa ra."],
  ["Mật độ theo cự ly", "Gần máy điểm dày, xa thưa dần — như scan thật."],
  ["Cường độ phản xạ", "Khác nhau theo vật liệu: bê tông / thép / target."],
  ["Nhiễu khoảng cách", "Sai số tăng theo cự ly: σ = 2 mm + 0.06 mm/m."],
];
const gw = 4.45, gh = 1.32, gx = [0.55, 5.0], gy = [1.75, 3.25];
feats.forEach((f, i) => {
  const x = gx[i % 2], y = gy[Math.floor(i / 2)];
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: gw, h: gh, fill: { color: PANEL }, shadow: sh() });
  s.addShape(pres.shapes.RECTANGLE, { x: x + 0.2, y: y + 0.28, w: 0.34, h: 0.34, fill: { color: TEAL } });
  s.addText(f[0], { x: x + 0.7, y: y + 0.2, w: gw - 0.9, h: 0.4, margin: 0, fontFace: BF, fontSize: 14, bold: true, color: INK, valign: "middle" });
  s.addText(f[1], { x: x + 0.7, y: y + 0.62, w: gw - 0.9, h: 0.6, margin: 0, fontFace: BF, fontSize: 12, color: MUTE, valign: "top" });
});
s.addText("Mesh hoàn hảo + nhiễu ngẫu nhiên = test lý tưởng hoá.   Raycasting = test giống thực tế.",
  { x: 0.55, y: 4.78, w: 8.9, h: 0.4, margin: 0, fontFace: BF, fontSize: 12.5, italic: true, color: TEAL, align: "center" });

// ============ SLIDE 6 — EVIDENCE / BENCHMARK ============
s = pres.addSlide(); s.background = { color: WHITE };
eyebrow(s, "Bằng chứng", TEAL, 0.55, 0.4);
title(s, "Đo lại đúng giá trị biết trước", INK, 0.72);
// big stat
s.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: 1.8, w: 3.0, h: 3.0, fill: { color: NAVY }, shadow: sh() });
s.addText("0.58", { x: 0.55, y: 2.05, w: 3.0, h: 1.0, margin: 0, fontFace: HF, fontSize: 60, bold: true, color: AMBER, align: "center" });
s.addText("mm sai số trung bình", { x: 0.55, y: 3.05, w: 3.0, h: 0.4, margin: 0, fontFace: BF, fontSize: 14, color: WHITE, align: "center" });
s.addText([
  { text: "Tối đa 2.45 mm", options: { fontSize: 13, color: "CFE0E6", breakLine: true, paraSpaceAfter: 4 } },
  { text: "6 mốc T0–T5 · 5 cặp liên tiếp", options: { fontSize: 12, color: "9DB3BD" } },
], { x: 0.7, y: 3.6, w: 2.7, h: 1.0, align: "center", valign: "top" });
// chart tool vs ground truth (T4-T5 increment)
s.addText("Tool vs giá trị biết trước (mm) — bước T4→T5", { x: 3.9, y: 1.7, w: 5.6, h: 0.35, margin: 0, fontFace: BF, fontSize: 12.5, bold: true, color: INK });
s.addChart(pres.charts.BAR, [
  { name: "Công cụ đo", labels: ["Lún đỉnh", "Hội tụ vách", "Hư hỏng cục bộ"], values: [15.0, 13.0, 13.59] },
  { name: "Biết trước", labels: ["Lún đỉnh", "Hội tụ vách", "Hư hỏng cục bộ"], values: [15.0, 13.0, 15.0] },
], {
  x: 3.85, y: 2.05, w: 5.75, h: 2.75, barDir: "col",
  chartColors: [TEAL, AMBER], chartArea: { fill: { color: "FFFFFF" } },
  catAxisLabelColor: MUTE, catAxisLabelFontSize: 11, valAxisLabelColor: MUTE, valAxisLabelFontSize: 10,
  valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
  showValue: true, dataLabelColor: INK, dataLabelFontSize: 9, dataLabelPosition: "outEnd",
  showLegend: true, legendPos: "b", legendColor: MUTE, legendFontSize: 11,
});

// ============ SLIDE 7 — ROADMAP ============
s = pres.addSlide(); s.background = { color: WHITE };
eyebrow(s, "Lộ trình", TEAL, 0.55, 0.4);
title(s, "Từ synthetic đến dữ liệu thật", INK, 0.72);
const stages = [
  ["Hiện tại", "Dữ liệu synthetic, giả định đã căn chỉnh. Tập trung kiểm chứng phần phân tích.", TEAL],
  ["Tiếp theo", "Mô phỏng đầy đủ môi trường LiDAR (nhiều trạm, sai lệch đặt máy) → kiểm chứng cả khâu căn chỉnh.", TEALL],
  ["Cuối cùng", "Đối chiếu trên dữ liệu quét thật của khách hàng.", AMBER],
];
const sw = 2.92, sgap = 0.12, sx0 = 0.55, sy0 = 1.85, shh = 2.7;
stages.forEach((st, i) => {
  const x = sx0 + i * (sw + sgap);
  s.addShape(pres.shapes.RECTANGLE, { x, y: sy0, w: sw, h: shh, fill: { color: PANEL }, shadow: sh() });
  s.addShape(pres.shapes.RECTANGLE, { x, y: sy0, w: sw, h: 0.62, fill: { color: st[2] } });
  s.addText(`Giai đoạn ${i + 1}`, { x: x + 0.2, y: sy0 + 0.12, w: sw - 0.4, h: 0.4, margin: 0, fontFace: BF, fontSize: 13, bold: true, color: i === 2 ? NAVY : WHITE, valign: "middle" });
  s.addText(st[0], { x: x + 0.2, y: sy0 + 0.78, w: sw - 0.4, h: 0.45, margin: 0, fontFace: HF, fontSize: 17, bold: true, color: INK });
  s.addText(st[1], { x: x + 0.2, y: sy0 + 1.3, w: sw - 0.4, h: 1.25, margin: 0, fontFace: BF, fontSize: 12.5, color: MUTE, valign: "top" });
  if (i < stages.length - 1) s.addText("→", { x: x + sw - 0.02, y: sy0 + shh / 2 - 0.3, w: 0.26, h: 0.6, margin: 0, fontFace: HF, fontSize: 22, bold: true, color: TEAL, align: "center", valign: "middle" });
});

// ============ SLIDE 8 — FAQ / CLOSING ============
s = pres.addSlide(); s.background = { color: NAVY };
eyebrow(s, "Khách hàng thường hỏi", AMBER, 0.6, 0.5);
s.addText("Hỏi & Đáp", { x: 0.55, y: 0.82, w: 8.9, h: 0.8, margin: 0, fontFace: HF, fontSize: 28, bold: true, color: WHITE });
const qa = [
  ["“Dữ liệu giả thì có ý nghĩa gì?”", "Giả nhưng vật lý đúng và biết đáp án — cách duy nhất chứng minh độ chính xác trước khi áp lên dữ liệu thật."],
  ["“Sao không dùng luôn hầm thật?”", "Hầm thật không có ground truth mm để chấm điểm; ta dùng nó ở bước cuối để xác nhận, không phải để đo độ chính xác."],
  ["“Khác gì digital twin?”", "Đây là digital twin có chủ đích để kiểm thử — biến dạng được cài đặt chính xác phục vụ validation."],
];
let qy = 1.85;
qa.forEach((q) => {
  s.addText(q[0], { x: 0.6, y: qy, w: 8.8, h: 0.4, margin: 0, fontFace: BF, fontSize: 15, bold: true, color: TEALL });
  s.addText(q[1], { x: 0.6, y: qy + 0.38, w: 8.8, h: 0.6, margin: 0, fontFace: BF, fontSize: 12.5, color: "CFE0E6", valign: "top" });
  qy += 1.12;
});
s.addText("Biến dạng biết trước → quét laser ảo → đo lại → đối chiếu.  Sai số ~0.6 mm.",
  { x: 0.6, y: 5.05, w: 8.8, h: 0.4, margin: 0, fontFace: BF, fontSize: 12.5, italic: true, color: AMBER });

const out = require("path").join(__dirname, "Raycasting_LiDAR_Validation_VI.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("WROTE", out));

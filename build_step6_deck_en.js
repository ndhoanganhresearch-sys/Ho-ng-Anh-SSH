// Step 6 explainer deck (English, T0 vs Tn focus) for SSL Tunnel Analysis.
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "SSL Tunnel Analysis";
pres.title = "Step 6 — T0 vs Tn Deformation Analysis";

const NAVY="0F2A43", NAVY2="163B5C", TEAL="14B8A6", TEAL_D="0E8C80", ICE="CFE8F2",
      INK="1E293B", MUTED="64748B", LIGHT="F4F7FA", WHITE="FFFFFF",
      OK="2EA86A", CAUT="E0A100", CRIT="D7263D";
const W=13.33, H=7.5, M=0.7, HF="Georgia", BF="Calibri";
const shadow=()=>({type:"outer",color:"000000",blur:7,offset:3,angle:135,opacity:0.18});
const bgLight=s=>s.background={color:LIGHT};
const bgDark=s=>s.background={color:NAVY};
function header(s,kicker,title){
  s.addText(kicker.toUpperCase(),{x:M,y:0.42,w:W-2*M,h:0.3,fontFace:BF,fontSize:12,bold:true,color:TEAL_D,charSpacing:2,margin:0});
  s.addText(title,{x:M,y:0.7,w:W-2*M,h:0.7,fontFace:HF,fontSize:28,bold:true,color:NAVY,margin:0});
}
const pageNum=(s,n)=>s.addText(String(n),{x:W-1.0,y:H-0.5,w:0.5,h:0.3,fontFace:BF,fontSize:10,color:MUTED,align:"right",margin:0});
function card(s,x,y,w,h,fill){
  s.addShape(pres.shapes.ROUNDED_RECTANGLE,{x,y,w,h,fill:{color:fill||WHITE},line:{color:"E2E8F0",width:1},rectRadius:0.08,shadow:shadow()});
}
const FIG_3D="step6_figures/m3c2_3d_en.png", FIG_MAP="step6_figures/m3c2_map_en.png";
const REAL={labels:["T0","T1","T2","T3","T4","T5"],max:[0,6.3,12.6,19.9,29.7,44.5],p95:[0,0.6,3.4,7.5,12.9,20.4],median:[0,0,0,0,0,0]};

// ===== Slide 1 — Title =====
let s=pres.addSlide(); bgDark(s);
s.addShape(pres.shapes.RECTANGLE,{x:0,y:0,w:0.28,h:H,fill:{color:TEAL}});
[3.2,2.5,1.8,1.1].forEach((r,i)=>s.addShape(pres.shapes.OVAL,{x:10.4-r,y:H/2-r*0.8,w:r*2,h:r*1.6,fill:{color:NAVY},line:{color:i===3?TEAL:NAVY2,width:i===3?3:2}}));
s.addText("SSL TUNNEL ANALYSIS",{x:0.9,y:1.5,w:8.5,h:0.4,fontFace:BF,fontSize:14,bold:true,color:TEAL,charSpacing:3,margin:0});
s.addText("Step 6 — T0 vs Tn\nDeformation Analysis",{x:0.9,y:2.0,w:9.5,h:1.7,fontFace:HF,fontSize:42,bold:true,color:WHITE,lineSpacingMultiple:1.05,margin:0});
s.addText("How it works and what the results mean",{x:0.9,y:3.85,w:9.5,h:0.5,fontFace:BF,fontSize:18,color:ICE,italic:true,margin:0});
s.addText([{text:"M3C2 displacement",options:{color:ICE}},{text:"   •   ",options:{color:TEAL}},{text:"deformation parameters",options:{color:ICE}},{text:"   •   ",options:{color:TEAL}},{text:"per-section warnings",options:{color:ICE}}],{x:0.9,y:5.3,w:11,h:0.4,fontFace:BF,fontSize:14,margin:0});

// ===== Slide 2 — Context =====
s=pres.addSlide(); bgLight(s);
header(s,"Context","Where Step 6 fits & what it solves");
const steps=["1 Load","2 Denoise","3 Register T0/Tn","4 Centerline","5 2D Sections","6 Deformation","7 Warnings"];
const sw=(W-2*M)/steps.length;
steps.forEach((t,i)=>{const on=i===5;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE,{x:M+i*sw,y:1.65,w:sw-0.12,h:0.7,fill:{color:on?TEAL:WHITE},line:{color:on?TEAL:"D8E0E8",width:1},rectRadius:0.06,shadow:on?shadow():undefined});
  s.addText(t,{x:M+i*sw,y:1.65,w:sw-0.12,h:0.7,align:"center",valign:"middle",fontFace:BF,fontSize:12,bold:on,color:on?WHITE:INK,margin:0});});
s.addText("Step 6 runs only after T0 + Tn are denoised and registered to a common frame.",{x:M,y:2.5,w:W-2*M,h:0.4,fontFace:BF,fontSize:13,italic:true,color:MUTED,margin:0});
const purpose=[
  ["Measure surface displacement","Compare the Tn cloud against the T0 baseline to see how far each point / section moved (mm)."],
  ["Quantify deformation","Crown settlement, lateral convergence, ovality and eccentricity for each cross-section."],
  ["Classify risk","Label every section OK / CAUTION / CRITICAL, tied to its local chainage."],
  ["(Extension) Trend & forecast","With 3+ epochs: deformation trend over time and time-to-threshold prediction."],
];
const cw=(W-2*M-0.6)/2, ch=1.5;
purpose.forEach((p,i)=>{const x=M+(i%2)*(cw+0.6), y=3.15+Math.floor(i/2)*(ch+0.35);
  card(s,x,y,cw,ch); s.addShape(pres.shapes.RECTANGLE,{x,y,w:0.1,h:ch,fill:{color:TEAL}});
  s.addText(p[0],{x:x+0.3,y:y+0.18,w:cw-0.5,h:0.4,fontFace:HF,fontSize:17,bold:true,color:NAVY,margin:0});
  s.addText(p[1],{x:x+0.3,y:y+0.62,w:cw-0.5,h:ch-0.7,fontFace:BF,fontSize:13.5,color:INK,margin:0});});
pageNum(s,2);

// ===== Slide 3 — T0 vs Tn + registration =====
s=pres.addSlide(); bgLight(s);
header(s,"Core concept","T0, Tn and why registration comes first");
const colw=(W-2*M-0.6)/2;
card(s,M,1.7,colw,2.0,NAVY);
s.addText("T0 — REFERENCE",{x:M+0.35,y:1.95,w:colw-0.7,h:0.4,fontFace:BF,fontSize:13,bold:true,color:TEAL,charSpacing:1.5,margin:0});
s.addText("Baseline scan, treated as the “clean / undeformed” tunnel. Every displacement is measured RELATIVE to T0.",{x:M+0.35,y:2.4,w:colw-0.7,h:1.1,fontFace:BF,fontSize:14.5,color:WHITE,margin:0});
card(s,M+colw+0.6,1.7,colw,2.0,TEAL);
s.addText("Tn — MONITORING",{x:M+colw+0.95,y:1.95,w:colw-0.7,h:0.4,fontFace:BF,fontSize:13,bold:true,color:NAVY,charSpacing:1.5,margin:0});
s.addText("A later scan (month / quarter). Compared to T0 to get settlement, convergence, ovality and eccentricity at time n.",{x:M+colw+0.95,y:2.4,w:colw-0.7,h:1.1,fontFace:BF,fontSize:14.5,color:NAVY,margin:0});
s.addShape(pres.shapes.ROUNDED_RECTANGLE,{x:M,y:3.95,w:W-2*M,h:2.35,fill:{color:WHITE},line:{color:"E2E8F0",width:1},rectRadius:0.06,shadow:shadow()});
s.addText("⚠  Registration must run BEFORE Step 6",{x:M+0.35,y:4.15,w:W-2*M-0.7,h:0.4,fontFace:HF,fontSize:18,bold:true,color:CRIT,margin:0});
s.addText([
  {text:"The two scans usually sit in different coordinate frames (different setups). Without bringing Tn back into T0’s frame, the difference is setup error — not deformation.",options:{breakLine:true,color:INK}},
  {text:"Key: registration aligns on the STABLE majority (trimmed-ICP / fixed targets) and must NOT absorb local deformation.",options:{breakLine:true,color:INK,bold:true}},
  {text:"Verified: register_epochs keeps 32.6 mm of a 60 mm ground-truth local settlement (not flattened to 0).",options:{color:TEAL_D,italic:true}},
],{x:M+0.35,y:4.6,w:W-2*M-0.7,h:1.6,fontFace:BF,fontSize:14,lineSpacingMultiple:1.15,paraSpaceAfter:6,margin:0});
pageNum(s,3);

// ===== Slide 4 — sub-steps =====
s=pres.addSlide(); bgLight(s);
header(s,"Workflow","The T0 → Tn pipeline inside Step 6");
const subs=[
  ["6.1","Load epochs","Load T0 (reference) and Tn (monitoring) point clouds."],
  ["6.3","M3C2 map","Signed surface displacement T0→Tn along normals + level-of-detection (LoD)."],
  ["5–6","Parameters","Per-section deformation parameters measured against the T0 reference sections."],
  ["7","Warnings","Classify each section OK / CAUTION / CRITICAL, shared by every view."],
];
const bw=(W-2*M-3*0.4)/4;
subs.forEach((p,i)=>{const x=M+i*(bw+0.4), y=1.85;
  card(s,x,y,bw,3.6);
  s.addShape(pres.shapes.OVAL,{x:x+bw/2-0.45,y:y+0.35,w:0.9,h:0.9,fill:{color:NAVY}});
  s.addText(p[0],{x:x+bw/2-0.45,y:y+0.35,w:0.9,h:0.9,align:"center",valign:"middle",fontFace:HF,fontSize:16,bold:true,color:TEAL,margin:0});
  s.addText(p[1],{x:x+0.2,y:y+1.45,w:bw-0.4,h:0.5,align:"center",fontFace:HF,fontSize:16,bold:true,color:NAVY,margin:0});
  s.addText(p[2],{x:x+0.22,y:y+2.0,w:bw-0.44,h:1.45,align:"center",fontFace:BF,fontSize:12.5,color:INK,margin:0});
  if(i<3) s.addText("→",{x:x+bw+0.04,y:y+1.4,w:0.34,h:0.6,align:"center",valign:"middle",fontFace:BF,fontSize:22,bold:true,color:TEAL,margin:0});});
s.addText("For a 2-scan T0/Tn pair this is the full workflow. Multiple epochs (T0…Tn) unlock the 6.2 trend chart and 6.5 forecast.",{x:M,y:5.75,w:W-2*M,h:0.5,fontFace:BF,fontSize:13,italic:true,color:MUTED,margin:0});
pageNum(s,4);

// ===== Slide 5 — M3C2 method =====
s=pres.addSlide(); bgLight(s);
header(s,"6.3 — How it computes","M3C2: signed displacement + level-of-detection");
const m3=[
  ["Surface normal","At each corepoint, estimate the local surface normal within normal_radius."],
  ["Signed distance","Project the T0→Tn change onto that normal inside cylinder cyl_radius → distance_mm (negative = inward)."],
  ["LoD (detection limit)","lod_mm = uncertainty from roughness / noise. Only |distance| > LoD counts as REAL deformation."],
  ["significant mask","Flags points above LoD → removes noise, prevents false alarms."],
];
m3.forEach((p,i)=>{const y=1.85+i*1.18;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE,{x:M,y,w:7.4,h:1.0,fill:{color:WHITE},line:{color:"E2E8F0",width:1},rectRadius:0.06});
  s.addShape(pres.shapes.OVAL,{x:M+0.2,y:y+0.22,w:0.56,h:0.56,fill:{color:TEAL}});
  s.addText(String(i+1),{x:M+0.2,y:y+0.22,w:0.56,h:0.56,align:"center",valign:"middle",fontFace:HF,fontSize:15,bold:true,color:WHITE,margin:0});
  s.addText(p[0],{x:M+0.95,y:y+0.12,w:6.3,h:0.35,fontFace:HF,fontSize:15,bold:true,color:NAVY,margin:0});
  s.addText(p[1],{x:M+0.95,y:y+0.46,w:6.3,h:0.5,fontFace:BF,fontSize:12.5,color:INK,margin:0});});
card(s,8.5,1.85,W-M-8.5,4.0,NAVY);
s.addText("What the numbers mean",{x:8.8,y:2.05,w:3.6,h:0.4,fontFace:BF,fontSize:13,bold:true,color:TEAL,charSpacing:1.5,margin:0});
s.addText([
  {text:"distance_mm < 0",options:{bold:true,color:WHITE,breakLine:true}},
  {text:"surface moved INWARD (settlement / convergence).",options:{color:ICE,breakLine:true}},
  {text:"",options:{breakLine:true,fontSize:6}},
  {text:"|distance| ≤ LoD",options:{bold:true,color:WHITE,breakLine:true}},
  {text:"within the noise band → no conclusion.",options:{color:ICE,breakLine:true}},
  {text:"",options:{breakLine:true,fontSize:6}},
  {text:"quality_warning",options:{bold:true,color:CAUT,breakLine:true}},
  {text:"fires if >50% of corepoints have no Tn neighbour (partial scan) → coverage alert.",options:{color:ICE}},
],{x:8.8,y:2.5,w:W-M-8.5-0.6,h:3.2,fontFace:BF,fontSize:13.5,lineSpacingMultiple:1.1,margin:0});
pageNum(s,5);

// ===== Slide 6 — Real output images =====
s=pres.addSlide(); bgLight(s);
header(s,"Real result — test data","M3C2 deformation map: T0 → Tn");
s.addImage({path:FIG_3D,x:0.6,y:1.75,w:7.0,h:3.62});
s.addText("3D cloud coloured by displacement (PyVista off-screen)",{x:0.6,y:5.42,w:7.0,h:0.35,align:"center",fontFace:BF,fontSize:11,italic:true,color:MUTED,margin:0});
s.addImage({path:FIG_MAP,x:7.85,y:1.75,w:5.0,h:1.98});
card(s,7.85,4.0,5.0,1.45);
s.addText([
  {text:"3 local damage zones (match ground truth):",options:{bold:true,color:NAVY,breakLine:true}},
  {text:"• Crown settlement @ chainage ~20 m (blue, crown)",options:{color:INK,breakLine:true}},
  {text:"• Sidewall convergence @ ~45 m",options:{color:INK,breakLine:true}},
  {text:"• Local damage @ ~65 m",options:{color:INK}},
],{x:8.1,y:4.15,w:4.6,h:1.2,fontFace:BF,fontSize:12,lineSpacingMultiple:1.12,margin:0});
s.addText("15,456 corepoints · method = M3C2 · real peak displacement −44.5 mm. Not a mock-up — computed from the dataset.",{x:0.6,y:5.85,w:W-1.2,h:0.5,fontFace:BF,fontSize:12,color:TEAL_D,italic:true,margin:0});
pageNum(s,6);

// ===== Slide 7 — 4 parameters =====
s=pres.addSlide(); bgLight(s);
header(s,"Main outputs","4 deformation parameters & warning thresholds");
const params=[
  ["Crown settlement","Lowering of the tunnel crown vs T0.","> 10 mm","> 25 mm"],
  ["Lateral convergence (dW)","Narrowing of the width between sidewalls.","> 10 mm","> 25 mm"],
  ["Ovality","Distortion away from the ideal circle.","> 0.5 %","> 1.0 %"],
  ["Eccentricity","Shift of the section centre vs the axis.","> 10 mm","> 25 mm"],
];
const pcw=(W-2*M-0.6)/2, pch=1.95;
params.forEach((p,i)=>{const x=M+(i%2)*(pcw+0.6), y=1.8+Math.floor(i/2)*(pch+0.35);
  card(s,x,y,pcw,pch); s.addShape(pres.shapes.RECTANGLE,{x,y,w:0.12,h:pch,fill:{color:TEAL}});
  s.addText(p[0],{x:x+0.35,y:y+0.2,w:pcw-0.6,h:0.4,fontFace:HF,fontSize:18,bold:true,color:NAVY,margin:0});
  s.addText(p[1],{x:x+0.35,y:y+0.66,w:pcw-0.6,h:0.55,fontFace:BF,fontSize:13,color:INK,margin:0});
  s.addShape(pres.shapes.ROUNDED_RECTANGLE,{x:x+0.35,y:y+1.33,w:1.9,h:0.46,fill:{color:"FBF1D2"},line:{color:CAUT,width:1},rectRadius:0.06});
  s.addText([{text:"CAUTION  ",options:{bold:true,color:CAUT}},{text:p[2],options:{color:INK}}],{x:x+0.35,y:y+1.33,w:1.9,h:0.46,align:"center",valign:"middle",fontFace:BF,fontSize:11.5,margin:0});
  s.addShape(pres.shapes.ROUNDED_RECTANGLE,{x:x+2.4,y:y+1.33,w:1.9,h:0.46,fill:{color:"F7D7DC"},line:{color:CRIT,width:1},rectRadius:0.06});
  s.addText([{text:"CRITICAL  ",options:{bold:true,color:CRIT}},{text:p[3],options:{color:INK}}],{x:x+2.4,y:y+1.33,w:1.9,h:0.46,align:"center",valign:"middle",fontFace:BF,fontSize:11.5,margin:0});});
pageNum(s,7);

// ===== Slide 8 — warning classification =====
s=pres.addSlide(); bgLight(s);
header(s,"Risk classification","Per-section thresholds (vs T0)");
const tbl=[
  [{text:"Metric",options:{fill:{color:NAVY},color:WHITE,bold:true,fontFace:BF,fontSize:13}},
   {text:"Meaning",options:{fill:{color:NAVY},color:WHITE,bold:true,fontFace:BF,fontSize:13}},
   {text:"CAUTION",options:{fill:{color:NAVY},color:CAUT,bold:true,fontFace:BF,fontSize:13,align:"center"}},
   {text:"CRITICAL",options:{fill:{color:NAVY},color:"FF8A95",bold:true,fontFace:BF,fontSize:13,align:"center"}}],
  ["dW / dH / dR","Width / height / radius change vs T0","≥ 10 mm","≥ 25 mm"],
  ["dOval","Ovality change vs T0","≥ 0.5 %","≥ 1.0 %"],
  ["dEcc","Eccentricity change vs T0","≥ 10 mm","≥ 25 mm"],
  ["clearance","Clearance-envelope intrusion","—","violation = CRITICAL"],
];
s.addTable(tbl,{x:M,y:1.8,w:7.5,colW:[1.7,3.1,1.35,1.35],rowH:[0.5,0.62,0.62,0.62,0.62],border:{pt:0.5,color:"D8E0E8"},align:"left",valign:"middle",fontFace:BF,fontSize:12.5,color:INK,fill:{color:WHITE}});
card(s,8.55,1.8,W-M-8.55,4.3,WHITE);
s.addText("“Local gate” — stops blanket alarms",{x:8.8,y:2.0,w:W-M-8.55-0.5,h:0.45,fontFace:HF,fontSize:15.5,bold:true,color:NAVY,margin:0});
s.addText([
  {text:"dOval, dEcc, single-scan: ",options:{bold:true,color:INK,breakLine:true}},
  {text:"flag only when the value exceeds the threshold AND is a local anomaly (v ≥ median + 3·MAD). Suppresses a uniform registration bias painting the whole tunnel red.",options:{color:INK,breakLine:true}},
  {text:"",options:{breakLine:true,fontSize:7}},
  {text:"dW, dH, dR: ",options:{bold:true,color:INK,breakLine:true}},
  {text:"absolute threshold (no local gate) — a real dimension change is real deformation, even across a wide band.",options:{color:INK,breakLine:true}},
  {text:"",options:{breakLine:true,fontSize:7}},
  {text:"One classifier shared by 2D / ruler / 3D / dashboard → every view stays consistent.",options:{color:TEAL_D,italic:true}},
],{x:8.8,y:2.5,w:W-M-8.55-0.5,h:3.5,fontFace:BF,fontSize:12.5,lineSpacingMultiple:1.1,margin:0});
pageNum(s,8);

// ===== Slide 9 — real example =====
s=pres.addSlide(); bgLight(s);
header(s,"Reading results — real example","complex_warning dataset (80 sections)");
s.addChart(pres.charts.BAR,[{name:"Sections",labels:["OK","CAUTION","CRITICAL"],values:[33,9,38]}],{
  x:M,y:1.9,w:6.4,h:4.3,barDir:"col",chartColors:[OK,CAUT,CRIT],showLegend:false,showValue:true,dataLabelPosition:"outEnd",dataLabelColor:INK,dataLabelFontSize:13,dataLabelFontBold:true,
  catAxisLabelColor:INK,catAxisLabelFontSize:13,valAxisLabelColor:MUTED,valGridLine:{color:"E2E8F0",size:0.5}});
const stats=[["92.0 mm","measured crown_max","GT ≈ 90 mm — matches",OK],["100 %","recall over deformation band","17/17 band sections flagged",TEAL_D],["38","CRITICAL sections","correctly localised to the damage zone",CRIT]];
stats.forEach((p,i)=>{const y=1.9+i*1.45; card(s,7.4,y,W-M-7.4,1.28);
  s.addText(p[0],{x:7.65,y:y+0.12,w:2.2,h:0.7,fontFace:HF,fontSize:30,bold:true,color:p[3],margin:0});
  s.addText(p[1],{x:9.95,y:y+0.2,w:W-M-9.95-0.2,h:0.4,fontFace:BF,fontSize:14,bold:true,color:NAVY,margin:0});
  s.addText(p[2],{x:9.95,y:y+0.62,w:W-M-9.95-0.2,h:0.5,fontFace:BF,fontSize:11.5,color:MUTED,margin:0});});
pageNum(s,9);

// ===== Slide 10 — extension: trend & forecast =====
s=pres.addSlide(); bgLight(s);
header(s,"Extension — multiple epochs (T0…Tn)","Trend chart & threshold forecast");
s.addChart(pres.charts.LINE,[
  {name:"max_abs_mm (peak)",labels:REAL.labels,values:REAL.max},
  {name:"p95_abs_mm (whole cloud)",labels:REAL.labels,values:REAL.p95},
  {name:"median_mm (whole cloud)",labels:REAL.labels,values:REAL.median},
],{x:M,y:1.85,w:7.4,h:4.4,lineSize:3,lineSmooth:true,chartColors:[CRIT,MUTED,"B6C2CE"],showLegend:true,legendPos:"b",legendColor:INK,legendFontSize:11,
  catAxisLabelColor:MUTED,valAxisLabelColor:MUTED,valGridLine:{color:"E2E8F0",size:0.5},catGridLine:{style:"none"},
  valAxisTitle:"displacement (mm)",showValAxisTitle:true,valAxisTitleColor:MUTED,valAxisTitleFontSize:11});
card(s,8.35,1.85,W-M-8.35,4.4,NAVY);
s.addText("Only with 3+ epochs",{x:8.6,y:2.05,w:W-M-8.35-0.5,h:0.4,fontFace:BF,fontSize:13,bold:true,color:TEAL,charSpacing:1,margin:0});
s.addText([
  {text:"6.2 Trend: ",options:{bold:true,color:WHITE,breakLine:true}},
  {text:"track the max_abs PEAK — median ≈ 0 even when the peak is 44.5 mm (local defect hidden by whole-cloud stats).",options:{color:ICE,breakLine:true}},
  {text:"",options:{breakLine:true,fontSize:7}},
  {text:"6.5 Forecast: ",options:{bold:true,color:WHITE,breakLine:true}},
  {text:"fit the trend → rate = +14.94 mm/unit, R² = 1.00, time-to-CAUTION/CRITICAL.",options:{color:ICE,breakLine:true}},
  {text:"",options:{breakLine:true,fontSize:7}},
  {text:"R² < 0.5 → low_confidence: do not trust the extrapolation.",options:{color:CAUT}},
],{x:8.6,y:2.5,w:W-M-8.35-0.5,h:3.6,fontFace:BF,fontSize:13,lineSpacingMultiple:1.1,margin:0});
pageNum(s,10);

// ===== Slide 11 — meaning & cautions =====
s=pres.addSlide(); bgLight(s);
header(s,"Meaning & cautions","Read the results correctly");
const notes=[
  ["Sign of displacement","Negative = inward (settlement/convergence), positive = outward. Always read with chainage for LOCATION.",TEAL],
  ["LoD is a filter","Values below LoD sit in the noise — don’t conclude deformation from them.",NAVY],
  ["Coverage warning","quality_warning fires when Tn is under-scanned (>50% with no neighbour) — results then unreliable.",CAUT],
  ["Registration preserves it","Alignment locks the stable part; local deformation is NOT cancelled (verified).",TEAL],
  ["Local beats global","Track the max_abs peak and warn per section, not whole-cloud percentiles.",NAVY],
  ["Forecast needs R²","Trust threshold forecasts only with R² ≥ 0.5 and ≥ 3 epochs.",CAUT],
];
const ncw=(W-2*M-0.8)/3, nch=2.0;
notes.forEach((p,i)=>{const x=M+(i%3)*(ncw+0.4), y=1.9+Math.floor(i/3)*(nch+0.3);
  card(s,x,y,ncw,nch); s.addShape(pres.shapes.OVAL,{x:x+0.25,y:y+0.25,w:0.4,h:0.4,fill:{color:p[2]}});
  s.addText(p[0],{x:x+0.8,y:y+0.22,w:ncw-1.0,h:0.7,fontFace:HF,fontSize:15,bold:true,color:NAVY,valign:"middle",margin:0});
  s.addText(p[1],{x:x+0.3,y:y+0.95,w:ncw-0.6,h:nch-1.1,fontFace:BF,fontSize:12.5,color:INK,margin:0});});
pageNum(s,11);

// ===== Slide 12 — summary =====
s=pres.addSlide(); bgDark(s);
s.addShape(pres.shapes.RECTANGLE,{x:0,y:0,w:0.28,h:H,fill:{color:TEAL}});
s.addText("SUMMARY",{x:0.9,y:0.8,w:8,h:0.4,fontFace:BF,fontSize:14,bold:true,color:TEAL,charSpacing:3,margin:0});
s.addText("Step 6 in one sentence",{x:0.9,y:1.2,w:11.5,h:0.7,fontFace:HF,fontSize:30,bold:true,color:WHITE,margin:0});
s.addText("Compare Tn against the T0 baseline to measure surface displacement (M3C2 + LoD), quantify per-section deformation, and flag CAUTION / CRITICAL tied to the local chainage.",{x:0.9,y:2.0,w:11.8,h:0.9,fontFace:BF,fontSize:16,color:ICE,lineSpacingMultiple:1.15,margin:0});
const chk=[
  "Denoise + register T0/Tn before running 6.x",
  "6.3 M3C2: trust only points above LoD; check quality_warning",
  "Read displacement with chainage; one classifier across all views",
  "Track the local peak (max_abs), not whole-cloud median / percentile",
  "Multi-epoch only: trend (6.2) + forecast (6.5) need ≥ 3 epochs & R² ≥ 0.5",
];
chk.forEach((t,i)=>{const y=3.25+i*0.72;
  s.addShape(pres.shapes.OVAL,{x:0.95,y:y+0.04,w:0.34,h:0.34,fill:{color:TEAL}});
  s.addText("✓",{x:0.95,y:y+0.04,w:0.34,h:0.34,align:"center",valign:"middle",fontFace:BF,fontSize:14,bold:true,color:NAVY,margin:0});
  s.addText(t,{x:1.45,y:y,w:11.4,h:0.45,fontFace:BF,fontSize:15,color:WHITE,valign:"middle",margin:0});});

pres.writeFile({fileName:"Step6_T0_Tn_Deformation_EN.pptx"}).then(f=>console.log("WROTE",f));

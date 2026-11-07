"""Draws the schematic diagrams used in the paper (PIL only). Usage: python experiments/diagrams.py"""
import math, os
from PIL import Image, ImageDraw, ImageFont
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"; SANSB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
F = lambda s, b=False: ImageFont.truetype(SANSB if b else SANS, s)
PAL = {"blue": ("#e3eefb", "#4a78b5"), "green": ("#e2f3e6", "#3d8f55"), "orange": ("#fde8dc", "#d0743a"), "yellow": ("#fff3d6", "#c99a2e"),
       "purple": ("#ece4f7", "#7a54b3"), "grey": ("#efefef", "#777777"), "red": ("#fbe3e3", "#c0392b")}

class Canvas:
    def __init__(self, w, h):
        self.im = Image.new("RGB", (w, h), "white"); self.d = ImageDraw.Draw(self.im)
    def box(self, x, y, w, h, title, lines=(), color="blue", ts=24, ls=20):
        fill, edge = PAL[color]; self.d.rounded_rectangle((x, y, x + w, y + h), 14, fill=fill, outline=edge, width=3)
        ty = y + 10
        if title:
            for t in title.split("\n"):
                self.d.text((x + w / 2 - self.d.textlength(t, font=F(ts, True)) / 2, ty), t, font=F(ts, True), fill="#1d2a1f"); ty += ts + 6
        for l in lines:
            self.d.text((x + w / 2 - self.d.textlength(l, font=F(ls)) / 2, ty + 2), l, font=F(ls), fill="#333"); ty += ls + 6
    def arrow(self, a, b, col="#222", w=4, label=None, lsize=18, off=(0, -22)):
        self.d.line((a, b), fill=col, width=w); ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for s in (0.45, -0.45): self.d.line((b, (b[0] - 20 * math.cos(ang + s), b[1] - 20 * math.sin(ang + s))), fill=col, width=w)
        if label:
            mx, my = (a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1]
            self.d.text((mx - self.d.textlength(label, font=F(lsize)) / 2, my), label, font=F(lsize), fill=col)
    def text(self, x, y, t, size=22, bold=False, col="#222"):
        self.d.text((x, y), t, font=F(size, bold), fill=col)
    def save(self, name): self.im.save(os.path.join(OUT, name))

# 1. System architecture
c = Canvas(1500, 900)
c.text(30, 15, "TYLCV-Guard system architecture", 30, True)
c.box(40, 80, 1420, 120, "Presentation layer: single-page web interface (static/index.html)", ["Gaps · Risk · Stacking · IPM · Surveillance · Field trials · Seed lots · Leaf scan · Evidence"], "blue")
c.box(40, 260, 1420, 90, "Service layer: JSON API (app/server.py, Python standard library)", ["GET/POST endpoints with input validation and size limits; no third-party web framework"], "green")
mods = [("risk.py", "climate & vector\nrisk index", "orange"), ("stacking.py", "Ty-locus\nstacking planner", "orange"), ("rotation.py", "MoA rotation\nplanner", "orange"),
        ("seqtools.py", "k-mer classify,\nrecombinant screen", "purple"), ("calibrate.py", "calibrated v2\nmodel (trials)", "yellow"), ("vision.py", "Leaf scan\n(Roboflow / local)", "red")]
x = 40
for n, d_, col in mods:
    c.box(x, 420, 220, 150, n, d_.split("\n"), col, 22, 19); x += 240
c.text(40, 385, "Domain modules", 22, True)
c.box(40, 650, 420, 120, "Storage", ["SQLite: trials, seed lots,", "reference sequences, submissions"], "grey")
c.box(500, 650, 420, 120, "Model file", ["data/model_v2.json (calibrated weights)"], "grey")
c.box(960, 650, 500, 120, "External / optional", ["Roboflow workflow API (HTTPS)", "dl/ package: local PyTorch checkpoint"], "grey")
for xx in (150, 390, 630, 870, 1110, 1350): c.arrow((xx, 200), (xx, 260), w=3) if False else None
c.arrow((750, 200), (750, 260)); c.arrow((750, 350), (750, 420), label="calls", off=(40, -18))
c.arrow((250, 570), (250, 650)); c.arrow((1130, 570), (1130, 650)); c.arrow((690, 570), (690, 650))
c.save("d_architecture.png")

# 2. Group-aware vs random split
c = Canvas(1500, 760)
c.text(30, 15, "Random split versus duplicate-aware group split", 30, True)
c.box(40, 90, 330, 150, "Image collection", ["photos of plants A, B, C ...", "each plant has several", "near-duplicate copies"], "blue")
c.box(520, 90, 360, 150, "Average hash (16×16)", ["images within 12 bits", "of each other are placed", "in one group"], "orange")
c.box(1030, 90, 430, 150, "Groups g1, g2, g3 ...", ["one group = one photograph", "and all its re-encodings"], "green")
c.arrow((370, 165), (520, 165)); c.arrow((880, 165), (1030, 165))
c.text(40, 300, "(a) Random split  →  copies of the same photo land on both sides  →  optimistic test score", 24, True, "#c0392b")
xs = [("A1", "#8fb8e8"), ("A2", "#8fb8e8"), ("B1", "#f2b58a"), ("A3", "#8fb8e8"), ("C1", "#9fd3a9"), ("B2", "#f2b58a"), ("C2", "#9fd3a9")]
for i, (t, col) in enumerate(xs):
    c.d.rounded_rectangle((60 + i * 90, 350, 130 + i * 90, 410), 8, fill=col, outline="#555", width=2); c.text(80 + i * 90, 368, t, 22)
c.box(720, 340, 330, 80, "Train", ["A1  B1  C1  A3  B2 (...)"], "grey", 22, 18); c.box(1090, 340, 360, 80, "Test", ["A2  C2 (copies of train photos)"], "red", 22, 18)
c.arrow((690, 380), (720, 380))
c.text(40, 480, "(b) Group-aware split  →  every group stays on one side  →  honest test score", 24, True, "#2a7d46")
for i, (t, col) in enumerate([("A1", "#8fb8e8"), ("A2", "#8fb8e8"), ("A3", "#8fb8e8"), ("B1", "#f2b58a"), ("B2", "#f2b58a"), ("C1", "#9fd3a9"), ("C2", "#9fd3a9")]):
    c.d.rounded_rectangle((60 + i * 90, 530, 130 + i * 90, 590), 8, fill=col, outline="#555", width=2); c.text(80 + i * 90, 548, t, 22)
c.box(720, 520, 330, 80, "Train", ["group A and group B"], "grey", 22, 18); c.box(1090, 520, 360, 80, "Test", ["group C only"], "green", 22, 18)
c.arrow((690, 560), (720, 560))
c.text(40, 650, "Validation data are split the same way; the threshold and temperature are fitted on validation data only.", 22)
c.save("d_group_split.png")

# 3. Classifier architecture
c = Canvas(1500, 640)
c.text(30, 15, "Transfer-learning classifier with calibrated output and Grad-CAM", 30, True)
c.box(30, 110, 200, 140, "Leaf photo", ["RGB, 224×224", "normalised"], "blue")
c.box(290, 110, 340, 140, "Backbone (pretrained)", ["MobileNetV3-Small /", "ResNet-18 / EfficientNet-B0"], "orange")
c.box(690, 110, 230, 140, "Global pooling", ["feature vector"], "green")
c.box(980, 110, 200, 140, "Linear head", ["2 logits z"], "yellow")
c.box(1240, 110, 230, 140, "z / T → softmax", ["temperature T", "(fitted on val)"], "purple")
for a, b in [(230, 290), (630, 690), (920, 980), (1180, 1240)]: c.arrow((a, 180), (b, 180))
c.box(1000, 330, 470, 120, "Decision", ["p(TYLCV) ≥ τ  →  flag for PCR confirmation", "τ chosen on validation data (max F1 or cost-based)"], "red", 22, 18)
c.arrow((1355, 250), (1355, 330))
c.box(290, 330, 630, 150, "Grad-CAM branch", ["gradients of the TYLCV score w.r.t. the last", "convolutional feature maps → heat-map overlay", "(shortcut check: is the model looking at the leaf?)"], "grey", 22, 18)
c.arrow((460, 250), (460, 330), "#777"); c.arrow((920, 400), (1000, 390), "#777")
c.text(30, 540, "Training: head only for 2 epochs, then full fine-tuning at 10× lower learning rate; class-weighted cross-entropy; early stopping on validation AUC.", 20)
c.save("d_classifier.png")

# 4. Risk index computation
c = Canvas(1500, 560)
c.text(30, 15, "Climate and vector risk index (v1) and its calibrated successor (v2)", 30, True)
fs = [("Temperature\nfactor f_T", "piecewise: 0 below 10 °C,", "1 at 22–30 °C, falls to 0.2 at 40 °C"), ("Vector factor f_V", "saturating in adults per leaf", "log(1+w) / log(6)"), ("Stage factor f_S", "seedling 1.0, vegetative 0.8,", "flowering 0.5, fruiting 0.3"), ("Protection (1−0.7p)", "p from Ty-locus planner", "exclusion nets × 0.25")]
x = 30
for t, a, b in fs:
    c.box(x, 90, 320, 170, t, [a, b], "orange", 22, 17); x += 350
c.box(300, 330, 420, 120, "Risk index = 100 · f_T · f_V · f_S · (1 − 0.7p)", ["category: Low <20, Moderate <40, High <65, Very high"], "yellow", 22, 18)
c.box(800, 330, 640, 120, "v2: logistic model fitted to logged trials", ["features: f_T, f_T², log(1+w), stage, each Ty locus, exclusion,", "recombinants, heat × Ty-1/3, recombinants × Ty-1/3, ≥2 mechanisms"], "purple", 22, 17)
for x0 in (190, 540, 890, 1240): c.arrow((x0, 260), (510 if x0 < 800 else 1100, 330), w=3)
c.arrow((720, 390), (800, 390))
c.save("d_risk_index.png")

# 5. Evaluation protocol
c = Canvas(1500, 700)
c.text(30, 15, "Evaluation protocol (maturity ladder levels L2–L5)", 30, True)
c.box(40, 90, 380, 140, "Training set", ["group-aware split", "class-weighted loss", "augmentation (small colour change)"], "blue", 22, 18)
c.box(40, 290, 380, 110, "Validation set", ["early stopping", "temperature scaling", "threshold τ"], "yellow", 22, 18)
c.box(520, 90, 420, 140, "Internal test set", ["no near-duplicate groups shared", "sensitivity, specificity, AUC, F1", "confusion matrix, 95% CIs"], "green", 22, 18)
c.box(520, 290, 420, 110, "External field set", ["other sites, phones, backgrounds"], "green", 22, 18)
c.box(520, 460, 420, 110, "Hard negatives", ["look-alike disorders: false-positive rate"], "green", 22, 18)
c.box(1030, 90, 430, 140, "Calibration", ["ECE and reliability diagram", "before / after temperature scaling"], "purple", 22, 18)
c.box(1030, 290, 430, 110, "Shortcut checks", ["background-only baseline", "Grad-CAM inspection"], "orange", 22, 18)
c.box(1030, 460, 430, 110, "Molecular subset (L5)", ["PCR / qPCR confirmed labels"], "red", 22, 18)
for y in (160, 345): c.arrow((420, y), (520, y))
c.arrow((420, 400), (520, 510)); c.arrow((940, 160), (1030, 160)); c.arrow((940, 345), (1030, 345)); c.arrow((940, 515), (1030, 515))
c.save("d_eval_protocol.png")

# 6. Leaf scan sequence
c = Canvas(1500, 640)
c.text(30, 15, "Leaf scan request flow", 30, True)
for i, (n, col) in enumerate([("Browser", "blue"), ("API server", "green"), ("vision.py", "orange"), ("Roboflow workflow\nor local model", "red")]):
    c.box(60 + i * 360, 80, 300, 90, n.split("\n")[0], n.split("\n")[1:] if "\n" in n else [], col, 24, 18)
    c.d.line((210 + i * 360, 170, 210 + i * 360, 600), fill="#999", width=3)
steps = [(0, 1, 230, "POST /api/diagnose (base64 image)"), (1, 2, 290, "validate JPEG/PNG, ≤ 5 MB"), (2, 3, 350, "temp file → run_workflow()"), (3, 2, 410, "detections / probability"), (2, 1, 470, "verdict + confidence + advice"), (1, 0, 530, "JSON response")]
for a, b, y, t in steps:
    c.arrow((210 + a * 360, y), (210 + b * 360, y), "#2f6f3e", 4); c.text(min(210 + a * 360, 210 + b * 360) + 20, y - 28, t, 19)
c.save("d_leafscan_flow.png")
print("ok", sorted(f for f in os.listdir(OUT) if f.startswith("d_")))

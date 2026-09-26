#!/usr/bin/env python3
"""
Agentic AI STLC Pipeline - Client Presentation PDF Generator.

Builds a non-technical, business-friendly PDF describing the project:
STLC process, tools used, run flow, agents and their work, with block
diagrams and flow charts drawn natively with ReportLab graphics.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, PageBreak, Flowable, NextPageTemplate,
)
from reportlab.pdfgen import canvas as pdfcanvas

# ----------------------------------------------------------------------------
# Palette
# ----------------------------------------------------------------------------
PRIMARY    = HexColor("#1B3A6B")   # deep corporate blue
PRIMARY_LT = HexColor("#2E5FA3")
ACCENT     = HexColor("#0E9594")   # teal accent
ACCENT_LT  = HexColor("#E3F4F4")
GOLD       = HexColor("#C9962E")
LIGHT      = HexColor("#F2F5FA")
BORDER     = HexColor("#C9D4E4")
TEXT       = HexColor("#222A35")
MUTED      = HexColor("#5A6675")
GREEN      = HexColor("#2E8B57")
GREEN_LT   = HexColor("#E4F3EA")
ORANGE     = HexColor("#D97706")
ORANGE_LT  = HexColor("#FCF0DD")
RED        = HexColor("#B3402E")
RED_LT     = HexColor("#F9E8E4")
PURPLE     = HexColor("#6B4FA1")
PURPLE_LT  = HexColor("#EFE9F7")
GREY_LT    = HexColor("#EEF1F5")

PAGE_W, PAGE_H = A4
MARGIN = 1.7 * cm

# ----------------------------------------------------------------------------
# Styles
# ----------------------------------------------------------------------------
def ps(name, **kw):
    base = dict(fontName="Helvetica", fontSize=10, leading=14.5, textColor=TEXT, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)

S_TITLE    = ps("title", fontName="Helvetica-Bold", fontSize=27, leading=33, textColor=white, alignment=TA_CENTER)
S_SUBTITLE = ps("subtitle", fontSize=12.5, leading=17, textColor=HexColor("#D6E2F2"), alignment=TA_CENTER)
S_H1       = ps("h1", fontName="Helvetica-Bold", fontSize=16.5, leading=21, textColor=PRIMARY, spaceBefore=4, spaceAfter=8)
S_H2       = ps("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16.5, textColor=PRIMARY_LT, spaceBefore=8, spaceAfter=5)
S_BODY     = ps("body", fontSize=9.8, leading=14.2)
S_BODY_B   = ps("bodyb", fontName="Helvetica-Bold", fontSize=9.8, leading=14.2)
S_SMALL    = ps("small", fontSize=8.6, leading=12, textColor=MUTED)
S_BULLET   = ps("bullet", fontSize=9.6, leading=13.8, leftIndent=10)
S_CAPTION  = ps("caption", fontSize=8.4, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceBefore=4)
S_TH       = ps("th", fontName="Helvetica-Bold", fontSize=8.8, leading=12, textColor=white)
S_TD       = ps("td", fontSize=8.8, leading=12.2)
S_TD_B     = ps("tdb", fontName="Helvetica-Bold", fontSize=8.8, leading=12.2)

# ----------------------------------------------------------------------------
# Drawing helpers
# ----------------------------------------------------------------------------
def rounded_box(c, x, y, w, h, fill, r=2.5*mm, stroke=None, sw=0.8):
    c.saveState()
    c.setLineWidth(sw)
    c.setFillColor(fill)
    if stroke is None:
        stroke = fill
    c.setStrokeColor(stroke)
    c.roundRect(x, y, w, h, r, stroke=1, fill=1)
    c.restoreState()

def para_lines(text, font, size, max_w):
    """Simple word-wrap -> list of lines."""
    words = text.split()
    lines, cur = [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if pdfcanvas.Canvas.stringWidth(pdfcanvas.Canvas(), t, font, size) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines

def draw_lines(c, lines, cx, top_y, font, size, color, leading):
    c.setFont(font, size)
    c.setFillColor(color)
    yy = top_y
    for ln in lines:
        c.drawCentredString(cx, yy, ln)
        yy -= leading
    return yy

def arrow(c, x1, y1, x2, y2, color=MUTED, lw=1.4, head=5):
    c.saveState()
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(lw)
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    ex, ey = x2 - head * 0.9 * math.cos(ang), y2 - head * 0.9 * math.sin(ang)
    c.line(x1, y1, ex, ey)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - head * math.cos(ang - 0.42), y2 - head * math.sin(ang - 0.42))
    p.lineTo(x2 - head * math.cos(ang + 0.42), y2 - head * math.sin(ang + 0.42))
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.restoreState()

# ----------------------------------------------------------------------------
# Custom flowable: pipeline flow chart (agent chain with swim-lane of outputs)
# ----------------------------------------------------------------------------
class PipelineFlowChart(Flowable):
    """7-box flow: input + 6 stages, with the Stage 4 -> Stage 3 healing loop."""

    STAGES = [
        ("INPUT", "Requirements &\nAcceptance Criteria", HexColor("#5A6675"), HexColor("#EEF1F5"), "Business hands over\nwhat to test"),
        ("STAGE 1", "Knowledge Retrieval\n(RAG Brain)", ACCENT, ACCENT_LT, "Reads past projects,\nfeatures & defects"),
        ("STAGE 2", "Agent 1\nTest Case Writer", PRIMARY, LIGHT, "Writes test cases\nfrom requirements"),
        ("STAGE 3", "Agent 2\nScript Builder", PRIMARY, LIGHT, "Builds scripts, re-applies\nhealed locators"),
        ("STAGE 4", "Agent 2b\nSelf-Healing Engine", PURPLE, PURPLE_LT, "Heals locators, feeds\nback to Stage 3"),
        ("STAGE 5", "Agent 3\nCI/CD Orchestrator", HexColor("#0E7490"), HexColor("#E0F2F7"), "Runs tests in the\ncloud, 3 browsers"),
        ("STAGE 6", "Agent 4\nFailure Investigator", ORANGE, ORANGE_LT, "Finds root cause,\nfiles Jira defects"),
    ]
    RESULTS = [
        "Test Plan Ready",
        "Test Cases Ready",
        "Test Scripts Ready",
        "Stable Scripts",
        "Healed Locators",
        "Test Results & Reports",
    ]

    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W = self.width
        H = self.height

        bw, bh = (W - 3 * 16) / 3.0, 62          # box size
        gapx, gapy = 16, 78
        top_y = H - bh - 28
        bot_y = top_y - bh - gapy
        third_y = bot_y - bh - 58
        end_y = third_y - 36

        boxes = []
        # Top row: stages 0,1,2  (input, rag, agent1)
        for i in range(3):
            boxes.append((8 + i * (bw + gapx), top_y))
        # Bottom row: stages 3,4,5 (agent2, agent2b, agent3)
        for i in range(3):
            boxes.append((8 + i * (bw + gapx), bot_y))
        # Third row: stage 6 (agent4), centred
        boxes.append(((W - bw) / 2, third_y))

        # --- draw all 7 boxes ---
        for idx in range(7):
            x, y = boxes[idx]
            tag, title, col, fill, note = self.STAGES[idx]
            self._box(c, x, y, bw, bh, tag, title, col, fill, note)

        # --- connectors top row ---
        for i in (0, 1):
            x1 = boxes[i][0] + bw + 2
            x2 = boxes[i + 1][0] - 2
            y = top_y + bh / 2
            arrow(c, x1, y, x2, y)
        # --- curve from stage2 (top right) down to stage3 (bottom left) ---
        sx = boxes[2][0] + bw / 2
        sy = top_y - 4
        ex = boxes[3][0] + bw / 2
        ey = bot_y + bh + 4
        c.saveState()
        c.setStrokeColor(MUTED); c.setLineWidth(1.4)
        p = c.beginPath()
        p.moveTo(sx, sy)
        p.curveTo(sx, sy - gapy / 2, ex, ey + gapy / 2, ex, ey)
        c.drawPath(p, stroke=1, fill=0)
        c.restoreState()
        arrow(c, ex, ey + 5, ex, ey)  # arrowhead at end of curve
        # --- connectors bottom row ---
        for i in (3, 4):
            x1 = boxes[i][0] + bw + 2
            x2 = boxes[i + 1][0] - 2
            y = bot_y + bh / 2
            arrow(c, x1, y, x2, y)

        # --- SELF-HEALING LOOP: Stage 4 feeds healed locators back to Stage 3 ---
        lsx = boxes[4][0] + 16           # leave from Stage 4 top-left area
        lex = boxes[3][0] + bw - 16      # enter Stage 3 top-right area
        lsy = bot_y + bh
        c.saveState()
        c.setStrokeColor(PURPLE); c.setLineWidth(1.3); c.setDash(4, 3)
        p = c.beginPath()
        p.moveTo(lsx, lsy)
        p.curveTo(lsx, lsy + 30, lex, lsy + 30, lex, lsy)
        c.drawPath(p, stroke=1, fill=0)
        c.restoreState()
        arrow(c, lex, lsy + 6, lex, lsy - 1, color=PURPLE, lw=1.3)
        c.setFillColor(PURPLE)
        c.setFont("Helvetica-Oblique", 6.9)
        c.drawCentredString((lsx + lex) / 2, lsy + 34, "healed locators fed back")

        # --- elbow connector: Stage 5 (bottom right) to Stage 6 (centred) ---
        s5, s6 = boxes[5], boxes[6]
        ey_y = bot_y + bh / 2
        mid_x = W - 5
        ty_y = third_y + bh / 2
        c.saveState()
        c.setStrokeColor(MUTED); c.setLineWidth(1.4)
        c.line(s5[0] + bw + 2, ey_y, mid_x, ey_y)
        c.line(mid_x, ey_y, mid_x, ty_y)
        c.restoreState()
        arrow(c, mid_x, ty_y, s6[0] + bw + 2, ty_y)

        # --- result chips under boxes 0..5 ---
        c.setFont("Helvetica-Bold", 7.6)
        for idx in range(6):
            x, y = boxes[idx]
            cx = x + bw / 2
            chip = self.RESULTS[idx]
            chip_y = y - 14
            c.setFillColor(white)
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.7)
            tw = c.stringWidth(chip, "Helvetica-Bold", 7.6) + 12
            c.roundRect(cx - tw / 2, chip_y - 4.6, tw, 13.4, 6, stroke=1, fill=1)
            c.setFillColor(PRIMARY)
            c.drawCentredString(cx, chip_y - 1, chip)

        # --- END box: Stage 6 output ---
        arrow(c, W / 2, third_y - 2, W / 2, end_y + 13, color=PRIMARY, lw=1.4)
        rounded_box(c, W / 2 - 82, end_y - 9, 164, 22, PRIMARY, r=4*mm)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8.2)
        c.drawCentredString(W / 2, end_y - 2.5, "JIRA DEFECTS + QUALITY REPORT")

    def _box(self, c, x, y, w, h, tag, title, col, fill, note):
        rounded_box(c, x, y, w, h, fill, stroke=col, sw=1.2)
        # tag pill
        c.setFillColor(col)
        c.roundRect(x + w / 2 - 26, y + h - 13, 52, 11, 5, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 6.8)
        c.drawCentredString(x + w / 2, y + h - 10, tag)
        # title
        c.setFillColor(col if col != HexColor("#5A6675") else TEXT)
        c.setFont("Helvetica-Bold", 9.2)
        ty = y + h - 27
        for ln in title.split("\n"):
            c.drawCentredString(x + w / 2, ty, ln)
            ty -= 11
        # note
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.9)
        ty -= 1.5
        for ln in note.split("\n"):
            c.drawCentredString(x + w / 2, ty, ln)
            ty -= 8.4

# ----------------------------------------------------------------------------
# Custom flowable: business flow (What the Business Sees)
# ----------------------------------------------------------------------------
class BusinessFlowChart(Flowable):
    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W, H = self.width, self.height
        steps = [
            ("1. Business\nDescribes", "What should the\nsoftware do?", GREY_LT, MUTED),
            ("2. AI Prepares\nthe Testing", "Studies history &\nwrites test plan", ACCENT_LT, ACCENT),
            ("3. AI Builds\nthe Tests", "Creates automated\ntest scripts", LIGHT, PRIMARY),
            ("4. Cloud Runs\nthe Tests", "Multiple browsers,\nevery change", HexColor("#E0F2F7"), HexColor("#0E7490")),
            ("5. AI Judges\nthe Results", "Real bug or just\na hiccup?", ORANGE_LT, ORANGE),
            ("6. Team Gets\nDefect Tickets", "Ready-to-work\nJira tickets", RED_LT, RED),
        ]
        n = len(steps)
        bw, gap = (W - (n - 1) * 14) / n, 14
        bh = 74
        y = H - bh - 12
        centers = []
        for i, (title, sub, fill, col) in enumerate(steps):
            x = 4 + i * (bw + gap)
            rounded_box(c, x, y, bw, bh, fill, stroke=col, sw=1.1)
            c.setFillColor(col)
            c.setFont("Helvetica-Bold", 8.2)
            ty = y + bh - 18
            for ln in title.split("\n"):
                c.drawCentredString(x + bw / 2, ty, ln)
                ty -= 10.5
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 6.8)
            ty -= 1.5
            for ln in sub.split("\n"):
                c.drawCentredString(x + bw / 2, ty, ln)
                ty -= 8.2
            centers.append((x, x + bw))
            if i < n - 1:
                arrow(c, x + bw + 1.5, y + bh / 2, x + bw + gap - 1.5, y + bh / 2, color=col)
        # loop-back note under step 6 to step 2
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 7.2)
        c.drawCentredString(W / 2, y - 16, "The cycle repeats automatically for every new software change - testing never sleeps.")

# ----------------------------------------------------------------------------
# Custom flowable: compact 3-step value chain (executive summary)
# ----------------------------------------------------------------------------
class ExecValueChain(Flowable):
    def __init__(self, width, height=84):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W, H = self.width, self.height
        gap = 42
        bw = (W - 2 * gap) / 3
        bh = 62
        y = (H - bh) / 2
        steps = [
            ("1. BUSINESS DESCRIBES", "What the software\nshould do", GREY_LT, MUTED, MUTED),
            ("2. AI QUALITY FACTORY", "Plans, writes, heals, runs\n& judges - automatically", PRIMARY, white, HexColor("#D6E2F2")),
            ("3. TEAM RECEIVES", "Reports, defect tickets\n& sign-off evidence", GREEN_LT, GREEN, MUTED),
        ]
        x = 0
        for i, (title, sub, fill, tcol, scol) in enumerate(steps):
            rounded_box(c, x, y, bw, bh, fill, stroke=tcol, sw=1.2)
            c.setFillColor(tcol)
            c.setFont("Helvetica-Bold", 8.6)
            c.drawCentredString(x + bw / 2, y + bh - 20, title)
            c.setFillColor(scol)
            c.setFont("Helvetica", 7.4)
            ty = y + bh - 36
            for ln in sub.split("\n"):
                c.drawCentredString(x + bw / 2, ty, ln)
                ty -= 9.5
            if i < 2:
                arrow(c, x + bw + 4, y + bh / 2, x + bw + gap - 4, y + bh / 2, color=ACCENT, lw=1.6)
            x += bw + gap

# ----------------------------------------------------------------------------
# Custom flowable: ROI paired bar chart (manual vs AI pipeline effort)
# ----------------------------------------------------------------------------
class ROIBarChart(Flowable):
    """Paired horizontal bars: manual effort today vs with the AI pipeline."""
    DATA = [
        ("Test planning & design", 12, 1.5),
        ("Test script writing", 40, 4),
        ("Script maintenance & fixing", 24, 3),
        ("Test execution & triage", 12, 1),
        ("Defect analysis & reporting", 4, 0.5),
    ]

    def __init__(self, width, height=196):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W, H = self.width, self.height
        label_w = 152
        axis_h = 18
        legend_h = 20
        bar_max = W - label_w - 52
        max_h = 40.0
        row_h = (H - axis_h - legend_h) / len(self.DATA)
        bar_h = 8.5
        bar_gap = 3.5

        before_col = HexColor("#8A97A8")
        after_col = ACCENT

        # vertical gridlines + axis labels
        for gh in range(0, 41, 10):
            gx = label_w + bar_max * gh / max_h
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.5)
            c.line(gx, axis_h, gx, H - legend_h + 2)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 6.6)
            c.drawCentredString(gx, axis_h - 11, f"{gh} h")

        # legend
        ly = H - 12
        c.setFillColor(before_col)
        c.rect(label_w, ly - 2, 14, 8, stroke=0, fill=1)
        c.setFillColor(TEXT)
        c.setFont("Helvetica", 7.6)
        t1 = "Traditional manual process"
        c.drawString(label_w + 18, ly, t1)
        lx2 = label_w + 18 + c.stringWidth(t1, "Helvetica", 7.6) + 26
        c.setFillColor(after_col)
        c.rect(lx2, ly - 2, 14, 8, stroke=0, fill=1)
        c.setFillColor(TEXT)
        c.drawString(lx2 + 18, ly, "With the Agentic AI pipeline")

        # paired bars
        for i, (label, before, after) in enumerate(self.DATA):
            row_top = H - legend_h - i * row_h
            y_before = row_top - bar_h - 6
            y_after = y_before - bar_gap - bar_h
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 7.8)
            c.drawRightString(label_w - 8, (y_before + y_after + bar_h) / 2 + 2, label)

            wb = bar_max * before / max_h
            wa = bar_max * after / max_h
            c.setFillColor(before_col)
            c.roundRect(label_w, y_before, wb, bar_h, 2, stroke=0, fill=1)
            c.setFillColor(TEXT)
            c.setFont("Helvetica", 7.2)
            c.drawString(label_w + wb + 5, y_before + 1.2, f"{before:g} h")
            c.setFillColor(after_col)
            c.roundRect(label_w, y_after, wa, bar_h, 2, stroke=0, fill=1)
            c.setFillColor(TEXT)
            c.drawString(label_w + wa + 5, y_after + 1.2, f"{after:g} h")

# ----------------------------------------------------------------------------
# Custom flowable: STLC wheel (6 phases with stage mapping)
# ----------------------------------------------------------------------------
class STLCWheel(Flowable):
    PHASES = [
        ("Requirement\nAnalysis", "Stage 1\nKnowledge Retrieval", ACCENT),
        ("Test\nPlanning", "Stage 2\nAgent 1 - Test Writer", PRIMARY),
        ("Test Case\nDevelopment", "Stage 2\nAgent 1 - Test Writer", PRIMARY),
        ("Test Environment\nSetup", "Stage 3-4\nAgents 2 & 2b", PURPLE),
        ("Test\nExecution", "Stage 5\nAgent 3 - CI/CD", HexColor("#0E7490")),
        ("Test Cycle\nClosure", "Stage 6\nAgent 4 - Defect Logger", ORANGE),
    ]

    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W, H = self.width, self.height
        R = min(W, H) / 2 - 46
        cx, cy = W / 2, H / 2
        n = 6
        import math
        # circle segments (wedges)
        for i in range(n):
            a0 = 90 + i * (360 / n)
            a1 = a0 + 360 / n
            phase, stage, col = self.PHASES[i]
            wedge_fill = col.clone()
            c.saveState()
            c.setFillColor(_tint(col, 0.82))
            c.setStrokeColor(col)
            c.setLineWidth(1.2)
            p = c.beginPath()
            p.moveTo(cx, cy)
            p.arcTo(cx - R, cy - R, cx + R, cy + R, startAng=360 - a1, extent=360 / n)
            p.lineTo(cx, cy)
            p.close()
            c.drawPath(p, fill=1, stroke=1)
            c.restoreState()
            # labels
            am = math.radians((a0 + a1) / 2)
            lx = cx + R * 0.62 * math.cos(am)
            ly = cy + R * 0.62 * math.sin(am)
            phase_lines = phase.split("\n")
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 8.0)
            yy = ly + 5
            for ln in phase_lines:
                c.drawCentredString(lx, yy, ln)
                yy -= 9.5
        # center
        c.setFillColor(PRIMARY)
        c.circle(cx, cy, 26, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7.6)
        c.drawCentredString(cx, cy + 3, "STLC")
        c.setFont("Helvetica", 6.4)
        c.drawCentredString(cx, cy - 6, "powered by")
        c.drawCentredString(cx, cy - 14, "6 AI stages")

        # outer labels: phase (in) -> stage (out)
        for i in range(n):
            am = math.radians(90 + i * (360 / n) + 30)
            phase, stage, col = self.PHASES[i]
            ox = cx + (R + 20) * math.cos(am)
            oy = cy + (R + 20) * math.sin(am)
            if ox > cx + 10:
                align = "l"; tx = ox
            elif ox < cx - 10:
                align = "r"; tx = ox
            else:
                align = "c"; tx = ox
            c.setFillColor(col)
            c.setFont("Helvetica-Bold", 7.4)
            yy = oy + 10
            for ln in phase.split("\n"):
                self._al(c, align, tx, yy, ln)
                yy -= 9
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 6.6)
            for ln in stage.split("\n"):
                self._al(c, align, tx, yy, ln)
                yy -= 8
            # connector tick
            c.setStrokeColor(col)
            c.setLineWidth(0.8)
            c.line(cx + (R + 2) * math.cos(am), cy + (R + 2) * math.sin(am),
                   cx + (R + 16) * math.cos(am), cy + (R + 16) * math.sin(am))
        # rotation hint
        arrow(c, cx + R * 0.9, cy + R * 0.55, cx + R * 0.55, cy + R * 0.95, color=BORDER, lw=1.0, head=4)

    @staticmethod
    def _al(c, align, x, y, text):
        if align == "l":
            c.drawString(x, y, text)
        elif align == "r":
            c.drawRightString(x, y, text)
        else:
            c.drawCentredString(x, y, text)

def _tint(col, f):
    """Lighten color toward white by factor f."""
    return HexColor(
        "#%02X%02X%02X" % tuple(int(v + (255 - v) * f) for v in (col.red * 255, col.green * 255, col.blue * 255))
    )

# ----------------------------------------------------------------------------
# Custom flowable: system block diagram (tools around pipeline)
# ----------------------------------------------------------------------------
class SystemBlockDiagram(Flowable):
    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W, H = self.width, self.height

        # center block
        cbw, cbh = W * 0.46, 74
        cx = (W - cbw) / 2
        cy = (H - cbh) / 2 + 6
        rounded_box(c, cx, cy, cbw, cbh, PRIMARY, r=3.5*mm)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(W / 2, cy + cbh - 22, "AGENTIC AI TESTING ENGINE")
        c.setFont("Helvetica", 7.6)
        c.drawCentredString(W / 2, cy + cbh - 36, "Orchestrated by LangGraph - a conveyor belt of 6 AI stages")
        c.setFont("Helvetica-Bold", 7.4)
        c.drawCentredString(W / 2, cy + cbh - 52, "NVIDIA Nemotron 3 Ultra (AI brain) + 4 specialised agents")
        c.setFont("Helvetica-Oblique", 7.0)
        c.setFillColor(HexColor("#D6E2F2"))
        c.drawCentredString(W / 2, cy + cbh - 63, "with a built-in self-healing loop: Stage 4 feeds fixed locators back to Stage 3")
        c.setFont("Helvetica", 6.8)
        c.drawCentredString(W / 2, cy + 9, "Automatic retries | Full trace of every decision | Mock mode for demos")

        def side_block(x, y, w, h, title, lines, col, fill):
            rounded_box(c, x, y, w, h, fill, stroke=col, sw=1.1)
            c.setFillColor(col)
            c.setFont("Helvetica-Bold", 7.8)
            yy = y + h - 12
            c.drawCentredString(x + w / 2, yy, title)
            yy -= 10
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 6.7)
            for ln in lines:
                c.drawCentredString(x + w / 2, yy, ln)
                yy -= 8.2

        bw, bh = W * 0.245, 58
        left_x = 6
        right_x = W - bw - 6
        top_y = H - bh - 8
        bot_y = 6

        side_block(left_x, top_y, bw, bh, "Business Input", ["Requirements &", "acceptance criteria,", "project documents"], HexColor("#5A6675"), GREY_LT)
        side_block(right_x, top_y, bw, bh, "Target Application", ["Web app being", "tested (e.g. online", "store checkout)"], GREEN, GREEN_LT)
        side_block(left_x, bot_y, bw, bh, "AI Brain", ["NVIDIA Nemotron", "3 Ultra 550B - the", "reasoning engine"], PURPLE, PURPLE_LT)
        side_block(right_x, bot_y, bw, bh, "Knowledge Library", ["ChromaDB memory -", "past test assets &", "defect lessons"], ACCENT, ACCENT_LT)

        top_mid_y = H - bh - 8
        bot_mid_y = 6
        mid_h = 58
        mid_w = W * 0.30
        # top middle: execution tools
        side_block((W - mid_w) / 2, top_mid_y, mid_w, mid_h, "Cloud Test Farm (GitHub Actions)", ["Runs the tests on Chromium,", "Firefox & Safari - every change"], HexColor("#0E7490"), HexColor("#E0F2F7"))
        # bottom middle: tracking
        side_block((W - mid_w) / 2, bot_mid_y, mid_w, mid_h, "Defect Tracker (Jira)", ["Ready-to-work bug tickets", "with steps & evidence"], ORANGE, ORANGE_LT)

        def conn(x1, y1, x2, y2, col=MUTED):
            arrow(c, x1, y1, x2, y2, color=col, lw=1.2, head=4.5)

        # left input -> engine
        conn(left_x + bw + 2, top_y + bh / 2, cx - 2, cy + cbh - 14)
        # knowledge -> engine (up)
        conn(left_x + bw + 2, bot_y + bh / 2, cx - 2, cy + 14)
        # engine -> target app
        conn(cx + cbw + 2, cy + cbh - 14, right_x - 2, top_y + bh / 2)
        # engine -> cloud farm (up)
        conn(W / 2 - 40, cy + cbh + 2, W / 2 - 40, top_mid_y - 2)
        # cloud farm -> engine (down, results) - single arrow down to Jira
        conn(W / 2 + 40, bot_mid_y + mid_h + 2, W / 2 + 40, cy - 2)
        # engine -> AI brain (down-left)
        conn(cx - 2, cy + 14, left_x + bw + 2, bot_y + bh / 2)

# ----------------------------------------------------------------------------
# Page decoration
# ----------------------------------------------------------------------------
def draw_cover_bg(cnv, doc):
    cnv.saveState()
    cnv.setFillColor(PRIMARY)
    cnv.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    # decorative circles
    cnv.setFillColor(HexColor("#24487E"))
    cnv.circle(PAGE_W - 2.2 * cm, PAGE_H - 3.0 * cm, 3.2 * cm, stroke=0, fill=1)
    cnv.setFillColor(HexColor("#2E5FA3"))
    cnv.circle(PAGE_W - 4.6 * cm, PAGE_H - 6.4 * cm, 1.7 * cm, stroke=0, fill=1)
    cnv.setFillColor(HexColor("#16305B"))
    cnv.circle(1.6 * cm, 3.4 * cm, 2.6 * cm, stroke=0, fill=1)
    cnv.setFillColor(HexColor("#1F4173"))
    cnv.circle(4.4 * cm, 1.4 * cm, 1.3 * cm, stroke=0, fill=1)
    # accent strip
    cnv.setFillColor(ACCENT)
    cnv.rect(0, PAGE_H - 0.55 * cm, PAGE_W, 0.55 * cm, stroke=0, fill=1)
    cnv.setFillColor(GOLD)
    cnv.rect(0, PAGE_H - 0.75 * cm, PAGE_W, 0.2 * cm, stroke=0, fill=1)
    cnv.restoreState()

def on_page(cnv, doc):
    if doc.page == 1:
        draw_cover_bg(cnv, doc)
        return
    cnv.saveState()
    # header
    cnv.setFillColor(PRIMARY)
    cnv.rect(0, PAGE_H - 1.05 * cm, PAGE_W, 1.05 * cm, stroke=0, fill=1)
    cnv.setFillColor(ACCENT)
    cnv.rect(0, PAGE_H - 1.16 * cm, PAGE_W, 0.11 * cm, stroke=0, fill=1)
    cnv.setFillColor(white)
    cnv.setFont("Helvetica-Bold", 8)
    cnv.drawString(MARGIN, PAGE_H - 0.72 * cm, "AGENTIC AI STLC PIPELINE")
    cnv.setFont("Helvetica", 7.6)
    cnv.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.72 * cm, "AI-Powered Software Testing - Client Overview")
    # footer
    cnv.setStrokeColor(BORDER)
    cnv.setLineWidth(0.6)
    cnv.line(MARGIN, 1.25 * cm, PAGE_W - MARGIN, 1.25 * cm)
    cnv.setFillColor(MUTED)
    cnv.setFont("Helvetica", 7.4)
    cnv.drawString(MARGIN, 0.9 * cm, "Agentic AI STLC Pipeline  |  Client Presentation")
    cnv.setFont("Helvetica-Bold", 7.8)
    cnv.setFillColor(PRIMARY)
    cnv.drawRightString(PAGE_W - MARGIN, 0.9 * cm, f"Page {doc.page - 1}")
    cnv.restoreState()

# ----------------------------------------------------------------------------
# Document build
# ----------------------------------------------------------------------------
class Doc(BaseDocTemplate):
    def __init__(self, path, **kw):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=1.8 * cm, bottomMargin=1.55 * cm, **kw)
        frame = Frame(MARGIN, 1.55 * cm, PAGE_W - 2 * MARGIN, PAGE_H - 3.35 * cm, id="main")
        self.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=on_page)])

def bullets(items, style=S_BULLET):
    return [Paragraph(f'<font color="#0E9594">&#9642;</font>&nbsp;&nbsp;{t}', style) for t in items]

def section_header(num, text, sub=None):
    rows = [[Paragraph(f"<b>{num}</b>", ps("n", fontName="Helvetica-Bold", fontSize=11.5, textColor=white, alignment=TA_CENTER)),
             Paragraph(f"<b>{text}</b>" + (f'<font size="9" color="#5A6675"> &nbsp;|&nbsp; {sub}</font>' if sub else ""), S_H1)]]
    t = Table(rows, colWidths=[1.05 * cm, None], rowHeights=[0.85 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("LINEBELOW", (0, 0), (-1, -1), 1.2, ACCENT),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t

def spaced(items, gap=3):
    out = []
    for i, it in enumerate(items):
        out.append(it)
        out.append(Spacer(1, gap))
    return out

# ============================================================================
# Story
# ============================================================================
def build_story():
    story = []

    # ---------------------------------------------------------------- COVER
    story.append(Spacer(1, 4.6 * cm))
    story.append(Paragraph("Agentic AI<br/>STLC Pipeline", S_TITLE))
    story.append(Spacer(1, 0.55 * cm))
    story.append(Paragraph("AI-Powered Software Testing - From Requirements to Verified Quality, End to End", S_SUBTITLE))
    story.append(Spacer(1, 1.1 * cm))
    chips = [
        "Test Planning", "Test Writing", "Self-Healing Scripts",
        "Cloud Execution", "Auto Defect Logging",
    ]
    chip_cells = []
    for ch in chips:
        chip_cells.append(Paragraph(
            f'<para align="center"><font color="white" size="8.6"><b>{ch}</b></font></para>',
            ps("chip")))
    chip_tbl = Table([chip_cells], colWidths=[(PAGE_W - 2 * MARGIN - 4 * 8) / 5] * 5, rowHeights=[0.72 * cm])
    chip_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), ACCENT),
        ("BACKGROUND", (1, 0), (1, 0), PRIMARY_LT),
        ("BACKGROUND", (2, 0), (2, 0), ACCENT),
        ("BACKGROUND", (3, 0), (3, 0), PRIMARY_LT),
        ("BACKGROUND", (4, 0), (4, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(chip_tbl)
    story.append(Spacer(1, 1.4 * cm))
    story.append(Paragraph(
        '<para align="center"><font color="#9FB4D4" size="10">A six-stage intelligent quality factory - planning, writing, healing, '
        'running and judging tests with minimal human effort</font></para>',
        S_SUBTITLE))
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        '<para align="center"><font color="#7E96BC" size="9">Client Presentation  |  2026</font></para>',
        S_SUBTITLE))

    story.append(PageBreak())

    # ---------------------------------------------------------------- EXEC SUMMARY
    story.append(section_header("ES", "Executive Summary", "One-Page Brief for Decision Makers"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "<b>The problem.</b> Software testing today is slow, manual and repetitive: every change to the software "
        "requires humans to re-plan, re-write and re-run tests before the business can safely release. Quality "
        "assurance has become the bottleneck of delivery.", S_BODY))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "<b>The solution we have built.</b> An AI-powered quality factory: a team of specialised AI agents that "
        "plans the tests, writes them, repairs them when screens change (feeding the fixes back into the scripts "
        "automatically), runs them in the cloud on every change, and investigates failures - raising ready-to-work "
        "Jira tickets only for genuine bugs. It runs on industry-standard tools (NVIDIA AI, GitHub, Jira) with full "
        "traceability of every decision.", S_BODY))
    story.append(Spacer(1, 7))
    story.append(ExecValueChain(PAGE_W - 2 * MARGIN))
    story.append(Spacer(1, 9))

    es_rows = [[Paragraph("Business question", S_TH), Paragraph("Answer", S_TH)]]
    es_qa = [
        ("What does it replace?", "Manual test planning, test writing, script maintenance, manual execution and manual failure analysis"),
        ("What does the team still do?", "Decide what to build, describe requirements, and approve releases - humans stay in charge"),
        ("When does it run?", "Automatically on every software change - testing becomes continuous, not a release-gate scramble"),
        ("What do we get?", "A prioritised test plan, runnable scripts, cross-browser reports and defect tickets after every run"),
        ("What is the return?", "~90% less testing effort per cycle (see ROI section) and quality issues caught before customers see them"),
        ("How risky is adoption?", "Low - pilots on one product area first; a built-in demo mode runs the whole flow with zero external calls"),
    ]
    for q, a in es_qa:
        es_rows.append([Paragraph(f"<b>{q}</b>", S_TD_B), Paragraph(a, S_TD)])
    es_tbl = Table(es_rows, colWidths=[4.9 * cm, None], repeatRows=1)
    es_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(es_tbl)
    story.append(Spacer(1, 9))
    story.append(Paragraph(
        '<para align="center"><font color="#1B3A6B" size="10.5"><b>Bottom line:</b></font> '
        '<font size="9.8" color="#222A35"> quality assurance stops being a manual bottleneck and becomes a '
        'continuously running, self-reporting service - at a fraction of today\'s effort.</font></para>', ps("bl", leading=14)))

    story.append(PageBreak())

    # ---------------------------------------------------------------- 1. OVERVIEW
    story.append(section_header("1", "What Has Been Built", "Project Overview"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "We have built an <b>AI-powered quality testing factory</b> for software. Today, every time a team changes "
        "software, human testers must plan, write, maintain and run tests, and then manually report problems. "
        "That cycle is slow, repetitive and error-prone.", S_BODY))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This project replaces that cycle with <b>a team of specialised AI agents</b> that work like a digital QA department: "
        "one plans the tests, one writes them, one repairs them when the software interface changes, one runs them in the cloud, "
        "and one investigates failures and raises ready-to-work defect tickets. Humans stay in charge - they decide what to test "
        "and approve what ships - but the heavy lifting is automated.", S_BODY))
    story.append(Spacer(1, 8))

    kpi = [
        ("6", "Automated stages\ncovers full STLC"),
        ("4+1", "AI agents\n(+1 knowledge brain)"),
        ("3", "Browsers tested\nChrome, Firefox, Safari"),
        ("24x7", "Testing on every\nsoftware change"),
        ("0", "Manual test writing\n& maintenance effort"),
    ]
    kpi_cells = []
    for num, lab in kpi:
        kpi_cells.append(Paragraph(
            f'<para align="center"><font color="#1B3A6B" size="17"><b>{num}</b></font><br/>'
            f'<font color="#5A6675" size="7.4">{lab.replace(chr(10), "<br/>")}</font></para>', ps("kpi")))
    kpi_tbl = Table([kpi_cells], colWidths=[(PAGE_W - 2 * MARGIN) / 5] * 5, rowHeights=[1.55 * cm])
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.6, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 10))
    story.append(Paragraph("Business benefits at a glance", S_H2))
    story.extend(spaced(bullets([
        "<b>Faster releases</b> - testing that took days now runs in minutes, on every change.",
        "<b>Lower cost</b> - less repetitive manual test writing and maintenance.",
        "<b>Fewer escaped bugs</b> - consistent, prioritised coverage with automatic defect reporting.",
        "<b>Lower flakiness</b> - self-healing scripts keep tests stable when the UI changes.",
        "<b>Full transparency</b> - every decision is traced; reports and tickets are generated automatically.",
    ])))

    story.append(PageBreak())

    # ---------------------------------------------------------------- 2. STLC
    story.append(section_header("2", "The STLC Process - and How AI Runs It", "Software Testing Life Cycle"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The <b>Software Testing Life Cycle (STLC)</b> is the industry-standard sequence every quality team follows: "
        "understand requirements, plan the testing, design the tests, prepare the environment, execute, and close the cycle "
        "with lessons learned. Each AI stage in our pipeline maps to one of these classic phases - the process is familiar, "
        "the execution is automated.", S_BODY))
    story.append(Spacer(1, 4))
    story.append(STLCWheel(PAGE_W - 2 * MARGIN, 10.6 * cm))
    story.append(Paragraph("Classic STLC phases (inner ring) mapped to the AI stages that now perform them (outer ring).", S_CAPTION))
    story.append(Spacer(1, 8))

    stlc_rows = [[Paragraph("STLC Phase", S_TH), Paragraph("What humans do today", S_TH), Paragraph("What our AI stage does", S_TH), Paragraph("AI Stage", S_TH)]]
    stlc_data = [
        ("Requirement Analysis", "Read documents, ask questions, extract what to test", "Knowledge Retrieval reads requirements plus a memory of past projects, features and defects", "Stage 1 - RAG"),
        ("Test Planning & Case Design", "Write test cases and prioritise by risk", "Agent 1 writes structured test cases with priorities, steps and expected results", "Stage 2 - Agent 1"),
        ("Environment & Test Preparation", "Build automation scripts, fix broken locators", "Agent 2 writes runnable scripts; Agent 2b keeps them stable via self-healing", "Stages 3-4 - Agents 2 & 2b"),
        ("Test Execution", "Run suites, triage results, re-run flakes", "Agent 3 dispatches the cloud test run, monitors it, retries flaky tests, collects reports", "Stage 5 - Agent 3"),
        ("Defect Logging & Cycle Closure", "Analyse failures, log bugs, report status", "Agent 4 finds the root cause and files a Jira ticket only for genuine product bugs", "Stage 6 - Agent 4"),
    ]
    for a, b, cc, d in stlc_data:
        stlc_rows.append([
            Paragraph(f"<b>{a}</b>", S_TD_B), Paragraph(b, S_TD), Paragraph(cc, S_TD),
            Paragraph(f'<font color="#1B3A6B"><b>{d}</b></font>', S_TD),
        ])
    stlc_tbl = Table(stlc_rows, colWidths=[3.4 * cm, 4.6 * cm, 6.2 * cm, 2.7 * cm], repeatRows=1)
    stlc_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(stlc_tbl)

    story.append(PageBreak())

    # ---------------------------------------------------------------- 3. ARCHITECTURE
    story.append(section_header("3", "System Overview - How the Pieces Fit", "Architecture Block Diagram"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Think of the engine as a factory floor: business input and a knowledge library feed an AI engine, which drives a cloud "
        "test farm against the real application, and pushes verified problems to the defect tracker.", S_BODY))
    story.append(Spacer(1, 4))
    story.append(SystemBlockDiagram(PAGE_W - 2 * MARGIN, 11.2 * cm))
    story.append(Paragraph("Surrounding tools are standard enterprise platforms - nothing exotic for IT to adopt.", S_CAPTION))

    story.append(PageBreak())

    # ---------------------------------------------------------------- 4. TOOLS
    story.append(section_header("4", "Tools & Technologies Used", "The Toolbox"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Every tool below is an industry-standard, enterprise-ready platform. The AI brain is NVIDIA's flagship reasoning model; "
        "everything else is the same toolchain quality teams already trust.", S_BODY))
    story.append(Spacer(1, 8))

    tools_rows = [[Paragraph("Tool", S_TH), Paragraph("Role in plain language", S_TH), Paragraph("Why it matters", S_TH)]]
    tools = [
        ("NVIDIA Nemotron 3 Ultra 550B", "The AI brain - a large language model that reads requirements and writes test plans, scripts, fixes and verdicts", "Human-quality reasoning at machine speed", PURPLE, PURPLE_LT),
        ("LangGraph (Orchestrator)", "The conveyor belt - passes work from one AI agent to the next, in order, with automatic retries", "Reliable, unbreakable flow with full traceability", PRIMARY, LIGHT),
        ("ChromaDB + Sentence Transformers", "The memory - stores past requirements, tests and defects; retrieves the most relevant lessons for each new run (RAG)", "Every new test benefits from everything learned before", ACCENT, ACCENT_LT),
        ("Playwright (TypeScript)", "The robot tester - drives a real browser like a human: clicks, types and verifies, in Chrome, Firefox and Safari", "Cross-browser confidence on every change", HexColor("#0E7490"), HexColor("#E0F2F7")),
        ("Robot Framework", "An alternative, keyword-based robot tester favoured by business analysts", "Readable tests even non-coders can follow", HexColor("#0E7490"), HexColor("#E0F2F7")),
        ("GitHub Actions (Cloud CI/CD)", "The test farm - runs the tests automatically in the cloud on every change, in parallel", "No lab maintenance; results in minutes", GREEN, GREEN_LT),
        ("Jira Cloud", "The defect tracker - receives ready-to-work bug tickets with steps, evidence and severity", "Developers get actionable tickets, not raw logs", ORANGE, ORANGE_LT),
        ("LangSmith", "The flight recorder - traces every AI decision for auditing and improvement", "Full transparency of what the AI did and why", HexColor("#6B4FA1"), PURPLE_LT),
    ]
    for name, role, why, col, fill in tools:
        hexv = "#%02X%02X%02X" % (int(col.red * 255), int(col.green * 255), int(col.blue * 255))
        tools_rows.append([
            Paragraph(f'<font color="{hexv}"><b>{name}</b></font>', S_TD_B),
            Paragraph(role, S_TD),
            Paragraph(why, S_TD),
        ])
    tools_tbl = Table(tools_rows, colWidths=[4.6 * cm, 8.1 * cm, 4.2 * cm], repeatRows=1)
    tools_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tools_tbl)

    story.append(PageBreak())

    # ---------------------------------------------------------------- 5. AGENTS
    story.append(section_header("5", "The AI Agents and Their Work", "The Digital QA Team"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Each agent is a specialist, exactly like roles in a human QA department. They hand work to each other down an assembly line.", S_BODY))
    story.append(Spacer(1, 8))

    agents = [
        ("Agent 1 - Test Case Writer", "The Planner",
         "Reads the business requirements and the knowledge library, then writes a complete, prioritised test plan.",
         [("Input:", "Requirements, acceptance criteria, past-project lessons"),
          ("Work:", "Designs positive, negative and edge-case scenarios; ranks them Critical to Low; marks automation feasibility"),
          ("Output:", "A structured test suite - the test plan - ready for automation")],
         PRIMARY, LIGHT),
        ("Agent 2 - Script Builder", "The Automator",
         "Turns the test plan into real, runnable automated test scripts - no human coding.",
         [("Input:", "The test plan plus knowledge of the application's screens (and healed locators on loop passes)"),
          ("Work:", "Writes Playwright (TypeScript) and Robot Framework scripts following the Page Object Model with stable locators; on loop passes it updates the scripts with the healed locators and re-emits them"),
          ("Output:", "Working test scripts, saved and version-controlled in the repository")],
         PRIMARY_LT, LIGHT),
        ("Agent 2b - Self-Healing Engine", "The Mechanic",
         "When a test breaks because a screen changed, this agent repairs the test and sends it back for a rebuild.",
         [("Input:", "The broken locator plus a snapshot of the current screen"),
          ("Work:", "Consults the healing service for candidate locators, ranks strategies (data-testid, role, label, text) and scores confidence; then feeds the healed locators back to Agent 2"),
          ("Output:", "Healed locators applied to the scripts - tests fix themselves instead of failing for days")],
         PURPLE, PURPLE_LT),
        ("Agent 3 - CI/CD Orchestrator", "The Runner",
         "Kicks off the test execution in the cloud and watches it through to completion.",
         [("Input:", "The test scripts and the target environment"),
          ("Work:", "Dispatches the GitHub Actions run, monitors progress, retries flaky tests, collects reports and artifacts"),
          ("Output:", "Pass/fail results across Chrome, Firefox and Safari with full reports")],
         HexColor("#0E7490"), HexColor("#E0F2F7")),
        ("Agent 4 - Failure Investigator", "The Detective",
         "Separates real product bugs from noise and raises tickets only where they matter.",
         [("Input:", "Failure logs, screenshots, browser traces and history"),
          ("Work:", "Classifies each failure: Product Bug / Script Issue / Environment / Flaky / Infrastructure; writes root-cause analysis"),
          ("Output:", "A ready-to-work Jira defect with steps, severity and evidence - only for genuine bugs")],
         ORANGE, ORANGE_LT),
    ]
    for name, role, one_liner, rows, col, fill in agents:
        hexv = "#%02X%02X%02X" % (int(col.red * 255), int(col.green * 255), int(col.blue * 255))
        head_l = Paragraph(f'<font color="white" size="10.2"><b>{name}</b></font><br/>'
                           f'<font color="#D6E2F2" size="8.2"><i>{role}</i></font>', ps("ah", leading=12.5))
        head_r = Paragraph(f'<para align="center"><font color="white" size="8.6">{one_liner}</font></para>', ps("ahr", leading=11))
        t = Table([[head_l, head_r]], colWidths=[6.4 * cm, None])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), col),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (0, 0), 10),
            ("LINEBELOW", (0, 0), (-1, -1), 2, GOLD),
        ]))
        story.append(t)
        body_rows = []
        for lbl, txt in rows:
            body_rows.append([Paragraph(f"<b>{lbl}</b>", S_TD_B), Paragraph(txt, S_TD)])
        bt = Table(body_rows, colWidths=[1.7 * cm, None])
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), fill),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (0, 0), 10),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, BORDER),
        ]))
        story.append(bt)
        story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ---------------------------------------------------------------- 6. RUN FLOW
    story.append(section_header("6", "How a Test Run Flows", "Run Flow Chart"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "One run of the pipeline, from business input to filed defects. Each box hands its output to the next. When the "
        "Self-Healing Engine repairs broken locators, they are fed back to the Script Builder, which updates the scripts "
        "before the suite runs in the cloud.", S_BODY))
    story.append(Spacer(1, 4))
    story.append(PipelineFlowChart(PAGE_W - 2 * MARGIN, 14.6 * cm))
    story.append(Paragraph("The full 6-stage run flow with the artefact each stage produces. Stage 4 feeds healed locators back to Stage 3 for re-generation (self-healing loop, capped at 3 rounds).", S_CAPTION))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Built-in reliability", S_H2))
    story.extend(spaced(bullets([
        "<b>Self-healing loop:</b> Stage 4 feeds healed locators back to Stage 3, which updates the scripts automatically - the loop is capped at 3 rounds to guarantee completion.",
        "<b>Automatic retries:</b> every stage retries failed attempts with growing pauses (1s, 2s, 4s...) - up to 3 times.",
        "<b>Safety valve:</b> if a stage cannot recover, the run stops cleanly with a clear reason - no silent failures.",
        "<b>Checkpointing:</b> each run can be resumed and audited stage by stage.",
        "<b>Mock mode:</b> the whole flow can be demonstrated offline, with zero external calls - perfect for stakeholder demos.",
    ])))

    story.append(PageBreak())

    # ---------------------------------------------------------------- 7. BUSINESS FLOW
    story.append(section_header("7", "What the Business Experiences", "Business Flow Chart"))
    story.append(Spacer(1, 6))
    story.append(Paragraph("All the technology disappears into six simple business steps:", S_BODY))
    story.append(Spacer(1, 4))
    story.append(BusinessFlowChart(PAGE_W - 2 * MARGIN, 4.6 * cm))
    story.append(Paragraph("The business conversation starts at step 1 and ends at step 6 - everything in between is automated.", S_CAPTION))
    story.append(Spacer(1, 10))
    story.append(Paragraph("What you receive after every run", S_H2))
    deliv_rows = [[Paragraph("Deliverable", S_TH), Paragraph("Description", S_TH)]]
    deliv = [
        ("Test plan", "Prioritised test cases covering positive, negative and edge scenarios"),
        ("Test scripts", "Runnable automation in two frameworks, stored in the repository"),
        ("Execution reports", "Pass/fail dashboards per browser, with screenshots and traces on failures"),
        ("Defect tickets", "Jira issues for genuine bugs, with reproduction steps, severity and evidence"),
        ("Run summary", "A one-page health check of the software after every run"),
    ]
    for a, b in deliv:
        deliv_rows.append([Paragraph(f"<b>{a}</b>", S_TD_B), Paragraph(b, S_TD)])
    deliv_tbl = Table(deliv_rows, colWidths=[4.2 * cm, None], repeatRows=1)
    deliv_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(deliv_tbl)
    story.append(Spacer(1, 10))

    # ---------------------------------------------------------------- 8. ROI
    story.append(PageBreak())
    story.append(section_header("8", "Return on Investment", "Cost & Time Savings"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "The chart below compares the typical hands-on effort for one full testing cycle, per release. Figures are "
        "indicative for a mid-sized web application and should be calibrated during the pilot.", S_BODY))
    story.append(Spacer(1, 4))
    story.append(ROIBarChart(PAGE_W - 2 * MARGIN))
    story.append(Paragraph("Effort per testing cycle (hours): traditional manual process vs the Agentic AI pipeline.", S_CAPTION))
    story.append(Spacer(1, 10))

    roi_rows = [[Paragraph("Metric", S_TH), Paragraph("Today (manual)", S_TH), Paragraph("With AI pipeline", S_TH), Paragraph("Impact", S_TH)]]
    roi_data = [
        ("Effort per testing cycle", "~92 hours", "~10 hours", "~90% reduction"),
        ("Test planning & design", "Days, done by seniors", "Minutes, generated & prioritised", "Faster start"),
        ("Script writing & maintenance", "Constant rework when UI changes", "Self-healing scripts fix themselves", "Near-zero upkeep"),
        ("Execution speed", "Nights/weekends, limited machines", "Minutes, in the cloud on every change", "Continuous QA"),
        ("Defect reporting", "Manual write-ups, inconsistent", "Ready-to-work Jira tickets with evidence", "Instant handover"),
        ("Coverage consistency", "Varies by tester and workload", "Same rigor on every single change", "Fewer escapes"),
    ]
    for a, b, cc, d in roi_data:
        roi_rows.append([
            Paragraph(f"<b>{a}</b>", S_TD_B), Paragraph(b, S_TD), Paragraph(cc, S_TD),
            Paragraph(f'<font color="#2E8B57"><b>{d}</b></font>', S_TD),
        ])
    roi_tbl = Table(roi_rows, colWidths=[4.3 * cm, 4.4 * cm, 5.2 * cm, 3.0 * cm], repeatRows=1)
    roi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(roi_tbl)
    story.append(Spacer(1, 10))

    roi_kpi = [
        ("~90%", "less manual effort", "per testing cycle"),
        ("~10x", "faster test turnaround", "from change to verified"),
        ("3x", "broader browser coverage", "at no extra effort"),
        ("100%", "of runs fully traced", "for audit & improvement"),
    ]
    roi_cells = []
    for num, lab, sub in roi_kpi:
        roi_cells.append(Paragraph(
            f'<para align="center"><font color="#2E8B57" size="16"><b>{num}</b></font><br/>'
            f'<font color="#1B3A6B" size="7.8"><b>{lab}</b></font><br/>'
            f'<font color="#5A6675" size="7.2">{sub}</font></para>', ps("rk")))
    roi_kpi_tbl = Table([roi_cells], colWidths=[(PAGE_W - 2 * MARGIN) / 4] * 4, rowHeights=[1.5 * cm])
    roi_kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREEN_LT),
        ("BOX", (0, 0), (-1, -1), 0.8, GREEN),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.6, HexColor("#BFDCC9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(roi_kpi_tbl)
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "<b>How the savings compound.</b> The effort reduction applies to every single release cycle, and testing becomes "
        "continuous rather than a release-gate scramble. The freed capacity shifts to higher-value work: exploratory "
        "testing, risk analysis and quality strategy. Savings grow over time as the knowledge library makes each new "
        "cycle smarter than the last.", S_BODY))

    story.append(PageBreak())

    # ---------------------------------------------------------------- 9. CLOSING
    story.append(section_header("9", "Where This Fits in Your Delivery", "Summary & Next Steps"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This pipeline is not a research demo - it is wired into the same tools your teams already use (GitHub for code, "
        "Jira for defects) and runs on every change. It turns quality assurance from a bottleneck into a continuously running, "
        "self-reporting service.", S_BODY))
    story.append(Spacer(1, 8))
    nxt_rows = [[Paragraph("#", S_TH), Paragraph("Suggested next step", S_TH), Paragraph("Outcome", S_TH)]]
    nxt = [
        ("1", "Pilot on one product area", "Measure release-cycle time and defect escape rate before/after"),
        ("2", "Expand coverage across suites", "Regression and smoke suites automated end-to-end"),
        ("3", "Enable stakeholder dashboards", "Business-facing quality health reporting in real time"),
    ]
    for a, b, cc in nxt:
        nxt_rows.append([Paragraph(f"<b>{a}</b>", S_TD_B), Paragraph(b, S_TD), Paragraph(cc, S_TD)])
    nxt_tbl = Table(nxt_rows, colWidths=[0.9 * cm, 6.4 * cm, None], repeatRows=1)
    nxt_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(nxt_tbl)
    story.append(Spacer(1, 12))
    quote = Table([[Paragraph(
        '<para align="center"><font color="#1B3A6B" size="11.5"><i>"The best time to find a bug is before your customer does. '
        'Now, something is testing your software every single day."</i></font></para>', ps("q", leading=16))]],
        colWidths=[None])
    quote.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
    ]))
    story.append(quote)

    return story

# ----------------------------------------------------------------------------
def main():
    out = "Agentic_AI_STLC_Pipeline_Overview.pdf"
    doc = Doc(out)
    doc.build(build_story())
    print(f"Created {out}")

if __name__ == "__main__":
    main()

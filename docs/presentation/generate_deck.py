# Corrected 2026-10-23: figures now come from docs/VERIFIED_METRICS.md; original wording preserved in Git commit 3926155.
# Usage: python3 generate_deck.py          -> PPTX only (non-interactive)
#        python3 generate_deck.py --pdf    -> also PDF via Apple Keynote (opens Keynote via AppleScript) + PNG previews
import os
import sys
import subprocess
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

def build_presentation(output_path, include_notes=True):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # --- Color Palette (Matching Reference Academic Beamer Style) ---
    c_white = RGBColor(255, 255, 255)
    c_bg = RGBColor(250, 250, 252)            # Clean off-white background
    c_maroon = RGBColor(163, 0, 0)             # Reference title & left footer crimson/maroon
    c_navy_header = RGBColor(27, 42, 107)      # Reference dark blue block header
    c_navy_card_bg = RGBColor(241, 244, 250)   # Reference soft blue-gray block fill
    c_card_border = RGBColor(210, 218, 230)    # Subtle card border
    c_card_inner_bg = RGBColor(246, 248, 252)  # Secondary card fill
    c_tbl_alt_bg = RGBColor(245, 248, 253)     # Alternating table row fill
    
    c_footer_mid = RGBColor(234, 237, 242)     # Middle footer light gray
    c_footer_right = RGBColor(222, 226, 232)   # Right footer gray
    
    c_text_dark = RGBColor(20, 25, 35)         # Primary dark body text
    c_text_muted = RGBColor(85, 95, 110)       # Secondary body text
    c_text_white = RGBColor(255, 255, 255)     # White text on dark headers
    c_text_code = RGBColor(20, 45, 95)         # Dark navy code snippet font
    c_green = RGBColor(0, 130, 50)             # Success metric green
    c_green_bg = RGBColor(235, 247, 238)       # Soft green row highlight

    # Helper: Set clean background
    def set_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = c_bg
        bg.line.fill.background()
        return bg

    # Helper: Footer matching Reference Beamer infolines template
    def add_footer(slide, slide_num):
        y = Inches(7.1)
        h = Inches(0.4)
        
        # Left segment: Maroon banner with Group/Course
        b_left = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, y, Inches(2.8), h)
        b_left.fill.solid()
        b_left.fill.fore_color.rgb = c_maroon
        b_left.line.fill.background()
        tf = b_left.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.08)
        p = tf.paragraphs[0]
        p.text = "Team AG-DATA / 23AID302"
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = c_text_white
        p.alignment = PP_ALIGN.CENTER

        # Middle segment: Light gray with project title
        b_mid = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(2.8), y, Inches(8.533), h)
        b_mid.fill.solid()
        b_mid.fill.fore_color.rgb = c_footer_mid
        b_mid.line.fill.background()
        tf = b_mid.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.08)
        p = tf.paragraphs[0]
        p.text = "Agricultural Commodity Price Analysis and Decision Support"
        p.font.size = Pt(10.5)
        p.font.color.rgb = c_maroon
        p.alignment = PP_ALIGN.CENTER

        # Right segment: Slide number
        b_right = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(11.333), y, Inches(2.0), h)
        b_right.fill.solid()
        b_right.fill.fore_color.rgb = c_footer_right
        b_right.line.fill.background()
        tf = b_right.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.08)
        p = tf.paragraphs[0]
        p.text = f"{slide_num} / 10"
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = c_text_dark
        p.alignment = PP_ALIGN.CENTER

    # Helper: Slide Header (Red/Maroon title exactly like Reference)
    def add_header(slide, title_text):
        tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.32), Inches(12.133), Inches(0.65))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = c_maroon

    # Helper: Reference Beamer Block (Dark Blue Rounded Header + Light Body)
    def add_beamer_block(slide, left, top, width, height, title):
        header_h = 0.42
        
        # Outer Card Body (Light Gray-Blue with rounded corners)
        body = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        body.fill.solid()
        body.fill.fore_color.rgb = c_navy_card_bg
        body.line.color.rgb = c_card_border
        body.line.width = Pt(1.0)
        
        # Header Bar (Dark Navy Rounded Top)
        hdr = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(header_h))
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = c_navy_header
        hdr.line.fill.background()
        
        # Header Text
        tb = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.06), Inches(width - 0.4), Inches(header_h - 0.1))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = c_text_white
        
        # Return content text frame
        tb_content = slide.shapes.add_textbox(Inches(left + 0.22), Inches(top + header_h + 0.1), Inches(width - 0.44), Inches(height - header_h - 0.18))
        tf_content = tb_content.text_frame
        tf_content.word_wrap = True
        tf_content.margin_left = tf_content.margin_top = tf_content.margin_right = tf_content.margin_bottom = 0
        return tf_content

    # Helper: Reference Callout Question Box (Full-width Dark Navy Header + Light Answer Box)
    def add_callout_box(slide, left, top, width, height, question, answer):
        header_h = 0.38
        
        # Body
        body = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        body.fill.solid()
        body.fill.fore_color.rgb = c_navy_card_bg
        body.line.color.rgb = c_card_border
        body.line.width = Pt(1.0)
        
        # Header
        hdr = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(header_h))
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = c_navy_header
        hdr.line.fill.background()
        
        # Question text
        tb_q = slide.shapes.add_textbox(Inches(left + 0.2), Inches(top + 0.05), Inches(width - 0.4), Inches(header_h - 0.1))
        tf_q = tb_q.text_frame
        tf_q.word_wrap = True
        tf_q.margin_left = tf_q.margin_top = tf_q.margin_right = tf_q.margin_bottom = 0
        p = tf_q.paragraphs[0]
        p.text = question
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = c_text_white
        
        # Answer text
        tb_a = slide.shapes.add_textbox(Inches(left + 0.25), Inches(top + header_h + 0.1), Inches(width - 0.5), Inches(height - header_h - 0.18))
        tf_a = tb_a.text_frame
        tf_a.word_wrap = True
        tf_a.margin_left = tf_a.margin_top = tf_a.margin_right = tf_a.margin_bottom = 0
        p = tf_a.paragraphs[0]
        p.text = answer
        p.font.size = Pt(11)
        p.font.color.rgb = c_text_dark
        return body

    # Helper: Set Speaker Notes
    def set_notes(slide, script, technical_point, likely_question, defensible_answer):
        if not include_notes:
            return
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = (
            f"=== PRESENTER SCRIPT (60-90 SECONDS) ===\n{script}\n\n"
            f"=== MAIN TECHNICAL POINT ===\n{technical_point}\n\n"
            f"=== LIKELY FACULTY QUESTION ===\n{likely_question}\n\n"
            f"=== SHORT, DEFENSIBLE ANSWER ===\n{defensible_answer}"
        )

    # =========================================================================
    # SLIDE 1: Title, Team, Faculty & Institution (Matching Reference Slide 1)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1)
    add_footer(s1, 1)

    # Top Light Gray Rounded Card for Title
    top_box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(0.55), Inches(12.133), Inches(1.8))
    top_box.fill.solid()
    top_box.fill.fore_color.rgb = RGBColor(236, 240, 246)
    top_box.line.color.rgb = RGBColor(215, 222, 232)
    top_box.line.width = Pt(1.2)

    tb1 = s1.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.733), Inches(1.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Agricultural Commodity Price Forecasting and Market Analysis"
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = c_maroon
    p.alignment = PP_ALIGN.CENTER

    p2 = tf1.add_paragraph()
    p2.text = "Using Hadoop HDFS, Apache Spark, MLlib, and Apache Kafka"
    p2.font.size = Pt(16)
    p2.font.color.rgb = c_maroon
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(6)

    # Subtitle: Final Review - Team AG-DATA
    tb_sub = s1.shapes.add_textbox(Inches(0.8), Inches(2.55), Inches(11.733), Inches(0.45))
    tf_sub = tb_sub.text_frame
    p = tf_sub.paragraphs[0]
    p.text = "Final Review — Team AG-DATA"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = c_text_dark
    p.alignment = PP_ALIGN.CENTER

    # Members Table Card - Real Structured Table
    members_data = [
        ("Name", "Register no."),
        ("C Rishitha", "CB.AI.U4AID24109"),
        ("Karthikeya Y", "CB.AI.U4AID24163"),
        ("Ashwin Tyagi", "CB.AI.U4AID24167"),
        ("Kaushal S", "CB.AI.U4AID24168")
    ]
    tbl_shape = s1.shapes.add_table(5, 2, Inches(4.1), Inches(3.15), Inches(5.133), Inches(2.1))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(2.56)
    tbl.columns[1].width = Inches(2.57)

    for r_idx, (name, reg) in enumerate(members_data):
        c0 = tbl.cell(r_idx, 0)
        c1 = tbl.cell(r_idx, 1)
        c0.text = name
        c1.text = reg
        
        for c in (c0, c1):
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.margin_left = Inches(0.15)
            c.margin_right = Inches(0.15)
            p = c.text_frame.paragraphs[0]
            p.font.size = Pt(12)
            if r_idx == 0:
                p.font.bold = True
                p.font.color.rgb = c_text_dark
                c.fill.solid()
                c.fill.fore_color.rgb = RGBColor(230, 235, 245)
            else:
                p.font.color.rgb = c_text_dark
                c.fill.solid()
                c.fill.fore_color.rgb = c_white if r_idx % 2 == 1 else c_tbl_alt_bg

    # Bottom Department & Faculty Info
    tb_bot = s1.shapes.add_textbox(Inches(0.8), Inches(5.45), Inches(11.733), Inches(1.3))
    tf_bot = tb_bot.text_frame
    tf_bot.word_wrap = True
    
    p = tf_bot.paragraphs[0]
    p.text = "23AID302 — Big Data Analytics"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = c_text_dark
    p.alignment = PP_ALIGN.CENTER

    p = tf_bot.add_paragraph()
    p.text = "Department of Artificial Intelligence and Data Science  ·  Amrita Vishwa Vidyapeetham"
    p.font.size = Pt(12)
    p.font.color.rgb = c_text_muted
    p.alignment = PP_ALIGN.CENTER
    p.space_before = Pt(3)

    p = tf_bot.add_paragraph()
    p.text = "Faculty Guide: Dr. Sreeja"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = c_maroon
    p.alignment = PP_ALIGN.CENTER
    p.space_before = Pt(4)

    set_notes(
        s1,
        "Good morning Dr. Sreeja and evaluators. Today, our team presents our Big Data Analytics final project: Agricultural Commodity Price Forecasting and Market Analysis using Hadoop HDFS and Apache Spark. Our team members are Rishitha, Karthikeya, Ashwin, and Kaushal. The goal of this project is an end-to-end distributed pipeline over 75.98 million archived mandi reports plus 7.7 million official records that forecasts mandi prices 1 to 14 days ahead with Spark MLlib, with measured 80% intervals, and streams daily reports through Kafka.",
        "Team and faculty title slide matching the exact 23AID302 course reference format.",
        "What is the core Big Data focus of this project?",
        "Ma'am, our core focus is distributed data architecture: distributed storage using HDFS replication, leakage-safe feature engineering and deduplication in Apache Spark, honestly evaluated price forecasting with Spark MLlib, and micro-batch processing of daily reports through Kafka and Structured Streaming."
    )

    # =========================================================================
    # SLIDE 2: 1. What Are We Trying to Find? (Matching Reference Slide 2)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_footer(s2, 2)
    add_header(s2, "1. What Are We Trying to Find?")

    # Left Block: Mandi Price Anomaly
    tf_left = add_beamer_block(s2, 0.6, 1.15, 5.85, 2.9, "Mandi: what price will be reported?")
    p = tf_left.paragraphs[0]
    p.text = "Forecast the modal price a mandi will report 1, 3, 7 and 14 days ahead: 36 commodities, 11,845 mandi series."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark

    p = tf_left.add_paragraph()
    p.text = "Every forecast carries an 80% conformal interval whose test coverage is measured."
    p.font.size = Pt(11)
    p.font.color.rgb = c_text_muted
    p.space_before = Pt(5)

    p = tf_left.add_paragraph()
    p.text = "Baseline: persistence (\"last price\"), which is hard to beat: 17–34% of price changes are exactly zero."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(5)

    # Right Block: Farmer Decision Support
    tf_right = add_beamer_block(s2, 6.85, 1.15, 5.85, 2.9, "Decision Support: cautious outlook cards")
    p = tf_right.paragraphs[0]
    p.text = "Forecasts and intervals become cards a farmer can adjust with own costs:"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_text_dark

    advisories = [
        ("SELL", "Even the upper interval estimate is not above the last price."),
        ("HOLD", "Even the lower estimate exceeds the last price plus storage costs."),
        ("WATCH", "No clear signal; the default card."),
        ("COMPARE", "A nearby mandi recently reported a clearly higher price.")
    ]
    for act, desc in advisories:
        p = tf_right.add_paragraph()
        p.text = f"• {act}: {desc}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = c_text_dark
        p.space_before = Pt(3)

    # Bottom Callout Box: Why do we need big data tools?
    add_callout_box(
        s2, 0.6, 4.35, 12.1, 1.7,
        "Why do we need big data tools?",
        "The archive alone has 75.98 million mandi reports, and the forecast panel has 21.06 million feature rows "
        "built with per-series window functions. That does not fit single-node Pandas on a 16 GB laptop. "
        "HDFS stores the layers in replicated blocks; Spark splits the work across executor threads."
    )

    # Goal Footer line
    tb_goal = s2.shapes.add_textbox(Inches(0.6), Inches(6.25), Inches(12.1), Inches(0.4))
    tf_goal = tb_goal.text_frame
    p = tf_goal.paragraphs[0]
    p.text = "Goal: prepare the data, compare forecasting models honestly, and stream daily reports."
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = c_text_dark

    set_notes(
        s2,
        "Slide 2 defines what we are trying to find. On the left: the modal price a mandi will report 1, 3, 7 and 14 days ahead, for 36 commodities and 11,845 series, each with an 80% interval. We always compare with persistence, the last reported price, which is hard to beat because 17 to 34% of price changes are exactly zero. On the right, the forecasts become cautious SELL, HOLD, WATCH and COMPARE cards. In the bottom box: 75.98 million reports and 21.06 million feature rows do not fit single-node Pandas, so HDFS stores the data in replicated blocks and Spark distributes the feature engineering and MLlib work across CPU cores.",
        "Problem formulation, domain objective, and big data justification using the reference layout.",
        "Why can't this be done in a standard SQL database or Pandas?",
        "Ma'am, per-series window features and business-key deduplication over 75 million reports exceed the memory of a single-node tool on our 16 GB laptop. Spark provides Catalyst query optimization, Tungsten execution and partition-level parallelism; on the full 75.6 million rows, 10 cores give a 2.4 to 3.0 times speed-up over one core."
    )

    # =========================================================================
    # SLIDE 3: 2. Our Data and the 5 Vs (Matching Reference Slide 3)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_footer(s3, 3)
    add_header(s3, "2. Our Data and the 5 Vs")

    # Left Block: Data already stored in HDFS
    tf_data = add_beamer_block(s3, 0.6, 1.15, 5.85, 4.95, "Data layers")
    
    # Dataset Summary Table inside Left Block
    dataset_rows = [
        ("File / Layer", "Rows", "Role"),
        ("Raw archive (Kaggle v134)", "75,984,017", "AGMARKNET 2001–2026"),
        ("Archive silver", "75,644,801", "After quality + dedup"),
        ("Official back-fill", "7,720,662", "data.gov.in, 2025-10 → 2026-10"),
        ("Silver v2", "82,114,083", "Archive + official"),
        ("Forecast panel", "21.06 M", "36 commodities, 11,845 series")
    ]
    t_shape_d = s3.shapes.add_table(6, 3, Inches(0.8), Inches(1.75), Inches(5.45), Inches(2.2))
    t_d = t_shape_d.table
    t_d.columns[0].width = Inches(2.35)
    t_d.columns[1].width = Inches(1.25)
    t_d.columns[2].width = Inches(1.85)

    for r_idx, (f, r, s) in enumerate(dataset_rows):
        c0 = t_d.cell(r_idx, 0)
        c1 = t_d.cell(r_idx, 1)
        c2 = t_d.cell(r_idx, 2)
        c0.text = f
        c1.text = r
        c2.text = s
        for c in (c0, c1, c2):
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.margin_left = Inches(0.08)
            c.margin_right = Inches(0.08)
            p = c.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            if r_idx == 0:
                p.font.bold = True
                p.font.color.rgb = c_navy_header
                c.fill.solid()
                c.fill.fore_color.rgb = RGBColor(228, 234, 246)
            else:
                p.font.color.rgb = c_text_dark
                c.fill.solid()
                c.fill.fore_color.rgb = c_white if r_idx % 2 == 1 else c_tbl_alt_bg

    # Descriptions below the table
    tb_ds_desc = s3.shapes.add_textbox(Inches(0.8), Inches(4.1), Inches(5.45), Inches(1.9))
    tf_ds_desc = tb_ds_desc.text_frame
    tf_ds_desc.word_wrap = True
    
    p = tf_ds_desc.paragraphs[0]
    p.text = "Attributes: State, District, Market, Commodity, Variety, Grade, Arrival_Date, Min/Max/Modal Price."
    p.font.size = Pt(9.5)
    p.font.color.rgb = c_text_muted

    p = tf_ds_desc.add_paragraph()
    p.text = "Coverage finding: the archive mirror holds only 30.0% of official reports for 2025-10 → 2026-04; where both exist, 99.33% of modal prices agree."
    p.font.size = Pt(9.5)
    p.font.color.rgb = c_text_muted
    p.space_before = Pt(4)

    # Right Block: The 5 Vs in our project
    tf_5vs = add_beamer_block(s3, 6.85, 1.15, 5.85, 4.95, "5 Vs in our project")
    p = tf_5vs.paragraphs[0]
    p.text = f"{'5 Vs':<12} {'In our project':<32}"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = c_navy_header

    five_vs_data = [
        ("Volume", "75.98M raw archive rows; 82.1M silver v2 rows; 692 MB silver Parquet in HDFS."),
        ("Velocity", "Daily reports through Kafka topic agri.prices.v1 into Structured Streaming."),
        ("Variety", "Archive CSV files and two official data.gov.in API resources."),
        ("Veracity", "Quality rules, de-duplication, quarantine; 30% archive coverage found."),
        ("Value", "Evaluated price forecasts with intervals and cautious decision cards.")
    ]
    for v, desc in five_vs_data:
        p = tf_5vs.add_paragraph()
        p.text = f"{v:<12} {desc}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = c_text_dark
        p.space_before = Pt(6)

    # Bottom Note (Matching Reference bottom note)
    tb_note = s3.shapes.add_textbox(Inches(0.6), Inches(6.25), Inches(12.1), Inches(0.4))
    tf_note = tb_note.text_frame
    p = tf_note.paragraphs[0]
    p.text = "All models are trained and tested on real data only. A v1 synthetic workload exists for scalability tests and is never used for any model."
    p.font.size = Pt(11)
    p.font.color.rgb = c_maroon

    set_notes(
        s3,
        "Slide 3 presents our data layers and the 5 Vs. The raw archive has 75.98 million rows; after quality rules and de-duplication the silver layer keeps 75.64 million. We back-filled 7.72 million official records from data.gov.in for October 2025 to October 2026, giving a silver v2 layer of 82.1 million rows. The back-fill showed that the archive mirror holds only 30% of official reports after September 2025. The forecast panel has 21.06 million feature rows over 11,845 series. On the right, the 5 Vs map to our project. All models are trained and tested on real data only.",
        "Dataset provenance, table breakdown, and the 5 Vs structured like Reference Slide 3.",
        "Why does silver v2 differ from the archive silver layer?",
        "Ma'am, the archive silver layer has 75.64 million rows. Silver v2 keeps the archive before 2025-10-01 (74.49 million rows) and replaces everything from 2025-10-01 with the official data.gov.in back-fill (7.63 million rows after the same rules), giving 82.11 million rows. We did this because the archive mirror holds only 30% of the official reports for that period."
    )

    # =========================================================================
    # SLIDE 4: 3. System Setup and Configuration (Matching Reference Slide 4)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_footer(s4, 4)
    add_header(s4, "3. System Setup and Configuration")

    # Flow Diagram: 5 Rounded Boxes with Arrows
    flow_steps = [
        ("Input", "Archive CSV\n+ official API"),
        ("HDFS", "Store files\nin blocks"),
        ("Scala", "Read, clean\n& dedup"),
        ("Spark", "Features\n& forecasts"),
        ("Results", "Gold, API\n& PWA")
    ]
    box_w = 1.95
    box_h = 1.05
    spacing = 0.55
    start_x = 0.6
    y_flow = 1.15

    for i, (hdr_text, sub_text) in enumerate(flow_steps):
        x = start_x + i * (box_w + spacing)
        box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y_flow), Inches(box_w), Inches(box_h))
        box.fill.solid()
        box.fill.fore_color.rgb = c_navy_card_bg
        box.line.color.rgb = c_navy_header
        box.line.width = Pt(1.5)
        
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.12)
        p = tf.paragraphs[0]
        p.text = hdr_text
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = c_maroon
        p.alignment = PP_ALIGN.CENTER
        
        p = tf.add_paragraph()
        p.text = sub_text
        p.font.size = Pt(10)
        p.font.color.rgb = c_text_dark
        p.alignment = PP_ALIGN.CENTER
        
        # Arrow to next box
        if i < len(flow_steps) - 1:
            arrow = s4.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + box_w + 0.1), Inches(y_flow + 0.35), Inches(spacing - 0.2), Inches(0.35))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = c_navy_header
            arrow.line.fill.background()

    # Middle Left Block: HDFS Storage Settings
    tf_hdfs = add_beamer_block(s4, 0.6, 2.5, 5.85, 2.6, "HDFS storage settings")
    p = tf_hdfs.paragraphs[0]
    p.text = "• 1 NameNode + 3 DataNodes (Docker, one host)."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p = tf_hdfs.add_paragraph()
    p.text = "• Block size: 128 MiB; replication: 3 copies of each block."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)
    p = tf_hdfs.add_paragraph()
    p.text = "• Silver layer: 692 MB, HEALTHY; readable with 1 DataNode down."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)
    p = tf_hdfs.add_paragraph()
    p.text = "• Clean output: Snappy Parquet, partitioned by year."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    # Middle Right Block: Spark Application Settings
    tf_spark = add_beamer_block(s4, 6.85, 2.5, 5.85, 2.6, "Spark application settings")
    p = tf_spark.paragraphs[0]
    p.text = "• Engine: Apache Spark 4.2 in local[*] mode (10 cores)."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p = tf_spark.add_paragraph()
    p.text = "• Multi-core local CPU threads (NOT YARN worker executors)."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)
    p = tf_spark.add_paragraph()
    p.text = "• Also benchmarked: Docker Spark cluster, 2 workers × 3 cores."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)
    p = tf_spark.add_paragraph()
    p.text = "• Shuffle partitions: 64 in the forecast jobs, coalesced by AQE."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    # Bottom Callout Box
    add_callout_box(
        s4, 0.6, 5.25, 12.1, 1.45,
        "Are HDFS DataNodes also running as Spark executors?",
        "No. HDFS runs in Docker containers strictly for block storage with replication factor 3; Spark runs in local[*] mode on host CPU cores. "
        "The three DataNodes share one physical disk, so replication shows HDFS behaviour, not hardware durability."
    )

    set_notes(
        s4,
        "Slide 4 details our System Setup and Configuration. Across the top is our end-to-end pipeline: archive CSVs and official API records are cleaned and de-duplicated by Scala readers, stored as Parquet layers in HDFS, Spark computes leakage-safe features and MLlib forecasts, and gold tables feed the API and the six-language app. On the middle left, HDFS runs 1 NameNode and 3 DataNodes in Docker with 128 MB blocks and replication factor 3; the 692 MB silver layer is HEALTHY and stayed readable with one DataNode down. On the middle right, Spark executes in local[*] mode on 10 cores with 64 shuffle partitions. The bottom box answers a frequent viva question: DataNodes store blocks, they are not Spark executors.",
        "Architecture flow diagram, storage settings, Spark settings, and callout box matching Reference Slide 4.",
        "Why didn't your team deploy a multi-node YARN compute cluster?",
        "Ma'am, we only had one machine, and we wanted to be transparent. Multi-container HDFS on Docker gives genuine block storage, replication and failover behaviour. Spark in local[*] mode uses all 10 cores; we also ran a 2-worker Docker Spark cluster on the same host (11.27 million rows: 9.2 s and 14.4 s for our two workloads). We do not claim a physical multi-node cluster."
    )

    # =========================================================================
    # SLIDE 5: 4. Spark Workflow and the DAG (Matching Reference Slide 5)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_footer(s5, 5)
    add_header(s5, "4. Spark Workflow and the DAG")

    # Left Block: Steps in Spark
    tf_steps = add_beamer_block(s5, 0.6, 1.15, 5.85, 3.8, "Steps in Spark")
    steps = [
        ("1", "Read and parse CSVs with explicit StructType schemas."),
        ("2", "Quality rules and business-key de-duplication → silver."),
        ("3", "Window features per series (≤ t) and targets (> t)."),
        ("4", "Fit MLlib pipelines, choose on 2024, score the test once.")
    ]
    for num, txt in steps:
        p = tf_steps.paragraphs[0] if num == "1" else tf_steps.add_paragraph()
        p.text = f"{num}  {txt}"
        p.font.size = Pt(11)
        p.font.color.rgb = c_text_dark
        if num != "1": p.space_before = Pt(4)

    p = tf_steps.add_paragraph()
    p.text = "Partitions: 64 shuffle partitions (AQE coalesces); year= directory pruning."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_maroon
    p.space_before = Pt(8)

    p = tf_steps.add_paragraph()
    p.text = "Scaling (measured): full 75.6M rows on 10 cores: W1 42.2 s, W2 65.9 s; speed-up 2.4× / 3.0× vs 1 core."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    # Right Block: DAG: a map of the work Spark runs
    tf_dag = add_beamer_block(s5, 6.85, 1.15, 5.85, 3.8, "DAG: a map of the work Spark runs")
    p = tf_dag.paragraphs[0]
    p.text = "Execution DAG (Shuffle-Delimited Stages):"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = c_navy_header

    # Draw Stage Diagram boxes inside Right Block
    dag_stages = [
        ("Step 1", "Parquet Read"),
        ("Step 2", "Harmonise & Filter"),
        ("Step 3", "Window Shuffle"),
        ("Step 4", "Features & Targets"),
        ("Step 5", "Model Fit / Score")
    ]
    dag_x = 7.15
    dag_y = 2.05
    for i, (stg, desc) in enumerate(dag_stages):
        cur_y = dag_y + i * 0.46
        box = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(dag_x), Inches(cur_y), Inches(1.8), Inches(0.38))
        box.fill.solid()
        box.fill.fore_color.rgb = c_white
        box.line.color.rgb = c_navy_header
        box.line.width = Pt(1.0)
        tf = box.text_frame
        tf.margin_top = Inches(0.06)
        p = tf.paragraphs[0]
        p.text = f"{stg}: {desc}"
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = c_navy_header
        p.alignment = PP_ALIGN.CENTER
        
        if i < len(dag_stages) - 1:
            arr = s5.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(dag_x + 0.8), Inches(cur_y + 0.38), Inches(0.2), Inches(0.08))
            arr.fill.solid()
            arr.fill.fore_color.rgb = c_maroon
            arr.line.fill.background()

    # Note next to DAG
    tb_dnote = s5.shapes.add_textbox(Inches(9.2), Inches(2.3), Inches(3.3), Inches(2.2))
    tf_dn = tb_dnote.text_frame
    tf_dn.word_wrap = True
    p = tf_dn.paragraphs[0]
    p.text = "Arrows show stage dependencies.\n\nWide transformations create shuffle boundaries.\n\nExact stage counts are read from the Spark UI for each run."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_muted

    # Bottom Callout Box
    add_callout_box(
        s5, 0.6, 5.15, 12.1, 1.55,
        "Where do the stages come from?",
        "Reads, joins, and calculations create the DAG. Narrow transformations pipeline within a stage without network movement. "
        "Wide transformations (Window.partitionBy, groupByKey) require cross-partition shuffles, creating stage boundaries. "
        "Spark assigns stage numbers dynamically at runtime."
    )

    set_notes(
        s5,
        "Slide 5 covers Spark Workflow and DAG execution. On the left are our steps: explicit schemas, quality rules and business-key de-duplication, leakage-safe window features and targets, and MLlib model fitting and scoring. We use 64 shuffle partitions, coalesced by AQE, and year directory pruning. On the full 75.6 million rows, 10 cores give a 2.4 to 3.0 times speed-up over one core. On the right, the DAG diagram shows how Spark schedules work: narrow transformations pipeline in memory, while wide transformations like Window.partitionBy trigger shuffles that divide the DAG into stages. The bottom box explains that stage boundaries come from shuffle dependencies; we read the exact counts in the Spark UI.",
        "Spark workflow, DAG stage breakdown, partitions, cache, and callout question matching Reference Slide 5.",
        "What is the difference between a transformation and an action in Spark?",
        "Ma'am, transformations like `filter()` and `withColumn()` are lazily evaluated—they only record operations in the DAG. No computation happens until an action like `count()`, `collect()`, or `write.parquet()` is called, which triggers Catalyst optimization and launches the DAG across stages."
    )

    # =========================================================================
    # SLIDE 6: 5. Scala Code and Streaming (Matching Reference Slide 6)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_footer(s6, 6)
    add_header(s6, "5. Scala Code and Streaming")

    # Left Block: Scala DataFrame API: source excerpt
    tf_code = add_beamer_block(s6, 0.6, 1.15, 6.2, 3.8, "Scala DataFrame API: source excerpt")
    code_text = (
        "// 1. Non-fatal date parsing (Readers.scala)\n"
        "expr(\"try_to_date(trim(Arrival_Date), 'yyyy-MM-dd')\")\n\n"
        "// 2. Business-key de-duplication (Deduplicate.scala)\n"
        "val w = Window.partitionBy(DataQuality.businessKey.map(col): _*)\n"
        "  .orderBy(/* deterministic quality order */)\n"
        "df.withColumn(\"_rn\", row_number().over(w))\n\n"
        "// 3. Leakage-safe features (forecast/Features.scala)\n"
        "def days(lo: Long, hi: Long) = byEntity.rangeBetween(lo, hi)\n"
        ".withColumn(\"mean30\", avg(lp).over(days(-29, 0)))  // ends at t"
    )
    p = tf_code.paragraphs[0]
    p.text = code_text
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = c_text_code

    # Right Block: What the code does
    tf_what = add_beamer_block(s6, 7.0, 1.15, 5.7, 3.8, "What the code does")
    bullets = [
        "Read CSV with fixed column types and explicit StructType schemas.",
        "Non-fatal date parsing: a malformed date becomes null, not a crash.",
        "Deterministic row_number() keeps one reproducible row per business key.",
        "Feature windows end at the current report; targets start after it; a perturbation test enforces this.",
        "Batch and streaming share one canonicalisation function."
    ]
    for i, b in enumerate(bullets):
        p = tf_what.paragraphs[0] if i == 0 else tf_what.add_paragraph()
        p.text = f"• {b}"
        p.font.size = Pt(11.5)
        p.font.color.rgb = c_text_dark
        if i > 0: p.space_before = Pt(6)

    # Bottom Callout Box
    add_callout_box(
        s6, 0.6, 5.15, 12.1, 1.55,
        "How do we use Structured Streaming?",
        "Reports go to Kafka topic agri.prices.v1 (6 partitions). PriceEventStream writes bronze (raw + offsets), quarantines invalid "
        "messages before a 10-day watermark, drops re-sends by event_id, and writes silver and alerts. "
        "Checkpointed offsets give effectively-once output per offset range (end-to-end exactly-once is not claimed)."
    )

    set_notes(
        s6,
        "Slide 6 presents our Scala implementation and streaming architecture. On the left are excerpts from our codebase: snippet 1 uses try_to_date so a malformed date becomes null instead of failing the job; snippet 2 de-duplicates deterministically over the business key with row_number; snippet 3 builds a feature window that ends at the current report, which our perturbation test enforces. The bottom box explains streaming: reports go through Kafka topic agri.prices.v1 into PriceEventStream, which writes bronze, quarantines invalid messages before the watermark, removes re-sends and writes silver and alerts. In our replay, 21,524 messages gave 20,000 rows in silver, 1,317 duplicates removed and 207 quarantined, with nothing missing.",
        "Code excerpts, architectural purpose, and Structured Streaming callout box matching Reference Slide 6.",
        "Why don't you compute forecast features in the stream?",
        "Ma'am, it was a deliberate trade-off: one feature implementation instead of two that could drift apart. Streaming validates reports and raises alerts; features and forecasts are recomputed by the daily batch job. Batch and stream share the same canonicalisation code, and our parity check found 0 mismatches between them."
    )

    # =========================================================================
    # SLIDE 7: 6. How We Train and Test the Models (Matching Reference Slide 7)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7)
    add_footer(s7, 7)
    add_header(s7, "6. How We Train and Test the Models")

    # Left Block: Two versions of the anomaly model
    tf_models = add_beamer_block(s7, 0.6, 1.15, 5.85, 3.8, "Baselines and models")
    p = tf_models.paragraphs[0]
    p.text = "1  Baselines"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_maroon

    p = tf_models.add_paragraph()
    p.text = "• Persistence (last report), moving averages, seasonal naive.\n• Target: log return to a report strictly after the origin.\n• Horizons: next report, 3, 7 and 14 days."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(3)

    p = tf_models.add_paragraph()
    p.text = "2  Spark MLlib pipelines"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_navy_header
    p.space_before = Pt(8)

    p = tf_models.add_paragraph()
    p.text = "• Linear regression, random forest, gradient-boosted trees.\n• One global model per horizon, fitted on training rows only.\n• 80% split-conformal intervals calibrated on 2024."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(3)

    p = tf_models.add_paragraph()
    p.text = "Selected: GBT, absolute loss (next, 3 d); random forest, 60 trees, depth 10 (7, 14 d)."
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = c_green
    p.space_before = Pt(6)

    # Right Block: Temporal split & Tuning
    tf_split = add_beamer_block(s7, 6.85, 1.15, 5.85, 3.8, "Strict temporal split & tuning")
    p = tf_split.paragraphs[0]
    p.text = "Chronological split (purged on target dates):"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_navy_header

    p = tf_split.add_paragraph()
    p.text = "• Train: origins 2016-01-01 .. 2023-12-31.\n• Validation: 2024, model choice and conformal calibration.\n• Test: 2025-01-01 .. 2026-04-20, scored once."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_split.add_paragraph()
    p.text = "Then, frozen models (no refitting):"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = c_navy_header
    p.space_before = Pt(6)

    p = tf_split.add_paragraph()
    p.text = "• Same test period on complete official data.\n• Prospective 2026-04-22 → 2026-10-22: data that did not exist in the archive."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(3)

    # Bottom Callout Box
    add_callout_box(
        s7, 0.6, 5.15, 12.1, 1.55,
        "Why keep test data aside chronologically?",
        "Random k-fold cross-validation lets future market information leak into training. "
        "Splitting chronologically and scoring the test once tests the models on genuinely later periods, as in deployment; "
        "the prospective check then uses months that did not exist when the models were trained."
    )

    set_notes(
        s7,
        "Slide 7 explains how we train and test. On the left: persistence, moving-average and seasonal-naive baselines against MLlib linear regression, random forests and gradient-boosted trees, one global model per horizon. Absolute-loss GBT was selected for next and 3 days, random forest for 7 and 14 days. On the right: train origins 2016 to 2023, model choice and conformal calibration on 2024, and the January 2025 to April 2026 test scored once. We then re-scored the frozen models on complete official data and on six months, April to October 2026, that did not exist in the archive. The bottom box explains why random splits would leak future information.",
        "Model definitions, temporal split strategy, and data leakage callout box matching Reference Slide 7.",
        "Why did you replace the v1 anomaly classifier with forecasting?",
        "Ma'am, we audited v1 and found its headline classifier metrics were not produced by any code or log, its labels were functions of its own features, and its outlier bounds were fitted on the test years; its only logged classifier (72.54% accuracy) was below the 84.35% all-normal baseline. Those claims are withdrawn (docs/AUDIT_PRIOR_RESULTS.md). The project title promises price forecasting, so we built an honest forecasting benchmark instead."
    )

    # =========================================================================
    # SLIDE 8: 7. Results for Both Tasks (Matching Reference Slide 8)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8)
    add_footer(s8, 8)
    add_header(s8, "7. Results")

    # Top Block: Model results table - Real Structured Table!
    tf_res_hdr = add_beamer_block(s8, 0.6, 1.15, 12.1, 2.65, "Forecasting — test 2025-01-01 .. 2026-04-20 (relative MAE vs persistence; lower is better)")
    
    results_rows = [
        ("Horizon (selected model)", "Persist. MAE ₹/q", "Model MAE ₹/q", "Rel. MAE", "80% cover.", "Frozen, 2026-04→10"),
        ("Next report (GBT, abs. loss)", "189.0", "183.5", "0.971", "78.6%", "0.963"),
        ("3 days (GBT, abs. loss)", "242.6", "231.1", "0.953", "79.4%", "0.955"),
        ("7 days (random forest)", "308.8", "289.7", "0.938", "80.0%", "0.958"),
        ("14 days (random forest)", "397.0", "366.4", "0.923", "80.5%", "0.952")
    ]
    t_shape_r = s8.shapes.add_table(5, 6, Inches(0.8), Inches(1.75), Inches(11.7), Inches(1.85))
    t_r = t_shape_r.table
    t_r.columns[0].width = Inches(4.7)
    t_r.columns[1].width = Inches(1.4)
    t_r.columns[2].width = Inches(1.4)
    t_r.columns[3].width = Inches(1.4)
    t_r.columns[4].width = Inches(1.4)
    t_r.columns[5].width = Inches(1.4)

    for r_idx, row in enumerate(results_rows):
        is_hdr = (r_idx == 0)
        is_task2 = False  # no single highlighted row: all four horizons are results
        for c_idx in range(6):
            cell = t_r.cell(r_idx, c_idx)
            cell.text = row[c_idx]
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.1)
            cell.margin_right = Inches(0.1)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(10.5)
            if c_idx > 0:
                p.alignment = PP_ALIGN.RIGHT
            else:
                p.alignment = PP_ALIGN.LEFT
                
            if is_hdr:
                p.font.bold = True
                p.font.color.rgb = c_navy_header
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(228, 234, 246)
            elif is_task2:
                p.font.bold = True
                p.font.color.rgb = c_green
                cell.fill.solid()
                cell.fill.fore_color.rgb = c_green_bg
            else:
                p.font.color.rgb = c_text_dark
                cell.fill.solid()
                cell.fill.fore_color.rgb = c_white if r_idx % 2 == 1 else c_tbl_alt_bg

    # Bottom Left Block: What the ML results mean
    tf_mean = add_beamer_block(s8, 0.6, 4.0, 5.85, 2.85, "What the results mean")
    p = tf_mean.paragraphs[0]
    p.text = "• 3–8% lower error than persistence; Diebold–Mariano p ≤ 1.3e-22 at every horizon."
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = c_green

    p = tf_mean.add_paragraph()
    p.text = "• Better than persistence on 58.5–76.4% of series; 80% intervals cover 78.6–80.5%."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_mean.add_paragraph()
    p.text = "• Cards (7 d): WATCH 98.5% of days; HOLD 0.5% (hit 80.0%); SELL 1.0% (hit 67.8%)."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_mean.add_paragraph()
    p.text = "• Anomaly flags (injected corruptions only): PR-AUC 0.704 vs 0.352 legacy IQR. No real-anomaly accuracy is claimed."
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = c_navy_header
    p.space_before = Pt(4)

    # Bottom Right Block: Real-Time Streaming Results
    tf_stream = add_beamer_block(s8, 6.85, 4.0, 5.85, 2.85, "Streaming and storage results")
    p = tf_stream.paragraphs[0]
    p.text = "Replay: 21,524 Kafka messages."
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = c_maroon

    p = tf_stream.add_paragraph()
    p.text = "• 20,000 to silver + 1,317 duplicates removed + 207 quarantined; 0 missing."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(5)

    p = tf_stream.add_paragraph()
    p.text = "• Batch/stream parity: 0 mismatches. Producer→sink latency p50: 1.69 s."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_stream.add_paragraph()
    p.text = "• Live pull 2026-10-23: 4/4 records through Kafka to silver."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_stream.add_paragraph()
    p.text = "• HDFS: 692 MB silver, replication 3, HEALTHY; readable with 1 DataNode down."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_muted
    p.space_before = Pt(4)

    set_notes(
        s8,
        "Slide 8 presents our verified results. The top table shows relative MAE against persistence on the 2025 to 2026 test: 0.971, 0.953, 0.938 and 0.923 for next, 3, 7 and 14 days, with 80% intervals covering 78.6 to 80.5%. The last column shows the frozen models on six unseen months: 0.952 to 0.963. Every Diebold–Mariano p-value is at most 1.3e-22. On the bottom left: the gains are modest but hold on most series; decision cards are conservative; anomaly flags are evaluated only on injected corruptions. On the bottom right: the Kafka replay delivered all 20,000 valid messages with 0 parity mismatches and a 1.69 second median latency, and HDFS stayed readable with one DataNode down.",
        "Model evaluation table, confusion matrix interpretation, and streaming replay validation matching Reference Slide 8.",
        "Your model beats 'last price' by only 3 to 8%. Why so small, and is it real?",
        "Ma'am, persistence is a hard baseline for mandi prices: 17 to 34% of price changes are exactly zero because mandis re-quote prices. The gain is real: Diebold–Mariano tests reject equal accuracy at every horizon, the model beats persistence on 58.5 to 76.4% of series, and the frozen models still score 0.952 to 0.963 on six months of data that did not exist when they were trained. A per-series exponential smoother matches us at 1 to 3 days, so our clear advantage is at 7 to 14 days."
    )

    # =========================================================================
    # SLIDE 9: 8. Challenges, Limits and Next Steps (Matching Reference Slide 9)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_bg(s9)
    add_footer(s9, 9)
    add_header(s9, "8. Challenges, Limits and Next Steps")

    # Left Block: Challenges we handled
    tf_chal = add_beamer_block(s9, 0.6, 1.15, 5.85, 3.2, "Challenges we handled")
    chal_bullets = [
        "JDK 21 reflection blocked Spark; solved via JVM --add-opens flags.",
        "Malformed dates handled by try_to_date instead of failing jobs.",
        "Persistence is hard to beat (17–34% zero changes): absolute-loss GBT was needed.",
        "The archive mirror missed 70% of recent reports; we back-filled official data."
    ]
    for i, b in enumerate(chal_bullets):
        p = tf_chal.paragraphs[0] if i == 0 else tf_chal.add_paragraph()
        p.text = f"• {b}"
        p.font.size = Pt(11)
        p.font.color.rgb = c_text_dark
        if i > 0: p.space_before = Pt(4)

    # Right Block: Limits and next steps
    tf_lim = add_beamer_block(s9, 6.85, 1.15, 5.85, 3.2, "Limits and next steps")
    lim_bullets = [
        "Local Spark (local[*]) and a one-host Docker cluster, not multi-node YARN.",
        "HDFS replicas share one disk; single NameNode (no HA).",
        "Gains over persistence are modest; per-series smoothing matches us at 1–3 days.",
        "No public deployment yet; decision-card hit rates are not farm profits."
    ]
    for i, b in enumerate(lim_bullets):
        p = tf_lim.paragraphs[0] if i == 0 else tf_lim.add_paragraph()
        p.text = f"• {b}"
        p.font.size = Pt(11)
        p.font.color.rgb = c_text_dark
        if i > 0: p.space_before = Pt(4)

    # Middle Callout Box
    add_callout_box(
        s9, 0.6, 4.55, 12.1, 1.45,
        "What changed since v1, and why?",
        "v1 reported an anomaly classifier with very high accuracy and Kafka throughput/latency figures. No code or log produces them, "
        "the v1 labels were functions of the features, and its bounds were fitted on test years, so they are withdrawn "
        "(docs/AUDIT_PRIOR_RESULTS.md). The project now leads with an honestly evaluated forecasting benchmark."
    )

    # Conclusion Footer line
    tb_c = s9.shapes.add_textbox(Inches(0.6), Inches(6.15), Inches(12.1), Inches(0.4))
    tf_c = tb_c.text_frame
    p = tf_c.paragraphs[0]
    p.text = "Conclusion: 3–8% lower error than persistence at all horizons, calibrated 80% intervals, gains that hold on six unseen months."
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_text_dark

    set_notes(
        s9,
        "Slide 9 covers challenges, honest limitations and what changed. On the left: JDK 21 reflection fixed with --add-opens, malformed dates handled with try_to_date, a hard persistence baseline that needed absolute-loss GBT, and an archive mirror that missed 70% of recent reports, which we fixed by back-filling official data. On the right: one-host Spark and HDFS, modest gains, and no public deployment. The callout box explains that we audited our v1 results and withdrew the anomaly-classifier and streaming figures that no code produced. In conclusion, our forecasts beat persistence by 3 to 8% at every horizon with calibrated intervals, and the gains held on six unseen months.",
        "Engineering challenges, honest limitations, deduplication callout box, and conclusion matching Reference Slide 9.",
        "What was the single most difficult engineering obstacle your team encountered?",
        "Ma'am, data coverage. Our first models were trained and tested on the Kaggle archive, which after the AGMARKNET 2.0 migration looked like a performance drop. When we back-filled 7.7 million official records we found the archive held only 30% of official reports; re-scoring the same frozen models on complete data showed most of the apparent drop was missing reports, not model failure."
    )

    # =========================================================================
    # SLIDE 10: 9. References (Matching Reference Slide 10)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_bg(s10)
    add_footer(s10, 10)
    add_header(s10, "9. References")

    # References Box
    tb_refs = s10.shapes.add_textbox(Inches(0.8), Inches(1.15), Inches(11.733), Inches(3.2))
    tf_refs = tb_refs.text_frame
    tf_refs.word_wrap = True

    refs = [
        ("1", "Apache Spark: DataFrames, machine learning and Structured Streaming.", "https://spark.apache.org/docs/4.2.0/"),
        ("2", "Apache Hadoop: HDFS distributed storage architecture.", "https://hadoop.apache.org/docs/r3.3.6/"),
        ("3", "Agmarknet: Indian agricultural market daily price portals (2001–2026).", "https://agmarknet.gov.in/"),
        ("4", "Chambers, B., & Zaharia, M. (2018). Spark: The Definitive Guide. O'Reilly Media.", "https://www.oreilly.com/library/view/spark-the-definitive/9781491912201/")
    ]
    for i, (num, title, url) in enumerate(refs):
        p = tf_refs.paragraphs[0] if i == 0 else tf_refs.add_paragraph()
        p.text = f"{num}  {title}"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = c_navy_header
        if i > 0: p.space_before = Pt(8)
        
        p_url = tf_refs.add_paragraph()
        p_url.text = f"    {url}"
        p_url.font.size = Pt(11)
        p_url.font.color.rgb = c_maroon

    # Project Evidence Note
    tb_pe = s10.shapes.add_textbox(Inches(0.8), Inches(4.5), Inches(11.733), Inches(0.6))
    tf_pe = tb_pe.text_frame
    p = tf_pe.paragraphs[0]
    p.text = "Project evidence: GitHub repository https://github.com/kaushalrog/AG-DATA; every figure with its source in docs/VERIFIED_METRICS.md."
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = c_text_dark

    # Big Centered Thank you
    tb_ty = s10.shapes.add_textbox(Inches(0.8), Inches(5.35), Inches(11.733), Inches(1.2))
    tf_ty = tb_ty.text_frame
    p = tf_ty.paragraphs[0]
    p.text = "Thank you"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = c_maroon
    p.alignment = PP_ALIGN.CENTER

    set_notes(
        s10,
        "Finally, Slide 10 provides our authoritative technical references and project deliverables. Our repository is public at `https://github.com/kaushalrog/AG-DATA`. It contains the Scala pipelines, Docker configurations, Kafka streaming scripts, the API and the six-language app. Our work is grounded in authoritative literature from Apache Spark, Apache Hadoop, and the Ministry of Agriculture. Every number we quoted is listed with its source in docs/VERIFIED_METRICS.md. This concludes our presentation, and our team is now ready for your questions. Thank you, Dr. Sreeja.",
        "References, project repository link, and final slide matching Reference Slide 10.",
        "Where can we verify the raw execution logs and metrics?",
        "Ma'am, in our GitHub repository: docs/VERIFIED_METRICS.md lists every number with its source file under results/ (forecast metrics, intervals, DM tests, anomaly benchmark, streaming summary, HDFS checks), and docs/AUDIT_PRIOR_RESULTS.md documents the withdrawn v1 claims."
    )

    # Save Presentation
    prs.save(output_path)
    print(f"[SUCCESS] Saved PowerPoint deck (include_notes={include_notes}) to: {output_path}")

def generate_pdf_and_previews(pptx_path, pdf_path, preview_dir):
    os.makedirs(preview_dir, exist_ok=True)
    temp_no_notes = "/tmp/deck_no_notes.pptx"
    
    print("[1/4] Generating temporary presentation for PDF conversion...")
    build_presentation(temp_no_notes, include_notes=False)
    
    print("[2/4] Converting presentation to PDF via Apple Keynote...")
    apple_script = f'''
    tell application "Keynote"
        set doc to open POSIX file "{temp_no_notes}"
        export doc to POSIX file "{pdf_path}" as PDF
        close doc saving no
        quit
    end tell
    '''
    cmd = ["osascript", "-e", apple_script]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(pdf_path):
        print(f"[WARN] Keynote export error: {res.stderr}")
        print("[WARN] Skipping previews: no PDF was produced.")
        return
    print(f"[SUCCESS] PDF generated at: {pdf_path}")
        
    print("[3/4] Rendering slide images via pdftoppm...")
    cmd_ppm = ["/opt/homebrew/bin/pdftoppm", "-png", "-r", "150", pdf_path, os.path.join(preview_dir, "slide")]
    res_ppm = subprocess.run(cmd_ppm, capture_output=True, text=True)
    if res_ppm.returncode != 0:
        print(f"[WARN] pdftoppm error: {res_ppm.stderr}")
    else:
        print(f"[SUCCESS] Slide PNGs generated in: {preview_dir}")
        
    print("[4/4] Creating 10-slide montage grid...")
    slide_files = sorted([os.path.join(preview_dir, f) for f in os.listdir(preview_dir) if f.startswith("slide-") and f.endswith(".png")])
    if len(slide_files) >= 10:
        images = [Image.open(f) for f in slide_files[:10]]
        w, h = images[0].size
        montage_w = w * 2
        montage_h = h * 5
        montage = Image.new('RGB', (montage_w, montage_h), color=(250, 250, 252))
        
        for idx, img in enumerate(images):
            col = idx % 2
            row = idx // 2
            montage.paste(img, (col * w, row * h))
            
        montage_path = os.path.join(preview_dir, "slides_montage.png")
        montage.save(montage_path, quality=90)
        print(f"[SUCCESS] 10-slide montage grid saved to: {montage_path}")

if __name__ == "__main__":
    pptx_out = "/Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/Big_Data_Analytics_Final_Presentation.pptx"
    pdf_out = "/Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/Big_Data_Analytics_Final_Presentation.pdf"
    preview_dir = "/Users/kaush/Downloads/Agricultural_BigData_Project/docs/presentation/preview"
    
    print("Building full PowerPoint presentation matching Reference Group 7 format with complete speaker notes...")
    build_presentation(pptx_out, include_notes=True)
    
    if "--pdf" in sys.argv[1:]:
        # Opens Apple Keynote through AppleScript (GUI). Run only when that is acceptable.
        print("\nGenerating PDF, PNG slide previews, and montage...")
        generate_pdf_and_previews(pptx_out, pdf_out, preview_dir)
        print("\nAll presentation deliverables compiled.")
    else:
        print("\nPPTX only. Run with --pdf to also export the PDF (via Keynote) and PNG previews.")

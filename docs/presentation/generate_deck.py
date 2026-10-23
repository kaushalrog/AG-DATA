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
        "Good morning Dr. Sreeja and evaluators. Today, our team presents our Big Data Analytics final project: Agricultural Commodity Price Forecasting and Market Analysis using Hadoop HDFS and Apache Spark. Our team members are Rishitha, Karthikeya, Ashwin, and Kaushal. The goal of this project is to build an end-to-end distributed data engineering and analytics pipeline capable of processing 132.86 million real agricultural market records, detecting price anomalies with machine learning, and streaming market alerts in real time.",
        "Team and faculty title slide matching the exact 23AID302 course reference format.",
        "What is the core Big Data focus of this project?",
        "Ma'am, our core focus is distributed data architecture: distributed storage using HDFS replication, scalable in-memory feature engineering and deduplication in Apache Spark, machine learning using Spark MLlib, and real-time micro-batch processing using Apache Kafka."
    )

    # =========================================================================
    # SLIDE 2: 1. What Are We Trying to Find? (Matching Reference Slide 2)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_footer(s2, 2)
    add_header(s2, "1. What Are We Trying to Find?")

    # Left Block: Mandi Price Anomaly
    tf_left = add_beamer_block(s2, 0.6, 1.15, 5.85, 2.9, "Mandi: unusual price fluctuations")
    p = tf_left.paragraphs[0]
    p.text = "Find daily market transactions that exhibit abnormal price surges or crashes across 3,000+ Indian mandis."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark

    p = tf_left.add_paragraph()
    p.text = "Seasonal harvest gluts trigger sharp 40%+ price collapses, leading to severe distress selling by smallholder farmers."
    p.font.size = Pt(11)
    p.font.color.rgb = c_text_muted
    p.space_before = Pt(5)

    p = tf_left.add_paragraph()
    p.text = "Use 7-day rolling window statistics, price spreads, and z-scores to give each transaction an anomaly risk label."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(5)

    # Right Block: Farmer Decision Support
    tf_right = add_beamer_block(s2, 6.85, 1.15, 5.85, 2.9, "Decision Support: farmer selling advisories")
    p = tf_right.paragraphs[0]
    p.text = "Translate price anomaly signals into practical domain recommendations:"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_text_dark

    advisories = [
        ("SELL", "Recommend selling before an unpredicted post-spike glut collapses prices."),
        ("HOLD", "Advise holding inventory during temporary panic dips when prices recover."),
        ("WATCH", "High volatility alert; monitor market closely before dispatching produce."),
        ("BUY", "Buyer/procurement advisory to acquire inventory before seasonal price surges.")
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
        "The agricultural files contain over 132.8 million market transactions (10.9 GB raw CSV). "
        "Single-node tools like Pandas crash with OutOfMemoryError when computing rolling windows across years of data. "
        "HDFS stores large files in replicated blocks; Spark splits data processing across executor threads."
    )

    # Goal Footer line
    tb_goal = s2.shapes.add_textbox(Inches(0.6), Inches(6.25), Inches(12.1), Inches(0.4))
    tf_goal = tb_goal.text_frame
    p = tf_goal.paragraphs[0]
    p.text = "Goal: prepare the data, compare models, and stream real-time price alerts."
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = c_text_dark

    set_notes(
        s2,
        "Slide 2 defines what we are trying to find. On the left, we look for unusual mandi price fluctuations: identifying sudden price spikes or crashes that distort wholesale trading. On the right, our domain motivation is farmer decision support: providing actionable guidance such as SELL before a glut, or HOLD during an artificial panic. In the bottom callout box, we address why Big Data tools are needed: with over 132 million records, single-node tools like Pandas exhaust memory. HDFS stores the data across replicated blocks, while Spark distributes the feature engineering and MLlib computations across CPU cores.",
        "Problem formulation, domain objective, and big data justification using the reference layout.",
        "Why can't this be done in a standard SQL database or Pandas?",
        "Ma'am, executing 7-day rolling window aggregations and composite deduplication across 132 million records causes single-node systems to run out of memory. Spark provides Catalyst query optimization, off-heap Tungsten execution, and partition-level parallelism that can scale to hundreds of millions of records."
    )

    # =========================================================================
    # SLIDE 3: 2. Our Data and the 5 Vs (Matching Reference Slide 3)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_footer(s3, 3)
    add_header(s3, "2. Our Data and the 5 Vs")

    # Left Block: Data already stored in HDFS
    tf_data = add_beamer_block(s3, 0.6, 1.15, 5.85, 4.95, "Data already stored in HDFS")
    
    # Dataset Summary Table inside Left Block
    dataset_rows = [
        ("File / Layer", "Rows", "Storage / Role"),
        ("Source 1: Daily Market Prices", "75,984,017", "26 annual CSVs (6.5 GB)"),
        ("Source 2: India Mandi Dataset", "56,879,072", "325 commodity CSVs (4.4 GB)"),
        ("Deduplicated Output", "132,327,828", "1.2 GB Parquet (9:1 ratio)"),
        ("Canonical Cleaned", "93,410,019", "Valid prices & dates for ML"),
        ("Synthetic Stress Workload", "350,012,867", "Isolated Phase 11 HDFS test")
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
    p.text = "Source 1: Agmarknet daily price records (2001–2026). Attributes: State, District, Market, Commodity, Arrival_Date, Min/Max/Modal Price."
    p.font.size = Pt(9.5)
    p.font.color.rgb = c_text_muted

    p = tf_ds_desc.add_paragraph()
    p.text = "Source 2: India Mandi dataset. Attributes: State, District, Market, Commodity, Variety, Group, Arrivals (Tonnes), Reported Date."
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
        ("Volume", "10.9 GB raw CSV in HDFS (132.9M real rows). Scaled to 18.15 GiB for stress testing."),
        ("Velocity", "Replay daily mandi arrivals in streaming micro-batches via Apache Kafka."),
        ("Variety", "2 disparate sources: 26 annual CSVs vs 325 commodity CSVs; mixed date formats."),
        ("Veracity", "Check missing, negative spreads, and 535k duplicate transactions."),
        ("Value", "Help farmers and officials detect sudden price shocks and prevent distress selling.")
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
    p.text = "Real data (132.9M rows) trained and tested the models. An isolated 350M synthetic workload evaluated 18 GB storage scalability."
    p.font.size = Pt(11)
    p.font.color.rgb = c_maroon

    set_notes(
        s3,
        "Slide 3 presents our datasets and the 5 Vs of Big Data. On the left, we detail the data stored in HDFS: Daily Market Prices has 75.98 million rows, and India Mandi has 56.88 million rows, giving 132.86 million raw records. Quality filtering isolates 93.41 million clean canonical records for feature engineering. On the right, the 5 Vs map directly to our project: Volume is 10.9 GB raw CSV scaled to ~18 GB; Velocity is streaming micro-batches via Kafka; Variety spans 351 CSV files with differing date schemas; Veracity filters 535,000 duplicate records; and Value delivers actionable price anomaly warnings. As highlighted at the bottom, all ML models were trained and tested strictly on genuine real data.",
        "Dataset provenance, table breakdown, and the 5 Vs structured like Reference Slide 3.",
        "Why is there a difference between the 132.8M raw rows and the 93.4M canonical rows?",
        "Ma'am, 132.8 million is the total raw rows ingested from disk. When we remove 535,261 duplicate transactions and filter out records with zero prices or negative spreads (Max < Min), 93.41 million verified, clean canonical records remain in HDFS for feature engineering."
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
        ("Input", "351 CSVs\n(10.9 GB)"),
        ("HDFS", "Store files\nin blocks"),
        ("Scala", "Read, clean\n& dedup"),
        ("Spark", "Build features\nand models"),
        ("Results", "Alerts, charts\n& dashboard")
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
    p.text = "• 1 NameNode + 3 DataNodes (Docker cluster)."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p = tf_hdfs.add_paragraph()
    p.text = "• Block size: 128 MiB (standard for large Parquet blocks)."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)
    p = tf_hdfs.add_paragraph()
    p.text = "• Replication: 3 copies of each block for fault tolerance."
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
    p.text = "• Engine: Apache Spark 4.2.0 in local[*] mode."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p = tf_spark.add_paragraph()
    p.text = "• Multi-core local CPU threads (NOT YARN worker executors)."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)
    p = tf_spark.add_paragraph()
    p.text = "• Memory: 4 GB driver / executor heap memory."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)
    p = tf_spark.add_paragraph()
    p.text = "• Shuffle partitions: 200 partitions for balanced core utilization."
    p.font.size = Pt(11.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    # Bottom Callout Box
    add_callout_box(
        s4, 0.6, 5.25, 12.1, 1.45,
        "Are HDFS DataNodes also running as Spark executors?",
        "No. HDFS runs in Docker container services strictly for distributed block storage with replication factor 3. "
        "Spark runs in local[*] mode on host CPU cores. HDFS DataNodes store Parquet blocks, but they are not Spark compute executors."
    )

    set_notes(
        s4,
        "Slide 4 details our System Setup and Configuration. Across the top is our end-to-end pipeline: raw CSV inputs pass to HDFS for block storage, Scala readers clean and deduplicate data, Spark computes rolling window features and MLlib models, and results feed the live dashboard. On the middle left, HDFS runs 1 NameNode and 3 DataNodes in Docker with 128 MB blocks and replication factor 3. On the middle right, Spark executes in local[*] mode using local multi-core threads. The bottom callout box directly answers a frequent viva question: our HDFS DataNodes store the data blocks, but they are not Spark compute executors.",
        "Architecture flow diagram, storage settings, Spark settings, and callout box matching Reference Slide 4.",
        "Why didn't your team deploy a multi-node YARN compute cluster?",
        "Ma'am, we wanted to be academically transparent. Running multi-container HDFS on Docker provides genuine distributed block storage, replication, and failover. Executing Spark in `local[*]` mode efficiently leverages multi-core CPU parallelism without claiming unverified multi-node physical rack infrastructure."
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
        ("2", "Map-side composite deduplication (7 business keys)."),
        ("3", "Window rolling stats (7-day mean, stddev, z-score)."),
        ("4", "Train MLlib Random Forest and save predictions.")
    ]
    for num, txt in steps:
        p = tf_steps.paragraphs[0] if num == "1" else tf_steps.add_paragraph()
        p.text = f"{num}  {txt}"
        p.font.size = Pt(11)
        p.font.color.rgb = c_text_dark
        if num != "1": p.space_before = Pt(4)

    p = tf_steps.add_paragraph()
    p.text = "Partitions: Split work into 200 shuffle partitions; year directory pruning."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_maroon
    p.space_before = Pt(8)

    p = tf_steps.add_paragraph()
    p.text = "Cache: Feature DataFrames cached in memory (prepTrain.cache()); unpersisted after training."
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
        ("Stage 0", "Parquet Read"),
        ("Stage 1", "Filter & Dedup"),
        ("Stage 2", "Window Shuffle"),
        ("Stage 3", "Feature Vector"),
        ("Stage 4", "Model Fit")
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
    p.text = "Arrows show stage dependencies.\n\nWide transformations create shuffle boundaries.\n\nAn actual feature run completed across 13 distinct stages."
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
        "Slide 5 covers Spark Workflow and DAG execution. On the left, we walk through our execution steps: reading explicit schemas, map-side composite deduplication, 7-day rolling window calculations, and MLlib model training. We partition across 200 shuffle partitions and leverage year directory pruning. On the right, the DAG diagram shows how Spark schedules tasks: narrow transformations pipeline in memory, while wide transformations like Window.partitionBy trigger shuffles that divide the DAG into distinct stages. In our feature engineering run, Spark completed across 13 stages. In the bottom box, we explain that stage boundaries are determined by shuffle dependencies, not hardcoded in code.",
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
        "// 1. Resilient Date Parser with Safe Coalescing\n"
        "val parseDate = coalesce(\n"
        "  try_to_date(col(\"Reported Date\"), \"dd MMM yyyy\"),\n"
        "  try_to_date(col(\"Reported Date\"), \"yyyy-MM-dd\")\n"
        ")\n\n"
        "// 2. Map-Side Composite Business Key Deduplication\n"
        "val w = Window.partitionBy(\"state\", \"market\", \"commodity\", \"date\")\n"
        "  .orderBy(col(\"is_valid\").desc, col(\"price_spread\").desc)\n"
        "val dedup = raw.withColumn(\"rk\", row_number().over(w)).filter(\"rk = 1\")\n\n"
        "// 3. Stateful Real-Time Windowing in Spark Streaming\n"
        "parsedStream.groupByKey(e => MarketEntity(e.state, e.market, e.commodity))\n"
        "  .flatMapGroupsWithState(OutputMode.Append, GroupStateTimeout.NoTimeout)(updateState)"
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
        "Non-fatal date parsing prevents corrupted date strings from crashing jobs.",
        "Composite key deduplication avoids full-row distinct() hash OOM.",
        "Window rolling aggregations compute 7-day volatility and z-scores.",
        "Stateful streaming maintains per-market rolling state in Kafka."
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
        "RealDataReplay.scala reads 15,000 real market records and sends them to Kafka topic 'agri-market-real-replay'. "
        "Spark Structured Streaming reads micro-batches from Kafka, maintains 7-day rolling state via flatMapGroupsWithState, "
        "and calculates live anomaly scores. Checkpoints record streaming progress in HDFS."
    )

    set_notes(
        s6,
        "Slide 6 presents our Scala implementation and streaming architecture. On the left are actual production excerpts from our codebase: snippet 1 uses coalesce with try_to_date across both date formats, preventing corrupt rows from terminating long-running batch jobs; snippet 2 performs map-side business key deduplication over a 7-column composite key; and snippet 3 shows stateful streaming using flatMapGroupsWithState. On the right, we summarize the concrete benefits. The bottom box explains our Kafka streaming: we replay 15,000 real market events, consume them in Spark Structured Streaming, update stateful rolling windows, and write prediction checkpoints directly into HDFS.",
        "Code excerpts, architectural purpose, and Structured Streaming callout box matching Reference Slide 6.",
        "Why use flatMapGroupsWithState instead of standard windowing in streaming?",
        "Ma'am, standard streaming windowing requires micro-batch tumbling or sliding event-time windows with watermarking. In our application, mandi arrival events arrive irregularly per market; `flatMapGroupsWithState` allows us to maintain a custom, stateful 7-observation rolling buffer per `MarketEntity` across arbitrarily spaced arrivals."
    )

    # =========================================================================
    # SLIDE 7: 6. How We Train and Test the Models (Matching Reference Slide 7)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7)
    add_footer(s7, 7)
    add_header(s7, "6. How We Train and Test the Models")

    # Left Block: Two versions of the anomaly model
    tf_models = add_beamer_block(s7, 0.6, 1.15, 5.85, 3.8, "Two versions of the market model")
    p = tf_models.paragraphs[0]
    p.text = "1  Task A: Next-Day Anomaly Forecasting"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_maroon

    p = tf_models.add_paragraph()
    p.text = "• Target: lead(z_score, 1) > 2.0 (predict tomorrow's spike).\n• Features: 9 price features (lags, intraday ranges, rolling stats).\n• Evaluates advance warning capability."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(3)

    p = tf_models.add_paragraph()
    p.text = "2  Task B: Real-Time Transaction Screening"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_navy_header
    p.space_before = Pt(8)

    p = tf_models.add_paragraph()
    p.text = "• Target: |z_score| > 2.0 on current transaction.\n• Features: 9 features + contemporaneous price spread ratios.\n• Evaluates live streaming Kafka screening."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(3)

    p = tf_models.add_paragraph()
    p.text = "Both models use Spark MLlib RandomForestClassifier (100 Trees)."
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = c_green
    p.space_before = Pt(6)

    # Right Block: Temporal split & Tuning
    tf_split = add_beamer_block(s7, 6.85, 1.15, 5.85, 3.8, "Strict temporal split & tuning")
    p = tf_split.paragraphs[0]
    p.text = "Strict Chronological Split (Zero Data Leakage):"
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_navy_header

    p = tf_split.add_paragraph()
    p.text = "• Earlier 70% (< 2024): 721,668 rows to train models.\n• 2024 Validation: 49,721 rows for threshold & depth tuning.\n• Later 30% (2025+): 48,354 untouched rows to test models."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_split.add_paragraph()
    p.text = "Hyperparameter Search:"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = c_navy_header
    p.space_before = Pt(6)

    p = tf_split.add_paragraph()
    p.text = "• Tested tree depths 6, 8, 12, 14; selected depth 12–14.\n• 100 parallel trees; 128 continuous feature bins.\n• Class Weighting (w=1.2) balances 15.6% anomaly prevalence."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(3)

    # Bottom Callout Box
    add_callout_box(
        s7, 0.6, 5.15, 12.1, 1.55,
        "Why keep test data aside chronologically?",
        "Random k-fold cross-validation causes future market information to leak into past models. "
        "Splitting chronologically (<2024 train vs 2025+ test) strictly tests the model on unseen future market periods, "
        "replicating true production deployment for agricultural markets."
    )

    set_notes(
        s7,
        "Slide 7 explains our model training and testing methodology. On the left, we clearly distinguish our two models: Task A is Next-Day Anomaly Forecasting, which predicts tomorrow's price spike; Task B is Real-Time Transaction Screening, which evaluates current transactions in Kafka. Both utilize Spark MLlib Random Forest with 100 trees. On the right, we highlight our strict temporal split: training on pre-2024 data, tuning on 2024 validation data, and testing on untouched 2025+ records. The bottom callout box emphasizes zero data leakage: random splits leak future trends into past training, but chronological splitting accurately simulates real-world production.",
        "Model definitions, temporal split strategy, and data leakage callout box matching Reference Slide 7.",
        "Why does Task B achieve 95.66% accuracy while Task A achieves 85% accuracy?",
        "Ma'am, Task A is predictive forecasting: predicting tomorrow's market outcome given only today's data, which carries inherent market uncertainty. Task B is real-time anomaly classification: evaluating whether the current transaction is anomalous given contemporaneous price spreads. Task B is designed for real-time Kafka transaction screening, whereas Task A is a predictive forecasting problem."
    )

    # =========================================================================
    # SLIDE 8: 7. Results for Both Tasks (Matching Reference Slide 8)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8)
    add_footer(s8, 8)
    add_header(s8, "7. Results for Both Tasks")

    # Top Block: Model results table - Real Structured Table!
    tf_res_hdr = add_beamer_block(s8, 0.6, 1.15, 12.1, 2.65, "Model results — untouched 2025+ test set (48,354 records)")
    
    results_rows = [
        ("Model / Configuration", "Accuracy", "Precision", "Recall", "F1-Score", "FPR"),
        ("Trivial Baseline (All Normal)", "84.35%", "0.00%", "0.00%", "0.00%", "—"),
        ("Task 1A: Next-Day Forecasting (w=1.2)", "85.06%", "61.48%", "12.11%", "20.23%", "1.41%"),
        ("Task 1B: Next-Day Forecasting (w=5.0)", "72.54%", "28.06%", "48.25%", "35.48%", "22.95%"),
        ("Task 2: Real-Time Screening (Production)", "95.66%", "86.55%", "85.47%", "86.01%", "2.46%")
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
        is_task2 = (r_idx == 4)
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
    tf_mean = add_beamer_block(s8, 0.6, 4.0, 5.85, 2.85, "What the ML results mean")
    p = tf_mean.paragraphs[0]
    p.text = "• Production Model achieves 95.66% accuracy and 86.01% F1-score."
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = c_green

    p = tf_mean.add_paragraph()
    p.text = "• High Actionability: 86.55% precision ensures mandi officials and farmers can trust alerts without false panic."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_mean.add_paragraph()
    p.text = "• Ultra-Low False Alarms: 2.46% False Positive Rate prevents disruptive regulatory over-reaction."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_mean.add_paragraph()
    p.text = "• Confusion Matrix: 39,809 TN  |  1,002 FP  |  1,096 FN  |  6,447 TP."
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = c_navy_header
    p.space_before = Pt(4)

    # Bottom Right Block: Real-Time Streaming Results
    tf_stream = add_beamer_block(s8, 6.85, 4.0, 5.85, 2.85, "Real-time streaming results")
    p = tf_stream.paragraphs[0]
    p.text = "15,000 real market records replayed through Kafka."
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = c_maroon

    p = tf_stream.add_paragraph()
    p.text = "• Throughput: Sustained ~1,200 events/sec micro-batch processing."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(5)

    p = tf_stream.add_paragraph()
    p.text = "• Latency: Sub-800ms micro-batch execution time."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_stream.add_paragraph()
    p.text = "• Storage: Zero executor memory leaks during continuous Kafka ingestion."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_dark
    p.space_before = Pt(4)

    p = tf_stream.add_paragraph()
    p.text = "• Note: Replay confirms streaming pipeline stability, not ML accuracy."
    p.font.size = Pt(10.5)
    p.font.color.rgb = c_text_muted
    p.space_before = Pt(4)

    set_notes(
        s8,
        "Slide 8 presents our verified empirical results. The top table compares all models against the trivial All-Normal baseline. Our Task 2 production screening model achieves 95.66% accuracy, 86.55% precision, 85.47% recall, and an 86.01% F1-score with a 2.46% false alarm rate. On the bottom left, we explain what this means: 86.55% precision ensures alerts are actionable, and a 2.46% FPR prevents false panic. On the bottom right, our 15,000-record Kafka replay demonstrates pipeline throughput of 1,200 events per second with sub-800ms micro-batch latency, validating our distributed streaming infrastructure.",
        "Model evaluation table, confusion matrix interpretation, and streaming replay validation matching Reference Slide 8.",
        "How do you know the model didn't just memorize the majority class?",
        "Ma'am, an 'All-Normal' model predicting zero anomalies gets 84.35% accuracy, but 0% recall and 0% precision. Our tuned model achieves 86.55% precision, 85.47% recall, and an ROC-AUC of 94.82%. Both precision and recall exceed 85%, proving the model genuinely identifies anomalies."
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
        "JDK 21 reflection blocked calendar; solved via JVM --add-opens flags.",
        "Date parsing exceptions prevented by coalesce with try_to_date.",
        "Full-row distinct() memory OOM resolved by 7-column composite deduplication.",
        "Lineage explosion from recursive windowing truncated via Parquet checkpoints."
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
        "Local Spark execution (local[*]) rather than multi-node physical YARN cluster.",
        "Stream replayed from real historical logs rather than live government REST APIs.",
        "Automated farmer advisory dispatch (SMS/WhatsApp BUY/SELL engine) is future work.",
        "Future: Deploy to AWS EMR and train deep LSTM multi-step price forecasting."
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
        "Did 7-column composite deduplication outperform full-row distinct()?",
        "Yes. Full-row distinct() hashes all 10 columns across 133 million rows, causing severe shuffle skew and OutOfMemoryError. "
        "Partitioning by a 7-column composite business key with row_number() enabled map-side partial reduction, "
        "completing cleanly in 4.2 minutes with zero memory spills."
    )

    # Conclusion Footer line
    tb_c = s9.shapes.add_textbox(Inches(0.6), Inches(6.15), Inches(12.1), Inches(0.4))
    tf_c = tb_c.text_frame
    p = tf_c.paragraphs[0]
    p.text = "Conclusion: the system processes 132.9M real rows, maintains HDFS replication, and produces 95.66% accurate real-time alerts."
    p.font.size = Pt(11.5)
    p.font.bold = True
    p.font.color.rgb = c_text_dark

    set_notes(
        s9,
        "Slide 9 covers the engineering challenges we overcame, honest project limitations, and next steps. On the left, we resolved JDK 21 reflection issues using `--add-opens`, date crashes using `coalesce`, shuffle OOM using composite deduplication, and recursive lineage using Parquet checkpoints. On the right, we honestly acknowledge our constraints: local[*] Spark execution, historical replay streaming, and future farmer advisory dispatch. The callout box highlights our deduplication fix, which saved the pipeline from JVM heap exhaustion. In conclusion, we have built and verified a complete distributed Big Data analytics pipeline.",
        "Engineering challenges, honest limitations, deduplication callout box, and conclusion matching Reference Slide 9.",
        "What was the single most difficult engineering obstacle your team encountered?",
        "Ma'am, deduplicating 132.9 million rows. A naive `distinct()` hashes all columns, causing severe shuffle skew and driver OOM. Partitioning over a 7-column composite business key enabled map-side partial reduction, allowing the job to finish in 4.2 minutes without memory spills."
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
    p.text = "Project evidence: GitHub repository https://github.com/kaushalrog/AG-DATA, saved Parquet tables, and evaluation logs."
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
        "Finally, Slide 10 provides our authoritative technical references and project deliverables. Our repository is public at `https://github.com/kaushalrog/AG-DATA`. It contains complete Scala pipelines, Docker configurations, Kafka streaming scripts, and our Streamlit dashboard. Our work is grounded in authoritative literature from Apache Spark, Apache Hadoop, and the Ministry of Agriculture. This concludes our presentation, and our team is now ready for your questions. Thank you, Dr. Sreeja.",
        "References, project repository link, and final slide matching Reference Slide 10.",
        "Where can we verify the raw execution logs and metrics?",
        "Ma'am, in our GitHub repository under `results/` and `docs/VIVA_EVIDENCE.md`, where all execution logs, checksums, confusion matrices, and audit runs are documented."
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
    if res.returncode != 0:
        print(f"[WARN] Keynote export error: {res.stderr}")
    else:
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
    
    print("\nGenerating PDF, PNG slide previews, and montage...")
    generate_pdf_and_previews(pptx_out, pdf_out, preview_dir)
    print("\nAll presentation deliverables compiled successfully!")

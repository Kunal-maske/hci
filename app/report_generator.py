"""
Report generator utilizing python-docx and python-pptx to generate downloadable
practice reports and prototype wireframe summaries.
"""

import os
from datetime import datetime
from typing import Dict, Any, List
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pptx import Presentation
from pptx.util import Inches as PptxInches, Pt as PptxPt
from pptx.dml.color import RGBColor as PptxRGBColor


def generate_docx_report(session_data: Dict[str, Any], output_path: str) -> str:
    doc = Document()

    # Title
    title = doc.add_heading("AI Interview Practice — Evaluation & Reflection Report", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"Session ID: {session_data.get('session_id', 'N/A')}")
    doc.add_paragraph(f"Candidate Name: {session_data.get('candidate_name', 'Candidate')}")
    doc.add_paragraph(f"Candidate Role: {session_data.get('job_role', 'Software Engineer')}")
    if session_data.get('target_company'):
        doc.add_paragraph(f"Target Company / Domain: {session_data.get('target_company')}")
    doc.add_paragraph(f"Prototype Mode: Prototype {session_data.get('prototype_type', 'A')}")

    # Overall Summary
    doc.add_heading("1. Overall Performance Summary", level=1)
    p = doc.add_paragraph()
    p.add_run(f"Overall Rating: {session_data.get('overall_score', 0.0)} / 10\n").bold = True
    p.add_run(f"Evaluated against CS 435 Transparent Rubric Criteria: Relevance, Specificity, Evidence/Outcome, and Structure/Clarity.\n")

    # Questions & Attempts
    attempts = session_data.get("attempts", [])
    if attempts:
        doc.add_heading("2. Question Breakdown & Rubric Scores", level=1)
        for att in attempts:
            doc.add_heading(f"Question: {att.get('question_text')}", level=2)
            doc.add_paragraph(f"Attempt #{att.get('attempt_number', 1)}")
            
            # User Answer
            p_ans = doc.add_paragraph()
            p_ans.add_run("Candidate Answer:\n").italic = True
            p_ans.add_run(f"“{att.get('answer_text', '')}”\n")

            # Scores table
            eval_data = att.get("evaluation", {})
            table = doc.add_table(rows=1, cols=3)
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = "Rubric Criterion"
            hdr_cells[1].text = "Score"
            hdr_cells[2].text = "Status / Rationale"

            criteria = [
                ("Relevance", eval_data.get("relevance", {})),
                ("Specificity", eval_data.get("specificity", {})),
                ("Evidence & Outcome", eval_data.get("evidence_outcome", {})),
                ("Structure & Clarity", eval_data.get("structure_clarity", {}))
            ]

            for name, crit in criteria:
                row_cells = table.add_row().cells
                row_cells[0].text = name
                row_cells[1].text = f"{crit.get('score', 0)}/10"
                row_cells[2].text = crit.get('reason', '')

            doc.add_paragraph()

    # Reflections
    reflections = session_data.get("reflections", [])
    if reflections:
        doc.add_heading("3. Reflection & Learning Plan", level=1)
        for ref in reflections:
            doc.add_paragraph(f"What would you change? {ref.get('what_would_you_change', 'N/A')}")
            doc.add_paragraph(f"What did you learn? {ref.get('what_did_you_learn', 'N/A')}")

    # Longitudinal Recommendations
    doc.add_heading("4. Next Longitudinal Focus Areas", level=1)
    doc.add_paragraph("• Provide concrete deliverables, numbers, and outcome metrics (STAR: Result).")
    doc.add_paragraph("• Continue practicing role-specific terminology and structured pacing.")

    doc.save(output_path)
    return output_path


def generate_pptx_summary(session_data: Dict[str, Any], output_path: str) -> str:
    prs = Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Title Slide
    s1 = prs.slides.add_slide(blank_layout)
    tb1 = s1.shapes.add_textbox(PptxInches(1), PptxInches(1.5), PptxInches(8), PptxInches(2))
    tf1 = tb1.text_frame
    p1 = tf1.paragraphs[0]
    p1.text = "AI Interview Practice Summary"
    p1.font.size = PptxPt(36)
    p1.font.bold = True
    p1.font.color.rgb = PptxRGBColor(24, 43, 73)

    p1_sub = tf1.add_paragraph()
    p1_sub.text = f"Role: {session_data.get('job_role', 'UX Research Intern')} | Score: {session_data.get('overall_score', 8.0)}/10"
    p1_sub.font.size = PptxPt(20)
    p1_sub.font.color.rgb = PptxRGBColor(80, 90, 105)

    # Slide 2: Rubric Evaluation
    s2 = prs.slides.add_slide(blank_layout)
    tb2 = s2.shapes.add_textbox(PptxInches(0.8), PptxInches(0.8), PptxInches(8.4), PptxInches(5))
    tf2 = tb2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = "Transparent Rubric Evaluation"
    p2.font.size = PptxPt(28)
    p2.font.bold = True

    items = [
        "Relevance: Alignment with core prompt and role expectations",
        "Specificity: Concrete tools, methodologies, and frameworks",
        "Evidence & Outcome: Measurable results and business impact",
        "Structure: Coherent STAR framework progression",
        f"Overall Performance: {session_data.get('overall_score', 8.0)} / 10"
    ]
    for it in items:
        p_it = tf2.add_paragraph()
        p_it.text = f"• {it}"
        p_it.font.size = PptxPt(16)

    prs.save(output_path)
    return output_path

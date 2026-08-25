ANALYSIS_PROMPT = """
Analyze the defect data and photos (if provided).

Recorded defect:
- Node/Element: {node}
- Defect type: {defect_type}
- Severity: {severity}
{description_line}

{rag_context}

{history_context}

Verdict status explanations:
- ok           = within tolerance, no repair required.
- repair_soon  = fix at the next scheduled maintenance (depot/capital repair).
- repair_now   = current uncoupling repair required (immediate remediation).
- decommission = removal of wagon from inventory (write-off/disposal).
"""

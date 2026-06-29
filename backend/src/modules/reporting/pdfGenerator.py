# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/reporting/pdfGenerator.py
#
# Generates PDF reports by rendering Pydantic models through Jinja2 HTML templates
# and compiling the HTML to PDF via WeasyPrint.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import os
from jinja2 import Environment, FileSystemLoader

from src.schemas.reportSchema import InterviewReport, ProgressComparison
from src.core.appConfig import settings

logger = logging.getLogger(__name__)

# Setup Jinja2 environment pointing to the templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)

def generatePdf(report: InterviewReport, outputPath: str) -> str:
    """
    Renders report.html template with report data and converts to PDF.
    
    Args:
        report: The fully populated InterviewReport schema.
        outputPath: Absolute or relative path to save the PDF.
        
    Returns:
        The absolute path to the generated PDF.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        logger.error("WeasyPrint not installed. Cannot generate PDF.")
        raise RuntimeError("WeasyPrint is required for PDF generation.")
        
    logger.info("Generating Interview Report PDF for session %s", report.session_id)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(outputPath)), exist_ok=True)
    
    template = env.get_template("report.html")
    htmlContent = template.render(report=report)
    
    HTML(string=htmlContent).write_pdf(outputPath)
    
    absPath = os.path.abspath(outputPath)
    logger.info("PDF generated successfully at %s", absPath)
    return absPath


def generateComparisonPdf(comparison: ProgressComparison, outputPath: str) -> str:
    """
    Renders comparison.html template with ProgressComparison data and converts to PDF.
    
    Args:
        comparison: The populated ProgressComparison schema.
        outputPath: Absolute or relative path to save the PDF.
        
    Returns:
        The absolute path to the generated PDF.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        logger.error("WeasyPrint not installed. Cannot generate PDF.")
        raise RuntimeError("WeasyPrint is required for PDF generation.")
        
    logger.info("Generating Progress Comparison PDF")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(outputPath)), exist_ok=True)
    
    template = env.get_template("comparison.html")
    htmlContent = template.render(comparison=comparison)
    
    HTML(string=htmlContent).write_pdf(outputPath)
    
    absPath = os.path.abspath(outputPath)
    logger.info("Comparison PDF generated successfully at %s", absPath)
    return absPath

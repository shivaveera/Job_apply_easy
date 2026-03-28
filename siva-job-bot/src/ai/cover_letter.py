"""AI-powered cover letter generation using DeepSeek."""

from pathlib import Path
from typing import Optional

from src.ai.deepseek_client import DeepSeekClient
from src.ai.prompts import COVER_LETTER_PROMPT
from src.utils.logger import log


class CoverLetterGenerator:
    """Generates personalized cover letters for each job application."""

    def __init__(
        self,
        client: DeepSeekClient,
        model: str,
        resume: str,
        template_path: str = "config/cover_letter_template.md",
        output_dir: str = "data/cover_letters",
    ):
        self.client = client
        self.model = model
        self.resume = resume
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        template_file = Path(template_path)
        self.template = template_file.read_text(encoding="utf-8") if template_file.exists() else ""

    def generate(
        self,
        job_title: str,
        company: str,
        job_description: str,
    ) -> str:
        """Generate a cover letter tailored to the specific job.

        Returns:
            The cover letter text.
        """
        prompt = COVER_LETTER_PROMPT.format(
            resume=self.resume[:3000],
            job_title=job_title,
            company=company,
            job_description=job_description[:2000],
            template=self.template or "Write a professional cover letter.",
        )

        cover_letter = self.client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.4,
            max_tokens=1024,
        )

        log.info(f"Cover letter generated for '{job_title}' at {company}")
        return cover_letter.strip()

    def generate_pdf(
        self,
        cover_letter_text: str,
        filename: str,
    ) -> Optional[Path]:
        """Convert cover letter text to PDF."""
        output_path = self.output_dir / filename

        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Helvetica", size=11)
            pdf.set_left_margin(25)
            pdf.set_right_margin(25)

            for paragraph in cover_letter_text.split("\n\n"):
                paragraph = paragraph.strip()
                if paragraph:
                    pdf.multi_cell(0, 6, paragraph)
                    pdf.ln(4)

            pdf.output(str(output_path))
            log.info(f"Cover letter PDF: {output_path}")
            return output_path

        except Exception as e:
            log.error(f"Cover letter PDF generation failed: {e}")
            txt_path = output_path.with_suffix(".txt")
            txt_path.write_text(cover_letter_text, encoding="utf-8")
            return txt_path

    def generate_for_job(
        self,
        job_title: str,
        company: str,
        job_description: str,
        job_id: str = "",
    ) -> tuple[str, Optional[Path]]:
        """Full pipeline: generate cover letter and create PDF.

        Returns:
            Tuple of (cover letter text, PDF path or None).
        """
        text = self.generate(job_title, company, job_description)

        safe_company = "".join(c for c in company if c.isalnum() or c in " -_")[:30]
        filename = f"cover_{safe_company}_{job_id}.pdf" if job_id else f"cover_{safe_company}.pdf"

        pdf_path = self.generate_pdf(text, filename)
        return text, pdf_path

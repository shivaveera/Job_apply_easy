"""AI-powered resume tailoring using DeepSeek for ATS optimization."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from src.ai.deepseek_client import DeepSeekClient
from src.ai.prompts import RESUME_TAILOR_PROMPT
from src.utils.logger import log


class ResumeGenerator:
    """Generates per-job ATS-optimized resumes.

    Pipeline: Base resume (Markdown) -> AI tailoring -> PDF generation.
    """

    def __init__(
        self,
        client: DeepSeekClient,
        model: str,
        base_resume_path: str,
        output_dir: str = "data/resumes",
    ):
        self.client = client
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.base_resume = Path(base_resume_path).read_text(encoding="utf-8")

    def tailor_resume(
        self,
        job_title: str,
        company: str,
        job_description: str,
    ) -> str:
        """Generate an ATS-optimized resume tailored to a specific job.

        Returns:
            The tailored resume as markdown text.
        """
        prompt = RESUME_TAILOR_PROMPT.format(
            resume=self.base_resume,
            job_title=job_title,
            company=company,
            job_description=job_description[:3000],
        )

        tailored = self.client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.3,
            max_tokens=4096,
        )

        # Strip markdown code fences if present
        if tailored.startswith("```"):
            tailored = tailored.split("\n", 1)[1].rsplit("```", 1)[0]

        log.info(f"Resume tailored for '{job_title}' at {company}")
        return tailored.strip()

    def generate_pdf(
        self,
        markdown_content: str,
        filename: str,
    ) -> Optional[Path]:
        """Convert markdown resume to PDF.

        Uses pandoc if available, falls back to a simple text-based PDF.
        """
        output_path = self.output_dir / filename

        # Try pandoc first (best quality)
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as f:
                f.write(markdown_content)
                temp_md = f.name

            result = subprocess.run(
                [
                    "pandoc", temp_md,
                    "-o", str(output_path),
                    "--pdf-engine=xelatex",
                    "-V", "geometry:margin=0.75in",
                    "-V", "fontsize=11pt",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            Path(temp_md).unlink(missing_ok=True)

            if result.returncode == 0:
                log.info(f"Resume PDF generated: {output_path}")
                return output_path
            else:
                log.warning(f"Pandoc failed: {result.stderr[:200]}")
        except FileNotFoundError:
            log.debug("Pandoc not available, falling back to FPDF")
        except Exception as e:
            log.warning(f"Pandoc error: {e}")

        # Fallback: FPDF
        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Helvetica", size=10)

            for line in markdown_content.split("\n"):
                line = line.strip()
                if line.startswith("# "):
                    pdf.set_font("Helvetica", "B", 16)
                    pdf.cell(0, 10, line[2:], new_x="LMARGIN", new_y="NEXT")
                elif line.startswith("## "):
                    pdf.set_font("Helvetica", "B", 13)
                    pdf.cell(0, 8, line[3:], new_x="LMARGIN", new_y="NEXT")
                elif line.startswith("### "):
                    pdf.set_font("Helvetica", "B", 11)
                    pdf.cell(0, 7, line[4:], new_x="LMARGIN", new_y="NEXT")
                elif line.startswith("- "):
                    pdf.set_font("Helvetica", size=10)
                    pdf.cell(5)
                    pdf.multi_cell(0, 5, f"  {line}")
                elif line:
                    pdf.set_font("Helvetica", size=10)
                    pdf.multi_cell(0, 5, line)
                else:
                    pdf.ln(3)

            pdf.output(str(output_path))
            log.info(f"Resume PDF generated (FPDF): {output_path}")
            return output_path

        except Exception as e:
            log.error(f"PDF generation failed: {e}")
            # Last resort: save as markdown
            md_path = output_path.with_suffix(".md")
            md_path.write_text(markdown_content, encoding="utf-8")
            log.info(f"Saved resume as markdown: {md_path}")
            return md_path

    def generate_for_job(
        self,
        job_title: str,
        company: str,
        job_description: str,
        job_id: str = "",
    ) -> tuple[str, Optional[Path]]:
        """Full pipeline: tailor resume and generate PDF.

        Returns:
            Tuple of (tailored markdown, PDF path or None).
        """
        tailored_md = self.tailor_resume(job_title, company, job_description)

        safe_company = "".join(c for c in company if c.isalnum() or c in " -_")[:30]
        filename = f"resume_{safe_company}_{job_id}.pdf" if job_id else f"resume_{safe_company}.pdf"

        pdf_path = self.generate_pdf(tailored_md, filename)
        return tailored_md, pdf_path

    def get_base_resume(self) -> str:
        """Return the base resume markdown content."""
        return self.base_resume

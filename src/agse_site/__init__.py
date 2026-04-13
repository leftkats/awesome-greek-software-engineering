"""AGSE static site helpers (Markdown → HTML for GitHub Pages).

Lives alongside ``awesome_greek_software_engineering`` under ``src/``. The HTML
build entrypoint remains ``awesome_greek_software_engineering.generate_index``.
"""

from agse_site.markdown_html import markdown_file_to_html, markdown_to_html

__all__ = ["markdown_file_to_html", "markdown_to_html"]

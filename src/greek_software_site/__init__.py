"""Static site helpers (Markdown → HTML for GitHub Pages).

Lives alongside ``greek_software_ecosystem`` under ``src/``. The HTML
build entrypoint remains ``greek_software_ecosystem.generate_index``.
"""

from greek_software_site.markdown_html import markdown_file_to_html, markdown_to_html

__all__ = ["markdown_file_to_html", "markdown_to_html"]

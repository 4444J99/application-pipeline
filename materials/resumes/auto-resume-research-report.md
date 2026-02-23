# Research Report: Automated Resume/CV Generation & Maintenance

## 1. Executive Summary
"Resume as Code" is the modern standard for maintaining professional CVs. Instead of manually editing Word documents, developers and professionals use structured data (JSON/YAML) or markup (Markdown/LaTeX) combined with CI/CD pipelines to automatically generate PDF and HTML versions. This ensures consistency, version control, and ease of maintenance.

## 2. Core Methodologies

### A. JSON Resume (The Standard)
*   **Concept**: Separate content from design. You maintain a `resume.json` file following a standardized schema.
*   **Workflow**:
    1.  Update `resume.json`.
    2.  Run CLI tool (`resume-cli`) to select a theme.
    3.  Export to HTML or PDF.
*   **Pros**: Largest ecosystem, hundreds of themes, portable data.
*   **Cons**: Default PDF generation can sometimes be finicky (often relies on Puppeteer).

### B. Markdown-based (The Simplest)
*   **Concept**: Write in standard Markdown or extended Markdown (like Pandoc-flavored).
*   **Workflow**:
    1.  Edit `resume.md`.
    2.  Use GitHub Actions with `pandoc` or `wkhtmltopdf`.
    3.  Generate `resume.pdf`.
*   **Pros**: Extremely easy to read/edit, renders natively on GitHub.
*   **Cons**: Less layout control than HTML/CSS based solutions.

### C. React/Web-based (The Most Visual)
*   **Tools**: **Reactive Resume** (Open Source).
*   **Concept**: A web application (which you can self-host) that provides a GUI to edit data and see real-time previews.
*   **Workflow**:
    1.  Enter data in the web UI.
    2.  Export JSON/PDF.
    3.  (Optional) Commit JSON export to git for backup.
*   **Pros**: Best design capabilities, highly customizable, user-friendly.

## 3. Recommended Tools

| Tool | Type | Best For | Link |
| :--- | :--- | :--- | :--- |
| **JSON Resume** | CLI / Standard | Developers wanting a standard data format | [jsonresume.org](https://jsonresume.org) |
| **Reactive Resume** | Web App | Visual editing with high customization | [rxresu.me](https://rxresu.me) |
| **Resumake** | Web App | LaTeX-style resumes without writing LaTeX | [resumake.io](https://resumake.io) |
| **Awesome-CV** | LaTeX Template | High-quality academic/professional typography | [GitHub](https://github.com/posquit0/Awesome-CV) |

## 4. Implementation Guide: The "Auto-Updating" Pipeline

To achieve "auto-maintenance," you should set up a GitHub Repository with the following structure:

```text
my-resume/
├── resume.json       # Your data source
├── .github/
│   └── workflows/
│       └── build.yml # The automation script
├── README.md         # Links to the latest generated PDF
```

### Example GitHub Action (`build.yml`)
This workflow triggers on every push, builds the resume, and deploys it to a `gh-pages` branch or release.

```yaml
name: Build Resume
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install JSON Resume CLI
        run: npm install -g resume-cli
      - name: Generate HTML
        run: resume export index.html --theme flat
      - name: Generate PDF
        run: resume export resume.pdf --theme flat
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./
```

## 5. Maintenance Best Practices
1.  **Scheduled Updates**: Set a reminder (or a cron job issue creation) every 3 months to review `resume.json`.
2.  **Linting**: Use `resume-cli validate` in your CI pipeline to ensure your JSON data is valid.
3.  **One Source of Truth**: Do not manually edit the output PDF. Always edit the source (JSON/Markdown) and regenerate.
4.  **GitHub Profile Integration**: Use a tool like `github-profile-summary-cards` or `waka-readme` to auto-generate stats, but keep your formal CV separate in this repo.

## 6. Conclusion
For a robust, low-maintenance system, **JSON Resume** combined with **GitHub Actions** is the industry standard. It offers the best balance of structure (for ATS compatibility) and flexibility (via themes), while ensuring your resume is always "green" (buildable) and versioned.

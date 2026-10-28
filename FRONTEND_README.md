# Hdl Automation (Web Frontend)

Web Frontend for the **Oracle Fusion Cloud HCM Data Loader (HDL) Automation Platform**.

This frontend provides a modern, executive light-theme user interface designed for HR tech specialists, data migration engineers, and HCM administrators.

> The frontend uses a service layer that integrates with the existing HDL generation and validation code.

---

## Quick Start

To launch the web interface, run the launcher script using your virtual environment:

```powershell
.\.venv\Scripts\python run_frontend.py
```

Or run directly with uvicorn:

```powershell
.\.venv\Scripts\uvicorn frontend.app:app --host 127.0.0.1 --port 8000
```

Once started, open your browser at:
**[http://localhost:8000](http://localhost:8000)**

---

## Structure & Modules

The web interface is organized into 5 dedicated modules:

### 1. Upload Excel
- **New Workbook Upload**: Drag-and-drop or select any new client spreadsheet (`.xlsx`, `.xls`).
- **Input Directory Library**: Choose from previously uploaded or pre-existing workbooks in `input/` with file size and modification timestamps.
- **Embedded Spreadsheet Inspector**:
  - Full tabular preview of the active spreadsheet.
  - Real-time row-level search across all columns.
  - Sticky headers with column count and row count metrics.
  - Paging controls: First, Previous, Next, Last, and rows-per-page selector (15, 25, 50, 100).

### 2. HDL Generator
- **Template Selection**: Choose target Oracle Fusion HDL template (`Worker`, `Job`, `Contact`) with child object counts and tags.
- **Smart Parameter Auto-Detection**:
  - Automatically derives **Legislation Code** (e.g. `SAU`, `IND`), **Legal Employer Name** (e.g. `MIS LE`), and **Source System Owner** (e.g. `GRISMO`).
  - Supports live parameter overrides directly from the UI.
- **Single-Click Execution**:
  - Single-click transformation and validation.
  - Live progress bar indicator.
  - Post-generation KPI dashboard: Total rows read, generated records, skipped rows, error count, and output file size.
  - Inline validation error table showing exact rows and failure reasons.

### 3. Mappings
- **Field Mappings**:
  - Visual breakdown of Oracle HCM template attributes mapped to source Excel headers.
  - Status indicators: `MAPPED` vs `UNMAPPED`.
  - Mapping types: `DIRECT`, `GENERATED`, `DEFAULT`.
  - Live search filter by field name, target object, or source column.

### 4. Outputs (All Data Visible, Downloadable & Copyable)
- **Artifacts Selector**: Switch between generated `.dat` files and audit reports (`mapping_report.xlsx`, `validation_errors.csv`).
- **Full On-Screen Data Visibility**:
  - `.dat` Files: Complete syntax-highlighted code view with line numbers (`METADATA|` in blue, `MERGE|` in emerald) and compact, normal line spacing.
  - `.csv` Reports: Full tabular grid of validation errors.
  - `.xlsx` Reports: Full tabular grid of mapped attribute definitions.
- **One-Click Copy**: "Copy All to Clipboard" button formats data as raw text or tab-delimited records for instant pasting into Excel or text editors.
- **One-Click Download**: Direct file download for any generated bundle or report.

### 5. Database Schema
- **MySQL Template Explorer**: Live query of templates, child objects, and attributes configured in MySQL database.
- **Attribute Diagnostics**: View data types, sequence numbers, and required attribute badges (`REQ`).
- **Connectivity Testing**: Diagnostic connection button and live server status indicator.

---

## Technical Specifications

- **Design**: Professional Enterprise Light Theme (slate-50 background, white panels, high-contrast typography, zero emojis, clean SVG iconography).
- **Backend Integration**: FastAPI (Python), Uvicorn ASGI server.
- **Styling**: Tailwind CSS, Inter & JetBrains Mono typography.
- **Integrity**: Uses the existing backend generation and validation logic; 44 unit tests pass.

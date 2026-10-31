# MuleSoft API Explorer Skill

An agent skill and toolkit to inspect, navigate, validate, and document MuleSoft (Mule 4.x) API projects.

## Overview

`mulesoft-api-explorer` provides automated extraction and inspection tools for MuleSoft development:
- **HTTP, FTP, SFTP & APIkit Listeners**: Extracts HTTP endpoints, FTP/SFTP listener directories and polling settings, and associated flows.
- **Anypoint MQ Subscribers**: Finds subscriber destinations, flows, acknowledgement settings, subscription mode (prefetch or polling), and circuit-breaker configuration.
- **Schedulers & Cron Triggers**: Identifies polling schedules, fixed frequencies, and cron expressions.
- **Environment-aware file listener reports**: Resolves FTP/SFTP directory, filename pattern, and polling frequency from `src/main/resources/properties/` and groups the results by environment.
- **Project Structure Validation**: Checks MuleSoft project health, Maven POM standards, secure properties, error handling, and `mule-artifact.json` descriptors.
- **HTML Exploration Reports**: Generates a self-contained, light dashboard-style HTML report with a blue header, white cards, and readable tables.

---

## Repository Structure

```text
.
├── SKILL.md                          # Main agent skill definition and instruction manual
├── references/                       # Quick reference guides
│   ├── anypoint-cli-commands.md      # Anypoint CLI reference cheatsheet
│   ├── dataweave-functions.md        # Common DataWeave 2.0 transformations
│   └── mule-xml-schema.md            # Mule 4 XML schema & namespaces
└── scripts/                          # Standalone Python analysis utilities
    ├── extract-endpoints.py          # Extracts HTTP & APIkit routes to JSON
    ├── extract-schedulers.py         # Extracts schedulers and cron expressions to JSON
    ├── generate-report.py            # Generates standalone HTML exploration reports
    └── validate-project.py           # Validates project configuration and best practices
```

---

## Standalone CLI Usage

Each script in `scripts/` can be run independently against any MuleSoft project root:

### 1. Generate Full HTML Report
```bash
python scripts/generate-report.py /path/to/mulesoft-project [output.html]
```

### 2. Validate Project Health
```bash
python scripts/validate-project.py /path/to/mulesoft-project
```

### 3. Extract Endpoints (JSON)
```bash
python scripts/extract-endpoints.py /path/to/mulesoft-project
```

### 4. Extract Schedulers (JSON)
```bash
python scripts/extract-schedulers.py /path/to/mulesoft-project
```

---

## Agent Skill Usage

To use this skill with Antigravity / Gemini / Hermes:
- **Global installation**: Place this folder inside `~/.gemini/config/skills/mulesoft-api-explorer`
- **Workspace installation**: Place this folder inside `<workspace-root>/.agents/skills/mulesoft-api-explorer`

Trigger it naturally in conversations:
- *"Inspect this MuleSoft project and list all HTTP listeners and APIkit routes."*
- *"Run validate-project on my Mule application."*
- *"Generate an HTML report of my Mule API."*

---

## License

MIT License. See [SKILL.md](SKILL.md) frontmatter for author and platform metadata.

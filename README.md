# MuleSoft API Explorer Skill

An agent skill and toolkit to inspect, navigate, validate, and document MuleSoft (Mule 4.x) API projects.

## Overview

`mulesoft-api-explorer` provides automated extraction and inspection tools for MuleSoft development:
- **HTTP, FTP, SFTP & APIkit Listeners**: Extracts HTTP listeners with configured paths (including listeners accepting any method), FTP/SFTP listener directories and polling settings, and associated flows.
- **APIkit route flows**: Includes only method/path-named flows linked to an `apikit:router` by matching source file and `config-ref`, excluding unrelated flow names that merely resemble APIkit routes.
- **Anypoint MQ Subscribers**: Finds active subscriber destinations, flows, acknowledgement settings, subscription mode (prefetch or polling), and circuit-breaker configuration; XML-commented subscribers and MQ publish operations are excluded from subscriber counts.
- **Schedulers & Cron Triggers**: Identifies Mule core flow schedulers and groups them by SIT/UAT/PROD, resolving cron placeholders from each environment YAML and showing flow, timezone, and source without a frequency column; unrelated polling strategies are not counted as schedulers.
- **Environment-aware file listener reports**: Resolves FTP/SFTP directory, filename pattern, and polling frequency from `src/main/resources/properties/` and groups the results by environment.
- **Project Structure Validation**: Checks MuleSoft project health, Maven POM standards, secure properties, error handling, and `mule-artifact.json` descriptors.
- **HTML Exploration Reports**: Generates a self-contained, light dashboard-style HTML report with a blue header, white cards, and readable tables.
- **Section shortcuts**: Summary cards link directly to the HTTP endpoint, APIkit flow, SFTP, FTP, Anypoint MQ subscriber, and scheduler sections.
- **Back-to-top control**: A floating circular button appears at the bottom-right after scrolling and returns smoothly to the top of the report.

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

When the skill is used to analyze a MuleSoft project, it generates a self-contained HTML project report by default at `<project-root>/target/mulesoft-report.html` and includes that path in its response. Skip this only when the user explicitly asks not to create a report.

**Maven restriction:** The skill must not execute Maven commands (`mvn` or `mvnw`) for any purpose, including builds, tests, packaging, dependency resolution, or effective-POM generation. Analyze source files and existing artifacts only.

### Invoke in Copilot Chat

Always provide the local directory path of the MuleSoft project when invoking the skill. The skill must not guess a project from the current workspace or conversation history. If the path is omitted, provide the directory before analysis can begin.

Type `/mulesoft-api-explorer`, then provide the local project folder and the analysis request:

```text
/mulesoft-api-explorer Analyze C:\path\to\mule-project
```

You can also ask in plain language:

```text
Use the mulesoft-api-explorer skill to analyze C:\path\to\mule-project
```

Other natural-language requests include:
- *"Inspect this MuleSoft project and list all HTTP listeners and APIkit routes."*
- *"Run validate-project on my Mule application."*
- *"Generate an HTML report of my Mule API."*

---

## License

MIT License. See [SKILL.md](SKILL.md) frontmatter for author and platform metadata.

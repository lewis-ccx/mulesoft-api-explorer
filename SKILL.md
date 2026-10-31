---
name: mulesoft-api-explorer
version: 1.0.0
argument-hint: '[project path] [analysis request]'
description: >-
  Explore MuleSoft APIs — endpoints, schedules, interfaces, flows, dependencies, and deployment artifacts.
  Use when inspecting, navigating, exploring, or understanding a MuleSoft (Mule 4.x) API project with a user-provided local project directory.
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags:
  - mulesoft
  - mule4
  - api
  - anypoint
  - maven
metadata:
  hermes:
    tags: [mulesoft, mule4, api, anypoint, maven]
    related_skills: [codebase-inspection]
---

# MuleSoft API Project Explorer

Use when you need to inspect, navigate, or understand a MuleSoft (Mule 4.x) API project. Provides commands and patterns for project structure, API endpoints, schedulers, interfaces, flows, dependencies, and deployment artifacts.

## When to Use

- Explore a MuleSoft project to understand its API surface
- List all HTTP endpoints, schedulers, and interfaces
- Find flows, sub-flows, and their configurations
- Inspect dependencies, properties, and deployment artifacts
- Debug or document an existing Mule application

## How to Invoke

When invoking this skill, the user must provide the local directory path of the MuleSoft project. Do not guess a project from the workspace, conversation history, or a previous request. If the user invokes the skill without a local directory, ask them to provide one before analyzing or generating a report.

In Copilot Chat, type `/mulesoft-api-explorer`, then provide the local project folder and what you want analyzed. For example:

```text
/mulesoft-api-explorer Analyze C:\path\to\mule-project
```

You can also invoke the skill in plain language, such as: `Use the mulesoft-api-explorer skill to analyze C:\path\to\mule-project`. The path must identify a local project directory. When analyzing a project, generate the HTML report by default and include its output path in the response.

## Prerequisites

- Java 11+ (for Mule 4.x)
- Project uses standard Maven structure (`pom.xml`, `src/main/mule/`)
- Optional: `anypoint-cli` for CloudHub operations
- Optional: `xmlstarlet`, `xmllint` for XML validation

## Maven Command Restriction

Never run Maven commands when using this skill. Do not run `mvn`, `mvnw`, or Maven goals for builds, packaging, testing, dependency resolution, effective-POM generation, or any other purpose. Analyze the project by reading its files and using the skill's Python extraction and report scripts. Do not perform Maven build verification.

## Quick Reference — Key Commands

### Project Overview
```bash
# Show project structure
tree -L 3 -I target

# List all Mule config files (recursive)
find src/main/mule -name '*.xml'

# Inspect parent POM and Mule version directly from pom.xml
cat pom.xml | grep -A5 "<parent>"
```

### API Endpoints (HTTP Listeners)
```bash
# List all HTTP listeners with paths
grep -r "http:listener" src/main/mule --include="*.xml" -A 3

# Extract endpoint paths and methods
grep -r "path=" src/main/mule --include="*.xml" -B 2 -A 2 | grep -E "path=|method="

# Find APIkit routers (REST from RAML/OAS)
grep -r "apikit:router" src/main/mule --include="*.xml" -B 3 -A 3

# List APIkit-generated flows (pattern: method:\path:config-name)
grep -r "<flow" src/main/mule --include="*.xml" -o | grep -E "get:|post:|put:|delete:|patch:" | sed 's/.*name="\([^"]*\)".*/\1/'
```

### SFTP Listeners
```bash
# Find SFTP listeners and their polling configuration
grep -r "sftp:listener" src/main/mule --include="*.xml" -B 2 -A 8
```

### FTP Listeners
```bash
# Find FTP listeners and their polling configuration
grep -r "ftp:listener" src/main/mule --include="*.xml" -B 2 -A 8
```

### Anypoint MQ Subscribers
```bash
# Find Anypoint MQ subscriber sources
grep -r "anypoint-mq:subscriber" src/main/mule --include="*.xml" -B 2 -A 8
```

### Schedulers (Polling / Cron)
```bash
# Find all schedulers
grep -r "scheduler" src/main/mule --include="*.xml" -B 2 -A 5

# Find Quartz/cron expressions
grep -r "cronExpression\|frequency" src/main/mule --include="*.xml" -B 2 -A 2

# List polling frequencies
grep -r "pollingFrequency\|fixedFrequency" src/main/mule --include="*.xml" -B 2 -A 2
```

### Interfaces & Contracts
```bash
# Find local RAML/OAS API definitions
find src/main/api -type f \( -name "*.raml" -o -name "*.json" -o -name "*.yaml" \) 2>/dev/null

# Show API title, version, baseUri (local files)
grep -E "title:|version:|baseUri:" src/main/api/*.raml 2>/dev/null

# Check for Exchange-hosted API (RAML zip dependency in pom.xml)
grep -A5 "classifier>raml</classifier>" pom.xml

# List all flows and sub-flows
grep -r "<flow\|<sub-flow" src/main/mule --include="*.xml" -o | sed 's/.*name="\([^"]*\)".*/\1/'
```

### Flows & Components
```bash
# List all component types used
grep -r "<[a-z]*:[a-z]*" src/main/mule --include="*.xml" -o | sort -u

# Find error handlers
grep -r "error-handler\|on-error" src/main/mule --include="*.xml" -B 1 -A 5

# Find DataWeave transformations
grep -r "ee:transform" src/main/mule --include="*.xml" -B 1 -A 10
```

### Configuration & Properties
```bash
# List all property placeholders
grep -r "\${[^}]*}" src/main/mule --include="*.xml" -o | sort -u

# Show environment property files (recursive, includes subfolders)
find src/main/resources -name "*.yaml" -o -name "*.properties" 2>/dev/null

# Show specific environment
cat src/main/resources/properties/prod.yaml 2>/dev/null || cat src/main/resources/prod.yaml 2>/dev/null || cat src/main/resources/application.yaml 2>/dev/null

# Find secure properties (encrypted with ![...] syntax)
grep -r "\$\{secure::" src/main/mule --include="*.xml" -o | sort -u
grep -r "!\\[" src/main/resources --include="*.yaml" -o | head -20
```

### Dependencies & Build
```bash
# Inspect dependency declarations directly in pom.xml
grep -A5 "<dependencies>" pom.xml

# Verify JAR contents
jar tf target/*.jar | grep -E "\.xml$|\.yaml$|mule-artifact"
```

### Runtime Metadata
```bash
# Show mule-artifact.json
cat mule-artifact.json

# Check Mule version from pom
xmlstarlet sel -N mvn=http://maven.apache.org/POM/4.0.0 -t -v "//mvn:mule.version" pom.xml 2>/dev/null || grep "<mule.version>" pom.xml
```

## Procedure — Full Exploration Workflow

1. **Run project overview** — `tree -L 3 -I target` to confirm structure
2. **Read `pom.xml`** — note Mule version, packaging, key dependencies
3. **Read `mule-artifact.json`** — confirm runtime requirements
4. **List all config files** — `find src/main/mule -name '*.xml'`
5. **Extract HTTP endpoints** — run HTTP listener commands above
6. **Extract schedulers** — run scheduler commands above
7. **Find API contracts** — check `src/main/api/` for RAML/OAS
8. **List all flows** — get flow/sub-flow names
9. **Check properties** — list placeholders and env files
10. **Generate the HTML project report** — run `python <skill-directory>/scripts/generate-report.py <project-root>` and verify the report was written to `<project-root>/target/mulesoft-report.html`
11. **Inspect deployment artifacts** — if a built JAR already exists, inspect it without invoking Maven

Generate the report by default whenever using this skill to analyze a MuleSoft project, even if the user did not explicitly request a report. Mention its output path in the response. Skip report generation only if the user explicitly asks not to create one. If report generation fails, report the error rather than implying the report exists.
Never invoke Maven as part of this workflow; inspect project files and any pre-existing artifacts only.

## Pitfalls

- **Non-standard structure** — some projects put configs in `src/main/resources/` or use multi-module; adapt `find` paths
- **Inline vs external DataWeave** — transformations may be in `.dwl` files under `src/main/resources/`; search both
- **Property encryption** — secure properties (e.g., `![value]`) need `secure-property` tool to decrypt
- **APIkit router** — if present, endpoints derive from RAML/OAS, not XML; always check `src/main/api/`
- **Multiple config files** — flows split across files; `grep -r` catches all
- **Commented-out components** — analyze parsed XML elements, not text matches; components inside XML comments are not active configuration and must be excluded from report counts and tables
- **Anypoint MQ report counts** — count only active `anypoint-mq:subscriber` elements; `anypoint-mq:publish` operations are not subscribers and must not affect subscriber counts
- **Mule schedulers** — scan active Mule core `<scheduler>` sources and extract nested `<cron>` or `<fixed-frequency>` settings with the containing flow; resolve cron placeholders from each SIT/UAT/PROD YAML file and group scheduler tables by environment; do not display a frequency column or treat unrelated `scheduling-strategy` polling configurations as scheduler sources
- **CloudHub vs on-prem** — `mule-artifact.json` `requiredProduct` may be `MULE` or `API_GATEWAY`

## Verification

- [ ] Project structure mapped
- [ ] All HTTP endpoints listed (path, method, flow)
- [ ] All schedulers listed (cron expression, flow)
- [ ] API contract (RAML/OAS) located and version noted
- [ ] All flows and sub-flows enumerated
- [ ] Property placeholders documented per environment
- [ ] HTML project report generated at `target/mulesoft-report.html` and its path provided
- [ ] Existing JAR, if available, contains expected configs and `mule-artifact.json` (do not build one)

### HTML Report Generation

Generate a self-contained HTML report of the full project analysis:

```bash
# Generate report (default output: <project-root>/target/mulesoft-report.html)
python <skill-directory>/scripts/generate-report.py <project-root>

# Custom output path
python <skill-directory>/scripts/generate-report.py <project-root> <output.html>
```

This report generation is a standard part of project analysis. After running the script, verify that the output file exists and include its path in the response. Do not overwrite an existing report at a custom path unless requested; use the default path or ask the user which output path to use.

The report includes:
- Clickable summary cards that jump to the HTTP Endpoints, APIkit-Generated Flows, SFTP Listeners, FTP Listeners, Anypoint MQ Subscribers, and Schedulers sections
- A floating circular bottom-right button that appears only after scrolling and returns to the top of the report
- Project metadata (Mule version, packaging, Java version)
- HTTP listeners with configured paths (including listeners that accept any method), listed with method, path, flow, config, and source; APIkit-generated flows linked to an `apikit:router` by source file and `config-ref`
- SFTP and FTP listeners (directory, file pattern, polling frequency, and flow resolved and grouped by environment from `src/main/resources/properties/`)
- Active Anypoint MQ subscribers only (destination, flow, acknowledgement, subscription mode—prefetch or polling—and circuit-breaker settings grouped by environment); publish operations are excluded
- Mule core flow schedulers grouped by SIT/UAT/PROD with environment-resolved cron, flow, timezone, and source (no frequency column), plus VM queues
- Property file inventory

Uses a light dashboard-style, self-contained HTML with no external dependencies. Review project-specific content before sharing.

## Linked References

- `references/mule-xml-schema.md` — Common XML namespaces and elements
- `references/dataweave-functions.md` — Frequently used DW functions
- `references/anypoint-cli-commands.md` — Anypoint CLI cheatsheet
- `scripts/extract-endpoints.py` — Python script to extract endpoints as JSON
- `scripts/extract-schedulers.py` — Python script to extract schedulers as JSON
- `scripts/validate-project.py` — Project validation checklist
- `scripts/generate-report.py` — Full HTML report generator
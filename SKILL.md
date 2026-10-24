---
name: mulesoft-api-explorer
version: 1.0.0
description: >-
  Explore MuleSoft APIs — endpoints, schedules, interfaces, flows, dependencies, and deployment artifacts.
  Use when inspecting, navigating, exploring, or understanding a MuleSoft (Mule 4.x) API project.
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

## Prerequisites

- Maven 3.6+ installed
- Java 11+ (for Mule 4.x)
- Project uses standard Maven structure (`pom.xml`, `src/main/mule/`)
- Optional: `anypoint-cli` for CloudHub operations
- Optional: `xmlstarlet`, `xmllint` for XML validation

## Quick Reference — Key Commands

### Project Overview
```bash
# Show project structure
tree -L 3 -I target

# List all Mule config files (recursive)
find src/main/mule -name '*.xml'

# Show effective POM (resolves parent POM)
mvn help:effective-pom -Doutput=target/effective-pom.xml

# Check parent POM for Mule version
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
# Dependency tree (Mule modules)
mvn dependency:tree | grep -E "mule|api-gateway|http|json|db|vm|jms|salesforce"

# Clean build
mvn clean package -DskipTests

# Run tests
mvn test

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
10. **Build and verify** — `mvn clean package -DskipTests`, check JAR

Each step produces output you can save or document.

## Pitfalls

- **Non-standard structure** — some projects put configs in `src/main/resources/` or use multi-module; adapt `find` paths
- **Inline vs external DataWeave** — transformations may be in `.dwl` files under `src/main/resources/`; search both
- **Property encryption** — secure properties (e.g., `![value]`) need `secure-property` tool to decrypt
- **APIkit router** — if present, endpoints derive from RAML/OAS, not XML; always check `src/main/api/`
- **Multiple config files** — flows split across files; `grep -r` catches all
- **CloudHub vs on-prem** — `mule-artifact.json` `requiredProduct` may be `MULE` or `API_GATEWAY`

## Verification

- [ ] Project structure mapped
- [ ] All HTTP endpoints listed (path, method, flow)
- [ ] All schedulers listed (cron expression, flow)
- [ ] API contract (RAML/OAS) located and version noted
- [ ] All flows and sub-flows enumerated
- [ ] Property placeholders documented per environment
- [ ] Build succeeds (`mvn clean package`)
- [ ] JAR contains expected configs and `mule-artifact.json`

### HTML Report Generation

Generate a self-contained HTML report of the full project analysis:

```bash
# Generate report (defaults to target/mulesoft-report.html)
python scripts/generate-report.py <project-root>

# Custom output path
python scripts/generate-report.py <project-root> /path/to/output.html
```

The report includes:
- Project metadata (Mule version, packaging, Java version)
- Validation results (errors, warnings, info)
- HTTP listeners and APIkit endpoints
- All flows and sub-flows
- Schedulers and VM queues
- Config file inventory
- Property file inventory

Uses the dark-themed, self-contained HTML (no external dependencies). Safe to share or open in any browser.

## Linked References

- `references/mule-xml-schema.md` — Common XML namespaces and elements
- `references/dataweave-functions.md` — Frequently used DW functions
- `references/anypoint-cli-commands.md` — Anypoint CLI cheatsheet
- `scripts/extract-endpoints.py` — Python script to extract endpoints as JSON
- `scripts/extract-schedulers.py` — Python script to extract schedulers as JSON
- `scripts/validate-project.py` — Project validation checklist
- `scripts/generate-report.py` — Full HTML report generator
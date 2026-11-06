import os
import re
import json

ROOT = r"C:\Project\Helios"
EXCLUDE_DIRS = {".git", "node_modules", ".pytest_cache", "dist", "__pycache__", ".venv", "build", ".idea", ".vscode"}

SEARCH_TERMS = [
    "api_key", "api-key", "apikey", "api_push", "api push",
    "/ingest", "x-helios-api-key", "key_hash", "api access", "apikey", "push_via_api"
]

all_matches = []

for root, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for f in files:
        if f.endswith((".pyc", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".lock", ".woff", ".woff2", ".ttf", ".eot")):
            continue
        filepath = os.path.join(root, f)
        relpath = os.path.relpath(filepath, ROOT).replace("\\", "/")
        if relpath in ["inventory_raw.json", "scripts/find_inventory.py", "scripts/check_db_api_keys.py", "inventory_result.txt"]:
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as infile:
                for line_num, line in enumerate(infile, 1):
                    lower_line = line.lower()
                    matched = [t for t in SEARCH_TERMS if t in lower_line]
                    
                    if not matched and re.search(r"\bpush\b", lower_line):
                        matched.append("push")
                        
                    if matched:
                        all_matches.append({
                            "file": relpath,
                            "line": line_num,
                            "text": line.strip(),
                            "matched": matched
                        })
        except Exception:
            pass

def classify(file_path, line_text):
    p = file_path.lower()
    
    # Filter out standard javascript array .push(...) unless it refers to api push
    if re.search(r"\.\s*push\s*\(", line_text) and not any(k in line_text.lower() for k in ["api_push", "api push", "api_key", "ingest", "source"]):
        return None
    # Filter out generic git push in non-doc if unrelated
    if "git push" in line_text.lower():
        if p.endswith((".md", ".txt", ".rst")) or "doc" in p:
            return "documents"
        return None

    # Group according to prompt:
    # routes, services, schemas, repositories, models, security helpers, frontend pages, routes,
    # services, types, sidebar items, env settings, docker settings, scripts, tests and documents.

    if p.endswith((".md", ".txt", ".rst")) or p.startswith("docs/"):
        return "documents"
    
    # Security helpers
    if p.startswith("backend/app/core/api_key") or "api_key_security" in p or "api_key_auth" in p:
        return "security helpers"

    # Backend routes
    if p.startswith("backend/app/api/") or p == "backend/app/main.py":
        return "routes"

    # Backend services
    if p.startswith("backend/app/services/"):
        return "services"

    # Backend schemas
    if p.startswith("backend/app/schemas/"):
        return "schemas"

    # Backend repositories
    if p.startswith("backend/app/repositories/"):
        return "repositories"

    # Backend models
    if p.startswith("backend/app/models/"):
        return "models"

    # Frontend pages
    if p.startswith("frontend/src/pages/"):
        return "frontend pages"

    # Frontend routes
    if p.startswith("frontend/src/routes/"):
        return "frontend routes"

    # Frontend services
    if p.startswith("frontend/src/services/"):
        return "frontend services"

    # Frontend types
    if p.startswith("frontend/src/types/"):
        return "frontend types"

    # Frontend sidebar items
    if "sidebar" in p or "layout" in p:
        return "frontend sidebar items"

    # Env settings
    if ".env" in p or "config.py" in p or "features.ts" in p:
        return "env settings"

    # Docker settings
    if "docker" in p:
        return "docker settings"

    # Tests
    if "test" in p or p.startswith("backend/tests/"):
        return "tests"

    # Scripts / database / pipeline
    if p.startswith("scripts/"):
        return "scripts"

    if p.startswith("database/"):
        return "database"

    if p.startswith("backend/pipeline/") or p.startswith("pipeline/") or p.startswith("resources/"):
        return "pipeline"

    return "other"

ORDERED_CATEGORIES = [
    "routes",
    "services",
    "schemas",
    "repositories",
    "models",
    "security helpers",
    "frontend pages",
    "frontend routes",
    "frontend services",
    "frontend types",
    "frontend sidebar items",
    "env settings",
    "docker settings",
    "scripts",
    "tests",
    "documents",
    "database",
    "pipeline",
    "other"
]

grouped = {cat: [] for cat in ORDERED_CATEGORIES}

for m in all_matches:
    cat = classify(m["file"], m["text"])
    if not cat:
        continue
    grouped[cat].append(m)

out_lines = []
out_lines.append("# INVENTORY OF API PUSH / API KEY REFERENCES")
out_lines.append(f"Total classified occurrences: {sum(len(v) for v in grouped.values())}\n")

for cat in ORDERED_CATEGORIES:
    items = grouped[cat]
    out_lines.append(f"## {cat.upper()} ({len(items)} occurrences)")
    if not items:
        out_lines.append("  (None)\n")
        continue
    file_map = {}
    for item in items:
        file_map.setdefault(item["file"], []).append(item)
    for f, lines in sorted(file_map.items()):
        out_lines.append(f"- **{f}** ({len(lines)} lines):")
        for l in lines:
            out_lines.append(f"  - Line {l['line']}: `{l['text']}`")
    out_lines.append("")

inventory_text = "\n".join(out_lines)
with open("inventory_result.txt", "w", encoding="utf-8") as out:
    out.write(inventory_text)

print("Inventory generated successfully! Output written to inventory_result.txt")

import os
import re

pattern = re.compile(r'api_key|api-key|apikey|api_push|X-Helios-Api-Key|key_hash|API Access|ApiKey', re.IGNORECASE)
exclude_dirs = {'.git', 'node_modules', '.next', 'dist', 'build', '__pycache__', '.pytest_cache', 'venv', '.venv'}

targets = ['backend', 'frontend/src', 'database', 'scripts', 'pipeline']
code_exts = ('.py', '.ts', '.tsx', '.sql', '.json', '.env', '.yml', '.yaml', '.sh')

hits = []
for target in targets:
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith(code_exts):
                if f.startswith('inventory') or f == 'verify_zero_hits.py':
                    continue
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    for idx, line in enumerate(fp, 1):
                        if pattern.search(line):
                            hits.append((path, idx, line.strip()))

# check root docker-compose and env files
for f in os.listdir('.'):
    if f.startswith(('docker-compose', '.env')) and os.path.isfile(f):
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            for idx, line in enumerate(fp, 1):
                if pattern.search(line):
                    hits.append((f, idx, line.strip()))

print(f"TOTAL CODE/CONFIG/SCRIPT HITS: {len(hits)}")
for h in hits:
    print(f"{h[0]}:{h[1]} -> {h[2]}")


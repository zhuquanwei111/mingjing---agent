"""Transform pip's platform-specific download report into a hashed lock."""

import json
import sys

report = json.load(sys.stdin)
extras = {"temporalio": "[opentelemetry]", "psycopg": "[binary]"}
for item in sorted(report["install"], key=lambda entry: entry["metadata"]["name"].lower()):
    name = item["metadata"]["name"]
    version = item["metadata"]["version"]
    digest = item["download_info"]["archive_info"]["hashes"]["sha256"]
    print(f"{name}{extras.get(name, '')}=={version} --hash=sha256:{digest}")

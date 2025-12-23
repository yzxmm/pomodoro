import json
import os
import sys

# Add current directory to path so we can import from tools
sys.path.append(os.getcwd())
from tools.generate_manifest import generate_manifest

base_dir = os.path.abspath("cloud")
# url_prefix = "http://localhost:8000"
# url_prefix = "https://raw.githubusercontent.com/yzxmm/pomodoro/main/cloud_mock"
url_prefix = "https://raw.githubusercontent.com/yzxmm/pomodoro-assets/main"

print(f"Generating manifest for {base_dir} with prefix {url_prefix}")
manifest = generate_manifest(base_dir, url_prefix)

output_path = os.path.join(base_dir, "manifest.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=4)

print(f"Manifest written to {output_path}")

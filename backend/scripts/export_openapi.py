"""Exporta el schema OpenAPI de la app FastAPI a un fichero JSON/YAML.

Uso:
    cd backend
    python scripts/export_openapi.py             # genera openapi.json
    python scripts/export_openapi.py --yaml      # genera openapi.yaml
"""
import sys
import json
import argparse
from pathlib import Path

# Asegurar que el path apunta al directorio backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Export OpenAPI schema")
    parser.add_argument("--yaml", action="store_true", help="Export as YAML")
    parser.add_argument("--out", default=None, help="Output file path")
    args = parser.parse_args()

    schema = app.openapi()

    if args.yaml:
        try:
            import yaml
        except ImportError:
            print("PyYAML not installed. Run: pip install pyyaml")
            sys.exit(1)
        out = args.out or "openapi.yaml"
        with open(out, "w", encoding="utf-8") as f:
            yaml.dump(schema, f, allow_unicode=True, sort_keys=False)
        print(f"OpenAPI schema exported to {out}")
    else:
        out = args.out or "openapi.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        print(f"OpenAPI schema exported to {out}")


if __name__ == "__main__":
    main()

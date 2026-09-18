from __future__ import annotations

import argparse
from pathlib import Path


INDEX_HTML = """<!doctype html>
<html lang="en">
  <head><meta charset="UTF-8"><title>Counter</title></head>
  <body>
    <main>
      <p data-testid="count">0</p>
      <button type="button" id="increment">Increment</button>
      <button type="button" id="decrement">Decrement</button>
    </main>
    <script>
      let count = 0;
      const output = document.querySelector('[data-testid="count"]');
      document.querySelector('#increment').addEventListener('click', () => {
        count += 1;
        output.textContent = String(count);
      });
      document.querySelector('#decrement').addEventListener('click', () => {
        count -= 1;
        output.textContent = String(count);
      });
    </script>
  </body>
</html>
"""

SERVER_PY = """from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent / "public")
server = ThreadingHTTPServer((os.environ.get("HOST", "0.0.0.0"), int(os.environ.get("PORT", "3000"))), SimpleHTTPRequestHandler)
server.serve_forever()
"""

DEPLOY_SH = """#!/usr/bin/env bash
set -euo pipefail
exec python3 server.py
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("requirements_dir")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    requirements = Path(args.requirements_dir)
    if not (requirements / "requirements.yaml").is_file():
        raise FileNotFoundError("requirements.yaml is missing")

    output = Path(args.output_dir)
    public = output / "public"
    public.mkdir(parents=True, exist_ok=True)
    (public / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (output / "server.py").write_text(SERVER_PY, encoding="utf-8")
    (output / "deploy.sh").write_text(DEPLOY_SH, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


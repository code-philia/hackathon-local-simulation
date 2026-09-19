#!/usr/bin/env python3
"""Minimal agent that exercises the local runner's deploy.sh contract.

WARNING: this path is local-only. The production runner has no deploy.sh
branch; it requires frontend/ and backend/ in the output directory. See the
warning at the top of README section 3.3 before building a real agent on it.

It writes no frontend/ or backend/ directory at all — only:

    <output-dir>/
    ├── deploy.sh
    ├── server.py
    └── public/
        └── index.html

so a successful run proves the local runner really did take the deploy.sh
branch rather than the standard npm one.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


DEPLOY_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail

exec python3 server.py
"""

SERVER = """import functools
import http.server
import os

handler = functools.partial(
    http.server.SimpleHTTPRequestHandler,
    directory="public",
)
port = int(os.environ.get("PORT", "3000"))
http.server.HTTPServer(("0.0.0.0", port), handler).serve_forever()
"""

# Implements the bundled public exercise (public-exercise/) so that a run of
# this example both proves the deploy.sh branch was taken and passes its test.
INDEX = """<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>Counter</title></head>
  <body>
    <p data-testid="count">0</p>
    <button id="increment">Increment</button>
    <button id="decrement">Decrement</button>
    <script>
      let value = 0;
      const display = document.querySelector('[data-testid="count"]');
      const render = () => { display.textContent = String(value); };
      document.getElementById('increment')
        .addEventListener('click', () => { value += 1; render(); });
      document.getElementById('decrement')
        .addEventListener('click', () => { value -= 1; render(); });
      render();
    </script>
  </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("requirements_dir")
    parser.add_argument("--output-dir", required=True)
    args, _unknown = parser.parse_known_args()

    output_dir = Path(args.output_dir).resolve()
    (output_dir / "public").mkdir(parents=True, exist_ok=True)

    (output_dir / "public" / "index.html").write_text(INDEX, encoding="utf-8")
    (output_dir / "server.py").write_text(SERVER, encoding="utf-8")

    deploy_script = output_dir / "deploy.sh"
    deploy_script.write_text(DEPLOY_SCRIPT, encoding="utf-8")
    os.chmod(deploy_script, 0o755)

    print(
        "[custom-deploy-agent] wrote deploy.sh, server.py and public/ "
        "(no frontend/ or backend/)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

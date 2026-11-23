"""Switch ARTEMIS model config between 'cloud' (all DeepSeek) and 'local' (Ollama qwen).

Usage:  .venv/Scripts/python.exe artemis_models.py local|cloud|show

Keeps three files in sync: repo config/artemis.jsonc (what the CLI reads when cwd is
the repo) and the global %APPDATA%/Artemis/artemis.jsonc (always loaded, wins).
"""

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).parent / "config"
GLOBAL = Path.home() / "AppData/Roaming/Artemis/artemis.jsonc"
TARGET = REPO / "artemis.jsonc"


def show() -> None:
    import re

    s = TARGET.read_text(encoding="utf-8")
    provs = re.findall(r'"provider": "([a-z]+)"', s)
    from collections import Counter

    print("current:", dict(Counter(provs)))


def switch(name: str) -> None:
    src = REPO / f"artemis.{name}.jsonc"
    if not src.exists():
        raise SystemExit(f"missing {src}")
    shutil.copy(src, TARGET)
    GLOBAL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, GLOBAL)
    print(f"switched to {name}: {src.name} -> config/artemis.jsonc + {GLOBAL}")
    print("now stop the daemon before the next run: python -m artemis.interfaces.cli.main stop")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "show"
    if arg == "show":
        show()
    else:
        switch(arg)

"""Download DeepSeek Harness into vendor/ at the commit pinned in vendor.toml.

None of its code is copied into this repo: the clone lives in a git-ignored
folder and our agent drives it from outside. Use --update-pin to move the pin
to upstream HEAD. Build it afterwards with the commands this script prints.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "vendor.toml"
DEST = ROOT / "vendor" / "deepseek-harness"
SECTION = "deepseek-harness"


def git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def load_pin() -> dict[str, str]:
    return tomllib.loads(PINS.read_text(encoding="utf-8"))[SECTION]


def update_pin(repo: str) -> str:
    head = git("ls-remote", repo, "HEAD").split()[0]
    text = PINS.read_text(encoding="utf-8")
    pattern = rf'(\[{re.escape(SECTION)}\][^\[]*?ref = ")[0-9a-f]+(")'
    updated = re.sub(pattern, rf"\g<1>{head}\g<2>", text, flags=re.DOTALL)
    PINS.write_text(updated, encoding="utf-8")
    return head


def fetch(repo: str, ref: str) -> None:
    if not (DEST / ".git").exists():
        DEST.parent.mkdir(parents=True, exist_ok=True)
        git("clone", "--filter=blob:none", "--no-checkout", repo, str(DEST))
    git("fetch", "--quiet", "origin", ref, cwd=DEST)
    git("-c", "advice.detachedHead=false", "checkout", "--quiet", ref, cwd=DEST)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--update-pin", action="store_true", help="pin upstream HEAD first")
    args = parser.parse_args()

    pin = load_pin()
    ref = update_pin(pin["repo"]) if args.update_pin else pin["ref"]
    try:
        fetch(pin["repo"], ref)
    except subprocess.CalledProcessError as exc:
        print(f"git failed: {exc.stderr or exc}", file=sys.stderr)
        return 1

    actual = git("rev-parse", "HEAD", cwd=DEST)
    manifest = json.loads((DEST / "package.json").read_text(encoding="utf-8"))
    pnpm = manifest.get("packageManager", "pnpm")
    node = manifest.get("engines", {}).get("node", "any")
    print(f"DeepSeek Harness at {actual[:12]} in {DEST.relative_to(ROOT)} (needs Node {node})")
    print("Build it with its own pinned package manager:")
    print(f"  cd {DEST.relative_to(ROOT).as_posix()} && npx {pnpm} install && npx {pnpm} run build")
    print(f"Or run the pinned npm release without building: npx {pin['npm']} web --no-open")
    return 0 if actual == ref else 1


if __name__ == "__main__":
    sys.exit(main())

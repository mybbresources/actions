"""Build the two files required by the MyBB Resources catalog submission form."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile


def encode(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def checked_path(value):
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) or part in {".", ".."}
           for part in value.split("/")):
        raise ValueError(f"Invalid package path: {value}")
    return value


def build(root, recipe, ref, output):
    version = ref.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?", version):
        raise ValueError("Provide a release version such as 1.2.3 or v1.2.3")
    config = json.loads((root / checked_path(recipe)).read_text())
    manifest = config["manifest"]
    slug = manifest["slug"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", slug):
        raise ValueError("Invalid catalog slug")

    entries = {}
    for file in config["files"]:
        destination = checked_path(file["destination"])
        if destination.lower() in entries:
            raise ValueError(f"Duplicate destination: {destination}")
        if "source" in file:
            path = root / checked_path(file["source"])
            if path.resolve() != path or not path.is_file():
                raise ValueError(f"Expected a regular source file: {path}")
            data = path.read_bytes()
        elif file.get("generate") == "core-version" and slug == "mybb-tooling-core":
            data = encode({"version": version})
        else:
            raise ValueError(f"Missing source for {destination}")
        entries[destination.lower()] = (destination, file["role"], data, file.get("executable", False))
    if not entries:
        raise ValueError("The package file map is empty")

    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{slug}-{version}.zip"
    manifest["version"] = version
    manifest["files"] = []
    with zipfile.ZipFile(archive, "w") as package:
        for destination, role, data, executable in sorted(entries.values()):
            source = f"upload/{destination}"
            entry = zipfile.ZipInfo(source)
            entry.create_system = 3
            entry.external_attr = (0o100755 if executable else 0o100644) << 16
            package.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED)
            manifest["files"].append({"source": source, "destination": destination, "role": role})
    manifest["package"] = {
        "url": f"https://plugins.mybbresources.com/api/v1/plugins/{slug}/releases/{version}/package",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "size": archive.stat().st_size,
        "signature": "",
        "key_id": "",
    }
    (output / "meta.json").write_bytes(encode(manifest))
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    (output / "source-commit.txt").write_text(commit + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--recipe", default="catalog-package.json")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.root.resolve(), args.recipe, args.version, args.output)

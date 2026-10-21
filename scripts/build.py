"""Assemble verified upstream software; no agent implementation lives here."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def download(asset: dict, cache: Path) -> Path:
    name = urllib.parse.unquote(urllib.parse.urlparse(asset["url"]).path.rsplit("/", 1)[1])
    target = cache / name
    for attempt in range(3):
        if not target.exists():
            partial = target.with_suffix(target.suffix + ".partial")
            request = urllib.request.Request(asset["url"], headers={"User-Agent": "PocketAgent-builder/0.1"})
            try:
                with urllib.request.urlopen(request, timeout=120) as source, partial.open("wb") as output:
                    shutil.copyfileobj(source, output)
                partial.replace(target)
            except Exception:
                partial.unlink(missing_ok=True)
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
                continue
        with target.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest == asset["sha256"]:
            print(f"Verified {asset['id']} {asset['version']}", flush=True)
            return target
        target.unlink()
        raise ValueError(f"SHA256 mismatch for {asset['id']}: {digest}")
    raise RuntimeError(f"Download failed: {asset['id']}")


def extract(asset: dict, archive: Path, destination: Path, scratch: Path) -> None:
    unpacked = scratch / asset["id"]
    unpacked.mkdir(parents=True)
    if asset["format"] == "zip":
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if not (unpacked / name).resolve().is_relative_to(unpacked.resolve()):
                    raise ValueError(f"Archive path escapes destination: {name}")
            bundle.extractall(unpacked)
    elif asset["format"] == "tar.gz":
        with tarfile.open(archive) as bundle:
            bundle.extractall(unpacked, filter="data")
    else:
        sevenzip = shutil.which("7z") or str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "7-Zip/7z.exe")
        subprocess.run([sevenzip, "x", str(archive), f"-o{unpacked}", "-y", "-bso0", "-bsp0"], check=True)
    if asset.get("strip_root"):
        children = list(unpacked.iterdir())
        if len(children) != 1 or not children[0].is_dir():
            raise ValueError(f"Unexpected archive layout for {asset['id']}")
        unpacked = children[0]
    shutil.copytree(unpacked, destination, dirs_exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist/PocketAgent")
    parser.add_argument("--download-only", action="store_true")
    args = parser.parse_args()
    lock = json.loads((ROOT / "upstream.lock.json").read_text(encoding="utf-8"))
    cache = ROOT / ".cache/downloads"
    cache.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        archives = list(pool.map(lambda asset: download(asset, cache), lock["assets"]))
    if args.download_only:
        return
    if os.name != "nt":
        raise RuntimeError("Build on Windows so the actual native launcher can be compiled and tested.")
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError(f"Output already exists; choose a clean output directory: {output}")
    output.mkdir(parents=True)
    scratch = ROOT / ".cache/unpack"
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        for asset, archive in zip(lock["assets"], archives):
            extract(asset, archive, output / asset["destination"], scratch)
        csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
        subprocess.run([
            str(csc), "/nologo", "/target:exe", "/platform:x64", "/optimize+",
            f"/win32manifest:{ROOT / 'launcher/app.manifest'}",
            f"/out:{output / 'PocketAgent.exe'}", str(ROOT / "launcher/PocketAgent.cs"),
        ], check=True)
        shutil.copytree(ROOT / "portable", output, dirs_exist_ok=True)
        shutil.copytree(ROOT / "defaults", output / "defaults")
        for name in ["README.md", "LICENSE", "THIRD_PARTY.md", "upstream.lock.json"]:
            shutil.copy2(ROOT / name, output / name)
        shutil.copytree(ROOT / "licenses", output / "licenses")
        inventory = {}
        for item in sorted(output.rglob("*")):
            if item.is_file():
                with item.open("rb") as source:
                    inventory[item.relative_to(output).as_posix()] = hashlib.file_digest(source, "sha256").hexdigest()
        (output / "bundle-files.sha256.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
        print(f"Assembled {len(inventory)} verified files at {output}", flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()


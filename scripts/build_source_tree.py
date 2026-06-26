#!/usr/bin/env python3
import argparse, yaml, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_releases(manifest_path: pathlib.Path):
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not data or "releases" not in data:
        raise SystemExit("metadata/releases.yaml must define 'releases'")
    return data["releases"]

def run_extract(src, dest, strip):
    cmd = [
        sys.executable, str(ROOT / "scripts" / "extract_any.py"),
        "--src", str(src),
        "--dest", str(dest),
        "--strip-components", str(strip if strip is not None else "auto"),
    ]
    subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "metadata" / "releases.yaml"))
    ap.add_argument("--out", default=str(ROOT / "source_code"))
    ap.add_argument("--clean", action="store_true", help="Delete output directory before building")
    args = ap.parse_args()

    manifest = pathlib.Path(args.manifest)
    outdir = pathlib.Path(args.out)

    releases = load_releases(manifest)

    if args.clean and outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for rel in releases:
        rid = rel["id"]
        rdir = outdir / rid
        if rdir.exists():
            shutil.rmtree(rdir)
        rdir.mkdir(parents=True, exist_ok=True)

        for src in rel.get("sources", []):
            path = ROOT / src["path"]
            strip = src.get("strip_components", "auto")
            run_extract(path, rdir, strip)

    print(f"Built {len(releases)} releases into {outdir}")

if __name__ == "__main__":
    main()

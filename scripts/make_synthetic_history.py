#!/usr/bin/env python3
import argparse, os, yaml, pathlib, shutil, subprocess, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]

def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)

def git(*args, **kw):
    return run(["git"] + list(args), **kw)

def load_releases(path: pathlib.Path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["releases"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "metadata" / "releases.yaml"))
    ap.add_argument("--srcroot", default=str(ROOT / "source_code"))
    ap.add_argument("--branch", default="SourceCode")
    ap.add_argument("--force", action="store_true", help="Force reset branch")
    ap.add_argument("--bot-name", default="SWH Curator Bot")
    ap.add_argument("--bot-email", default="bot@softwareheritage.org")
    args = ap.parse_args()

    manifest = pathlib.Path(args.manifest)
    releases = load_releases(manifest)

    # Ensure full history
    git("fetch", "--all", "--tags", "--prune")
    # Create or reset orphan branch
    if args.force:
        try: git("branch", "-D", args.branch)
        except subprocess.CalledProcessError: pass

    # Switch to orphan
    git("checkout", "--orphan", args.branch)
    # Clear worktree while keeping project infra
    keep = {".git", ".github", "scripts", "metadata", "raw_materials"}
    for p in list(ROOT.iterdir()):
        if p.name in keep:
            continue
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.is_file():
            try: p.unlink()
            except FileNotFoundError: pass
    run(["git", "rm", "-r", "--cached", ".", "--ignore-unmatch"])

    os.environ["GIT_AUTHOR_NAME"] = args.bot_name
    os.environ["GIT_AUTHOR_EMAIL"] = args.bot_email
    os.environ["GIT_COMMITTER_NAME"] = args.bot_name
    os.environ["GIT_COMMITTER_EMAIL"] = args.bot_email

    for rel in releases:
        rid = rel["id"]
        title = rel.get("title", rid)
        msg = rel.get("message", f"{title}")
        date = rel.get("date")  # ISO date or datetime
        author = rel.get("author")  # "Name <email>" optional

        # Wipe worktree except infra
        for p in list(ROOT.iterdir()):
            if p.name in {".git", ".github", "scripts", "metadata", "raw_materials"}:
                continue
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.is_file():
                try: p.unlink()
                except FileNotFoundError: pass

        build_dir = pathlib.Path(args.srcroot) / rid
        if not build_dir.exists():
            raise SystemExit(f"Missing build for release {rid}: {build_dir}")

        # Copy content to repo root
        for p in build_dir.iterdir():
            dest = ROOT / p.name
            if p.is_dir():
                shutil.copytree(p, dest)
            else:
                shutil.copy2(p, dest)

        run(["git", "add", "-A"])

        env = os.environ.copy()
        if date:
            # Accept YYYY-MM-DD or full ISO; default to noon UTC
            try:
                dt = datetime.datetime.fromisoformat(date.replace("Z",""))
            except Exception:
                dt = datetime.datetime.strptime(date, "%Y-%m-%d")
            if dt.tzinfo is None:
                dt = dt.replace(hour=12, minute=0, second=0, tzinfo=datetime.timezone.utc)
            ts = dt.astimezone(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
            env["GIT_AUTHOR_DATE"] = ts
            env["GIT_COMMITTER_DATE"] = ts

        if author:
            run(["git", "commit", "-m", msg, "--author", author], env=env)
        else:
            run(["git", "commit", "-m", msg], env=env)

    # Force-update remote branch
    git("push", "-f", "origin", args.branch)
    print(f"Rebuilt synthetic history on {args.branch} with {len(releases)} commits.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse, csv, hashlib, pathlib, datetime, yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]

def sha256sum(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def append_checksums(checksums_csv: pathlib.Path, files: list[pathlib.Path]):
    rows = []
    if checksums_csv.exists():
        rows = checksums_csv.read_text().splitlines()
    existing = set()
    if rows:
        for line in rows[1:]:
            try:
                path,size,_ = line.split(",",2)
                existing.add((path,size))
            except ValueError:
                continue
    new_rows = []
    for f in files:
        key = (str(f), str(f.stat().st_size))
        if key in existing:
            continue
        new_rows.append([str(f), f.stat().st_size, sha256sum(f)])
    if not checksums_csv.exists():
        checksums_csv.parent.mkdir(parents=True, exist_ok=True)
        hdr = "path,size,sha256\n"
        checksums_csv.write_text(hdr + "\n".join(",".join(map(str, r)) for r in new_rows))
    else:
        with checksums_csv.open("a", encoding="utf-8") as out:
            for r in new_rows:
                out.write(",".join(map(str,r))+"\n")
    return new_rows

def journal_append(journal_md: pathlib.Path, msg: str):
    journal_md.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    head = "# Curation journal\n"
    body = journal_md.read_text(encoding="utf-8") if journal_md.exists() else head
    entry = f"\n## {today}\n\n{msg.strip()}\n"
    journal_md.write_text(body + entry, encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(ROOT / "metadata" / "releases.yaml"))
    ap.add_argument("--checksums", default=str(ROOT / "metadata" / "checksums.csv"))
    ap.add_argument("--journal", default=str(ROOT / "metadata" / "journal.md"))
    args = ap.parse_args()

    releases = yaml.safe_load(pathlib.Path(args.manifest).read_text(encoding="utf-8"))["releases"]
    files = []
    for rel in releases:
        for src in rel.get("sources", []):
            p = (ROOT / src["path"]).resolve()
            if p.is_file():
                files.append(p)
            elif p.is_dir():
                for child in p.rglob("*"):
                    if child.is_file():
                        files.append(child)

    new_rows = append_checksums(pathlib.Path(args.checksums), files)
    if new_rows:
        lines = "\n".join(f"- {path} ({size} bytes) sha256={sha}" for path,size,sha in new_rows)
        journal_append(pathlib.Path(args.journal), f"Recorded checksums for:\n{lines}")
        print(f"Appended {len(new_rows)} checksum rows and journal entry.")
    else:
        print("No new raw files to checksum.")

if __name__ == "__main__":
    main()

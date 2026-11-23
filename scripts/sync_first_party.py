#!/usr/bin/env python3
"""Add new GitHub releases of first-party plugin repos to the catalogue.

For each repo in first-party.txt, reads its latest release. If the release's
.etherpkg version is not yet in plugins/<id>.yaml, downloads the asset,
computes its SHA-256 and prepends a version entry. minEther comes from the
release notes line "minEther: X.Y.Z". Prints the ids it changed.
"""
import hashlib, json, os, re, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def gh(*args):
    return json.loads(subprocess.check_output(["gh", "api", *args], text=True))


def main():
    changed = []
    repos = [l.strip() for l in open(os.path.join(ROOT, "first-party.txt")) if l.strip() and not l.startswith("#")]
    for repo in repos:
        try:
            rel = gh(f"repos/{repo}/releases/latest")
        except subprocess.CalledProcessError:
            print(f"{repo}: no release yet", file=sys.stderr)
            continue
        assets = [a for a in rel.get("assets", []) if a["name"].endswith(".etherpkg")]
        if len(assets) != 1:
            print(f"{repo}: expected one .etherpkg on {rel['tag_name']}", file=sys.stderr)
            continue
        asset = assets[0]
        m = re.fullmatch(r"(.+)-(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)\.etherpkg", asset["name"])
        if not m:
            print(f"{repo}: unexpected asset name {asset['name']}", file=sys.stderr)
            continue
        pid, version = m.groups()
        if rel["tag_name"] != "v" + version:
            print(f"{repo}: tag {rel['tag_name']} does not match {version}", file=sys.stderr)
            continue
        mm = re.search(r"^minEther:\s*(\d+\.\d+\.\d+)\s*$", rel.get("body") or "", re.M)
        if not mm:
            print(f"{repo}: release notes lack 'minEther: X.Y.Z'", file=sys.stderr)
            continue
        path = os.path.join(ROOT, "plugins", pid + ".yaml")
        if not os.path.exists(path):
            print(f"{repo}: plugins/{pid}.yaml does not exist; add the first entry by hand", file=sys.stderr)
            continue
        text = open(path).read()
        if re.search(r"^\s*-\s*version:\s*" + re.escape(version) + r"\s*$", text, re.M):
            continue
        with urllib.request.urlopen(asset["browser_download_url"], timeout=120) as r:
            sha = hashlib.sha256(r.read()).hexdigest()
        released = rel["published_at"].replace(".000", "")
        idx = re.search(r"^versions:\n", text, re.M)
        indent = re.search(r"^versions:\n(\s*)-", text, re.M)
        pad = indent.group(1) if indent else "    "
        sub = pad + "  "
        entry = (f"{pad}- version: {version}\n{sub}url: {asset['browser_download_url']}\n"
                 f"{sub}sha256: {sha}\n{sub}releasedAt: \"{released}\"\n{sub}minEther: {mm.group(1)}\n")
        text = text[: idx.end()] + entry + text[idx.end():]
        open(path, "w").write(text)
        changed.append(f"{pid} {version}")
    print("\n".join(changed))


if __name__ == "__main__":
    main()

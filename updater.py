import sys, os, requests, zipfile, tempfile, shutil
import re
import json
from pathlib import Path
import version

APP_DIR = Path.cwd()

UPDATE_DIR = version.UPDATE_DIR

def apply_update(staged_dir: Path, target_dir: Path = APP_DIR):
    if not staged_dir.exists():
        return
    for item in staged_dir.iterdir():
        dest = target_dir / item.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        shutil.move(str(item), str(dest))
    staged_dir.rmdir()
    

def parse_version(v: str):
    if not v:
        return (0,)
    nums = re.findall(r"\d+", v)
    if not nums:
        return (0,)
    return tuple(map(int, nums))

def is_newer(latest: str):
    return parse_version(latest) > parse_version(version.__version__)

def get_latest_release():
    r = requests.get(version.GITHUB_API, timeout=10)
    if r.status_code != 200:
        if r.status_code == 404:
            raise Exception(f"GitHub returned status code 404. Your current repo ({version.GITHUB_USER}/{version.GITHUB_REPO}) does not have any releases.")
        raise Exception(f"GitHub returned status code {r.status_code}.")
    return r.json()

def download_release(url: str):
    tmp = Path(tempfile.mkdtemp())
    zip_path = tmp / "update.zip"
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

    extract_dir = tmp / "extracted"
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_dir)

    return extract_dir

def stage_update(extract_dir: Path, tag: str):
    if UPDATE_DIR.exists() and not UPDATE_DIR.is_dir():
        shutil.rmtree(UPDATE_DIR)
    UPDATE_DIR.mkdir(parents=True, exist_ok=True)

    version_name = tag.lstrip("v")
    target = UPDATE_DIR / version_name

    if target.exists():
        shutil.rmtree(target)

    entries = list(extract_dir.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        src = entries[0]
        shutil.move(str(src), str(target))
        try:
            extract_dir.rmdir()
        except Exception:
            shutil.rmtree(extract_dir, ignore_errors=True)
    else:
        shutil.move(str(extract_dir), str(target))

def check_and_stage_update(apply: bool = False, printing: bool = True, ask: bool = False, cfg: dict = None, debug: bool = False, autoupdating: bool = False):
    def print(*args, **kwargs):
        if printing:
            __builtins__.print(*args, **kwargs)
    try:
        release = get_latest_release()
        latest = release["tag_name"]

        skip_versions = []
        skip_versions = cfg.get("skip_versions", [])
        
        if is_newer(latest):
            if autoupdating and latest in skip_versions:
                print(f"Skipping version {latest} (marked to skip in config).")
                return

            response = "y"
            if ask:
                response = input(f"A new version {latest} is available. Do you want to update now? (y/n/(s)kip): ").strip().lower()
            if response.startswith("s"):
                target_cfg = cfg
                if target_cfg is None:
                    try:
                        with open(APP_DIR / "config.json", "r") as f:
                            target_cfg = json.load(f)
                    except Exception:
                        target_cfg = None

                if isinstance(target_cfg, dict):
                    target_cfg.setdefault("skip_versions", [])
                    if latest not in target_cfg["skip_versions"]:
                        target_cfg["skip_versions"].append(latest)
                        try:
                            with open(APP_DIR / "config.json", "w") as f:
                                json.dump(target_cfg, f, indent=4)
                        except Exception:
                            pass
                print(f"Skipped version {latest}.")
                return
            if response != 'y':
                return
            print(f"DuoKLI update available: {latest}")
            url = release["zipball_url"]
            extract_dir = download_release(url)
            stage_update(extract_dir, latest)
            staged_path = UPDATE_DIR / latest.lstrip("v")
            if apply:
                print(f"Applying update {latest} now...")
                try:
                    apply_update(staged_path, APP_DIR)
                except Exception as e:
                    print("Failed to apply update:", e)
                    sys.exit(1)

                python = sys.executable
                duo_script = APP_DIR / "DuoKLI.py"
                if not duo_script.exists():
                    print(f"Cannot restart: {duo_script} not found.")
                    sys.exit(1)

                print("Restarting DuoKLI...")
                os.chdir(str(APP_DIR))
                os.execv(python, [python, str(duo_script)])
            else:
                print(f"Update staged at {staged_path}. It will be applied on next launch.")
                sys.exit(0)
        else:
            print("DuoKLI is up to date.")
    except Exception as e:
        print("Failed to check for updates:", e)

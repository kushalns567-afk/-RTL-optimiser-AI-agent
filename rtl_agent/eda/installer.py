"""
EDA Tools Installer & Path Manager
Checks for Yosys and Icarus Verilog, and provides automated downloading for Windows.
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile
import json
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"

OSS_CAD_SUITE_REPO = "YosysHQ/oss-cad-suite-build"
IVERILOG_WINDOWS_URL = "https://github.com/steveicarus/iverilog/releases"

# Auto-configure PATH with OSS CAD Suite bin and lib if present
_oss_bin = TOOLS_DIR / "oss-cad-suite" / "bin"
_oss_lib = TOOLS_DIR / "oss-cad-suite" / "lib"
if _oss_bin.exists():
    _cur_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{_oss_bin.resolve()};{_oss_lib.resolve()};{_cur_path}"

def _test_executable(path_str: str) -> bool:
    try:
        res = subprocess.run([path_str, "-V"], capture_output=True, text=True, timeout=5)
        # Check if it ran without path-with-spaces failure
        out = (res.stdout or "") + (res.stderr or "")
        if "not recognized as an internal or external command" in out:
            return False
        return res.returncode == 0 or len(res.stdout.strip()) > 0
    except Exception:
        return False

def get_installed_tool(tool_name: str, custom_path: str = "") -> str:
    """Find a verified tool executable either from custom_path, tools/ directory, or PATH."""
    if custom_path and os.path.isfile(custom_path) and _test_executable(custom_path):
        return str(Path(custom_path).resolve())

    # Check aliases first e.g. yowasp-yosys for yosys (immune to DLL and space issues)
    if tool_name == "yosys":
        yowasp = shutil.which("yowasp-yosys") or shutil.which("yowasp-yosys.exe")
        if yowasp and _test_executable(yowasp):
            return str(Path(yowasp).resolve())

    # Check system PATH
    found = shutil.which(tool_name)
    if found and _test_executable(found):
        return str(Path(found).resolve())

    # Check tools/ directory
    local_candidates = [
        TOOLS_DIR / f"{tool_name}.exe",
        TOOLS_DIR / "oss-cad-suite" / "bin" / f"{tool_name}.exe",
        TOOLS_DIR / "bin" / f"{tool_name}.exe",
        TOOLS_DIR / "iverilog" / "bin" / f"{tool_name}.exe",
    ]
    for cand in local_candidates:
        if cand.is_file() and _test_executable(str(cand)):
            return str(cand.resolve())

    return ""

def check_eda_environment():
    """Returns a dictionary reporting status of Yosys, Icarus Verilog, and VVP."""
    yosys = get_installed_tool("yosys")
    iverilog = get_installed_tool("iverilog")
    vvp = get_installed_tool("vvp")

    status = {
        "yosys": {
            "available": bool(yosys),
            "path": yosys,
            "version": _get_tool_version(yosys, ["-V"]) if yosys else None
        },
        "iverilog": {
            "available": bool(iverilog),
            "path": iverilog,
            "version": _get_tool_version(iverilog, ["-V"]) if iverilog else None
        },
        "vvp": {
            "available": bool(vvp),
            "path": vvp,
            "version": _get_tool_version(vvp, ["-V"]) if vvp else None
        }
    }
    return status

def _get_tool_version(executable: str, args: list) -> str:
    try:
        res = subprocess.run([executable] + args, capture_output=True, text=True, timeout=5)
        out = (res.stdout or res.stderr).strip().splitlines()
        return out[0] if out else "Unknown"
    except Exception as e:
        return f"Error: {e}"

def download_file_with_progress(url: str, dest_path: Path):
    """Download a file with console progress indicator."""
    print(f"Downloading from: {url}")
    print(f"Saving to: {dest_path}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    def _reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, (downloaded / total_size) * 100)
            mb_down = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            sys.stdout.write(f"\rProgress: [{percent:5.1f}%] {mb_down:6.1f}MB / {mb_total:6.1f}MB")
        else:
            sys.stdout.write(f"\rDownloaded {downloaded / (1024 * 1024):.1f}MB")
        sys.stdout.flush()

    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url, str(dest_path), _reporthook)
    print("\nDownload finished.")

def fetch_latest_oss_cad_suite_url() -> tuple[str, str]:
    """Query GitHub API for latest OSS CAD Suite Windows release."""
    api_url = f"https://api.github.com/repos/{OSS_CAD_SUITE_REPO}/releases/latest"
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    
    # Find windows asset (e.g. oss-cad-suite-windows-x64-*.exe or .zip)
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if "windows-x64" in name and (name.endswith(".exe") or name.endswith(".zip")):
            return asset.get("browser_download_url"), name
    
    raise RuntimeError("Could not find Windows asset in OSS CAD Suite latest release.")

def install_oss_cad_suite():
    """Downloads and extracts OSS CAD Suite into tools/oss-cad-suite."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        download_url, filename = fetch_latest_oss_cad_suite_url()
    except Exception as e:
        print(f"Failed to fetch latest OSS CAD Suite URL: {e}")
        # Direct fallback known release URL
        filename = "oss-cad-suite-windows-x64-latest.exe"
        download_url = f"https://github.com/YosysHQ/oss-cad-suite-build/releases/latest/download/{filename}"
    
    dest_file = TOOLS_DIR / filename
    if not dest_file.exists():
        download_file_with_progress(download_url, dest_file)
    
    extract_dir = TOOLS_DIR / "oss-cad-suite"
    print(f"Extracting package to: {extract_dir}")
    if filename.endswith(".zip"):
        with zipfile.ZipFile(dest_file, 'r') as zip_ref:
            zip_ref.extractall(TOOLS_DIR)
    elif filename.endswith(".exe"):
        # The .exe is typically a 7z SFX self-extracting archive
        # Run self-extractor into TOOLS_DIR
        print("Executing 7z self-extractor...")
        subprocess.run([str(dest_file), f"-o{str(TOOLS_DIR)}", "-y"], check=True)
        
    print(f"OSS CAD Suite installed successfully in {extract_dir}!")
    return extract_dir

if __name__ == "__main__":
    env = check_eda_environment()
    print("EDA Tools Environment:")
    for tool, info in env.items():
        print(f" - {tool}: {'[FOUND] ' + str(info['path']) if info['available'] else '[NOT FOUND]'}")

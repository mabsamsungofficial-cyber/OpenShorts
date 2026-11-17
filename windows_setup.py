"""
OpenShorts - Windows Automated Setup & Compatibility Initializer
This script runs automatically when starting OpenShorts on Windows.
It ensures all Windows-specific shims, dependencies, FFmpeg, and desktop shortcuts are configured.
"""
import os
import sys
import site
import subprocess
import shutil

FCNTL_SHIM = '''"""
Windows compatibility shim for fcntl.
Provides flock and standard constants for Unix-oriented libraries running on Windows.
"""
import os
import msvcrt

LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8

def flock(fd, operation):
    if hasattr(fd, "fileno"):
        fd = fd.fileno()
    try:
        if operation & LOCK_UN:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        elif operation & LOCK_NB:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
    except (OSError, IOError):
        if operation & LOCK_NB:
            raise
        pass

def fcntl(fd, op, arg=0):
    return 0

def ioctl(fd, op, arg=0, mutate_flag=True):
    return 0
'''

SITECUSTOMIZE_SHIM = '''import sys
import os
import subprocess
import socket
import types

# 1. Prefer IPv4 to avoid [WinError 10054] connection resets from ISPs where IPv6 to CDNs fails
_orig_getaddrinfo = socket.getaddrinfo
def _getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0 or family == socket.AF_UNSPEC:
        family = socket.AF_INET
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _getaddrinfo_ipv4

# 2. Windows compatibility shims
if sys.platform == "win32":
    if not hasattr(os, "nice"):
        os.nice = lambda n: 0

    if "resource" not in sys.modules:
        class _RUsage:
            ru_utime = 0.0
            ru_stime = 0.0
        _res = types.ModuleType("resource")
        _res.RUSAGE_SELF = 0
        _res.RUSAGE_CHILDREN = 1
        _res.getrusage = lambda who: _RUsage()
        sys.modules["resource"] = _res

    _orig_popen_init = subprocess.Popen.__init__
    def _patched_popen_init(self, *args, **kwargs):
        if "preexec_fn" in kwargs:
            kwargs.pop("preexec_fn", None)
        return _orig_popen_init(self, *args, **kwargs)
    subprocess.Popen.__init__ = _patched_popen_init

try:
    import av
    _orig_av_open = av.open
    def _patched_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _patched_av_open
except Exception:
    pass
'''

def install_shims():
    """Install fcntl and sitecustomize shims into site-packages."""
    sp_dirs = site.getsitepackages()
    target_dir = None
    for d in sp_dirs:
        if os.path.exists(d) and "site-packages" in d:
            target_dir = d
            break
    if not target_dir and sp_dirs:
        target_dir = sp_dirs[0]

    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
        fcntl_path = os.path.join(target_dir, "fcntl.py")
        sitecust_path = os.path.join(target_dir, "sitecustomize.py")
        
        with open(fcntl_path, "w", encoding="utf-8") as f:
            f.write(FCNTL_SHIM)
        with open(sitecust_path, "w", encoding="utf-8") as f:
            f.write(SITECUSTOMIZE_SHIM)
        print("✓ Windows compatibility shims verified.")

def check_python_deps():
    """Ensure python requirements are installed."""
    try:
        import fastapi
        import uvicorn
        import faster_whisper
        import ultralytics
        import scenedetect
        import boto3
        import cv2
        import mediapipe
        print("✓ Core Python dependencies already installed.")
    except ImportError as e:
        print(f"📦 Missing dependency ({e.name}). Installing Python packages from requirements.txt...")
        req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_file, "boto3", "mediapipe==0.10.14"],
            check=True
        )
        print("✓ Python dependencies installed.")

def check_ffmpeg():
    """Ensure ffmpeg is available."""
    if shutil.which("ffmpeg") is None:
        print("⚠️ FFmpeg not found in PATH. Checking winget...")
        try:
            subprocess.run(
                ["winget", "install", "--id", "Gyan.FFmpeg", "-e", "--accept-package-agreements", "--accept-source-agreements"],
                check=True
            )
            print("✓ FFmpeg installed via winget.")
        except Exception:
            print("⚠️ Could not auto-install FFmpeg via winget.")
            print("Please install FFmpeg manually or add it to PATH.")
    else:
        print("✓ FFmpeg is available.")

def check_dashboard_deps():
    """Ensure dashboard node_modules exist."""
    dashboard_dir = os.path.join(os.path.dirname(__file__), "dashboard")
    node_modules = os.path.join(dashboard_dir, "node_modules")
    if not os.path.exists(node_modules):
        print("📦 Installing dashboard frontend dependencies (npm install)...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        subprocess.run([npm_cmd, "install"], cwd=dashboard_dir, check=True)
        print("✓ Dashboard dependencies installed.")
    else:
        print("✓ Dashboard dependencies already present.")

def create_desktop_shortcut():
    """Create OpenShorts desktop shortcut on Windows."""
    try:
        user_profile = os.environ.get("USERPROFILE")
        if not user_profile:
            return
        desktop = os.path.join(user_profile, "Desktop")
        if not os.path.exists(desktop):
            return

        shortcut_file = os.path.join(desktop, "OpenShorts.lnk")
        project_dir = os.path.abspath(os.path.dirname(__file__))
        target_bat = os.path.join(project_dir, "Start_OpenShorts.bat")
        icon_path = os.path.join(project_dir, "assets", "openshorts.ico")

        vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_file}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_bat}"
oLink.WorkingDirectory = "{project_dir}"
oLink.IconLocation = "{icon_path}"
oLink.Description = "OpenShorts - AI Short Video Generator"
oLink.Save
'''
        vbs_path = os.path.join(project_dir, "_temp_shortcut.vbs")
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        subprocess.run(["cscript", "//nologo", vbs_path], check=True)
        if os.path.exists(vbs_path):
            os.remove(vbs_path)
        print("✓ Desktop shortcut 'OpenShorts' ready on your Desktop!")
    except Exception:
        pass

def main():
    print("🔧 Running OpenShorts Windows Setup & Diagnostics...")
    install_shims()
    check_python_deps()
    check_ffmpeg()
    check_dashboard_deps()
    create_desktop_shortcut()
    print("🚀 All systems checked! Ready to launch.")

if __name__ == "__main__":
    main()

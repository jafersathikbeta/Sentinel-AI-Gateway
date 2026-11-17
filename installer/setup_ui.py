"""
Sentinel AI Gateway Windows Setup Wizard (dark-themed tkinter).

Installs Python 3.12 (if needed), creates a venv, pip-installs requirements,
installs FFmpeg via winget, pre-caches HF models, and creates a
Desktop shortcut.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import winshell
from win32com.client import Dispatch

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def project_root() -> Path:
    """Resolve the Sentinel AI Gateway project directory (must contain requirements.txt)."""
    if getattr(sys, "frozen", False):
        # PyInstaller onedir: Setup.exe lives in dist/Setup/ (payload: Sentinel_AI_Gateway/)
        candidates = [
            Path(sys.executable).resolve().parent,
            Path(sys.executable).resolve().parent.parent,
            Path(sys.executable).resolve().parent.parent.parent,
            Path.cwd(),
        ]
    else:
        candidates = [
            Path(__file__).resolve().parents[1],
            Path.cwd(),
        ]
    for c in candidates:
        if (c / "requirements.txt").exists() and (c / "run.py").exists():
            return c
    # Fall back to CWD — installer will fail clearly if files missing
    return Path.cwd()


ROOT = project_root()
VENV_PY = ROOT / "venv" / "Scripts" / "python.exe"
VENV_PIP = ROOT / "venv" / "Scripts" / "pip.exe"
VENV_PYTHONW = ROOT / "venv" / "Scripts" / "pythonw.exe"
ICON_CANDIDATES = [
    ROOT / "installer" / "icon.ico",
    ROOT / "icon.ico",
    Path(getattr(sys, "_MEIPASS", "")) / "icon.ico" if getattr(sys, "frozen", False) else None,
]


# ---------------------------------------------------------------------------
# Colors / theme
# ---------------------------------------------------------------------------

BG = "#0d1117"
PANEL = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#1f6feb"
ACCENT_HOVER = "#388bfd"
OK = "#3fb950"
ERR = "#f85149"
LOG_BG = "#010409"


class SentinelSetup(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Sentinel AI Gateway Setup")
        self.geometry("600x600")
        self.minsize(600, 600)
        self.configure(bg=BG)
        self.resizable(True, True)

        self._installing = False
        self._done = False

        self._build_style()
        self._build_ui()

        try:
            icon = next(p for p in ICON_CANDIDATES if p and p.exists())
            self.iconbitmap(default=str(icon))
        except Exception:
            pass

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=PANEL,
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
        )
        style.configure(
            "Dark.TFrame",
            background=BG,
        )

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x", padx=0, pady=0)

        brand = tk.Frame(header, bg=PANEL)
        brand.pack(fill="x", padx=20, pady=16)

        logo = tk.Canvas(brand, width=40, height=40, bg=PANEL, highlightthickness=0)
        logo.pack(side="left")
        logo.create_oval(2, 2, 38, 38, fill=ACCENT, outline="")
        logo.create_text(20, 20, text="A", fill="white", font=("Segoe UI", 14, "bold"))

        titles = tk.Frame(brand, bg=PANEL)
        titles.pack(side="left", padx=12)
        tk.Label(
            titles,
            text="Sentinel AI Gateway Setup",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            titles,
            text="Enterprise Cybersecurity AI Firewall — Windows Installer",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        # Pack footer first so Install/Finish are never clipped by the expanding body
        footer = tk.Frame(self, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        footer.pack(fill="x", side="bottom")

        self.create_shortcut_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            footer,
            text="Create a Desktop Shortcut",
            variable=self.create_shortcut_var,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=TEXT,
            selectcolor=PANEL,
            highlightthickness=0,
            font=("Segoe UI", 10),
            cursor="hand2",
        ).pack(anchor="w", padx=20, pady=(12, 0))

        self.install_btn = tk.Button(
            footer,
            text="Install",
            command=self._on_install,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=22,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        self.install_btn.pack(pady=10)

        self.finish_btn = tk.Button(
            footer,
            text="Finish",
            command=self.destroy,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=22,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            state="disabled",
        )
        self.finish_btn.pack(pady=10)
        self.finish_btn.pack_forget()

        self.cancel_btn = tk.Button(
            footer,
            text="Cancel",
            command=self._on_cancel,
            bg=PANEL,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=18,
            pady=8,
            font=("Segoe UI", 10),
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.cancel_btn.pack(pady=(0, 12))

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(
            body,
            text=f"Install location:\n{ROOT}",
            bg=BG,
            fg=MUTED,
            justify="left",
            font=("Consolas", 9),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        self.progress = ttk.Progressbar(
            body,
            mode="determinate",
            maximum=100,
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x", pady=(0, 8))

        self.status = tk.Label(
            body,
            text="Ready to install.",
            bg=BG,
            fg=TEXT,
            anchor="w",
            font=("Segoe UI", 10),
        )
        self.status.pack(fill="x", pady=(0, 8))

        log_frame = tk.Frame(body, bg=BORDER, bd=0)
        log_frame.pack(fill="both", expand=True)

        self.log = tk.Text(
            log_frame,
            bg=LOG_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
            height=12,
            padx=10,
            pady=8,
        )
        scroll = tk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.log.configure(state="disabled")

    # ----- logging helpers -----

    def _append_log(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def log_line(self, line: str) -> None:
        self.after(0, self._append_log, line.rstrip("\n"))

    def set_status(self, text: str) -> None:
        self.after(0, lambda: self.status.configure(text=text))

    def set_progress(self, value: float) -> None:
        self.after(0, lambda: self.progress.configure(value=value))

    # ----- process runner -----

    def run_cmd(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        env: dict | None = None,
        check: bool = True,
    ) -> int:
        self.log_line(f"> {' '.join(args)}")
        merged = os.environ.copy()
        if env:
            merged.update(env)
        # Force UTF-8 friendly output on Windows consoles
        merged.setdefault("PYTHONUTF8", "1")
        merged.setdefault("PYTHONIOENCODING", "utf-8")

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        proc = subprocess.Popen(
            args,
            cwd=str(cwd or ROOT),
            env=merged,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            self.log_line(line.rstrip("\n"))
        code = proc.wait()
        if check and code != 0:
            raise RuntimeError(f"Command failed ({code}): {' '.join(args)}")
        return code

    # ----- install steps -----

    def _find_python312(self) -> str | None:
        # Prefer explicit 3.12 on PATH / py launcher
        candidates = [
            shutil.which("python3.12"),
            shutil.which("python"),
        ]
        try:
            out = subprocess.check_output(
                ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if out:
                candidates.insert(0, out)
        except Exception:
            pass

        for c in candidates:
            if not c:
                continue
            try:
                ver = subprocess.check_output(
                    [c, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                if ver.startswith("3.12"):
                    return c
            except Exception:
                continue
        return None

    def _ensure_python312(self) -> str:
        """
        Always ensure Python 3.12 via winget FIRST (idempotent if already present),
        then resolve the interpreter for venv creation.
        """
        self.log_line(
            "Ensuring Python 3.12 via winget "
            "(silent; safe if already installed)…"
        )
        self.run_cmd(
            [
                "winget",
                "install",
                "Python.Python.3.12",
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            check=False,
        )
        # Refresh PATH from machine/user env after possible install
        self._refresh_path()

        found = self._find_python312()
        if found:
            self.log_line(f"Python 3.12 ready: {found}")
            return found

        raise RuntimeError(
            "Python 3.12 installation did not complete. "
            "Install Python 3.12 manually and re-run Setup."
        )

    def _refresh_path(self) -> None:
        try:
            import winreg

            paths: list[str] = []
            for root, sub in (
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                (winreg.HKEY_CURRENT_USER, r"Environment"),
            ):
                try:
                    with winreg.OpenKey(root, sub) as key:
                        val, _ = winreg.QueryValueEx(key, "Path")
                        paths.append(val)
                except OSError:
                    pass
            if paths:
                os.environ["PATH"] = os.pathsep.join(paths + [os.environ.get("PATH", "")])
        except Exception as exc:
            self.log_line(f"(PATH refresh note: {exc})")

    def _create_desktop_shortcut(self) -> None:
        # Ensure os.getcwd() resolves to the project root (Setup.exe may start elsewhere)
        os.chdir(ROOT)
        try:
            desktop = winshell.desktop()
            path = os.path.join(desktop, "Sentinel AI Gateway.lnk")
            target = os.path.join(os.getcwd(), "run_app.vbs")
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(path)
            shortcut.Targetpath = target
            shortcut.WorkingDirectory = os.getcwd()
            shortcut.IconLocation = os.path.join(os.getcwd(), "icon.ico")
            shortcut.save()
        except Exception as exc:
            self.log_line(f"Warning: desktop shortcut failed: {exc}")
            return

        if Path(path).exists():
            self.log_line(f"Desktop shortcut created: {path}")
        else:
            self.log_line("Warning: desktop shortcut was not created.")

    def _install_pipeline(self, create_shortcut: bool) -> None:
        steps = [
            ("Installing Python 3.12 via winget…", 5),
            ("Creating virtual environment…", 20),
            ("Installing Python packages…", 45),
            ("Installing FFmpeg…", 70),
            ("Caching Hugging Face models…", 88),
            ("Creating Desktop shortcut…", 96),
            ("Finishing…", 100),
        ]

        self.set_status(steps[0][0])
        self.set_progress(steps[0][1])
        py = self._ensure_python312()

        self.set_status(steps[1][0])
        self.set_progress(steps[1][1])
        venv_dir = ROOT / "venv"
        if not VENV_PY.exists():
            self.run_cmd([py, "-m", "venv", str(venv_dir)])
        else:
            self.log_line("venv already exists — reusing.")

        self.set_status(steps[2][0])
        self.set_progress(steps[2][1])
        if not (ROOT / "requirements.txt").exists():
            raise RuntimeError(f"requirements.txt not found in {ROOT}")
        self.run_cmd([str(VENV_PY), "-m", "pip", "install", "--upgrade", "pip"])
        self.run_cmd(
            [str(VENV_PIP), "install", "-r", str(ROOT / "requirements.txt")]
        )

        self.set_status(steps[3][0])
        self.set_progress(steps[3][1])
        for pkg_id, label in (
            ("Gyan.FFmpeg", "FFmpeg"),
        ):
            self.log_line(f"Installing {label} ({pkg_id}) via winget…")
            self.run_cmd(
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    pkg_id,
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
                check=False,
            )

        self.set_status(steps[4][0])
        self.set_progress(steps[4][1])
        model_script = ROOT / "installer" / "download_models.py"
        if not model_script.exists():
            # When frozen, copy from _MEIPASS if bundled
            meipass = Path(getattr(sys, "_MEIPASS", ""))
            alt = meipass / "download_models.py"
            if alt.exists():
                model_script = alt
        if model_script.exists():
            self.run_cmd([str(VENV_PY), str(model_script)])
        else:
            self.log_line("download_models.py missing — skipping model cache.")

        self.set_status(steps[5][0])
        self.set_progress(steps[5][1])
        if create_shortcut:
            self._create_desktop_shortcut()
        else:
            self.log_line("Desktop shortcut skipped (unchecked).")

        # Fresh ledger for first launch after install
        audit_log = ROOT / ".sentinel_install.log"
        try:
            if audit_log.exists():
                audit_log.unlink()
                self.log_line("Cleared existing .sentinel_install.log for a fresh ledger.")
        except Exception as exc:
            self.log_line(f"Warning: could not delete .sentinel_install.log: {exc}")

        self.set_status("Installation complete.")
        self.set_progress(100)
        self.log_line("")
        self.log_line("=== Sentinel AI Gateway installed successfully ===")
        self.log_line("Launch from the Desktop shortcut, or run: run_app.vbs")

    def _on_install(self) -> None:
        if self._done or self._installing:
            return
        self._installing = True
        # Capture checkbox state on the UI thread before starting the worker
        create_shortcut = bool(self.create_shortcut_var.get())
        self.install_btn.configure(state="disabled", text="Installing…")
        self.finish_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")

        def worker(create_shortcut: bool) -> None:
            try:
                self._install_pipeline(create_shortcut)
            except Exception as exc:
                self.log_line(f"ERROR: {exc}")
                self.set_status("Installation failed.")
                self.after(
                    0,
                    lambda: messagebox.showerror("Sentinel AI Gateway Setup", f"Install failed:\n{exc}"),
                )
                self.after(
                    0,
                    lambda: self.install_btn.configure(state="normal", text="Retry"),
                )
                self.after(0, lambda: self.cancel_btn.configure(state="normal"))
                self._installing = False
                return

            self._done = True
            self._installing = False

            def finish_ui() -> None:
                self.install_btn.pack_forget()
                self.finish_btn.pack(pady=10)
                self.finish_btn.config(state=tk.NORMAL)
                self.cancel_btn.configure(state="disabled")
                messagebox.showinfo(
                    "Sentinel AI Gateway Setup",
                    "Installation complete!\n\nUse the Desktop shortcut to launch Sentinel AI Gateway.",
                )

            self.after(0, finish_ui)

        threading.Thread(target=worker, args=(create_shortcut,), daemon=True).start()

    def _on_cancel(self) -> None:
        if self._installing:
            if not messagebox.askyesno(
                "Sentinel AI Gateway Setup",
                "Installation is in progress. Exit anyway?",
            ):
                return
        self.destroy()


def main() -> None:
    app = SentinelSetup()
    app.mainloop()


if __name__ == "__main__":
    main()

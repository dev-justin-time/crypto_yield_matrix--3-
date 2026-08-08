"""Simple GUI to start and monitor all 12 Blocks agents.

Requires nothing beyond Python stdlib (tkinter). Double-click or run:
    python src/deployments/agent_gui.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import Tk, Frame, Label, Button, Canvas, messagebox, BOTH, LEFT, RIGHT, X, Y, GROOVE
from tkinter.font import Font

ROOT = Path(__file__).resolve().parents[2]
DEPLOY_ROOT = ROOT / "blocks_deploy"
LOG_DIR = ROOT / "blocks-agent-logs"
ENV_PATH = ROOT / ".env"

AGENTS = sorted(
    d.name for d in DEPLOY_ROOT.iterdir()
    if d.is_dir() and (d / "pyproject.toml").exists()
)

def load_api_key() -> str:
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("BLOCKS_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""

API_KEY = load_api_key()


def agent_status(name: str) -> str:
    """Check agent status from log file."""
    log = LOG_DIR / f"{name}.log"
    if not log.exists():
        return "stopped"
    try:
        text = log.read_text()
        if "Registered agent:" in text and "running (press Ctrl+C to stop)" in text:
            return "running"
        if "RuntimeError" in text or "Error" in text:
            return "error"
    except OSError:
        pass
    return "starting"


def start_agent(name: str) -> subprocess.Popen | None:
    """Start a single agent in the background."""
    agent_dir = DEPLOY_ROOT / name
    venv_python = agent_dir / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        return None

    log_file = LOG_DIR / f"{name}.log"
    LOG_DIR.mkdir(exist_ok=True)

    env = {**os.environ, "BLOCKS_API_KEY": API_KEY, "PYTHONUNBUFFERED": "1"}
    with open(log_file, "w") as f:
        return subprocess.Popen(
            [str(venv_python), "-m", "blocks_network"],
            cwd=str(agent_dir),
            stdout=f,
            stderr=subprocess.STDOUT,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )


def stop_agent(name: str) -> None:
    """Stop an agent by killing its python process."""
    # Look for the python process running from the agent's venv
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/FI", f"IMAGENAME eq python.exe", "/FI", f"WINDOWTITLE eq *{name}*"],
            capture_output=True,
        )
    else:
        subprocess.run(["pkill", "-f", f"blocks_deploy/{name}"], capture_output=True)


class AgentGUI:
    def __init__(self):
        self.root = Tk()
        self.root.title("Crypto Yield Matrix — Agent Control Panel")
        self.root.geometry("680x580")
        self.root.configure(bg="#0f172a")
        self.root.resizable(True, True)

        # Fonts
        self.title_font = Font(family="Segoe UI", size=16, weight="bold")
        self.agent_font = Font(family="Consolas", size=11)
        self.status_font = Font(family="Segoe UI", size=9)
        self.btn_font = Font(family="Segoe UI", size=9, weight="bold")

        # Header
        header = Frame(self.root, bg="#1e293b", pady=12)
        header.pack(fill=X)
        Label(
            header, text="⚡ Crypto Yield Matrix — 12 Agents",
            font=self.title_font, fg="#38bdf8", bg="#1e293b",
        ).pack()

        # API key status
        key_status = "✅ API key loaded" if API_KEY else "❌ No API key — create .env with BLOCKS_API_KEY"
        Label(
            header, text=key_status,
            font=self.status_font,
            fg="#22c55e" if API_KEY else "#ef4444", bg="#1e293b",
        ).pack(pady=(4, 0))

        # Main content
        content = Frame(self.root, bg="#0f172a", padx=16, pady=12)
        content.pack(fill=BOTH, expand=True)

        # Agent list header
        list_header = Frame(content, bg="#1e293b")
        list_header.pack(fill=X, pady=(0, 4))
        for col, w in [("Agent", 34), ("Status", 12), ("Action", 14)]:
            Label(
                list_header, text=col, font=self.status_font,
                fg="#94a3b8", bg="#1e293b", width=w, anchor="w",
            ).pack(side=LEFT, padx=(16 if col == "Agent" else 4, 4), pady=4)

        # Scrollable agent list
        canvas = Canvas(content, bg="#0f172a", highlightthickness=0, height=380)
        scroll_frame = Frame(canvas, bg="#0f172a")
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.pack(fill=BOTH, expand=True, pady=(0, 8))

        self.agent_frames: dict[str, Frame] = {}
        self.status_labels: dict[str, Label] = {}
        self.action_buttons: dict[str, Button] = {}
        self.processes: dict[str, subprocess.Popen | None] = {}

        for name in AGENTS:
            frame = Frame(scroll_frame, bg="#1e293b", pady=3)
            frame.pack(fill=X, pady=1)

            # Agent name
            Label(
                frame, text=f"  {name}", font=self.agent_font,
                fg="#e2e8f0", bg="#1e293b", anchor="w", width=34,
            ).pack(side=LEFT, padx=(4, 4))

            # Status indicator
            status = Label(
                frame, text="● stopped", font=self.status_font,
                fg="#64748b", bg="#1e293b", width=12, anchor="w",
            )
            status.pack(side=LEFT, padx=4)
            self.status_labels[name] = status

            # Action button
            btn = Button(
                frame, text="▶ Start", font=self.btn_font,
                bg="#16a34a", fg="white", activebackground="#22c55e",
                relief="flat", cursor="hand2", padx=12, pady=2,
                command=lambda n=name: self.toggle_agent(n),
            )
            btn.pack(side=RIGHT, padx=8)
            self.action_buttons[name] = btn
            self.agent_frames[name] = frame

        # Bottom control bar
        controls = Frame(self.root, bg="#1e293b", pady=10)
        controls.pack(fill=X, side="bottom")

        Button(
            controls, text="▶ Start All Agents", font=self.btn_font,
            bg="#2563eb", fg="white", activebackground="#3b82f6",
            relief="flat", cursor="hand2", padx=20, pady=6,
            command=self.start_all,
        ).pack(side=LEFT, padx=12)

        Button(
            controls, text="■ Stop All Agents", font=self.btn_font,
            bg="#dc2626", fg="white", activebackground="#ef4444",
            relief="flat", cursor="hand2", padx=20, pady=6,
            command=self.stop_all,
        ).pack(side=LEFT, padx=4)

        Label(
            controls, text="", font=self.status_font, fg="#94a3b8", bg="#1e293b",
        ).pack(side=LEFT, padx=12)

        Button(
            controls, text="↻ Refresh", font=self.btn_font,
            bg="#475569", fg="white", activebackground="#64748b",
            relief="flat", cursor="hand2", padx=16, pady=6,
            command=self.refresh_status,
        ).pack(side=RIGHT, padx=12)

        # Status bar
        self.status_bar = Label(
            self.root, text="Ready — 0/12 running", font=self.status_font,
            fg="#94a3b8", bg="#0f172a", anchor="w", pady=4, padx=12,
        )
        self.status_bar.pack(fill=X, side="bottom")

        # Periodic refresh
        self.refresh_status()
        self.root.after(3000, self._auto_refresh)
        self.root.mainloop()

    def _auto_refresh(self) -> None:
        self.refresh_status()
        self.root.after(3000, self._auto_refresh)

    def toggle_agent(self, name: str) -> None:
        status = agent_status(name)
        if status in ("running", "starting"):
            threading.Thread(target=self._stop_one, args=(name,), daemon=True).start()
        else:
            threading.Thread(target=self._start_one, args=(name,), daemon=True).start()
        self.root.after(1500, self.refresh_status)

    def _start_one(self, name: str) -> None:
        self.status_labels[name].config(text="● starting", fg="#f59e0b")
        self.action_buttons[name].config(text="...", state="disabled")
        proc = start_agent(name)
        if proc:
            self.processes[name] = proc

    def _stop_one(self, name: str) -> None:
        self.status_labels[name].config(text="● stopping", fg="#f59e0b")
        self.action_buttons[name].config(text="...", state="disabled")
        stop_agent(name)

    def start_all(self) -> None:
        if not API_KEY:
            messagebox.showerror("No API Key", "Create a .env file with BLOCKS_API_KEY first.")
            return
        threading.Thread(target=self._start_all_thread, daemon=True).start()

    def _start_all_thread(self) -> None:
        for name in AGENTS:
            if agent_status(name) in ("running", "starting"):
                continue
            self.root.after(0, lambda n=name: (
                self.status_labels[n].config(text="● starting", fg="#f59e0b"),
                self.action_buttons[n].config(text="...", state="disabled"),
            ))
            proc = start_agent(name)
            if proc:
                self.processes[name] = proc
            time.sleep(1.5)  # Stagger starts to avoid thundering herd
        self.root.after(2000, self.refresh_status)

    def stop_all(self) -> None:
        threading.Thread(target=self._stop_all_thread, daemon=True).start()

    def _stop_all_thread(self) -> None:
        for name in AGENTS:
            if agent_status(name) == "stopped":
                continue
            self.root.after(0, lambda n=name: (
                self.status_labels[n].config(text="● stopping", fg="#f59e0b"),
                self.action_buttons[n].config(text="...", state="disabled"),
            ))
            stop_agent(name)
            time.sleep(0.5)
        self.root.after(2000, self.refresh_status)

    def refresh_status(self) -> None:
        running = 0
        for name in AGENTS:
            status = agent_status(name)
            if status == "running":
                self.status_labels[name].config(text="● running", fg="#22c55e")
                self.action_buttons[name].config(text="■ Stop", bg="#dc2626", fg="white", state="normal", activebackground="#ef4444")
                running += 1
            elif status == "starting":
                self.status_labels[name].config(text="● starting", fg="#f59e0b")
                self.action_buttons[name].config(text="...", state="disabled")
            elif status == "error":
                self.status_labels[name].config(text="⚠ error", fg="#ef4444")
                self.action_buttons[name].config(text="▶ Start", bg="#16a34a", fg="white", state="normal", activebackground="#22c55e")
            else:
                self.status_labels[name].config(text="● stopped", fg="#64748b")
                self.action_buttons[name].config(text="▶ Start", bg="#16a34a", fg="white", state="normal", activebackground="#22c55e")
        self.status_bar.config(text=f"{running}/12 agents running — API key: {'✅ loaded' if API_KEY else '❌ missing'}")


if __name__ == "__main__":
    AgentGUI()

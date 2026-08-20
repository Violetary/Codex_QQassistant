from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, Button, Frame, Label, Tk, messagebox, scrolledtext


ROOT = Path(__file__).resolve().parent
PYTHON = Path(r"C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
BOT_PORT = 8000
NAPCAT_PORT = 3000
BRIDGE_URL = f"http://127.0.0.1:{BOT_PORT}"
LOG_DIR = ROOT / "logs"
CONTROL_LOG = LOG_DIR / "control-panel.log"


class ControlPanel:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("QQ 洛克王国机器人控制面板")
        self.root.geometry("920x640")
        self.root.minsize(820, 540)

        self.status_label = Label(self.root, text="正在读取状态...", anchor="w", font=("Microsoft YaHei UI", 11))
        self.status_label.pack(fill="x", padx=12, pady=(12, 6))

        button_area = Frame(self.root)
        button_area.pack(fill="x", padx=12, pady=6)

        self._button(button_area, "启动机器人", self.start_bot).pack(side=LEFT, padx=4)
        self._button(button_area, "关闭机器人", self.stop_bot).pack(side=LEFT, padx=4)
        self._button(button_area, "启动 NapCat/QQ", self.start_napcat).pack(side=LEFT, padx=4)
        self._button(button_area, "关闭 NapCat", self.stop_napcat).pack(side=LEFT, padx=4)
        self._button(button_area, "全部启动", self.start_all).pack(side=LEFT, padx=4)
        self._button(button_area, "全部关闭", self.stop_all).pack(side=LEFT, padx=4)

        button_area2 = Frame(self.root)
        button_area2.pack(fill="x", padx=12, pady=6)
        self._button(button_area2, "刷新状态", self.refresh_status).pack(side=LEFT, padx=4)
        self._button(button_area2, "查看诊断", self.refresh_diagnostics).pack(side=LEFT, padx=4)
        self._button(button_area2, "一键更新数据库", self.update_database).pack(side=LEFT, padx=4)
        self._button(button_area2, "打开图片目录", self.open_cards_dir).pack(side=LEFT, padx=4)
        self._button(button_area2, "打开日志目录", self.open_logs_dir).pack(side=LEFT, padx=4)

        hint = Label(
            self.root,
            text="提示：首次登录或掉线时点“启动 NapCat/QQ”，在弹出的 QQ/NapCat 窗口完成登录。机器人查询服务可以隐藏运行。",
            anchor="w",
            fg="#555555",
            font=("Microsoft YaHei UI", 9),
        )
        hint.pack(fill="x", padx=12, pady=(2, 8))

        self.output = scrolledtext.ScrolledText(self.root, wrap="word", font=("Consolas", 10))
        self.output.pack(fill=BOTH, expand=True, padx=12, pady=(0, 12))

        bottom = Frame(self.root)
        bottom.pack(fill="x", padx=12, pady=(0, 12))
        Label(bottom, text=f"项目目录：{ROOT}", anchor="w", fg="#666666").pack(side=LEFT)
        Button(bottom, text="退出面板", command=self.root.destroy).pack(side=RIGHT)

        self.refresh_status()
        self.root.after(8000, self._auto_refresh)

    def run(self) -> None:
        self.root.mainloop()

    def _button(self, parent: Frame, text: str, command) -> Button:  # type: ignore[no-untyped-def]
        return Button(parent, text=text, command=command, width=14, height=2)

    def _auto_refresh(self) -> None:
        self.refresh_status(silent=True)
        self.root.after(8000, self._auto_refresh)

    def start_bot(self) -> None:
        if self._port_pid(BOT_PORT):
            self._write("机器人桥接已经在运行。")
            self.refresh_status()
            return
        script = ROOT / "scripts" / "start_bot_onebot.ps1"
        self._start_powershell(script, visible=False)
        self._write("已启动机器人桥接，等待健康检查...")
        self.root.after(2500, self.refresh_status)

    def stop_bot(self) -> None:
        self._stop_port(BOT_PORT, "机器人桥接")
        self.refresh_status()

    def start_napcat(self) -> None:
        if self._port_pid(NAPCAT_PORT):
            self._write("NapCat API 已经在运行。")
            self.refresh_status()
            return
        script = ROOT / "scripts" / "start_napcat.ps1"
        self._start_powershell(script, visible=True)
        self._write("已打开 NapCat/QQ 启动窗口。若需要扫码或登录，请在弹出的窗口操作。")
        self.root.after(3500, self.refresh_status)

    def stop_napcat(self) -> None:
        if messagebox.askyesno("确认关闭", "要关闭 NapCat/QQ API 进程吗？这可能会让机器人 QQ 下线。"):
            self._stop_port(NAPCAT_PORT, "NapCat API")
            self.refresh_status()

    def start_all(self) -> None:
        self.start_bot()
        self.root.after(1500, self.start_napcat)

    def stop_all(self) -> None:
        self.stop_bot()
        if messagebox.askyesno("确认关闭", "是否同时关闭 NapCat/QQ API？"):
            self._stop_port(NAPCAT_PORT, "NapCat API")
        self.refresh_status()

    def update_database(self) -> None:
        if not messagebox.askyesno("确认更新", "一键更新会花几分钟，并会重启机器人桥接。现在开始吗？"):
            return
        script = ROOT / "scripts" / "update_database_and_restart.ps1"
        self._run_background("一键更新数据库", ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)])

    def refresh_status(self, silent: bool = False) -> None:
        bot_pid = self._port_pid(BOT_PORT)
        napcat_pid = self._port_pid(NAPCAT_PORT)
        health = self._get_json(f"{BRIDGE_URL}/health") if bot_pid else None
        bot_state = f"运行中 PID {bot_pid}" if bot_pid else "未运行"
        napcat_state = f"运行中 PID {napcat_pid}" if napcat_pid else "未运行"
        health_state = "健康" if health and health.get("ok") else "未连接"
        self.status_label.config(text=f"机器人：{bot_state} | 健康：{health_state} | NapCat API：{napcat_state}")
        if not silent:
            self._write(f"状态刷新：机器人={bot_state}，健康={health_state}，NapCat={napcat_state}")

    def refresh_diagnostics(self) -> None:
        data = self._get_json(f"{BRIDGE_URL}/diagnostics")
        if not data:
            self._write("诊断失败：机器人桥接未运行或 /diagnostics 不可访问。")
            return
        self._write("诊断信息：")
        self._write(json.dumps(data, ensure_ascii=False, indent=2))

    def open_cards_dir(self) -> None:
        path = ROOT / "outputs" / "cards"
        path.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer.exe", str(path)])

    def open_logs_dir(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer.exe", str(LOG_DIR)])

    def _start_powershell(self, script: Path, visible: bool) -> None:
        if not script.exists():
            messagebox.showerror("文件不存在", str(script))
            return
        command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
        creationflags = subprocess.CREATE_NEW_CONSOLE if visible else subprocess.CREATE_NO_WINDOW
        log_file = (LOG_DIR / f"{script.stem}.log").open("a", encoding="utf-8")
        subprocess.Popen(command, cwd=ROOT, stdout=log_file, stderr=subprocess.STDOUT, creationflags=creationflags)
        self._log(f"started {script.name}")

    def _run_background(self, title: str, command: list[str]) -> None:
        def worker() -> None:
            self._write(f"{title} 开始...")
            started = time.perf_counter()
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            assert process.stdout is not None
            for line in process.stdout:
                self._write(line.rstrip())
            code = process.wait()
            seconds = round(time.perf_counter() - started, 1)
            self._write(f"{title} 结束，退出码={code}，耗时={seconds}s")
            self.refresh_status()
            if code == 0:
                messagebox.showinfo("完成", f"{title} 已完成。")
            else:
                messagebox.showerror("失败", f"{title} 失败，退出码：{code}")

        threading.Thread(target=worker, daemon=True).start()

    def _stop_port(self, port: int, label: str) -> None:
        pid = self._port_pid(port)
        if not pid:
            self._write(f"{label} 未运行。")
            return
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="replace",
        )
        if result.returncode == 0:
            self._write(f"已关闭 {label}，PID {pid}。")
            self._log(f"stopped {label} pid={pid}")
        else:
            self._write(f"关闭 {label} 失败：{result.stdout}{result.stderr}")

    def _port_pid(self, port: int) -> int | None:
        result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, encoding="gbk", errors="replace")
        marker = f":{port}"
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[1].endswith(marker) and parts[3].upper() == "LISTENING":
                try:
                    return int(parts[4])
                except ValueError:
                    return None
        return None

    def _get_json(self, url: str) -> dict | None:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def _write(self, text: str) -> None:
        def append() -> None:
            stamp = datetime.now().strftime("%H:%M:%S")
            self.output.insert(END, f"[{stamp}] {text}\n")
            self.output.see(END)
            self._log(text)

        self.root.after(0, append)

    def _log(self, text: str) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with CONTROL_LOG.open("a", encoding="utf-8") as file:
            file.write(f"{datetime.now().isoformat(timespec='seconds')} {text}\n")


if __name__ == "__main__":
    ControlPanel().run()

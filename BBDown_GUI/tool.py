import os
import signal
import subprocess
import sys
import time

# Windows: 启动控制台子进程（BBDown.exe / taskkill）时不弹出黑窗
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def get_workdir():
    if getattr(sys, "frozen", False):
        workdir = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        workdir = os.path.dirname(os.path.abspath(__file__))
    return workdir

def get_bbdowndir():
    bbdowndir = os.path.join(get_workdir(), "BBDown.exe")
    return bbdowndir

# 显示图标
# 单文件打包引入外部资源
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = get_workdir()
    return os.path.join(base_path, relative_path)

def log(message=''):
    t = time.time()
    return f'[{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))}.{int(t * 1000) % 1000}] - {message}'


def decode_line(data: bytes) -> str:
    """把 BBDown 子进程 stdout 的一行 bytes 解码为 str（剥掉行尾换行）。

    实测（BBDown v1.7.3）：stdout 重定向到管道时是 UTF-8、行尾 \r\n、
    无 ANSI/ESC 字节，正常不会解码失败；万一失败（旧版二进制/被第三方包装）
    再按 GBK 兜底 + errors="replace"，保证显示层永不崩。
    """
    if data.endswith(b"\r\n"):
        data = data[:-2]
    elif data.endswith(b"\n") or data.endswith(b"\r"):
        data = data[:-1]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("gbk", errors="replace")


def get_bbdowndata_dir(exe_path: str) -> str:
    """凭据文件所在目录 = BBDown.exe 所在目录。

    CLI 的数据目录 APP_DIR 是 AppContext.BaseDirectory（Program.cs），即 exe
    目录；BBDown.data / BBDownTV.data 都写在 exe 同目录，与 GUI 工作目录及
    GUI 进程的 cwd 无关。
    """
    return os.path.dirname(os.path.abspath(exe_path))


def get_credential_path(exe_path: str, mode: str) -> str:
    """mode: "login" -> BBDown.data（cookie 串）；"logintv" -> BBDownTV.data（access_token）。"""
    name = "BBDownTV.data" if mode == "logintv" else "BBDown.data"
    return os.path.join(get_bbdowndata_dir(exe_path), name)


def kill_process_tree(pid: int) -> bool:
    """强杀整棵进程树（BBDown 下载中可能拉出 ffmpeg/aria2c）。"""
    if os.name != "nt":
        try:
            os.kill(pid, signal.SIGKILL)
            return True
        except OSError:
            return False
    try:
        return subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        ).returncode == 0
    except OSError:
        return False

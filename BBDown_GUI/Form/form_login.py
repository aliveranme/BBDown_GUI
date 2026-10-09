import os
import queue
import re
import subprocess
import tempfile
import threading

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QThread, QTimer, pyqtSignal

from BBDown_GUI.UI.ui_qrcode import Ui_Form_QRcode
from BBDown_GUI.tool import (CREATE_NO_WINDOW, decode_line, get_bbdowndir,
                             get_credential_path, get_workdir, kill_process_tree,
                             resource_path)

_LOG_PREFIX = re.compile(r"^\[\d{4}-\d{2}-\d{2} [\d:.]+\] - ")
_QR_BLOCK_CHARS = set("█ ")


def _snapshot(path):
    """凭据文件 (mtime_ns, size) 快照；不存在返回 None。"""
    try:
        st = os.stat(path)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


class LoginThread(QThread):
    """驱动 BBDown login/logintv：

    - cwd 固定（GUI 工作目录，不可写则临时目录），qrcode.png 就生成在这里；
    - 启动前删除旧 qrcode.png（强杀残留，CLI 的 finally 不会清理）；
    - 后台线程逐行读 stdout；主循环每 0.1s 检查进程存活/二维码/凭据文件，
      进程一退出立即收敛结局，不再固定空转 181 秒。
    """
    label_signal = pyqtSignal(str)           # 更新状态 label
    qrcode_signal = pyqtSignal(str)          # qrcode.png 路径（稳定出现时发一次）
    finished_signal = pyqtSignal(bool, str)  # (是否成功, 结局文案)

    def __init__(self, exe_path: str, mode: str, parent=None):
        super().__init__(parent)
        self.exe_path = exe_path
        self.mode = mode                     # "login" / "logintv"（= CLI 子命令名）
        self.cwd = get_workdir()
        self.p = None
        self._stop_requested = False
        self._expired = False

    @staticmethod
    def _pick_cwd():
        """优先 GUI 工作目录；不可写（如装在 Program Files）时退到系统临时目录。"""
        for d in (get_workdir(), tempfile.gettempdir()):
            probe = os.path.join(d, ".bbdown_gui_write_test.tmp")
            try:
                with open(probe, "w") as f:
                    f.write("")
                os.remove(probe)
                return d
            except OSError:
                continue
        return tempfile.gettempdir()

    def run(self):
        self.cwd = self._pick_cwd()
        qr_path = os.path.join(self.cwd, "qrcode.png")
        cred_path = get_credential_path(self.exe_path, self.mode)
        cred_before = _snapshot(cred_path)

        # 启动前删除旧二维码，避免把上一轮强杀残留的图当成新图
        try:
            if os.path.exists(qr_path):
                os.remove(qr_path)
        except OSError:
            pass

        try:
            self.p = subprocess.Popen(
                [self.exe_path, self.mode],
                cwd=self.cwd,                      # CLI 的 qrcode.png 落在 cwd
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError as e:
            self.finished_signal.emit(False, f"无法启动 BBDown.exe: {e}")
            return

        if self._stop_requested:
            kill_process_tree(self.p.pid)

        # 后台读线程 + 队列：主循环得以固定节拍检查文件与进程状态
        line_queue = queue.Queue()
        sentinel = object()

        def reader():
            try:
                for line in iter(self.p.stdout.readline, b""):
                    line_queue.put(line)
            finally:
                line_queue.put(sentinel)

        threading.Thread(target=reader, daemon=True).start()

        qr_emitted = False
        qr_last_size = -1
        success_line_seen = False
        rc = None

        while True:
            try:
                item = line_queue.get(timeout=0.1)
            except queue.Empty:
                item = None
            if item is sentinel:
                rc = self.p.wait()
                break
            if isinstance(item, (bytes, bytearray)):
                text = decode_line(item)
                if self._handle_line(text):
                    success_line_seen = True

            # 旧图已删，qrcode.png 出现即本轮生成；等文件大小连续两次一致
            # 再读数，避免加载到写入中途的半张图
            if not qr_emitted and os.path.exists(qr_path):
                try:
                    size = os.path.getsize(qr_path)
                except OSError:
                    size = -1
                if size > 0 and size == qr_last_size:
                    qr_emitted = True
                    self.qrcode_signal.emit(qr_path)
                    self.label_signal.emit("请使用 Bilibili 手机客户端扫码")
                qr_last_size = size

        # ---- 结局判定 ----
        cred_after = _snapshot(cred_path)
        cred_changed = cred_after is not None and cred_after != cred_before

        if self._stop_requested:
            self.finished_signal.emit(False, "已取消")
        elif rc == 0 and (cred_changed or success_line_seen):
            self.finished_signal.emit(True, "登录成功")
        elif self._expired:
            self.finished_signal.emit(False, "二维码已过期, 请重新登录")
        elif rc == 0:
            self.finished_signal.emit(False, "登录结束，但未检测到新凭据")
        else:
            self.finished_signal.emit(False, f"登录失败（退出码 {rc}）")

    def _handle_line(self, text: str) -> bool:
        """过滤方块二维码/启动横幅噪音，把日志行映射成 label 文案；返回是否见到成功日志。"""
        stripped = text.strip()
        if not stripped or set(stripped) <= _QR_BLOCK_CHARS:
            return False                        # 控制台方块二维码 / 空行
        if "BBDown version" in stripped or "github.com" in stripped or "遇到问题请首先" in stripped:
            return False                        # 启动横幅
        line = _LOG_PREFIX.sub("", stripped)    # 去掉 [时间戳] - 前缀

        if "扫码成功" in line:
            self.label_signal.emit("扫码成功, 请确认...")
        elif "二维码已过期" in line:
            self._expired = True
            self.label_signal.emit("二维码已过期, 请关闭窗口后重试")
        elif "未取得有效凭证" in line:
            self.label_signal.emit("登录成功但未取得有效凭证")
        elif "登录成功" in line:
            self.label_signal.emit("登录成功")
            return True
        elif ("登录失败" in line) or ("超时" in line) or ("登录已取消" in line):
            self.label_signal.emit(line[:60])
        elif "请扫描下方打印的控制台二维码" in line:
            self.label_signal.emit("二维码图片不可用（请用命令行窗口扫描）")
        elif "生成二维码" in line:
            self.label_signal.emit("二维码生成中...")
        elif "获取登录地址" in line:
            self.label_signal.emit("获取登录地址...")
        return False

    def stop(self):
        """窗口关闭时调用：停掉子进程（进程树）。"""
        self._stop_requested = True
        if self.p is not None:
            try:
                if self.p.poll() is None:
                    kill_process_tree(self.p.pid)
            except OSError:
                pass


class FormLogin(QMainWindow, Ui_Form_QRcode):
    def __init__(self, arg, exe_path=None, parent=None):
        super(FormLogin, self).__init__(parent)
        self.arg = arg
        self.exe_path = os.path.abspath(exe_path or get_bbdowndir())
        self.setupUi(self)
        icon = QIcon()
        icon.addPixmap(QPixmap(resource_path("./UI/favicon.ico")), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.label_QR.setScaledContents(True)
        self.label.setText("获取二维码中")

        # 注意：不再预删已有凭据文件。CLI 成功时会覆盖写；登录失败应保留旧凭据
        # （旧实现先删再登录：失败即丢失既有登录态）。
        self.work = LoginThread(self.exe_path, arg)
        self.work.label_signal.connect(self.label.setText)
        self.work.qrcode_signal.connect(self.show_qrcode)
        self.work.finished_signal.connect(self.on_finished)
        self.work.start()

    def show_qrcode(self, path):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.label_QR.setPixmap(pixmap)

    def on_finished(self, ok, message):
        self.label.setText(message)
        if ok:
            QTimer.singleShot(1500, self.close)  # 成功后稍候自动关窗（保留原行为）

    def closeEvent(self, event):
        # 关窗即清理子进程，避免扫码轮询进程残留
        if self.work.isRunning() or (self.work.p is not None and self.work.p.poll() is None):
            self.work.stop()
            self.work.wait(3000)
        super(FormLogin, self).closeEvent(event)

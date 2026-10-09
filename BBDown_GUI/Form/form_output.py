import subprocess

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QThread, pyqtSignal

from BBDown_GUI.UI.ui_output import Ui_Form_output
from BBDown_GUI.tool import CREATE_NO_WINDOW, decode_line, kill_process_tree, log, resource_path


class DownloadThread(QThread):
    """以 argv 列表启动 BBDown.exe，逐行读取合并后的 stdout/stderr 实时回传。"""
    output_signal = pyqtSignal(str)    # 每行文本（已解码、无行尾）
    finished_signal = pyqtSignal(int)  # 进程退出码；-1 = 启动失败

    def __init__(self, exe_path: str, args, cwd=None):
        super().__init__()
        self.exe_path = exe_path
        self.args = list(args)
        self.cwd = cwd
        self.p = None
        self._stop_requested = False

    def request_stop(self):
        """请求停止（GUI 线程调用）：置标志并强杀进程树。

        置标志可覆盖 Popen 尚未返回的竞态窗口——run() 启动成功后会对
        标志做二次检查。
        """
        self._stop_requested = True
        if self.p is not None:
            try:
                if self.p.poll() is None:
                    kill_process_tree(self.p.pid)
            except OSError:
                pass

    def run(self):
        try:
            # 关键：列表 argv、无 shell；CREATE_NO_WINDOW 防止 GUI 启动
            # 控制台程序时闪黑窗。中文路径/参数不再经过 cmd.exe 二次解析。
            self.p = subprocess.Popen(
                [self.exe_path, *self.args],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,      # stderr 合并，报错同样能看到
                stdin=subprocess.DEVNULL,
                cwd=self.cwd,
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError as e:
            self.output_signal.emit(f"[BBDown_GUI] 无法启动 {self.exe_path}: {e}")
            self.finished_signal.emit(-1)
            return

        # 竞态检查：Popen 返回前用户已点“停止”/关窗，则立即终止
        if self._stop_requested:
            kill_process_tree(self.p.pid)

        # 二进制逐行读：readline() 在本行 \n 到达时立即返回（实测逐行实时到达），
        # 进程静默期间此处阻塞，不影响窗口响应。
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            self.output_signal.emit(decode_line(line))
        self.p.wait()
        self.finished_signal.emit(self.p.returncode if self.p.returncode is not None else -2)


class FormOutput(QMainWindow, Ui_Form_output):
    def __init__(self, exe_path: str, args, cwd=None, parent=None):
        super(FormOutput, self).__init__(parent)
        self.setupUi(self)
        self.exe_path = exe_path
        self.args = list(args)
        self.cwd = cwd
        self.flag_stop = False
        self.flag_finished = False
        icon = QIcon()
        icon.addPixmap(QPixmap(resource_path("./UI/favicon.ico")), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)

        # 用 list2cmdline 还原成与 Windows 实际传给 CreateProcess 等价的命令串
        cmd_display = subprocess.list2cmdline([self.exe_path, *self.args])
        self.lineEdit_cmd.setText(cmd_display)
        self.lineEdit_cmd.setCursorPosition(0)  # 光标置头，长命令先看开头
        title = cmd_display if len(cmd_display) <= 120 else cmd_display[:117] + "..."
        self.setWindowTitle(f"下载 - {title}")

        self.pushButton_stop.clicked.connect(self.stop)
        self.execute()

    def execute(self):
        # 先连接信号再 start()，避免极快的进程在接线前就发出输出
        self.work = DownloadThread(self.exe_path, self.args, self.cwd)
        self.work.output_signal.connect(self.display)
        self.work.finished_signal.connect(self.on_finished)
        self.work.start()

    def display(self, message):
        # 保持原有追加行为（整段拼接 setText）
        self.textEdit_output.setText(self.textEdit_output.toPlainText() + message.strip() + '\n')
        self.textEdit_output.verticalScrollBar().setValue(self.textEdit_output.verticalScrollBar().maximum())

    def stop(self):
        # 防重复点击：标志 + 按钮禁用双保险
        if self.flag_stop or self.flag_finished:
            return
        self.flag_stop = True
        self.pushButton_stop.setEnabled(False)
        if self.work.isRunning():
            self.work.request_stop()
        self.display("")
        self.display(log("[BBDown_GUI] 下载已停止"))

    def on_finished(self, rc):
        self.flag_finished = True
        self.pushButton_stop.setEnabled(False)
        if self.flag_stop:
            return  # 停止提示已输出，不再报退出码
        if rc == -1:
            return  # 启动失败信息已由线程输出
        if rc == 0:
            self.display(log("[BBDown_GUI] 任务完成"))
        else:
            self.display(log(f"[BBDown_GUI] BBDown 已退出（退出码 {rc}）"))

    def closeEvent(self, event):
        # 关窗即清理整棵进程树，避免孤儿 BBDown/ffmpeg/aria2c 继续跑
        if self.work.isRunning():
            self.flag_stop = True
            self.work.request_stop()
            self.work.wait(3000)
        super(FormOutput, self).closeEvent(event)

import os
import json
import subprocess

from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QIcon

from BBDown_GUI.UI.ui_main import Ui_Form_main

from BBDown_GUI.Form.form_login import FormLogin
from BBDown_GUI.Form.form_output import FormOutput
from BBDown_GUI.Form.form_about import FormAbout

from BBDown_GUI.tool import resource_path, get_workdir, get_bbdowndir

workdir = get_workdir()
bbdowndir = get_bbdowndir()


class FormMain(QMainWindow, Ui_Form_main):
    def __init__(self):
        def Load(self):
            f = open(os.path.join(workdir, "config.json"), "r")
            config = json.loads(f.read())
            f.close()
            for item in config:
                if item == "advanced":
                    self.advanced = config[item]
                    if self.advanced:
                        self.pushButton_advanced.setText("简易选项<")
                        self.resize(1560, 630)
                        self.advanced = True
                    else:
                        self.pushButton_advanced.setText("高级选项>")
                        self.resize(620, 400)
                        self.advanced = False
                elif type(config[item]) == type(True):
                    exec(f'self.{item}.setChecked({config[item]})')
                elif type(config[item]) == type(''):
                    exec(f'self.{item}.setText(r"{config[item]}")')
                elif type(config[item]) == type(0):
                    exec(f'self.{item}.setCurrentIndex({config[item]})')
        
        super(FormMain, self).__init__()
        self.setupUi(self)
        icon = QIcon()
        icon.addPixmap(QPixmap(resource_path("./UI/favicon.ico")), QIcon.Normal, QIcon.Off)
        self.setWindowIcon(icon)
        self.pushButton_login.clicked.connect(self.login)
        self.pushButton_logintv.clicked.connect(self.logintv)
        self.lineEdit_ffmpeg.setText(os.path.join(workdir, "ffmpeg.exe"))
        self.lineEdit_aria2c_path.setText(os.path.join(workdir, "aria2c.exe"))
        self.lineEdit_dir.setText(os.path.join(workdir, "Download"))
        self.lineEdit_bbdown.setText(bbdowndir)
        self.pushButton_ffmpeg.clicked.connect(self.ffmpegpath)
        self.pushButton_dir.clicked.connect(self.opendownpath)
        self.pushButton_bbdown.clicked.connect(self.bbdownpath)
        self.pushButton_param.clicked.connect(self.param)
        self.pushButton_download.clicked.connect(self.download)
        self.pushButton_advanced.clicked.connect(self.advanced)
        self.advanced = False
        self.pushButton_about.clicked.connect(self.about)
        try:
            Load(self)
        except:
            # 当之前没有保存过任何参数时，界面为默认
            self.resize(620, 400)

    # 当前实际使用的 BBDown.exe 路径：以“程序位置”输入框为准，为空回退默认位置
    def bbdown_exe(self):
        exe = self.lineEdit_bbdown.text().strip().strip('"')
        if not exe:
            exe = get_bbdowndir()
        return os.path.abspath(exe)

    # 登录（网页端）
    def login(self):
        self._open_login("login")  

    # 登录（tv端）
    def logintv(self):
        self._open_login("logintv")

    # 打开登录窗口：把当前选择的 BBDown.exe 路径传给登录窗
    def _open_login(self, mode):
        old = getattr(self, "win_login", None)
        if old is not None:
            try:
                old.close()  # 关掉旧窗口；其 closeEvent 会停掉残留子进程
            except RuntimeError:
                pass
        self.win_login = FormLogin(mode, self.bbdown_exe())
        self.win_login.show()   

    # 设置ffmpeg位置
    def ffmpegpath(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "选择文件", os.getcwd(), "ffmpeg (ffmpeg.exe);;All Files (*.*)")
        filepath = filepath.replace("/","\\")
        self.lineEdit_ffmpeg.setText(filepath)

    # 设置下载目录
    def opendownpath(self):
        if not os.path.exists(self.lineEdit_dir.text()):
            os.makedirs(self.lineEdit_dir.text())
        os.startfile(self.lineEdit_dir.text())

    # 设置BBDown位置
    def bbdownpath(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "选择文件", os.getcwd(), "BBDown (BBDown.exe);;All Files (*.*)")
        if filepath:
            self.lineEdit_bbdown.setText(filepath.replace("/", "\\"))

    # 获取下载参数（返回 argv 列表：选项与取值各占一个元素，不做手工引号拼接）
    def arg(self):
        args = [self.lineEdit_url.text()]

        # 画质选择
        if self.radioButton_dfn_priority.isChecked():
            pass
        elif self.radioButton_dfn_1080P.isChecked():
            args += ['--dfn-priority', '1080P 高清']
        elif self.radioButton_dfn_720P.isChecked():
            args += ['--dfn-priority', '720P 高清']
        elif self.radioButton_dfn_480P.isChecked():
            args += ['--dfn-priority', '480P 清晰']
        elif self.radioButton_dfn_360P.isChecked():
            args += ['--dfn-priority', '360P 流畅']
        elif self.radioButton_dfn_more.isChecked():
            if self.comboBox_dfn_more.currentIndex() != 0:
                dfn = self.comboBox_dfn_more.itemText(self.comboBox_dfn_more.currentIndex())
                args += ['--dfn-priority', dfn]

        # 下载源选择（v1.7.x 写法：-t / -a / --use-intl-api）
        if self.comboBox_source.currentIndex() != 0:
            choice = ['', '-t', '-a', '--use-intl-api']
            args += [choice[self.comboBox_source.currentIndex()]]

        # 下载视频编码选择
        if self.comboBox_encoding.currentIndex() != 0:
            choice = ['', 'AVC', 'AV1', 'HEVC']
            args += ['--encoding-priority', choice[self.comboBox_encoding.currentIndex()]]

        # 指定FFmpeg路径
        if self.checkBox_ffmpeg.isChecked():
            args += ['--ffmpeg-path', self.lineEdit_ffmpeg.text()]

        # 下载分P选项
        if self.radioButton_p_current.isChecked():
            pass
        elif self.radioButton_p_all.isChecked():
            args += ['-p', 'ALL']
        elif self.radioButton_p_new.isChecked():
            args += ['-p', 'NEW']

        # 高级面板其余选项：仅在面板展开时参与（保持原有行为）
        if self.advanced:
            # 下载选项
            if self.checkBox_audio_only.isChecked():
                args += ['--audio-only']
            if self.checkBox_video_only.isChecked():
                args += ['--video-only']
            if self.checkBox_sub_only.isChecked():
                args += ['--sub-only']
            if self.checkBox_danmaku.isChecked():
                args += ['-d']

            # 交互选项
            if self.checkBox_ia.isChecked():
                args += ['-i']
            if self.checkBox_info.isChecked():
                args += ['-I']
            if self.checkBox_hs.isChecked():
                args += ['--hide-streams']
            if self.checkBox_debug.isChecked():
                args += ['--debug']

            # Cookies
            if self.checkBox_token.isChecked():
                args += ['--access-token', self.lineEdit_token.text()]
            if self.checkBox_c.isChecked():
                args += ['-c', self.lineEdit_c.text()]

            # 跳过选项
            if self.checkBox_skip_subtitle.isChecked():
                args += ['--skip-subtitle']
            if self.checkBox_skip_cover.isChecked():
                args += ['--skip-cover']
            if self.checkBox_skip_mux.isChecked():
                args += ['--skip-mux']
            if self.checkBox_skip_ai.isChecked():
                args += ['--skip-ai', 'true']
            else:
                args += ['--skip-ai', 'false']

            # MP4box
            if self.checkBox_mp4box.isChecked():
                args += ['--use-mp4box']
            if self.checkBox_mp4box_path.isChecked():
                args += ['--mp4box-path', self.lineEdit_mp4box_path.text()]

            # 其他
            if self.checkBox_mt.isChecked():
                args += ['--multi-thread', 'true']
            else:
                args += ['--multi-thread', 'false']
            if self.checkBox_force_http.isChecked():
                args += ['--force-http', 'true']
            else:
                args += ['--force-http', 'false']
            if self.checkBox_language.isChecked():
                args += ['--language', self.lineEdit_language.text()]

            # 分P
            if self.checkBox_p_show_all.isChecked():
                args += ['--show-all']
            if self.checkBox_p.isChecked():
                v = self.lineEdit_p.text().strip()
                if v:
                    args += ['-p', v]
            if self.checkBox_p_delay.isChecked():
                v = self.lineEdit_p_delay.text().strip()
                if v:
                    args += ['--delay-per-page', v]

            # aria2c
            if self.checkBox_use_aria2c.isChecked():
                args += ['--use-aria2c']
            if self.checkBox_aria2c_path.isChecked():
                args += ['--aria2c-path', self.lineEdit_aria2c_path.text()]
            if self.checkBox_aria2c_proxy.isChecked():
                args += ['--aria2c-proxy', self.lineEdit_aria2c_proxy.text()]
            if self.checkBox_aria2c_args.isChecked():
                args += ['--aria2c-args', self.lineEdit_aria2c_args.text()]

            # 文件名选项
            if self.checkBox_F.isChecked():
                args += ['-F', self.lineEdit_F.text()]
            if self.checkBox_M.isChecked():
                args += ['-M', self.lineEdit_M.text()]

            # 代理
            if self.checkBox_enable_proxy.isChecked():
                if self.checkBox_host.isChecked():
                    args += ['--host', self.lineEdit_host.text()]
                if self.checkBox_ep_host.isChecked():
                    args += ['--ep-host', self.lineEdit_ep_host.text()]
                if self.checkBox_area.isChecked():
                    args += ['--area', self.lineEdit_area.text()]

        # 新功能选项（BBDown v1.7.x 新增，位于「更多选项」面板）：
        # 是否生效只取决于自身勾选状态，与高级面板是否展开无关——用户勾选后
        # 收起面板再下载不应丢失参数（曾导致「仅下载封面」被忽略）。
        if self.checkBox_danmaku_only.isChecked():
            args += ['--danmaku-only']
        if self.checkBox_cover_only.isChecked():
            args += ['--cover-only']
        if self.checkBox_comments.isChecked():
            args += ['--comments']
        if self.checkBox_save_archives.isChecked():
            args += ['--save-archives-to-file']
        if self.checkBox_allow_preview.isChecked():
            args += ['--allow-preview']
        if self.checkBox_simply_mux.isChecked():
            args += ['--simply-mux']
        if self.checkBox_no_decrypt_drm.isChecked():
            args += ['--no-decrypt-drm']
        if self.checkBox_danmaku_formats.isChecked():
            v = self.lineEdit_danmaku_formats.text().strip()
            if v:
                args += ['--download-danmaku-formats', v]
        if self.checkBox_video_ascending.isChecked():
            args += ['--video-ascending']
        if self.checkBox_audio_ascending.isChecked():
            args += ['--audio-ascending']
        if self.checkBox_allow_pcdn.isChecked():
            args += ['--allow-pcdn']
        if self.checkBox_force_replace.isChecked():
            # CLI 默认强制替换下载服务器 host；勾选后使用原始地址，备份镜像 404 时可尝试
            args += ['--force-replace-host', 'false']
        if self.checkBox_insecure.isChecked():
            args += ['--insecure']

        # 下载路径
        args += ['--work-dir', self.lineEdit_dir.text()]

        return args

    def param(self):
        args = self.arg()
        self.lineEdit_param.setText(subprocess.list2cmdline(args))

    # 保存当前所有控件状态到 config.json（下载时与关闭窗口时都会调用）
    def save_config(self):
        config = {}
        for i in dir(self):
            if i[:9] == "checkBox_":
                config[i] = getattr(self, i).isChecked()
            elif i[:12] == "radioButton_":
                config[i] = getattr(self, i).isChecked()
            elif i[:9] == "lineEdit_":
                config[i] = getattr(self, i).text()
            elif i[:9] == "comboBox_":
                config[i] = getattr(self, i).currentIndex()
        config["advanced"] = self.advanced
        f = open(os.path.join(workdir, "config.json"), "w")
        f.write(json.dumps(config, indent=4))
        f.close()

    # 关闭主窗口时保存设置，避免“勾选后未点下载就退出”导致勾选状态丢失
    def closeEvent(self, event):
        try:
            self.save_config()
        except Exception:
            pass
        super(FormMain, self).closeEvent(event)

    # 开始下载
    def download(self):
        url = self.lineEdit_url.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请先填写视频地址")
            return
        if self.advanced and self.checkBox_p.isChecked() and not self.lineEdit_p.text().strip():
            QMessageBox.warning(self, "提示", "已勾选“指定下载分P”，请填写分P或范围（如 1,2 或 3-5 或 ALL）")
            return
        if self.advanced and self.checkBox_p_delay.isChecked() and not self.lineEdit_p_delay.text().strip():
            QMessageBox.warning(self, "提示", "已勾选“分P下载时间间隔”，请填写间隔秒数（如 5）")
            return

        self.save_config()
        args = self.arg()

        self.win_output = FormOutput(self.bbdown_exe(), args)
        self.win_output.show()


    # 高级选项
    def advanced(self):
        if not self.advanced:
            self.pushButton_advanced.setText("简易选项<")
            self.resize(1560, 630)
            self.advanced = True
        else:
            self.pushButton_advanced.setText("高级选项>")
            self.resize(620, 400)
            self.advanced = False


    # 关于
    def about(self):
        self.win_about = FormAbout()
        self.win_about.show()
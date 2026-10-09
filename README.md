# BBDown_GUI
BBDown的图形化版本 - 哔哩哔哩(B站)视频下载、音频下载、字幕下载 - bilibili video download

## 屏幕截图

### 简易模式

<img src="https://user-images.githubusercontent.com/29673994/169644975-066c4ac5-7fb1-4361-8c62-bb1e5aba4381.png" height="50%" width="50%" >

### 高级模式

<img src="https://user-images.githubusercontent.com/29673994/200099369-51250aa4-bd7f-4547-864c-f552143adcc1.png">

## 特性

- [x] 记忆下载参数
- [x] 下载剧集选项（当前剧集、全部剧集、最新剧集）
- [x] 优先显示常用选项，亦保留有所有功能
- [x] 下载进度控制
- [x] 适配 BBDown v1.7.x 新版命令行（`-t`、`-a`、`--use-intl-api`、`-d`、`-I`、`--access-token`、`--multi-thread`、`--hide-streams` 等写法）
- [x] 高级模式补充实用选项（仅下载弹幕/封面、下载评论、充电试看片段、弹幕格式、视频/音频体积优先、PCDN 域名、跳过 SSL 验证等）
- [x] 支持 DRM 解密（配套发行包内置 mp4decrypt 与 device.wvd，开箱即用）

## 使用方法

将 BBDown 的可执行程序与本 UI 程序置于同一文件夹中，直接运行即可。这样以后 BBDown 主程序更新也可以直接替换使用

本 GUI 按 BBDown v1.7.x 的新版命令行拼装参数，请配套使用 [aliveranme/BBDown](https://github.com/aliveranme/BBDown) 构建的 BBDown.exe（v1.7.3 起），过旧的版本可能不识别部分参数。

若需要 DRM 解密开箱即用，请从其 [Release](https://github.com/aliveranme/BBDown/releases) 下载 `BBDown_v*_win-x64.zip` 并整包解压到与本程序同一文件夹（BBDown.exe、device.wvd、mp4decrypt.exe、mp4decrypt-LICENSE.txt）。

## 下载

### 从 [Releases](https://github.com/aliveranme/BBDown_GUI/releases) 中下载使用 [![img](https://img.shields.io/github/v/release/aliveranme/BBDown_GUI?label=%E7%89%88%E6%9C%AC)](https://github.com/aliveranme/BBDown_GUI/releases) 

预打包好的二进制文件，包括
- BBDown - GUI
- BBDown（含 mp4decrypt.exe、device.wvd，DRM 开箱即用）
- FFmpeg
- Aria2c

### 从 [PyPI](https://pypi.org/project/BBDown-GUI/) 安装使用  [![](https://img.shields.io/pypi/v/BBDown_GUI)](https://pypi.org/project/BBDown-GUI/) 

安装

```
pip install BBDown-GUI
```

运行（不区分大小写，下划线可省略）
```
BBDown_GUI
```

### 从源码运行使用
```
pip install -r requirements.txt
python -m BBDown_GUI
```

### 从[持续集成](https://github.com/aliveranme/BBDown_GUI/actions/workflows/build.yml)中下载(beta version) [![Pack Python application](https://github.com/aliveranme/BBDown_GUI/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/aliveranme/BBDown_GUI/actions/workflows/build.yml)
进入Actions，选择Pack Python application，进入需要下载的工作流
![image](https://github.com/1299172402/BBDown_GUI/assets/29673994/d7944b79-ae96-4c6a-9892-f8e7d3238a61)
到下方Artifacts下载BBDown_GUI
![image](https://github.com/1299172402/BBDown_GUI/assets/29673994/45c92ba5-80cc-47db-b5cc-8abe23de2078)


## 致谢&License

 - https://github.com/nilaoda/BBDown (MIT License，BBDown 上游)
 - https://github.com/aliveranme/BBDown (本 GUI 配套的 BBDown 分支)
 - https://github.com/aria2/aria2 (随包分发)
 - https://ffmpeg.org (随包分发)
 - https://github.com/axiomatic-systems/Bento4 (mp4decrypt，GPL-2.0/商业双许可)

<!--

## 相关Repository

 - [BBDown_hk](https://github.com/1299172402/BBDown_hk)

-->

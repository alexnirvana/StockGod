# 语音讲解说明

[English](NARRATION.md) · [简体中文](NARRATION_CN.md)

0.5 版本内置 30 段 MP3：五章课程正文、五章教练概要和五种常见教练讲解，各有中英文版本。这些是合成语音，不是真人录音。

## 使用方式

进入「交易训练 → 学习讲解 → 播放讲解」。支持暂停、重播、拖动进度、段落跳转，以及 0.75×、1×、1.25×、1.5×、2× 语速；朗读语言可独立选择。教练回答也提供播放按钮。

点击后才开始播放。关闭弹窗、离开课程、退出账号或切换朗读语言时，原有音频停止；开始另一个播放器会暂停之前的播放。播放失败会显示可重试提示，文字讲解始终可读。

课程听课位置与语速按账号、课程、朗读语言分别保存到 MySQL。连续播放约每十秒保存一次，暂停、拖动与关闭讲解时再保存。突然结束浏览器或网络中断可能丢失最近尚未保存的几秒。「学习档案 → 我的听课记录」会打开对应课程和朗读语言。教练音频不创建课程听课记录。

听课位置与课程通关独立。拖到最后或听完整段音频不会获得经验、解锁章节，也不能代替测验。多个窗口通过版本号避免互相覆盖；若另一个窗口已更新位置，请重新打开讲解再保存。

## 部署与更新

音频位于 `content/narration/`，由需要登录的 API 提供，支持字节范围读取。播放需要访问已部署的程序，无需外部语音服务、密钥或系统语音包。Linux Docker 也使用同一份文件，仅重新生成音频时需要语音引擎。

清单记录内容版本、文件校验值、时长、段落位置和所用声音。修改正文或预设回答后应重新生成音频。音频版本变化会重置该版本的续听位置，保留用户语速偏好。缺少音频不会阻止阅读课程。

## 重新生成

在 Windows 上准备项目 Python 环境，让 FFmpeg 和 ffprobe 可从 PATH 调用。当前生成器通过 System.Speech 使用本机 `Microsoft Huihui Desktop` 中文语音和 `Microsoft Zira Desktop` 英文语音，然后执行：

```powershell
.\scripts\build-narration.ps1
```

脚本读取课程与教练原文，在已忽略的 `data/narration-build/` 生成中间 WAV，再输出 MP3 与 `content/narration/manifest.json`，不调用网络语音服务。提交文字改动时，同时提交当前清单及其引用的全部音频。

```sh
python -m pytest tests/integration/test_narration.py -q
npm --prefix frontend test
npm --prefix frontend run build
```

测试覆盖音频完整性和文案一致性、登录与范围读取、课程锁、账号隔离、重复请求、多窗口冲突、回退位置和奖励不变。浏览器测试还需实际媒体播放支持，隔离环境见[运维说明](OPERATIONS_CN.md)。

实现参考：[浏览器音频播放](https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/play)、[System.Speech WAV 输出](https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer.setoutputtowavefile)。

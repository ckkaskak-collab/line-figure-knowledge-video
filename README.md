# 线条小人知识视频工作流

把定稿文案或已有配音，做成 **白底线条小人 + 浅灰手绘知识画面** 的视频。支持角色动作状态、声学对齐、ChatCut 可编辑工程、字幕、配乐、MP4 和按需封面。

这是给 Codex 等支持 Skill 的助手使用的工作流。角色参考、绘图规则和四种 B-roll 模板已经内置，无需安装作者的其他 Skill，也无需访问作者的项目、飞书账号或 API 配置。第三方生成和剪辑服务使用你自己的账号。

![浅灰手绘视觉参考](assets/broll/approved-light-gray-handdrawn.png)

## 安装

从本仓库 **Code → Download ZIP** 下载并解压，进入包含 `SKILL.md` 的目录。使用 Python 3.9 或更新版本：

```bash
python3 scripts/doctor.py
python3 scripts/install.py
```

Windows 可以把 `python3` 换成 `py`。默认安装到 `$CODEX_HOME/skills/line-figure-knowledge-video`；未设置 `CODEX_HOME` 时使用 `~/.codex/skills/line-figure-knowledge-video`。重启或新开 Codex 任务，调用 `$line-figure-knowledge-video`。

安装到其他支持 Skill 的工具时，可运行 `python3 scripts/install.py --destination "目标技能目录/line-figure-knowledge-video"`。已有同名 Skill 时默认拒绝覆盖；明确升级可加 `--replace`，旧版自动保存在同级 `.skill-backups/`。

也可以直接把整个本仓库文件夹放到技能目录，保持文件夹名为 `line-figure-knowledge-video`。不要只复制 `SKILL.md`。

## 第一次使用

把定稿或音频放入你的项目目录，然后告诉助手：

> 使用 $line-figure-knowledge-video。用这份定稿和已有配音制作一条线条小人知识视频，采用内置角色与浅灰手绘风格，完成 ChatCut 可编辑工程并导出 MP4。按已授权范围连续执行，记录需要补充的真实素材。

只需要方案可以说：

> 使用 $line-figure-knowledge-video。先根据这份文案设计角色动作与视觉方案；我还没有音频，暂不填写毫秒时间。

制作前助手会检查本次需要的工具。已有工程会复用，不会重新生成所有素材。

| 要做什么 | 需要什么 |
|---|---|
| 阅读工作流、分镜方案、项目初始化、离线示例 | 支持 Skill 的助手；运行脚本时需要 Python 3.9+ |
| 新生成角色图或封面 | 能接收参考图片的图像生成工具；已有图片可直接复用 |
| 自动声学转写 | 本地 faster-whisper，或你提供的真实词级声学结果 |
| 豆包新配音（可选） | 自己的豆包/火山语音服务凭据、可用音色及 `httpx` |
| 可编辑整片与 MP4 | 已登录且权限可用的 ChatCut 插件；导出能力以你的账号为准 |
| 本地成片解码检查 | FFmpeg / ffprobe（可选） |

没有豆包密钥也能使用已有音频继续。未连接 ChatCut 时可准备分镜和素材，但不能声称已经创建可编辑工程或导出视频。工具检查不会替你购买额度。

## 不调用外部服务的试运行

```bash
python3 scripts/doctor.py
python3 scripts/verify_sources.py
python3 scripts/smoke_test.py
python3 -m unittest discover -s tests -v
```

试运行在临时目录模拟安装、初始化、时间交接、字幕和模板配置；使用明确标记的测试时间数据，证明本地工具可用，不冒充真实配音或成片。可加 `--output "新的目录"` 保留试运行文件。

## 使用自己的音频

```bash
python3 scripts/init_project.py --script narration.txt --audio narration.wav --output my-video
```

原稿和音频会复制到新项目，保持原件。非 WAV 音频也可导入；若本地没有 ffprobe，时长留空，转写或宿主读取真实时长后再填写。

可选本地 Whisper 环境：

```bash
python3 -m venv .venv
# macOS / Linux
.venv/bin/python -m pip install -r requirements-asr.txt
.venv/bin/python scripts/transcribe.py --audio my-video/audio/source.wav --output my-video/audio/asr.json
# Windows 用 .venv\Scripts\python 替换 .venv/bin/python
```

默认使用 large-v3、CPU int8；第一次运行会下载模型，需要网络和足够磁盘空间。已有缓存可加 `--offline`。词级结果经定稿核对后，用 [本地工具说明](references/local-tools.md) 中的对齐命令生成字幕和连续编排表。识别不一致会输出复核记录，不会静默改写成“全部匹配”。实现依据 [faster-whisper 官方用法](https://github.com/SYSTRAN/faster-whisper)。

## 可选豆包配音

```bash
python3 -m pip install -r requirements-tts.txt
```

把 [配置示例](config/doubao-tts.example.json) 复制到你的配置目录，在本机填写 `api_key`。macOS / Linux 默认位置为 `~/.config/line-figure-knowledge-video/doubao-tts.json`，设置 `chmod 600`；Windows 或其他位置使用 `--config`。也可通过环境变量 `DOUBAO_TTS_API_KEY` 提供密钥。不要提交真实凭据。

把 `YOUR_AVAILABLE_SPEAKER_ID` 换成自己账号可用的音色 ID。先预览请求参数，再在已确认使用该服务时合成：

```bash
python3 scripts/synthesize_doubao.py --script narration.txt --output my-video/audio/tts --speaker "YOUR_AVAILABLE_SPEAKER_ID"
python3 scripts/synthesize_doubao.py --script narration.txt --output my-video/audio/tts --speaker "YOUR_AVAILABLE_SPEAKER_ID" --synthesize
```

默认新合成 `speech_rate=15`，整篇只发送一次。成功音频会复用；失败或超时记录为待核实，不自动重试。语速、音色和服务可用性按你的账号与当前接口核对。配置字段依据 [字节跳动官方示例](https://github.com/bytedance/agentkit-samples/blob/main/skills/byted-text-to-speech/scripts/text_to_speech.py)。

## 包内内容

- [SKILL.md](SKILL.md)：执行入口与阶段路由。
- [角色原图](assets/character/reference.jpg)、[绘图规则](references/illustration/character-ip.md)：默认角色，也支持项目自己的角色参考。
- [B-roll 模板目录](assets/broll/templates/index.json)：检索到回答、双侧比较、分流、真实截图外围布局；文字、颜色与动作帧可编辑。
- [字幕与交付](references/captions-and-delivery.md)、[配乐](references/audio-postproduction.md)、[封面](references/covers.md)：按需读取的制作说明。
- [原文来源清单](references/source-manifest.json)：八段提示词及快照，离线可读，原文保持不变。
- `scripts/`：安装、检查、项目初始化、声学转写/对齐、SRT 和模板实例化；脚本参数均可用 `--help` 查看。

模板依赖 ChatCut 原生 MG 运行时，不能当作独立网页直接播放。实例化后需通过当前 ChatCut 工具导入、上轨并检查。字体查询、角色一致性、语音听感、全片连续观看需要在实际项目中完成，离线测试不能替代。

原创代码和说明采用 [MIT](LICENSE)；第三方原文、Ian 参考和角色素材的边界见 [来源说明](THIRD_PARTY_NOTICES.md)。

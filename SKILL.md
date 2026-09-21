---
name: line-figure-knowledge-video
description: "将定稿文案或已有配音制作成白底线条小人 A-roll、浅灰手绘 B-roll 的知识视频。内置角色参考、动作接口、可编辑动画模板，支持声学对齐、ChatCut 整片剪辑、字幕、配乐和按需封面；也用于这套工作流的分镜与续做。"
---

# 线条小人知识视频

本包内置角色原图、Ian 风格参考、B-roll 模板和执行脚本，可独立安装，不依赖另一份本地 Skill。安装与环境见 [README](README.md)，来源与许可边界见 [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md)。

## 开始本次任务

1. 先读取用户提供的文案、音频及已有 `project-state.json`，判断本次范围是方案、素材、整片、修改还是封面。按已授权范围连续执行；不为每镜重复提问。
2. 首次使用运行 `python3 scripts/doctor.py`。它检查本地包与可选 Python 依赖；图像生成、ChatCut 的登录/权限/费用仍由当前宿主工具核对。维护 Skill 不调用 TTS、生图或渲染。
3. 已有配音直接保留。需要新配音时按项目选择配置豆包；默认新合成 `speech_rate=15`，不再二次加速。没有音频可以做内容与动作方案，不能编造实测时长。
4. 默认角色是 [包内原图](assets/character/reference.jpg)。若用户指定自己的角色，将其保存在项目并记录路径，替代角色参考和对应身份描述。每次生图都实际查看并传入选定原图。
5. 新项目使用 `python3 scripts/init_project.py --script <定稿.txt> --output <新项目目录>`，可加 `--audio <已有音频>`；它保存输入与续做结构，不自动触发外部付费操作。输入音频可由任意已获授权的来源提供。

## 已确定的默认风格

- A-roll：白底、黑线留白的小人参与具体动作，使用必要数量的独立关键状态图，必要时少量推近；缩放不替代人物行动。详见 [A-roll 接口](references/aroll-ian.md)。
- B-roll：近白浅灰底、炭黑手绘、柔和蓝和少量暖橙。制作前查看 [规范和确认图](references/broll-visual-style.md)。
- 先布局，后动画。优先匹配 [包内模板](assets/broll/templates/index.json)，根据真实配音重设动作锚点；模板不匹配时自行设计，记录实际来源。
- 画布默认 1920×1080、30 fps；已有工程沿用实际规格。新项目的字幕、字体、音色和片尾选择写入项目记录。没有指定片尾时不附加其他 IP 的片尾。
- 标题字体可先试 Ma Shan Zheng，字幕可先试 Noto Sans SC；每个目标工程查询实际可用字体并检查合成字形，名称相同也不能替代渲染检查。

## 原文与执行规则

X 的六段提示词和飞书 2.0 的两段提示词完整保存在 `references/original-prompts/`。来源、原版本和哈希见 [来源清单](references/source-manifest.json)。先运行 `python3 scripts/verify_sources.py`，不以重算基准掩盖原文变化。

执行某阶段时完整读取对应原文。具体输入、角色、配色、工具接口和本包补充规则放在原文外，不改写原文。默认视觉编排采用飞书 2.0，X 02 留作可选原路线。A-roll 使用包内角色接口，X 03/04/05 作为角色三视图或原路线的可选参考，不同时强制注入。

以下调度是本包补充：只请求分镜时到分镜结束；用户要求整片时，分镜完成后继续已授权的制作。单独请求挑动效时提供方案供选择；已授权整片时自行选合适模板并记录，不逐镜重问。外部费用按用户已有预算和授权执行，不能把原文“使用 Codex 额度”解释为第三方服务免费。

## 按阶段读取

| 阶段 | 读取 | 执行与交付 |
|---|---|---|
| 配音与对齐 | [X 01](references/original-prompts/x/01-voice-alignment.txt)、[时间和配音](references/timing-and-handoff.md)、[本地脚本](references/local-tools.md) | 整段合成或保留音频；保存原始 ASR、按定稿核对的短语表和连续编排表 |
| 视觉编排 | [飞书编排 2.0](references/original-prompts/feishu/visual-storyboard-v2.txt) | 九列表、镜头结束节拍点、逗号数值、所缺素材；每次内部变化绑定真实短语/词锚点 |
| A-roll | [角色动作接口](references/aroll-ian.md) | 读包内角色/风格/生图/QA 参考，独立生成状态图，保持角色与道具连续 |
| B-roll | [视觉规范](references/broll-visual-style.md)、[可编辑实现](references/broll-editable.md)、[X 06](references/original-prompts/x/06-broll-motion.txt) | 静态布局、可编辑图形和实际模板记录；真实截图独立导入，不能用生成图冒充证据 |
| 整片剪辑 | [ChatCut 接口](references/chatcut-workflow.md)、[飞书剪辑 2.0](references/original-prompts/feishu/chatcut-editing-v2.txt) | 使用当前宿主的 ChatCut 基础/导入/MG/验证/导出技能；连续完成时间轴及两份制作清单 |
| 字幕与交付检查 | [字幕与成片](references/captions-and-delivery.md) | 核对最终 Card、渲染画面和 SRT；保存源码与实例参数；分别报告抽帧、播放、听审、导出 |
| 配乐与音效 | [声音后期](references/audio-postproduction.md) | 按内容选择或复用素材，记录来源、混音和实际听审状态 |
| 封面 | [封面分支](references/covers.md) | 用户要求时制作独立比例的封面；标题与概念画面不改变正文事实 |

## 续做和真实交付

续做先看项目记录，再核对实时工程。静态资产、上轨、合成抽帧、连续观看、连续回听、编码导出是不同状态，各自记录证据。新配音或音频剪辑后重新对齐；只替换配乐时沿用已确认的人声、画面和字幕。

交付分别列出原生可编辑工程、本地源素材与代码、MP4、SRT、封面，以及确实取得的 NLE 包。云端链接、源码 ZIP、扁平 MP4 不能互相替代。缺少外部工具或材料时完成不受影响的部分，标明具体缺项，不把准备完毕写成视频已经完成。

# 本地脚本接口

以下命令从 Skill 根目录执行。基础脚本仅用 Python 3.9+ 标准库；新配音和本地转写另装 README 中相应依赖。所有输出都要求新路径，避免覆盖已确认资产。

## 初始化与转写

```bash
python3 scripts/init_project.py --script narration.txt --audio narration.wav --output my-video
python3 scripts/transcribe.py --audio my-video/audio/source.wav --output my-video/audio/asr.json
```

`transcribe.py` 默认 large-v3 / CPU int8，保存原始段落和词级时间，同时输出下述规范化 `words`。已有模型可加 `--offline`；需要 GPU 或其他算力时显式传 `--device`、`--compute-type`。缺包、模型或网络会报出明确原因，不创建成功标记。特征提取出现数值溢出或无效值警告时停止，先检查运行环境或使用独立 ASR 复核，不能因为转写文字看似正常就采用异常运行的时间戳。

```json
{
  "duration_ms": 2500,
  "words": [
    {"text": "先查资料", "start_ms": 200, "end_ms": 1000},
    {"text": "再回答", "start_ms": 1300, "end_ms": 2200}
  ]
}
```

以上是格式示例，数值不是音频证据。使用 ChatCut 或其他 ASR 时，按实际返回转换为同一结构，保留原始结果及来源。

## 从真实词时间到连续编排表

先按语义准备 `phrases.txt`，每行一段定稿短语，按原文顺序完整覆盖正文，不增加或删改字词。

```bash
python3 scripts/align_audio.py --script my-video/script.txt --asr my-video/audio/asr.json --phrases phrases.txt --output my-video/alignment --fps 30
```

输出真实声学短语 `phrase-acoustic.json`、连续 `vo-align.txt`、声学 `captions.srt` 和共享帧边界。开头/末尾覆盖实际音频，相邻静音取中点。帧率可写 `30000/1001`；内部四舍五入采用 half-up，最终帧向上覆盖尾部。

发生文本差异、跨 ASR 词切分、异常重叠或重复帧时停止并输出复核信息，不按字数插值。若确认只是识别错字，在 ASR 副本的对应词添加 `reviewed_text`，保留原 `text` 和时间，并记录复核依据。真实漏读必须修正音频或由用户决定文案，不能用 `reviewed_text` 掩盖。

## 导出最终字幕

将最终 Card 转成 [规范格式](captions-and-delivery.md)，然后运行：

```bash
python3 scripts/captions_to_srt.py --input final-cards.json --output final.srt
```

该工具使用 Card 的最终显示时间；声学 SRT 与最终显示 SRT 是两个不同文件。

## 实例化 B-roll 模板

```bash
python3 scripts/template_payload.py --template compare --duration-frames 150 --beats 0,45,100 --props examples/quickstart/compare-props.json --output compare-payload.json
```

模板名见 [索引](../assets/broll/templates/index.json)。三项 beats 是新镜头的局部动作帧；`retrieve-answer` 需要对应资料出现、选中、回答出现的三个帧值。帧值必须递增且落在镜内，动作结束也应在镜内。模板以 30 fps 作为默认创建规格，实际项目需按配音锚点和工程帧率确定帧值。

输出包含 `name`、`code`、`width`、`height`、`durationInFrames`、`properties` 和 `description`，可交给当前 ChatCut MG 创建工具；`--props` 中的值会成为本次属性默认值。修改时长不会自动缩放旧配音锚点。布局检查后关闭静态预览，再检查动态中段及结果帧。

对齐核对保留小数点、正负号、百分号、分数和单位等意义，遇到数字写法或 ASR 分词差异时停下复核。分词把小数点与数字拆开时也可能触发复核；不要通过删除符号强行匹配。

# 生图提示词模板

每张图单独生成。先查看并附上项目选定的角色原图，未另行指定时使用本工作流的 `assets/character/reference.jpg`；使用该文件的绝对路径作为 `referenced_image_paths`。自有角色需将下方默认身份段落替换成该角色的身份记录，其他构图和风格规则仍适用。根据正文替换变量，不要把多张图拼在一起。

```text
Generate one standalone 16:9 horizontal Chinese article illustration.

Visual DNA:
Pure white background. Minimalist black hand-drawn line art. Slightly wobbly pen lines. Lots of empty white space. Sparse red/orange/blue handwritten Chinese annotations. Clean absurd product-sketch feeling. No gradients, no shadows, no paper texture, no complex background, no commercial vector style, no PPT infographic look, no cute mascot poster, no children's illustration, no realistic UI.

Recurring IP character required:
Use the attached character reference as the identity anchor. Preserve its large head and short body, fluffy rounded short-hair outline with angular fringe, simple curved ear, two short vertical black-line eyes, loose long sleeves, wide trousers and flat rounded feet. Black hand-drawn contours with white unfilled hair, face and clothing. No added nose, prominent mouth, blush, accessories, colored clothing, solid-black body, white dot eyes or stick legs. Keep the reference proportions and natural simplicity; do not exaggerate cuteness. Invent a new pose and scene, not a copy of the reference pose. The character must perform the core conceptual action. Put absurdity in the action and props, while keeping the character recognizable.

Theme:
{正文配图主题}

Structure type:
{结构类型：Workflow / 系统局部 / 前后对比 / 角色状态 / 概念隐喻 / 方法分层 / 地图路线 / 小漫画分镜}

Core idea:
{这张图要表达的核心意思}

Composition:
{具体画面：线稿小人在哪里、正在做什么、主要物件是什么、信息如何流动}

Suggested elements:
{元素1} / {元素2} / {元素3} / {元素4}

Chinese handwritten labels:
{标注词1} / {标注词2} / {标注词3} / {标注词4} / {可选标注词5}

Color use:
Black for main line art and character contours only; keep character interiors white. Orange for main flow/path/arrows. Red only for key warnings/problems/results. Blue only for secondary notes or feedback/system state.

Constraints:
One image explains only one core structure. Keep the main subject around 40%-60% of the canvas. Preserve at least 35% blank white space. Use at most 5-8 short handwritten Chinese labels. Do not write a title in the top-left corner. Do not write the structure type on the image. Do not make it a formal diagram, course slide, or dense explainer. Do not copy prior examples or reuse known case compositions unless explicitly requested; invent a fresh visual metaphor for this specific article. It should be clear but not instructional, interesting but not childish, strange but clean.
```

## 图像编辑提示

去掉左上角标题：

```text
Edit the provided image. Remove only the handwritten title "{要删除的文字}" and its underline from the top-left corner. Fill that area with the same clean white background, matching the surrounding blank paper. Preserve everything else exactly: characters, labels, paths, line style, composition, aspect ratio, and image quality. Do not add any new text or objects.
```

增强怪诞感：

```text
Regenerate this illustration with the same core meaning and simple layout, but make 线稿小人 more central to the conceptual action. 线稿小人 should be doing the strange work that explains the idea, not standing beside the diagram. Keep it clean, sparse, hand-drawn, and faithful to the attached character reference.
```

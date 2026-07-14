# TikTok AI Video Workflow

使用 GitHub Actions 调用 xAI Grok Imagine API，完成：

1. 根据“文生图提示词”生成一张 9:16 竖屏图片。
2. 把生成图片和“图生视频提示词”提交给 Grok。
3. 轮询视频生成任务并下载成品。
4. 将提示词、API 响应、源图片和视频保存为 GitHub Actions Artifact。

## 使用的模型

- 文生图：`grok-imagine-image-quality`
- 图生视频：`grok-imagine-video-1.5`

接口实现参考 xAI 官方的 [Image Generation](https://docs.x.ai/developers/model-capabilities/images/generation) 和 [Image-to-Video](https://docs.x.ai/developers/model-capabilities/video/image-to-video) 文档。

## 第一次配置

### 1. 创建 xAI API Key

前往 [xAI Console](https://console.x.ai/) 创建 API Key，并确认账户已有可用额度。

### 2. 添加 GitHub Secret

进入本仓库：

`Settings → Secrets and variables → Actions → New repository secret`

填写：

- Name：`XAI_API_KEY`
- Secret：你的 xAI API Key

不要把 API Key 写进 README、工作流输入或代码。

## 运行工作流

合并本功能分支后：

1. 打开仓库的 `Actions`。
2. 选择 `Generate TikTok video with Grok`。
3. 点击 `Run workflow`。
4. 填写：
   - `image_prompt`：文生图提示词。
   - `video_prompt`：图生视频提示词。
   - `duration`：5–15 秒。
   - `video_resolution`：480p、720p 或 1080p。
   - `dry_run`：建议第一次保持开启。
5. 先运行一次 `dry_run=true`，检查 Artifact 中的 `request-plan.json`。
6. 确认提示词无误后，再用 `dry_run=false` 生成付费视频。

## 提示词示例

文生图提示词：

```text
A premium cream-white mini electric pressure cooker on a clean Malaysian condo kitchen counter, lid open, glossy chicken rice inside, warm natural daylight, realistic commercial product photography, precise product shape, centered composition, vertical 9:16, no people, no text, no watermark
```

图生视频提示词：

```text
Keep the cooker and kitchen visually consistent with the source image. Slow cinematic push-in toward the open cooker, gentle realistic steam rises from the chicken rice, subtle highlights move across the glossy food, then a smooth 10-degree orbit to reveal the texture. Stable product geometry, natural motion, premium appliance advertisement, no morphing, no extra objects, no text.
```

## 输出文件

每次运行会上传一个保留 7 天的 Artifact：

- `request-plan.json`
- `source-image.png`
- `video.mp4`
- xAI API 响应 JSON

当 `dry_run=true` 时只会生成 `request-plan.json`，不会调用付费 API。

## 费用提醒

xAI 的图片与视频生成按实际调用收费，价格可能调整。运行非 dry-run 任务前，请查看 [xAI Pricing](https://docs.x.ai/developers/pricing)。

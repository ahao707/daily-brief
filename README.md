# 📰 每日简报 · Daily Brief

一个**每天自动更新**的个人新闻页：AI 圈 + 全球动态，有视频自动嵌入。
通过 GitHub Actions 每天抓 RSS → 生成 HTML → 推到 GitHub Pages。

页面长这样：暖牛皮纸 + 朱红 + 深墨的杂志风格，响应式，手机也能看。

---

## 🚀 部署（一次配置，永久运行）

### 1. 创建仓库

在 GitHub 上新建一个 **public** 仓库（必须 public 才能用免费 Pages），比如叫 `daily-brief`。

把本文件夹里所有文件上传上去。三种方式任选：

**A. 网页直接拖**：在新仓库页面点 "uploading an existing file"，把所有文件拖进去。

**B. 命令行**：
```bash
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/你的用户名/daily-brief.git
git push -u origin main
```

**C. GitHub CLI**：
```bash
gh repo create daily-brief --public --source=. --push
```

### 2. 开启 GitHub Pages

仓库 → `Settings` → 左侧 `Pages` →

- **Source**: `Deploy from a branch`
- **Branch**: `main` / `/ (root)`
- 点 **Save**

等 1 分钟，你会得到一个 URL：`https://你的用户名.github.io/daily-brief/`

### 3. 允许 Actions 写仓库

仓库 → `Settings` → 左侧 `Actions` → `General` → 滚到底 `Workflow permissions` →

- 选 **Read and write permissions**
- 点 **Save**

> 没这一步的话，Actions 跑完没法把新 HTML 推回来。

### 4. 手动跑一次试试

仓库 → 顶部 `Actions` → 左侧 `Update Daily Brief` → 右上 `Run workflow` → 绿色按钮 `Run workflow`。

跑完（约 1 分钟）后，回到 Pages 给的 URL，你应该能看到今天的内容了。

之后每天 UTC 13:00（北京时间 21:00 / 美西 6:00）会自动跑。

---

## 🔧 自定义

### 改新闻源

编辑 `scripts/sources.yml`。每条加一个 RSS URL 就行：

```yaml
ai:
  - name: 你想叫它什么
    url: https://example.com/feed.xml
    keywords_required: false  # true = 只收含 AI 关键词的条目
```

**找 RSS 地址的小技巧：**
- 大多数新闻站底部有 RSS 图标
- 在浏览器地址栏前加 `view-source:` 然后搜 `rss` 或 `atom`
- 没 RSS 的站可以用 [RSSHub](https://rsshub.app) 把任何东西转 RSS
- HackerNews 用 [hnrss.org](https://hnrss.org) 可以按关键词订阅

**找 YouTube channel ID：**
1. 打开频道主页
2. 右键 → 查看源代码
3. Ctrl+F 搜 `"channelId":"` 或 `"externalId":"`
4. 复制后面那一串 `UC...` 开头的 ID
5. 拼成 `https://www.youtube.com/feeds/videos.xml?channel_id=那个 ID`

### 改更新时间

编辑 `.github/workflows/update.yml`，改 cron 那一行。
[crontab.guru](https://crontab.guru) 可以可视化测试。

注意 cron 用的是 **UTC**：
- 北京时间 8:00 = `0 0 * * *`
- 北京时间 21:00 = `0 13 * * *`（默认）
- 美东时间 7:00 = `0 11 * * *`（夏令时）

### 改时区显示

编辑 `scripts/build.py` 顶部的 `TIMEZONE_OFFSET = 8`。
北京 = 8，纽约 = -4（夏）/ -5（冬），洛杉矶 = -7 / -8。

### 改 AI 关键词

编辑 `scripts/build.py` 里的 `AI_KEYWORDS` 列表。

### 改样式

编辑 `templates/index.html.j2`。最上面 `:root` 里的 CSS 变量改起来最快——换配色、换字体都改那。

---

## 🧪 本地试跑

不想等 Actions，想本地看效果：

```bash
pip install -r scripts/requirements.txt
python scripts/build.py
open index.html   # macOS
# 或者 start index.html  (Windows)
# 或者 xdg-open index.html  (Linux)
```

---

## 🛠 故障排查

**Actions 跑失败？** 点进失败的那次 run 看日志。最常见两个原因：
1. 没开第 3 步的写权限 → 报 `permission denied`
2. 某个 RSS 源挂了 → 脚本会跳过那个继续，不影响其他

**页面空白？** 可能是 RSS 那一刻都不可达。等下次自动跑（或手动 re-run）。

**视频不能播？** YouTube 在某些地区 / 网络下嵌入会被拦。这是浏览器侧的事，跟脚本无关。点 "阅读原文" 跳到 YouTube 看。

**Pages 没生效？** GitHub Pages 首次部署有时要 5-10 分钟。再等等。

---

## 📁 文件说明

```
daily-brief/
├── .github/workflows/update.yml   # GitHub Actions 定时任务
├── scripts/
│   ├── build.py                   # 抓 RSS、渲染模板的主脚本
│   ├── sources.yml                # 新闻源配置（你最常改的）
│   └── requirements.txt           # Python 依赖
├── templates/
│   └── index.html.j2              # 页面模板（要改样式改这）
├── index.html                     # 生成产物，GitHub Pages 服务这个
└── README.md
```

---

享受你的每日简报 🗞

#!/usr/bin/env python3
"""
Daily Brief Builder
读取 sources.yml 配置的 RSS 源，过滤、去重、识别视频，
渲染模板生成 index.html。

由 GitHub Actions 每日定时调用。
"""
import feedparser
import yaml
import re
import html
import sys
from datetime import datetime, timedelta, timezone
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
TEMPLATES = ROOT / "templates"

# ---------- 配置 ----------
AI_KEYWORDS = [
    # 英文
    "AI", "artificial intelligence", "GPT", "Claude", "Gemini", "Sonnet", "Opus",
    "Anthropic", "OpenAI", "DeepMind", "Mistral", "Meta AI",
    "agent", "agentic", "LLM", "language model", "ChatGPT",
    "Copilot", "Cursor", "Llama", "DeepSeek", "Qwen",
    "machine learning", "deep learning", "neural", "transformer",
    "diffusion", "robotic", "humanoid", "AGI", "NVIDIA",
    # 中文
    "人工智能", "大模型", "智能体", "深度学习", "生成式", "通用人工智能",
    "机器人", "具身智能",
]

MAX_PER_SECTION = 9     # 每个板块最多展示几条
MAX_AGE_HOURS = 48      # 只取最近 48 小时内的内容
TIMEZONE_OFFSET = 8     # 显示用时区（北京 = +8，纽约 = -5/-4）
# --------------------------


def parse_date(entry):
    """从 RSS entry 提取发布时间，返回 UTC datetime。"""
    for field in ["published_parsed", "updated_parsed"]:
        v = entry.get(field)
        if v:
            try:
                return datetime(*v[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
    return None


def clean_text(text, max_len=200):
    """清理 HTML，截断到指定长度。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def extract_video(entry):
    """识别 YouTube 视频，提取 ID 和缩略图。"""
    link = entry.get("link", "")
    # YouTube watch URL 或短链
    match = re.search(r"(?:watch\?v=|youtu\.be/|/embed/)([\w-]{11})", link)
    if match:
        vid = match.group(1)
        return {
            "youtube_id": vid,
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "embed_url": f"https://www.youtube.com/embed/{vid}",
            "watch_url": f"https://www.youtube.com/watch?v={vid}",
        }
    # media:content 里如果是 video 类型
    for media in entry.get("media_content", []) or []:
        m_type = media.get("type", "")
        if media.get("medium") == "video" or m_type.startswith("video"):
            return {
                "youtube_id": None,
                "thumbnail": None,
                "embed_url": media.get("url"),
                "watch_url": entry.get("link", "#"),
            }
    return None


def extract_thumbnail(entry):
    """从 RSS entry 提取缩略图 URL。"""
    for media in entry.get("media_thumbnail", []) or []:
        if media.get("url"):
            return media.get("url")
    for media in entry.get("media_content", []) or []:
        if media.get("medium") == "image" or "image" in media.get("type", ""):
            if media.get("url"):
                return media.get("url")
    for enc in entry.get("enclosures", []) or []:
        if enc.get("type", "").startswith("image"):
            return enc.get("href")
    # content 字段内嵌图片
    content = entry.get("summary", "") + str(entry.get("content", ""))
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', content)
    if m:
        return m.group(1)
    return None


def is_ai_related(title, summary):
    """检查文本是否包含 AI 相关关键词。"""
    text = (title + " " + summary).lower()
    return any(kw.lower() in text for kw in AI_KEYWORDS)


def fetch_feed(url, source_name, default_category, keywords_filter=False):
    """抓取并解析一个 RSS feed，返回标准化的条目列表。"""
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"  ✗ {source_name}: {e}", file=sys.stderr)
        return []

    if feed.bozo and not feed.entries:
        print(f"  ⚠ {source_name}: feed 解析异常", file=sys.stderr)
        return []

    items = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)

    for e in feed.entries[:30]:
        published = parse_date(e) or now
        if published < cutoff:
            continue

        title = clean_text(e.get("title", ""), max_len=300).strip()
        summary = clean_text(
            e.get("summary", "") or e.get("description", ""), max_len=200
        )

        if not title:
            continue

        if keywords_filter and not is_ai_related(title, summary):
            continue

        video = extract_video(e)
        thumbnail = extract_thumbnail(e)
        if not thumbnail and video:
            thumbnail = video["thumbnail"]

        items.append({
            "title": title,
            "url": e.get("link", "#"),
            "summary": summary,
            "published": published,
            "published_str": format_relative(now - published),
            "source": source_name,
            "category": default_category,
            "video": video,
            "thumbnail": thumbnail,
            "has_video": bool(video),
        })

    print(f"  ✓ {source_name}: {len(items)} 条")
    return items


def format_relative(delta):
    """把时间差转成 '3 小时前' 这种相对描述。"""
    seconds = delta.total_seconds()
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{int(seconds // 60)} 分钟前"
    if seconds < 86400:
        return f"{int(seconds // 3600)} 小时前"
    return f"{int(seconds // 86400)} 天前"


def dedupe(items):
    """按 URL 和标题去重。"""
    seen_urls = set()
    seen_titles = set()
    result = []
    for item in items:
        url_key = item["url"].split("?")[0].rstrip("/")
        title_key = re.sub(r"\W+", "", item["title"].lower())[:60]
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        result.append(item)
    return result


def rank(items):
    """排序：有视频的优先，再按发布时间倒序。"""
    return sorted(
        items,
        key=lambda x: (0 if x["has_video"] else 1, -x["published"].timestamp()),
    )


def main():
    sources_path = SCRIPTS / "sources.yml"
    if not sources_path.exists():
        print(f"找不到 {sources_path}", file=sys.stderr)
        sys.exit(1)

    sources = yaml.safe_load(sources_path.read_text(encoding="utf-8"))

    ai_items = []
    world_items = []

    print("→ AI 圈来源：")
    for src in sources.get("ai", []):
        items = fetch_feed(
            src["url"],
            src["name"],
            "ai",
            keywords_filter=src.get("keywords_required", False),
        )
        ai_items.extend(items)

    print("\n→ 全球来源：")
    for src in sources.get("world", []):
        items = fetch_feed(
            src["url"],
            src["name"],
            "world",
            keywords_filter=False,
        )
        world_items.extend(items)

    ai_items = rank(dedupe(ai_items))[:MAX_PER_SECTION]
    world_items = rank(dedupe(world_items))[:MAX_PER_SECTION]

    print(f"\n→ 最终：AI {len(ai_items)} 条，全球 {len(world_items)} 条")

    if not ai_items and not world_items:
        print("⚠ 没有抓到任何内容，跳过生成", file=sys.stderr)
        sys.exit(0)

    # 渲染
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("index.html.j2")

    now_local = datetime.now(timezone.utc) + timedelta(hours=TIMEZONE_OFFSET)
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    date_str = (
        f"{now_local.year}年{now_local.month}月{now_local.day}日 · "
        f"星期{weekdays[now_local.weekday()]}"
    )

    def split(items):
        """切成头条 + 副条 + 网格三块。"""
        return {
            "lede_main": items[0] if len(items) > 0 else None,
            "lede_side": items[1:3] if len(items) > 1 else [],
            "grid": items[3:] if len(items) > 3 else [],
            "count": len(items),
        }

    rendered = template.render(
        date=date_str,
        updated_at=now_local.strftime("%Y-%m-%d %H:%M"),
        ai=split(ai_items),
        world=split(world_items),
    )

    output_path = ROOT / "index.html"
    output_path.write_text(rendered, encoding="utf-8")
    print(f"\n✓ 生成 {output_path}")


if __name__ == "__main__":
    main()

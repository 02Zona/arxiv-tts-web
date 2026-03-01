# arxiv-tts-web

一个**纯文本 arXiv feed + 网页本地 TTS 播放器**的小项目。

## 项目结构

- `index.html`：网页播放器，直接读取 `feed.xml` 并朗读 `itunes:summary`。
- `feed.xml`：每天自动生成的 RSS 文件（不包含音频 enclosure）。
- `tools/config.yml`：类别、时间窗口、最大条数配置。
- `tools/generate_feed.py`：抓取 arXiv RSS 并生成 `feed.xml`。
- `.github/workflows/generate_feed.yml`：GitHub Actions 每日自动更新 feed。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r tools/requirements.txt
python tools/generate_feed.py
python -m http.server 8000
```

然后打开 `http://localhost:8000`。

## 自动更新

工作流每天 UTC `17:15` 运行一次，只有 `feed.xml` 发生变化时才会自动提交。

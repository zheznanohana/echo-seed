# Echo Seed / 回声种子

> 让每一个想法都有回声 🌱  
> Every idea deserves an echo.

简洁优雅的想法记录工具，支持快速记录、智能分类、时间线视图和多端同步。

A simple and elegant idea capture tool with quick notes, smart categorization, timeline view, and multi-platform sync.

---

## ✨ 特性 / Features

- 📝 **快速记录** - 一键创建，支持 8 种类型（笔记/灵感/链接/日记/思考/收藏/待办/语音）
- 🎨 **智能分类** - 自动标签、颜色编码、类型区分
- 📅 **时间线视图** - 按时间顺序浏览所有想法
- 🔍 **搜索筛选** - 全文搜索、类型过滤、标签筛选
- 📊 **统计面板** - 数据可视化、类型分布、趋势分析
- 🤖 **AI 增强** - 点子扩张、链接分析、智能关联（可选）
- 🔄 **多端同步** - Notion、Google Calendar、Telegram Bot

- 📝 **Quick Capture** - 8 types (note/idea/link/diary/thought/collection/todo/voice)
- 🎨 **Smart Categorization** - Auto tags, color coding
- 📅 **Timeline View** - Browse by time
- 🔍 **Search & Filter** - Full-text search, type filter
- 📊 **Statistics** - Data visualization
- 🤖 **AI Enhanced** - Idea expansion, link analysis, smart relations
- 🔄 **Multi-Platform Sync** - Notion, Google Calendar, Telegram Bot

---

## 🚀 快速开始 / Quick Start

### 安装 / Installation

```bash
# 克隆项目 / Clone repository
git clone https://github.com/zheznanohana/echo-seed.git
cd echo-seed

# 安装依赖 / Install dependencies
pip install -r requirements.txt
```

### 启动服务 / Start Service

```bash
# 启动 Web 服务 / Start Web service
python3 scripts/echo-web.py

# 访问 / Visit
http://localhost:5000
```

### 配置（可选）/ Configuration (Optional)

复制配置示例并编辑：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml` 配置：
- 数据库路径 / Database path
- Web 服务端口 / Web port
- Notion API（同步用）/ Notion API (for sync)
- Google Calendar（待办同步）/ Google Calendar (for todo sync)

---

## 📱 Telegram Bot

通过 Bot 快速创建种子：

Quick seed creation via Telegram Bot:

```bash
# 启动 Bot / Start Bot
python3 scripts/echo-telegram-bot.py
```

**支持的命令 / Supported Commands:**

| 命令 / Command | 说明 / Description |
|----------------|-------------------|
| `/note` | 创建笔记 / Create note |
| `/idea` | 创建灵感 / Create idea |
| `/link` | 创建链接 / Create link |
| `/todo` | 创建待办 / Create todo |
| `/diary` | 创建日记 / Create diary |
| `/thought` | 创建思考 / Create thought |
| `/collect` | 创建收藏 / Create collection |
| `/voice` | 创建语音 / Create voice |
| `/list` | 查看最近种子 / List recent seeds |
| `/search` | 搜索种子 / Search seeds |
| `/stats` | 统计信息 / Statistics |

---

## 🤖 AI 功能 / AI Features

Echo Seed 支持 AI 增强功能：

Echo Seed supports AI-enhanced features:

- **点子扩张** - 输入简单想法，AI 扩展成完整方案
- **链接分析** - 输入 URL，AI 自动提取内容并总结
- **智能关联** - 自动发现相关种子，建立知识关联

- **Idea Expansion** - AI expands simple ideas into detailed plans
- **Link Analysis** - AI extracts and summarizes URL content
- **Smart Relations** - Auto-discover related seeds

详见 / See: [README-AI.md](README-AI.md)

---

## 📦 数据库 / Database

使用 SQLite 存储，默认路径：`data/echo.db`

Uses SQLite storage, default path: `data/echo.db`

数据库会自动创建，包含以下表：

Database auto-created with tables:
- `seeds` - 种子主表 / Main seeds table
- `seed_relations` - 种子关联表 / Seed relations table
- `seed_tags` - 种子标签表 / Seed tags table
- `ai_analyses` - AI 分析记录表 / AI analysis records

---

## 🔧 API

提供 REST API 供前端调用：

REST API endpoints:

| 端点 / Endpoint | 方法 / Method | 说明 / Description |
|-----------------|---------------|-------------------|
| `/api/seeds` | GET | 获取种子列表 / Get seeds list |
| `/api/seeds` | POST | 创建种子 / Create seed |
| `/api/seeds/<id>` | PUT | 更新种子 / Update seed |
| `/api/seeds/<id>` | DELETE | 删除种子 / Delete seed |
| `/api/stats` | GET | 获取统计信息 / Get statistics |
| `/api/export/<format>` | GET | 导出数据 / Export data (json/csv/markdown) |
| `/api/seed/<id>/analyze/expand` | POST | AI 点子扩张 / AI idea expansion |
| `/api/seed/<id>/analyze/link` | POST | AI 链接分析 / AI link analysis |
| `/api/seed/<id>/relations` | GET | 获取关联种子 / Get related seeds |

---

## 🛠️ 技术栈 / Tech Stack

- **后端 / Backend:** Python 3.10+, Flask
- **数据库 / Database:** SQLite
- **前端 / Frontend:** HTML, TailwindCSS, Vue 3 (CDN)
- **AI:** MiniMax API (兼容 Anthropic 格式 / Anthropic-compatible)

---

## 📄 许可证 / License

MIT License

---

**GitHub:** https://github.com/zheznanohana/echo-seed  
**作者 / Author:** Zhu Zhe (@zheznanohana)

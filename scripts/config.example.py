#!/usr/bin/env python3
"""
Echo Seed 配置文件示例

复制此文件为 config.py 并填入你的配置信息
"""

# =============================================================================
# Telegram Bot 配置
# =============================================================================
# 通过 @BotFather 创建 Bot 并获取 Token
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# =============================================================================
# Notion API 配置
# =============================================================================
# 1. 访问 https://www.notion.so/my-integrations 创建 Integration
# 2. 获取 Internal Integration Token
# 3. 将你的页面分享到该 Integration
NOTION_API_KEY = "YOUR_NOTION_API_KEY_HERE"
NOTION_PARENT_PAGE_ID = "YOUR_PARENT_PAGE_ID_HERE"

# =============================================================================
# Google Calendar API 配置
# =============================================================================
# 使用 Maton Gateway 或 Google Cloud Console 获取 API Key
GOOGLE_CALENDAR_API_KEY = "YOUR_GOOGLE_CALENDAR_API_KEY_HERE"

# =============================================================================
# MiniMax API 配置（可选）
# =============================================================================
# 访问 https://platform.minimaxi.com/ 获取 API Key
MINIMAX_API_KEY = "YOUR_MINIMAX_API_KEY_HERE"
MINIMAX_BASE_URL = "https://api.minimaxi.com/anthropic"

# =============================================================================
# Bailian API 配置（可选）
# =============================================================================
# 访问 https://bailian.console.aliyun.com/ 获取 API Key
BAILIAN_API_KEY = "YOUR_BAILIAN_API_KEY_HERE"

# =============================================================================
# 本地服务配置
# =============================================================================
# Echo Seed Web 服务地址
ECHO_SEED_API = "http://localhost:5000/api/capsules"

# =============================================================================
# 数据库配置
# =============================================================================
# SQLite 数据库路径
DATABASE_PATH = "data/capsules.db"

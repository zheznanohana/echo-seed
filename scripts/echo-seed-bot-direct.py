#!/usr/bin/env python3
"""
Echo Seed Telegram Bot - 直接连接 Telegram API 版本

用于测试和调试
"""

import sys
import time
import logging
import requests
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 导入消息处理模块
from echo_telegram import process_message

# 配置 - 请替换为你的 Bot Token
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 日志
LOG_DIR = ROOT_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'echo-seed-bot-direct.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

processed_messages = set()

def get_updates(offset=None):
    """获取更新"""
    url = f"{TELEGRAM_API}/getUpdates"
    params = {'timeout': 30, 'offset': offset}
    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json().get('result', [])
    except Exception as e:
        logger.error(f"获取更新失败：{e}")
        return []

def send_message(chat_id, text):
    """发送消息"""
    url = f"{TELEGRAM_API}/sendMessage"
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        if result.get('ok'):
            return True
        else:
            logger.error(f"发送失败：{result}")
            return False
    except Exception as e:
        logger.error(f"发送消息失败：{e}")
        return False

def format_ai_reply(result):
    """格式化 AI 分析回复（第一条消息）"""
    capsule_type = result.get('type', 'note')
    type_names = {
        'note': '📝 笔记',
        'idea': '💡 灵感',
        'link': '🔗 链接',
        'todo': '✅ 待办',
        'diary': '📔 日记',
        'thought': '💭 思考',
        'collection': '⭐ 收藏',
        'voice': '🎤 语音',
    }
    type_name = type_names.get(capsule_type, '📝 笔记')
    
    content = result.get('content', '')
    
    # 构建美观的回复
    lines = []
    lines.append(f"*{type_name} 已创建* ✨")
    lines.append("")
    lines.append(f"📝 {content[:150]}{'...' if len(content) > 150 else ''}")
    lines.append("")
    lines.append(f"🆔 `{result.get('id', '')}`")
    
    # AI 分析
    ai_analysis = result.get('ai_analysis', {})
    if ai_analysis and isinstance(ai_analysis, dict):
        lines.append("")
        lines.append("━" * 20)
        lines.append("*💡 AI 分析*")
        lines.append("━" * 20)
        
        for key, value in ai_analysis.items():
            lines.append("")
            lines.append(f"*{key}：*")
            if isinstance(value, list):
                for i, item in enumerate(value[:5], 1):
                    lines.append(f"  {i}. {item}")
            else:
                lines.append(f"  {value}")
    
    # 标签
    tags = result.get('tags', [])
    if tags:
        lines.append("")
        lines.append(f"🏷️ `{' | '.join(tags[:5])}`")
    
    return "\n".join(lines)

def format_sync_links(result):
    """格式化同步链接回复（第二条消息）"""
    lines = []
    
    lines.append("━" * 20)
    lines.append("*📌 同步状态*")
    lines.append("━" * 20)
    
    notion_url = result.get('notion_url')
    if notion_url:
        lines.append(f"✅ Notion 已同步")
        lines.append(f"   🔗 {notion_url}")
    
    calendar_link = result.get('calendar_link')
    if calendar_link:
        lines.append(f"✅ 日历提醒已创建")
        lines.append(f"   📅 {calendar_link}")
    elif result.get('type') == 'todo':
        lines.append(f"⚠️ 未检测到时间信息，无法创建日历提醒")
    
    return "\n".join(lines)

def main():
    """主循环"""
    logger.info("=" * 60)
    logger.info("🌱 Echo Seed Bot (Direct) 启动中...")
    logger.info(f"Bot: @echo_seed_bot")
    logger.info(f"API: http://localhost:5000/api/capsules")
    logger.info("=" * 60)
    
    # 测试 Bot 连接
    try:
        me = requests.get(f"{TELEGRAM_API}/getMe", timeout=10).json()
        if me.get('ok'):
            logger.info(f"✅ Bot 登录成功：@{me['result'].get('username', 'Unknown')}")
        else:
            logger.error(f"❌ Bot 登录失败：{me}")
    except Exception as e:
        logger.error(f"❌ 无法连接 Telegram: {e}")
        return
    
    offset = None
    
    while True:
        try:
            updates = get_updates(offset)
            
            for update in updates:
                offset = update.get('update_id') + 1
                
                message = update.get('message', {})
                chat_id = message.get('chat', {}).get('id')
                user_id = message.get('from', {}).get('id')
                text = message.get('text', '')
                msg_id = message.get('message_id')
                
                # 跳过已处理的消息
                if msg_id in processed_messages:
                    continue
                
                processed_messages.add(msg_id)
                if len(processed_messages) > 1000:
                    processed_messages.clear()
                
                logger.info(f"收到消息：{user_id} - {text[:50]}...")
                
                # 处理消息（返回完整结果）
                result = process_message(text, user_id, return_full_result=True)
                
                # 发送消息
                if result.get('success'):
                    # 消息 1：AI 分析
                    reply1 = format_ai_reply(result)
                    logger.info(f"发送 AI 分析回复")
                    send_message(chat_id, reply1)
                    time.sleep(0.5)
                    
                    # 消息 2：Notion 链接
                    notion_url = result.get('notion_url')
                    if notion_url:
                        reply2 = f"━━━━━━━━━━━━━━━━━━━━\n*📌 Notion 同步*\n━━━━━━━━━━━━━━━━━━━━\n✅ 已同步到 Notion\n   🔗 {notion_url}"
                        logger.info(f"发送 Notion 链接")
                        send_message(chat_id, reply2)
                        time.sleep(0.5)
                    
                    # 消息 3：Calendar 链接
                    calendar_link = result.get('calendar_link')
                    if calendar_link:
                        reply3 = f"━━━━━━━━━━━━━━━━━━━━\n*📅 日历提醒*\n━━━━━━━━━━━━━━━━━━━━\n✅ 已创建日历事件\n   📅 {calendar_link}"
                        logger.info(f"发送 Calendar 链接")
                        send_message(chat_id, reply3)
                    elif result.get('type') == 'todo':
                        reply3 = f"━━━━━━━━━━━━━━━━━━━━\n*📅 日历提醒*\n━━━━━━━━━━━━━━━━━━━━\n⚠️ 未检测到时间信息"
                        logger.info(f"发送 Calendar 提醒（无时间）")
                        send_message(chat_id, reply3)
                else:
                    # 失败时发送错误消息
                    send_message(chat_id, result.get('error', '❌ 处理失败'))
            
            time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("Bot 停止")
            break
        except Exception as e:
            logger.error(f"错误：{e}")
            time.sleep(5)

if __name__ == '__main__':
    main()

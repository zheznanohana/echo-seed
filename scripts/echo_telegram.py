#!/usr/bin/env python3
"""
Echo Seed Telegram Bot - 消息处理模块

配合 echo-telegram-bot.py 使用
支持：语义分析、AI 扩写、Notion 同步、Calendar 同步
"""

import sys
import json
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 导入 AI 服务
from ai_service import analyze_expansion, analyze_link, analyze_capsule

# Telegram Bot 配置 - 请替换为你的 Bot Token
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Echo Seed API
ECHO_SEED_API = "http://localhost:5000/api/capsules"

# Notion 配置 - 请替换为你的 API Key 和 Page ID
NOTION_API_KEY = "YOUR_NOTION_API_KEY_HERE"
NOTION_BASE_URL = "https://gateway.maton.ai/notion/v1/"
NOTION_PARENT_PAGE_ID = "YOUR_PARENT_PAGE_ID_HERE"

# Google Calendar 配置
GOOGLE_CALENDAR_BASE_URL = "https://gateway.maton.ai/google-calendar/calendar/v3/"

# 类型映射
TYPE_COMMANDS = {
    '/note': 'note',
    '/idea': 'idea',
    '/link': 'link',
    '/todo': 'todo',
    '/diary': 'diary',
    '/thought': 'thought',
    '/collect': 'collection',
    '/voice': 'voice',
}

TYPE_NAMES = {
    'note': '📝 笔记',
    'idea': '💡 灵感',
    'link': '🔗 链接',
    'todo': '✅ 待办',
    'diary': '📔 日记',
    'thought': '💭 思考',
    'collection': '⭐ 收藏',
    'voice': '🎤 语音',
}

def parse_command(text):
    """解析命令，返回 (类型，内容)"""
    lines = text.strip().split('\n', 1)
    command = lines[0].strip().lower()
    content = lines[1].strip() if len(lines) > 1 else ''
    
    capsule_type = None
    
    # 检查是否以 / 开头的命令
    if command.startswith('/'):
        for cmd, ctype in TYPE_COMMANDS.items():
            if command.startswith(cmd):
                capsule_type = ctype
                if command[len(cmd):].strip():
                    content = command[len(cmd):].strip() + '\n' + content
                break
        
        if not capsule_type:
            capsule_type = 'note'
    else:
        # 没有 / 命令，自动语义分析
        capsule_type, content = semantic_analysis(text)
    
    return capsule_type, content

def semantic_analysis(text):
    """语义分析识别胶囊类型"""
    text_lower = text.lower()
    
    # 待办：提醒、记得、时间、任务相关
    todo_keywords = ['提醒', '记得', '明天', '下午', '上午', '点', 'todo', '待办', 
                     '叫我', '起床', '闹钟', '开会', '面试', '去医院', '预约',
                     '要去', '要做', '别忘了', '记得要']
    if any(kw in text_lower for kw in todo_keywords):
        return 'todo', text
    
    # 灵感：创意、想法、做个
    elif any(kw in text_lower for kw in ['想法', '创意', 'idea', '灵感', '做个', '做一个', '开发', '产品']):
        return 'idea', text
    
    # 链接：URL
    elif any(kw in text_lower for kw in ['http://', 'https://', '链接', 'link', '网址']):
        return 'link', text
    
    # 日记：心情、情感
    elif any(kw in text_lower for kw in ['日记', '心情', 'diary', '今天好', '今天很', '今天真']):
        return 'diary', text
    
    # 思考：深度思考
    elif any(kw in text_lower for kw in ['思考', 'thought', '我觉得', '我认为', '怎么看']):
        return 'thought', text
    
    # 收藏：收藏、mark
    elif any(kw in text_lower for kw in ['收藏', 'collect', 'mark', '马住']):
        return 'collection', text
    
    # 默认：笔记
    return 'note', text

def extract_time(text):
    """从文本中提取时间（支持今天/明天/后天/具体日期）"""
    # 标准化文本
    text_normalized = text.replace('明早', '明天早上').replace('今晚', '今天晚上')
    text_lower = text_normalized.lower()
    
    now = datetime.now()
    target_date = now  # 默认今天
    
    # 1. 识别日期（今天/明天/后天/大后天）
    if '明天' in text_lower or '明早' in text_normalized:
        target_date = now + timedelta(days=1)
    elif '后天' in text_lower:
        target_date = now + timedelta(days=2)
    elif '大后天' in text_lower:
        target_date = now + timedelta(days=3)
    
    # 2. 识别具体日期（3 月 10 号、3/10、3.10）
    date_patterns = [
        r'(\d+) 月 (\d+) [号日]',
        r'(\d+)/(\d+)',
        r'(\d+)\.(\d+)',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            # 假设是当前年份
            target_date = now.replace(month=month, day=day)
            break
    
    # 3. 识别时间（冒号格式 9:30）
    time_patterns_colon = [
        r'(\d+):(\d+)',
    ]
    for pattern in time_patterns_colon:
        match = re.search(pattern, text_normalized)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            
            # 处理上午/下午
            is_pm = '下午' in text_lower or '晚上' in text_lower or '今晚' in text_lower
            is_am = '上午' in text_lower or '早上' in text_lower
            
            if is_pm and hour < 12:
                hour += 12
            elif is_am and hour >= 12:
                hour -= 12
            
            reminder = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 如果时间已过，设为明天（如果是今天的话）
            if target_date.date() == now.date() and reminder < now:
                reminder = reminder + timedelta(days=1)
            
            return reminder.isoformat()
    
    # 4. 识别时间（"点"格式：9 点、9 点 30）
    time_patterns_dian = [
        (r'(\d+) 点 (\d+)', True),  # 9 点 30
        (r'(\d+) 点', False),  # 9 点
    ]
    for pattern, has_minute in time_patterns_dian:
        match = re.search(pattern, text_normalized)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if has_minute and match.group(2) else 0
            
            # 处理上午/下午
            is_pm = '下午' in text_lower or '晚上' in text_lower or '今晚' in text_lower
            is_am = '上午' in text_lower or '早上' in text_lower
            
            if is_pm and hour < 12:
                hour += 12
            elif is_am and hour >= 12:
                hour -= 12
            
            reminder = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 如果时间已过，设为明天（如果是今天的话）
            if target_date.date() == now.date() and reminder < now:
                reminder = reminder + timedelta(days=1)
            
            return reminder.isoformat()
    
    return None

def extract_url(text):
    """从文本中提取 URL"""
    url_pattern = r'https?://[^\s]+'
    match = re.search(url_pattern, text)
    return match.group(0) if match else ''

def sync_to_notion(capsule_id, capsule_type, title, content, tags, ai_analysis=None):
    """同步胶囊到 Notion（包含 AI 分析）"""
    try:
        headers = {
            'Authorization': f'Bearer {NOTION_API_KEY}',
            'Notion-Version': '2025-09-03',
            'Content-Type': 'application/json'
        }
        
        type_emoji = TYPE_NAMES.get(capsule_type, '📝').split()[0]
        
        # 构建页面内容块
        children = [
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': content or ''
                            }
                        }
                    ]
                }
            }
        ]
        
        # 添加 AI 分析内容
        if ai_analysis:
            children.append({
                'object': 'block',
                'type': 'heading_3',
                'heading_3': {
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': '💡 AI 分析'
                            }
                        }
                    ]
                }
            })
            
            if isinstance(ai_analysis, dict):
                for key, value in ai_analysis.items():
                    # 添加小标题（使用 heading_4 而不是 paragraph+bold）
                    children.append({
                        'object': 'block',
                        'type': 'heading_4',
                        'heading_4': {
                            'rich_text': [
                                {
                                    'type': 'text',
                                    'text': {
                                        'content': key
                                    }
                                }
                            ]
                        }
                    })
                    
                    # 添加内容
                    if isinstance(value, list):
                        for item in value:
                            children.append({
                                'object': 'block',
                                'type': 'bulleted_list_item',
                                'bulleted_list_item': {
                                    'rich_text': [
                                        {
                                            'type': 'text',
                                            'text': {
                                                'content': str(item)
                                            }
                                        }
                                    ]
                                }
                            })
                    else:
                        children.append({
                            'object': 'block',
                            'type': 'paragraph',
                            'paragraph': {
                                'rich_text': [
                                    {
                                        'type': 'text',
                                        'text': {
                                            'content': str(value)
                                        }
                                    }
                                ]
                            }
                        })
        
        # 添加标签
        if tags:
            children.append({
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': f'\n🏷️ Tags: {", ".join(tags)}'
                            }
                        }
                    ]
                }
            })
        
        page_data = {
            'parent': {'type': 'page_id', 'page_id': NOTION_PARENT_PAGE_ID},
            'properties': {
                'title': [
                    {
                        'text': {
                            'content': f"{type_emoji} {title or 'Untitled Capsule'}"
                        }
                    }
                ]
            },
            'children': children
        }
        
        response = requests.post(
            f'{NOTION_BASE_URL}pages',
            headers=headers,
            json=page_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            return result.get('id'), result.get('url')
        else:
            print(f"Notion 同步失败：{response.status_code} - {response.text}")
            return None, None
            
    except Exception as e:
        print(f"Notion 同步异常：{e}")
        import traceback
        traceback.print_exc()
        return None, None

def sync_to_calendar(title, content, reminder_at):
    """同步待办事项到 Google Calendar"""
    try:
        if not reminder_at:
            return None, None
        
        headers = {
            'Authorization': f'Bearer {NOTION_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # 处理时间格式
        reminder_dt = datetime.fromisoformat(reminder_at)
        
        event_data = {
            'summary': f'✅ {title or "Capsule Reminder"}',
            'description': content or '',
            'start': {
                'dateTime': reminder_dt.isoformat(),
                'timeZone': 'Asia/Shanghai'
            },
            'end': {
                'dateTime': (reminder_dt + timedelta(hours=1)).isoformat(),
                'timeZone': 'Asia/Shanghai'
            }
        }
        
        response = requests.post(
            f'{GOOGLE_CALENDAR_BASE_URL}calendars/primary/events',
            headers=headers,
            json=event_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            event_id = result.get('id')
            html_link = result.get('htmlLink')
            return event_id, html_link
        else:
            print(f"Calendar 同步失败：{response.status_code} - {response.text}")
            return None, None
            
    except Exception as e:
        print(f"Calendar 同步异常：{e}")
        import traceback
        traceback.print_exc()
        return None, None

def create_capsule(capsule_type, content, url='', tags=''):
    """创建种子（带 AI 分析和同步）"""
    try:
        data = {
            'type': capsule_type,
            'title': content[:50] if content else 'Untitled',
            'content': content,
            'url': url,
            'tags': tags,
        }
        
        response = requests.post(ECHO_SEED_API, json=data, timeout=15)
        
        if response.status_code != 200:
            return False, {'error': response.text}
        
        result = response.json()
        capsule_id = result.get('id')
        
        # AI 分析（所有类型都分析）
        ai_tags = []
        ai_analysis = None
        
        try:
            # 使用通用的 analyze_capsule 函数
            ai_result = analyze_capsule(capsule_id, capsule_type, content, url)
            if ai_result.get('success'):
                ai_tags.extend(ai_result.get('suggested_tags', []))
                ai_analysis = ai_result.get('analysis', {})
        except Exception as e:
            pass
        
        # 同步到 Notion（包含 AI 分析）
        notion_page_id, notion_url = sync_to_notion(
            capsule_id, capsule_type,
            data['title'], content, tags,
            ai_analysis
        )
        
        # 同步到 Google Calendar
        calendar_event_id = None
        calendar_link = None
        if capsule_type == 'todo':
            reminder_at = extract_time(content)
            if reminder_at:
                calendar_event_id, calendar_link = sync_to_calendar(data['title'], content, reminder_at)
        
        # 构建回复
        type_name = TYPE_NAMES.get(capsule_type, '📝 笔记')
        reply = f"""✅ {type_name} 已创建

📝 内容：{content[:100]}{'...' if len(content) > 100 else ''}
🆔 ID: `{capsule_id}`
"""
        
        # AI 分析内容（所有类型都显示）
        if ai_analysis:
            reply += "\n💡 AI 分析：\n"
            if isinstance(ai_analysis, dict):
                for key, value in ai_analysis.items():
                    if isinstance(value, list):
                        reply += f"\n{key}:\n"
                        for item in value[:5]:
                            reply += f"  • {item}\n"
                    else:
                        reply += f"\n{key}: {value}\n"
            else:
                reply += f"{ai_analysis}\n"
        elif ai_tags:
            reply += f"\n🏷️ AI 标签：{', '.join(ai_tags[:5])}\n"
        
        if notion_url:
            reply += f"🔗 Notion: {notion_url}\n"
        
        if calendar_event_id:
            reply += f"📅 Calendar: 已添加提醒"
        
        return True, {
            'id': capsule_id,
            'notion_url': notion_url,
            'calendar_event_id': calendar_event_id,
            'calendar_link': calendar_link,
            'ai_tags': ai_tags,
            'ai_analysis': ai_analysis,
            'reply': reply
        }
    
    except Exception as e:
        return False, {'error': str(e)}

def process_message(text, user_id=None, return_full_result=False):
    """处理 Telegram 消息"""
    if not text:
        return "❌ 消息不能为空" if not return_full_result else {'success': False, 'error': '消息不能为空'}
    
    capsule_type, content = parse_command(text)
    url = extract_url(content)
    success, result = create_capsule(capsule_type, content, url)
    
    if success:
        if return_full_result:
            # 返回完整结果供 Bot 格式化
            return {
                'success': True,
                'id': result.get('id'),
                'type': capsule_type,
                'content': content,
                'tags': result.get('ai_tags', []),
                'ai_analysis': result.get('ai_analysis', {}),
                'notion_url': result.get('notion_url'),
                'calendar_event_id': result.get('calendar_event_id'),
                'calendar_link': result.get('calendar_link'),
            }
        else:
            return result.get('reply', '✅ 创建成功')
    else:
        if return_full_result:
            return {'success': False, 'error': result.get('error', 'Unknown error')}
        else:
            return f"❌ 创建失败：{result.get('error', 'Unknown error')}"

if __name__ == '__main__':
    # 测试
    print(process_message("/idea 做个 VR 版的 B 站", "test_user"))

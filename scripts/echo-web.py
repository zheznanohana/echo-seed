#!/usr/bin/env python3
"""
Echo Seed Web 端 - Flask 后端

提供 REST API 和 Web 界面
"""

from flask import Flask, render_template, jsonify, request, Response
import sqlite3
import json
import csv
import io
import requests
from datetime import datetime, timedelta
from pathlib import Path
import sys

# API 配置
NOTION_API_KEY = '3nkZbXz4HX_EuDapN2Gbv1ZE8iML1MmbO8VwdO-lgJJTXvm5fWk_CeHfCZkrCOdA3AYZKT9NHvAHii0j4MLL2m6Cl5JMaCUkksk'
NOTION_BASE_URL = 'https://gateway.maton.ai/notion/v1/'
GOOGLE_CALENDAR_BASE_URL = 'https://gateway.maton.ai/google-calendar/calendar/v3/'

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 初始化 Flask，明确指定模板和静态文件路径
app = Flask(__name__,
            template_folder=str(ROOT_DIR / 'templates'),
            static_folder=str(ROOT_DIR / 'static'))

# 数据库路径
DB_PATH = ROOT_DIR / 'data' / 'capsules.db'

# 胶囊类型配置（颜色）
CAPSULE_CONFIG = {
    'note': {'name': '笔记', 'emoji': '📝', 'color': '#6B7280', 'bg': '#F3F4F6'},
    'idea': {'name': '灵感', 'emoji': '💡', 'color': '#F59E0B', 'bg': '#FEF3C7'},
    'link': {'name': '链接', 'emoji': '🔗', 'color': '#3B82F6', 'bg': '#DBEAFE'},
    'diary': {'name': '日记', 'emoji': '📔', 'color': '#10B981', 'bg': '#D1FAE5'},
    'thought': {'name': '思考', 'emoji': '💭', 'color': '#8B5CF6', 'bg': '#EDE9FE'},
    'collection': {'name': '收藏', 'emoji': '⭐', 'color': '#EC4899', 'bg': '#FCE7F3'},
    'todo': {'name': '待办', 'emoji': '✅', 'color': '#EF4444', 'bg': '#FEE2E2'},
    'voice': {'name': '语音', 'emoji': '🎤', 'color': '#06B6D4', 'bg': '#CFFAFE'},
}

# 状态配置
STATUS_CONFIG = {
    'active': {'name': '活跃', 'color': '#10B981'},
    'completed': {'name': '已完成', 'color': '#6B7280'},
    'archived': {'name': '已归档', 'color': '#9CA3AF'},
}


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS capsules (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL DEFAULT 'note',
            title TEXT,
            content TEXT,
            url TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reminder_at TIMESTAMP,
            status TEXT DEFAULT 'active',
            completed_at TIMESTAMP,
            archived_at TIMESTAMP,
            notion_id TEXT,
            calendar_event_id TEXT,
            voice_data TEXT,
            metadata TEXT
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON capsules(type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON capsules(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_created ON capsules(created_at)')
    
    conn.commit()
    conn.close()


def sync_to_notion(capsule_id, capsule_type, title, content, tags):
    """同步胶囊到 Notion"""
    try:
        # 获取 Notion 数据库 ID（从 metadata 或配置）
        # 这里使用一个简单的页面创建方式
        headers = {
            'Authorization': f'Bearer {NOTION_API_KEY}',
            'Notion-Version': '2025-09-03',
            'Content-Type': 'application/json'
        }
        
        # 构建页面内容
        type_emoji = CAPSULE_CONFIG.get(capsule_type, {}).get('emoji', '📝')
        type_name = CAPSULE_CONFIG.get(capsule_type, {}).get('name', capsule_type)
        
        # 使用搜索 API 获取用户的 Notion 空间中的第一个页面作为父级
        # 或者直接创建独立页面（需要 parent）
        # 这里我们先尝试创建一个简单页面
        page_data = {
            'parent': {'type': 'page_id', 'page_id': '31ad06db920781079a13d1a5738c5bdd'},  # 红烧肉菜谱页面作为测试
            'properties': {
                'title': [
                    {
                        'text': {
                            'content': f"{type_emoji} {title or 'Untitled Capsule'}"
                        }
                    }
                ]
            },
            'children': [
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
        }
        
        if tags:
            page_data['children'].append({
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': f'Tags: {tags}'
                            }
                        }
                    ]
                }
            })
        
        response = requests.post(
            f'{NOTION_BASE_URL}pages',
            headers=headers,
            json=page_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            return result.get('id')
        else:
            print(f"Notion sync failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Notion sync error: {e}")
        return None


def sync_to_calendar(capsule_id, title, content, reminder_at):
    """同步待办事项到 Google Calendar"""
    try:
        if not reminder_at:
            return None
        
        headers = {
            'Authorization': f'Bearer {NOTION_API_KEY}',  # 使用相同的 API key
            'Content-Type': 'application/json'
        }
        
        # 解析提醒时间
        try:
            reminder_dt = datetime.fromisoformat(reminder_at.replace('Z', '+00:00'))
        except:
            reminder_dt = datetime.now() + timedelta(days=1)
        
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
            return result.get('id')
        else:
            print(f"Calendar sync failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Calendar sync error: {e}")
        return None


@app.route('/')
def index():
    """Web 界面"""
    return render_template('index.html')


@app.route('/api/capsules', methods=['GET'])
def get_capsules():
    """获取胶囊列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取查询参数
        capsule_type = request.args.get('type')
        status = request.args.get('status')
        search = request.args.get('search')
        limit = request.args.get('limit', 100)
        
        # 构建查询
        query = 'SELECT * FROM capsules WHERE 1=1'
        params = []
        
        if capsule_type:
            query += ' AND type = ?'
            params.append(capsule_type)
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if search:
            query += ' AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(int(limit))
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        capsules = []
        for row in rows:
            capsule = dict(row)
            type_info = CAPSULE_CONFIG.get(capsule['type'], {})
            capsule['type_name'] = type_info.get('name', capsule['type'])
            capsule['type_emoji'] = type_info.get('emoji', '')
            capsule['type_color'] = type_info.get('color', '#6B7280')
            capsule['type_bg'] = type_info.get('bg', '#F3F4F6')
            capsules.append(capsule)
        
        return jsonify({'success': True, 'data': capsules, 'count': len(capsules)})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/capsules', methods=['POST'])
def create_capsule():
    """创建胶囊"""
    try:
        data = request.json
        capsule_id = data.get('id', datetime.now().strftime('%Y%m%d%H%M%S%f'))
        created_at = datetime.now().isoformat()
        
        capsule_type = data.get('type', 'note')
        title = data.get('title', '')
        content = data.get('content', '')
        tags = data.get('tags', '')
        reminder_at = data.get('reminder_at')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 先插入胶囊
        cursor.execute('''
            INSERT INTO capsules 
            (id, type, title, content, url, tags, created_at, reminder_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            capsule_id,
            capsule_type,
            title,
            content,
            data.get('url', ''),
            tags,
            created_at,
            reminder_at,
            json.dumps(data.get('metadata', {}))
        ))
        
        # 同步到 Notion
        notion_page_id = sync_to_notion(capsule_id, capsule_type, title, content, tags)
        
        # 同步到 Google Calendar（仅待办类型且有提醒时间）
        calendar_event_id = None
        if capsule_type == 'todo' and reminder_at:
            calendar_event_id = sync_to_calendar(capsule_id, title, content, reminder_at)
        
        # 更新同步 ID
        if notion_page_id or calendar_event_id:
            updates = []
            params = []
            if notion_page_id:
                updates.append('notion_page_id = ?')
                params.append(notion_page_id)
            if calendar_event_id:
                updates.append('calendar_event_id = ?')
                params.append(calendar_event_id)
            params.append(capsule_id)
            cursor.execute(f"UPDATE capsules SET {', '.join(updates)} WHERE id = ?", params)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': capsule_id, 'notion_page_id': notion_page_id, 'calendar_event_id': calendar_event_id})
    
    except Exception as e:
        print(f"Create capsule error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/capsules/<capsule_id>', methods=['PUT'])
def update_capsule(capsule_id):
    """更新胶囊"""
    try:
        data = request.json
        conn = get_db()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        for field in ['title', 'content', 'url', 'tags', 'status', 'reminder_at']:
            if field in data:
                updates.append(f'{field} = ?')
                params.append(data[field])
        
        if not updates:
            return jsonify({'success': False, 'error': 'No fields to update'})
        
        params.append(capsule_id)
        query = f"UPDATE capsules SET {', '.join(updates)} WHERE id = ?"
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/capsules/<capsule_id>', methods=['DELETE'])
def delete_capsule(capsule_id):
    """删除胶囊"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM capsules WHERE id = ?', (capsule_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 总数
        cursor.execute('SELECT COUNT(*) FROM capsules')
        total = cursor.fetchone()[0]
        
        # 按类型统计
        cursor.execute('SELECT type, COUNT(*) FROM capsules GROUP BY type')
        by_type = dict(cursor.fetchall())
        
        # 按状态统计
        cursor.execute('SELECT status, COUNT(*) FROM capsules GROUP BY status')
        by_status = dict(cursor.fetchall())
        
        # 待办事项
        cursor.execute("SELECT COUNT(*) FROM capsules WHERE type = 'todo' AND status = 'active'")
        active_todos = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'by_type': by_type,
                'by_status': by_status,
                'active_todos': active_todos
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/<format>', methods=['GET'])
def export_capsules(format):
    """导出胶囊数据"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取查询参数
        capsule_type = request.args.get('type')
        search = request.args.get('search')
        
        # 构建查询
        query = 'SELECT * FROM capsules WHERE 1=1'
        params = []
        
        if capsule_type:
            query += ' AND type = ?'
            params.append(capsule_type)
        
        if search:
            query += ' AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        capsules = [dict(row) for row in rows]
        
        if format == 'json':
            return Response(
                json.dumps(capsules, ensure_ascii=False, indent=2),
                mimetype='application/json',
                headers={'Content-Disposition': 'attachment; filename=capsules.json'}
            )
        
        elif format == 'csv':
            output = io.StringIO()
            if capsules:
                writer = csv.DictWriter(output, fieldnames=capsules[0].keys())
                writer.writeheader()
                writer.writerows(capsules)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=capsules.csv'}
            )
        
        elif format == 'markdown':
            md = "# Echo Seed Capsules\n\n"
            for c in capsules:
                md += f"## {c['title'] or 'Untitled'}\n\n"
                md += f"**类型:** {c['type']}  \n"
                md += f"**创建时间:** {c['created_at']}  \n"
                if c['tags']:
                    md += f"**标签:** {c['tags']}  \n"
                md += f"\n{c['content'] or ''}\n\n"
                if c['url']:
                    md += f"🔗 {c['url']}\n\n"
                md += "---\n\n"
            return Response(
                md,
                mimetype='text/markdown',
                headers={'Content-Disposition': 'attachment; filename=capsules.md'}
            )
        
        else:
            return jsonify({'success': False, 'error': 'Unsupported format'}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/stats', methods=['GET'])
def export_stats():
    """导出统计信息"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM capsules')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT type, COUNT(*) FROM capsules GROUP BY type')
        by_type = dict(cursor.fetchall())
        
        cursor.execute('SELECT status, COUNT(*) FROM capsules GROUP BY status')
        by_status = dict(cursor.fetchall())
        
        cursor.execute("SELECT COUNT(*) FROM capsules WHERE type = 'todo' AND status = 'active'")
        active_todos = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'by_type': by_type,
                'by_status': by_status,
                'active_todos': active_todos
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # 确保数据库目录存在
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 初始化数据库
    init_db()
    
    print("🚀 Echo Seed Web 端启动中...")
    print(f"📂 项目根目录：{ROOT_DIR}")
    print(f"📊 数据库路径：{DB_PATH}")
    print("📱 访问地址：http://localhost:5000")
    print("🌐 局域网访问：http://0.0.0.0:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

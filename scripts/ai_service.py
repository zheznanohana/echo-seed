#!/usr/bin/env python3
"""
Echo Seed AI 分析服务模块

提供 AI 点子扩张、链接分析、智能关联等功能
"""

import requests
import json
from datetime import datetime
from pathlib import Path
import sqlite3

# ==================== 配置区 ====================

# 小小爪 API 配置
XIAOXIAOZHAO_CONFIG = {
    "base_url": "https://api.minimaxi.com/anthropic/v1",
    "api_key": "sk-cp-i3RGI_SA2M0OeNKhDKMs_sYuz9CM3ukFc1MmH7Ci8SRHgV7tJF0qARzCe6nXHJa1vl5zIw8C2TsP-w_vjPl--3N7KeUHL7m64Xwso2R-wVYAplB8DoKoEw8",
    "model": "MiniMax-M2.5"
}

# 导入数据库助手（与 Web 端统一）
import sys
sys.path.insert(0, str(Path(__file__).parent))
from db_helper import get_db_connection, execute_query, DB_PATH

# ==================== 工具函数 ====================

def get_db():
    """获取数据库连接（使用 db_helper）"""
    return get_db_connection()

def call_xiaoxiaozhao(prompt: str, system_prompt: str = None, timeout: int = 90) -> dict:
    """
    调用小小爪 API
    
    Args:
        prompt: 用户输入
        system_prompt: 系统提示
        timeout: 超时时间（秒）
    
    Returns:
        dict: API 响应（包含 text 和 metadata）
    """
    headers = {
        "Authorization": f"Bearer {XIAOXIAOZHAO_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }
    
    messages = [{"role": "user", "content": prompt}]
    if system_prompt:
        messages.insert(0, {"role": "system", "content": system_prompt})
    
    payload = {
        "model": XIAOXIAOZHAO_CONFIG["model"],
        "messages": messages,
        "max_tokens": 4000
    }
    
    try:
        response = requests.post(
            f"{XIAOXIAOZHAO_CONFIG['base_url']}/messages",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        
        # 解析响应
        content = result.get("content", [])
        text = ""
        for item in content:
            if item.get("type") == "text":
                text = item.get("text", "")
                break
        
        return {
            "success": True,
            "text": text,
            "tokens_used": result.get("usage", {}).get("output_tokens", 0),
            "raw_response": result
        }
        
    except requests.exceptions.Timeout:
        return {"success": False, "error": "API 超时", "text": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "text": ""}

def fetch_url_content(url: str, timeout: int = 30) -> dict:
    """
    提取网页内容
    
    Args:
        url: 网页 URL
        timeout: 超时时间
    
    Returns:
        dict: 网页内容（title, content, summary）
    """
    try:
        # 使用 web_fetch 工具（模拟）
        # 实际部署时可用：from openclaw import web_fetch
        # 不配置代理（避免影响 Tailscale 连接）
        response = requests.get(url, timeout=timeout, verify=False)
        response.raise_for_status()
        
        # 简单提取（实际应用中可用 BeautifulSoup 或 web_fetch）
        html = response.text
        title = ""
        if "<title>" in html:
            title = html.split("<title>")[1].split("</title>")[0].strip()
        
        # 移除 HTML 标签
        import re
        content = re.sub(r'<[^>]+>', '', html)
        content = content[:5000]  # 限制长度
        
        return {
            "success": True,
            "title": title,
            "content": content[:3000],
            "url": url
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== AI 分析服务 ====================

# System Prompts
EXPANSION_SYSTEM_PROMPT = """你是 Echo Seed 的 AI 创意助手，负责帮用户扩展想法。

请将用户的简单想法扩展成完整方案，包括：
1. 技术方案（使用什么技术栈）
2. 核心功能（主要功能列表）
3. 工作量评估（预计开发时间）
4. 风险评估（可能的风险和挑战）
5. 行动建议（下一步可以做什么）

输出格式（JSON）：
{
    "技术方案": ["技术 1", "技术 2"],
    "核心功能": ["功能 1", "功能 2"],
    "工作量": "预计时间",
    "风险": ["风险 1", "风险 2"],
    "行动建议": ["建议 1", "建议 2"]
}

语气：友好、专业、有建设性"""

LINK_SYSTEM_PROMPT = """你是 Echo Seed 的 AI 分析助手，负责分析网页内容。

请总结网页内容，提取关键词，并给出标签建议。

输出格式（JSON）：
{
    "title": "网页标题",
    "summary": "内容摘要（200 字以内）",
    "keywords": ["关键词 1", "关键词 2"],
    "suggested_tags": ["标签 1", "标签 2"]
}"""

# 各类型胶囊的 AI 分析 Prompt
CAPSULE_AI_PROMPTS = {
    'idea': {
        'system': EXPANSION_SYSTEM_PROMPT,
        'user': '请扩展以下想法，提供技术方案、功能列表、工作量评估、风险和建议：\n{content}'
    },
    'link': {
        'system': LINK_SYSTEM_PROMPT,
        'user': '请分析以下链接内容：\nURL: {url}\n标题：{title}\n内容：{content}'
    },
    'todo': {
        'system': """你是 Echo Seed 的时间管理助手。请帮用户分析待办事项，提供：
1. 步骤分解（如何拆解成可执行的小步骤）
2. 准备事项（需要提前准备什么）
3. 时间建议（预计耗时、最佳执行时间）
4. 可能的障碍及应对方案

输出格式（JSON）：
{
    "步骤分解": ["步骤 1", "步骤 2"],
    "准备事项": ["事项 1", "事项 2"],
    "时间建议": "建议内容",
    "可能障碍": ["障碍 1", "障碍 2"]
}""",
        'user': '请分析以下待办事项：\n{content}'
    },
    'note': {
        'system': """你是 Echo Seed 的知识整理助手。请帮用户整理笔记，提供：
1. 核心要点（提炼关键信息）
2. 补充细节（可能遗漏的重要信息）
3. 跟进建议（后续可以做什么）
4. 相关资源（推荐的学习资料或工具）

输出格式（JSON）：
{
    "核心要点": ["要点 1", "要点 2"],
    "补充细节": ["细节 1", "细节 2"],
    "跟进建议": ["建议 1", "建议 2"],
    "相关资源": ["资源 1", "资源 2"]
}""",
        'user': '请整理以下笔记：\n{content}'
    },
    'diary': {
        'system': """你是 Echo Seed 的情感陪伴助手。请回应用户的日记，提供：
1. 情感共鸣（理解并回应用户的感受）
2. 温暖回应（给予鼓励和支持）
3. 推荐资源（相关的书籍、音乐、活动等）
4. 反思问题（帮助用户更深入思考）

输出格式（JSON）：
{
    "情感共鸣": "回应内容",
    "温暖回应": "鼓励内容",
    "推荐资源": ["资源 1", "资源 2"],
    "反思问题": ["问题 1", "问题 2"]
}""",
        'user': '请回应以下日记：\n{content}'
    },
    'thought': {
        'system': """你是 Echo Seed 的思想分析助手。请帮用户深度分析思考，提供：
1. 多角度见解（从不同视角分析问题）
2. 思想资源（相关的理论、概念、名言）
3. 逻辑梳理（整理思路，指出可能的逻辑漏洞）
4. 延伸思考（可以进一步探索的方向）

输出格式（JSON）：
{
    "多角度见解": ["视角 1", "视角 2"],
    "思想资源": ["资源 1", "资源 2"],
    "逻辑梳理": "梳理内容",
    "延伸思考": ["方向 1", "方向 2"]
}""",
        'user': '请分析以下思考：\n{content}'
    },
    'collection': {
        'system': """你是 Echo Seed 的收藏分析助手。请帮用户分析收藏内容，提供：
1. 理解价值（为什么值得收藏）
2. 归类建议（可以归入什么类别）
3. 背景信息（相关的背景知识）
4. 使用建议（如何应用或利用这个收藏）

输出格式（JSON）：
{
    "理解价值": "价值说明",
    "归类建议": ["类别 1", "类别 2"],
    "背景信息": "背景说明",
    "使用建议": ["建议 1", "建议 2"]
}""",
        'user': '请分析以下收藏：\n{content}'
    },
}

def analyze_expansion(capsule_id: str, content: str) -> dict:
    """
    AI 点子扩张
    
    Args:
        capsule_id: 种子 ID
        content: 种子内容
    
    Returns:
        dict: 分析结果
    """
    prompt = f"""请扩展以下想法：

{content}

请给出详细的技术方案、功能列表、工作量评估、风险和建议。"""
    
    result = call_xiaoxiaozhao(prompt, EXPANSION_SYSTEM_PROMPT)
    
    if result["success"]:
        # 保存分析记录
        save_analysis(capsule_id, "expansion", content, result["text"], result["tokens_used"])
        
        # 解析 JSON 结果
        try:
            import json
            # 尝试提取 JSON
            start = result["text"].find("{")
            end = result["text"].rfind("}") + 1
            if start >= 0 and end > start:
                expanded = json.loads(result["text"][start:end])
            else:
                expanded = {"raw": result["text"]}
        except:
            expanded = {"raw": result["text"]}
        
        # 查找关联种子
        relations = find_related_capsules(content, limit=3)
        
        # 建议标签
        tags = extract_tags(content)
        
        return {
            "success": True,
            "analysis_id": get_last_analysis_id(),
            "original": content,
            "expanded": expanded,
            "related_capsules": relations,
            "suggested_tags": tags
        }
    else:
        return {"success": False, "error": result["error"]}

def analyze_capsule(capsule_id: str, capsule_type: str, content: str, url: str = '') -> dict:
    """
    通用胶囊 AI 分析
    
    Args:
        capsule_id: 种子 ID
        capsule_type: 种子类型 (idea/link/todo/note/diary/thought/collection)
        content: 种子内容
        url: 链接（可选）
    
    Returns:
        dict: 分析结果
    """
    # 获取对应类型的 Prompt
    prompt_config = CAPSULE_AI_PROMPTS.get(capsule_type, CAPSULE_AI_PROMPTS['note'])
    system_prompt = prompt_config['system']
    user_prompt = prompt_config['user'].format(content=content, url=url, title='')
    
    result = call_xiaoxiaozhao(user_prompt, system_prompt)
    
    if result["success"]:
        # 保存分析记录
        save_analysis(capsule_id, capsule_type, content, result["text"], result["tokens_used"])
        
        # 解析 JSON 结果
        try:
            import json
            start = result["text"].find("{")
            end = result["text"].rfind("}") + 1
            if start >= 0 and end > start:
                analysis = json.loads(result["text"][start:end])
            else:
                analysis = {"raw": result["text"]}
        except:
            analysis = {"raw": result["text"]}
        
        # 查找关联种子
        relations = find_related_capsules(content, limit=3)
        
        # 建议标签
        tags = extract_tags(content)
        
        return {
            "success": True,
            "analysis_id": get_last_analysis_id(),
            "original": content,
            "analysis": analysis,
            "related_capsules": relations,
            "suggested_tags": tags
        }
    else:
        return {"success": False, "error": result["error"]}

def analyze_link(capsule_id: str, url: str) -> dict:
    """
    AI 链接分析
    
    Args:
        capsule_id: 种子 ID
        url: 网页 URL
    
    Returns:
        dict: 分析结果
    """
    # 提取网页内容
    web_content = fetch_url_content(url)
    
    if not web_content.get("success"):
        return {"success": False, "error": f"无法提取网页：{web_content.get('error')}"}
    
    # AI 分析
    prompt = f"""请分析以下网页内容：

标题：{web_content.get('title', '无标题')}
URL: {url}
内容：{web_content.get('content', '')[:2000]}

请总结内容，提取关键词，并给出标签建议。"""
    
    result = call_xiaoxiaozhao(prompt, LINK_SYSTEM_PROMPT)
    
    if result["success"]:
        # 保存分析记录
        save_analysis(capsule_id, "link", url, result["text"], result["tokens_used"])
        
        # 解析 JSON 结果
        try:
            import json
            start = result["text"].find("{")
            end = result["text"].rfind("}") + 1
            if start >= 0 and end > start:
                analysis = json.loads(result["text"][start:end])
            else:
                analysis = {"summary": result["text"]}
        except:
            analysis = {"summary": result["text"]}
        
        # 建议标签
        tags = analysis.get("suggested_tags", extract_tags(web_content.get("content", "")))
        
        return {
            "success": True,
            "analysis_id": get_last_analysis_id(),
            "url": url,
            "title": web_content.get("title", ""),
            "analysis": analysis,
            "suggested_tags": tags
        }
    else:
        return {"success": False, "error": result["error"]}

def find_relations(capsule_id: str) -> dict:
    """
    智能关联 - 查找相关种子
    
    Args:
        capsule_id: 种子 ID
    
    Returns:
        dict: 关联种子列表
    """
    # 获取当前种子
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM capsules WHERE id = ?", (capsule_id,))
    current = cursor.fetchone()
    
    if not current:
        conn.close()
        return {"success": False, "error": "种子不存在"}
    
    # 获取所有其他种子
    cursor.execute("SELECT id, title, content, tags FROM capsules WHERE id != ?", (capsule_id,))
    all_capsules = cursor.fetchall()
    conn.close()
    
    # 简单关键词匹配（实际可用 embedding）
    current_text = (current["title"] or "") + " " + (current["content"] or "")
    current_keywords = set(current_text.lower().split())
    
    relations = []
    for capsule in all_capsules:
        capsule_text = (capsule["title"] or "") + " " + (capsule["content"] or "")
        capsule_keywords = set(capsule_text.lower().split())
        
        # 计算相似度
        intersection = current_keywords & capsule_keywords
        if len(intersection) >= 2:  # 至少 2 个共同关键词
            similarity = len(intersection) / max(len(current_keywords), len(capsule_keywords))
            if similarity > 0.3:  # 相似度阈值
                relations.append({
                    "id": capsule["id"],
                    "title": capsule["title"] or "无标题",
                    "similarity": round(similarity, 2)
                })
    
    # 按相似度排序
    relations.sort(key=lambda x: x["similarity"], reverse=True)
    
    # 保存到数据库
    save_relations(capsule_id, relations)
    
    return {
        "success": True,
        "relations": relations[:10]  # 返回前 10 个
    }

# ==================== 数据库操作 ====================

def save_analysis(capsule_id: str, analysis_type: str, input_content: str, 
                  output_content: str, tokens_used: int):
    """保存 AI 分析记录"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO ai_analyses (capsule_id, analysis_type, input_content, output_content, tokens_used)
        VALUES (?, ?, ?, ?, ?)
    """, (capsule_id, analysis_type, input_content, output_content, tokens_used))
    
    conn.commit()
    conn.close()

def get_last_analysis_id():
    """获取最后一条分析 ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM ai_analyses ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_relations(capsule_id: str, relations: list):
    """保存种子关联"""
    conn = get_db()
    cursor = conn.cursor()
    
    for rel in relations:
        cursor.execute("""
            INSERT OR REPLACE INTO capsule_relations 
            (source_capsule_id, target_capsule_id, relation_type, similarity_score)
            VALUES (?, ?, 'keyword', ?)
        """, (capsule_id, rel["id"], rel["similarity"]))
    
    conn.commit()
    conn.close()

def extract_tags(text: str, limit: int = 5) -> list:
    """简单标签提取（基于关键词频率）"""
    import re
    
    # 分词（简单按空格和标点）
    words = re.findall(r'\w+', text.lower())
    
    # 过滤停用词
    stop_words = {'the', 'a', 'an', 'is', 'are', 'in', 'on', 'at', 'to', 'for', 
                  '的', '了', '是', '在', '和', '与', '或', '一个', '这个', '那个'}
    words = [w for w in words if w not in stop_words and len(w) > 1]
    
    # 统计频率
    from collections import Counter
    freq = Counter(words)
    
    # 返回高频词
    return [word for word, count in freq.most_common(limit)]

def find_related_capsules(content: str, limit: int = 5) -> list:
    """查找相关种子（用于 AI 分析时推荐）"""
    # 临时种子 ID 用于查找关联
    temp_id = "temp_" + datetime.now().strftime("%Y%m%d%H%M%S")
    
    # 临时保存
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO capsules (id, type, content, created_at)
        VALUES (?, 'note', ?, ?)
    """, (temp_id, content[:500], datetime.now()))
    conn.commit()
    conn.close()
    
    # 查找关联
    result = find_relations(temp_id)
    
    # 删除临时种子
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM capsules WHERE id = ?", (temp_id,))
    conn.commit()
    conn.close()
    
    return result.get("relations", [])[:limit]

def get_analysis_history(capsule_id: str) -> list:
    """获取种子的分析历史"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, analysis_type, input_content, output_content, tokens_used, created_at
        FROM ai_analyses
        WHERE capsule_id = ?
        ORDER BY created_at DESC
    """, (capsule_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row["id"],
            "type": row["analysis_type"],
            "input": row["input_content"],
            "output": row["output_content"],
            "tokens": row["tokens_used"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]

# ==================== 测试入口 ====================

if __name__ == "__main__":
    print("🤖 Echo Seed AI 服务测试")
    print("=" * 50)
    
    # 测试 1: 点子扩张
    print("\n1️⃣ 测试点子扩张...")
    result = analyze_expansion("test_001", "做个 VR 版 B 站")
    if result["success"]:
        print(f"✅ 扩张成功：{result['expanded']}")
    else:
        print(f"❌ 失败：{result['error']}")
    
    # 测试 2: 链接分析
    print("\n2️⃣ 测试链接分析...")
    result = analyze_link("test_002", "https://www.example.com")
    if result["success"]:
        print(f"✅ 分析成功：{result['analysis']}")
    else:
        print(f"❌ 失败：{result['error']}")
    
    # 测试 3: 智能关联
    print("\n3️⃣ 测试智能关联...")
    result = find_relations("test_001")
    if result["success"]:
        print(f"✅ 找到 {len(result['relations'])} 个关联种子")
    else:
        print(f"❌ 失败：{result['error']}")
    
    print("\n" + "=" * 50)
    print("测试完成！")

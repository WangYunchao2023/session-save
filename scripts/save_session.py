#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Saver Script
Extracts session content from JSONL and saves as HTML + MD with formatting preserved.
"""
import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path

def parse_timestamp(ts):
    """Convert ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%a %Y-%m-%d %H:%M GMT+8')
    except:
        return ts

def escape_html(text):
    """Escape special HTML characters"""
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;'))

def convert_text_to_html(text):
    """Convert markdown-like text to HTML with proper table/code rendering"""
    lines = text.split('\n')
    result = []
    in_pre = False
    table_rows = []
    
    for line in lines:
        # Code blocks (must process before other formatting)
        if line.strip().startswith('```'):
            if not in_pre:
                lang = line.strip()[3:]
                result.append(f'<pre><code class="language-{lang}">' if lang else '<pre><code>')
                in_pre = True
            else:
                result.append('</code></pre>')
                in_pre = False
            continue
        
        if in_pre:
            result.append(escape_html(line))
            continue
        
        # Tables - collect rows
        if '|' in line and line.strip().startswith('|'):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            # Skip separator rows like |---|---|
            if parts and all(re.match(r'^[-:]+$', p.replace(' ', '').replace(':', '')) for p in parts if p):
                continue
            if parts:
                table_rows.append(parts)
            continue
        else:
            # Flush accumulated table
            if table_rows:
                result.append('<table>')
                result.append('<thead><tr>')
                for th in table_rows[0]:
                    result.append(f'<th>{th}</th>')
                result.append('</tr></thead>')
                result.append('<tbody>')
                for row in table_rows[1:]:
                    result.append('<tr>')
                    for td in row:
                        result.append(f'<td>{td}</td>')
                    result.append('</tr>')
                result.append('</tbody></table>')
                table_rows = []
        
        # Headers
        if line.startswith('####'):
            result.append(f'<h4>{line[4:].strip()}</h4>')
        elif line.startswith('###'):
            result.append(f'<h3>{line[3:].strip()}</h3>')
        elif line.startswith('##'):
            result.append(f'<h2>{line[2:].strip()}</h2>')
        elif line.startswith('#'):
            result.append(f'<h1>{line[1:].strip()}</h1>')
        elif line.strip() == '---':
            result.append('<hr>')
        elif line.startswith('>'):
            content = line[1:].strip()
            result.append(f'<blockquote>{content}</blockquote>')
        elif line.startswith('- ') or line.startswith('* '):
            result.append(f'<li>{line[2:].strip()}</li>')
        elif re.match(r'^\d+\.\s', line):
            match = re.match(r'^(\d+)\.\s(.*)', line)
            if match:
                result.append(f'<li>{match.group(2)}</li>')
        elif line.strip() == '':
            result.append('<br>')
        else:
            formatted = escape_html(line)
            formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted)
            formatted = re.sub(r'`(.*?)`', r'<code>\1</code>', formatted)
            formatted = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', formatted)
            result.append(f'<p>{formatted}</p>')
    
    # Flush remaining table
    if table_rows:
        result.append('<table>')
        result.append('<thead><tr>')
        for th in table_rows[0]:
            result.append(f'<th>{th}</th>')
        result.append('</tr></thead>')
        result.append('<tbody>')
        for row in table_rows[1:]:
            result.append('<tr>')
            for td in row:
                result.append(f'<td>{td}</td>')
            result.append('</tr>')
        result.append('</tbody></table>')
    
    return '\n'.join(result)

HTML_HEADER = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
.container {{ max-width: 1000px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }}
.header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; padding: 28px 36px; }}
.header h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 6px; }}
.header .meta {{ font-size: 13px; color: rgba(255,255,255,0.7); }}
.session-id {{ background: #fff9c4; color: #333; padding: 12px 36px; font-size: 13px; border-bottom: 1px solid #eee; }}
.conversation {{ padding: 0; }}
.message {{ padding: 24px 36px; border-bottom: 1px solid #eee; }}
.message:last-child {{ border-bottom: none; }}
.message.user {{ background: #f8f9fa; }}
.message.assistant {{ background: #fff; }}
.msg-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
.msg-role {{ font-size: 11px; font-weight: 600; padding: 4px 12px; border-radius: 12px; letter-spacing: 0.3px; }}
.role-user {{ background: #e3f2fd; color: #1565c0; }}
.role-assistant {{ background: #f3e5f5; color: #7b1fa2; }}
.msg-time {{ font-size: 12px; color: #999; margin-left: 8px; }}
.msg-content {{ font-size: 14px; line-height: 1.75; color: #333; }}
.msg-content h1 {{ font-size: 18px; margin: 20px 0 12px; color: #1a1a2e; border-bottom: 2px solid #eee; padding-bottom: 6px; }}
.msg-content h2 {{ font-size: 16px; margin: 18px 0 10px; color: #1a1a2e; }}
.msg-content h3 {{ font-size: 14px; margin: 14px 0 8px; color: #333; }}
.msg-content h4 {{ font-size: 13px; margin: 12px 0 6px; color: #333; }}
.msg-content pre {{ background: #f8f9fa; padding: 14px 18px; border-radius: 6px; overflow-x: auto; margin: 10px 0; font-size: 13px; border-left: 4px solid #1565c0; }}
.msg-content code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 13px; font-family: "SF Mono", Monaco, Consolas, monospace; }}
.msg-content pre code {{ background: transparent; padding: 0; }}
.msg-content table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13px; }}
.msg-content th, .msg-content td {{ border: 1px solid #ddd; padding: 10px 14px; text-align: left; }}
.msg-content th {{ background: #f5f5f5; font-weight: 600; color: #333; }}
.msg-content tr:nth-child(even) {{ background: #fafafa; }}
.msg-content p {{ margin-bottom: 10px; }}
.msg-content ul, .msg-content ol {{ margin: 8px 0 10px 24px; }}
.msg-content li {{ margin-bottom: 4px; }}
.msg-content blockquote {{ border-left: 4px solid #1565c0; background: #f0f7ff; padding: 10px 16px; margin: 12px 0; border-radius: 0 6px 6px 0; }}
.msg-content hr {{ border: none; border-top: 1px solid #eee; margin: 20px 0; }}
.msg-content strong {{ color: #1a1a2e; }}
.footer {{ background: #1a1a2e; color: rgba(255,255,255,0.6); padding: 16px 36px; font-size: 12px; text-align: center; }}
.footer span {{ margin: 0 8px; }}
.footer .highlight {{ background: #fff9c4; color: #333; padding: 2px 8px; border-radius: 4px; font-weight: 600; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{title}</h1>
    <div class="meta">{date_range} | {session_type}</div>
  </div>
  <div class="session-id">
    <strong>Session ID:</strong> <code>{session_id}</code> &nbsp;|&nbsp;
    <strong>开始时间:</strong> {start_time} &nbsp;|&nbsp;
    <strong>工作目录:</strong> {workspace}
  </div>
  <div class="conversation">
'''

HTML_FOOTER = '''
  </div>
  <div class="footer">
    <span class="highlight">会话结束</span>
    <span>Session ID: {session_id}</span>
    <span>结束时间: {end_time}</span>
  </div>
</div>
</body>
</html>
'''

def find_session_file(session_key):
    """Find the JSONL file for a given session key across ALL agent directories.
    
    Searches ~/.openclaw/agents/*/sessions/ for the session, including:
    - ~/.openclaw/agents/main/sessions/
    - ~/.openclaw/agents/{workspace-agent}/sessions/
    - ~/.openclaw/agents/*/sessions/
    """
    agents_base = Path.home() / '.openclaw' / 'agents'
    if not agents_base.exists():
        return None
    
    # Get all agent session directories
    agent_dirs = [d for d in agents_base.iterdir() if d.is_dir() and (d / 'sessions').is_dir()]
    
    # Extract search key parts
    key_part = session_key.split(':')[-1][:8] if ':' in session_key else session_key[:8]
    
    for agent_dir in agent_dirs:
        sessions_dir = agent_dir / 'sessions'
        sessions_json = sessions_dir / 'sessions.json'
        
        # Strategy 1: Check sessions.json for key mapping
        if sessions_json.exists():
            try:
                with open(sessions_json, 'r') as f:
                    data = json.load(f)
                
                # Normalize prefixes to try
                prefixes_to_try = [session_key]
                if not session_key.startswith('agent:'):
                    prefixes_to_try.append('agent:' + session_key)
                if session_key.startswith('agent:'):
                    parts = session_key.split(':')
                    if len(parts) >= 3:
                        prefixes_to_try.append(':'.join(parts[2:]))  # bare key
                
                for key_to_try in prefixes_to_try:
                    if key_to_try in data:
                        fp = data[key_to_try].get('sessionFile')
                        if fp:
                            p = Path(fp)
                            if p.exists():
                                return p
                
                # Search by sessionId match
                for k, v in data.items():
                    if isinstance(v, dict):
                        sid = v.get('sessionId', '')
                        if key_part in sid or sid in session_key:
                            fp = v.get('sessionFile')
                            if fp:
                                p = Path(fp)
                                if p.exists():
                                    return p
            except Exception as e:
                print(f"Error reading {sessions_json}: {e}", file=sys.stderr)
        
        # Strategy 2: Direct filename match (UUID partial match)
        for f in sessions_dir.glob('*.jsonl'):
            if key_part in f.name and not any(x in f.name for x in ['.deleted','.reset','.checkpoint']):
                return f
        
        # Strategy 3: Content search (first 5 lines of each file)
        for f in sessions_dir.glob('*.jsonl'):
            if any(x in f.name for x in ['.deleted','.reset','.checkpoint']):
                continue
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    for i, line in enumerate(file):
                        if i > 5:
                            break
                        if session_key in line:
                            return f
            except:
                continue
    
    return None

def extract_messages(session_file, session_key):
    """Extract messages from JSONL file"""
    messages = []
    
    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get('type') == 'message' and obj.get('message', {}).get('role') in ('user', 'assistant'):
                    role = obj['message']['role']
                    timestamp = obj.get('timestamp', '')
                    time_str = parse_timestamp(timestamp)
                    
                    text = ''
                    for content in obj.get('message', {}).get('content', []):
                        if content.get('type') == 'text':
                            t = content.get('text', '')
                            # Clean user messages
                            if role == 'user':
                                t = re.sub(r'Sender \(untrusted metadata\):.*?```json.*?```\n*', '', t, flags=re.DOTALL)
                                t = re.sub(r'^\[.*?\]\s*', '', t.strip())
                            text += t
                    
                    if text.strip():
                        messages.append((role, time_str, text.strip()))
            except Exception as e:
                continue
    
    return messages

def detect_session_type_and_target(messages):
    """Detect if session is about skill optimization and identify target skill"""
    # Keywords for skill optimization
    skill_opt_keywords = ['优化', 'skill优化', 'auto-optimize', 'skill-creator', '改进', '改善', '提升']
    
    # Known skill names to look for
    known_skills = [
        'session-save', 'session_save', 'session save',
        'auto-optimize-skills', 'auto_optimize', 'auto optimize',
        'feishu-bitable', 'feishu-calendar', 'feishu-im-read',
        'document-processor', 'guidance-web-access', 'pharma-report-analyzer',
        'ocr', 'weather', 'github', 'coding-agent'
    ]
    
    # Check first 5 messages
    check_msgs = messages[:5] if len(messages) >= 5 else messages
    
    combined_text = ' '.join([msg[2].lower() for msg in check_msgs])
    
    # Check if it's a skill optimization session
    is_optimization = False
    for kw in skill_opt_keywords:
        if kw.lower() in combined_text:
            is_optimization = True
            break
    
    if not is_optimization:
        return ('general', None)
    
    # Try to identify which skill is being optimized
    target_skill = None
    for skill in known_skills:
        skill_lower = skill.lower()
        # Look for patterns like "优化 session-save" or "session-save skill"
        if skill_lower in combined_text:
            # Normalize skill name (replace _ to -)
            target_skill = skill.replace('_', '-')
            break
    
    return ('skill_optimization', target_skill)

def get_time_filename(msg):
    """Extract time for filename: YYYY-MM-DD-HHMM"""
    # Format: "Thu 2026-03-26 13:36 GMT+8"
    parts = msg[1].split(' ')
    if len(parts) >= 3:
        # date_part = "2026-03-26", time_part = "13:36"
        date_part = parts[1]
        time_part = parts[2][:5]  # "13:36"
        return f"{date_part}-{time_part}"
    return "unknown"

def save_session(session_key, output_dir=None):
    """Main function to save session"""
    # Find session file
    session_file = find_session_file(session_key)
    if not session_file:
        print(f"Session file not found for key: {session_key}")
        return False
    
    # Extract messages
    messages = extract_messages(session_file, session_key)
    if not messages:
        print("No messages found in session")
        return False
    
    # Detect session type and target skill
    session_type, target_skill = detect_session_type_and_target(messages)
    
    # Get session info
    first_msg = messages[0]
    last_msg = messages[-1]
    start_time = get_time_filename(first_msg)
    end_time = get_time_filename(last_msg)
    date_range = f"{first_msg[1].split(' ')[1]} - {last_msg[1].split(' ')[1]}"
    
    # Determine output directory and filename based on session type
    if output_dir is None:
        if session_type == 'skill_optimization' and target_skill:
            # Save to target skill's folder
            workspace_skills = Path.home() / '.openclaw' / 'workspace' / 'skills'
            skill_dir = workspace_skills / target_skill
            if not skill_dir.exists():
                # Fallback to session-save folder if target skill not found
                skill_dir = Path(__file__).parent.parent
            subdir = skill_dir / '优化过程对话记录'
            subdir.mkdir(parents=True, exist_ok=True)
            output_dir = subdir
            base_name = f"优化过程对话记录-{start_time}-{end_time}"
        else:
            # Save to desktop
            output_dir = Path.home() / 'Desktop'
            base_name = f"session-{start_time}-{end_time}"
    else:
        output_dir = Path(output_dir)
        base_name = f"session-{start_time}-{end_time}"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate HTML
    session_type_display = 'Skill优化会话' if session_type == 'skill_optimization' else '常规会话'
    html = HTML_HEADER.format(
        title='会话记录',
        date_range=date_range,
        session_id=session_key,
        session_type=session_type_display,
        start_time=start_time,
        workspace='/home/wangyc/.openclaw/workspace'
    )
    
    for role, time_str, text in messages:
        role_class = 'role-user' if role == 'user' else 'role-assistant'
        role_text = '用户' if role == 'user' else 'Cortana 💙'
        html_content = convert_text_to_html(text)
        html += f'\n  <div class="message {role}">\n    <div class="msg-header"><span class="msg-role {role_class}">{role_text}</span><span class="msg-time">{time_str}</span></div>\n    <div class="msg-content">{html_content}</div>\n  </div>'
    
    html += HTML_FOOTER.format(
        session_id=session_key,
        end_time=end_time
    )
    
    # Generate Markdown
    md_header = f'''# 会话记录

**Session ID:** `{session_key}`  
**工作目录:** `/home/wangyc/.openclaw/workspace`  
**日期:** {date_range}

---

'''
    
    md = md_header
    for role, time_str, text in messages:
        role_text = '**用户**' if role == 'user' else '**Cortana 💙**'
        md += f'\n## {role_text} - {time_str}\n\n{text}\n\n---\n'
    
    md += f'\n---\n\n<span style="background-color: yellow; color: black;">**会话结束**</span> | **Session ID:** {session_key} | **结束时间:** {end_time}\n'
    
    # Save files
    html_path = output_dir / f"{base_name}.html"
    md_path = output_dir / f"{base_name}.md"
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    print(f"Saved {len(messages)} messages")
    if session_type == 'skill_optimization' and target_skill:
        print(f"Type: Skill优化会话 - 目标: {target_skill}")
    else:
        print(f"Type: 常规会话")
    print(f"HTML: {html_path} ({len(html)} bytes)")
    print(f"MD: {md_path} ({len(md)} bytes)")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python save_session.py <session_key> [output_dir]")
        sys.exit(1)
    
    session_key = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = save_session(session_key, output_dir)
    sys.exit(0 if success else 1)

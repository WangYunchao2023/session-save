#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Saver Script v1.2.1
Extracts session content from JSONL and saves as HTML + MD with formatting preserved.
"""
import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────
# Timestamp / HTML utilities
# ─────────────────────────────────────────────

def parse_timestamp(ts):
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%a %Y-%m-%d %H:%M GMT+8')
    except:
        return ts

def escape_html(text):
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;'))

def convert_text_to_html(text):
    lines = text.split('\n')
    result, in_pre, table_rows = [], False, []
    for line in lines:
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
            result.append(escape_html(line)); continue
        if '|' in line and line.strip().startswith('|'):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if parts and all(re.match(r'^[-:]+$', p.replace(' ', '').replace(':', '')) for p in parts if p):
                continue
            if parts: table_rows.append(parts); continue
        else:
            if table_rows:
                result.append('<table><thead><tr>')
                for th in table_rows[0]: result.append(f'<th>{th}</th>')
                result.append('</tr></thead><tbody>')
                for row in table_rows[1:]:
                    result.append('<tr>')
                    for td in row: result.append(f'<td>{td}</td>')
                    result.append('</tr>')
                result.append('</tbody></table>')
                table_rows = []
        if line.startswith('####'): result.append(f'<h4>{line[4:].strip()}</h4>')
        elif line.startswith('###'): result.append(f'<h3>{line[3:].strip()}</h3>')
        elif line.startswith('##'): result.append(f'<h2>{line[2:].strip()}</h2>')
        elif line.startswith('#'): result.append(f'<h1>{line[1:].strip()}</h1>')
        elif line.strip() == '---': result.append('<hr>')
        elif line.startswith('>'): result.append(f'<blockquote>{line[1:].strip()}</blockquote>')
        elif line.startswith('- ') or line.startswith('* '): result.append(f'<li>{line[2:].strip()}</li>')
        elif re.match(r'^\d+\.\s', line):
            m = re.match(r'^(\d+)\.\s(.*)', line)
            if m: result.append(f'<li>{m.group(2)}</li>')
        elif line.strip() == '': result.append('<br>')
        else:
            fmt = escape_html(line)
            fmt = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', fmt)
            fmt = re.sub(r'`(.*?)`', r'<code>\1</code>', fmt)
            fmt = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', fmt)
            result.append(f'<p>{fmt}</p>')
    if table_rows:
        result.append('<table><thead><tr>')
        for th in table_rows[0]: result.append(f'<th>{th}</th>')
        result.append('</tr></thead><tbody>')
        for row in table_rows[1:]:
            result.append('<tr>')
            for td in row: result.append(f'<td>{td}</td>')
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

# ─────────────────────────────────────────────
# Session file discovery (scans ALL agent dirs)
# ─────────────────────────────────────────────

def find_session_file(session_key):
    """Find JSONL across ~/.openclaw/agents/*/sessions/."""
    agents_base = Path.home() / '.openclaw' / 'agents'
    if not agents_base.exists():
        return None
    agent_dirs = [d for d in agents_base.iterdir() if d.is_dir() and (d / 'sessions').is_dir()]
    key_part = session_key.split(':')[-1][:8] if ':' in session_key else session_key[:8]

    for agent_dir in agent_dirs:
        sessions_dir = agent_dir / 'sessions'
        sessions_json = sessions_dir / 'sessions.json'

        # Strategy 1: sessions.json
        if sessions_json.exists():
            try:
                with open(sessions_json, 'r') as f:
                    data = json.load(f)
                prefixes = [session_key]
                if not session_key.startswith('agent:'):
                    prefixes.append('agent:' + session_key)
                if session_key.startswith('agent:'):
                    parts = session_key.split(':')
                    if len(parts) >= 3:
                        prefixes.append(':'.join(parts[2:]))
                for k in prefixes:
                    if k in data:
                        fp = data[k].get('sessionFile')
                        if fp and Path(fp).exists():
                            return Path(fp)
                for k, v in data.items():
                    if isinstance(v, dict):
                        sid = v.get('sessionId', '')
                        if key_part in sid or sid in session_key:
                            fp = v.get('sessionFile')
                            if fp and Path(fp).exists():
                                return Path(fp)
            except Exception as e:
                print(f"Error reading {sessions_json}: {e}", file=sys.stderr)

        # Strategy 2: filename match
        for f in sessions_dir.glob('*.jsonl'):
            if key_part in f.name and not any(x in f.name for x in ['.deleted', '.reset', '.checkpoint']):
                return f

        # Strategy 3: content search
        for f in sessions_dir.glob('*.jsonl'):
            if any(x in f.name for x in ['.deleted', '.reset', '.checkpoint']):
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
                    ts = obj.get('timestamp', '')
                    tstr = parse_timestamp(ts)
                    text = ''
                    for c in obj.get('message', {}).get('content', []):
                        if c.get('type') == 'text':
                            t = c.get('text', '')
                            if role == 'user':
                                t = re.sub(r'Sender \(untrusted metadata\):.*?```json.*?```\n*', '', t, flags=re.DOTALL)
                                t = re.sub(r'^\[.*?\]\s*', '', t.strip())
                            text += t
                    if text.strip():
                        messages.append((role, tstr, text.strip()))
            except:
                continue
    return messages

def detect_session_type_and_target(messages):
    opt_kws = ['优化', 'skill优化', 'auto-optimize', 'skill-creator', '改进', '改善', '提升']
    known = ['session-save', 'auto-optimize-skills', 'feishu-bitable', 'feishu-calendar',
             'feishu-im-read', 'document-processor', 'guidance-web-access',
             'pharma-report-analyzer', 'ocr', 'weather', 'github', 'coding-agent']
    check = ' '.join([m[2].lower() for m in messages[:5]])
    if not any(k.lower() in check for k in opt_kws):
        return ('general', None)
    for s in known:
        if s.lower() in check:
            return ('skill_optimization', s.replace('_', '-'))
    return ('skill_optimization', '其他')

def generate_auto_prefix(messages):
    """Extract short prefix from message content. Priority:
    1. First 5 user messages
    2. All messages if still nothing
    Returns a slug up to 20 chars.
    """
    def extract(texts):
        combined = ' '.join(texts)
        out = []
        out += re.findall(r'[\u4e00-\u9fff]{2,12}(?:注射液|片|胶囊|颗粒|丸|口服液|栓剂|膏)', combined)
        out += re.findall(r'[A-Z][-_]?\d{2,6}[-_]?\w*', combined)
        out += re.findall(r'[\u4e00-\u9fff]{3,10}(?:合规性|非临床|研究|报告|分析|评估|优化|方案|审查)', combined)
        out += re.findall(r'[\u4e00-\u9fff]{3,6}', combined)
        seen, cleaned = set(), []
        for c in out:
            c = re.sub(r'[`*\[\]()（）]', '', c.strip())
            if len(c) >= 2 and c not in seen:
                seen.add(c); cleaned.append(c)
        return cleaned

    user_msgs = [m[2] for m in messages if m[0] == 'user']
    cand = extract(user_msgs[:5])
    if not cand:
        cand = extract([m[2] for m in messages])
    if cand:
        prefix = ''.join(cand[:3])[:20]
        return prefix if prefix else '会话'
    return '会话'

def get_time_filename(msg):
    parts = msg[1].split(' ')
    if len(parts) >= 3:
        return f"{parts[1]}-{parts[2][:5]}"
    return 'unknown'

def resolve_output_path(base_name, output_dir):
    """Ensure unique path (add -1, -2 … if file already exists)."""
    out_dir = Path(output_dir) if output_dir else Path.home() / 'Documents' / '工作' / '1 AI实际应用导出'
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{base_name}.html"
    md_path = out_dir / f"{base_name}.md"
    n = 1
    while html_path.exists() or md_path.exists():
        html_path = out_dir / f"{base_name}-{n}.html"
        md_path = out_dir / f"{base_name}-{n}.md"
        n += 1
    return html_path, md_path, out_dir

def build_html(title, date_range, session_id, start_time, workspace, session_type, messages):
    html = HTML_HEADER.format(
        title=title, date_range=date_range, session_id=session_id,
        start_time=start_time, workspace=workspace, session_type=session_type)
    for role, tstr, text in messages:
        rc = 'role-user' if role == 'user' else 'role-assistant'
        rt = '用户' if role == 'user' else '助手'
        html += f'\n  <div class="message {role}">\n    <div class="msg-header"><span class="msg-role {rc}">{rt}</span><span class="msg-time">{tstr}</span></div>\n    <div class="msg-content">{convert_text_to_html(text)}</div>\n  </div>'
    html += f'\n  <div class="footer"><span class="highlight">会话结束</span> <span>Session ID: {session_id}</span> <span>结束时间: {start_time}</span></div>\n  </div></body></html>'
    return html

def build_md(title, session_id, workspace, date_range, messages):
    md = f'''# {title}

**Session ID:** `{session_id}`  
**工作目录:** `{workspace}`  
**日期:** {date_range}

---

'''
    for role, tstr, text in messages:
        rt = '**用户**' if role == 'user' else '**助手**'
        md += f'\n## {rt} - {tstr}\n\n{text}\n\n---\n'
    md += f'\n---\n\n<span style="background-color: yellow; color: black;">**会话结束**</span> | **Session ID:** {session_id}\n'
    return md

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def save_session(session_key, output_dir=None, custom_prefix=None):
    session_file = find_session_file(session_key)
    if not session_file:
        print(f"Session file not found for key: {session_key}")
        return False

    messages = extract_messages(session_file, session_key)
    if not messages:
        print("No messages found in session")
        return False

    session_type, target_skill = detect_session_type_and_target(messages)
    st = get_time_filename(messages[0])
    et = get_time_filename(messages[-1])
    date_range = f"{messages[0][1].split(' ')[1]} - {messages[-1][1].split(' ')[1]}"
    type_display = 'Skill优化会话' if session_type == 'skill_optimization' else '常规会话'

    # ── Filename and path ──────────────────────
    if output_dir is None:
        if session_type == 'skill_optimization' and target_skill:
            skill_dir = Path.home() / '.openclaw' / 'workspace' / 'skills' / target_skill
            if not skill_dir.exists():
                skill_dir = Path(__file__).parent.parent
            out_dir = skill_dir / '优化过程对话记录'
            out_dir.mkdir(parents=True, exist_ok=True)
            base_name = f"优化过程对话记录-{st}-{et}"
        else:
            out_dir = Path.home() / 'Documents' / '工作' / '1 AI实际应用导出'
            prefix = custom_prefix if custom_prefix else generate_auto_prefix(messages)
            base_name = f"{prefix}-session-{st}-{et}"
    else:
        out_dir = Path(output_dir)
        prefix = custom_prefix if custom_prefix else generate_auto_prefix(messages)
        base_name = f"{prefix}-session-{st}-{et}"

    html_path, md_path, _ = resolve_output_path(base_name, out_dir)

    # ── Build content ─────────────────────────
    title = base_name
    html = build_html(title, date_range, session_key, et, '/home/wangyc/.openclaw/workspace', type_display, messages)
    md = build_md(title, session_key, '/home/wangyc/.openclaw/workspace', date_range, messages)

    # ── Save both files ───────────────────────
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)

    # ── Report ───────────────────────────────
    print(f"Saved {len(messages)} messages")
    if session_type == 'skill_optimization':
        print(f"Type: Skill优化会话 | 目标: {target_skill}")
    else:
        prefix_used = custom_prefix if custom_prefix else generate_auto_prefix(messages)
        print(f"Type: 常规会话 | Prefix: {prefix_used}")
    print(f"HTML: {html_path} ({len(html):,} bytes)")
    print(f"MD:   {md_path} ({len(md):,} bytes)")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python save_session.py <session_key> [output_dir] [prefix]")
        print("  session_key : Session key, UUID, or 'current'")
        print("  output_dir  : Optional. Defaults to Desktop (general) or skill folder (optimization)")
        print("  prefix      : Optional. Short prefix for regular sessions (e.g. '参芪扶正_S152')")
        print("               If omitted, auto-extracted from message content.")
        print()
        print("Examples:")
        print("  python save_session.py agent:main:main")
        print("  python save_session.py 6cc94624-fcc1-4d52-b99d-9f61a0e88af0")
        print("  python save_session.py current ~/Documents/工作/1 AI实际应用导出 '参芪扶正_S152合规'")
        sys.exit(1)

    session_key = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    custom_prefix = sys.argv[3] if len(sys.argv) > 3 else None

    success = save_session(session_key, output_dir, custom_prefix)
    sys.exit(0 if success else 1)

---
name: session-save
version: "1.0.0"
description: |
  保存完整会话记录（保留表格和图示）。当用户要求保存会话、导出会话、保存对话记录到桌面时使用。

  关键：必须从 JSONL 文件提取原始内容以保留表格、ASCII 图等格式，不能依赖会话历史 API（会丢失格式）。

  路径规则：
  - Skill优化类 → 保存到 `~/.openclaw/workspace/skills/{被优化skill}/优化过程对话记录/`
  - 常规会话 → 保存到 `~/Desktop/`

  文件名格式：`类型-开始时间-结束时间.html/md`
---

# Session Save Skill

## 功能说明

自动判断会话类型，保存到正确位置：
- **Skill优化类**：保存到被优化 Skill 的文件夹下的 `优化过程对话记录/` 子目录
- **常规会话**：保存到桌面

## 判断逻辑

1. 扫描前5条消息内容
2. 检测「优化」「改进」「改善」「提升」等关键词
3. 识别目标 Skill 名称（如 session-save、auto-optimize-skills 等）

## 时间格式

- 开始时间：`YYYY-MM-DD-HHMM`
- 结束时间：`YYYY-MM-DD-HHMM`

---

## 工作流程

1. **判断会话类型和目标**
   - 检测优化关键词 + 识别目标 Skill

2. **找到会话文件**
   - 从 `sessions.json` 查找 session key → JSONL 映射
   - 直接读取 JSONL（不用 `sessions_history` API）

3. **生成文件**
   - `.html` - 带样式（表格、代码块正确渲染）
   - `.md` - 原始 Markdown 格式

---

## 关键教训

- **`sessions_history` API 会丢失格式**，必须读 JSONL
- **JSONL 每行一个完整 JSON 对象**，含原始文本（含表格、ASCII 图）
- **用户标签（`<final>`）和 sender metadata 应移除**

---

## 使用方式

```bash
python3 ~/.openclaw/workspace/skills/session-save/scripts/save_session.py <session_key>
```

---

## 已知 Skill 列表

session-save, auto-optimize-skills, feishu-bitable, feishu-calendar, feishu-im-read, document-processor, guidance-web-access, pharma-report-analyzer, ocr, weather, github, coding-agent 等。

---

## 版本历史

### 1.0.0
- 初始版本
- 支持自动判断会话类型（Skill优化/常规）
- 支持识别目标 Skill 并保存到对应文件夹
- 生成 HTML + Markdown 两种格式
- 保留原始表格、ASCII 图等格式

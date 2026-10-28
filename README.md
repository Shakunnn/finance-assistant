# 财务报销制度智能咨询助手 — 项目总览 README

> 依据：《概要设计说明书-2026-10-28修订版》（以下简称“概要设计”）第 4 章（数据库）、第 5 章（接口）为准。
> 本文件写于 2026-10-28，反映的是**从头重建的新项目**，不是旧项目。
> 本文件是 push 到仓库用的版本：所有路径都是仓库内的相对路径，不依赖任何个人电脑的绝对路径；所有命令都给出 Windows 和 macOS / Linux 两种写法，Windows 也能直接跑。
> 旧项目已存档为 `finance-assistant-old-20261028`，不再往上打补丁，旧库迁移、旧 seed、旧接口一律作废。

## 1. 项目是干什么的

面向企业员工的报销制度咨询助手，回答“某项费用能不能报、标准是多少、要经过谁审批、特殊情况怎么办”这类问题。

- **员工（employee）**：查制度、查标准、问答、看自己的会话和浏览历史。
- **管理员（admin）**：维护分类、文档、文件、标准、审批流程、特殊规则、FAQ、字典、用户，看问答日志和数据看板。
- **游客**：只能看首页分类卡片和公开封面缩略图，详情和问答必须登录。

核心原则，写代码和改数据时都不要违反：

- 查不到就说查不到，**不要编造**金额、条款、流程。
- 金额以结构化标准表为准，不要让模型从文本里猜数字。
- 文档正文是 RAG 的知识来源，标准、审批、特殊、FAQ 是结构化数据，**不向量化**。
- 问答先走 FAQ 文本匹配，再走结构化工具，再走向量检索，最后才是大模型；没有依据就拒答。

## 2. 当前进度（2026-10-28，写本文件时）

| 步骤 | 状态 | 说明 |
|---|---|---|
| 第 1 步：骨架 + `init_db()` | ✅ 已完成并验证 | 空库建表、二次建表幂等、`/api/health` 200 |
| 第 2 步：18 张表 schema | ✅ 已完成并验证 | 列、类型、非空、默认值、外键、索引、CHECK、部分唯一索引都验过，见第 5 节 |
| 第 3 步：seed 基础数据 | ✅ 已完成并验证 | 行数和字段都抽查过，见第 6 节 |
| 第 4 步：61 个接口 | ⏳ 未开始做，prompt 已给 | 按第 5 章分组做，见第 7 节；做完一项勾一项，不要说“全部完成” |
| 第 5 步：前端 Vue3 | ⏳ 未开始 | 按概要设计第 7 章页面结构搭，主线是登录、首页、详情、问答 |
| 向量化 Worker（BGE + Chroma） | ⏳ 未开始 | 文档保存时先登记 sync_jobs，Worker 本身缺口要明说，不要假装已向量化 |

> 注意：本 README 里写的接口是**概要设计里定的接口**，不是已经实现好的接口。实现进度以第 4 步的实际代码和测试为准。

## 3. 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 语言 | Python 3.11 | 项目只保证 3.10 / 3.11，优先 3.11；低于 3.10 不行，高于 3.11 不在保证范围内。Windows 用 python.org 的 3.11 安装包（安装时勾选 Add Python to PATH，不要用 Microsoft Store 的 Python）；macOS 用 `brew install python@3.11` 或 python.org 的 arm64 安装包，不要用无版本号的 `brew install python` |
| 后端 | FastAPI + Uvicorn | 接口一律 `/api` 前缀，UTF-8 JSON |
| 数据库 | SQLite（单文件） | `data/app.db`，`data/` 是 gitignore 的，不进仓库；`journal_mode=WAL` |
| 数据访问 | SQLAlchemy，只用 Engine + Session + `text()` 原生 SQL | **不要求 ORM 模型**，不要为了“规范”重写成 ORM |
| 前端 | Vue3（计划中） | 员工走移动端页面，管理员走 PC 后台 Dashboard，直接跳转，不设选择页 |
| 向量化 | 本地 BGE-small-zh-v1.5，384 维，固定版本 | **不用云端 Embedding API**；云端外部接口只有 DeepSeek（对话生成与摘要）和 Tavily（联网搜索）两个 |
| 向量库 | Chroma，`data/chroma` | 只存已发布、未删除、块版本等于 `active_vector_version` 的内容 |
| 认证 | JWT Bearer，含 sid | sid 对应 `auth_sessions.id`（TEXT，UUID），服务端校验未过期、未撤销、账号仍启用，有效期 120 分钟 |
| 密码 | bcrypt，`bcrypt>=4.0,<4.1` | 只存加盐哈希，永不存明文；这个 pin 是因为 passlib 1.7.4 + bcrypt 5.0.0 不兼容，**不要去掉、不要放宽**，换鉴权要先经用户决定 |
| 切块 | 300–500 字，重叠约 50 字 | 不是旧的 800 / 150 |
| 问答 | 真 SSE 流式 | 首字 ≤3 秒；不是 stream 占位 |

### 本地开发环境变量（`.env.example` 只放占位符）

```
APP_ENV=development
APP_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=5173
DATABASE_PATH=data/app.db
CHROMA_PATH=data/chroma
UPLOAD_DIR=data/uploads
JWT_SECRET=<占位符，本地自己填>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=120
DEEPSEEK_API_KEY=<占位符>
DEEPSEEK_MODEL=deepseek-chat
WEB_SEARCH_ENABLED=true
RAG_SCORE_THRESHOLD=0.35   # 本地各机补，不进 git
```

`.env` 本身不进仓库。`ADMIN_PASSWORD` 只在跑 seed 时从环境变量读，不要写进代码仓库。

## 4. 目录结构（仓库根目录，Windows / macOS 通用）

```
finance-assistant/       # git clone 仓库后得到的项目根目录，以下路径一律是相对路径
  .venv/                 # Python 3.11 虚拟环境，激活后统一用 python，不要直接写 .venv/bin/python 或 .venv\Scripts\python.exe
  app/
    main.py              # FastAPI 入口，含 /api/health
    database.py          # init_db()、SessionLocal、EXPECTED_TABLES
    seed.py              # seed_db()，只在空库上跑一次
  data/                  # gitignore：app.db、chroma、uploads
  # 注意：verify_step3.py 等验证脚本只在本地跑，不要 push 进仓库
```

> 旧项目是 `backend/` 结构，新项目是 `app/` 结构，不要把两个结构混着抄。以后以新项目实际目录为准，本节如有出入以代码为准。

### 本地运行（Windows / macOS 通用）

```bash
# 1. 克隆仓库（私有仓库，需要有权限的账号）
git clone https://github.com/Shakunnn/finance-assistant.git
cd finance-assistant

# 2. 建虚拟环境（任选一种，Python 必须是 3.11）
# Windows（PowerShell / CMD）：
python -m venv .venv
# macOS / Linux：
python3.11 -m venv .venv

# 3. 激活虚拟环境，激活后统一用 python，不要再写完整路径
# Windows（PowerShell）：.venv\Scripts\Activate.ps1
# Windows（CMD）：.venv\Scripts\activate.bat
# macOS / Linux：source .venv/bin/activate
python --version   # 应该显示 Python 3.11.x

# 4. 删库重建（data/ 是 gitignore 的，不进仓库）
# Windows：del data\app.db data\app.db-shm data\app.db-wal
# macOS / Linux：rm -f data/app.db data/app.db-shm data/app.db-wal
python -c "from app.database import init_db; print(init_db())"
python -c "from app.seed import seed_db; print(seed_db())"
```

### Windows 环境注意

- 装 Python 时一定要勾选 Add Python to PATH，否则 `python` 命令找不到；如果打出的是 Microsoft Store 的提示，说明 PATH 没配好，重装时勾选，或者用 `py -3.11 --version` 试一下。
- 命令里的路径分隔符在 Windows 上是 `\`，在代码和配置文件里一律用 `/`，不要把 Windows 的绝对路径（例如 `C:\Users\...`）写进代码、配置或文档。
- BGE 向量化在没有 GPU 的 Windows 机器上走 CPU 也能跑，只是慢一点，不要因为没 GPU 就改模型或改代码；有 RTX 等 GPU 的机器按项目里的设备选择逻辑走（cuda → mps → cpu），不要硬编码设备。
- 文件一律 UTF-8，换行和编码问题先检查 Git 设置，不要把个人编辑器的绝对路径、个人用户名写进提交。

## 5. 表参数：18 张表

约定（全部 18 张表适用）：

- 时间：库内统一 Asia/Shanghai 本地时间，格式 `YYYY-MM-DD HH:MM:SS`。实现上是 `strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')`，不是 `datetime('now','localtime')`，这样不管服务器时区怎么设，结果都是上海时间。中国无夏令时，+8 没有时令问题。
- 金额：库内一律整数分，字段名后缀 `_cents`；对外是元（两位小数字符串），转换在服务层做。
- 外键删除规则：一律 `ON DELETE RESTRICT`，被引用时不能物理删除；账号用 `is_active`、文档和会话用 `is_deleted` 做逻辑控制。
- 0/1 字段：一律 `CHECK (x IN (0,1))`。
- JSON 字段：一律 `json_valid()` + 顶层类型检查（数组或对象按字段定）。
- 字符串长度、字典类型、管理员身份、同会话归属、有效期不重叠等，按概要设计 §4.4 分工：主键、外键、非空、唯一、数值范围、JSON 合法性由数据库约束落实，其余由服务层在写入前校验，数据库里再加一层长度 CHECK 不冲突，但服务层必须先给出友好提示，不能让数据库 CHECK 直接报 500。

### 5.1 表清单

| # | 表 | 说明 | 关键约束 |
|---|---|---|---|
| 1 | departments | 部门选项 | name 唯一（2–50 字） |
| 2 | dict_items | 业务维度字典 | UNIQUE(dict_type, code)；dict_type 只允许 city / grade / expense_type / scene |
| 3 | users | 用户账号 | username 全局唯一、比较忽略大小写；role 只允许 employee / admin |
| 4 | auth_sessions | 登录会话 | id 是 TEXT（JWT 里的 sid，UUID），不是自增整数；expires_at 默认签发后 120 分钟 |
| 5 | categories | 文档分类 | name 唯一（2–20 字） |
| 6 | files | 文件元信息 | storage_key 唯一；kind 只允许 attachment / cover |
| 7 | documents | 制度文档 | publish_status 与 sync_status 分离；version ≥1 |
| 8 | document_chunks | 知识块映射 | UNIQUE(document_id, document_version, chunk_no)；vector_id 唯一 |
| 9 | sync_jobs | 同步任务 | UNIQUE(document_id, target_version, action)；attempts 只能 0–3 |
| 10 | reimbursement_standards | 差旅标准 | UNIQUE(city_code, grade_code, expense_type_code, effective_from)；currency 只允许 CNY |
| 11 | approval_flows | 审批流程节点 | UNIQUE(flow_code, effective_from, step_no)；组内 step_no 从 1 连续 |
| 12 | special_expense_rules | 特殊费用规则 | scene_code 不设唯一，同场景多条件可并存 |
| 13 | faq | 常见问题 | normalized_question 唯一；question 本身不再唯一 |
| 14 | conversations | 聊天会话 | summary_until_message_id 引用 messages（见 5.3 循环外键说明） |
| 15 | messages | 会话消息 | UNIQUE(conversation_id, request_id, role)；role 只允许 user / assistant |
| 16 | qa_logs | 问答日志 | assistant_message_id 唯一；没有 updated_at |
| 17 | browse_history | 浏览历史 | UNIQUE(user_id, document_id)；同一员工同一文档只有一条 |
| 18 | audit_logs | 审计日志 | 只追加；后台不提供修改 / 删除入口；detail_json 先脱敏 |

没有的表 / 字段，不要自己加：旧项目的 `user_doc_actions`（收藏）、`categories.slug / description`、`document_chunks.token_count`、`qa_log.feedback_*`、`answer_chars`，概要设计里都没有，新 schema 里也没有。

### 5.2 逐表字段（已验证的实际 schema）

> 类型、非空、默认值均来自 2026-10-28 的 PRAGMA 验证输出。`id` 为 INTEGER 主键时 PRAGMA 的 notnull 显示为 0 是 SQLite 的 rowid 特性，不代表可以插 NULL。

**departments（6 列）**：id INTEGER PK，name TEXT NOT NULL UNIQUE，sort_order INTEGER NOT NULL DEFAULT 0，is_active INTEGER NOT NULL DEFAULT 1，created_at / updated_at TEXT NOT NULL DEFAULT 上海时间。

**dict_items（8 列）**：id，dict_type TEXT NOT NULL（city / grade / expense_type / scene），code TEXT NOT NULL（1–40 字），label TEXT NOT NULL（1–50 字），sort_order DEFAULT 0，is_active DEFAULT 1，created_at / updated_at。

**users（12 列）**：id，username TEXT NOT NULL COLLATE NOCASE UNIQUE（4–20 字），password_hash TEXT NOT NULL，display_name TEXT NOT NULL（2–20 字），department_id INTEGER NULL（员工必填、管理员可空，CHECK：`role='admin' OR department_id IS NOT NULL`），role TEXT NOT NULL DEFAULT 'employee'（employee / admin），is_active DEFAULT 1，failed_login_count DEFAULT 0，locked_until NULL，must_change_password DEFAULT 0，created_at / updated_at。外键：department_id → departments(id) RESTRICT。

**auth_sessions（6 列）**：id TEXT NOT NULL PK（UUID sid），user_id INTEGER NOT NULL，expires_at TEXT NOT NULL DEFAULT 上海时间 +120 分钟，revoked_at NULL，created_at NOT NULL DEFAULT 上海时间，last_seen_at NOT NULL DEFAULT 上海时间。外键：user_id → users(id) RESTRICT。另有 CHECK：`expires_at > created_at`。

**categories（5 列）**：id，name TEXT NOT NULL UNIQUE（2–20 字），sort_order DEFAULT 0，created_at / updated_at。

**files（9 列，无 updated_at）**：id，kind TEXT NOT NULL（attachment / cover），original_name TEXT NOT NULL（1–255 字），storage_key TEXT NOT NULL UNIQUE，mime_type TEXT NOT NULL，size_bytes INTEGER NOT NULL，sha256 TEXT NOT NULL（64 位），uploaded_by INTEGER NOT NULL，created_at。外键：uploaded_by → users(id) RESTRICT。附件 ≤20MiB、封面 ≤5MiB 由服务层按 kind 校验。

**documents（16 列）**：id，category_id NOT NULL，title TEXT NOT NULL（1–100 字），body_markdown TEXT NOT NULL（非空），attachment_file_id NULL，cover_file_id NULL，publish_status TEXT NOT NULL DEFAULT 'draft'（draft / published / unpublished），version INTEGER NOT NULL DEFAULT 1（≥1），active_vector_version NULL（≤ version），sync_status TEXT NOT NULL DEFAULT 'pending'（pending / syncing / synced / failed），sync_error NULL，is_deleted DEFAULT 0，created_by / updated_by NOT NULL，created_at / updated_at。外键全部 RESTRICT。

**document_chunks（10 列，无 updated_at）**：id，document_id NOT NULL，document_version NOT NULL（≥1），chunk_no NOT NULL（≥0），vector_id TEXT NOT NULL UNIQUE，section_path TEXT NOT NULL DEFAULT ''（识别不出条款时保持空串，不能编造），content TEXT NOT NULL（非空），content_hash TEXT NOT NULL（64 位），embedding_model TEXT NOT NULL，created_at。

**sync_jobs（13 列）**：id，document_id NOT NULL，target_version NOT NULL（≥1），action TEXT NOT NULL（rebuild / remove），status TEXT NOT NULL DEFAULT 'pending'（pending / running / succeeded / failed / superseded），attempts DEFAULT 0（0–3），next_retry_at NULL，lease_until NULL，last_error NULL，started_at NULL，finished_at NULL，created_at / updated_at。外键：document_id → documents(id) RESTRICT。

**reimbursement_standards（16 列）**：id，city_code NOT NULL，grade_code NOT NULL，expense_type_code NOT NULL，amount_limit_cents INTEGER NOT NULL（≥0），unit TEXT NOT NULL（night / day / trip / item），currency TEXT NOT NULL DEFAULT 'CNY'（只允许 CNY），effective_from NOT NULL（YYYY-MM-DD，长度 10），effective_to NULL（≥ effective_from），source_document_id NOT NULL，source_version NOT NULL（≥1），source_clause TEXT NOT NULL（1–200 字），is_active DEFAULT 1，updated_by NOT NULL，created_at / updated_at。

**approval_flows（19 列）**：id，flow_code TEXT NOT NULL（1–40 字），flow_name TEXT NOT NULL（1–100 字），expense_type_code NOT NULL，min_amount_cents DEFAULT 0（≥0，含下界），max_amount_cents NULL（> min，不含上界），step_no NOT NULL（>0），approver_role TEXT NOT NULL（1–50 字），condition_text TEXT NOT NULL DEFAULT ''，is_required DEFAULT 1，effective_from NOT NULL，effective_to NULL，source_document_id NOT NULL，source_version NOT NULL（≥1），source_clause NOT NULL（1–200 字），is_active DEFAULT 1，updated_by NOT NULL，created_at / updated_at。

**special_expense_rules（16 列）**：id，scene_code NOT NULL，keywords TEXT NOT NULL DEFAULT ''，condition_text TEXT NOT NULL（1–500 字），rule_text TEXT NOT NULL（1–3000 字），is_allowed NULL（空表示结合条件判断），required_materials TEXT NOT NULL DEFAULT ''，effective_from NOT NULL，effective_to NULL，source_document_id NOT NULL，source_version NOT NULL（≥1），source_clause NOT NULL（1–200 字），is_active DEFAULT 1，updated_by NOT NULL，created_at / updated_at。

**faq（13 列）**：id，question TEXT NOT NULL（1–500 字，不再唯一），normalized_question TEXT NOT NULL UNIQUE（规范化规则见第 8 节），answer TEXT NOT NULL（1–3000 字），category_id NOT NULL，source_document_id NOT NULL，source_version NOT NULL（≥1），source_clause NOT NULL（1–200 字），hit_count DEFAULT 0，is_active DEFAULT 1，updated_by NOT NULL，created_at / updated_at。

**conversations（9 列）**：id，user_id NOT NULL，title TEXT NOT NULL DEFAULT '新会话'（1–50 字），summary NULL，summary_until_message_id NULL，context_document_id NULL，is_deleted DEFAULT 0，created_at / updated_at。

**messages（13 列）**：id，conversation_id NOT NULL，role TEXT NOT NULL（user / assistant，不保存独立 system / tool 角色消息），content TEXT NOT NULL DEFAULT ''，status TEXT NOT NULL（completed / generating / interrupted / failed，无默认值），request_id TEXT NOT NULL（同一轮 user 和 assistant 共用），reply_to_message_id NULL（assistant 必须指向同会话 user 消息，CHECK：`role='user' OR reply_to_message_id IS NOT NULL`），citations_json DEFAULT '[]'（合法 JSON 数组），used_tools_json DEFAULT '[]'（合法 JSON 数组），error_code NULL，token_count DEFAULT 0，created_at / updated_at。

**qa_logs（17 列，无 updated_at）**：id，user_id NOT NULL，conversation_id NOT NULL，assistant_message_id INTEGER NOT NULL UNIQUE，question TEXT NOT NULL（1–500 字），rewritten_query NULL，hit_chunks_json DEFAULT '[]'，top_score REAL NULL（0–1），used_tools_json DEFAULT '[]'，answer_type TEXT NOT NULL（faq / rag / structured / web / clarify / refusal / error，无默认值），is_refused DEFAULT 0，latency_ms INTEGER NOT NULL（≥0，无默认值），first_token_ms NULL，knowledge_supplemented DEFAULT 0，supplemented_by NULL，supplemented_at NULL，created_at NOT NULL。

**browse_history（5 列，无 created_at）**：id，user_id NOT NULL，document_id NOT NULL，last_viewed_at TEXT NOT NULL DEFAULT 上海时间，view_count INTEGER NOT NULL DEFAULT 1（≥1）。

**audit_logs（10 列，无 updated_at）**：id，actor_user_id NULL（未登录可空），action TEXT NOT NULL，target_type TEXT NOT NULL（1–40 字），target_id TEXT NULL，request_id TEXT NOT NULL，result TEXT NOT NULL（success / failure），detail_json TEXT NOT NULL DEFAULT '{}'（合法 JSON 对象，先脱敏），client_ip NULL，created_at NOT NULL。

### 5.3 关键索引（已验证）

- 普通索引（按概要设计第 4 章）：users(role, is_active, department_id)、documents(category_id, publish_status, is_deleted, updated_at DESC) 和 (sync_status, updated_at)、standards(expense_type_code, city_code, grade_code, effective_from, effective_to)、approval(expense_type_code, effective_from, min_amount_cents)、special(scene_code, is_active, effective_from, effective_to)、faq(category_id, is_active)、conversations(user_id, is_deleted, updated_at DESC)、messages(conversation_id, id DESC) 和 (reply_to_message_id)、qa_logs(created_at, user_id, is_refused) 和 (answer_type, created_at)、browse(user_id, last_viewed_at DESC)、audit(created_at, action) 和 (actor_user_id, created_at)，其余见建表 SQL。
- **部分唯一索引（两条，缺一不可）**：
  - `uq_sync_jobs_doc_running: CREATE UNIQUE INDEX ... ON sync_jobs(document_id) WHERE status = 'running'` —— 一个文档同一时刻最多一个 running 任务。
  - `uq_messages_conv_generating: CREATE UNIQUE INDEX ... ON messages(conversation_id) WHERE role = 'assistant' AND status = 'generating'` —— 一个会话最多一条生成中的助手消息。
- 注意：sync_jobs 还有一条普通唯一约束 `UNIQUE(document_id, target_version, action)`，它和部分唯一索引是两回事。测部分索引时必须换 target_version 或 action，否则会被普通唯一约束挡住，测不出部分索引。

### 5.4 循环外键：conversations ↔ messages

`conversations.summary_until_message_id → messages.id`，同时 `messages.conversation_id → conversations.id`，两边互相指。这是概要设计本来的写法，不是 bug。

正常顺序不会撞上：先建会话（摘要指针 NULL）→ 再发消息 → 攒够了再回填摘要指针。顺序反了（建会话时就填还不存在的消息）会被 FK 挡住，这是对的。

物理删除会被两边 RESTRICT 挡住，但项目用逻辑删除（`is_deleted`），平时不物理删。真要物理清理，顺序是：先把摘要指针置 NULL，再删消息，最后删会话。

如果以后想降低顺序约束，又不想丢完整性，改法不是删外键，而是改成 `DEFERRABLE INITIALLY DEFERRED`（同一事务内任意顺序，提交时才检查）。现在库是空的，要改也是现在改最便宜。

## 6. Seed 基础数据（第 3 步，已验证）

seed 只在空库上跑一次，非空直接跳过，不重复插。seed 脚本在 `app/seed.py`，`seed_db()`。

| 表 | 行数 | 内容（示例、非真实制度） |
|---|---|---|
| departments | 3 | 财务部 10、人事部 20、技术部 30，全部启用 |
| dict_items | 8 | city：BEIJING 北京、SHANGHAI 上海；grade：P5 五级专员、P6 六级主管；expense_type：HOTEL 住宿、MEAL_ALLOWANCE 餐补；scene：LOST_RECEIPT 票据丢失、OVER_STANDARD 超标准 |
| users | 1 | admin，系统管理员，role=admin，department_id 可空，bcrypt 哈希（`$2b$12$`），must_change_password=1 |
| categories | 2 | 差旅报销、票据规范 |
| documents | 2 | 差旅费用报销管理办法（示例制度）、报销票据与凭证管理规范（示例制度），published + pending + active_vector_version=NULL |
| reimbursement_standards | 2 | SHANGHAI / P5 / HOTEL / 80000 分 / night / CNY；* / P5 / MEAL_ALLOWANCE / 12000 分 / day / CNY |
| approval_flows | 2 | 同一组 TRAVEL_HOTEL / HOTEL，步骤 1 直属主管、步骤 2 财务专员，min_amount_cents=0 |
| special_expense_rules | 1 | OVER_STANDARD，keywords=超标准，条件是一句人话，不是 JSON |
| faq | 2 | 规范化按第 8 节规则生成，例如 `P5员工去上海出差住宿标准是多少？` → `p5员工去上海出差住宿标准是多少` |
| sync_jobs | 2 | 文档 1、文档 2 各一条 rebuild、pending、target_version=1 |
| document_chunks / conversations / messages / qa_logs / browse_history / audit_logs / auth_sessions / files | 0 | 运行时才产生的数据，seed 里一律不插 |

管理员密码从环境变量 `ADMIN_PASSWORD` 读，没设置时用本地测试临时密码，并在输出里提醒第一次登录必须改密码。**不要拿这个 seed 库当正式环境用，第一次登录改掉密码之后才算安全。**

## 7. 接口分类：61 个接口（概要设计第 5 章）

统一约定：

- 成功：`{code:"OK", message:"成功", data:业务对象, request_id:UUID}`；失败：`{code:错误码, message:原因, data:null, request_id:UUID, details:字段错误数组或null}`。
- 状态码：200 成功、201 创建、202 异步受理、401 未登录、403 无权限、404 不存在、409 冲突、413 文件过大、422 参数不合法、429 限流、502 / 503 依赖或服务故障。
- 权限：除公开注册、登录、部门选项、首页卡片、封面缩略外，一律要 `Authorization: Bearer <JWT>`；员工只能看本人会话和历史，后台接口仅 admin。
- 分页：`Page<T> = {items, page, page_size, total}`，page 默认 1、page_size 默认 10、范围 1–50；员工文档列表固定 10；消息 limit 默认 20、范围 1–20，历史用游标 `before_id / next_before_id`。
- 金额：接口传元（两位小数字符串），库内是分。
- 时间：接口日期用 `YYYY-MM-DD`，时间用带时区的 ISO 8601（Asia/Shanghai）；库内时间见第 5 节开头。

### 7.1 分组清单（共 61 个，编号、方法、路径、调用者）

**认证 AUTH（5 个）**

| 编号 | 方法与路径 | 调用者 | 主要参数 / 说明 |
|---|---|---|---|
| AUTH-01 | POST /api/auth/register | 游客 | username 4–20（字母数字下划线）、password 8–20（含字母和数字）、display_name 2–20、department_id；角色固定 employee；成功自动登录，201 |
| AUTH-02 | POST /api/auth/login | 游客 | username、password；连续 5 次错误锁 10 分钟；失败统一凭据错误，不暴露账号存在性；禁用 403，锁定 429 |
| AUTH-03 | POST /api/auth/logout | 员工 / 管理员 | 无；幂等撤销当前 sid |
| AUTH-04 | GET /api/auth/me | 员工 / 管理员 | 无；返回当前账号信息，不含密码哈希 |
| AUTH-05 | PUT /api/auth/password | 员工 / 管理员 | old_password、new_password（8–20，含字母和数字） |

**公开 PUB（3 个）**

| 编号 | 方法与路径 | 调用者 | 说明 |
|---|---|---|---|
| PUB-01 | GET /api/public/departments | 游客 | 只返回启用部门 |
| PUB-02 | GET /api/home | 游客 / 已登录 | 每分类最多 4 篇，只返回 published 且未删除的标题、封面、分类，不返回正文或附件 |
| PUB-03 | GET /api/public/covers/{file_id} | 游客 | 只返回当前已上架文档引用的 cover，固定最大 480 像素缩略图，其他文件 404 |

**公共 COMMON（2 个）**

| 编号 | 方法与路径 | 调用者 | 说明 |
|---|---|---|---|
| COMMON-01 | GET /api/dict-items?dict_type=city\|grade\|expense_type\|scene | 员工 / 管理员 | 只返回已启用项 |
| COMMON-02 | GET /api/files/{file_id}/content | 员工 / 管理员 | 员工仅可下载已上架未删除文档关联附件；无关联或无权限 404 / 403 |

**员工文档 DOC（3 个）**

| 编号 | 方法与路径 | 调用者 | 说明 |
|---|---|---|---|
| DOC-01 | GET /api/categories | 员工 | document_count 只统计员工可见文档 |
| DOC-02 | GET /api/documents?category_id&keyword&page&page_size | 员工 | keyword 1–50，标题与正文关键词参数化匹配；page_size 固定 10；过滤下架和逻辑删除；**不调用向量库** |
| DOC-03 | GET /api/documents/{document_id} | 员工 | 详情更新 browse_history，写失败不阻止正文读取；下架 / 不存在 404；Markdown 安全处理 |

**浏览历史 HIS（3 个，员工仅本人）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| HIS-01 | GET /api/me/browse-history?page&page_size | 按最近访问倒序；隐藏下架和删除文档 |
| HIS-02 | DELETE /api/me/browse-history/{document_id} | 记录不存在也幂等返回成功 |
| HIS-03 | DELETE /api/me/browse-history | 返回 deleted_count |

**分类管理 CAT（4 个，管理员）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| CAT-01 | GET /api/admin/categories | 计数含后台未删除文档 |
| CAT-02 | POST /api/admin/categories | name 2–20、sort_order 默认 0；重名 409 |
| CAT-03 | PUT /api/admin/categories/{category_id} | 改名不改变引用外键 |
| CAT-04 | DELETE /api/admin/categories/{category_id} | 仍有文档或 FAQ 则 409，并返回关联数量，不自动移走文档 |

**文件 FILE（1 个，管理员）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| FILE-01 | POST /api/admin/files（multipart） | kind=attachment\|cover；附件 doc / docx / pdf / txt / md ≤20MiB，封面 jpg / png ≤5MiB；检验真实类型、随机存储名 |

**后台文档 ADOC（8 个，管理员）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| ADOC-01 | GET /api/admin/documents?keyword&category_id&publish_status&sync_status&page&page_size | 默认排除逻辑删除，支持同步失败筛选 |
| ADOC-02 | POST /api/admin/documents | Body DocWrite；202，返回 {document, job_id}；事务保存文档与 rebuild 任务；正文未传时从附件解析 |
| ADOC-03 | GET /api/admin/documents/{document_id} | 后台详情 |
| ADOC-04 | PUT /api/admin/documents/{document_id} | Body DocWrite + expected_version；正文、标题、分类、附件变化递增 version；版本冲突 409；202 |
| ADOC-05 | DELETE /api/admin/documents/{document_id}?expected_version | 先逻辑删除并提交 remove 任务；202 |
| ADOC-06 | PUT /api/admin/documents/{document_id}/publication | publish_status=published\|unpublished + expected_version；发布执行 rebuild，下架立即隐藏并 remove；202 |
| ADOC-07 | GET /api/admin/documents/{document_id}/sync-status | 前端仅 pending / syncing 每 2 秒轮询，终态停止 |
| ADOC-08 | POST /api/admin/documents/{document_id}/sync/retry | Body target_version；只重试当前目标版本；进行中幂等返回原任务；过期版本 409；202 |

**差旅标准 STD（4 个，管理员）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| STD-01 | GET /api/admin/standards?city_code&grade_code&expense_type_code&needs_review&page&page_size | — |
| STD-02 | POST /api/admin/standards | Body StandardWrite；维度必须有效；重复组合或有效期交叠 409；保存不触发向量化 |
| STD-03 | PUT /api/admin/standards/{standard_id} | 来源必须为当前版本；保存后查询即生效 |
| STD-04 | DELETE /api/admin/standards/{standard_id} | 设置 is_active=0，不是物理删除；历史回答快照不变 |

**审批流程 FLOW（4 个，管理员，按组操作）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| FLOW-01 | GET /api/admin/approval-flows?expense_type_code&needs_review&page&page_size | 按 flow_code + effective_from 分组，每个流程对象含有序 steps |
| FLOW-02 | POST /api/admin/approval-flows | Body ApprovalWrite；一个事务保存全部节点；节点连续、同费用生效期及金额适用范围不冲突 |
| FLOW-03 | PUT /api/admin/approval-flows/{flow_code}/{effective_from} | 整组替换节点；调整生效日通过新增版本组，不隐式修改组标识 |
| FLOW-04 | DELETE /api/admin/approval-flows/{flow_code}/{effective_from} | 整组 is_active=0，不执行真实审批 |

**特殊费用规则 RULE（4 个，管理员）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| RULE-01 | GET /api/admin/special-rules?scene_code&needs_review&page&page_size | — |
| RULE-02 | POST /api/admin/special-rules | Body SpecialWrite |
| RULE-03 | PUT /api/admin/special-rules/{rule_id} | Body SpecialWrite |
| RULE-04 | DELETE /api/admin/special-rules/{rule_id} | 设置 is_active=0 |

**FAQ（4 个，管理员）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| FAQ-01 | GET /api/admin/faqs?keyword&category_id&needs_review&page&page_size | keyword ≤50 |
| FAQ-02 | POST /api/admin/faqs | Body FAQWrite；规范化问题重复 409；不向量化 |
| FAQ-03 | PUT /api/admin/faqs/{faq_id} | Body FAQWrite |
| FAQ-04 | DELETE /api/admin/faqs/{faq_id} | 设置 is_active=0 |

**字典 DICT（1 个，管理员）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| DICT-01 | POST /api/admin/dict-items | dict_type、code 1–40（字母数字下划线）、label 1–50、sort_order；重复代码 409 |

**会话 CONV（6 个，员工仅本人）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| CONV-01 | POST /api/conversations | title 可选（不传暂为“新会话”，首问后前 10 字自动更新）、context_document_id 可选（必须可见） |
| CONV-02 | GET /api/conversations?page&page_size | 仅本人未删除会话，updated_at 倒序 |
| CONV-03 | GET /api/conversations/{conversation_id} | 他人会话 403；已删除或不存在 404 |
| CONV-04 | GET /api/conversations/{conversation_id}/messages?before_id&limit | limit 1–20，默认 20；最近 20 条按正序返回；next_before_id 用于更早一页 |
| CONV-05 | PATCH /api/conversations/{conversation_id} | title 1–50 |
| CONV-06 | DELETE /api/conversations/{conversation_id} | 设置 is_deleted=1；有生成任务时取消并保存中断状态 |

**问答 CHAT（2 个，员工，SSE）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| CHAT-01 | POST /api/chat（Accept: text/event-stream） | Body ChatWrite；会话归属校验；同一会话生成中返回 409；client_request_id 重复不创建新轮次；不传 conversation_id 时服务端创建会话；事件结构见概要设计本接口 SSE 定义 |
| CHAT-02 | POST /api/messages/{message_id}/retry（Accept: text/event-stream） | 仅 failed 或 interrupted；成功完成消息 409；复用原问题与 assistant ID，使用最新有效证据重新生成并替换旧引用，日志 upsert |

**问答日志 LOG（3 个，管理员）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| LOG-01 | GET /api/admin/qa-logs?start_date&end_date&user_id&is_refused&knowledge_supplemented&page&page_size | 仅运营审计入口可读 |
| LOG-02 | PATCH /api/admin/qa-logs/{log_id}/supplement | knowledge_supplemented:bool；只标记处理结果，不自动生成 FAQ 或修改文档 |
| LOG-03 | GET /api/admin/qa-logs/export | 与 LOG-01 筛选相同，不接收分页；Excel 二进制，文件名 `问答日志_YYYY-MM-DD.xlsx`，最多 10000 条；以 =、+、-、@ 起始文本转为安全文本防公式注入 |

**数据看板 DASH（1 个，管理员）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| DASH-01 | GET /api/admin/dashboard?start_date&end_date | 时间范围最多 366 天；命中 = faq / rag / structured，分母为有效业务轮次，排除 clarify / error；拒答率同分母 |

**用户管理 USER（3 个，管理员，仅员工可操作）**

| 编号 | 方法与路径 | 说明 |
|---|---|---|---|
| USER-01 | GET /api/admin/users?keyword&department_id&is_active&page&page_size | 仅返回 employee，无密码哈希及失败次数 |
| USER-02 | PATCH /api/admin/users/{user_id}/status | is_active:bool；禁用撤销全部会话；记录审计 |
| USER-03 | POST /api/admin/users/{user_id}/reset-password | new_password 8–20（含字母与数字）；只返回结果不回传密码；设置强制改密，撤销全部登录会话；只写脱敏审计 |

> 另外，新项目里已有的 `/api/health` 不在上面 61 个里，它是健康检查接口，返回 `{status:"ok", table_count:18, fk_check_empty:true, timestamp}`，不要把它和业务接口混在一起数。

## 8. 问答流程（概要设计第 5 章，CHAT-01 / CHAT-02 共用）

```
用户问题（1–500 字）
  → 校验：本人会话、消息状态、幂等键（client_request_id）
  → 1. FAQ 前置匹配：规范化问题后匹配 normalized_question
        命中 → 直接返回标准答案，hit_count+1
               （含金额的答案仍要经结构化标准工具复核）
  → 2. 结构化工具：金额 → reimbursement_standards 精确查询
                   审批 → approval_flows 按费用类型 + 金额 + 日期
                   特殊 → special_expense_rules 按 scene_code
  → 3. 向量 + 关键词 RRF Top5：document_chunks（只取已发布、未删除、
        块版本 = active_vector_version 的内容），本地 BGE 向量化
  → 4. DeepSeek 生成：按证据和对话上下文生成，temperature 0.2（模型支持时）
        对话上下文 = 最近 6 轮 + 更早摘要（不是最近 20 条，20 条是历史加载数）
  → 5. 联网搜索（Tavily）：仅在内部无有效依据、且问题涉及外部时效信息时，
        每轮最多 1 次；网络结论不得替代公司制度和报销金额标准
  → 无依据 → 拒答（answer_type=refusal，is_refused=1），不要编造
  → 保存：用户消息、助手消息、引用、qa_logs（重试时 upsert 原日志）
  → SSE 输出，首字 ≤3 秒；中断 / 失败保留状态，可用 CHAT-02 重试
```

FAQ 规范化规则（服务层和 seed 必须用同一套，否则匹配不上）：

```
Unicode NFKC（全角转半角）→ 去首尾空白、连续空白合并为一个
→ 去掉中英文标点 → 英文转小写
```

## 9. 已知缺口和不要踩的坑

- 接口（61 个）和前端（Vue3）还没做完，本 README 不代表它们已经实现。
- 向量化 Worker 还没做，文档保存时只登记 sync_jobs，状态流转要先做对。
- seed 里的部门、职级中文名、标准金额、FAQ 都是示例，正式使用前必须由管理员换成真实制度，并把示例文档、示例标准逐条核对后再启用（seed 里示例标准是 is_active=1，正式上线前要复核）。
- `auth_sessions.expires_at`、`conversations.title` 现在有数据库默认值，服务层漏了也不会报错，但服务层仍应在登录时显式算 120 分钟过期、在创建会话时显式处理标题逻辑，不要完全依赖默认值。
- `users.username`、`dict_items.code` 的字符集（字母数字下划线）目前数据库 CHECK 只做了长度，字符集由服务层校验。
- `files.size_bytes` 的 kind 专属上限（附件 20MiB、封面 5MiB）由服务层按 kind 校验，数据库 CHECK 只做了基础范围。
- 旧项目、旧库、旧迁移说明都已作废，不要再从旧代码里抄字段、抄接口、抄 seed。

## 附录 A：61 个接口开发 prompt（直接复制可用）

> 下面这段就是做第 4 步接口时用的 prompt，附在这里，开发时直接复制给开发助手就能用，不用重新写。
> 附上本 README 和《概要设计说明书-2026-10-28修订版.docx》一起用，接口清单以本 README 第 7 节和概要设计第 5 章为准。

```
请在本仓库项目里做第 4 步：接口，不要改 schema、不要改 seed、不要推送。

前提：18 张表和 seed 已经做完并验过，departments=3、dict_items=8、admin=1、documents=2、standards=2、flows=2、special=1、faq=2，这些都不要再动。

1. 唯一依据
- 随 prompt 附上的《概要设计说明书-2026-10-28修订版.docx》第 5 章是唯一标准，61 个接口按第 5 章的分组来，不要自己发明接口、不要改路径、不要改字段名。
- 先从第 5 章里把 61 个接口列成一张清单，做完一项勾一项，最后把清单和完成情况一起交出来，漏了哪个要明说，不要说“全部完成”。

2. 按这个顺序做，每组做完先自测
- 4a 认证与公共入口：注册、登录、登出、部门选项、首页卡片、封面缩略。注册只能建 employee，admin 只能由 seed 预置；登录要写 auth_sessions，JWT 里带 sid，服务端校验未过期、未撤销、账号仍启用，有效期 120 分钟。
- 4b 文档与分类：分类管理、文档管理、文件上传、文档详情、分类文档列表、文档搜索、浏览历史。详情读取成功后要写 browse_history，写失败不能阻止正文读取；文档搜索走数据库关键词，不要走向量库；附件 ≤20MiB、封面 ≤5MiB。
- 4c 结构化数据管理：字典、部门、标准、审批、特殊、FAQ 的后台维护。金额对外是元（两位小数字符串），库内是整数分，转换在服务层做；标准、审批、特殊、FAQ 的 source_version、source_clause、updated_by 都必填。
- 4d 会话与问答：会话 CRUD、消息历史、问答 SSE。问答顺序按第 5 章走：先 FAQ 文本匹配（命中直接返回并 hit_count+1，含金额的答案仍要经标准工具复核），再结构化工具（金额、审批、特殊），再向量 + 关键词 RRF Top5，最后才是 DeepSeek；查不到就拒答，不要编造。SSE 要真流式，首字 ≤3 秒；重试要复用原问题和原回答记录，不要另起一轮。
- 4e 日志与后台：问答日志、看板、用户管理、同步状态。文档保存、上下架时要同步写 sync_jobs，状态查询和手动重试要能跑；向量化 Worker 本身如果这一步做不完，先把任务登记和状态流转做对，Worker 的缺口要明说，不要假装已经向量化了。

3. 统一约定，一律按第 5 章来
- 成功响应：{code:"OK", message:"成功", data:业务对象, request_id:UUID}；失败响应：{code:错误码, message:原因, data:null, request_id:UUID, details:字段错误数组或null}。
- 状态码：201 创建、202 异步受理、200 成功、401 未登录、403 无权限、404 不存在、409 冲突、413 文件过大、422 参数不合法。
- 权限：除公开注册、登录、部门选项、首页卡片、封面缩略外，一律要 Authorization: Bearer <JWT>；员工只能看本人会话和历史，后台接口仅 admin。
- 分页：Page 格式 {items, page, page_size, total}，page 默认 1、page_size 默认 10、范围 1–50，员工文档列表固定 10；消息 limit 默认 20、范围 1–20。
- 时间：接口的日期用 YYYY-MM-DD，时间用带时区的 ISO 8601（Asia/Shanghai），不要直接把库里的本地时间原样当 ISO 时间返回。
- 游客只有首页卡片，详情和问答一律要登录。

4. 验证，必须跑过再交
- 用 TestClient 对每组接口至少测：公开接口不用登录能通、受保护接口没 token 返回 401、员工调后台接口返回 403、分页和参数错误返回 422、FAQ 命中、标准精确查询、会话创建和续聊、问答拒答这几条主线。
- 原有的 /api/health、init_db 18 张表、seed 行数这些测试不能被改坏，跑一遍确认还是过的。
- 验证命令和结果原样贴出来，哪些接口还没做、哪些是占位，单独列一张表，不要混在“完成”里。
- 交的东西只有接口代码和测试，不要改 schema、不要改 seed、不要推送。
```

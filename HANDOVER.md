# 财务报销制度智能咨询助手 — 开发注意事项

> 写于 2026-10-28。
> 本文件和同目录 `README.md` 配合使用：`README.md` 写的是框架、技术栈、表参数、接口清单，本文件写的是开发和配置时要注意的事。
> 唯一依据：《概要设计说明书-2026-10-28老师反馈修订版v0.0.3》（以下简称“概要设计”）。老师反馈修订后：知识库正文文件化、audit_logs 表删除，表数 17 张；原附录 A 的接口开发 prompt 已删除，做接口前需按 v0.0.3 重新给 prompt。

## 1. 项目现状

- 旧项目已经放弃打补丁，2026-10-28 当天决定按最终定的概要设计从头重建，旧库迁移、旧 seed、旧接口一律作废。
- 新项目就是 push 到仓库后的 main，旧代码只留 Git 历史存档，不要再从旧代码里抄字段、抄接口、抄 seed。注意：仓库远端 main 目前还是旧的 18 表版本，Mac 本地已改为 17 表，推送前必须确认推的是本地 17 表版本。
- 当前进度：骨架 + 17 张表 + seed 已做完并验过（2026-10-28 晚按 v0.0.3 重验，verify_step3_v003.py PASS=56 FAIL=0），接口（61 个）和前端还没做。
- 仓库：私有仓库 `Shakunnn/finance-assistant`，main。2026-10-28 中午已推送过旧 18 表版本（586631b、5b4f856），新的 17 表版本（v0.0.3）目前只在 Mac 本地，还没推送；之前说的 `83ab89e` 在仓库里找不到，不要再去对那笔账。

## 2. 配置环境时注意

- Python 只保证 3.10 / 3.11，优先 3.11；低于 3.10 不行，高于 3.11 不在保证范围内。
- Windows 用 python.org 的 3.11 安装包，安装时勾选 Add Python to PATH，不要用 Microsoft Store 的 Python；macOS 用 `brew install python@3.11` 或 python.org 的 arm64 安装包，不要用无版本号的 `brew install python`。
- 建虚拟环境、激活、跑命令，Windows 和 macOS 的写法不一样，按 `README.md` 第 4 节选自己系统的写法，激活后统一用 `python`，不要把 `.venv/bin/python`、`.venv\Scripts\python.exe`、个人电脑的绝对路径写进代码、配置或文档。
- `.env`、`.env.example` 里只放占位符，真实值本地自己填；`.env` 本身不进仓库。
- `data/` 是 gitignore 的，里面是 `app.db`、`chroma`、`uploads`，不进仓库；`data/app.db` 删了可以重建，`init_db()` + `seed_db()` 就能恢复到基础数据。
- BGE 向量化在没有 GPU 的机器上走 CPU 也能跑，只是慢一点，不要因为没 GPU 就改模型或改代码；有 GPU 的机器按设备选择逻辑走（cuda → mps → cpu），不要硬编码设备。
- 文件一律 UTF-8，代码和配置文件里的路径一律用 `/`，不要把 Windows 的绝对路径写进去。

## 3. 开发时已定决策，不要自己改

这些都是 2026-10-28 之前定下来的，改任何一条都要先确认，不要在代码里悄悄改回去。

| 决策 | 定法 |
|---|---|
| 向量化 | 本地 BGE-small-zh-v1.5，384 维，固定版本；不用云端 Embedding API。云端外部接口只有 2 个：DeepSeek（对话生成与摘要）、Tavily（联网搜索）。按概要设计 §5 的 EXT 编号，EXT-LLM、EXT-WEB 是云端，EXT-DB、EXT-VEC、EXT-EMB、EXT-FS 是本地支持接口 |
| 密码 | bcrypt，`bcrypt>=4.0,<4.1`，只存加盐哈希。原因是 passlib 1.7.4 + bcrypt 5.0.0 不兼容，永不去掉、永不放宽 |
| 时间 | 库内统一 Asia/Shanghai 本地时间，格式 `YYYY-MM-DD HH:MM:SS`。实现是 `strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')`，不是 `datetime('now','localtime')`，这样不管服务器时区怎么设都是上海时间。接口时间用带时区的 ISO 8601（Asia/Shanghai） |
| 数据访问 | SQLAlchemy 只用 Engine + Session + `text()` 原生 SQL，不要求 ORM 模型。概要设计只在软件环境表里提了一次 SQLAlchemy，没有要求 ORM 模型，改全套 ORM 要重写 30 多条 SQL、无收益，不要做 |
| 金额 | 库内整数分，字段 `_cents`；对外是元（两位小数字符串），转换在服务层做 |
| 切块 | 300–500 字，重叠约 50 字，不是旧的 800 / 150 |
| 角色 | employee / admin，不是 user / admin；员工必填部门，管理员可空；公开注册只能建 employee |
| 问答 | 真 SSE 流式，首字 ≤3 秒；问题 1–500 字；会话标题首问前 10 字 |
| 上下架与同步 | publish_status 与 sync_status 分离；active_vector_version 机制；文档下架或逻辑删除立即停止员工访问及新检索 |
| 历史 | 历史加载最近 20 条，模型上下文最近 6 轮 + 更早摘要，这两个数不能混为一谈 |
| 文档搜索 vs 问答检索 | 文档搜索走数据库关键词，不走向量库；问答检索走向量 + 关键词 RRF Top5，不要把两个通道混在一起 |
| 旧库处理 | 旧库已废弃，不做迁移。旧库迁移说明里的 13 项待确认、slug / condition_json 转文本、system / tool 消息、收藏、feedback 这些旧数据处理规则，全部作废 |
| 推送纪律 | 代码推送、邮件发送一律先预览、确认后再推 / 再发，绝不跳过核验直接推 |

### 被推翻的旧决定，不要再用

- SRS 云端 Embedding → 已推翻，改本地 BGE；SRS §§2.5 / 8 的云端写法还没同步改，暂时不动 SRS。
- 本地 per-machine 部署、800 / 150 切块、user / admin、stream 占位 → 已被 SRS 标准推翻，之后又以概要设计为准，不要再用。
- 旧项目 12 表 → 18 表的迁移方案 → 已作废，改为从头重建；2026-10-28 晚又按老师反馈修订为 17 表最终版（删 audit_logs、documents 改 file_path/file_hash、document_chunks 删 content），不要再用 18 表版本。

## 4. 数据库开发时注意

- 17 张表、列、类型、非空、默认值、外键、索引、CHECK、部分唯一索引，见 `README.md` 第 5 节，开发时不要自己加表、加列、改字段名。documents 是元数据表（file_path + file_hash，不存正文），document_chunks 是向量索引（不存正文），没有 audit_logs 表。
- 外键删除规则一律 `ON DELETE RESTRICT`，被引用时不能物理删除；账号用 `is_active`、文档和会话用 `is_deleted` 做逻辑控制。
- 没有的表 / 字段，不要自己加：旧项目的 `user_doc_actions`（收藏）、`categories.slug / description`、`document_chunks.token_count`、`qa_log.feedback_*`、`answer_chars`，概要设计里都没有，新 schema 里也没有。
- 时间默认值、金额单位、0/1 字段、JSON 字段的规则，见 `README.md` 第 5 节开头，写新代码时按那个来。
- `auth_sessions.id` 是 TEXT（JWT 里的 sid，UUID），不是自增整数，而且是 NOT NULL；`auth_sessions.expires_at` 默认签发后 120 分钟；`conversations.title` 默认 `'新会话'`。这三处是 2026-10-28 当天补的，不要再改回去。
- `users.username`、`dict_items.code` 的字符集（字母数字下划线）目前数据库 CHECK 只做了长度，字符集必须在服务层校验。
- `files.size_bytes` 的 kind 专属上限（附件 20MiB、封面 5MiB）由服务层按 kind 校验，数据库 CHECK 只做了基础范围。

### 循环外键，写摘要时注意顺序

`conversations.summary_until_message_id` ↔ `messages.conversation_id`，两边互相指，这是概要设计本来的写法，不是 bug。

顺序必须是：先建会话（指针 NULL）→ 再发消息 → 再回填指针。顺序反了会被 FK 挡住，这是对的。

物理删除会被两边 RESTRICT 挡住，但项目用逻辑删除，平时不物理删。真要物理清理，顺序是：先把摘要指针置 NULL，再删消息，最后删会话。

如果想降顺序约束，又不想丢完整性，改法不是删外键，而是改成 `DEFERRABLE INITIALLY DEFERRED`（同一事务内任意顺序，提交时才检查）。现在库是空的，要改也是现在改最便宜。

### 部分唯一索引，测试时注意

- 一个文档同一时刻最多一个 running 任务：`UNIQUE(document_id) WHERE status='running'`。
- 一个会话最多一条生成中的助手消息：`UNIQUE(conversation_id) WHERE role='assistant' AND status='generating'`。
- 这两个都是靠部分唯一索引落实的，不是靠“先查再插”，先查再插在并发下会漏。
- sync_jobs 还有一条普通唯一约束 `UNIQUE(document_id, target_version, action)`，它和部分唯一索引是两回事。测部分索引必须换 target_version 或 action，否则会被普通约束挡住，测不出部分索引。

## 5. 接口开发时注意

- 61 个接口按 `README.md` 第 7 节分组做：认证与公共入口、文档与分类、结构化数据管理、会话与问答、日志与后台。每组做完先自测，61 个列成清单，做完一项勾一项，漏了要明说。
- 统一响应格式：成功 `{code:"OK", message:"成功", data:业务对象, request_id:UUID}`；失败 `{code:错误码, message:原因, data:null, request_id:UUID, details:字段错误数组或null}`。状态码：200 成功、201 创建、202 异步受理、401 未登录、403 无权限、404 不存在、409 冲突、413 文件过大、422 参数不合法。
- 权限：除公开注册、登录、部门选项、首页卡片、封面缩略外，一律要 `Authorization: Bearer <JWT>`；员工只能看本人会话和历史，后台接口仅 admin。
- 分页：`Page<T> = {items, page, page_size, total}`，page 默认 1、page_size 默认 10、范围 1–50；员工文档列表固定 10；消息 limit 默认 20、范围 1–20，历史用游标 `before_id / next_before_id`。
- 金额、时间、文件大小的转换规则，见 `README.md` 第 7 节开头，写接口时不要自己发明一套。
- 文档保存、上下架时要同步写 sync_jobs，状态查询和手动重试要能跑；向量化 Worker 本身如果做不完，先把任务登记和状态流转做对，缺口要明说，不要假装已经向量化了。
- 游客只有首页卡片，详情和问答一律要登录。

## 6. 问答开发时注意

流程按 `README.md` 第 8 节走，顺序不能乱：

```
FAQ 文本匹配 → 结构化工具（金额、审批、特殊）→ 向量 + 关键词 RRF Top5
→ DeepSeek 生成 → 联网搜索（仅在内部无有效依据、且问题涉及外部时效信息时）
→ 无依据就拒答，不要编造
```

- FAQ 规范化规则三处必须用同一套：seed、FAQ 维护、问答匹配。规则是：Unicode NFKC（全角转半角）→ 去首尾空白、连续空白合并为一个 → 去掉中英文标点 → 英文转小写。否则 seed 里的数据问答时匹配不上。
- FAQ 命中直接返回并 `hit_count+1`，含金额的答案仍要经标准工具复核。
- 文档搜索走数据库关键词，不走向量库；问答检索只取已发布、未删除、块版本等于 `active_vector_version` 的内容。
- SSE 要真流式，首字 ≤3 秒；重试要复用原问题和原回答记录，不要另起一轮；中断 / 失败保留状态，可用重试接口。
- 查不到就拒答（`answer_type=refusal`，`is_refused=1`），不要编造金额、条款、流程。

## 7. Seed 开发时注意

- seed 只在空库上跑一次，非空直接跳过，不重复插；跑之前先检查表是不是空的，已经有数据就停下来。
- seed 里的数据全部是示例、非真实制度：部门、字典、admin、分类、示例文档、标准、流程、特殊规则、FAQ，见 `README.md` 第 6 节。
- 管理员密码从环境变量 `ADMIN_PASSWORD` 读，没设置时用本地测试临时密码，并在输出里提醒第一次登录必须改密码，`must_change_password=1`。不要拿这个 seed 库当正式环境用。
- 会话、消息、问答日志、浏览历史、登录会话这些运行时才产生的数据，seed 里一律不插，从空开始。注意：已没有审计日志表，不要再往所谓 audit_logs 里写数据，操作日志按 v0.0.3 的 LOG/USER/OPS 接口写法处理。
- 文档先是 published + pending + `active_vector_version=NULL`，不要插假分块；给每篇文档在 sync_jobs 里插一条 rebuild、pending 的任务就行。
- seed 里的部门、职级中文名、标准金额、FAQ 都是示例，正式使用前必须由管理员换成真实制度，并把示例文档、示例标准逐条核对后再启用。

## 8. 凭证与秘密，开发时注意

- `.env`、`.env.example` 里只放占位符，真实值本地自己填。
- `JWT_SECRET`、`DEEPSEEK_API_KEY`、Tavily 密钥、管理员密码，一律不进代码、不进 seed SQL、不进 README、不进本文件。
- 操作日志的 detail_json 写入前必须脱敏，不能保存密码、完整令牌或供应商密钥（v0.0.3 已删除 audit_logs 表，不要再建审计表）。
- 一次性 key / 密码只暂用、不入记忆、不入文件、不入报告，用完要核查无残留。

## 9. 推送前注意

- 推送前必须先确认推的是新项目、不是旧项目，推完在 GitHub 网页上看一眼 main 里的 schema 是不是 17 张表、documents 是不是 file_path/file_hash。
- 推送前先跑一遍：删库 → `init_db()` → `seed_db()` → `/api/health`，确认还是 17 张表、seed 行数都对；验证脚本用 verify_step3_v003.py，不要用旧的 verify_step3.py。
- 推送时不要把 `data/`、验证脚本（verify_step3.py、verify_step3_v003.py）、`ADMIN_PASSWORD`、真实密钥推上去；`data/` 是 gitignore 的，验证脚本只在本地跑。注意：verify_step3_v003.py 目前不在 .gitignore 里，推送时要手动排除或先把它加进 .gitignore。
- 不要在没确认的情况下 force push；如果远程 main 和本地不一致，先看清楚远程多了什么，再决定。

## 10. 还没定的事项，开发时不要自己定

| 事项 | 说明 |
|---|---|
| 接口 61 个的实际实现进度 | 以代码和测试为准，不要以 `README.md` 里的清单为准；清单是概要设计定的，不是已实现清单 |
| 前端页面细节 | 概要设计第 7 章只给了页面结构，具体的组件、样式、移动端 / PC 端的细节以实际定的为准 |
| 部门、职级中文名、标准金额 | seed 里的都是示例，正式使用前必须换成真实制度并逐条核对 |
| 向量化 Worker 的具体实现 | BGE 模型文件放在哪、Chroma 集合怎么命名、失败重试和租约恢复怎么做，按概要设计第 4、5 章来，不要自己发明 |
| 是否推送、推到哪个仓库 / 分支 | 推送前必须先确认，不要擅自推 |

## 11. 开发自查清单

- [ ] 工作目录是仓库克隆后的项目根目录 `finance-assistant/`，不是旧项目
- [ ] 已跑通删库 → `init_db()` → `seed_db()` → `/api/health`，17 张表、seed 行数都对
- [ ] 已读完 `README.md` 第 5、7、8 节和本文件第 3–7 节
- [ ] 已知道哪些决策不能改（第 3 节），哪些坑不能踩（第 4–6 节）
- [ ] 接口按分组做，做完先自测，漏了的接口明说了，没有混在“完成”里
- [ ] 推送前已确认推的是新项目，没有把 `data/`、验证脚本、真实密钥推上去

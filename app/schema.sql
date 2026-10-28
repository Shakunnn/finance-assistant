-- 财务报销制度智能咨询助手（FA）数据库 Schema
-- 严格依据《概要设计说明书-2026-10-28修订版.docx》第 4 章 §4.3 定义（18 张表）
-- 幂等执行：全部采用 CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS

-- 1. 部门字典 departments
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) BETWEEN 2 AND 50),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours'))
);
CREATE INDEX IF NOT EXISTS idx_departments_active_sort
    ON departments(is_active, sort_order, id);

-- 2. 业务维度字典 dict_items
CREATE TABLE IF NOT EXISTS dict_items (
    id INTEGER PRIMARY KEY,
    dict_type TEXT NOT NULL CHECK (dict_type IN ('city', 'grade', 'expense_type', 'scene')),
    code TEXT NOT NULL CHECK (length(trim(code)) BETWEEN 1 AND 40),
    label TEXT NOT NULL CHECK (length(trim(label)) BETWEEN 1 AND 50),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    UNIQUE (dict_type, code)
);
CREATE INDEX IF NOT EXISTS idx_dict_items_type_active_sort
    ON dict_items(dict_type, is_active, sort_order);

-- 3. 用户账号 users
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (length(trim(username)) BETWEEN 4 AND 20),
    password_hash TEXT NOT NULL CHECK (length(trim(password_hash)) > 0),
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) BETWEEN 2 AND 20),
    department_id INTEGER REFERENCES departments(id) ON DELETE RESTRICT,
    role TEXT NOT NULL DEFAULT 'employee' CHECK (role IN ('employee', 'admin')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    failed_login_count INTEGER NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until TEXT,
    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    CHECK (role = 'admin' OR department_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_users_role_active_dept
    ON users(role, is_active, department_id);

-- 4. 登录会话 auth_sessions
CREATE TABLE IF NOT EXISTS auth_sessions (
    id TEXT NOT NULL PRIMARY KEY CHECK (length(trim(id)) > 0),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    expires_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours', '+120 minutes')),
    revoked_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    last_seen_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_revoked_expires
    ON auth_sessions(user_id, revoked_at, expires_at);

-- 5. 文档分类 categories
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) BETWEEN 2 AND 20),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours'))
);
CREATE INDEX IF NOT EXISTS idx_categories_sort_id
    ON categories(sort_order, id);

-- 6. 文件元信息 files
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('attachment', 'cover')),
    original_name TEXT NOT NULL CHECK (length(trim(original_name)) BETWEEN 1 AND 255),
    storage_key TEXT NOT NULL UNIQUE CHECK (length(trim(storage_key)) > 0),
    mime_type TEXT NOT NULL CHECK (length(trim(mime_type)) > 0),
    size_bytes INTEGER NOT NULL CHECK (
        size_bytes > 0
        AND (
            (kind = 'attachment' AND size_bytes <= 20971520)
            OR (kind = 'cover' AND size_bytes <= 5242880)
        )
    ),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    uploaded_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours'))
);
CREATE INDEX IF NOT EXISTS idx_files_uploaded_by_created
    ON files(uploaded_by, created_at);

-- 7. 制度文档 documents
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 100),
    body_markdown TEXT NOT NULL CHECK (length(trim(body_markdown)) > 0),
    attachment_file_id INTEGER REFERENCES files(id) ON DELETE RESTRICT,
    cover_file_id INTEGER REFERENCES files(id) ON DELETE RESTRICT,
    publish_status TEXT NOT NULL DEFAULT 'draft' CHECK (publish_status IN ('draft', 'published', 'unpublished')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    active_vector_version INTEGER CHECK (
        active_vector_version IS NULL
        OR (active_vector_version >= 1 AND active_vector_version <= version)
    ),
    sync_status TEXT NOT NULL DEFAULT 'pending' CHECK (sync_status IN ('pending', 'syncing', 'synced', 'failed')),
    sync_error TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    updated_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours'))
);
CREATE INDEX IF NOT EXISTS idx_documents_cat_pub_del_updated
    ON documents(category_id, publish_status, is_deleted, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_sync_updated
    ON documents(sync_status, updated_at);

-- 8. 知识块映射 document_chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    document_version INTEGER NOT NULL CHECK (document_version >= 1),
    chunk_no INTEGER NOT NULL CHECK (chunk_no >= 0),
    vector_id TEXT NOT NULL UNIQUE CHECK (length(trim(vector_id)) > 0),
    section_path TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL CHECK (length(trim(content)) > 0),
    content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
    embedding_model TEXT NOT NULL CHECK (length(trim(embedding_model)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    UNIQUE (document_id, document_version, chunk_no)
);
CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_ver
    ON document_chunks(document_id, document_version);

-- 9. 同步任务 sync_jobs
CREATE TABLE IF NOT EXISTS sync_jobs (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    target_version INTEGER NOT NULL CHECK (target_version >= 1),
    action TEXT NOT NULL CHECK (action IN ('rebuild', 'remove')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'superseded')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 3),
    next_retry_at TEXT,
    lease_until TEXT,
    last_error TEXT,
    started_at TEXT,
    finished_at TEXT CHECK (finished_at IS NULL OR (started_at IS NOT NULL AND finished_at >= started_at)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    UNIQUE (document_id, target_version, action)
);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_status_retry_created
    ON sync_jobs(status, next_retry_at, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_jobs_doc_running
    ON sync_jobs(document_id) WHERE status = 'running';

-- 10. 差旅标准 reimbursement_standards
CREATE TABLE IF NOT EXISTS reimbursement_standards (
    id INTEGER PRIMARY KEY,
    city_code TEXT NOT NULL CHECK (length(trim(city_code)) > 0),
    grade_code TEXT NOT NULL CHECK (length(trim(grade_code)) > 0),
    expense_type_code TEXT NOT NULL CHECK (length(trim(expense_type_code)) > 0),
    amount_limit_cents INTEGER NOT NULL CHECK (amount_limit_cents >= 0),
    unit TEXT NOT NULL CHECK (unit IN ('night', 'day', 'trip', 'item')),
    currency TEXT NOT NULL DEFAULT 'CNY' CHECK (currency = 'CNY'),
    effective_from TEXT NOT NULL CHECK (length(effective_from) = 10),
    effective_to TEXT CHECK (effective_to IS NULL OR (length(effective_to) = 10 AND effective_to >= effective_from)),
    source_document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    source_version INTEGER NOT NULL CHECK (source_version >= 1),
    source_clause TEXT NOT NULL CHECK (length(trim(source_clause)) BETWEEN 1 AND 200),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    updated_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    UNIQUE (city_code, grade_code, expense_type_code, effective_from)
);
CREATE INDEX IF NOT EXISTS idx_reimbursement_standards_query
    ON reimbursement_standards(expense_type_code, city_code, grade_code, effective_from, effective_to);

-- 11. 审批流程节点 approval_flows
CREATE TABLE IF NOT EXISTS approval_flows (
    id INTEGER PRIMARY KEY,
    flow_code TEXT NOT NULL CHECK (length(trim(flow_code)) BETWEEN 1 AND 40),
    flow_name TEXT NOT NULL CHECK (length(trim(flow_name)) BETWEEN 1 AND 100),
    expense_type_code TEXT NOT NULL CHECK (length(trim(expense_type_code)) > 0),
    min_amount_cents INTEGER NOT NULL DEFAULT 0 CHECK (min_amount_cents >= 0),
    max_amount_cents INTEGER CHECK (max_amount_cents IS NULL OR max_amount_cents > min_amount_cents),
    step_no INTEGER NOT NULL CHECK (step_no > 0),
    approver_role TEXT NOT NULL CHECK (length(trim(approver_role)) BETWEEN 1 AND 50),
    condition_text TEXT NOT NULL DEFAULT '',
    is_required INTEGER NOT NULL DEFAULT 1 CHECK (is_required IN (0, 1)),
    effective_from TEXT NOT NULL CHECK (length(effective_from) = 10),
    effective_to TEXT CHECK (effective_to IS NULL OR (length(effective_to) = 10 AND effective_to >= effective_from)),
    source_document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    source_version INTEGER NOT NULL CHECK (source_version >= 1),
    source_clause TEXT NOT NULL CHECK (length(trim(source_clause)) BETWEEN 1 AND 200),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    updated_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    UNIQUE (flow_code, effective_from, step_no)
);
CREATE INDEX IF NOT EXISTS idx_approval_flows_query
    ON approval_flows(expense_type_code, effective_from, min_amount_cents);

-- 12. 特殊费用规则 special_expense_rules
CREATE TABLE IF NOT EXISTS special_expense_rules (
    id INTEGER PRIMARY KEY,
    scene_code TEXT NOT NULL CHECK (length(trim(scene_code)) > 0),
    keywords TEXT NOT NULL DEFAULT '',
    condition_text TEXT NOT NULL CHECK (length(trim(condition_text)) BETWEEN 1 AND 500),
    rule_text TEXT NOT NULL CHECK (length(trim(rule_text)) BETWEEN 1 AND 3000),
    is_allowed INTEGER CHECK (is_allowed IS NULL OR is_allowed IN (0, 1)),
    required_materials TEXT NOT NULL DEFAULT '',
    effective_from TEXT NOT NULL CHECK (length(effective_from) = 10),
    effective_to TEXT CHECK (effective_to IS NULL OR (length(effective_to) = 10 AND effective_to >= effective_from)),
    source_document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    source_version INTEGER NOT NULL CHECK (source_version >= 1),
    source_clause TEXT NOT NULL CHECK (length(trim(source_clause)) BETWEEN 1 AND 200),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    updated_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours'))
);
CREATE INDEX IF NOT EXISTS idx_special_expense_rules_query
    ON special_expense_rules(scene_code, is_active, effective_from, effective_to);

-- 13. 常见问题 faq
CREATE TABLE IF NOT EXISTS faq (
    id INTEGER PRIMARY KEY,
    question TEXT NOT NULL CHECK (length(trim(question)) BETWEEN 1 AND 500),
    normalized_question TEXT NOT NULL UNIQUE CHECK (length(trim(normalized_question)) > 0),
    answer TEXT NOT NULL CHECK (length(trim(answer)) BETWEEN 1 AND 3000),
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    source_document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    source_version INTEGER NOT NULL CHECK (source_version >= 1),
    source_clause TEXT NOT NULL CHECK (length(trim(source_clause)) BETWEEN 1 AND 200),
    hit_count INTEGER NOT NULL DEFAULT 0 CHECK (hit_count >= 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    updated_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours'))
);
CREATE INDEX IF NOT EXISTS idx_faq_category_active
    ON faq(category_id, is_active);

-- 14. 聊天会话 conversations
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title TEXT NOT NULL DEFAULT '新会话' CHECK (length(trim(title)) BETWEEN 1 AND 50),
    summary TEXT,
    summary_until_message_id INTEGER REFERENCES messages(id) ON DELETE RESTRICT,
    context_document_id INTEGER REFERENCES documents(id) ON DELETE RESTRICT,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours'))
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_del_updated
    ON conversations(user_id, is_deleted, updated_at DESC);

-- 15. 会话消息 messages
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL DEFAULT '' CHECK (
        role = 'assistant' OR (length(trim(content)) BETWEEN 1 AND 500)
    ),
    status TEXT NOT NULL CHECK (status IN ('completed', 'generating', 'interrupted', 'failed')),
    request_id TEXT NOT NULL CHECK (length(trim(request_id)) > 0),
    reply_to_message_id INTEGER REFERENCES messages(id) ON DELETE RESTRICT,
    citations_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(citations_json) AND json_type(citations_json) = 'array'),
    used_tools_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(used_tools_json) AND json_type(used_tools_json) = 'array'),
    error_code TEXT,
    token_count INTEGER NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    CHECK (role = 'user' OR reply_to_message_id IS NOT NULL),
    UNIQUE (conversation_id, request_id, role)
);
CREATE INDEX IF NOT EXISTS idx_messages_conv_id_desc
    ON messages(conversation_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_messages_reply_to
    ON messages(reply_to_message_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_messages_conv_generating
    ON messages(conversation_id) WHERE role = 'assistant' AND status = 'generating';

-- 16. 问答日志 qa_logs
CREATE TABLE IF NOT EXISTS qa_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE RESTRICT,
    assistant_message_id INTEGER NOT NULL UNIQUE REFERENCES messages(id) ON DELETE RESTRICT,
    question TEXT NOT NULL CHECK (length(trim(question)) BETWEEN 1 AND 500),
    rewritten_query TEXT,
    hit_chunks_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(hit_chunks_json) AND json_type(hit_chunks_json) = 'array'),
    top_score REAL CHECK (top_score IS NULL OR (top_score >= 0.0 AND top_score <= 1.0)),
    used_tools_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(used_tools_json) AND json_type(used_tools_json) = 'array'),
    answer_type TEXT NOT NULL CHECK (answer_type IN ('faq', 'rag', 'structured', 'web', 'clarify', 'refusal', 'error')),
    is_refused INTEGER NOT NULL DEFAULT 0 CHECK (is_refused IN (0, 1)),
    latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
    first_token_ms INTEGER CHECK (first_token_ms IS NULL OR first_token_ms >= 0),
    knowledge_supplemented INTEGER NOT NULL DEFAULT 0 CHECK (knowledge_supplemented IN (0, 1)),
    supplemented_by INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    supplemented_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours'))
);
CREATE INDEX IF NOT EXISTS idx_qa_logs_created_user_refused
    ON qa_logs(created_at, user_id, is_refused);
CREATE INDEX IF NOT EXISTS idx_qa_logs_answer_type_created
    ON qa_logs(answer_type, created_at);

-- 17. 浏览历史 browse_history
CREATE TABLE IF NOT EXISTS browse_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    last_viewed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours')),
    view_count INTEGER NOT NULL DEFAULT 1 CHECK (view_count >= 1),
    UNIQUE (user_id, document_id)
);
CREATE INDEX IF NOT EXISTS idx_browse_history_user_viewed
    ON browse_history(user_id, last_viewed_at DESC);

-- 18. 审计日志 audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY,
    actor_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    action TEXT NOT NULL CHECK (length(trim(action)) > 0),
    target_type TEXT NOT NULL CHECK (length(trim(target_type)) BETWEEN 1 AND 40),
    target_id TEXT,
    request_id TEXT NOT NULL CHECK (length(trim(request_id)) > 0),
    result TEXT NOT NULL CHECK (result IN ('success', 'failure')),
    detail_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(detail_json) AND json_type(detail_json) = 'object'),
    client_ip TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', '+8 hours'))
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_action
    ON audit_logs(created_at, action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_created
    ON audit_logs(actor_user_id, created_at);

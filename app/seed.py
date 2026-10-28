from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from typing import Any

import bcrypt
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import BASE_DIR, shanghai_now_str
from app.database import SessionLocal

DEFAULT_TEMP_ADMIN_PASSWORD = "admin123"


def normalize_question(question: str) -> str:
    """
    问题规范化规则：
    1. Unicode NFKC 规范化（含全角转半角）
    2. 额外全角字符转半角兜底
    3. 去除全部标点符号（Unicode P 类标点与常见符号）
    4. 英文统一转小写
    5. 去首尾空白并将连续空白合并为单个空格
    """
    text_val = unicodedata.normalize("NFKC", question or "")
    halfwidth_chars: list[str] = []
    for ch in text_val:
        code = ord(ch)
        if code == 0x3000:
            halfwidth_chars.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            halfwidth_chars.append(chr(code - 0xFEE0))
        else:
            halfwidth_chars.append(ch)
    text_val = "".join(halfwidth_chars).lower()

    no_punct_chars = [
        ch for ch in text_val if not unicodedata.category(ch).startswith("P")
    ]
    text_val = "".join(no_punct_chars)
    text_val = re.sub(r"\s+", " ", text_val).strip()
    if not text_val:
        raise ValueError("规范化后的问题不能为空")
    return text_val


def _collect_table_counts(session: Session) -> dict[str, int]:
    mapping = {
        "departments": "departments",
        "dict_items": "dict_items",
        "users": "users",
        "categories": "categories",
        "documents": "documents",
        "standards": "reimbursement_standards",
        "flows": "approval_flows",
        "special": "special_expense_rules",
        "faq": "faq",
        "sync_jobs": "sync_jobs",
        "chunks": "document_chunks",
        "conversations": "conversations",
        "messages": "messages",
        "qa_logs": "qa_logs",
        "browse_history": "browse_history",
    }
    counts: dict[str, int] = {}
    for alias, table_name in mapping.items():
        cnt = session.execute(text(f"SELECT count(*) FROM {table_name}")).scalar()
        counts[alias] = int(cnt or 0)
    return counts


def seed_db() -> dict[str, Any]:
    """
    在空库上执行一次性示例数据初始化（非真实企业制度）。
    若发现已有业务数据则立即停止，不重复插入。
    """
    admin_password = os.getenv("ADMIN_PASSWORD") or DEFAULT_TEMP_ADMIN_PASSWORD
    using_temp_password = not bool(os.getenv("ADMIN_PASSWORD"))

    now_str = shanghai_now_str()

    with SessionLocal() as session:
        session.execute(text("PRAGMA foreign_keys = ON"))

        check_tables = (
            "departments",
            "dict_items",
            "users",
            "categories",
            "documents",
            "reimbursement_standards",
            "approval_flows",
            "special_expense_rules",
            "faq",
            "sync_jobs",
        )
        existing_non_empty: dict[str, int] = {}
        for tbl in check_tables:
            cnt = int(session.execute(text(f"SELECT count(*) FROM {tbl}")).scalar() or 0)
            if cnt > 0:
                existing_non_empty[tbl] = cnt

        if existing_non_empty:
            counts = _collect_table_counts(session)
            print(f"[seed] 检测到数据库非空 {existing_non_empty}，跳过初始化，不重复插入。")
            return {
                "seeded": False,
                "reason": "database_not_empty",
                "counts": counts,
            }

        # 1. departments：财务部(10)、人事部(20)、技术部(30)
        departments_data = [
            {"name": "财务部", "sort_order": 10, "is_active": 1, "created_at": now_str, "updated_at": now_str},
            {"name": "人事部", "sort_order": 20, "is_active": 1, "created_at": now_str, "updated_at": now_str},
            {"name": "技术部", "sort_order": 30, "is_active": 1, "created_at": now_str, "updated_at": now_str},
        ]
        for dept in departments_data:
            session.execute(
                text(
                    "INSERT INTO departments (name, sort_order, is_active, created_at, updated_at) "
                    "VALUES (:name, :sort_order, :is_active, :created_at, :updated_at)"
                ),
                dept,
            )

        # 2. dict_items：8 项，label 一律中文，不把 * 登记为字典项
        dict_items_data = [
            {"dict_type": "city", "code": "SHANGHAI", "label": "上海", "sort_order": 10},
            {"dict_type": "city", "code": "BEIJING", "label": "北京", "sort_order": 20},
            {"dict_type": "grade", "code": "P5", "label": "五级专员", "sort_order": 10},
            {"dict_type": "grade", "code": "P6", "label": "六级主管", "sort_order": 20},
            {"dict_type": "expense_type", "code": "HOTEL", "label": "住宿", "sort_order": 10},
            {"dict_type": "expense_type", "code": "MEAL_ALLOWANCE", "label": "餐补", "sort_order": 20},
            {"dict_type": "scene", "code": "OVER_STANDARD", "label": "超标准", "sort_order": 10},
            {"dict_type": "scene", "code": "LOST_RECEIPT", "label": "票据丢失", "sort_order": 20},
        ]
        for item in dict_items_data:
            session.execute(
                text(
                    "INSERT INTO dict_items (dict_type, code, label, sort_order, is_active, created_at, updated_at) "
                    "VALUES (:dict_type, :code, :label, :sort_order, 1, :created_at, :updated_at)"
                ),
                {**item, "created_at": now_str, "updated_at": now_str},
            )

        # 3. users：仅 1 个 admin，bcrypt 现算哈希，must_change_password=1
        password_hash = bcrypt.hashpw(
            admin_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        session.execute(
            text(
                "INSERT INTO users ("
                "username, password_hash, display_name, department_id, role, "
                "is_active, failed_login_count, locked_until, must_change_password, created_at, updated_at"
                ") VALUES ("
                ":username, :password_hash, :display_name, :department_id, :role, "
                "1, 0, NULL, 1, :created_at, :updated_at"
                ")"
            ),
            {
                "username": "admin",
                "password_hash": password_hash,
                "display_name": "系统管理员",
                "department_id": None,
                "role": "admin",
                "created_at": now_str,
                "updated_at": now_str,
            },
        )
        admin_id = int(
            session.execute(
                text("SELECT id FROM users WHERE username = 'admin'")
            ).scalar_one()
        )

        # 4. categories：差旅报销、票据规范
        categories_data = [
            {"name": "差旅报销", "sort_order": 10},
            {"name": "票据规范", "sort_order": 20},
        ]
        for cat in categories_data:
            session.execute(
                text(
                    "INSERT INTO categories (name, sort_order, created_at, updated_at) "
                    "VALUES (:name, :sort_order, :created_at, :updated_at)"
                ),
                {**cat, "created_at": now_str, "updated_at": now_str},
            )
        cat_travel_id = int(
            session.execute(
                text("SELECT id FROM categories WHERE name = '差旅报销'")
            ).scalar_one()
        )
        cat_receipt_id = int(
            session.execute(
                text("SELECT id FROM categories WHERE name = '票据规范'")
            ).scalar_one()
        )

        # 5. documents：2 篇示例制度文档（存元数据 file_path + file_hash，正文在 knowledge_base/ 文件中）
        documents_data = [
            {
                "category_id": cat_travel_id,
                "title": "差旅费用报销管理办法（示例制度）",
                "file_path": "knowledge_base/travel-expense-reimbursement.md",
                "version": 1,
            },
            {
                "category_id": cat_receipt_id,
                "title": "报销票据与凭证管理规范（示例制度）",
                "file_path": "knowledge_base/receipt-management.md",
                "version": 1,
            },
        ]
        doc_ids: list[int] = []
        for doc in documents_data:
            md_file = (BASE_DIR / doc["file_path"]).resolve()
            if not md_file.is_file():
                raise FileNotFoundError(f"知识库示例文档文件不存在: {doc['file_path']}")
            file_bytes = md_file.read_bytes()
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            session.execute(
                text(
                    "INSERT INTO documents ("
                    "category_id, title, file_path, file_hash, attachment_file_id, cover_file_id, "
                    "publish_status, version, active_vector_version, sync_status, sync_error, "
                    "is_deleted, created_by, updated_by, created_at, updated_at"
                    ") VALUES ("
                    ":category_id, :title, :file_path, :file_hash, NULL, NULL, "
                    "'published', :version, NULL, 'pending', NULL, "
                    "0, :admin_id, :admin_id, :created_at, :updated_at"
                    ")"
                ),
                {
                    **doc,
                    "file_hash": file_hash,
                    "admin_id": admin_id,
                    "created_at": now_str,
                    "updated_at": now_str,
                },
            )
            doc_id = int(
                session.execute(
                    text("SELECT id FROM documents WHERE title = :title"),
                    {"title": doc["title"]},
                ).scalar_one()
            )
            doc_ids.append(doc_id)

            # 6. sync_jobs：每篇文档插入一条 rebuild 任务，不插假分块
            session.execute(
                text(
                    "INSERT INTO sync_jobs ("
                    "document_id, target_version, action, status, attempts, "
                    "next_retry_at, lease_until, last_error, started_at, finished_at, created_at, updated_at"
                    ") VALUES ("
                    ":document_id, :target_version, 'rebuild', 'pending', 0, "
                    "NULL, NULL, NULL, NULL, NULL, :created_at, :updated_at"
                    ")"
                ),
                {
                    "document_id": doc_id,
                    "target_version": doc["version"],
                    "created_at": now_str,
                    "updated_at": now_str,
                },
            )

        travel_doc_id, receipt_doc_id = doc_ids[0], doc_ids[1]

        # 7. reimbursement_standards：2 条（整数分存储）
        standards_data = [
            {
                "city_code": "SHANGHAI",
                "grade_code": "P5",
                "expense_type_code": "HOTEL",
                "amount_limit_cents": 80000,
                "unit": "night",
                "currency": "CNY",
                "effective_from": "2026-01-01",
                "effective_to": None,
                "source_document_id": travel_doc_id,
                "source_version": 1,
                "source_clause": "第三章 第八条",
                "is_active": 1,
                "updated_by": admin_id,
                "created_at": now_str,
                "updated_at": now_str,
            },
            {
                "city_code": "*",
                "grade_code": "P5",
                "expense_type_code": "MEAL_ALLOWANCE",
                "amount_limit_cents": 12000,
                "unit": "day",
                "currency": "CNY",
                "effective_from": "2026-01-01",
                "effective_to": None,
                "source_document_id": travel_doc_id,
                "source_version": 1,
                "source_clause": "第三章 第十条",
                "is_active": 1,
                "updated_by": admin_id,
                "created_at": now_str,
                "updated_at": now_str,
            },
        ]
        for std in standards_data:
            session.execute(
                text(
                    "INSERT INTO reimbursement_standards ("
                    "city_code, grade_code, expense_type_code, amount_limit_cents, unit, currency, "
                    "effective_from, effective_to, source_document_id, source_version, source_clause, "
                    "is_active, updated_by, created_at, updated_at"
                    ") VALUES ("
                    ":city_code, :grade_code, :expense_type_code, :amount_limit_cents, :unit, :currency, "
                    ":effective_from, :effective_to, :source_document_id, :source_version, :source_clause, "
                    ":is_active, :updated_by, :created_at, :updated_at"
                    ")"
                ),
                std,
            )

        # 8. approval_flows：1 组 2 个节点（step_no 1=直属主管，2=财务专员）
        flows_data = [
            {
                "flow_code": "TRAVEL_HOTEL",
                "flow_name": "差旅住宿审批",
                "expense_type_code": "HOTEL",
                "min_amount_cents": 0,
                "max_amount_cents": None,
                "step_no": 1,
                "approver_role": "直属主管",
                "condition_text": "",
                "is_required": 1,
                "effective_from": "2026-01-01",
                "effective_to": None,
                "source_document_id": travel_doc_id,
                "source_version": 1,
                "source_clause": "第四章 第十二条",
                "is_active": 1,
                "updated_by": admin_id,
                "created_at": now_str,
                "updated_at": now_str,
            },
            {
                "flow_code": "TRAVEL_HOTEL",
                "flow_name": "差旅住宿审批",
                "expense_type_code": "HOTEL",
                "min_amount_cents": 0,
                "max_amount_cents": None,
                "step_no": 2,
                "approver_role": "财务专员",
                "condition_text": "",
                "is_required": 1,
                "effective_from": "2026-01-01",
                "effective_to": None,
                "source_document_id": travel_doc_id,
                "source_version": 1,
                "source_clause": "第四章 第十二条",
                "is_active": 1,
                "updated_by": admin_id,
                "created_at": now_str,
                "updated_at": now_str,
            },
        ]
        for flow_node in flows_data:
            session.execute(
                text(
                    "INSERT INTO approval_flows ("
                    "flow_code, flow_name, expense_type_code, min_amount_cents, max_amount_cents, "
                    "step_no, approver_role, condition_text, is_required, effective_from, effective_to, "
                    "source_document_id, source_version, source_clause, is_active, updated_by, created_at, updated_at"
                    ") VALUES ("
                    ":flow_code, :flow_name, :expense_type_code, :min_amount_cents, :max_amount_cents, "
                    ":step_no, :approver_role, :condition_text, :is_required, :effective_from, :effective_to, "
                    ":source_document_id, :source_version, :source_clause, :is_active, :updated_by, :created_at, :updated_at"
                    ")"
                ),
                flow_node,
            )

        # 9. special_expense_rules：1 条（OVER_STANDARD）
        session.execute(
            text(
                "INSERT INTO special_expense_rules ("
                "scene_code, keywords, condition_text, rule_text, is_allowed, required_materials, "
                "effective_from, effective_to, source_document_id, source_version, source_clause, "
                "is_active, updated_by, created_at, updated_at"
                ") VALUES ("
                ":scene_code, :keywords, :condition_text, :rule_text, :is_allowed, :required_materials, "
                ":effective_from, :effective_to, :source_document_id, :source_version, :source_clause, "
                ":is_active, :updated_by, :created_at, :updated_at"
                ")"
            ),
            {
                "scene_code": "OVER_STANDARD",
                "keywords": "超标准",
                "condition_text": "因旺季展会或紧急公务无法预订标准限额内酒店且经部门主管事前同意",
                "rule_text": "在标准限额上浮20%以内据实报销，超出部分由个人承担，报销时须随单附情况说明。",
                "is_allowed": 1,
                "required_materials": "情况说明",
                "effective_from": "2026-01-01",
                "effective_to": None,
                "source_document_id": travel_doc_id,
                "source_version": 1,
                "source_clause": "第五章 第十五条",
                "is_active": 1,
                "updated_by": admin_id,
                "created_at": now_str,
                "updated_at": now_str,
            },
        )

        # 10. faq：2 条
        faqs_data = [
            {
                "question": "P5员工去上海出差住宿标准是多少？",
                "answer": "根据《差旅费用报销管理办法（示例制度）》第三章第八条，五级专员（P5）赴上海出差住宿费标准上限为每晚 800.00 元。",
                "category_id": cat_travel_id,
                "source_document_id": travel_doc_id,
                "source_version": 1,
                "source_clause": "第三章 第八条",
            },
            {
                "question": "报销电子发票有什么要求？",
                "answer": "根据《报销票据与凭证管理规范（示例制度）》第二章第六条，报销增值税电子发票须填写完整公司名称及纳税人识别号，上传电子发票原件并确保未重复报销。",
                "category_id": cat_receipt_id,
                "source_document_id": receipt_doc_id,
                "source_version": 1,
                "source_clause": "第二章 第六条",
            },
        ]
        for faq_row in faqs_data:
            norm_q = normalize_question(faq_row["question"])
            session.execute(
                text(
                    "INSERT INTO faq ("
                    "question, normalized_question, answer, category_id, "
                    "source_document_id, source_version, source_clause, "
                    "hit_count, is_active, updated_by, created_at, updated_at"
                    ") VALUES ("
                    ":question, :normalized_question, :answer, :category_id, "
                    ":source_document_id, :source_version, :source_clause, "
                    "0, 1, :updated_by, :created_at, :updated_at"
                    ")"
                ),
                {
                    **faq_row,
                    "normalized_question": norm_q,
                    "updated_by": admin_id,
                    "created_at": now_str,
                    "updated_at": now_str,
                },
            )

        session.commit()
        counts = _collect_table_counts(session)

    if using_temp_password:
        print(
            "[seed] 未设置环境变量 ADMIN_PASSWORD，已使用本地测试临时密码初始化 admin 账号；"
            "提醒：第一次登录必须改密码（must_change_password=1）。"
        )
    else:
        print(
            "[seed] 已使用环境变量 ADMIN_PASSWORD 初始化 admin 账号；"
            "提醒：第一次登录必须改密码（must_change_password=1）。"
        )

    summary_str = ", ".join(f"{k}={v}" for k, v in counts.items())
    print(f"[seed] 各表行数: {summary_str}")

    return {
        "seeded": True,
        "must_change_password": 1,
        "counts": counts,
    }


if __name__ == "__main__":
    seed_db()

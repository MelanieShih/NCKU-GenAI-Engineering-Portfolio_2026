import argparse
import csv
import json
import os
import shutil
import sqlite3
import sys
from abc import ABC, abstractmethod
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from rich import print as rprint
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table


# --- 系統常數與資料檔路徑 ---
DB_FILE = os.path.join(os.path.dirname(__file__), "tickets.db")
JSON_DATA_FILE = os.path.join(os.path.dirname(__file__), "tickets.json")

# 狀態、故障類型與優先級的標準化定義
STATUSES = {"open", "in_progress", "closed"}
FAILURE_TYPES = {"mechanical", "electrical", "sensor", "quality", "other"}
PRIORITIES = {"low", "medium", "high"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
FAILURE_ORDER = ["mechanical", "electrical", "sensor", "quality", "other"]


def now_str() -> str:
    """回傳一致格式的目前系統時間字串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fail(msg: str, code: int = 1) -> None:
    """輸出錯誤訊息到標準錯誤並以非 0 狀態結束程式"""
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def validate_choice(value, allowed, name: str) -> None:
    """驗證輸入值是否屬於允許的列舉選項"""
    if value is not None and value not in allowed:
        fail(f"invalid {name} '{value}'", 2)


def validate_non_negative(value, name: str) -> None:
    """驗證數值欄位是否為非負數"""
    if value is not None and value < 0:
        fail(f"{name} must be >= 0", 2)


def parse_date(date_str: str) -> datetime:
    """解析 YYYY-MM-DD 日期格式，供 summary 條件查詢使用"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        fail("date format must be YYYY-MM-DD", 2)


def safe_parse_timestamp(value: str) -> Optional[datetime]:
    """解析舊版或新版資料中的日期時間字串。"""
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


class Ticket:
    """工廠維修工單的資料樣式"""

    def __init__(self, **kw):
        self.id = kw.get("id")
        self.machine_id = kw.get("machine_id")
        self.line_id = kw.get("line_id")
        self.issue = kw.get("issue", "")
        self.failure_type = kw.get("failure_type", "other")
        self.priority = kw.get("priority", "low")
        self.status = kw.get("status", "open")
        self.downtime_minutes = kw.get("downtime_minutes", 0)
        self.created_at = kw.get("created_at", now_str())
        self.updated_at = kw.get("updated_at", self.created_at)
        # 保留 v1 的欄位名稱 resolution，以維持向下相容
        self.resolution = kw.get("resolution", "")
        # v2 新增的結案專用欄位
        self.actual_repair_minutes = kw.get("actual_repair_minutes")
        self.closed_at = kw.get("closed_at")

        # metadata 可能來自 SQLite 字串或 Python dict，需做相容處理
        raw_meta = kw.get("metadata", {"notes": []})
        if isinstance(raw_meta, str):
            try:
                self.metadata = json.loads(raw_meta) if raw_meta else {"notes": []}
            except json.JSONDecodeError:
                self.metadata = {"notes": []}
        else:
            self.metadata = raw_meta or {"notes": []}
        self.metadata.setdefault("notes", [])

    def to_db_dict(self, include_id: bool = False) -> Dict:
        """將工單物件轉為可寫入資料庫的字典格式"""
        data = {
            "machine_id": self.machine_id,
            "line_id": self.line_id,
            "issue": self.issue,
            "failure_type": self.failure_type,
            "priority": self.priority,
            "status": self.status,
            "downtime_minutes": self.downtime_minutes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolution": self.resolution,
            "actual_repair_minutes": self.actual_repair_minutes,
            "closed_at": self.closed_at,
            "metadata": json.dumps(self.metadata, ensure_ascii=False),
        }
        if include_id and self.id is not None:
            data["id"] = self.id
        return data


class BaseStorage(ABC):
    """資料存取抽象介面，讓服務層不綁定特定儲存實作"""

    @abstractmethod
    def list_all(self) -> List[Ticket]:
        pass

    @abstractmethod
    def get_by_id(self, tid: int) -> Optional[Ticket]:
        pass

    @abstractmethod
    def add(self, ticket: Ticket) -> int:
        pass

    @abstractmethod
    def update(self, tid: int, updates: Dict) -> bool:
        pass

    @abstractmethod
    def delete(self, tid: int) -> bool:
        pass


class SqliteStorage(BaseStorage):
    """以 SQLite 為基礎的工單儲存層，適合輕量化工廠環境"""

    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _column_names(self) -> set:
        rows = self.conn.execute("PRAGMA table_info(tickets)").fetchall()
        return {row[1] for row in rows}

    def _init_db(self) -> None:
        """建立資料表，並對舊版欄位做輕量升級"""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                line_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                failure_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                downtime_minutes INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolution TEXT NOT NULL DEFAULT '',
                actual_repair_minutes INTEGER,
                closed_at TEXT,
                metadata TEXT NOT NULL DEFAULT '{"notes": []}'
            )
            """
        )
        self.conn.commit()

        # 若資料庫來自舊版，這裡會自動補上 v2 需要的新欄位
        columns = self._column_names()
        migrations = {
            "resolution": "ALTER TABLE tickets ADD COLUMN resolution TEXT NOT NULL DEFAULT ''",
            "actual_repair_minutes": "ALTER TABLE tickets ADD COLUMN actual_repair_minutes INTEGER",
            "closed_at": "ALTER TABLE tickets ADD COLUMN closed_at TEXT",
            "metadata": "ALTER TABLE tickets ADD COLUMN metadata TEXT NOT NULL DEFAULT '{\"notes\": []}'",
        }
        for col, sql in migrations.items():
            if col not in columns:
                self.conn.execute(sql)
        self.conn.commit()

    def list_all(self) -> List[Ticket]:
        rows = self.conn.execute("SELECT * FROM tickets ORDER BY id ASC").fetchall()
        return [Ticket(**dict(row)) for row in rows]

    def get_by_id(self, tid: int) -> Optional[Ticket]:
        row = self.conn.execute("SELECT * FROM tickets WHERE id = ?", (tid,)).fetchone()
        return Ticket(**dict(row)) if row else None

    def add(self, ticket: Ticket) -> int:
        """新增工單並回傳資料庫配置的工單 ID"""
        data = ticket.to_db_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        cur = self.conn.execute(
            f"INSERT INTO tickets ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def import_ticket_preserve_id(self, ticket: Ticket) -> int:
        """匯入舊版工單資料並保留原始工單 ID"""
        data = ticket.to_db_dict(include_id=True)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        self.conn.execute(
            f"INSERT OR REPLACE INTO tickets ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        self.conn.commit()
        return int(ticket.id)

    def count_all(self) -> int:
        """回傳目前資料庫中的工單總數"""
        row = self.conn.execute("SELECT COUNT(*) AS c FROM tickets").fetchone()
        return int(row["c"])

    def update(self, tid: int, updates: Dict) -> bool:
        if not updates:
            return False
        updates = dict(updates)
        if "metadata" in updates:
            updates["metadata"] = json.dumps(updates["metadata"], ensure_ascii=False)
        updates["updated_at"] = now_str()
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        cur = self.conn.execute(
            f"UPDATE tickets SET {set_clause} WHERE id = ?",
            list(updates.values()) + [tid],
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, tid: int) -> bool:
        cur = self.conn.execute("DELETE FROM tickets WHERE id = ?", (tid,))
        self.conn.commit()
        return cur.rowcount > 0


class TicketService:
    """工單生命週期、統計分析、搜尋與匯出的業務邏輯層"""

    def __init__(self, storage: BaseStorage):
        self.storage = storage

    def create_ticket(self, **kw) -> int:
        """驗證業務規則後建立新工單"""
        validate_choice(kw.get("failure_type"), FAILURE_TYPES, "failure type")
        validate_choice(kw.get("priority"), PRIORITIES, "priority")
        validate_non_negative(kw.get("downtime_minutes"), "downtime")
        ticket = Ticket(**kw)
        return self.storage.add(ticket)

    def list_tickets(self, filters: Dict, sort_by: str) -> List[Ticket]:
        """以記憶體中的過濾與排序邏輯列出工單"""
        tickets = self.storage.list_all()
        for field, value in filters.items():
            if value is not None:
                tickets = [t for t in tickets if getattr(t, field, None) == value]

        if sort_by == "priority":
            tickets.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 9), t.id))
        elif sort_by == "downtime":
            tickets.sort(key=lambda t: (-t.downtime_minutes, t.id))
        elif sort_by in {"id", "machine_id", "line_id", "status", "failure_type", "created_at"}:
            tickets.sort(key=lambda t: (getattr(t, sort_by, None), t.id))
        else:
            fail(f"unsupported sort field '{sort_by}'", 2)
        return tickets

    def update_ticket(self, tid: int, **updates) -> bool:
        """更新工單，並在結案時強制檢查 v2 必填欄位"""
        validate_choice(updates.get("status"), STATUSES, "status")
        validate_choice(updates.get("priority"), PRIORITIES, "priority")
        validate_non_negative(updates.get("downtime_minutes"), "downtime")
        validate_non_negative(updates.get("actual_repair_minutes"), "actual repair minutes")

        current = self.storage.get_by_id(tid)
        if not current:
            return False

        new_status = updates.get("status")
        # 結案被視為獨立業務動作，必須補齊實際維修時間與結案描述
        if new_status == "closed":
            missing = []
            if updates.get("actual_repair_minutes") is None:
                missing.append("actual_repair_minutes")
            resolution_value = updates.get("resolution")
            if resolution_value is None or str(resolution_value).strip() == "":
                missing.append("resolution")
            if missing:
                fail("closing a ticket requires: " + ", ".join(missing), 2)
            updates["closed_at"] = now_str()

        return self.storage.update(tid, updates)

    def search_tickets(self, keyword: str) -> List[Dict]:
        """
        搜尋工單並回傳命中的欄位與內容摘要。
        """
        kw = keyword.lower().strip()
        results = []

        for t in self.storage.list_all():
            # 以下內容必須縮排在 for 迴圈內 (比 for 往右縮進 4 個空白)
            notes = t.metadata.get("notes", [])

            field_candidates = [
                ("問題描述", t.issue or ""),
                ("設備 ID", t.machine_id or ""),
                ("產線", t.line_id or ""),
                ("故障類型", t.failure_type or ""),
                ("結案描述", t.resolution or ""),
            ]

            matched_in = None
            matched_text = None

            # 檢查一般欄位
            for field_name, value in field_candidates:
                if kw in value.lower():
                    matched_in = field_name
                    matched_text = value
                    break

            # 一般欄位沒命中，再檢查備註
            if matched_in is None:
                for note in notes:
                    if kw in note.lower():
                        matched_in = "備註"
                        matched_text = note
                        break

            # 只要有命中，就新增到結果清單
            if matched_in is not None:
                results.append({
                    "ticket": t,
                    "matched_in": matched_in,
                    "matched_text": matched_text,
                })

        return results

    def _filter_by_line_and_date(
        self,
        tickets: List[Ticket],
        line_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Ticket]:
        """依產線與建立日期區間套用 summary 過濾條件"""
        if line_id:
            tickets = [t for t in tickets if t.line_id == line_id]

        if start_date or end_date:
            start_dt = parse_date(start_date) if start_date else datetime.min
            end_dt = parse_date(end_date) if end_date else datetime.max
            if end_dt < start_dt:
                fail("end_date cannot be earlier than start_date", 2)
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

            filtered = []
            for t in tickets:
                created_dt = safe_parse_timestamp(t.created_at)
                if created_dt and start_dt <= created_dt <= end_dt:
                    filtered.append(t)
            tickets = filtered

        return tickets

    def get_summary(
        self,
        line_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict:
        """建立帶條件的摘要統計，供生管或管理者查看"""
        tickets = self._filter_by_line_and_date(self.storage.list_all(), line_id, start_date, end_date)
        return {
            "total": len(tickets),
            "open": sum(1 for t in tickets if t.status == "open"),
            "in_progress": sum(1 for t in tickets if t.status == "in_progress"),
            "closed": sum(1 for t in tickets if t.status == "closed"),
            "total_downtime": sum(t.downtime_minutes for t in tickets),
            "by_type": {ft: sum(1 for tk in tickets if tk.failure_type == ft) for ft in FAILURE_ORDER},
            "query_label": build_query_label(line_id, start_date, end_date),
        }

    def add_note(self, tid: int, text: str) -> bool:
        """將備註附加到工單的維修日誌中"""
        ticket = self.storage.get_by_id(tid)
        if not ticket:
            return False
        ticket.metadata.setdefault("notes", [])
        ticket.metadata["notes"].append(f"{now_str()} | {text}")
        return self.storage.update(tid, {"metadata": ticket.metadata})

    def machine_recent_failure_count(self, machine_id: str, days: int = 90) -> int:
        """統計單一設備在指定近期區間內的工單數量"""
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        for t in self.storage.list_all():
            if t.machine_id != machine_id:
                continue
            created_dt = safe_parse_timestamp(t.created_at)
            if created_dt and created_dt >= cutoff:
                count += 1
        return count

    def recommend_tickets(self) -> List[Dict]:
        """依優先級、停機時間與近期故障頻率排序待處理工單"""
        tickets = [t for t in self.storage.list_all() if t.status != "closed"]
        priority_score = {"high": 100, "medium": 60, "low": 30}
        recs = []
        for t in tickets:
            recent_count = self.machine_recent_failure_count(t.machine_id, 90)
            # 推薦分數 = 優先級分數 + 停機影響 + 近期故障頻率加權
            score = priority_score.get(t.priority, 0) + min(t.downtime_minutes, 60) + (recent_count * 15)
            recs.append({
                "ticket": t,
                "score": score,
                "recent_failure_count": recent_count,
            })
        recs.sort(key=lambda x: (-x["score"], x["ticket"].id))
        return recs

    def get_machine_report(self, machine_id: str) -> Optional[Dict]:
        """彙整單一設備的維修歷史與工單資訊"""
        tickets = [t for t in self.storage.list_all() if t.machine_id == machine_id]
        if not tickets:
            return None

        status_counts = {status: sum(1 for t in tickets if t.status == status) for status in sorted(STATUSES)}
        type_counter = Counter(t.failure_type for t in tickets)
        common_type = type_counter.most_common(1)[0][0] if type_counter else "other"

        return {
            "machine_id": machine_id,
            "total": len(tickets),
            "status_counts": status_counts,
            "total_downtime": sum(t.downtime_minutes for t in tickets),
            "most_common_failure_type": common_type,
            "recent_90_days": self.machine_recent_failure_count(machine_id, 90),
        }

    def export_tickets(self, status: Optional[str] = None, line_id: Optional[str] = None) -> Optional[Dict]:
        """將符合條件的工單匯出為 CSV，並回傳檔案資訊"""
        tickets = self.list_tickets({"status": status, "line_id": line_id}, "id")
        if not tickets:
            return None

        filename = f"tickets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = os.path.abspath(filename)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id",
                "machine_id",
                "line_id",
                "issue",
                "failure_type",
                "priority",
                "status",
                "downtime_minutes",
                "created_at",
                "updated_at",
                "actual_repair_minutes",
                "resolution",
                "closed_at",
                "notes",
            ])
            for t in tickets:
                notes = "\n".join(t.metadata.get("notes", []))
                writer.writerow([
                    t.id,
                    t.machine_id,
                    t.line_id,
                    t.issue,
                    t.failure_type,
                    t.priority,
                    t.status,
                    t.downtime_minutes,
                    t.created_at,
                    t.updated_at,
                    t.actual_repair_minutes if t.actual_repair_minutes is not None else "",
                    t.resolution,
                    t.closed_at or "",
                    notes,
                ])
        return {"path": path, "count": len(tickets)}


def build_query_label(line_id: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> str:
    """建立可讀性較高的 summary 查詢條件標籤"""
    parts = []
    if line_id:
        parts.append(f"{line_id} 產線")
    if start_date or end_date:
        parts.append(f"{start_date or '起始'} 至 {end_date or '結束'}")
    return " ｜ ".join(parts) if parts else "全部工單"


def print_ticket_table(tickets: List[Ticket]) -> None:
    """以表格方式顯示工單清單"""
    if not tickets:
        rprint("[yellow]INFO: No tickets found[/yellow]")
        return

    table = Table(title="[bold blue]工廠維護工單監控清單[/bold blue]", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=4)
    table.add_column("機器 ID", width=12)
    table.add_column("產線", width=8)
    table.add_column("狀態", width=12)
    table.add_column("優先級", width=10)
    table.add_column("停機(分)", justify="right")
    table.add_column("問題描述")

    for t in tickets:
        status_color = "green" if t.status == "closed" else ("cyan" if t.status == "in_progress" else "yellow")
        prio_color = "red" if t.priority == "high" else ("yellow" if t.priority == "medium" else "white")
        table.add_row(
            str(t.id),
            str(t.machine_id),
            str(t.line_id),
            f"[{status_color}]{t.status}[/{status_color}]",
            f"[{prio_color}]{t.priority}[/{prio_color}]",
            str(t.downtime_minutes),
            t.issue,
        )
        
    Console().print(table)
def print_search_table(results: List[Dict]) -> None:
    """
    顯示搜尋結果表格，額外標示命中來源，避免使用者誤以為系統找錯資料。
    """
    if not results:
        rprint("[yellow]INFO: No tickets found[/yellow]")
        return

    table = Table(
        title="[bold blue]工廠維護工單搜尋結果[/bold blue]",
        show_header=True,
        header_style="bold magenta"
    )

    table.add_column("ID", style="dim", width=4)
    table.add_column("機器 ID", width=10)
    table.add_column("產線", width=6)
    table.add_column("狀態", width=12)
    table.add_column("命中欄位", width=10, style="cyan")
    table.add_column("命中內容摘要", overflow="fold")

    for item in results:
        t = item["ticket"]
        matched_in = item["matched_in"]
        matched_text = item["matched_text"] or ""

        status_color = "green" if t.status == "closed" else ("cyan" if t.status == "in_progress" else "yellow")
        # 摘要處理：若文字過長則截斷，保持畫面整潔
        preview = matched_text if len(matched_text) <= 50 else matched_text[:50] + "..."

        table.add_row(
            str(t.id),
            str(t.machine_id),
            str(t.line_id),
            f"[{status_color}]{t.status}[/{status_color}]",
            matched_in,
            preview,
        )

    Console().print(table)

def print_summary_report(summary: Dict) -> None:
    """顯示帶有條件的摘要統計面板"""
    content = (
        f"查詢條件: [bold]{summary['query_label']}[/bold]\n"
        f"總工單數: [bold]{summary['total']}[/bold]\n"
        f"待處理 (Open): [yellow]{summary['open']}[/yellow] | "
        f"處理中 (In Progress): [cyan]{summary['in_progress']}[/cyan] | "
        f"已結案 (Closed): [green]{summary['closed']}[/green]\n"
        f"總停機時間: [red]{summary['total_downtime']}[/red] 分鐘\n"
        f"{'-' * 30}\n"
        "故障類型分布:\n"
    )
    for ft in FAILURE_ORDER:
        content += f" • {ft:<12}: {summary['by_type'].get(ft, 0)}\n"
    Console().print(Panel(content, title="[bold]工廠異常維護總結報告[/bold]", expand=False, border_style="blue"))


def print_detail(ticket: Ticket) -> None:
    """顯示工單完整內容，並將結案資訊與一般備註分開呈現"""
    notes = ticket.metadata.get("notes", [])
    notes_str = "\n".join([f"  • {n}" for n in notes]) if notes else "  (尚無維修備註)"

    detail_table = Table(box=None, show_header=False)
    detail_table.add_row("[bold]工單 ID  :[/bold]", str(ticket.id))
    detail_table.add_row("[bold]機台代號 :[/bold]", ticket.machine_id)
    detail_table.add_row("[bold]生產線別 :[/bold]", ticket.line_id)
    detail_table.add_row("[bold]故障類別 :[/bold]", ticket.failure_type)
    detail_table.add_row("[bold]優先級別 :[/bold]", ticket.priority)
    detail_table.add_row("[bold]當前狀態 :[/bold]", f"[{'green' if ticket.status == 'closed' else 'yellow'}]{ticket.status}[/]")
    detail_table.add_row("[bold]停機時間 :[/bold]", f"{ticket.downtime_minutes} 分鐘")
    detail_table.add_row("[bold]建立日期 :[/bold]", ticket.created_at)
    detail_table.add_row("[bold]更新日期 :[/bold]", ticket.updated_at)

    body_items = [detail_table]
    if ticket.status == "closed":
        body_items.append(
            Panel.fit(
                f"實際維修耗時: {ticket.actual_repair_minutes} 分鐘\n"
                f"結案處置描述: {ticket.resolution or '(未填寫)'}\n"
                f"結案時間: {ticket.closed_at or '(未記錄)'}",
                title="✅ 結案資訊",
                border_style="green",
            )
        )
    body_items.append(Panel.fit(ticket.issue, title="問題描述", border_style="yellow"))
    body_items.append(Panel.fit(notes_str, title="維修日誌追蹤", border_style="magenta"))

    Console().print(
        Panel(
            Group(*body_items),
            title=f"[bold cyan]維修工單詳細報告 - #{ticket.id}[/bold cyan]",
            expand=False,
            border_style="cyan",
        )
    )


def print_machine_report(report: Dict) -> None:
    """顯示設備健康度與歷史維修統計面板"""
    status_lines = "\n".join(f" • {status}: {count}" for status, count in report["status_counts"].items())
    content = (
        f"設備 ID: [bold]{report['machine_id']}[/bold]\n"
        f"歷史工單總數: [bold]{report['total']}[/bold]\n"
        f"累積停機總時間: [red]{report['total_downtime']}[/red] 分鐘\n"
        f"近 90 天工單數: [yellow]{report['recent_90_days']}[/yellow]\n"
        f"最常出現故障類型: [bold cyan]{report['most_common_failure_type']}[/bold cyan]\n"
        f"{'-' * 30}\n"
        f"各狀態工單數量:\n{status_lines}"
    )
    Console().print(Panel(content, title="[bold green]設備健康度追蹤報告[/bold green]", expand=False, border_style="green"))


def migrate_from_json_if_needed(json_path: str, storage: BaseStorage) -> Optional[Dict]:
    """首次執行時，將 v1 JSON 資料遷移到 SQLite，並備份舊檔"""
    if not os.path.exists(json_path):
        return None
    if not isinstance(storage, SqliteStorage):
        return None
    # 只有在 SQLite 尚未有資料時，才執行一次性的資料遷移
    if storage.count_all() > 0:
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    tickets = payload.get("tickets", [])
    if not isinstance(tickets, list) or not tickets:
        return None

    imported = 0
    max_id = 0
    for row in tickets:
        if not isinstance(row, dict):
            continue
        ticket = Ticket(**row)
        if ticket.id is None:
            continue
        storage.import_ticket_preserve_id(ticket)
        imported += 1
        max_id = max(max_id, int(ticket.id))

    if imported == 0:
        return None

    backup_path = f"{json_path}.migrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
    shutil.move(json_path, backup_path)

    try:
        storage.conn.execute(
            "UPDATE sqlite_sequence SET seq = ? WHERE name = 'tickets'",
            (max_id,),
        )
        if storage.conn.total_changes == 0:
            storage.conn.execute(
                "INSERT INTO sqlite_sequence(name, seq) VALUES ('tickets', ?)",
                (max_id,),
            )
        storage.conn.commit()
    except sqlite3.DatabaseError:
        storage.conn.rollback()

    return {"imported": imported, "backup_path": backup_path}


def interactive_report_wizard(service: TicketService) -> None:
    """啟動互動式精靈，支援建立新工單或引導結案"""
    try:
        import questionary
    except ImportError:
        fail("wizard mode requires 'questionary'. Please install it from requirements.txt", 1)

    rprint(Panel("[bold green]啟動互動式工單小幫手 (Wizard Mode)[/bold green]"))

    # Wizard 支援兩條主流程：建立工單或引導結案
    action = questionary.select(
        "請選擇要執行的動作:",
        choices=[
            "建立新工單",
            "結案既有工單",
            "取消",
        ],
    ).ask()

    if action == "取消" or action is None:
        rprint("[yellow]已取消 Wizard 操作。[/yellow]")
        return

    if action == "建立新工單":
        machine_id = questionary.text("請輸入設備 ID (例如 M101):").ask()
        line_id = questionary.select("請選擇所屬產線:", choices=["L1", "L2", "L3", "L4"]).ask()
        issue = questionary.text("請簡述故障問題:").ask()
        failure_type = questionary.select("故障類型:", choices=sorted(FAILURE_TYPES)).ask()
        priority = questionary.select("優先級:", choices=["low", "medium", "high"]).ask()
        downtime = questionary.text("預估停機分鐘數:", validate=lambda text: text.isdigit(), default="0").ask()

        if not machine_id or not issue:
            rprint("[red]錯誤: 設備 ID 與問題描述為必填項目[/red]")
            return

        if questionary.confirm("確定要提交此工單嗎?").ask():
            tid = service.create_ticket(
                machine_id=machine_id,
                line_id=line_id,
                issue=issue,
                failure_type=failure_type,
                priority=priority,
                downtime_minutes=int(downtime),
            )
            rprint(f"[bold green]SUCCESS: 已成功建立工單 [ID: {tid}][/bold green]")
        return

    ticket_id_text = questionary.text(
        "請輸入要結案的工單 ID:",
        validate=lambda text: text.isdigit() and int(text) > 0,
    ).ask()
    if not ticket_id_text:
        rprint("[yellow]未輸入工單 ID，已取消。[/yellow]")
        return

    tid = int(ticket_id_text)
    ticket = service.storage.get_by_id(tid)
    if not ticket:
        rprint(f"[red]錯誤: 找不到工單 ID {tid}[/red]")
        return

    if ticket.status == "closed":
        rprint(f"[yellow]INFO: 工單 [{tid}] 已經是 closed 狀態。[/yellow]")
        return

    rprint(
        Panel(
            f"工單 ID: {ticket.id}\n"
            f"設備 ID: {ticket.machine_id}\n"
            f"產線: {ticket.line_id}\n"
            f"目前狀態: {ticket.status}\n"
            f"問題描述: {ticket.issue}",
            title="即將進行結案確認",
            border_style="cyan",
        )
    )

    actual_repair = questionary.text(
        "請輸入實際維修耗時（分鐘）:",
        validate=lambda text: text.isdigit() and int(text) >= 0,
    ).ask()
    resolution = questionary.text("請輸入結案處置描述（必填）:").ask()

    if resolution is None or str(resolution).strip() == "":
        rprint("[red]錯誤: 結案處置描述不可為空白[/red]")
        return

    if questionary.confirm("確認將此工單結案嗎?").ask():
        service.update_ticket(
            tid,
            status="closed",
            actual_repair_minutes=int(actual_repair),
            resolution=resolution.strip(),
        )
        rprint(f"[bold green]SUCCESS: 工單 [{tid}] 已完成結案[/bold green]")


def build_parser() -> argparse.ArgumentParser:
    """建立 CLI 參數解析器，保留 v1 指令並加入 v2 選項"""
    parser = argparse.ArgumentParser(prog="factory-ticket-cli")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("wizard", help="啟動互動式引導報修 / 結案")

    p = sub.add_parser("report", help="建立新工單")
    p.add_argument("--machine_id", required=True)
    p.add_argument("--line_id", required=True)
    p.add_argument("--issue", required=True)
    p.add_argument("--failure_type", choices=sorted(FAILURE_TYPES), required=True)
    p.add_argument("--priority", choices=sorted(PRIORITIES), required=True)
    p.add_argument("--downtime_minutes", type=int, default=0)

    p = sub.add_parser("list", help="列出工單清單")
    p.add_argument("--status", choices=sorted(STATUSES))
    p.add_argument("--line_id")
    p.add_argument("--sort", default="id")

    p = sub.add_parser("update", help="更新工單欄位")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--status", choices=sorted(STATUSES))
    p.add_argument("--priority", choices=sorted(PRIORITIES))
    p.add_argument("--downtime_minutes", type=int)
    p.add_argument("--actual_repair_minutes", type=int)
    p.add_argument("--resolution")

    p = sub.add_parser("show", help="顯示單張工單詳細內容")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("summary", help="顯示摘要統計")
    p.add_argument("--line_id")
    p.add_argument("--start_date")
    p.add_argument("--end_date")

    p = sub.add_parser("search", help="關鍵字搜尋工單")
    p.add_argument("--keyword", required=True)

    p = sub.add_parser("note", help="新增工單備註")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--text", required=True)

    sub.add_parser("recommend", help="顯示維修優先序建議")

    p = sub.add_parser("delete", help="刪除工單")
    p.add_argument("--id", type=int, required=True)

    p = sub.add_parser("machine", help="查詢設備健康度報表")
    p.add_argument("--machine_id", required=True)

    p = sub.add_parser("export", help="匯出工單為 CSV")
    p.add_argument("--status", choices=sorted(STATUSES))
    p.add_argument("--line_id")

    return parser


def main() -> None:
    """程式主入口"""
    storage = SqliteStorage(DB_FILE)
    migration = migrate_from_json_if_needed(JSON_DATA_FILE, storage)
    if migration:
        rprint(
            f"[green]INFO: 已自動從 tickets.json 匯入 {migration['imported']} 筆資料，"
            f"原檔已備份為 {migration['backup_path']}[/green]"
        )

    service = TicketService(storage)
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "wizard":
        interactive_report_wizard(service)
    elif args.command == "report":
        kw = {k: v for k, v in vars(args).items() if k != "command"}
        tid = service.create_ticket(**kw)
        print(f"SUCCESS: Reported Ticket [{tid}]")
    elif args.command == "list":
        print_ticket_table(service.list_tickets({"status": args.status, "line_id": args.line_id}, args.sort))
    elif args.command == "update":
        updates = {k: v for k, v in vars(args).items() if v is not None and k not in {"command", "id"}}
        if not updates:
            fail("At least one field to update must be provided", 2)
        if service.update_ticket(args.id, **updates):
            print(f"SUCCESS: Ticket [{args.id}] updated")
        else:
            fail("Ticket not found", 1)
    elif args.command == "show":
        ticket = service.storage.get_by_id(args.id)
        if ticket:
            print_detail(ticket)
        else:
            fail("Ticket not found", 1)
    elif args.command == "summary":
        summary = service.get_summary(args.line_id, args.start_date, args.end_date)
        print_summary_report(summary)
    elif args.command == "search":
        print_search_table(service.search_tickets(args.keyword))
    elif args.command == "note":
        if service.add_note(args.id, args.text):
            print("SUCCESS: Note added")
        else:
            fail("Ticket not found", 1)
    elif args.command == "recommend":
        recs = service.recommend_tickets()
        if not recs:
            rprint("[yellow]目前無待處理工單，產線運作正常。[/yellow]")
        else:
            table = Table(title="[bold green]維修優先序建議 (v2.0 頻率加權算法)[/bold green]")
            table.add_column("序位", justify="center", style="dim")
            table.add_column("ID", style="cyan")
            table.add_column("優先分", style="bold red")
            table.add_column("近90天頻率", style="yellow")
            table.add_column("設備 ID")
            for i, item in enumerate(recs, 1):
                table.add_row(
                    str(i),
                    str(item["ticket"].id),
                    str(item["score"]),
                    str(item["recent_failure_count"]),
                    item["ticket"].machine_id,
                )
            Console().print(table)
    elif args.command == "delete":
        if service.storage.delete(args.id):
            print("SUCCESS: Ticket deleted")
        else:
            fail("Ticket not found", 1)
    elif args.command == "machine":
        report = service.get_machine_report(args.machine_id)
        if report:
            print_machine_report(report)
        else:
            rprint(f"[yellow]INFO: Device '{args.machine_id}' has no ticket history[/yellow]")
    elif args.command == "export":
        result = service.export_tickets(status=args.status, line_id=args.line_id)
        if result is None:
            rprint("[yellow]INFO: No matching tickets found. Export cancelled.[/yellow]")
        else:
            print(f"SUCCESS: Exported {result['count']} tickets to {result['path']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

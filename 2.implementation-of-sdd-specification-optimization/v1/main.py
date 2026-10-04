import argparse
import json
import os
import sys
import questionary
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint


# 設定資料儲存路徑
DATA_FILE = os.path.join(os.path.dirname(__file__), "tickets.json")

# 設定標準化的標籤資料
STATUSES = {"open", "in_progress", "closed"}
FAILURE_TYPES = {"mechanical", "electrical", "sensor", "quality", "other"}
PRIORITIES = {"low", "medium", "high"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
FAILURE_ORDER = ["mechanical", "electrical", "sensor", "quality", "other"]

# --- 通用工具 ---
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fail(msg, code=1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)

def validate_choice(value, allowed, name):
    if value is not None and value not in allowed:
        fail(f"invalid {name} '{value}'", 2)

def validate_non_negative(value, name):
    if value is not None and value < 0:
        fail(f"{name} must be >= 0", 2)

# --- 資料模型 (Data Model) ---
class Ticket:
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
        self.resolution = kw.get("resolution", "")
        self.metadata = kw.get("metadata", {}) or {}
        self.metadata.setdefault("notes", [])

    def to_dict(self):
        return self.__dict__

# --- 資料存取層 (定義存取介面並保持未來可擴充性) ---
class BaseStorage(ABC):
    @abstractmethod
    def next_id(self) -> int: pass
    @abstractmethod
    def list_all(self) -> List[Ticket]: pass
    @abstractmethod
    def get_by_id(self, tid: int) -> Optional[Ticket]: pass
    @abstractmethod
    def add(self, ticket: Ticket): pass
    @abstractmethod
    def update(self, tid: int, updates: Dict) -> bool: pass
    @abstractmethod
    def delete(self, tid: int) -> bool: pass

# --- 工單資料存取層與儲存模組(json) ---
class JsonStorage(BaseStorage):
    def __init__(self, path):
        self.path = path

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, FileNotFoundError): # 加上 FileNotFoundError
            fail("failed to read data file", 1) # 確保 code 是 1)

    def _save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def next_id(self): return self._load()["next_id"]
    def list_all(self): return [Ticket(**row) for row in self._load()["tickets"]]
    def get_by_id(self, tid):
        for t in self.list_all():
            if t.id == tid: return t
        return None

    def add(self, ticket):
        data = self._load()
        data["tickets"].append(ticket.to_dict())
        data["next_id"] += 1
        self._save(data)

    def update(self, tid, updates):
        data = self._load()
        for row in data["tickets"]:
            if row["id"] == tid:
                for k, v in updates.items():
                    if v is not None: row[k] = v
                row["updated_at"] = now_str()
                self._save(data)
                return True
        return False

    def delete(self, tid):
        data = self._load()
        orig_len = len(data["tickets"])
        data["tickets"] = [r for r in data["tickets"] if r["id"] != tid]
        if len(data["tickets"]) == orig_len: return False
        self._save(data)
        return True

# 服務層：建立生產管理驗證邏輯與權重計分演算法
class TicketService:
    def __init__(self, storage: BaseStorage):
        self.storage = storage

    def create_ticket(self, **kw):
        validate_choice(kw.get("failure_type"), FAILURE_TYPES, "failure type")
        validate_choice(kw.get("priority"), PRIORITIES, "priority")
        validate_non_negative(kw.get("downtime_minutes"), "downtime")
        ticket = Ticket(id=self.storage.next_id(), **kw)
        self.storage.add(ticket)
        return ticket.id

    def list_tickets(self, filters: Dict, sort_by: str):
        tickets = self.storage.list_all()
        for field, value in filters.items():
            if value: tickets = [t for t in tickets if getattr(t, field) == value]
        
        if sort_by == "priority":
            tickets.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 9), t.id))
        elif sort_by == "downtime":
            tickets.sort(key=lambda t: (-t.downtime_minutes, t.id))
        else:
            tickets.sort(key=lambda t: getattr(t, sort_by, t.id))
        return tickets

    def update_ticket(self, tid, **updates):
        validate_choice(updates.get("status"), STATUSES, "status")
        validate_choice(updates.get("priority"), PRIORITIES, "priority")
        validate_non_negative(updates.get("downtime_minutes"), "downtime")
        return self.storage.update(tid, updates)

    def search_tickets(self, keyword):
        kw = keyword.lower()
        results = []
        for t in self.storage.list_all():
            if kw in t.issue.lower() or any(kw in n.lower() for n in t.metadata["notes"]):
                results.append(t)
        return results

    def get_summary(self):
        tickets = self.storage.list_all()
        summary = {
            "total": len(tickets),
            "open": sum(1 for t in tickets if t.status == "open"),
            "closed": sum(1 for t in tickets if t.status == "closed"),
            "total_downtime": sum(t.downtime_minutes for t in tickets),
            "by_type": {t: sum(1 for tk in tickets if tk.failure_type == t) for t in FAILURE_TYPES}
        }
        return summary

    def add_note(self, tid, text):
        t = self.storage.get_by_id(tid)
        if not t: return False
        t.metadata["notes"].append(f"{now_str()} | {text}")
        return self.storage.update(tid, {"metadata": t.metadata})

    def recommend_tickets(self):
        tickets = [t for t in self.storage.list_all() if t.status != "closed"]
        priority_score = {"high": 100, "medium": 60, "low": 30}
        recs = [{"ticket": t, "score": priority_score.get(t.priority, 0) + min(t.downtime_minutes, 60)} for t in tickets]
        recs.sort(key=lambda x: (-x["score"], x["ticket"].id))
        return recs

# --- 顯示層 (Presentation Layer) ---
def print_ticket_table(tickets):
    if not tickets:
        rprint("[yellow]INFO: No tickets found[/yellow]")
        return
    
    console = Console()
    table = Table(title="[bold blue]工廠維護工單監控清單[/bold blue]", show_header=True, header_style="bold magenta")
    
    table.add_column("ID", style="dim", width=4)
    table.add_column("機器 ID", width=12)
    table.add_column("狀態", width=12)
    table.add_column("優先級", width=10)
    table.add_column("停機(分)", justify="right")
    table.add_column("問題描述")

    for t in tickets:
        # 根據狀態與優先順序上色 (視覺化管理)
        status_color = "green" if t.status == "closed" else "yellow"
        prio_color = "red" if t.priority == "high" else "white"
        
        table.add_row(
            str(t.id),
            t.machine_id,
            f"[{status_color}]{t.status}[/{status_color}]",
            f"[{prio_color}]{t.priority}[/{prio_color}]",
            str(t.downtime_minutes),
            t.issue
        )
    console.print(table)

def print_summary_report(s: Dict):
    console = Console()
    content = (
        f"總工單數: [bold]{s['total']}[/bold]\n"
        f"待處理 (Open): [yellow]{s['open']}[/yellow] | 已結案 (Closed): [green]{s['closed']}[/green]\n"
        f"總停機時間: [red]{s['total_downtime']}[/red] 分鐘\n"
        f"{'-'*30}\n"
        "故障類型分布:\n"
    )
    for ft, count in s['by_type'].items():
        content += f" • {ft:<12}: {count}\n"
    
    console.print(Panel(content, title="[bold]工廠異常維護總結報告[/bold]", expand=False, border_style="blue"))

# --- 互動式輸入模組 ---
def interactive_report_wizard(service: TicketService):
    """啟動互動式 Wizard 報修精靈"""
    rprint(Panel("[bold green]啟動互動式報修小幫手 (Wizard Mode)[/bold green]"))
    
    machine_id = questionary.text("請輸入設備 ID (例如 M101):").ask()
    line_id = questionary.select("請選擇所屬產線:", choices=["L1", "L2", "L3", "L4"]).ask()
    issue = questionary.text("請簡述故障問題:").ask()
    f_type = questionary.select("故障類型:", choices=list(FAILURE_TYPES)).ask()
    priority = questionary.select("優先級:", choices=list(PRIORITIES)).ask()
    downtime = questionary.text("預估停機分鐘數:", validate=lambda text: text.isdigit(), default="0").ask()

    if not machine_id or not issue:
        rprint("[red]錯誤: 設備 ID 與問題描述為必填項目[/red]")
        return

    if questionary.confirm("確定要提交此工單嗎?").ask():
        tid = service.create_ticket(
            machine_id=machine_id, line_id=line_id, issue=issue,
            failure_type=f_type, priority=priority, downtime_minutes=int(downtime)
        )
        rprint(f"[bold green]SUCCESS: 已成功建立工單 [ID: {tid}][/bold green]")

def build_parser():
    parser = argparse.ArgumentParser(prog="factory-ticket-cli")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("wizard", help="啟動互動式引導報修")

    p = sub.add_parser("report")
    p.add_argument("--machine_id", required=True); p.add_argument("--line_id", required=True)
    p.add_argument("--issue", required=True); p.add_argument("--failure_type", choices=FAILURE_TYPES, required=True)
    p.add_argument("--priority", choices=PRIORITIES, required=True); p.add_argument("--downtime_minutes", type=int, default=0)

    p = sub.add_parser("list")
    p.add_argument("--status", choices=STATUSES); p.add_argument("--sort", default="id")

    p = sub.add_parser("update")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--status", choices=STATUSES)
    p.add_argument("--priority", choices=PRIORITIES)
    p.add_argument("--downtime_minutes", type=int)

    p = sub.add_parser("show"); p.add_argument("--id", type=int, required=True)
    sub.add_parser("summary")
    p = sub.add_parser("search"); p.add_argument("--keyword", required=True)
    p = sub.add_parser("note"); p.add_argument("--id", type=int, required=True); p.add_argument("--text", required=True)
    sub.add_parser("recommend")
    p = sub.add_parser("delete"); p.add_argument("--id", type=int, required=True)
    return parser

def print_detail(t: Ticket):
    """
    [視覺化管理] 顯示特定工單的詳細完整報告。
    """
    console = Console()
    # 格式化日誌顯示邏輯
    notes_list = t.metadata.get("notes", [])
    notes_str = "\n".join([f"  • {n}" for n in notes_list]) if notes_list else "  (尚無維修備註)"

    # 建立詳細資訊表格 (不顯示邊框以維持簡潔)
    detail_table = Table(box=None, show_header=False)
    detail_table.add_row("[bold]工單 ID  :[/bold]", str(t.id))
    detail_table.add_row("[bold]機台代號 :[/bold]", t.machine_id)
    detail_table.add_row("[bold]生產線別 :[/bold]", t.line_id)
    detail_table.add_row("[bold]故障類別 :[/bold]", t.failure_type)
    detail_table.add_row("[bold]當前狀態 :[/bold]", f"[{'green' if t.status=='closed' else 'yellow'}]{t.status}[/]")
    detail_table.add_row("[bold]停機時間 :[/bold]", f"{t.downtime_minutes} 分鐘")
    detail_table.add_row("[bold]建立日期 :[/bold]", t.created_at)

    # 使用 Panel 包裝，強化視覺層級感
    console.print(Panel(
        f"{detail_table}\n[hr]\n[bold]問題描述:[/bold]\n{t.issue}\n\n[bold]維修日誌追蹤:[/bold]\n{notes_str}",
        title=f"[bold cyan]維修工單詳細報告 - #{t.id}[/bold cyan]",
        expand=False,
        border_style="cyan"
    ))

# --- CLI 入口 ---
def main():
    service = TicketService(JsonStorage(DATA_FILE))
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "wizard":
        interactive_report_wizard(service)
    elif args.command == "report":
        kw = {k: v for k, v in vars(args).items() if k != 'command'}
        print(f"SUCCESS: Reported Ticket [{service.create_ticket(**kw)}]")
    elif args.command == "list":
        print_ticket_table(service.list_tickets({"status": args.status}, args.sort))
    elif args.command == "update":
        updates = {k: v for k, v in vars(args).items() if v is not None and k not in ['command', 'id']}
        if not updates: fail("At least one field to update must be provided", 2)
        if service.update_ticket(args.id, **updates): print(f"SUCCESS: Ticket [{args.id}] updated")
        else: fail("Ticket not found")
    elif args.command == "show":
        t = service.storage.get_by_id(args.id)
        if t: print_detail(t)
        else: fail("Ticket not found")
    elif args.command == "summary":
        print_summary_report(service.get_summary())

    elif args.command == "search":
        print_ticket_table(service.search_tickets(args.keyword))
    elif args.command == "note":
        if service.add_note(args.id, args.text): print("SUCCESS: Note added")
        else: fail("Ticket not found")
    elif args.command == "recommend":
        recs = service.recommend_tickets()
        if not recs:
            rprint("[yellow]目前無待處理工單，產線運作正常。[/yellow]")
        else:
            table = Table(title="[bold green]維修優先序建議 (基於權重評分系統)[/bold green]")
            table.add_column("序位", justify="center", style="dim")
            table.add_column("ID", style="cyan")
            table.add_column("優先分", style="bold red")
            table.add_column("設備 ID")
            for i, item in enumerate(recs, 1):
                table.add_row(str(i), str(item['ticket'].id), str(item['score']), item['ticket'].machine_id)
            Console().print(table)
    elif args.command == "delete":
        if service.storage.delete(args.id): print("SUCCESS: Ticket deleted")
        else: fail("Ticket not found")
    else: parser.print_help()

if __name__ == "__main__":
    main()
    
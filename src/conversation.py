import sqlite3
import json
import uuid
import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_history.db")

@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class EvidenceCache:
    theory_docs: List[Dict]
    moment_docs: List[Dict]
    turn_id: int
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Conversation:
    conversation_id: str
    messages: List[Message] = field(default_factory=list)
    summary: str = ""
    topic_keywords: List[str] = field(default_factory=list)
    evidence_cache: Optional[EvidenceCache] = None
    turn_id: int = 0
    title: str = ""  # 【新增】标题字段
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

class ConversationStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 升级建表语句，包含 title
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            summary TEXT,
            topic_keywords TEXT,
            evidence_cache TEXT,
            turn_id INTEGER DEFAULT 0,
            title TEXT, 
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
        ''')
        conn.commit()
        conn.close()

    def create_conversation(self) -> str:
        conversation_id = str(uuid.uuid4())
        now = datetime.now()
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (id, summary, topic_keywords, turn_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (conversation_id, "", "[]", 0, "", now, now)
        )
        conn.commit()
        conn.close()
        return conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 显式查询所有字段，防止列顺序混乱
        cursor.execute("SELECT id, summary, topic_keywords, evidence_cache, turn_id, created_at, updated_at, title FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
            
        cid, summary, keywords_json, evidence_json, turn_id, created_at, updated_at, title = row
        
        # 处理旧数据可能没有 title 的情况
        if title is None: title = ""

        cursor.execute("SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,))
        msg_rows = cursor.fetchall()
        
        messages = []
        for r, c, t in msg_rows:
            if isinstance(t, str):
                try: t = datetime.fromisoformat(t)
                except: t = datetime.now()
            messages.append(Message(role=r, content=c, timestamp=t))
            
        topic_keywords = json.loads(keywords_json) if keywords_json else []
        
        evidence_cache = None
        if evidence_json:
            try:
                e_dict = json.loads(evidence_json)
                ts = datetime.fromisoformat(e_dict['timestamp']) if 'timestamp' in e_dict else datetime.now()
                evidence_cache = EvidenceCache(
                    theory_docs=e_dict.get('theory_docs', []),
                    moment_docs=e_dict.get('moment_docs', []),
                    turn_id=e_dict.get('turn_id', 0),
                    timestamp=ts
                )
            except:
                pass

        if isinstance(created_at, str): created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str): updated_at = datetime.fromisoformat(updated_at)

        conn.close()

        return Conversation(
            conversation_id=cid,
            messages=messages,
            summary=summary,
            topic_keywords=topic_keywords,
            evidence_cache=evidence_cache,
            turn_id=turn_id,
            title=title,
            created_at=created_at,
            updated_at=updated_at
        )
    
    def add_message(self, conversation_id: str, role: str, content: str) -> Conversation:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,))
        if not cursor.fetchone():
            now = datetime.now()
            cursor.execute(
                "INSERT INTO conversations (id, summary, topic_keywords, turn_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (conversation_id, "", "[]", 0, "", now, now)
            )
        
        now = datetime.now()
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, now)
        )
        cursor.execute(
            "UPDATE conversations SET turn_id = turn_id + 1, updated_at = ? WHERE id = ?",
            (now, conversation_id)
        )
        conn.commit()
        conn.close()
        return self.get_conversation(conversation_id)
    
    # 【新增】更新标题的方法
    def update_title(self, conversation_id: str, title: str) -> None:
        conn = self._get_conn()
        conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))
        conn.commit()
        conn.close()

    # --- 以下保持原有方法不变，为节省篇幅，请确保没有删除它们 ---
    def update_summary(self, conversation_id: str, summary: str) -> None:
        conn = self._get_conn()
        conn.execute("UPDATE conversations SET summary = ?, updated_at = ? WHERE id = ?", 
                     (summary, datetime.now(), conversation_id))
        conn.commit()
        conn.close()
    
    def update_topic_keywords(self, conversation_id: str, keywords: List[str]) -> None:
        conn = self._get_conn()
        conn.execute("UPDATE conversations SET topic_keywords = ?, updated_at = ? WHERE id = ?", 
                     (json.dumps(keywords, ensure_ascii=False), datetime.now(), conversation_id))
        conn.commit()
        conn.close()
    
    def update_evidence_cache(self, conversation_id: str, theory_docs: List[Dict], moment_docs: List[Dict]) -> None:
        conv = self.get_conversation(conversation_id)
        if not conv: return
        cache_data = {"theory_docs": theory_docs, "moment_docs": moment_docs, "turn_id": conv.turn_id, "timestamp": datetime.now().isoformat()}
        conn = self._get_conn()
        conn.execute("UPDATE conversations SET evidence_cache = ?, updated_at = ? WHERE id = ?", 
                     (json.dumps(cache_data, ensure_ascii=False), datetime.now(), conversation_id))
        conn.commit()
        conn.close()

    def get_recent_messages(self, conversation_id: str, max_count: int = 2) -> List[Message]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?", (conversation_id, max_count))
        rows = cursor.fetchall()
        conn.close()
        messages = []
        for r, c, t in reversed(rows):
            if isinstance(t, str): t = datetime.fromisoformat(t)
            messages.append(Message(role=r, content=c, timestamp=t))
        return messages

    def get_conversation_summary(self, conversation_id: str) -> str:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT summary FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""

    def should_summarize(self, conversation_id: str, max_messages: int = 10, max_chars: int = 6000) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,))
        count = cursor.fetchone()[0]
        if count >= max_messages:
            conn.close()
            return True
        cursor.execute("SELECT content FROM messages WHERE conversation_id = ?", (conversation_id,))
        rows = cursor.fetchall()
        conn.close()
        total_chars = sum(len(r[0]) for r in rows)
        return total_chars >= max_chars

    def get_last_assistant_answer(self, conversation_id: str) -> str:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM messages WHERE conversation_id = ? AND role = 'assistant' ORDER BY id DESC LIMIT 1", (conversation_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""

    def get_recent_messages_dict(self, conversation_id: str, max_count: int = 10) -> List[Dict]:
        msgs = self.get_recent_messages(conversation_id, max_count)
        return [{"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat() if hasattr(m.timestamp, "isoformat") else str(m.timestamp)} for m in msgs]

    def delete_conversation(self, conversation_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_all_conversations(self) -> List[Conversation]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conversations ORDER BY updated_at DESC")
        ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return [self.get_conversation(cid) for cid in ids if cid]
        
    def update_last_assistant_message(self, conversation_id: str, content: str) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM messages WHERE conversation_id = ? AND role = 'assistant' ORDER BY id DESC LIMIT 1", (conversation_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE messages SET content = ? WHERE id = ?", (content, row[0]))
            conn.commit()
        else:
            self.add_message(conversation_id, "assistant", content)
        conn.close()
        return True

conversation_store = ConversationStore()
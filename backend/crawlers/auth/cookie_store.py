# -*- coding: utf-8 -*-
"""
Cookie 持久化存储

支持：
- SQLite 存储
- 加密存储
- 过期检测
- 多平台管理
"""
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cookie_encryptor import CookieEncryptor

logger = logging.getLogger(__name__)


class CookieStore:
    """Cookie 存储管理器"""

    def __init__(self, db_path: str = None, encrypt: bool = True):
        self._shared_conn: Optional[sqlite3.Connection] = None
        if db_path is None:
            base_dir = Path(__file__).parent.parent.parent
            db_path = base_dir / "data" / "cookies.db"

        self._memory_mode = db_path == ":memory:"
        if self._memory_mode:
            self.db_path = Path(".")
            # Keep one shared in-memory connection alive for the lifetime of the store.
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.encrypt = encrypt
        self.encryptor = CookieEncryptor() if encrypt else None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """获取数据库连接。内存模式复用同一个连接。"""
        if self._memory_mode:
            assert self._shared_conn is not None
            return self._shared_conn
        return sqlite3.connect(str(self.db_path))

    def _close(self, conn: sqlite3.Connection):
        """关闭数据库连接。内存模式下保留共享连接。"""
        if not self._memory_mode:
            conn.close()

    def _init_db(self):
        """初始化数据库"""
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cookies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                domain TEXT,
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                path TEXT DEFAULT '/',
                expires TIMESTAMP,
                secure BOOLEAN DEFAULT 0,
                http_only BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, domain, name)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL UNIQUE,
                session_data TEXT,
                is_valid BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        conn.commit()
        self._close(conn)

    def save_cookies(self, platform: str, cookies: List[Dict[str, Any]]) -> bool:
        """保存 Cookie"""
        conn = self._connect()
        try:
            for cookie in cookies:
                value = cookie.get('value', '')
                # 加密 Cookie 值
                if self.encryptor and value:
                    value = self.encryptor.encrypt(value)
                
                conn.execute("""
                    INSERT OR REPLACE INTO cookies 
                    (platform, domain, name, value, path, expires, secure, http_only, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    platform,
                    cookie.get('domain', ''),
                    cookie.get('name', ''),
                    value,
                    cookie.get('path', '/'),
                    cookie.get('expires'),
                    cookie.get('secure', False),
                    cookie.get('httpOnly', False),
                    datetime.now().isoformat(),
                ))
            conn.commit()
            logger.info(f"保存 {len(cookies)} 个 Cookie 到 {platform}")
            return True
        except Exception as e:
            logger.error(f"保存 Cookie 失败: {e}")
            return False
        finally:
            self._close(conn)

    def get_cookies(self, platform: str, domain: str = None) -> List[Dict[str, Any]]:
        """获取 Cookie"""
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        try:
            if domain:
                rows = conn.execute(
                    "SELECT * FROM cookies WHERE platform = ? AND domain = ?",
                    (platform, domain)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM cookies WHERE platform = ?",
                    (platform,)
                ).fetchall()
            
            cookies = []
            for row in rows:
                cookie = dict(row)
                # 检查是否过期
                if cookie.get('expires'):
                    try:
                        expires = datetime.fromisoformat(cookie['expires'])
                        if expires < datetime.now():
                            continue  # 跳过过期 Cookie
                    except:
                        pass
                
                # 解密 Cookie 值
                value = cookie['value']
                if self.encryptor and value:
                    decrypted = self.encryptor.decrypt(value)
                    if decrypted:
                        value = decrypted
                
                cookies.append({
                    'name': cookie['name'],
                    'value': value,
                    'domain': cookie['domain'],
                    'path': cookie['path'],
                    'expires': cookie['expires'],
                    'secure': bool(cookie['secure']),
                    'httpOnly': bool(cookie['http_only']),
                })
            return cookies
        except Exception as e:
            logger.error(f"获取 Cookie 失败: {e}")
            return []
        finally:
            self._close(conn)

    def delete_cookies(self, platform: str, domain: str = None) -> bool:
        """删除 Cookie"""
        conn = self._connect()
        try:
            if domain:
                conn.execute("DELETE FROM cookies WHERE platform = ? AND domain = ?", (platform, domain))
            else:
                conn.execute("DELETE FROM cookies WHERE platform = ?", (platform,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除 Cookie 失败: {e}")
            return False
        finally:
            self._close(conn)

    def save_session(self, platform: str, session_data: Dict[str, Any], expires_hours: int = 24) -> bool:
        """保存会话"""
        conn = self._connect()
        try:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
            conn.execute("""
                INSERT OR REPLACE INTO sessions 
                (platform, session_data, is_valid, updated_at, expires_at)
                VALUES (?, ?, 1, ?, ?)
            """, (
                platform,
                json.dumps(session_data, ensure_ascii=False),
                datetime.now().isoformat(),
                expires_at.isoformat(),
            ))
            conn.commit()
            logger.info(f"保存会话到 {platform}")
            return True
        except Exception as e:
            logger.error(f"保存会话失败: {e}")
            return False
        finally:
            self._close(conn)

    def get_session(self, platform: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM sessions WHERE platform = ? AND is_valid = 1",
                (platform,)
            ).fetchone()
            
            if not row:
                return None
            
            session = dict(row)
            # 检查是否过期
            if session.get('expires_at'):
                try:
                    expires = datetime.fromisoformat(session['expires_at'])
                    if expires < datetime.now():
                        return None
                except:
                    pass
            
            return json.loads(session['session_data'])
        except Exception as e:
            logger.error(f"获取会话失败: {e}")
            return None
        finally:
            self._close(conn)

    def invalidate_session(self, platform: str) -> bool:
        """使会话失效"""
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE sessions SET is_valid = 0 WHERE platform = ?",
                (platform,)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"使会话失效失败: {e}")
            return False
        finally:
            self._close(conn)

    def list_platforms(self) -> List[str]:
        """列出所有平台"""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT DISTINCT platform FROM sessions WHERE is_valid = 1"
            ).fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"列出平台失败: {e}")
            return []
        finally:
            self._close(conn)

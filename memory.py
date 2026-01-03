"""
Jarvis Memory System
Combines SQLite (structured) + ChromaDB (semantic) for persistent memory.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from google import genai

from config import Config


class MemoryManager:
    """
    Manages Jarvis's memory across conversations.

    - SQLite: Stores full conversation history with metadata
    - ChromaDB: Stores embeddings for semantic retrieval
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Config.DATA_DIR / "jarvis_memory.db"
        self.chroma_path = Config.DATA_DIR / "chroma"

        # Initialize Gemini client for embeddings
        self.genai_client = genai.Client(api_key=Config.GOOGLE_API_KEY)
        self.embedding_model = "text-embedding-004"

        # Initialize databases
        self._init_sqlite()
        self._init_chromadb()

    def _init_sqlite(self):
        """Initialize SQLite database for structured storage."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp);
            
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        self.conn.commit()

    def _init_chromadb(self):
        """Initialize ChromaDB for semantic search."""
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )

        # Collection for conversation chunks
        self.collection = self.chroma_client.get_or_create_collection(
            name="jarvis_memory",
            metadata={"hnsw:space": "cosine"},
        )

    def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding using Gemini."""
        result = self.genai_client.models.embed_content(
            model=self.embedding_model,
            contents=text,
        )
        return result.embeddings[0].values

    def store(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        metadata: Optional[dict] = None,
    ):
        """
        Store a conversation exchange in memory.

        Args:
            session_id: Unique identifier for the conversation session
            user_message: The user's input
            assistant_response: Jarvis's response
            metadata: Optional additional metadata
        """
        timestamp = datetime.now().isoformat()
        meta_json = json.dumps(metadata) if metadata else None

        # Store in SQLite
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            (session_id, "user", user_message, timestamp, meta_json),
        )
        cursor.execute(
            "INSERT INTO conversations (session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            (session_id, "assistant", assistant_response, timestamp, meta_json),
        )
        self.conn.commit()

        # Store in ChromaDB for semantic search
        # Combine user + assistant for context
        combined = f"User: {user_message}\nJarvis: {assistant_response}"

        try:
            embedding = self._get_embedding(combined)

            # Use timestamp as unique ID
            doc_id = f"{session_id}_{timestamp}"

            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[combined],
                metadatas=[
                    {
                        "session_id": session_id,
                        "timestamp": timestamp,
                        "user_message": user_message[:500],  # Truncate for metadata
                    }
                ],
            )
        except Exception as e:
            # Don't fail if embedding fails - SQLite still has the data
            print(f"Warning: Failed to store embedding: {e}")

    def recall(
        self,
        query: str,
        n_results: int = 5,
        session_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Recall relevant memories based on semantic similarity.

        Args:
            query: The query to search for
            n_results: Number of results to return
            session_id: Optional filter by session

        Returns:
            List of relevant memory chunks with metadata
        """
        try:
            embedding = self._get_embedding(query)

            where_filter = {"session_id": session_id} if session_id else None

            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            memories = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    memories.append(
                        {
                            "content": doc,
                            "metadata": (
                                results["metadatas"][0][i]
                                if results["metadatas"]
                                else {}
                            ),
                            "relevance": (
                                1 - results["distances"][0][i]
                                if results["distances"]
                                else 0
                            ),
                        }
                    )

            return memories

        except Exception as e:
            print(f"Warning: Failed to recall memories: {e}")
            return []

    def get_recent_history(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """Get recent conversation history from SQLite."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT role, content, timestamp 
            FROM conversations 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """,
            (session_id, limit),
        )

        rows = cursor.fetchall()
        return [dict(row) for row in reversed(rows)]

    def get_all_sessions(self) -> list[dict]:
        """Get all conversation sessions."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT 
                session_id,
                MIN(timestamp) as started,
                MAX(timestamp) as last_active,
                COUNT(*) as message_count
            FROM conversations 
            GROUP BY session_id
            ORDER BY last_active DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def track_pattern(self, pattern_type: str, pattern_data: str):
        """
        Track recurring patterns in user behavior.

        Args:
            pattern_type: Type of pattern (e.g., 'topic', 'time_of_day', 'task_type')
            pattern_data: The pattern value
        """
        cursor = self.conn.cursor()

        # Check if pattern exists
        cursor.execute(
            "SELECT id, frequency FROM patterns WHERE pattern_type = ? AND pattern_data = ?",
            (pattern_type, pattern_data),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE patterns SET frequency = frequency + 1, last_seen = CURRENT_TIMESTAMP WHERE id = ?",
                (existing["id"],),
            )
        else:
            cursor.execute(
                "INSERT INTO patterns (pattern_type, pattern_data) VALUES (?, ?)",
                (pattern_type, pattern_data),
            )

        self.conn.commit()

    def get_patterns(
        self, pattern_type: Optional[str] = None, min_frequency: int = 2
    ) -> list[dict]:
        """Get tracked patterns, optionally filtered by type."""
        cursor = self.conn.cursor()

        if pattern_type:
            cursor.execute(
                """
                SELECT * FROM patterns 
                WHERE pattern_type = ? AND frequency >= ?
                ORDER BY frequency DESC
                """,
                (pattern_type, min_frequency),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM patterns 
                WHERE frequency >= ?
                ORDER BY frequency DESC
                """,
                (min_frequency,),
            )

        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """Get memory statistics."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM conversations")
        total_messages = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(DISTINCT session_id) as total FROM conversations")
        total_sessions = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM patterns")
        total_patterns = cursor.fetchone()["total"]

        chroma_count = self.collection.count()

        return {
            "total_messages": total_messages,
            "total_sessions": total_sessions,
            "total_patterns": total_patterns,
            "embedded_chunks": chroma_count,
        }

    def close(self):
        """Close database connections."""
        self.conn.close()

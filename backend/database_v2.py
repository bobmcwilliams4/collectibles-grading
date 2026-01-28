"""
Optimized Database Module v2
Normalized schema, optimized indexes, and async operations
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    logger.warning("aiosqlite not installed - using synchronous SQLite")
    import sqlite3


@dataclass
class QueryResult:
    """Result of a database query"""
    success: bool
    data: Any = None
    affected_rows: int = 0
    last_id: int = 0
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class AsyncDatabaseManager:
    """
    Optimized async database manager with normalized schema

    Features:
    - Normalized database schema
    - Optimized indexes for common queries
    - Async operations with connection pooling
    - Full-text search support
    - Automatic migrations
    """

    DB_PATH = "P:/SOVEREIGN_APPS/collectibles_grading_system/data/database/comics_v2.db"
    SCHEMA_VERSION = 2

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_PATH
        self._pool_size = 5
        self._connection_pool: List[Any] = []
        self._pool_lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize database with schema and indexes"""
        if self._initialized:
            return

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        async with self._get_connection() as conn:
            # Enable WAL mode for better concurrency
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=10000")
            await conn.execute("PRAGMA temp_store=MEMORY")
            await conn.execute("PRAGMA foreign_keys=ON")

            # Create schema
            await self._create_schema(conn)

            # Create indexes
            await self._create_indexes(conn)

            # Run migrations if needed
            await self._run_migrations(conn)

            await conn.commit()

        self._initialized = True
        logger.info(f"Database initialized at {self.db_path}")

    @asynccontextmanager
    async def _get_connection(self):
        """Get a database connection from pool"""
        if AIOSQLITE_AVAILABLE:
            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row
            try:
                yield conn
            finally:
                await conn.close()
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    async def _create_schema(self, conn):
        """Create normalized database schema"""
        # Publishers table (normalization)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS publishers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                country TEXT,
                founded_year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Series table (normalization)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                publisher_id INTEGER REFERENCES publishers(id),
                start_year INTEGER,
                end_year INTEGER,
                era TEXT,
                genre TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title, publisher_id, start_year)
            )
        """)

        # Comics table (main entity)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS comics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_id INTEGER REFERENCES series(id),
                issue_number TEXT,
                variant_description TEXT,
                publication_date DATE,
                cover_price DECIMAL(10,2),
                page_count INTEGER,

                -- Image paths
                front_image_path TEXT,
                back_image_path TEXT,
                front_thumbnail_path TEXT,
                back_thumbnail_path TEXT,

                -- Grading
                consensus_grade DECIMAL(3,1),
                front_grade DECIMAL(3,1),
                back_grade DECIMAL(3,1),
                page_quality TEXT,
                cover_gloss TEXT,
                graded_at TIMESTAMP,
                grading_version INTEGER DEFAULT 1,

                -- Pricing
                current_value DECIMAL(10,2),
                last_price_check TIMESTAMP,

                -- Status
                key_issue_notes TEXT,
                requires_manual_review BOOLEAN DEFAULT 0,
                review_reason TEXT,
                grader_notes TEXT,
                is_published BOOLEAN DEFAULT 0,
                is_archived BOOLEAN DEFAULT 0,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                updated_by INTEGER
            )
        """)

        # Defects table (one-to-many with comics)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS defects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comic_id INTEGER REFERENCES comics(id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                defect_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                location TEXT,
                side TEXT,
                grade_impact DECIMAL(3,2),
                confirmed_by_providers TEXT,  -- JSON array
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Grading history table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS grading_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comic_id INTEGER REFERENCES comics(id) ON DELETE CASCADE,
                grade DECIMAL(3,1),
                confidence DECIMAL(5,2),
                provider_grades TEXT,  -- JSON object
                defects_snapshot TEXT,  -- JSON array
                era_detected TEXT,
                grading_prompt_version TEXT,
                graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                graded_by INTEGER
            )
        """)

        # Pricing history table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pricing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comic_id INTEGER REFERENCES comics(id) ON DELETE CASCADE,
                consensus_price DECIMAL(10,2),
                gpa_price DECIMAL(10,2),
                heritage_price DECIMAL(10,2),
                ebay_price DECIMAL(10,2),
                ebay_sold_count INTEGER,
                price_trend TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Provider metrics table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS provider_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                comic_id INTEGER REFERENCES comics(id),
                grade_returned DECIMAL(3,1),
                confidence DECIMAL(5,2),
                latency_ms INTEGER,
                success BOOLEAN,
                error_message TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Users table (for multi-user support)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS grading_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                role TEXT DEFAULT 'viewer',
                is_active BOOLEAN DEFAULT 1,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Audit log table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                ip_address TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tags table (for flexible categorization)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT
            )
        """)

        # Comic tags junction table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS comic_tags (
                comic_id INTEGER REFERENCES comics(id) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (comic_id, tag_id)
            )
        """)

        # Full-text search virtual table (standalone, not content-synced)
        await conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS comics_fts USING fts5(
                title,
                issue_number,
                key_issue_notes
            )
        """)

        # Schema version tracking
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    async def _create_indexes(self, conn):
        """Create optimized indexes"""
        indexes = [
            # Comics indexes
            "CREATE INDEX IF NOT EXISTS idx_comics_series ON comics(series_id)",
            "CREATE INDEX IF NOT EXISTS idx_comics_grade ON comics(consensus_grade)",
            "CREATE INDEX IF NOT EXISTS idx_comics_value ON comics(current_value)",
            "CREATE INDEX IF NOT EXISTS idx_comics_created ON comics(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_comics_review ON comics(requires_manual_review) WHERE requires_manual_review = 1",
            "CREATE INDEX IF NOT EXISTS idx_comics_published ON comics(is_published)",

            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_comics_grade_value ON comics(consensus_grade, current_value)",
            "CREATE INDEX IF NOT EXISTS idx_comics_series_issue ON comics(series_id, issue_number)",

            # Defects indexes
            "CREATE INDEX IF NOT EXISTS idx_defects_comic ON defects(comic_id)",
            "CREATE INDEX IF NOT EXISTS idx_defects_severity ON defects(severity)",
            "CREATE INDEX IF NOT EXISTS idx_defects_type ON defects(category, defect_type)",

            # History indexes
            "CREATE INDEX IF NOT EXISTS idx_grading_history_comic ON grading_history(comic_id)",
            "CREATE INDEX IF NOT EXISTS idx_grading_history_date ON grading_history(graded_at)",
            "CREATE INDEX IF NOT EXISTS idx_pricing_history_comic ON pricing_history(comic_id)",
            "CREATE INDEX IF NOT EXISTS idx_pricing_history_date ON pricing_history(recorded_at)",

            # Provider metrics indexes
            "CREATE INDEX IF NOT EXISTS idx_provider_metrics_provider ON provider_metrics(provider_name)",
            "CREATE INDEX IF NOT EXISTS idx_provider_metrics_comic ON provider_metrics(comic_id)",
            "CREATE INDEX IF NOT EXISTS idx_provider_metrics_date ON provider_metrics(recorded_at)",

            # Series indexes
            "CREATE INDEX IF NOT EXISTS idx_series_publisher ON series(publisher_id)",
            "CREATE INDEX IF NOT EXISTS idx_series_era ON series(era)",

            # Audit log indexes
            "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource_type, resource_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(recorded_at)",
        ]

        for index_sql in indexes:
            try:
                await conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

    async def _run_migrations(self, conn):
        """Run pending schema migrations"""
        # Get current version
        try:
            cursor = await conn.execute(
                "SELECT MAX(version) FROM schema_version"
            )
            row = await cursor.fetchone()
            current_version = row[0] if row and row[0] else 0
        except:
            current_version = 0

        # Run migrations
        migrations = self._get_migrations()
        for version, migration_statements in migrations.items():
            if version > current_version:
                logger.info(f"Running migration v{version}")
                try:
                    for statement in migration_statements:
                        await conn.execute(statement)
                    await conn.execute(
                        "INSERT INTO schema_version (version) VALUES (?)",
                        (version,)
                    )
                except Exception as e:
                    logger.error(f"Migration v{version} failed: {e}")
                    raise

    def _get_migrations(self) -> Dict[int, List[str]]:
        """Define schema migrations (list of statements per version)"""
        return {
            1: [
                "SELECT 1"  # Initial schema marker
            ],
            2: [
                "ALTER TABLE comics ADD COLUMN cgc_cert_number TEXT",
                "ALTER TABLE comics ADD COLUMN cgc_grade DECIMAL(3,1)",
                "ALTER TABLE comics ADD COLUMN cgc_label_type TEXT"
            ]
        }

    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================

    async def create_comic(self, data: Dict[str, Any]) -> QueryResult:
        """Create a new comic entry"""
        start_time = datetime.utcnow()

        async with self._get_connection() as conn:
            try:
                # Handle series lookup/creation
                series_id = await self._get_or_create_series(conn, data)

                # Insert comic
                fields = [
                    'series_id', 'issue_number', 'variant_description',
                    'publication_date', 'cover_price', 'page_count',
                    'front_image_path', 'back_image_path',
                    'key_issue_notes', 'created_by'
                ]
                values = [series_id]
                for field in fields[1:]:
                    values.append(data.get(field))

                placeholders = ','.join(['?' for _ in fields])
                field_names = ','.join(fields)

                cursor = await conn.execute(f"""
                    INSERT INTO comics ({field_names})
                    VALUES ({placeholders})
                """, values)

                await conn.commit()
                comic_id = cursor.lastrowid

                # Update FTS index
                await self._update_fts(conn, comic_id, data)

                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                return QueryResult(
                    success=True,
                    last_id=comic_id,
                    affected_rows=1,
                    execution_time_ms=execution_time
                )

            except Exception as e:
                logger.error(f"Create comic error: {e}")
                return QueryResult(success=False, error=str(e))

    async def get_comic(self, comic_id: int) -> QueryResult:
        """Get comic by ID with all related data"""
        start_time = datetime.utcnow()

        async with self._get_connection() as conn:
            try:
                # Get comic with series info
                cursor = await conn.execute("""
                    SELECT
                        c.*,
                        s.title as series_title,
                        s.era,
                        p.name as publisher_name
                    FROM comics c
                    LEFT JOIN series s ON c.series_id = s.id
                    LEFT JOIN publishers p ON s.publisher_id = p.id
                    WHERE c.id = ?
                """, (comic_id,))

                row = await cursor.fetchone()
                if not row:
                    return QueryResult(success=False, error="Comic not found")

                comic = dict(row)

                # Get defects
                cursor = await conn.execute("""
                    SELECT * FROM defects WHERE comic_id = ?
                """, (comic_id,))
                comic['defects'] = [dict(r) for r in await cursor.fetchall()]

                # Get tags
                cursor = await conn.execute("""
                    SELECT t.* FROM tags t
                    JOIN comic_tags ct ON t.id = ct.tag_id
                    WHERE ct.comic_id = ?
                """, (comic_id,))
                comic['tags'] = [dict(r) for r in await cursor.fetchall()]

                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                return QueryResult(
                    success=True,
                    data=comic,
                    execution_time_ms=execution_time
                )

            except Exception as e:
                logger.error(f"Get comic error: {e}")
                return QueryResult(success=False, error=str(e))

    async def update_comic(self, comic_id: int, data: Dict[str, Any]) -> QueryResult:
        """Update comic entry"""
        start_time = datetime.utcnow()

        async with self._get_connection() as conn:
            try:
                # Build update query
                updates = []
                values = []
                for key, value in data.items():
                    if key not in ('id', 'created_at'):
                        updates.append(f"{key} = ?")
                        values.append(value)

                if not updates:
                    return QueryResult(success=False, error="No fields to update")

                values.append(datetime.utcnow())  # updated_at
                values.append(comic_id)

                cursor = await conn.execute(f"""
                    UPDATE comics
                    SET {', '.join(updates)}, updated_at = ?
                    WHERE id = ?
                """, values)

                await conn.commit()

                # Update FTS if relevant fields changed
                if any(k in data for k in ['title', 'issue_number', 'key_issue_notes']):
                    await self._update_fts(conn, comic_id, data)

                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                return QueryResult(
                    success=True,
                    affected_rows=cursor.rowcount,
                    execution_time_ms=execution_time
                )

            except Exception as e:
                logger.error(f"Update comic error: {e}")
                return QueryResult(success=False, error=str(e))

    async def search_comics(
        self,
        query: str = None,
        filters: Dict[str, Any] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> QueryResult:
        """
        Search comics with full-text search and filters

        Args:
            query: Full-text search query
            filters: Filter conditions
            sort_by: Sort field
            sort_order: 'asc' or 'desc'
            limit: Max results
            offset: Result offset
        """
        start_time = datetime.utcnow()
        filters = filters or {}

        async with self._get_connection() as conn:
            try:
                # Base query
                sql = """
                    SELECT
                        c.*,
                        s.title as series_title,
                        s.era,
                        p.name as publisher_name
                    FROM comics c
                    LEFT JOIN series s ON c.series_id = s.id
                    LEFT JOIN publishers p ON s.publisher_id = p.id
                """

                conditions = []
                values = []

                # Full-text search
                if query:
                    sql = """
                        SELECT c.*, s.title as series_title, s.era, p.name as publisher_name
                        FROM comics_fts fts
                        JOIN comics c ON fts.rowid = c.id
                        LEFT JOIN series s ON c.series_id = s.id
                        LEFT JOIN publishers p ON s.publisher_id = p.id
                        WHERE fts.comics_fts MATCH ?
                    """
                    values.append(query)

                # Apply filters
                if filters.get('publisher'):
                    conditions.append("p.name = ?")
                    values.append(filters['publisher'])

                if filters.get('era'):
                    conditions.append("s.era = ?")
                    values.append(filters['era'])

                if filters.get('min_grade'):
                    conditions.append("c.consensus_grade >= ?")
                    values.append(filters['min_grade'])

                if filters.get('max_grade'):
                    conditions.append("c.consensus_grade <= ?")
                    values.append(filters['max_grade'])

                if filters.get('min_value'):
                    conditions.append("c.current_value >= ?")
                    values.append(filters['min_value'])

                if filters.get('needs_review'):
                    conditions.append("c.requires_manual_review = 1")

                if filters.get('is_published') is not None:
                    conditions.append("c.is_published = ?")
                    values.append(1 if filters['is_published'] else 0)

                # Add conditions
                if conditions:
                    if query:
                        sql += " AND " + " AND ".join(conditions)
                    else:
                        sql += " WHERE " + " AND ".join(conditions)

                # Count total
                count_sql = sql.replace(
                    "SELECT c.*, s.title as series_title, s.era, p.name as publisher_name",
                    "SELECT COUNT(*)"
                )
                cursor = await conn.execute(count_sql, values)
                total = (await cursor.fetchone())[0]

                # Add ordering and pagination
                allowed_sort = ['created_at', 'consensus_grade', 'current_value', 'series_title']
                if sort_by in allowed_sort:
                    sql += f" ORDER BY {sort_by} {sort_order.upper()}"
                else:
                    sql += " ORDER BY c.created_at DESC"

                sql += " LIMIT ? OFFSET ?"
                values.extend([limit, offset])

                cursor = await conn.execute(sql, values)
                rows = [dict(r) for r in await cursor.fetchall()]

                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                return QueryResult(
                    success=True,
                    data={'comics': rows, 'total': total},
                    execution_time_ms=execution_time
                )

            except Exception as e:
                logger.error(f"Search comics error: {e}")
                return QueryResult(success=False, error=str(e))

    async def get_grading_history(self, comic_id: int) -> QueryResult:
        """Get grading history for a comic"""
        async with self._get_connection() as conn:
            try:
                cursor = await conn.execute("""
                    SELECT * FROM grading_history
                    WHERE comic_id = ?
                    ORDER BY graded_at DESC
                """, (comic_id,))
                rows = [dict(r) for r in await cursor.fetchall()]
                return QueryResult(success=True, data=rows)
            except Exception as e:
                return QueryResult(success=False, error=str(e))

    async def save_grading_result(
        self,
        grade_data: Dict[str, Any]
    ) -> QueryResult:
        """Save grading result with history"""
        start_time = datetime.utcnow()
        comic_id = grade_data.get('comic_id')
        if not comic_id:
            return QueryResult(success=False, error="comic_id is required")

        async with self._get_connection() as conn:
            try:
                # Update comic
                await conn.execute("""
                    UPDATE comics SET
                        consensus_grade = ?,
                        front_grade = ?,
                        back_grade = ?,
                        page_quality = ?,
                        cover_gloss = ?,
                        graded_at = CURRENT_TIMESTAMP,
                        grading_version = grading_version + 1,
                        requires_manual_review = ?,
                        review_reason = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    grade_data.get('consensus_grade'),
                    grade_data.get('front_grade'),
                    grade_data.get('back_grade'),
                    grade_data.get('page_quality'),
                    grade_data.get('cover_gloss'),
                    grade_data.get('requires_review', False),
                    grade_data.get('review_reason'),
                    comic_id
                ))

                # Save to history
                await conn.execute("""
                    INSERT INTO grading_history (
                        comic_id, grade, confidence, provider_grades,
                        defects_snapshot, era_detected, grading_prompt_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    comic_id,
                    grade_data.get('consensus_grade'),
                    grade_data.get('confidence'),
                    json.dumps(grade_data.get('provider_grades', {})),
                    json.dumps(grade_data.get('defects', [])),
                    grade_data.get('era'),
                    grade_data.get('prompt_version', '1.0')
                ))

                # Save defects
                await conn.execute("DELETE FROM defects WHERE comic_id = ?", (comic_id,))
                for defect in grade_data.get('defects', []):
                    await conn.execute("""
                        INSERT INTO defects (
                            comic_id, category, defect_type, severity,
                            location, side, grade_impact, confirmed_by_providers
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        comic_id,
                        defect.get('category'),
                        defect.get('type'),
                        defect.get('severity'),
                        defect.get('location'),
                        defect.get('side'),
                        defect.get('impact'),
                        json.dumps(defect.get('confirmed_by', []))
                    ))

                await conn.commit()
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                return QueryResult(
                    success=True,
                    affected_rows=1,
                    execution_time_ms=execution_time
                )

            except Exception as e:
                logger.error(f"Save grading error: {e}")
                return QueryResult(success=False, error=str(e))

    async def save_pricing_result(
        self,
        comic_id: int,
        price_data: Dict[str, Any]
    ) -> QueryResult:
        """Save pricing data with history"""
        async with self._get_connection() as conn:
            try:
                # Update comic
                await conn.execute("""
                    UPDATE comics SET
                        current_value = ?,
                        last_price_check = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (price_data.get('consensus_price'), comic_id))

                # Save to history
                await conn.execute("""
                    INSERT INTO pricing_history (
                        comic_id, consensus_price, gpa_price,
                        heritage_price, ebay_price, ebay_sold_count, price_trend
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    comic_id,
                    price_data.get('consensus_price'),
                    price_data.get('gpa_price'),
                    price_data.get('heritage_price'),
                    price_data.get('ebay_price'),
                    price_data.get('ebay_sold_count'),
                    price_data.get('trend')
                ))

                await conn.commit()
                return QueryResult(success=True, affected_rows=1)

            except Exception as e:
                return QueryResult(success=False, error=str(e))

    async def get_statistics(self) -> QueryResult:
        """Get collection statistics"""
        async with self._get_connection() as conn:
            try:
                stats = {}

                # Total comics
                cursor = await conn.execute("SELECT COUNT(*) FROM comics")
                stats['total_comics'] = (await cursor.fetchone())[0]

                # Graded comics
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM comics WHERE consensus_grade IS NOT NULL"
                )
                stats['graded_comics'] = (await cursor.fetchone())[0]

                # Total value
                cursor = await conn.execute(
                    "SELECT COALESCE(SUM(current_value), 0) FROM comics"
                )
                stats['total_value'] = (await cursor.fetchone())[0]

                # Average grade
                cursor = await conn.execute(
                    "SELECT AVG(consensus_grade) FROM comics WHERE consensus_grade IS NOT NULL"
                )
                stats['average_grade'] = (await cursor.fetchone())[0] or 0

                # Grade distribution
                cursor = await conn.execute("""
                    SELECT
                        CASE
                            WHEN consensus_grade >= 9.0 THEN 'Near Mint+'
                            WHEN consensus_grade >= 7.0 THEN 'Fine/Very Fine'
                            WHEN consensus_grade >= 4.0 THEN 'Very Good'
                            ELSE 'Good or Below'
                        END as grade_category,
                        COUNT(*) as count
                    FROM comics
                    WHERE consensus_grade IS NOT NULL
                    GROUP BY grade_category
                """)
                stats['grade_distribution'] = {
                    r['grade_category']: r['count']
                    for r in await cursor.fetchall()
                }

                # Era distribution
                cursor = await conn.execute("""
                    SELECT s.era, COUNT(*) as count
                    FROM comics c
                    JOIN series s ON c.series_id = s.id
                    GROUP BY s.era
                """)
                stats['era_distribution'] = {
                    r['era']: r['count']
                    for r in await cursor.fetchall()
                }

                # Pending review count
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM comics WHERE requires_manual_review = 1"
                )
                stats['pending_review'] = (await cursor.fetchone())[0]

                return QueryResult(success=True, data=stats)

            except Exception as e:
                return QueryResult(success=False, error=str(e))

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_or_create_series(
        self,
        conn,
        data: Dict[str, Any]
    ) -> Optional[int]:
        """Get or create series entry"""
        title = data.get('title') or data.get('series_title')
        if not title:
            return None

        # Check for existing
        cursor = await conn.execute(
            "SELECT id FROM series WHERE title = ?",
            (title,)
        )
        row = await cursor.fetchone()
        if row:
            return row[0]

        # Get or create publisher
        publisher_id = None
        if data.get('publisher'):
            publisher_id = await self._get_or_create_publisher(conn, data['publisher'])

        # Create series
        cursor = await conn.execute("""
            INSERT INTO series (title, publisher_id, era)
            VALUES (?, ?, ?)
        """, (title, publisher_id, data.get('era')))

        return cursor.lastrowid

    async def _get_or_create_publisher(self, conn, name: str) -> int:
        """Get or create publisher entry"""
        cursor = await conn.execute(
            "SELECT id FROM publishers WHERE name = ?",
            (name,)
        )
        row = await cursor.fetchone()
        if row:
            return row[0]

        cursor = await conn.execute(
            "INSERT INTO publishers (name) VALUES (?)",
            (name,)
        )
        return cursor.lastrowid

    async def _update_fts(self, conn, comic_id: int, data: Dict[str, Any]):
        """Update full-text search index"""
        try:
            # Get series title if not in data
            title = data.get('title', '')
            if not title:
                cursor = await conn.execute("""
                    SELECT series.title FROM comics
                    JOIN series ON comics.series_id = series.id
                    WHERE comics.id = ?
                """, (comic_id,))
                row = await cursor.fetchone()
                if row:
                    title = row[0] or ''

            issue_number = data.get('issue_number', '')
            key_issue_notes = data.get('key_issue_notes', '')

            # Check if entry exists
            cursor = await conn.execute(
                "SELECT rowid FROM comics_fts WHERE rowid = ?",
                (comic_id,)
            )
            exists = await cursor.fetchone()

            if exists:
                # Update existing
                await conn.execute("""
                    UPDATE comics_fts
                    SET title = ?, issue_number = ?, key_issue_notes = ?
                    WHERE rowid = ?
                """, (title, issue_number, key_issue_notes, comic_id))
            else:
                # Insert new
                await conn.execute("""
                    INSERT INTO comics_fts (rowid, title, issue_number, key_issue_notes)
                    VALUES (?, ?, ?, ?)
                """, (comic_id, title, issue_number, key_issue_notes))

            await conn.commit()
        except Exception as e:
            logger.warning(f"FTS update error: {e}")

    async def close(self):
        """Close database connections"""
        # Connections are managed per-operation, nothing to close explicitly
        self._initialized = False
        logger.info("Database manager closed")

    async def vacuum(self):
        """Optimize database"""
        async with self._get_connection() as conn:
            await conn.execute("VACUUM")
            await conn.execute("ANALYZE")

    async def backup(self, backup_path: str):
        """Create database backup"""
        async with self._get_connection() as conn:
            backup_conn = await aiosqlite.connect(backup_path)
            await conn.backup(backup_conn)
            await backup_conn.close()
            logger.info(f"Database backed up to {backup_path}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_db_manager: Optional[AsyncDatabaseManager] = None


async def get_database() -> AsyncDatabaseManager:
    """Get or create database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = AsyncDatabaseManager()
        await _db_manager.initialize()
    return _db_manager


# Export
__all__ = [
    'QueryResult',
    'AsyncDatabaseManager',
    'get_database',
]

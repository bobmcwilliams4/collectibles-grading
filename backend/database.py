"""
SQLite Database Operations with Enhanced Features
Connection pooling, migrations, full-text search, and optimized queries
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

# Thread-local storage for database connections
_local = threading.local()


class DatabaseManager:
    """Enhanced SQLite Database Manager with Connection Pooling"""

    def __init__(self, db_path: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/collectibles.db"):
        self.db_path = db_path
        self._ensure_directory()
        self._init_database()

    def _ensure_directory(self):
        """Ensure database directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """Thread-safe connection context manager"""
        if not hasattr(_local, 'connection') or _local.connection is None:
            _local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            _local.connection.row_factory = sqlite3.Row
            _local.connection.execute("PRAGMA journal_mode=WAL")
            _local.connection.execute("PRAGMA synchronous=NORMAL")
            _local.connection.execute("PRAGMA cache_size=10000")
            _local.connection.execute("PRAGMA foreign_keys=ON")

        try:
            yield _local.connection
        except Exception as e:
            _local.connection.rollback()
            raise e

    def _init_database(self):
        """Initialize database schema with all tables"""
        with self.get_connection() as conn:
            c = conn.cursor()

            # Main comics table
            c.execute('''
                CREATE TABLE IF NOT EXISTS comics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id INTEGER,
                    title TEXT NOT NULL,
                    issue_number TEXT,
                    publisher TEXT,
                    publication_year INTEGER,

                    -- Variant info
                    variant_cover BOOLEAN DEFAULT 0,
                    variant_description TEXT,

                    -- Key issue status
                    key_issue BOOLEAN DEFAULT 0,
                    key_issue_reason TEXT,

                    -- AI Consensus Grading
                    consensus_grade REAL,
                    grade_label TEXT,
                    grade_confidence REAL,
                    front_grade REAL,
                    back_grade REAL,
                    agreement_percentage REAL,
                    standard_deviation REAL,
                    quality_adjusted BOOLEAN DEFAULT 0,
                    quality_penalty REAL DEFAULT 0,
                    requires_manual_review BOOLEAN DEFAULT 0,
                    review_reason TEXT,

                    -- Individual AI Grades (JSON)
                    claude_grade_data TEXT,
                    gemini_grade_data TEXT,
                    openrouter_grade_data TEXT,
                    huggingface_grade_data TEXT,
                    local_llm_grade_data TEXT,

                    -- Defects (JSON array)
                    confirmed_defects TEXT,
                    all_detected_defects TEXT,

                    -- Pricing
                    consensus_price REAL,
                    price_range_low REAL,
                    price_range_high REAL,
                    gpa_price_data TEXT,
                    heritage_price_data TEXT,
                    ebay_price_data TEXT,
                    pricing_confidence REAL,
                    market_trend TEXT,

                    -- Buy/Sell Tracking (P&L)
                    buy_price REAL,
                    buy_date TIMESTAMP,
                    buy_source TEXT,
                    sold_price REAL,
                    sold_date TIMESTAMP,
                    sold_to TEXT,
                    sold_platform TEXT,
                    shipping_cost REAL DEFAULT 0,
                    fees_paid REAL DEFAULT 0,

                    -- Images
                    front_image_path TEXT,
                    back_image_path TEXT,
                    front_image_hash TEXT,
                    back_image_hash TEXT,

                    -- Image Quality Scores (JSON)
                    front_quality_score TEXT,
                    back_quality_score TEXT,

                    -- Capture Metadata (JSON)
                    front_capture_metadata TEXT,
                    back_capture_metadata TEXT,

                    -- Notes
                    notes TEXT,
                    investor_notes TEXT,
                    grader_notes TEXT,

                    -- Timestamps
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_graded TIMESTAMP,
                    last_priced TIMESTAMP,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    -- Export Status
                    published_to_portal BOOLEAN DEFAULT 0,
                    portal_published_at TIMESTAMP,

                    -- Search optimization
                    search_text TEXT,

                    -- Extended AI-extracted metadata (JSON)
                    comic_metadata TEXT,
                    key_issue_info TEXT,

                    -- Creative team
                    writer TEXT,
                    cover_artist TEXT,
                    interior_artist TEXT,
                    editor TEXT,

                    -- Additional details
                    cover_date TEXT,
                    cover_price TEXT,
                    era TEXT,
                    characters TEXT,
                    genre TEXT,
                    story_title TEXT,
                    format TEXT,
                    series_type TEXT
                )
            ''')

            # Grading history table
            c.execute('''
                CREATE TABLE IF NOT EXISTS grading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comic_id INTEGER NOT NULL,
                    grade_data TEXT NOT NULL,
                    graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    grade_type TEXT DEFAULT 'auto',
                    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE
                )
            ''')

            # Pricing history table
            c.execute('''
                CREATE TABLE IF NOT EXISTS pricing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comic_id INTEGER NOT NULL,
                    price_data TEXT NOT NULL,
                    priced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE
                )
            ''')

            # AI provider performance tracking
            c.execute('''
                CREATE TABLE IF NOT EXISTS ai_provider_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model TEXT,
                    request_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    avg_response_time_ms REAL DEFAULT 0,
                    total_tokens_used INTEGER DEFAULT 0,
                    last_used TIMESTAMP,
                    last_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Export history
            c.execute('''
                CREATE TABLE IF NOT EXISTS export_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    export_type TEXT NOT NULL,
                    comic_count INTEGER NOT NULL,
                    file_path TEXT,
                    exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')

            # Collections table - for grouping items (Comics, Baseball Cards, etc.)
            c.execute('''
                CREATE TABLE IF NOT EXISTS collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    collection_type TEXT NOT NULL DEFAULT 'comics',
                    description TEXT,
                    icon TEXT DEFAULT '📚',
                    color TEXT DEFAULT '#6366f1',
                    item_count INTEGER DEFAULT 0,
                    total_value REAL DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Collection types - extensible for future item types
            c.execute('''
                CREATE TABLE IF NOT EXISTS collection_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type_name TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    icon TEXT DEFAULT '📦',
                    grading_scale TEXT DEFAULT 'cgc',
                    fields_schema TEXT,
                    is_enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert default collection types
            c.execute('''
                INSERT OR IGNORE INTO collection_types (type_name, display_name, icon, grading_scale)
                VALUES
                    ('comics', 'Comic Books', '📚', 'cgc'),
                    ('baseball_cards', 'Baseball Cards', '⚾', 'psa'),
                    ('sports_cards', 'Sports Cards', '🏆', 'psa'),
                    ('trading_cards', 'Trading Cards', '🃏', 'psa'),
                    ('coins', 'Coins', '🪙', 'ngc'),
                    ('stamps', 'Stamps', '📮', 'philatelic'),
                    ('vinyl', 'Vinyl Records', '💿', 'goldmine'),
                    ('action_figures', 'Action Figures', '🦸', 'afa'),
                    ('toys', 'Toys & Collectible Figures', '🧸', 'afa'),
                    ('signed_books', 'Signed & First Edition Books', '✍️', 'bibliophile'),
                    ('art', 'Art & Prints', '🎨', 'art_grading'),
                    ('other', 'Other Collectibles', '📦', 'generic')
            ''')

            # System configuration
            c.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Batch jobs tracking
            c.execute('''
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    total_items INTEGER DEFAULT 0,
                    processed_items INTEGER DEFAULT 0,
                    successful_items INTEGER DEFAULT 0,
                    failed_items INTEGER DEFAULT 0,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_log TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Migration: Add collection_id to existing comics table if not present
            c.execute("PRAGMA table_info(comics)")
            columns = [col[1] for col in c.fetchall()]
            if 'collection_id' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN collection_id INTEGER')

            # Migration: Add extended metadata columns
            new_metadata_cols = [
                ('comic_metadata', 'TEXT'),
                ('key_issue_info', 'TEXT'),
                ('writer', 'TEXT'),
                ('cover_artist', 'TEXT'),
                ('interior_artist', 'TEXT'),
                ('editor', 'TEXT'),
                ('cover_date', 'TEXT'),
                ('cover_price', 'TEXT'),
                ('era', 'TEXT'),
                ('characters', 'TEXT'),
                ('genre', 'TEXT'),
                ('story_title', 'TEXT'),
                ('format', 'TEXT'),
                ('series_type', 'TEXT'),
            ]
            for col_name, col_type in new_metadata_cols:
                if col_name not in columns:
                    c.execute(f'ALTER TABLE comics ADD COLUMN {col_name} {col_type}')
                    logger.info(f"Added column {col_name} to comics table")

            # Migration: Add buy/sell tracking columns
            if 'buy_price' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN buy_price REAL')
            if 'buy_date' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN buy_date TIMESTAMP')
            if 'buy_source' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN buy_source TEXT')
            if 'sold_price' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN sold_price REAL')
            if 'sold_date' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN sold_date TIMESTAMP')
            if 'sold_to' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN sold_to TEXT')
            if 'sold_platform' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN sold_platform TEXT')
            if 'shipping_cost' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN shipping_cost REAL DEFAULT 0')
            if 'fees_paid' not in columns:
                c.execute('ALTER TABLE comics ADD COLUMN fees_paid REAL DEFAULT 0')

            # Migration: Add grading_status column for tracking grading workflow
            # Values: 'pending', 'graded', 'needs_review', 'failed'
            if 'grading_status' not in columns:
                c.execute("ALTER TABLE comics ADD COLUMN grading_status TEXT DEFAULT 'pending'")
                # Set existing graded comics to 'graded' status
                c.execute("UPDATE comics SET grading_status = 'graded' WHERE consensus_grade IS NOT NULL")
                logger.info("Added grading_status column and updated existing graded comics")

            conn.commit()

            # Create indexes for performance
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_grade ON comics(consensus_grade DESC)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_price ON comics(consensus_price DESC)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_publisher ON comics(publisher)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_year ON comics(publication_year)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_title ON comics(title)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_key_issue ON comics(key_issue)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_review ON comics(requires_manual_review)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_published ON comics(published_to_portal)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_date ON comics(date_added DESC)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_grading_history_comic ON grading_history(comic_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_pricing_history_comic ON pricing_history(comic_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_collection ON comics(collection_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_collections_active ON collections(is_active)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_comics_grading_status ON comics(grading_status)')

            # Full-text search virtual table
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS comics_fts USING fts5(
                    title, publisher, notes, investor_notes,
                    content='comics',
                    content_rowid='id'
                )
            ''')

            # Triggers to keep FTS in sync
            c.execute('''
                CREATE TRIGGER IF NOT EXISTS comics_ai AFTER INSERT ON comics BEGIN
                    INSERT INTO comics_fts(rowid, title, publisher, notes, investor_notes)
                    VALUES (new.id, new.title, new.publisher, new.notes, new.investor_notes);
                END
            ''')

            c.execute('''
                CREATE TRIGGER IF NOT EXISTS comics_ad AFTER DELETE ON comics BEGIN
                    INSERT INTO comics_fts(comics_fts, rowid, title, publisher, notes, investor_notes)
                    VALUES ('delete', old.id, old.title, old.publisher, old.notes, old.investor_notes);
                END
            ''')

            c.execute('''
                CREATE TRIGGER IF NOT EXISTS comics_au AFTER UPDATE ON comics BEGIN
                    INSERT INTO comics_fts(comics_fts, rowid, title, publisher, notes, investor_notes)
                    VALUES ('delete', old.id, old.title, old.publisher, old.notes, old.investor_notes);
                    INSERT INTO comics_fts(rowid, title, publisher, notes, investor_notes)
                    VALUES (new.id, new.title, new.publisher, new.notes, new.investor_notes);
                END
            ''')

            conn.commit()
            logger.info("Database initialized successfully")

    def create_comic(self, data: Dict[str, Any]) -> int:
        """Create a new comic entry"""
        with self.get_connection() as conn:
            c = conn.cursor()

            # Build search text
            search_text = f"{data.get('title', '')} {data.get('publisher', '')} {data.get('issue_number', '')}"

            # Use estimated_value as consensus_price if provided
            consensus_price = data.get('consensus_price') or data.get('estimated_value')

            # Determine grading status based on whether a grade is provided
            grading_status = 'graded' if data.get('consensus_grade') else 'pending'

            c.execute('''
                INSERT INTO comics (
                    title, issue_number, publisher, publication_year,
                    variant_cover, variant_description,
                    key_issue, key_issue_reason,
                    front_image_path, back_image_path,
                    consensus_grade, grade_confidence, consensus_price,
                    notes, search_text, grading_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('title'),
                data.get('issue_number'),
                data.get('publisher'),
                data.get('publication_year'),
                data.get('variant_cover', False),
                data.get('variant_description'),
                data.get('key_issue', False),
                data.get('key_issue_reason'),
                data.get('front_image_path'),
                data.get('back_image_path'),
                data.get('consensus_grade'),
                data.get('grade_confidence'),
                consensus_price,
                data.get('notes'),
                search_text,
                grading_status
            ))

            conn.commit()
            return c.lastrowid

    def _parse_json_fields(self, comic: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON string fields into Python objects"""
        json_fields = [
            'comic_metadata', 'key_issue_info', 'confirmed_defects', 'all_detected_defects',
            'claude_grade_data', 'gemini_grade_data', 'openrouter_grade_data',
            'huggingface_grade_data', 'local_llm_grade_data',
            'gpa_price_data', 'heritage_price_data', 'ebay_price_data',
            'front_quality_score', 'back_quality_score',
            'front_capture_metadata', 'back_capture_metadata',
            'characters', 'genre'
        ]
        for field in json_fields:
            if field in comic and comic[field] and isinstance(comic[field], str):
                try:
                    comic[field] = json.loads(comic[field])
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string if not valid JSON
        return comic

    def get_comic(self, comic_id: int) -> Optional[Dict[str, Any]]:
        """Get comic by ID"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM comics WHERE id = ?', (comic_id,))
            row = c.fetchone()
            if row:
                return self._parse_json_fields(dict(row))
            return None

    def update_comic(self, comic_id: int, data: Dict[str, Any]) -> bool:
        """Update comic entry"""
        with self.get_connection() as conn:
            c = conn.cursor()

            # Field name mapping (frontend names -> database columns)
            field_mapping = {
                'year': 'publication_year',
                'grade': 'consensus_grade',
                'price': 'consensus_price',
                'issue': 'issue_number',
            }

            # Build dynamic update query
            fields = []
            values = []
            for key, value in data.items():
                if key != 'id':
                    # Map frontend field names to database column names
                    db_column = field_mapping.get(key, key)
                    fields.append(f"{db_column} = ?")
                    values.append(json.dumps(value) if isinstance(value, (dict, list)) else value)

            if not fields:
                return False

            fields.append("last_modified = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(comic_id)

            query = f"UPDATE comics SET {', '.join(fields)} WHERE id = ?"
            c.execute(query, values)
            conn.commit()
            return c.rowcount > 0

    def update_grading(self, comic_id: int, grade_data: Dict[str, Any]) -> bool:
        """Update comic grading data including extended AI-extracted metadata"""
        with self.get_connection() as conn:
            c = conn.cursor()

            # Extract comic_info for extended metadata
            comic_info = grade_data.get('comic_info', {})
            key_issue_info = grade_data.get('key_issue_info', {})

            # Handle list fields - convert to JSON strings
            # Helper function to safely convert list/value to string
            def safe_string(val):
                if val is None:
                    return None
                if isinstance(val, list):
                    return json.dumps(val)
                return str(val)

            writer = safe_string(comic_info.get('writer'))
            cover_artist = safe_string(comic_info.get('cover_artist'))
            interior_artist = safe_string(comic_info.get('interior_artist'))
            editor = safe_string(comic_info.get('editor'))
            characters = safe_string(comic_info.get('characters'))
            genre = safe_string(comic_info.get('genre'))
            story_title = safe_string(comic_info.get('story_title'))

            c.execute('''
                UPDATE comics SET
                    consensus_grade = ?,
                    grade_label = ?,
                    grade_confidence = ?,
                    front_grade = ?,
                    back_grade = ?,
                    agreement_percentage = ?,
                    standard_deviation = ?,
                    quality_adjusted = ?,
                    quality_penalty = ?,
                    requires_manual_review = ?,
                    review_reason = ?,
                    confirmed_defects = ?,
                    claude_grade_data = ?,
                    gemini_grade_data = ?,
                    openrouter_grade_data = ?,
                    huggingface_grade_data = ?,
                    comic_metadata = ?,
                    key_issue_info = ?,
                    writer = ?,
                    cover_artist = ?,
                    interior_artist = ?,
                    editor = ?,
                    cover_date = ?,
                    cover_price = ?,
                    era = ?,
                    characters = ?,
                    genre = ?,
                    story_title = ?,
                    format = ?,
                    series_type = ?,
                    key_issue = ?,
                    key_issue_reason = ?,
                    grading_status = ?,
                    last_graded = ?,
                    last_modified = ?
                WHERE id = ?
            ''', (
                grade_data.get('consensus_grade'),
                grade_data.get('grade_label'),
                grade_data.get('confidence'),
                grade_data.get('front_grade'),
                grade_data.get('back_grade'),
                grade_data.get('agreement_percentage'),
                grade_data.get('standard_deviation'),
                grade_data.get('quality_adjusted', False),
                grade_data.get('quality_penalty', 0),
                grade_data.get('requires_manual_review', False),
                grade_data.get('review_reason'),
                json.dumps(grade_data.get('confirmed_defects', [])),
                json.dumps(grade_data.get('individual_grades', {}).get('claude')),
                json.dumps(grade_data.get('individual_grades', {}).get('gemini')),
                json.dumps(grade_data.get('individual_grades', {}).get('openrouter')),
                json.dumps(grade_data.get('individual_grades', {}).get('huggingface')),
                json.dumps(comic_info),  # Full comic metadata as JSON
                json.dumps(key_issue_info),  # Key issue info as JSON
                writer,
                cover_artist,
                interior_artist,
                editor,
                comic_info.get('cover_date'),
                comic_info.get('cover_price'),
                comic_info.get('era'),
                characters,
                genre,
                story_title,
                comic_info.get('format'),
                comic_info.get('series_type'),
                key_issue_info.get('is_key_issue', False),
                json.dumps(key_issue_info.get('key_reasons', [])) if key_issue_info.get('key_reasons') else None,
                'needs_review' if grade_data.get('requires_manual_review') else 'graded',
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                comic_id
            ))

            # Add to grading history
            c.execute('''
                INSERT INTO grading_history (comic_id, grade_data, grade_type)
                VALUES (?, ?, ?)
            ''', (comic_id, json.dumps(grade_data), 'auto'))

            conn.commit()
            return c.rowcount > 0

    def update_pricing(self, comic_id: int, price_data: Dict[str, Any]) -> bool:
        """Update comic pricing data"""
        with self.get_connection() as conn:
            c = conn.cursor()

            c.execute('''
                UPDATE comics SET
                    consensus_price = ?,
                    price_range_low = ?,
                    price_range_high = ?,
                    gpa_price_data = ?,
                    heritage_price_data = ?,
                    ebay_price_data = ?,
                    pricing_confidence = ?,
                    market_trend = ?,
                    last_priced = ?,
                    last_modified = ?
                WHERE id = ?
            ''', (
                price_data.get('consensus_price'),
                price_data.get('price_range_low'),
                price_data.get('price_range_high'),
                json.dumps(price_data.get('gpa_price')),
                json.dumps(price_data.get('heritage_price')),
                json.dumps(price_data.get('ebay_price')),
                price_data.get('confidence'),
                price_data.get('market_trend'),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                comic_id
            ))

            # Add to pricing history
            c.execute('''
                INSERT INTO pricing_history (comic_id, price_data)
                VALUES (?, ?)
            ''', (comic_id, json.dumps(price_data)))

            conn.commit()
            return c.rowcount > 0

    def search_comics(self, query: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        """Advanced search with full-text search and filters"""
        with self.get_connection() as conn:
            c = conn.cursor()

            conditions = ["1=1"]
            params = []

            # Full-text search
            if query.get('search_term'):
                conditions.append("id IN (SELECT rowid FROM comics_fts WHERE comics_fts MATCH ?)")
                params.append(query['search_term'])

            # Publisher filter
            if query.get('publisher'):
                conditions.append("publisher = ?")
                params.append(query['publisher'])

            # Year range
            if query.get('year_min'):
                conditions.append("publication_year >= ?")
                params.append(query['year_min'])
            if query.get('year_max'):
                conditions.append("publication_year <= ?")
                params.append(query['year_max'])

            # Grade range
            if query.get('grade_min') is not None:
                conditions.append("consensus_grade >= ?")
                params.append(query['grade_min'])
            if query.get('grade_max') is not None:
                conditions.append("consensus_grade <= ?")
                params.append(query['grade_max'])

            # Price range
            if query.get('price_min') is not None:
                conditions.append("consensus_price >= ?")
                params.append(query['price_min'])
            if query.get('price_max') is not None:
                conditions.append("consensus_price <= ?")
                params.append(query['price_max'])

            # Boolean filters
            if query.get('key_issues_only'):
                conditions.append("key_issue = 1")
            if query.get('needs_manual_review'):
                conditions.append("requires_manual_review = 1")
            if query.get('not_published'):
                conditions.append("published_to_portal = 0")

            # Grading status filter (pending, graded, needs_review, failed)
            if query.get('grading_status'):
                conditions.append("grading_status = ?")
                params.append(query['grading_status'])

            where_clause = " AND ".join(conditions)

            # Sort
            sort_by = query.get('sort_by', 'date_added')
            sort_order = query.get('sort_order', 'DESC').upper()
            valid_sorts = ['date_added', 'consensus_grade', 'consensus_price', 'title', 'publication_year']
            if sort_by not in valid_sorts:
                sort_by = 'date_added'
            if sort_order not in ['ASC', 'DESC']:
                sort_order = 'DESC'

            # Count total
            count_query = f"SELECT COUNT(*) FROM comics WHERE {where_clause}"
            c.execute(count_query, params)
            total = c.fetchone()[0]

            # Get results with pagination
            limit = min(query.get('limit', 50), 1000)
            offset = query.get('offset', 0)

            select_query = f"""
                SELECT * FROM comics
                WHERE {where_clause}
                ORDER BY {sort_by} {sort_order}
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            c.execute(select_query, params)
            results = [self._parse_json_fields(dict(row)) for row in c.fetchall()]

            return results, total

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        with self.get_connection() as conn:
            c = conn.cursor()

            stats = {}

            # Total counts
            c.execute("SELECT COUNT(*) FROM comics")
            stats['total_comics'] = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM comics WHERE consensus_grade IS NOT NULL")
            stats['total_graded'] = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM comics WHERE requires_manual_review = 1")
            stats['awaiting_review'] = c.fetchone()[0]

            # Average grade
            c.execute("SELECT AVG(consensus_grade) FROM comics WHERE consensus_grade IS NOT NULL")
            avg = c.fetchone()[0]
            stats['average_grade'] = round(avg, 2) if avg else 0
            stats['avg_grade'] = stats['average_grade']  # Alias for frontend

            # Total value - use consensus_price if available, otherwise fall back to buy_price
            c.execute("""
                SELECT SUM(COALESCE(consensus_price, buy_price, 0))
                FROM comics
                WHERE consensus_price IS NOT NULL OR buy_price IS NOT NULL
            """)
            total = c.fetchone()[0]
            stats['total_estimated_value'] = round(total, 2) if total else 0

            # Calculate total raw value based on average grade
            # Raw copies sell for less than graded - the discount depends on grade level
            avg_grade = stats['average_grade'] or 6.0
            if avg_grade >= 9.8:
                raw_multiplier = 0.40
            elif avg_grade >= 9.4:
                raw_multiplier = 0.50
            elif avg_grade >= 9.0:
                raw_multiplier = 0.55
            elif avg_grade >= 7.0:
                raw_multiplier = 0.60
            elif avg_grade >= 4.0:
                raw_multiplier = 0.70
            else:
                raw_multiplier = 0.80

            stats['total_raw_value'] = round((stats['total_estimated_value'] or 0) * raw_multiplier, 2)

            # Grades by time period
            now = datetime.utcnow()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            c.execute("SELECT COUNT(*) FROM comics WHERE last_graded >= ?", (today.isoformat(),))
            stats['grades_today'] = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM comics WHERE last_graded >= ?", (week_ago.isoformat(),))
            stats['grades_this_week'] = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM comics WHERE last_graded >= ?", (month_ago.isoformat(),))
            stats['grades_this_month'] = c.fetchone()[0]

            # Publisher breakdown
            c.execute("""
                SELECT publisher, COUNT(*) as count
                FROM comics
                WHERE publisher IS NOT NULL
                GROUP BY publisher
                ORDER BY count DESC
                LIMIT 10
            """)
            stats['top_publishers'] = [{'publisher': row[0], 'count': row[1]} for row in c.fetchall()]

            # Grade distribution
            c.execute("""
                SELECT
                    CASE
                        WHEN consensus_grade >= 9.0 THEN 'Near Mint+'
                        WHEN consensus_grade >= 8.0 THEN 'Very Fine'
                        WHEN consensus_grade >= 6.0 THEN 'Fine'
                        WHEN consensus_grade >= 4.0 THEN 'Very Good'
                        WHEN consensus_grade >= 2.0 THEN 'Good'
                        ELSE 'Poor'
                    END as grade_range,
                    COUNT(*) as count
                FROM comics
                WHERE consensus_grade IS NOT NULL
                GROUP BY grade_range
            """)
            stats['grade_distribution'] = {row[0]: row[1] for row in c.fetchall()}

            # AI provider stats
            c.execute("SELECT * FROM ai_provider_stats")
            stats['ai_provider_stats'] = [dict(row) for row in c.fetchall()]

            return stats

    def update_ai_provider_stats(self, provider: str, model: str, success: bool, response_time_ms: int, tokens: int = 0, error: str = None):
        """Update AI provider performance statistics"""
        with self.get_connection() as conn:
            c = conn.cursor()

            c.execute("""
                INSERT INTO ai_provider_stats (provider, model, request_count, success_count, error_count, avg_response_time_ms, total_tokens_used, last_used, last_error)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider) DO UPDATE SET
                    request_count = request_count + 1,
                    success_count = success_count + ?,
                    error_count = error_count + ?,
                    avg_response_time_ms = (avg_response_time_ms * request_count + ?) / (request_count + 1),
                    total_tokens_used = total_tokens_used + ?,
                    last_used = ?,
                    last_error = COALESCE(?, last_error)
            """, (
                provider, model,
                1 if success else 0,
                0 if success else 1,
                response_time_ms,
                tokens,
                datetime.utcnow().isoformat(),
                error,
                1 if success else 0,
                0 if success else 1,
                response_time_ms,
                tokens,
                datetime.utcnow().isoformat(),
                error
            ))
            conn.commit()

    def delete_comic(self, comic_id: int) -> bool:
        """Delete a comic and all related data"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM comics WHERE id = ?", (comic_id,))
            conn.commit()
            return c.rowcount > 0

    def get_comics_for_export(self, comic_ids: List[int] = None) -> List[Dict[str, Any]]:
        """Get comics ready for export"""
        with self.get_connection() as conn:
            c = conn.cursor()

            if comic_ids:
                placeholders = ','.join(['?' for _ in comic_ids])
                query = f"SELECT * FROM comics WHERE id IN ({placeholders}) AND consensus_grade IS NOT NULL"
                c.execute(query, comic_ids)
            else:
                c.execute("SELECT * FROM comics WHERE published_to_portal = 1 AND consensus_grade IS NOT NULL")

            return [dict(row) for row in c.fetchall()]

    def mark_as_published(self, comic_ids: List[int]) -> int:
        """Mark comics as published to portal"""
        with self.get_connection() as conn:
            c = conn.cursor()

            placeholders = ','.join(['?' for _ in comic_ids])
            c.execute(f"""
                UPDATE comics
                SET published_to_portal = 1, portal_published_at = ?
                WHERE id IN ({placeholders})
            """, [datetime.utcnow().isoformat()] + comic_ids)

            conn.commit()
            return c.rowcount

    def get_grading_history(self, comic_id: int) -> List[Dict[str, Any]]:
        """Get grading history for a comic"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM grading_history
                WHERE comic_id = ?
                ORDER BY graded_at DESC
            """, (comic_id,))
            return [dict(row) for row in c.fetchall()]

    def get_pricing_history(self, comic_id: int) -> List[Dict[str, Any]]:
        """Get pricing history for a comic"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM pricing_history
                WHERE comic_id = ?
                ORDER BY priced_at DESC
            """, (comic_id,))
            return [dict(row) for row in c.fetchall()]

    def cleanup_old_history(self, days: int = 90):
        """Remove old history records"""
        with self.get_connection() as conn:
            c = conn.cursor()
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

            c.execute("DELETE FROM grading_history WHERE graded_at < ?", (cutoff,))
            c.execute("DELETE FROM pricing_history WHERE priced_at < ?", (cutoff,))

            conn.commit()
            logger.info(f"Cleaned up history older than {days} days")

    def vacuum(self):
        """Optimize database"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            logger.info("Database optimized")

    # ===========================================
    # Collection Management Methods
    # ===========================================

    def create_collection(self, data: Dict[str, Any]) -> int:
        """Create a new collection"""
        with self.get_connection() as conn:
            c = conn.cursor()

            # Check if this is the first collection - make it default
            c.execute("SELECT COUNT(*) FROM collections")
            is_first = c.fetchone()[0] == 0

            c.execute('''
                INSERT INTO collections (
                    name, collection_type, description, icon, color, is_default, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('collection_type', 'comics'),
                data.get('description'),
                data.get('icon', '📚'),
                data.get('color', '#6366f1'),
                is_first or data.get('is_default', False),
                data.get('sort_order', 0)
            ))

            conn.commit()
            return c.lastrowid

    def get_collection(self, collection_id: int) -> Optional[Dict[str, Any]]:
        """Get collection by ID"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM collections WHERE id = ?', (collection_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_all_collections(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all collections"""
        with self.get_connection() as conn:
            c = conn.cursor()
            if include_inactive:
                c.execute('SELECT * FROM collections ORDER BY sort_order, name')
            else:
                c.execute('SELECT * FROM collections WHERE is_active = 1 ORDER BY sort_order, name')
            return [dict(row) for row in c.fetchall()]

    def update_collection(self, collection_id: int, data: Dict[str, Any]) -> bool:
        """Update collection"""
        with self.get_connection() as conn:
            c = conn.cursor()

            fields = []
            values = []
            for key, value in data.items():
                if key not in ('id', 'created_at'):
                    fields.append(f"{key} = ?")
                    values.append(value)

            if not fields:
                return False

            fields.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(collection_id)

            query = f"UPDATE collections SET {', '.join(fields)} WHERE id = ?"
            c.execute(query, values)
            conn.commit()
            return c.rowcount > 0

    def delete_collection(self, collection_id: int, move_items_to: int = None) -> bool:
        """Delete collection, optionally moving items to another collection"""
        with self.get_connection() as conn:
            c = conn.cursor()

            # Check if collection exists
            c.execute('SELECT is_default FROM collections WHERE id = ?', (collection_id,))
            row = c.fetchone()
            if not row:
                return False

            if row[0]:  # is_default
                logger.warning("Cannot delete default collection")
                return False

            if move_items_to:
                # Move items to another collection
                c.execute('UPDATE comics SET collection_id = ? WHERE collection_id = ?',
                         (move_items_to, collection_id))
            else:
                # Set items to no collection
                c.execute('UPDATE comics SET collection_id = NULL WHERE collection_id = ?',
                         (collection_id,))

            c.execute('DELETE FROM collections WHERE id = ?', (collection_id,))
            conn.commit()
            return c.rowcount > 0

    def set_default_collection(self, collection_id: int) -> bool:
        """Set a collection as the default"""
        with self.get_connection() as conn:
            c = conn.cursor()

            # Unset current default
            c.execute('UPDATE collections SET is_default = 0 WHERE is_default = 1')

            # Set new default
            c.execute('UPDATE collections SET is_default = 1 WHERE id = ?', (collection_id,))

            conn.commit()
            return c.rowcount > 0

    def get_default_collection(self) -> Optional[Dict[str, Any]]:
        """Get the default collection"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM collections WHERE is_default = 1 LIMIT 1')
            row = c.fetchone()
            return dict(row) if row else None

    def update_collection_stats(self, collection_id: int) -> bool:
        """Update collection item count and total value"""
        with self.get_connection() as conn:
            c = conn.cursor()

            c.execute('''
                UPDATE collections SET
                    item_count = (SELECT COUNT(*) FROM comics WHERE collection_id = ?),
                    total_value = (SELECT COALESCE(SUM(consensus_price), 0) FROM comics WHERE collection_id = ? AND consensus_price IS NOT NULL),
                    updated_at = ?
                WHERE id = ?
            ''', (collection_id, collection_id, datetime.utcnow().isoformat(), collection_id))

            conn.commit()
            return c.rowcount > 0

    def get_collection_types(self) -> List[Dict[str, Any]]:
        """Get all available collection types"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM collection_types WHERE is_enabled = 1 ORDER BY display_name')
            return [dict(row) for row in c.fetchall()]

    def get_collection_statistics(self, collection_id: int = None) -> Dict[str, Any]:
        """Get statistics for a specific collection or all collections"""
        with self.get_connection() as conn:
            c = conn.cursor()

            collection_filter = ""
            params = []
            if collection_id:
                collection_filter = "WHERE collection_id = ?"
                params = [collection_id]

            stats = {}

            c.execute(f"SELECT COUNT(*) FROM comics {collection_filter}", params)
            stats['total_items'] = c.fetchone()[0]

            c.execute(f"SELECT COUNT(*) FROM comics {collection_filter} {'AND' if collection_filter else 'WHERE'} consensus_grade IS NOT NULL",
                     params if collection_filter else [])
            stats['total_graded'] = c.fetchone()[0]

            c.execute(f"SELECT COALESCE(SUM(consensus_price), 0) FROM comics {collection_filter} {'AND' if collection_filter else 'WHERE'} consensus_price IS NOT NULL",
                     params if collection_filter else [])
            stats['total_value'] = c.fetchone()[0]

            c.execute(f"SELECT AVG(consensus_grade) FROM comics {collection_filter} {'AND' if collection_filter else 'WHERE'} consensus_grade IS NOT NULL",
                     params if collection_filter else [])
            avg = c.fetchone()[0]
            stats['average_grade'] = round(avg, 2) if avg else 0

            return stats

    def move_items_to_collection(self, item_ids: List[int], target_collection_id: int) -> int:
        """Move multiple items to a collection"""
        with self.get_connection() as conn:
            c = conn.cursor()

            placeholders = ','.join(['?' for _ in item_ids])
            c.execute(f'UPDATE comics SET collection_id = ? WHERE id IN ({placeholders})',
                     [target_collection_id] + item_ids)

            conn.commit()
            return c.rowcount

    # ========================================
    # System Configuration / User Profile
    # ========================================

    def get_config(self, key: str) -> Optional[str]:
        """Get a configuration value by key"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT value FROM system_config WHERE key = ?', (key,))
            row = c.fetchone()
            return row['value'] if row else None

    def set_config(self, key: str, value: str) -> bool:
        """Set a configuration value (upsert)"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO system_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
            ''', (key, value))
            conn.commit()
            return True

    def get_user_profile(self) -> Dict[str, Any]:
        """Get the user profile settings"""
        profile_json = self.get_config('user_profile')
        if profile_json:
            try:
                return json.loads(profile_json)
            except json.JSONDecodeError:
                pass
        # Return default profile
        return {
            'display_name': '',
            'store_name': '',
            'collector_type': 'hobbyist',  # hobbyist, dealer, investor
            'favorite_publishers': [],
            'voice_preference': 'bree',  # bree, collection_master
            'greeting_style': 'casual'  # casual, formal, sassy
        }

    def save_user_profile(self, profile: Dict[str, Any]) -> bool:
        """Save the user profile settings"""
        return self.set_config('user_profile', json.dumps(profile))

    def get_all_configs(self) -> Dict[str, Any]:
        """Get all configuration key-value pairs"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT key, value FROM system_config')
            rows = c.fetchall()
            return {row['key']: row['value'] for row in rows}


# Global instance
db = DatabaseManager()


def init_database():
    """Initialize database (convenience function)"""
    return db


def get_db():
    """Get database instance (for dependency injection)"""
    return db

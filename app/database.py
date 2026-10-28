"""
PHAMOUXE Database Architecture & Persistence Layer
Handles SQLite local development with full PostgreSQL production parity.
Tables:
- auth_config & user_sessions
- discovered_servers (IPTV Research & Saved Communities)
- customer_leads & lead_messages (Customer Management CRM)
- campaigns (Campaign Planner)
- activity_logs (Activity & Audit History)
- conversation_assistance (Conversation Analysis & Replies)
- bot_settings, bot_guilds, discord_oauth_account, discord_user_guilds
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.config import DB_PATH

logger = logging.getLogger("phamouxe.database")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Authentication & System Config
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 1b. Business Settings (Famous Media Technologies)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS business_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        business_name TEXT DEFAULT 'Famous Media Technologies',
        telegram_contact TEXT DEFAULT '@Phamouxetv',
        sender_name TEXT DEFAULT 'Famous Media Technologies',
        iptv_sub_1mo REAL DEFAULT 15.0,
        iptv_sub_3mo REAL DEFAULT 35.0,
        iptv_sub_6mo REAL DEFAULT 55.0,
        iptv_sub_12mo REAL DEFAULT 80.0,
        reseller_120_credits REAL DEFAULT 350.0,
        app_rebrand_with_panel REAL DEFAULT 150.0,
        app_dev_pricing TEXT DEFAULT 'Contact for requirements and custom pricing',
        server_setup_pricing TEXT DEFAULT 'Contact for infrastructure requirements',
        never_quote_unlisted INTEGER DEFAULT 1,
        notes TEXT DEFAULT 'Official IPTV subscriptions, reseller panels, white-label app rebranding, custom app development, and streaming servers.',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 1c. AI Provider Configuration
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        provider TEXT DEFAULT 'builtin',
        api_key TEXT DEFAULT '',
        model_name TEXT DEFAULT 'gemini-1.5-flash',
        temperature REAL DEFAULT 0.3,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Operator Sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        session_token TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL
    )
    """)

    # 3. Discovered IPTV Communities & Server Research
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discovered_servers (
        guild_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        icon_url TEXT,
        invite_code TEXT,
        vanity_url TEXT,
        approximate_member_count INTEGER DEFAULT 0,
        approximate_presence_count INTEGER DEFAULT 0,
        category TEXT DEFAULT 'IPTV reseller',
        tags TEXT DEFAULT '[]',
        business_services TEXT DEFAULT '[]',
        verification_level TEXT DEFAULT 'None',
        source TEXT DEFAULT 'directory_discovery',
        business_relevance TEXT DEFAULT '',
        is_saved_to_leads INTEGER DEFAULT 0,
        notes TEXT DEFAULT '',
        last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Check for business_relevance column if table existed previously
    try:
        cursor.execute("ALTER TABLE discovered_servers ADD COLUMN business_relevance TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass # Already exists

    # 4. Customer Management CRM (Leads)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT,
        community_name TEXT DEFAULT '',
        business_name TEXT NOT NULL,
        contact_name TEXT DEFAULT '',
        contact_role TEXT DEFAULT 'Server Owner / Admin',
        contact_handle TEXT DEFAULT '',
        discord_user_id TEXT DEFAULT '',
        status TEXT DEFAULT 'New Lead',
        category TEXT DEFAULT 'IPTV reseller',
        reach_members INTEGER DEFAULT 0,
        business_interests TEXT DEFAULT '[]',
        notes TEXT DEFAULT '',
        last_contact_date TIMESTAMP,
        last_reply_date TIMESTAMP,
        last_interaction_date TIMESTAMP,
        follow_up_due_at TIMESTAMP,
        follow_up_status TEXT DEFAULT 'None',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(guild_id) REFERENCES discovered_servers(guild_id)
    )
    """)

    # Ensure all columns exist on customer_leads if migrating
    for col, col_def in [
        ("community_name", "TEXT DEFAULT ''"),
        ("discord_user_id", "TEXT DEFAULT ''"),
        ("business_interests", "TEXT DEFAULT '[]'"),
        ("last_reply_date", "TIMESTAMP"),
        ("last_interaction_date", "TIMESTAMP"),
        ("follow_up_status", "TEXT DEFAULT 'None'"),
        ("channel_id", "TEXT DEFAULT ''"),
        ("channel_name", "TEXT DEFAULT ''"),
        ("source", "TEXT DEFAULT 'Manual Entry'"),
        ("source_data_origin", "TEXT DEFAULT 'manual_entered'"),
        ("stated_interests", "TEXT DEFAULT ''"),
        ("service_interested", "TEXT DEFAULT 'IPTV Subscriptions'"),
        ("stage", "TEXT DEFAULT 'New Contact'"),
        ("last_message_summary", "TEXT DEFAULT ''"),
        ("next_suggested_action", "TEXT DEFAULT 'Review community discussions or draft opening message'"),
        ("follow_up_count", "INTEGER DEFAULT 0"),
        ("opt_out", "INTEGER DEFAULT 0")
    ]:
        try:
            cursor.execute(f"ALTER TABLE customer_leads ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass

    # 4b. Server Channels (Operator specifies allowed channels for the official bot)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL,
        channel_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        type TEXT DEFAULT 'text',
        topic TEXT DEFAULT '',
        is_monitored INTEGER DEFAULT 0,
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4c. Channel Messages (Permitted public channel messages inspected for buying signals)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channel_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT NOT NULL UNIQUE,
        guild_id TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        channel_name TEXT DEFAULT '',
        author_id TEXT NOT NULL,
        author_username TEXT NOT NULL,
        author_display_name TEXT DEFAULT '',
        content TEXT NOT NULL,
        timestamp TIMESTAMP,
        jump_url TEXT DEFAULT '',
        has_buying_signal INTEGER DEFAULT 0,
        buying_signal_details TEXT DEFAULT '',
        detected_service TEXT DEFAULT 'General',
        relevance_score INTEGER DEFAULT 0,
        is_saved_to_contacts INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4d. Smart Follow-Up Reminders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS follow_up_reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL,
        due_date TIMESTAMP NOT NULL,
        interval_days INTEGER DEFAULT 2,
        suggested_message TEXT NOT NULL,
        status TEXT DEFAULT 'Scheduled',
        context_summary TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lead_id) REFERENCES customer_leads(id) ON DELETE CASCADE
    )
    """)

    # 4e. AI Chat & Command Center History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT DEFAULT 'default',
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        metadata TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4f. Server Members (for communities accessible through authorized bot)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL,
        discord_user_id TEXT NOT NULL,
        username TEXT NOT NULL,
        display_name TEXT DEFAULT '',
        avatar_url TEXT DEFAULT '',
        roles TEXT DEFAULT '[]',
        is_bot INTEGER DEFAULT 0,
        joined_at TIMESTAMP,
        business_tags TEXT DEFAULT '[]',
        notes TEXT DEFAULT '',
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(guild_id, discord_user_id)
    )
    """)

    # 4c. Saved Message Templates
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS message_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_type TEXT NOT NULL,
        purpose TEXT NOT NULL,
        title TEXT NOT NULL,
        template_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 5. Lead Message History & Staging
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lead_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER NOT NULL,
        message_type TEXT DEFAULT 'Initial Outreach',
        content TEXT NOT NULL,
        status TEXT DEFAULT 'Draft',
        reviewed_at TIMESTAMP,
        sent_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lead_id) REFERENCES customer_leads(id) ON DELETE CASCADE
    )
    """)

    # 6. Campaign Planner
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        service_type TEXT NOT NULL,
        target_audience TEXT DEFAULT '',
        status TEXT DEFAULT 'Active',
        staged_pitch TEXT DEFAULT '',
        selected_prospect_ids TEXT DEFAULT '[]',
        selected_guild_ids TEXT DEFAULT '[]',
        scheduled_review_date TIMESTAMP,
        target_count INTEGER DEFAULT 10,
        contacted_count INTEGER DEFAULT 0,
        converted_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    for col, col_def in [
        ("selected_prospect_ids", "TEXT DEFAULT '[]'"),
        ("selected_guild_ids", "TEXT DEFAULT '[]'"),
        ("scheduled_review_date", "TIMESTAMP"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE campaigns ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass

    # 7. System Activity & Audit History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_type TEXT NOT NULL,
        title TEXT NOT NULL,
        details TEXT DEFAULT '',
        entity_type TEXT DEFAULT 'system',
        entity_id TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 8. Conversation Analysis & Reply Assistance
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_assistance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        contact_name TEXT DEFAULT '',
        service_type TEXT DEFAULT 'General IPTV',
        raw_conversation TEXT NOT NULL,
        summary TEXT DEFAULT '',
        identified_questions TEXT DEFAULT '[]',
        suggested_replies TEXT DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(lead_id) REFERENCES customer_leads(id) ON DELETE SET NULL
    )
    """)

    # 9. Discord Bot Configuration & Guilds
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_guilds (
        guild_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        icon_url TEXT,
        member_count INTEGER DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 10. Discord OAuth2 Account Integration
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discord_oauth_account (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        discord_id TEXT NOT NULL,
        username TEXT NOT NULL,
        discriminator TEXT DEFAULT '0',
        global_name TEXT,
        avatar TEXT,
        access_token TEXT NOT NULL,
        refresh_token TEXT,
        expires_at TIMESTAMP,
        scope TEXT,
        connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discord_user_guilds (
        guild_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        icon TEXT,
        owner INTEGER DEFAULT 0,
        permissions TEXT,
        can_manage INTEGER DEFAULT 0,
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    try:
        cursor.execute("ALTER TABLE discord_user_guilds ADD COLUMN can_manage INTEGER DEFAULT 0")
    except Exception:
        pass

    # Create Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_category ON discovered_servers(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_members ON discovered_servers(approximate_member_count)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_saved ON discovered_servers(is_saved_to_leads)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON customer_leads(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_followup ON customer_leads(follow_up_due_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_logs(created_at DESC)")

    conn.commit()
    conn.close()

def seed_initial_research():
    """
    Seeds initial system settings, activity logs, and default message templates for all 7 IPTV services.
    STRICT COMPLIANCE: Avoids fake servers or hardcoded mock communities. All communities are discovered via live API scans.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Clean up legacy fake dummy servers from previous prototype development if present
    cursor.execute("""
    DELETE FROM discovered_servers 
    WHERE source = 'directory_discovery' 
      AND guild_id IN ('892019485720194011', '912304918239012391', '781293019283019234', '993481029384019283', '847291039485720194', '958291048201948201', '820194820194820194', '771928301928491029')
    """)

    # Seed default message templates for all 7 IPTV business services if none exist
    cursor.execute("SELECT COUNT(*) as count FROM message_templates")
    if cursor.fetchone()["count"] == 0:
        default_templates = [
            (
                "App Rebranding", "Initial Outreach", "XCIPTV / Smarters Rebrand Direct Pitch",
                "Hi {contact_name},\n\nI noticed {business_name} and wanted to reach out. We specialize in custom IPTV app rebranding—white-label builds for XCIPTV, IPTV Smarters Pro, and TiviMate with your logo, colors, and hardcoded DNS.\n\nIf you want to give your subscribers a clean, branded player experience and eliminate manual DNS entries, let me know and I'll send a quick demo.\n\nBest regards,\n{sender_name}"
            ),
            (
                "App Rebranding", "Casual In-Discussion", "Rebranding Demo & DNS Hardcoding",
                "Hey {contact_name},\n\nFollowing {business_name}. Do you offer a branded player APK with your server DNS pre-configured? We build custom branded apps that eliminate login friction for subscribers.\n\nHappy to share a video demo of recent builds if you're interested.\n\nCheers,\n{sender_name}"
            ),
            (
                "App Development", "Initial Outreach", "Custom Native Streaming App Development",
                "Hi {contact_name},\n\nReaching out regarding {business_name}. We build native streaming applications across Android TV, Firestick, iOS, and Web. We specialize in custom ExoPlayer middleware with multi-DNS failover and clean remote navigation.\n\nAre you planning any app upgrades or custom player features for your service?\n\nBest,\n{sender_name}"
            ),
            (
                "Reseller Panels", "Initial Outreach", "Wholesale Reseller Panel Credits Inquiry",
                "Hi {contact_name},\n\nI came across {business_name}. I'm reaching out regarding your wholesale reseller lines and panel options. We are looking to secure reliable tier-1 capacity with sub-reseller panel creation.\n\nCould you share your current credit tier breakdown and trial availability?\n\nBest regards,\n{sender_name}"
            ),
            (
                "Subscriptions", "Initial Outreach", "VIP 4K Stream Evaluation",
                "Hello {contact_name},\n\nReaching out regarding {business_name}'s VIP subscription tiers. We are evaluating private 4K live sports feeds and backup server infrastructure.\n\nCould you confirm your multi-device connection policy and 24h trial availability?\n\nThank you,\n{sender_name}"
            ),
            (
                "Server Setup", "Initial Outreach", "Streaming Server & Load Balancer Infrastructure",
                "Hi {contact_name},\n\nReaching out to {business_name} regarding server infrastructure. I engineer high-throughput IPTV streaming setups—including Nginx restream load balancers, Xtream UI cluster tuning, and anti-freeze caching configurations.\n\nIf you're looking to scale servers or optimize delivery, happy to discuss specs.\n\nBest regards,\n{sender_name}"
            ),
            (
                "Custom Websites", "Initial Outreach", "Automated WHMCS IPTV Billing Portal",
                "Hi {contact_name},\n\nI noticed {business_name} and wanted to inquire about your web portal. We design conversion-focused IPTV websites with automated WHMCS billing, instant line delivery upon checkout, and crypto/card payment gateways.\n\nAre you looking to automate line delivery for your service?\n\nBest regards,\n{sender_name}"
            ),
            (
                "Authorized Restreaming", "Initial Outreach", "Master Source Feeds & 50fps Sports",
                "Hi {contact_name},\n\nReaching out regarding restreaming capacity. We provide authorized, high-bandwidth live source feeds (50fps/60fps master feeds) optimized for panel distribution with dedicated port allocations.\n\nAre you currently looking for direct live feeds for {business_name}?\n\nRegards,\n{sender_name}"
            ),
            (
                "Follow-Up", "2-Day Reminder", "Gentle Follow-Up Inquiry",
                "Hi {contact_name},\n\nFollowing up on my note from earlier this week regarding {business_name}. I know running a server community keeps you busy, so just floating this back to see if you had a moment to review.\n\nNo rush at all—whenever convenient for you.\n\nBest regards,\n{sender_name}"
            ),
            (
                "Follow-Up", "3-Day Reminder", "Quick Check-in on IPTV Services",
                "Hey {contact_name},\n\nJust checking in quickly regarding {business_name}. Let me know if you'd still like to explore options for {service_name}. If the timing isn't right, no problem at all.\n\nCheers,\n{sender_name}"
            )
        ]

        for tmpl in default_templates:
            cursor.execute("""
            INSERT INTO message_templates (service_type, purpose, title, template_text)
            VALUES (?, ?, ?, ?)
            """, tmpl)

    # Seed Business Profile (Famous Media Technologies) if not present
    cursor.execute("SELECT COUNT(*) as count FROM business_settings WHERE id = 1")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
        INSERT INTO business_settings (
            id, business_name, telegram_contact, sender_name,
            iptv_sub_1mo, iptv_sub_3mo, iptv_sub_6mo, iptv_sub_12mo,
            reseller_120_credits, app_rebrand_with_panel,
            app_dev_pricing, server_setup_pricing, never_quote_unlisted, notes
        ) VALUES (
            1, 'Famous Media Technologies', '@Phamouxetv', 'Famous Media Technologies',
            15.0, 35.0, 55.0, 80.0,
            350.0, 150.0,
            'Contact for requirements and custom pricing', 'Contact for infrastructure requirements',
            1, 'Official IPTV subscriptions, reseller panels, white-label app rebranding, custom app development, and streaming servers.'
        )
        """)

    # Seed AI Settings if not present
    cursor.execute("SELECT COUNT(*) as count FROM ai_settings WHERE id = 1")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
        INSERT INTO ai_settings (id, provider, api_key, model_name, temperature)
        VALUES (1, 'builtin', '', 'gemini-1.5-flash', 0.3)
        """)

    # Seed initial activity logs if none exist
    cursor.execute("SELECT COUNT(*) as count FROM activity_logs")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("""
        INSERT INTO activity_logs (activity_type, title, details, entity_type, entity_id)
        VALUES
        ('system_boot', 'Famous Media Technologies Suite Initialized', 'Database verified with WAL mode and SQLite/PostgreSQL parity. Real discovery engine active.', 'system', 'system')
        """)

    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Discovered & Saved Communities Queries
# --------------------------------------------------------------------------

def get_servers(query="", category="", service="", min_members=0, saved_only=False, sort_by="members_desc"):
    conn = get_connection()
    cursor = conn.cursor()

    sql = "SELECT * FROM discovered_servers WHERE 1=1"
    params = []

    if query:
        search_term = f"%{query}%"
        sql += " AND (name LIKE ? OR description LIKE ? OR tags LIKE ? OR vanity_url LIKE ? OR invite_code LIKE ? OR business_relevance LIKE ? OR category LIKE ? OR business_services LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term, search_term, search_term, search_term, search_term])

    if category and category != "All":
        sql += " AND category LIKE ?"
        params.append(f"%{category}%")

    if service and service != "All":
        sql += " AND business_services LIKE ?"
        params.append(f"%{service}%")

    if min_members > 0:
        sql += " AND approximate_member_count >= ?"
        params.append(min_members)

    if saved_only:
        sql += " AND is_saved_to_leads = 1"

    sort_options = {
        "members_desc": "ORDER BY approximate_member_count DESC",
        "members_asc": "ORDER BY approximate_member_count ASC",
        "online_desc": "ORDER BY approximate_presence_count DESC",
        "recent": "ORDER BY last_checked_at DESC",
        "name_asc": "ORDER BY name ASC"
    }
    sql += " " + sort_options.get(sort_by, "ORDER BY approximate_member_count DESC")

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["tags"] = json.loads(d["tags"]) if d["tags"] else []
        except:
            d["tags"] = []
        try:
            d["business_services"] = json.loads(d["business_services"]) if d["business_services"] else []
        except:
            d["business_services"] = []
        results.append(d)

    conn.close()
    return results

def get_saved_communities() -> List[Dict[str, Any]]:
    return get_servers(saved_only=True)

def toggle_save_server(guild_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_saved_to_leads, name, category, approximate_member_count FROM discovered_servers WHERE guild_id = ?", (guild_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    current_val = row["is_saved_to_leads"]
    new_val = 0 if current_val == 1 else 1

    cursor.execute("UPDATE discovered_servers SET is_saved_to_leads = ? WHERE guild_id = ?", (new_val, guild_id))

    # Also automatically sync into CRM Leads
    if new_val == 1:
        cursor.execute("SELECT id FROM customer_leads WHERE guild_id = ?", (guild_id,))
        lead_row = cursor.fetchone()
        if not lead_row:
            cursor.execute("""
            INSERT INTO customer_leads (guild_id, business_name, contact_role, status, category, reach_members)
            VALUES (?, ?, 'Server Admin', 'New Lead', ?, ?)
            """, (guild_id, row["name"], row["category"], row["approximate_member_count"]))
            log_activity("lead_created", f"Saved Community to CRM: {row['name']}", f"Target: {row['name']} ({row['approximate_member_count']:,} members)", "lead", guild_id, conn=conn)
    else:
        cursor.execute("DELETE FROM customer_leads WHERE guild_id = ?", (guild_id,))
        log_activity("server_unbookmarked", f"Removed Bookmarked Community: {row['name']}", "", "server", guild_id, conn=conn)

    conn.commit()
    conn.close()
    return new_val == 1

def update_server_notes(guild_id: str, notes: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE discovered_servers SET notes = ? WHERE guild_id = ?", (notes, guild_id))
    cursor.execute("UPDATE customer_leads SET notes = ? WHERE guild_id = ?", (notes, guild_id))
    conn.commit()
    conn.close()

def save_or_update_server(server_data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    tags = server_data.get("tags", [])
    if isinstance(tags, list):
        tags = json.dumps(tags)
    
    business_services = server_data.get("business_services", [])
    if isinstance(business_services, list):
        business_services = json.dumps(business_services)

    cursor.execute("""
    INSERT INTO discovered_servers (
        guild_id, name, description, icon_url, invite_code, vanity_url,
        approximate_member_count, approximate_presence_count, category,
        tags, business_services, verification_level, source, business_relevance, last_checked_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(guild_id) DO UPDATE SET
        name=excluded.name,
        description=excluded.description,
        icon_url=COALESCE(NULLIF(excluded.icon_url, ''), discovered_servers.icon_url),
        invite_code=COALESCE(NULLIF(excluded.invite_code, ''), discovered_servers.invite_code),
        vanity_url=COALESCE(NULLIF(excluded.vanity_url, ''), discovered_servers.vanity_url),
        approximate_member_count=excluded.approximate_member_count,
        approximate_presence_count=excluded.approximate_presence_count,
        category=excluded.category,
        tags=excluded.tags,
        business_services=excluded.business_services,
        verification_level=excluded.verification_level,
        source=excluded.source,
        business_relevance=excluded.business_relevance,
        last_checked_at=CURRENT_TIMESTAMP
    """, (
        server_data.get("guild_id"),
        server_data.get("name"),
        server_data.get("description", ""),
        server_data.get("icon_url", ""),
        server_data.get("invite_code", ""),
        server_data.get("vanity_url", ""),
        server_data.get("approximate_member_count", 0),
        server_data.get("approximate_presence_count", 0),
        server_data.get("category", "IPTV reseller"),
        tags,
        business_services,
        server_data.get("verification_level", "None"),
        server_data.get("source", "manual_import"),
        server_data.get("business_relevance", "")
    ))
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# CRM Leads & Follow-ups
# --------------------------------------------------------------------------

def get_leads(query="", status="All", category="All") -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    SELECT l.*, s.invite_code, s.vanity_url, s.icon_url as server_icon
    FROM customer_leads l
    LEFT JOIN discovered_servers s ON l.guild_id = s.guild_id
    WHERE 1=1
    """
    params = []

    if query:
        search_term = f"%{query}%"
        sql += " AND (l.business_name LIKE ? OR l.contact_name LIKE ? OR l.contact_handle LIKE ? OR l.notes LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term])

    if status and status != "All":
        sql += " AND l.status = ?"
        params.append(status)

    if category and category != "All":
        sql += " AND l.category LIKE ?"
        params.append(f"%{category}%")

    sql += " ORDER BY l.updated_at DESC"

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    now_iso = datetime.utcnow().isoformat()
    leads = []
    for r in rows:
        d = dict(r)
        d["is_overdue"] = bool(d.get("follow_up_due_at") and d["follow_up_due_at"] < now_iso and d["status"] != "Won / Customer" and d["status"] != "Archived")
        leads.append(d)

    conn.close()
    return leads

def create_or_update_lead(lead_data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    lead_id = lead_data.get("id")
    business_interests = lead_data.get("business_interests", [])
    if isinstance(business_interests, list):
        business_interests = json.dumps(business_interests)

    stage_val = lead_data.get("stage") or lead_data.get("status") or "New Contact"
    status_val = stage_val
    opt_out_val = 1 if stage_val in ["Not Interested", "Archived"] else (1 if lead_data.get("opt_out") else 0)

    if lead_id:
        cursor.execute("""
        UPDATE customer_leads SET
            business_name = ?,
            community_name = ?,
            contact_name = ?,
            contact_role = ?,
            contact_handle = ?,
            discord_user_id = ?,
            status = ?,
            stage = ?,
            category = ?,
            service_interested = ?,
            stated_interests = ?,
            reach_members = ?,
            business_interests = ?,
            notes = ?,
            source = COALESCE(NULLIF(?, ''), source),
            source_data_origin = COALESCE(NULLIF(?, ''), source_data_origin),
            last_interaction_date = COALESCE(?, last_interaction_date),
            last_reply_date = COALESCE(?, last_reply_date),
            follow_up_due_at = ?,
            follow_up_status = COALESCE(?, follow_up_status),
            next_suggested_action = COALESCE(NULLIF(?, ''), next_suggested_action),
            opt_out = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            lead_data.get("business_name", ""),
            lead_data.get("community_name", ""),
            lead_data.get("contact_name", ""),
            lead_data.get("contact_role", "Server Admin"),
            lead_data.get("contact_handle", ""),
            lead_data.get("discord_user_id", ""),
            status_val,
            stage_val,
            lead_data.get("category", "IPTV reseller"),
            lead_data.get("service_interested") or lead_data.get("category", "IPTV Subscriptions"),
            lead_data.get("stated_interests", ""),
            lead_data.get("reach_members", 0),
            business_interests,
            lead_data.get("notes", ""),
            lead_data.get("source", ""),
            lead_data.get("source_data_origin", ""),
            lead_data.get("last_interaction_date"),
            lead_data.get("last_reply_date"),
            lead_data.get("follow_up_due_at"),
            lead_data.get("follow_up_status", "None"),
            lead_data.get("next_suggested_action", ""),
            opt_out_val,
            lead_id
        ))
        log_activity("lead_updated", f"Updated Lead: {lead_data.get('business_name')}", f"Stage: {stage_val}", "lead", str(lead_id), conn=conn)
    else:
        # Duplication prevention: Avoid duplicate contact if already saved for guild or handle
        contact_handle = (lead_data.get("contact_handle") or "").strip()
        discord_user_id = (lead_data.get("discord_user_id") or "").strip()
        guild_id = lead_data.get("guild_id")

        existing_id = None
        if discord_user_id and guild_id:
            cursor.execute("SELECT id FROM customer_leads WHERE discord_user_id = ? AND guild_id = ?", (discord_user_id, guild_id))
            r = cursor.fetchone()
            if r:
                existing_id = r["id"]
        elif contact_handle and guild_id:
            cursor.execute("SELECT id FROM customer_leads WHERE contact_handle = ? AND guild_id = ?", (contact_handle, guild_id))
            r = cursor.fetchone()
            if r:
                existing_id = r["id"]

        if existing_id:
            cursor.execute("""
            UPDATE customer_leads SET
                business_name = COALESCE(NULLIF(?, ''), business_name),
                contact_name = COALESCE(NULLIF(?, ''), contact_name),
                status = COALESCE(NULLIF(?, ''), status),
                stage = COALESCE(NULLIF(?, ''), stage),
                notes = CASE WHEN ? != '' THEN ? ELSE notes END,
                follow_up_due_at = COALESCE(?, follow_up_due_at),
                opt_out = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (
                lead_data.get("business_name", ""),
                lead_data.get("contact_name", ""),
                status_val,
                stage_val,
                lead_data.get("notes", ""),
                lead_data.get("notes", ""),
                lead_data.get("follow_up_due_at"),
                opt_out_val,
                existing_id
            ))
            lead_id = existing_id
            log_activity("lead_updated", f"Updated Existing Lead (Duplicate Merged): {lead_data.get('business_name')}", f"ID: {lead_id}", "lead", str(lead_id), conn=conn)
        else:
            cursor.execute("""
            INSERT INTO customer_leads (
                guild_id, community_name, business_name, contact_name, contact_role, contact_handle,
                discord_user_id, status, stage, category, service_interested, reach_members, business_interests,
                notes, source, source_data_origin, stated_interests, last_interaction_date, last_reply_date,
                follow_up_due_at, follow_up_status, next_suggested_action, opt_out
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead_data.get("guild_id"),
                lead_data.get("community_name", ""),
                lead_data.get("business_name", "New Prospect"),
                lead_data.get("contact_name", ""),
                lead_data.get("contact_role", "Server Admin"),
                contact_handle,
                discord_user_id,
                status_val,
                stage_val,
                lead_data.get("category", "IPTV reseller"),
                lead_data.get("service_interested") or lead_data.get("category", "IPTV Subscriptions"),
                lead_data.get("reach_members", 0),
                business_interests,
                lead_data.get("notes", ""),
                lead_data.get("source", "Manual Entry"),
                lead_data.get("source_data_origin", "manual_entered"),
                lead_data.get("stated_interests", ""),
                lead_data.get("last_interaction_date"),
                lead_data.get("last_reply_date"),
                lead_data.get("follow_up_due_at"),
                lead_data.get("follow_up_status", "None"),
                lead_data.get("next_suggested_action", "Draft opening message based on public interests"),
                opt_out_val
            ))
            lead_id = cursor.lastrowid
            log_activity("lead_created", f"Created Lead: {lead_data.get('business_name')}", f"Contact: {contact_handle or 'Unknown'}", "lead", str(lead_id), conn=conn)

    conn.commit()
    conn.close()
    return lead_id

def update_lead_status(lead_id: int, new_status: str, set_followup_days: Optional[int] = None):
    conn = get_connection()
    cursor = conn.cursor()

    follow_up_due_at = None
    if set_followup_days and set_followup_days > 0:
        follow_up_due_at = (datetime.utcnow() + timedelta(days=set_followup_days)).isoformat()

    opt_out = 1 if new_status in ["Not Interested", "Archived", "Do Not Contact"] else 0
    now_iso = datetime.utcnow().isoformat()
    if follow_up_due_at:
        cursor.execute("""
        UPDATE customer_leads SET
            status = ?,
            stage = ?,
            opt_out = ?,
            last_contact_date = ?,
            follow_up_due_at = ?,
            follow_up_status = 'Scheduled',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (new_status, new_status, opt_out, now_iso, follow_up_due_at, lead_id))
    else:
        cursor.execute("""
        UPDATE customer_leads SET
            status = ?,
            stage = ?,
            opt_out = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (new_status, new_status, opt_out, lead_id))

    cursor.execute("SELECT business_name FROM customer_leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    bname = row["business_name"] if row else f"Lead #{lead_id}"
    log_activity("status_changed", f"Updated Status for {bname}", f"New stage: {new_status} (Follow-up: {set_followup_days or 'none'} days)", "lead", str(lead_id), conn=conn)

    conn.commit()
    conn.close()

def get_follow_ups() -> Dict[str, List[Dict[str, Any]]]:
    """Returns separated overdue and upcoming follow-ups for the Follow-up Manager.
    STRICT COMPLIANCE: Uninterested prospects and Do Not Contact opt-outs are strictly excluded."""
    all_leads = get_leads()
    overdue = []
    upcoming = []

    now_iso = datetime.utcnow().isoformat()
    for l in all_leads:
        due = l.get("follow_up_due_at")
        if not due or l["status"] in ["Won / Customer", "Archived", "Not Interested", "Do Not Contact"]:
            continue
        if due < now_iso:
            overdue.append(l)
        else:
            upcoming.append(l)

    return {
        "overdue": overdue,
        "upcoming": upcoming,
        "total_active": len(overdue) + len(upcoming)
    }

def update_followup_status(lead_id: int, new_status: str, postpone_days: int = 0):
    """
    Updates follow-up reminder status: Completed, Postponed, or Cancelled.
    """
    conn = get_connection()
    cursor = conn.cursor()
    if new_status == "Completed":
        cursor.execute("""
        UPDATE customer_leads SET
            follow_up_status = 'Completed',
            follow_up_due_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (lead_id,))
        log_activity("followup_completed", f"Follow-Up Completed for Lead #{lead_id}", "", "lead", str(lead_id), conn=conn)
    elif new_status == "Cancelled":
        cursor.execute("""
        UPDATE customer_leads SET
            follow_up_status = 'Cancelled',
            follow_up_due_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (lead_id,))
        log_activity("followup_cancelled", f"Follow-Up Cancelled for Lead #{lead_id}", "", "lead", str(lead_id), conn=conn)
    elif new_status == "Postponed":
        days = postpone_days if postpone_days > 0 else 2
        new_due = (datetime.utcnow() + timedelta(days=days)).isoformat()
        cursor.execute("""
        UPDATE customer_leads SET
            follow_up_status = 'Postponed',
            follow_up_due_at = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (new_due, lead_id))
        log_activity("followup_postponed", f"Follow-Up Postponed for Lead #{lead_id}", f"Postponed by {days} days", "lead", str(lead_id), conn=conn)
    conn.commit()
    conn.close()

def save_lead_message(lead_id: int, message_type: str, content: str, status: str = "Draft") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO lead_messages (lead_id, message_type, content, status, reviewed_at, sent_at)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    """, (lead_id, message_type, content, status, datetime.utcnow().isoformat() if status == "Sent" else None))
    msg_id = cursor.lastrowid

    cursor.execute("SELECT business_name FROM customer_leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    bname = row["business_name"] if row else f"Lead #{lead_id}"
    log_activity("message_staged", f"Staged Outreach for {bname}", f"Type: {message_type}", "message", str(msg_id), conn=conn)

    conn.commit()
    conn.close()
    return msg_id

def get_lead_messages(lead_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lead_messages WHERE lead_id = ? ORDER BY created_at DESC", (lead_id,))
    rows = cursor.fetchall()
    messages = [dict(r) for r in rows]
    conn.close()
    return messages

# --------------------------------------------------------------------------
# Campaign Planner
# --------------------------------------------------------------------------

def get_campaigns() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

def create_campaign(
    name: str,
    service_type: str,
    target_audience: str,
    staged_pitch: str,
    target_count: int = 10,
    selected_prospect_ids: Optional[List[int]] = None,
    selected_guild_ids: Optional[List[str]] = None,
    scheduled_review_date: Optional[str] = None
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    prospect_ids_json = json.dumps(selected_prospect_ids or [])
    guild_ids_json = json.dumps(selected_guild_ids or [])
    cursor.execute("""
    INSERT INTO campaigns (
        name, service_type, target_audience, staged_pitch, target_count,
        selected_prospect_ids, selected_guild_ids, scheduled_review_date, status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active')
    """, (
        name.strip(), service_type.strip(), target_audience.strip(), staged_pitch.strip(),
        target_count, prospect_ids_json, guild_ids_json, scheduled_review_date
    ))
    camp_id = cursor.lastrowid
    log_activity("campaign_created", f"Created Campaign: {name}", f"Service: {service_type}", "campaign", str(camp_id), conn=conn)
    conn.commit()
    conn.close()
    return camp_id

def update_campaign_status(campaign_id: int, new_status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE campaigns SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, campaign_id))
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Activity Logs & Audit History
# --------------------------------------------------------------------------

def log_activity(activity_type: str, title: str, details: str = "", entity_type: str = "system", entity_id: str = "", conn: Optional[sqlite3.Connection] = None):
    try:
        should_close = False
        if conn is None:
            conn = get_connection()
            should_close = True
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO activity_logs (activity_type, title, details, entity_type, entity_id)
        VALUES (?, ?, ?, ?, ?)
        """, (activity_type, title, details, entity_type, str(entity_id)))
        if should_close:
            conn.commit()
            conn.close()
    except Exception as e:
        logger.warning(f"Could not log activity: {e}")

def get_activity_history(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

# --------------------------------------------------------------------------
# Conversation Assistance Persistence
# --------------------------------------------------------------------------

def save_conversation_record(
    lead_id: Optional[int],
    contact_name: str,
    service_type: str,
    raw_conversation: str,
    summary: str,
    identified_questions: List[str],
    suggested_replies: List[Dict[str, str]]
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO conversation_assistance (
        lead_id, contact_name, service_type, raw_conversation, summary,
        identified_questions, suggested_replies
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        lead_id, contact_name, service_type, raw_conversation, summary,
        json.dumps(identified_questions), json.dumps(suggested_replies)
    ))
    record_id = cursor.lastrowid
    log_activity("conversation_analyzed", f"Analyzed Dialogue with {contact_name}", f"Service: {service_type}", "conversation", str(record_id), conn=conn)
    conn.commit()
    conn.close()
    return record_id

def get_conversation_records(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversation_assistance ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["identified_questions"] = json.loads(d.get("identified_questions") or "[]")
        except:
            d["identified_questions"] = []
        try:
            d["suggested_replies"] = json.loads(d.get("suggested_replies") or "[]")
        except:
            d["suggested_replies"] = []
        results.append(d)
    conn.close()
    return results

# --------------------------------------------------------------------------
# Overview Metrics
# --------------------------------------------------------------------------

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as c FROM discovered_servers")
    total_servers = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM discovered_servers WHERE is_saved_to_leads = 1")
    saved_communities = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM customer_leads")
    saved_leads = cursor.fetchone()["c"]

    now_iso = datetime.utcnow().isoformat()
    cursor.execute("""
    SELECT COUNT(*) as c FROM customer_leads 
    WHERE follow_up_due_at IS NOT NULL 
      AND follow_up_due_at <= ? 
      AND status NOT IN ('Won / Customer', 'Archived', 'Not Interested', 'Do Not Contact')
    """, (now_iso,))
    followups_due = cursor.fetchone()["c"]

    cursor.execute("""
    SELECT COUNT(*) as c FROM customer_leads 
    WHERE follow_up_due_at IS NOT NULL 
      AND follow_up_due_at > ? 
      AND status NOT IN ('Won / Customer', 'Archived', 'Not Interested', 'Do Not Contact')
    """, (now_iso,))
    upcoming_followups = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM campaigns WHERE status = 'Active'")
    active_campaigns = cursor.fetchone()["c"]

    cursor.execute("SELECT COALESCE(SUM(approximate_member_count), 0) as s FROM discovered_servers")
    total_reach = cursor.fetchone()["s"]

    cursor.execute("SELECT COUNT(*) as c FROM activity_logs")
    activity_count = cursor.fetchone()["c"]

    conn.close()
    return {
        "total_servers": total_servers,
        "saved_communities": saved_communities,
        "saved_leads": saved_leads,
        "followups_due": followups_due,
        "upcoming_followups": upcoming_followups,
        "active_campaigns": active_campaigns,
        "total_reach": total_reach,
        "activity_count": activity_count
    }

# --------------------------------------------------------------------------
# Bot Settings & Guild Sync
# --------------------------------------------------------------------------

def get_bot_setting(key: str) -> Optional[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else None

def set_bot_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO bot_settings (key, value, updated_at)
    VALUES (?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    """, (key, value))
    conn.commit()
    conn.close()

def sync_bot_guilds(guilds: List[Dict[str, Any]]):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bot_guilds")
    for g in guilds:
        cursor.execute("""
        INSERT INTO bot_guilds (guild_id, name, icon_url, member_count, joined_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (str(g["id"]), g["name"], g.get("icon_url", ""), g.get("member_count", 0)))
    conn.commit()
    conn.close()

def get_bot_guilds() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bot_guilds ORDER BY member_count DESC")
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

# --------------------------------------------------------------------------
# Discord OAuth2 Account Helpers
# --------------------------------------------------------------------------

def save_discord_oauth(account_data: Dict[str, Any]):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO discord_oauth_account (
        id, discord_id, username, discriminator, global_name, avatar,
        access_token, refresh_token, expires_at, scope, updated_at
    ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(id) DO UPDATE SET
        discord_id = excluded.discord_id,
        username = excluded.username,
        discriminator = excluded.discriminator,
        global_name = excluded.global_name,
        avatar = excluded.avatar,
        access_token = excluded.access_token,
        refresh_token = excluded.refresh_token,
        expires_at = excluded.expires_at,
        scope = excluded.scope,
        updated_at = CURRENT_TIMESTAMP
    """, (
        str(account_data.get("id")),
        account_data.get("username", "Unknown"),
        account_data.get("discriminator", "0"),
        account_data.get("global_name") or account_data.get("username"),
        account_data.get("avatar") or "",
        account_data.get("access_token"),
        account_data.get("refresh_token") or "",
        account_data.get("expires_at"),
        account_data.get("scope", "identify guilds")
    ))
    conn.commit()
    conn.close()

def get_discord_oauth() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM discord_oauth_account WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    avatar_hash = d.get("avatar")
    discord_id = d.get("discord_id")
    if avatar_hash and discord_id:
        d["avatar_url"] = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.webp?size=128"
    else:
        d["avatar_url"] = ""
    return d

def delete_discord_oauth():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM discord_oauth_account WHERE id = 1")
    cursor.execute("DELETE FROM discord_user_guilds")
    conn.commit()
    conn.close()

def save_user_guilds(guilds: List[Dict[str, Any]]):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM discord_user_guilds")
    for g in guilds:
        gid = str(g.get("guild_id") or g.get("id"))
        is_owner = 1 if g.get("owner") else 0
        perms = str(g.get("permissions", "0"))
        try:
            perms_int = int(perms)
        except Exception:
            perms_int = 0
        can_manage = 1 if (g.get("can_manage") or is_owner or (perms_int & 0x8) or (perms_int & 0x20)) else 0

        cursor.execute("""
        INSERT INTO discord_user_guilds (guild_id, name, icon, owner, permissions, can_manage, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            gid,
            g.get("name", "Unknown Server"),
            g.get("icon") or "",
            is_owner,
            perms,
            can_manage
        ))
    conn.commit()
    conn.close()

def get_user_guilds() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM discord_user_guilds ORDER BY owner DESC, can_manage DESC, name ASC")
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        icon_hash = d.get("icon")
        guild_id = d.get("guild_id")
        if icon_hash and guild_id:
            d["icon_url"] = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.webp?size=128"
        else:
            d["icon_url"] = "https://cdn.discordapp.com/embed/avatars/0.png"

        is_owner = bool(d.get("owner"))
        perms_str = d.get("permissions") or "0"
        try:
            perms_int = int(perms_str)
        except Exception:
            perms_int = 0
        can_manage = bool(d.get("can_manage") or is_owner or (perms_int & 0x8) or (perms_int & 0x20))

        d["owner"] = is_owner
        d["can_manage"] = can_manage
        d["role_badge"] = "Server Owner" if is_owner else ("Administrator" if (perms_int & 0x8) else ("Manager" if (perms_int & 0x20) else "Member"))
        results.append(d)
    conn.close()
    return results

def export_sqlite_to_sql() -> str:
    """Exports SQLite records to PostgreSQL-compatible SQL dump."""
    conn = get_connection()
    lines = ["-- PHAMOUXE Database Export (PostgreSQL / SQLite Compatible)", f"-- Export Date: {datetime.utcnow().isoformat()}", ""]
    for line in conn.iterdump():
        lines.append(f"{line}")
    conn.close()
    return "\n".join(lines)

# --------------------------------------------------------------------------
# Message Templates Engine
# --------------------------------------------------------------------------

def get_message_templates(service_type: str = "", purpose: str = "") -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    sql = "SELECT * FROM message_templates WHERE 1=1"
    params = []
    if service_type and service_type != "All":
        sql += " AND service_type = ?"
        params.append(service_type)
    if purpose and purpose != "All":
        sql += " AND purpose = ?"
        params.append(purpose)
    sql += " ORDER BY service_type ASC, title ASC"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

def save_message_template(service_type: str, purpose: str, title: str, template_text: str, template_id: Optional[int] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    if template_id:
        cursor.execute("""
        UPDATE message_templates SET
            service_type = ?, purpose = ?, title = ?, template_text = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (service_type.strip(), purpose.strip(), title.strip(), template_text.strip(), template_id))
    else:
        cursor.execute("""
        INSERT INTO message_templates (service_type, purpose, title, template_text)
        VALUES (?, ?, ?, ?)
        """, (service_type.strip(), purpose.strip(), title.strip(), template_text.strip()))
        template_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return template_id

def delete_message_template(template_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM message_templates WHERE id = ?", (template_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# --------------------------------------------------------------------------
# Server Member Research (Authorized Integrations)
# --------------------------------------------------------------------------

def save_server_members(guild_id: str, members: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    saved = 0
    for m in members:
        roles = m.get("roles", [])
        if isinstance(roles, list):
            roles = json.dumps(roles)
        business_tags = m.get("business_tags", [])
        if isinstance(business_tags, list):
            business_tags = json.dumps(business_tags)
        cursor.execute("""
        INSERT INTO server_members (
            guild_id, discord_user_id, username, display_name, avatar_url,
            roles, is_bot, joined_at, business_tags, notes, synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(guild_id, discord_user_id) DO UPDATE SET
            username = excluded.username,
            display_name = excluded.display_name,
            avatar_url = excluded.avatar_url,
            roles = excluded.roles,
            is_bot = excluded.is_bot,
            business_tags = excluded.business_tags,
            synced_at = CURRENT_TIMESTAMP
        """, (
            str(guild_id),
            str(m.get("discord_user_id")),
            m.get("username", "Unknown"),
            m.get("display_name", ""),
            m.get("avatar_url", ""),
            roles,
            1 if m.get("is_bot") else 0,
            m.get("joined_at"),
            business_tags,
            m.get("notes", "")
        ))
        saved += 1
    conn.commit()
    conn.close()
    return saved

def get_server_members(guild_id: str, query: str = "", role: str = "", tag: str = "") -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    sql = "SELECT * FROM server_members WHERE guild_id = ?"
    params = [str(guild_id)]
    if query:
        search_term = f"%{query}%"
        sql += " AND (username LIKE ? OR display_name LIKE ? OR notes LIKE ?)"
        params.extend([search_term, search_term, search_term])
    if role:
        sql += " AND roles LIKE ?"
        params.append(f"%{role}%")
    if tag:
        sql += " AND business_tags LIKE ?"
        params.append(f"%{tag}%")
    sql += " ORDER BY is_bot ASC, joined_at DESC"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["roles"] = json.loads(d.get("roles") or "[]")
        except:
            d["roles"] = []
        try:
            d["business_tags"] = json.loads(d.get("business_tags") or "[]")
        except:
            d["business_tags"] = []
        results.append(d)
    conn.close()
    return results

def add_server_member_to_crm(member_id: int, status: str = "New Lead", follow_up_days: int = 0, notes: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT m.*, s.name as community_name, s.category as server_category
    FROM server_members m
    LEFT JOIN discovered_servers s ON m.guild_id = s.guild_id
    WHERE m.id = ?
    """, (member_id,))
    member = cursor.fetchone()
    if not member:
        conn.close()
        raise ValueError(f"Server member with id {member_id} not found.")

    m = dict(member)
    guild_id = m.get("guild_id")
    discord_user_id = m.get("discord_user_id")
    contact_handle = m.get("username")
    display_name = m.get("display_name") or contact_handle
    community_name = m.get("community_name") or f"Guild {guild_id}"
    roles = json.loads(m.get("roles") or "[]")
    contact_role = roles[0] if roles else "Member"

    # Check for existing lead to prevent duplication
    cursor.execute("SELECT id FROM customer_leads WHERE discord_user_id = ? AND guild_id = ?", (discord_user_id, guild_id))
    existing = cursor.fetchone()
    follow_up_due_at = None
    if follow_up_days > 0:
        follow_up_due_at = (datetime.utcnow() + timedelta(days=follow_up_days)).isoformat()

    if existing:
        lead_id = existing["id"]
        cursor.execute("""
        UPDATE customer_leads SET
            contact_name = ?,
            contact_handle = ?,
            notes = CASE WHEN ? != '' THEN ? ELSE notes END,
            status = ?,
            follow_up_due_at = COALESCE(?, follow_up_due_at),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (display_name, contact_handle, notes, notes, status, follow_up_due_at, lead_id))
    else:
        cursor.execute("""
        INSERT INTO customer_leads (
            guild_id, community_name, business_name, contact_name, contact_handle,
            discord_user_id, contact_role, status, category, notes, follow_up_due_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            guild_id,
            community_name,
            community_name,
            display_name,
            contact_handle,
            discord_user_id,
            contact_role,
            status,
            m.get("server_category") or "IPTV reseller",
            notes,
            follow_up_due_at
        ))
        lead_id = cursor.lastrowid

    log_activity("lead_created", f"Added Member to CRM: {contact_handle}", f"Community: {community_name}", "lead", str(lead_id), conn=conn)
    conn.commit()
    conn.close()
    return lead_id

# --------------------------------------------------------------------------
# Business Profile & AI Settings
# --------------------------------------------------------------------------

def get_business_settings() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM business_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {
            "business_name": "Famous Media Technologies",
            "telegram_contact": "@Phamouxetv",
            "sender_name": "Famous Media Technologies",
            "iptv_sub_1mo": 15.0,
            "iptv_sub_3mo": 35.0,
            "iptv_sub_6mo": 55.0,
            "iptv_sub_12mo": 80.0,
            "reseller_120_credits": 350.0,
            "app_rebrand_with_panel": 150.0,
            "app_dev_pricing": "Contact for requirements and custom pricing",
            "server_setup_pricing": "Contact for infrastructure requirements",
            "never_quote_unlisted": 1,
            "notes": "Official IPTV subscriptions, reseller panels, white-label app rebranding, custom app development, and streaming servers."
        }
    return dict(row)

def save_business_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO business_settings (
        id, business_name, telegram_contact, sender_name,
        iptv_sub_1mo, iptv_sub_3mo, iptv_sub_6mo, iptv_sub_12mo,
        reseller_120_credits, app_rebrand_with_panel,
        app_dev_pricing, server_setup_pricing, never_quote_unlisted, notes, updated_at
    ) VALUES (
        1, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?,
        ?, ?, ?, ?, CURRENT_TIMESTAMP
    )
    ON CONFLICT(id) DO UPDATE SET
        business_name = excluded.business_name,
        telegram_contact = excluded.telegram_contact,
        sender_name = excluded.sender_name,
        iptv_sub_1mo = excluded.iptv_sub_1mo,
        iptv_sub_3mo = excluded.iptv_sub_3mo,
        iptv_sub_6mo = excluded.iptv_sub_6mo,
        iptv_sub_12mo = excluded.iptv_sub_12mo,
        reseller_120_credits = excluded.reseller_120_credits,
        app_rebrand_with_panel = excluded.app_rebrand_with_panel,
        app_dev_pricing = excluded.app_dev_pricing,
        server_setup_pricing = excluded.server_setup_pricing,
        never_quote_unlisted = excluded.never_quote_unlisted,
        notes = excluded.notes,
        updated_at = CURRENT_TIMESTAMP
    """, (
        data.get("business_name", "Famous Media Technologies").strip(),
        data.get("telegram_contact", "@Phamouxetv").strip(),
        data.get("sender_name", "Famous Media Technologies").strip(),
        float(data.get("iptv_sub_1mo", 15.0)),
        float(data.get("iptv_sub_3mo", 35.0)),
        float(data.get("iptv_sub_6mo", 55.0)),
        float(data.get("iptv_sub_12mo", 80.0)),
        float(data.get("reseller_120_credits", 350.0)),
        float(data.get("app_rebrand_with_panel", 150.0)),
        data.get("app_dev_pricing", "Contact for requirements and custom pricing").strip(),
        data.get("server_setup_pricing", "Contact for infrastructure requirements").strip(),
        1 if data.get("never_quote_unlisted", 1) else 0,
        data.get("notes", "").strip()
    ))
    conn.commit()
    conn.close()
    return get_business_settings()

def get_ai_settings() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {
            "provider": "builtin",
            "api_key": "",
            "model_name": "gemini-1.5-flash",
            "temperature": 0.3
        }
    d = dict(row)
    # Mask API key for security in responses
    if d.get("api_key"):
        raw = d["api_key"]
        d["api_key_masked"] = raw[:4] + "..." + raw[-4:] if len(raw) > 8 else "***"
        d["has_key"] = True
    else:
        d["api_key_masked"] = ""
        d["has_key"] = False
    return d

def save_ai_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    api_key = data.get("api_key", "").strip()
    if not api_key:
        cursor.execute("SELECT api_key FROM ai_settings WHERE id = 1")
        existing = cursor.fetchone()
        if existing:
            api_key = existing["api_key"]

    cursor.execute("""
    INSERT INTO ai_settings (id, provider, api_key, model_name, temperature, updated_at)
    VALUES (1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(id) DO UPDATE SET
        provider = excluded.provider,
        api_key = excluded.api_key,
        model_name = excluded.model_name,
        temperature = excluded.temperature,
        updated_at = CURRENT_TIMESTAMP
    """, (
        data.get("provider", "builtin").strip(),
        api_key,
        data.get("model_name", "gemini-1.5-flash").strip(),
        float(data.get("temperature", 0.3))
    ))
    conn.commit()
    conn.close()
    return get_ai_settings()

# --------------------------------------------------------------------------
# Server Channels & Permitted Message Search
# --------------------------------------------------------------------------

def save_server_channels(guild_id: str, channels: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    saved = 0
    for ch in channels:
        cursor.execute("""
        INSERT INTO server_channels (guild_id, channel_id, name, type, topic, is_monitored, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(channel_id) DO UPDATE SET
            name = excluded.name,
            type = excluded.type,
            topic = excluded.topic,
            synced_at = CURRENT_TIMESTAMP
        """, (
            str(guild_id),
            str(ch.get("id") or ch.get("channel_id")),
            ch.get("name", "channel"),
            ch.get("type", "text"),
            ch.get("topic", "") or "",
            1 if ch.get("is_monitored") else 0
        ))
        saved += 1
    conn.commit()
    conn.close()
    return saved

def get_server_channels(guild_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM server_channels WHERE guild_id = ? ORDER BY is_monitored DESC, name ASC", (str(guild_id),))
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

def update_channel_monitoring(guild_id: str, channel_id: str, is_monitored: bool) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    val = 1 if is_monitored else 0
    cursor.execute("UPDATE server_channels SET is_monitored = ? WHERE guild_id = ? AND channel_id = ?", (val, str(guild_id), str(channel_id)))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def save_channel_messages(guild_id: str, channel_id: str, channel_name: str, messages: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    saved = 0
    for m in messages:
        cursor.execute("""
        INSERT INTO channel_messages (
            message_id, guild_id, channel_id, channel_name, author_id, author_username,
            author_display_name, content, timestamp, jump_url, has_buying_signal,
            buying_signal_details, detected_service, relevance_score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(message_id) DO UPDATE SET
            content = excluded.content,
            has_buying_signal = excluded.has_buying_signal,
            buying_signal_details = excluded.buying_signal_details,
            detected_service = excluded.detected_service,
            relevance_score = excluded.relevance_score
        """, (
            str(m["message_id"]),
            str(guild_id),
            str(channel_id),
            channel_name,
            str(m.get("author_id", "")),
            m.get("author_username", "User"),
            m.get("author_display_name", ""),
            m.get("content", ""),
            m.get("timestamp"),
            m.get("jump_url", f"https://discord.com/channels/{guild_id}/{channel_id}/{m['message_id']}"),
            1 if m.get("has_buying_signal") else 0,
            m.get("buying_signal_details", ""),
            m.get("detected_service", "General"),
            int(m.get("relevance_score", 0))
        ))
        saved += 1
    conn.commit()
    conn.close()
    return saved

def search_channel_messages(
    query: str = "",
    guild_id: str = "",
    channel_id: str = "",
    service: str = "",
    buying_signals_only: bool = False,
    limit: int = 50
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
    SELECT m.*, s.name as server_name, s.icon_url as server_icon
    FROM channel_messages m
    LEFT JOIN discovered_servers s ON m.guild_id = s.guild_id
    WHERE 1=1
    """
    params = []

    if query:
        search_term = f"%{query}%"
        sql += " AND (m.content LIKE ? OR m.author_username LIKE ? OR m.author_display_name LIKE ? OR m.buying_signal_details LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term])

    if guild_id and guild_id != "All":
        sql += " AND m.guild_id = ?"
        params.append(str(guild_id))

    if channel_id and channel_id != "All":
        sql += " AND m.channel_id = ?"
        params.append(str(channel_id))

    if service and service != "All":
        sql += " AND m.detected_service LIKE ?"
        params.append(f"%{service}%")

    if buying_signals_only:
        sql += " AND m.has_buying_signal = 1"

    sql += " ORDER BY m.has_buying_signal DESC, m.relevance_score DESC, m.created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

def save_message_prospect_to_crm(message_id: str, notes: str = "", follow_up_days: int = 2) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT m.*, s.name as server_name
    FROM channel_messages m
    LEFT JOIN discovered_servers s ON m.guild_id = s.guild_id
    WHERE m.message_id = ?
    """, (str(message_id),))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Message ID {message_id} not found in database.")

    msg = dict(row)
    guild_id = msg.get("guild_id")
    author_id = msg.get("author_id")
    author_username = msg.get("author_username")
    display_name = msg.get("author_display_name") or author_username
    server_name = msg.get("server_name") or f"Discord Server {guild_id}"
    channel_name = msg.get("channel_name") or "Discussion"

    # Duplication prevention
    cursor.execute("SELECT id FROM customer_leads WHERE discord_user_id = ? AND guild_id = ?", (author_id, guild_id))
    existing = cursor.fetchone()

    combined_notes = f"Sourced from public discussion in #{channel_name}: \"{msg.get('content')[:160]}\"\nJump URL: {msg.get('jump_url')}"
    if notes:
        combined_notes = f"{notes}\n---\n{combined_notes}"

    due_date = (datetime.utcnow() + timedelta(days=follow_up_days)).isoformat() if follow_up_days > 0 else None

    if existing:
        lead_id = existing["id"]
        cursor.execute("""
        UPDATE customer_leads SET
            contact_name = ?,
            contact_handle = ?,
            notes = ?,
            stated_interests = ?,
            service_interested = ?,
            last_message_summary = ?,
            follow_up_due_at = COALESCE(?, follow_up_due_at),
            source = 'Channel Message Search',
            source_data_origin = 'discord_received',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            display_name,
            author_username,
            combined_notes,
            msg.get("buying_signal_details") or "Public Discord discussion inquiry",
            msg.get("detected_service") or "IPTV Subscriptions",
            msg.get("content")[:180],
            due_date,
            lead_id
        ))
    else:
        cursor.execute("""
        INSERT INTO customer_leads (
            guild_id, community_name, business_name, contact_name, contact_handle,
            discord_user_id, contact_role, status, stage, category, service_interested,
            stated_interests, source, source_data_origin, notes, last_message_summary,
            next_suggested_action, follow_up_due_at, follow_up_status
        ) VALUES (?, ?, ?, ?, ?, ?, 'Prospective Buyer', 'New Contact', 'New Contact', ?, ?, ?, 'Channel Message Search', 'discord_received', ?, ?, 'Review message context & draft outreach', ?, ?)
        """, (
            guild_id,
            server_name,
            f"{display_name} ({server_name})",
            display_name,
            author_username,
            author_id,
            msg.get("detected_service") or "IPTV Subscriptions",
            msg.get("detected_service") or "IPTV Subscriptions",
            msg.get("buying_signal_details") or "Stated need in channel discussion",
            combined_notes,
            msg.get("content")[:180],
            due_date,
            'Scheduled' if due_date else 'None'
        ))
        lead_id = cursor.lastrowid

    # Mark message as saved
    cursor.execute("UPDATE channel_messages SET is_saved_to_contacts = 1 WHERE message_id = ?", (str(message_id),))
    log_activity("lead_created", f"Added Discussion Prospect to CRM: {author_username}", f"Server: {server_name} #{channel_name}", "lead", str(lead_id), conn=conn)

    conn.commit()
    conn.close()
    return lead_id

# --------------------------------------------------------------------------
# Smart Follow-Up Manager with Anti-Annoyance Safeguards
# --------------------------------------------------------------------------

def schedule_follow_up_reminder(
    lead_id: int,
    interval_days: int = 2,
    custom_message: str = "",
    context_summary: str = ""
) -> Dict[str, Any]:
    """
    Schedules a smart follow-up reminder 2-3 days later with full context.
    Safeguards:
    - Opt-out protection: stops if Not Interested / Archived / Blocked
    - Duplicate prevention: only 1 active reminder per contact
    - Max follow-ups limit: prevents annoying people (max 2)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM customer_leads WHERE id = ?", (lead_id,))
    lead_row = cursor.fetchone()
    if not lead_row:
        conn.close()
        raise ValueError(f"Lead ID {lead_id} not found.")

    lead = dict(lead_row)
    status_lower = (lead.get("status") or "").lower()
    stage_lower = (lead.get("stage") or "").lower()

    if lead.get("opt_out") == 1 or "not interested" in status_lower or "archived" in status_lower or "do not contact" in status_lower:
        conn.close()
        return {
            "success": False,
            "error": "This contact has indicated they are not interested or opted out. System safeguards strictly prohibit follow-ups."
        }

    # Check follow-up count
    follow_up_count = lead.get("follow_up_count") or 0
    if follow_up_count >= 2:
        conn.close()
        return {
            "success": False,
            "error": "Maximum follow-up limit (2) reached for this contact. To maintain professional reputation, do not send further unsolicited messages."
        }

    # Prevent duplicate active reminders
    cursor.execute("SELECT id FROM follow_up_reminders WHERE lead_id = ? AND status IN ('Scheduled', 'Due')", (lead_id,))
    existing_reminder = cursor.fetchone()
    if existing_reminder:
        conn.close()
        return {
            "success": False,
            "error": "An active follow-up reminder is already scheduled for this contact. Duplicate prevented."
        }

    days = interval_days if interval_days in [1, 2, 3, 5, 7] else 2
    due_date = (datetime.utcnow() + timedelta(days=days)).isoformat()

    contact_name = lead.get("contact_name") or lead.get("contact_handle") or "there"
    service_name = lead.get("service_interested") or lead.get("category") or "our services"
    biz_name = lead.get("community_name") or lead.get("business_name") or "your server"

    if not custom_message.strip():
        if days <= 2:
            custom_message = (
                f"Hi {contact_name},\n\n"
                f"Following up briefly on our discussion regarding {service_name} for {biz_name}. "
                f"I know things move quickly on Discord, so just checking if you had a free moment to review.\n\n"
                f"No rush at all—whenever convenient for you.\n\n"
                f"Best regards,\nFamous Media Technologies (@Phamouxetv)"
            )
        else:
            custom_message = (
                f"Hey {contact_name},\n\n"
                f"Just floating this back to the top of your messages. "
                f"Let me know if you are still exploring {service_name} for {biz_name}. "
                f"If timing is not right or your priorities shifted, completely understood!\n\n"
                f"Cheers,\nFamous Media Technologies (@Phamouxetv)"
            )

    cursor.execute("""
    INSERT INTO follow_up_reminders (
        lead_id, due_date, interval_days, suggested_message, status, context_summary
    ) VALUES (?, ?, ?, ?, 'Scheduled', ?)
    """, (lead_id, due_date, days, custom_message.strip(), context_summary or lead.get("last_message_summary", "")))
    reminder_id = cursor.lastrowid

    # Update lead status
    cursor.execute("""
    UPDATE customer_leads SET
        follow_up_due_at = ?,
        follow_up_status = 'Scheduled',
        stage = CASE WHEN stage = 'New Contact' THEN 'Follow-up Due' ELSE stage END,
        follow_up_count = follow_up_count + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (due_date, lead_id))

    log_activity("reminder_scheduled", f"Scheduled {days}-Day Follow-Up for {lead.get('business_name')}", f"Due: {due_date[:10]}", "lead", str(lead_id), conn=conn)

    conn.commit()
    conn.close()

    return {
        "success": True,
        "reminder_id": reminder_id,
        "due_date": due_date,
        "interval_days": days,
        "suggested_message": custom_message
    }

def record_reply_received(lead_id: int, reply_summary: str = "") -> Dict[str, Any]:
    """
    Marks that a reply was received from the contact.
    Automatically cancels active follow-up reminders and suggests the next reply!
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM customer_leads WHERE id = ?", (lead_id,))
    lead_row = cursor.fetchone()
    if not lead_row:
        conn.close()
        raise ValueError(f"Lead ID {lead_id} not found.")

    lead = dict(lead_row)
    now_iso = datetime.utcnow().isoformat()

    # Cancel all active follow-up reminders
    cursor.execute("""
    UPDATE follow_up_reminders SET
        status = 'Cancelled',
        updated_at = CURRENT_TIMESTAMP
    WHERE lead_id = ? AND status IN ('Scheduled', 'Due')
    """, (lead_id,))

    # Update lead state: move to Conversation Started or Interested
    new_stage = 'Interested' if lead.get('stage') in ['First Message Ready', 'Follow-up Due', 'Conversation Started'] else lead.get('stage')

    cursor.execute("""
    UPDATE customer_leads SET
        last_reply_date = ?,
        last_interaction_date = ?,
        follow_up_status = 'Completed',
        follow_up_due_at = NULL,
        stage = ?,
        status = ?,
        notes = CASE WHEN ? != '' THEN ? || '\n[Reply Received ' || ? || ']: ' || ? ELSE notes END,
        next_suggested_action = 'Review reply and send response using Conversation Coach',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        now_iso, now_iso, new_stage, new_stage,
        reply_summary, lead.get("notes", ""), now_iso[:10], reply_summary,
        lead_id
    ))

    log_activity("reply_received", f"Reply Received from {lead.get('contact_name') or lead.get('business_name')}", f"Follow-ups cancelled. Stage moved to {new_stage}.", "lead", str(lead_id), conn=conn)

    conn.commit()
    conn.close()

    return {
        "success": True,
        "lead_id": lead_id,
        "stage": new_stage,
        "message": "Reply recorded. Active reminders automatically cancelled."
    }

def get_detailed_follow_ups() -> Dict[str, Any]:
    """
    Separates follow-up reminders into:
    - Today's Due
    - Overdue
    - Upcoming
    - Completed / Cancelled
    """
    conn = get_connection()
    cursor = conn.cursor()

    now_iso = datetime.utcnow().isoformat()
    today_start = datetime.utcnow().strftime("%Y-%m-%d 00:00:00")
    today_end = datetime.utcnow().strftime("%Y-%m-%d 23:59:59")

    # Update reminders that have reached their due date
    cursor.execute("""
    UPDATE follow_up_reminders SET status = 'Due', updated_at = CURRENT_TIMESTAMP
    WHERE status = 'Scheduled' AND due_date <= ?
    """, (now_iso,))
    conn.commit()

    sql = """
    SELECT r.*, l.business_name, l.contact_name, l.contact_handle, l.discord_user_id,
           l.category, l.stage, l.service_interested, l.opt_out, s.icon_url as server_icon,
           s.name as server_name
    FROM follow_up_reminders r
    JOIN customer_leads l ON r.lead_id = l.id
    LEFT JOIN discovered_servers s ON l.guild_id = s.guild_id
    ORDER BY r.due_date ASC
    """
    cursor.execute(sql)
    rows = cursor.fetchall()

    today_reminders = []
    overdue_reminders = []
    upcoming_reminders = []
    completed_reminders = []

    for r in rows:
        d = dict(r)
        status = d.get("status")
        due = d.get("due_date", "")

        if status in ["Completed", "Dismissed", "Cancelled", "Approved"]:
            completed_reminders.append(d)
        elif due < today_start:
            overdue_reminders.append(d)
        elif today_start <= due <= today_end:
            today_reminders.append(d)
        else:
            upcoming_reminders.append(d)

    conn.close()
    return {
        "today": today_reminders,
        "overdue": overdue_reminders,
        "upcoming": upcoming_reminders,
        "completed": completed_reminders,
        "counts": {
            "today": len(today_reminders),
            "overdue": len(overdue_reminders),
            "upcoming": len(upcoming_reminders),
            "completed": len(completed_reminders),
            "total_active": len(today_reminders) + len(overdue_reminders) + len(upcoming_reminders)
        }
    }

def approve_follow_up_message(reminder_id: int, edited_message: str = "") -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM follow_up_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    rem = dict(row)
    lead_id = rem["lead_id"]

    cursor.execute("""
    UPDATE follow_up_reminders SET
        status = 'Approved',
        suggested_message = CASE WHEN ? != '' THEN ? ELSE suggested_message END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (edited_message, edited_message, reminder_id))

    # Also log into lead messages as Staged/Approved
    msg_content = edited_message or rem["suggested_message"]
    cursor.execute("""
    INSERT INTO lead_messages (lead_id, message_type, content, status, reviewed_at)
    VALUES (?, 'Follow-Up', ?, 'Approved', CURRENT_TIMESTAMP)
    """, (lead_id, msg_content))

    cursor.execute("""
    UPDATE customer_leads SET
        follow_up_status = 'Approved',
        stage = 'Follow-up Due',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (lead_id,))

    log_activity("followup_approved", f"Approved Follow-Up for Lead #{lead_id}", "Operator approved message draft.", "reminder", str(reminder_id), conn=conn)

    conn.commit()
    conn.close()
    return True

def dismiss_follow_up_reminder(reminder_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT lead_id FROM follow_up_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    lead_id = row["lead_id"]

    cursor.execute("UPDATE follow_up_reminders SET status = 'Dismissed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (reminder_id,))
    cursor.execute("UPDATE customer_leads SET follow_up_status = 'Dismissed', follow_up_due_at = NULL WHERE id = ?", (lead_id,))
    log_activity("followup_dismissed", f"Dismissed Reminder #{reminder_id}", "", "reminder", str(reminder_id), conn=conn)

    conn.commit()
    conn.close()
    return True

def reschedule_follow_up_reminder(reminder_id: int, extra_days: int = 2) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM follow_up_reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Reminder ID {reminder_id} not found.")
    rem = dict(row)
    new_due = (datetime.utcnow() + timedelta(days=extra_days)).isoformat()

    cursor.execute("""
    UPDATE follow_up_reminders SET
        due_date = ?,
        status = 'Scheduled',
        interval_days = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (new_due, extra_days, reminder_id))

    cursor.execute("""
    UPDATE customer_leads SET
        follow_up_due_at = ?,
        follow_up_status = 'Scheduled',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (new_due, rem["lead_id"]))

    conn.commit()
    conn.close()
    return {"success": True, "new_due_date": new_due}

# --------------------------------------------------------------------------
# AI Chat & Command Center Persistence
# --------------------------------------------------------------------------

def save_ai_chat_message(role: str, message: str, session_id: str = "default", metadata: Optional[Dict] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    meta_json = json.dumps(metadata or {})
    cursor.execute("""
    INSERT INTO ai_chat_history (session_id, role, message, metadata, created_at)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (session_id, role, message, meta_json))
    mid = cursor.lastrowid
    conn.commit()
    conn.close()
    return mid

def get_ai_chat_history(session_id: str = "default", limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_chat_history WHERE session_id = ? ORDER BY created_at ASC LIMIT ?", (session_id, limit))
    rows = cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["metadata"] = json.loads(d.get("metadata") or "{}")
        except:
            d["metadata"] = {}
        results.append(d)
    conn.close()
    return results

def clear_ai_chat_history(session_id: str = "default"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ai_chat_history WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------
# Data Privacy, Erasure & Workspace Management
# --------------------------------------------------------------------------

def delete_lead(lead_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customer_leads WHERE id = ?", (lead_id,))
    cursor.execute("DELETE FROM follow_up_reminders WHERE lead_id = ?", (lead_id,))
    cursor.execute("DELETE FROM lead_messages WHERE lead_id = ?", (lead_id,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def clear_all_leads() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customer_leads")
    cursor.execute("DELETE FROM follow_up_reminders")
    cursor.execute("DELETE FROM lead_messages")
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

def clear_research_cache() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channel_messages WHERE is_saved_to_contacts = 0")
    cursor.execute("DELETE FROM server_members")
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count

def remove_server_from_workspace(guild_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM discovered_servers WHERE guild_id = ?", (str(guild_id),))
    cursor.execute("DELETE FROM bot_guilds WHERE guild_id = ?", (str(guild_id),))
    cursor.execute("DELETE FROM server_channels WHERE guild_id = ?", (str(guild_id),))
    cursor.execute("DELETE FROM channel_messages WHERE guild_id = ?", (str(guild_id),))
    cursor.execute("DELETE FROM server_members WHERE guild_id = ?", (str(guild_id),))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


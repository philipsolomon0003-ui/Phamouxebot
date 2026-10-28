-- ============================================================================
-- PHAMOUXE — Executive IPTV Research & Customer CRM Suite
-- PostgreSQL Production Schema Migration File
-- Compatible with PostgreSQL 13+, Supabase, Neon, AWS RDS, and self-hosted VPS
-- ============================================================================

-- Extensions (optional for UUIDs if needed)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Authentication & System Configuration
CREATE TABLE IF NOT EXISTS auth_config (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 1b. Business Profile Settings (Famous Media Technologies)
CREATE TABLE IF NOT EXISTS business_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    business_name VARCHAR(255) DEFAULT 'Famous Media Technologies',
    telegram_contact VARCHAR(128) DEFAULT '@Phamouxetv',
    sender_name VARCHAR(255) DEFAULT 'Famous Media Technologies',
    iptv_sub_1mo NUMERIC(10,2) DEFAULT 15.00,
    iptv_sub_3mo NUMERIC(10,2) DEFAULT 35.00,
    iptv_sub_6mo NUMERIC(10,2) DEFAULT 55.00,
    iptv_sub_12mo NUMERIC(10,2) DEFAULT 80.00,
    reseller_120_credits NUMERIC(10,2) DEFAULT 350.00,
    app_rebrand_with_panel NUMERIC(10,2) DEFAULT 150.00,
    app_dev_pricing TEXT DEFAULT 'Contact for requirements and custom pricing',
    server_setup_pricing TEXT DEFAULT 'Contact for infrastructure requirements',
    never_quote_unlisted INTEGER DEFAULT 1,
    notes TEXT DEFAULT 'Official IPTV subscriptions, reseller panels, white-label app rebranding, custom app development, and streaming servers.',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 1c. AI Provider Configuration
CREATE TABLE IF NOT EXISTS ai_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    provider VARCHAR(64) DEFAULT 'builtin',
    api_key TEXT DEFAULT '',
    model_name VARCHAR(128) DEFAULT 'gemini-1.5-flash',
    temperature NUMERIC(3,2) DEFAULT 0.30,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Active Operator Sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    session_token VARCHAR(128) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- 3. Discovered IPTV Communities & Server Research
CREATE TABLE IF NOT EXISTS discovered_servers (
    guild_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon_url TEXT,
    invite_code VARCHAR(64),
    vanity_url VARCHAR(64),
    approximate_member_count INTEGER DEFAULT 0,
    approximate_presence_count INTEGER DEFAULT 0,
    category VARCHAR(64) DEFAULT 'IPTV reseller',
    tags JSONB DEFAULT '[]'::jsonb,
    business_services JSONB DEFAULT '[]'::jsonb,
    verification_level VARCHAR(32) DEFAULT 'None',
    source VARCHAR(64) DEFAULT 'directory_discovery',
    business_relevance TEXT DEFAULT '',
    is_saved_to_leads INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    last_checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Customer Management CRM (Leads & Contacts)
CREATE TABLE IF NOT EXISTS customer_leads (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(32) REFERENCES discovered_servers(guild_id) ON DELETE SET NULL,
    channel_id VARCHAR(64) DEFAULT '',
    channel_name VARCHAR(128) DEFAULT '',
    community_name VARCHAR(255) DEFAULT '',
    business_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(128) DEFAULT '',
    contact_role VARCHAR(128) DEFAULT 'Server Owner / Admin',
    contact_handle VARCHAR(128) DEFAULT '',
    discord_user_id VARCHAR(64) DEFAULT '',
    status VARCHAR(64) DEFAULT 'New Contact',
    stage VARCHAR(64) DEFAULT 'New Contact',
    category VARCHAR(64) DEFAULT 'IPTV reseller',
    service_interested VARCHAR(128) DEFAULT 'IPTV Subscriptions',
    reach_members INTEGER DEFAULT 0,
    business_interests JSONB DEFAULT '[]'::jsonb,
    stated_interests TEXT DEFAULT '',
    source VARCHAR(64) DEFAULT 'Manual Entry',
    source_data_origin VARCHAR(32) DEFAULT 'manual_entered',
    notes TEXT DEFAULT '',
    last_message_summary TEXT DEFAULT '',
    next_suggested_action TEXT DEFAULT 'Review community discussions or draft opening message',
    last_contact_date TIMESTAMP WITH TIME ZONE,
    last_reply_date TIMESTAMP WITH TIME ZONE,
    last_interaction_date TIMESTAMP WITH TIME ZONE,
    follow_up_due_at TIMESTAMP WITH TIME ZONE,
    follow_up_status VARCHAR(32) DEFAULT 'None',
    follow_up_count INTEGER DEFAULT 0,
    opt_out INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4b. Server Channels (Operator specifies allowed channels for official bot)
CREATE TABLE IF NOT EXISTS server_channels (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(32) NOT NULL,
    channel_id VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    type VARCHAR(32) DEFAULT 'text',
    topic TEXT DEFAULT '',
    is_monitored INTEGER DEFAULT 0,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4c. Channel Messages (Permitted public channel messages analyzed for buying signals)
CREATE TABLE IF NOT EXISTS channel_messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(64) NOT NULL UNIQUE,
    guild_id VARCHAR(32) NOT NULL,
    channel_id VARCHAR(64) NOT NULL,
    channel_name VARCHAR(128) DEFAULT '',
    author_id VARCHAR(64) NOT NULL,
    author_username VARCHAR(128) NOT NULL,
    author_display_name VARCHAR(128) DEFAULT '',
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE,
    jump_url TEXT DEFAULT '',
    has_buying_signal INTEGER DEFAULT 0,
    buying_signal_details TEXT DEFAULT '',
    detected_service VARCHAR(128) DEFAULT 'General',
    relevance_score INTEGER DEFAULT 0,
    is_saved_to_contacts INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4d. Smart Follow-Up Reminders
CREATE TABLE IF NOT EXISTS follow_up_reminders (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES customer_leads(id) ON DELETE CASCADE,
    due_date TIMESTAMP WITH TIME ZONE NOT NULL,
    interval_days INTEGER DEFAULT 2,
    suggested_message TEXT NOT NULL,
    status VARCHAR(32) DEFAULT 'Scheduled',
    context_summary TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4e. AI Chat Command Center History
CREATE TABLE IF NOT EXISTS ai_chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) DEFAULT 'default',
    role VARCHAR(32) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4b. Server Members (For communities accessible through authorized bot)
CREATE TABLE IF NOT EXISTS server_members (
    id SERIAL PRIMARY KEY,
    guild_id VARCHAR(32) NOT NULL,
    discord_user_id VARCHAR(64) NOT NULL,
    username VARCHAR(128) NOT NULL,
    display_name VARCHAR(128) DEFAULT '',
    avatar_url TEXT DEFAULT '',
    roles JSONB DEFAULT '[]'::jsonb,
    is_bot INTEGER DEFAULT 0,
    joined_at TIMESTAMP WITH TIME ZONE,
    business_tags JSONB DEFAULT '[]'::jsonb,
    notes TEXT DEFAULT '',
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, discord_user_id)
);

-- 4c. Saved Message Templates
CREATE TABLE IF NOT EXISTS message_templates (
    id SERIAL PRIMARY KEY,
    service_type VARCHAR(128) NOT NULL,
    purpose VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    template_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Lead Message History & Staging
CREATE TABLE IF NOT EXISTS lead_messages (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES customer_leads(id) ON DELETE CASCADE,
    message_type VARCHAR(64) DEFAULT 'Initial Outreach',
    content TEXT NOT NULL,
    status VARCHAR(32) DEFAULT 'Draft',
    reviewed_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Campaign Planner
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    service_type VARCHAR(128) NOT NULL,
    target_audience TEXT DEFAULT '',
    status VARCHAR(32) DEFAULT 'Planning',
    staged_pitch TEXT DEFAULT '',
    selected_prospect_ids JSONB DEFAULT '[]'::jsonb,
    selected_guild_ids JSONB DEFAULT '[]'::jsonb,
    scheduled_review_date TIMESTAMP WITH TIME ZONE,
    target_count INTEGER DEFAULT 10,
    contacted_count INTEGER DEFAULT 0,
    converted_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. System Activity & Audit History
CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    activity_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    details TEXT DEFAULT '',
    entity_type VARCHAR(64) DEFAULT 'system',
    entity_id VARCHAR(64) DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Conversation Analysis & Reply Assistance
CREATE TABLE IF NOT EXISTS conversation_assistance (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES customer_leads(id) ON DELETE SET NULL,
    contact_name VARCHAR(128) DEFAULT '',
    service_type VARCHAR(128) DEFAULT 'General IPTV',
    raw_conversation TEXT NOT NULL,
    summary TEXT DEFAULT '',
    identified_questions JSONB DEFAULT '[]'::jsonb,
    suggested_replies JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Discord Bot Settings & Guild Sync
CREATE TABLE IF NOT EXISTS bot_settings (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_guilds (
    guild_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon_url TEXT,
    member_count INTEGER DEFAULT 0,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. Discord OAuth2 Account Integration
CREATE TABLE IF NOT EXISTS discord_oauth_account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    discord_id VARCHAR(32) NOT NULL,
    username VARCHAR(128) NOT NULL,
    discriminator VARCHAR(8) DEFAULT '0',
    global_name VARCHAR(128),
    avatar VARCHAR(128),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    scope VARCHAR(128),
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS discord_user_guilds (
    guild_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(128),
    owner INTEGER DEFAULT 0,
    permissions VARCHAR(64),
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_servers_category ON discovered_servers(category);
CREATE INDEX IF NOT EXISTS idx_servers_members ON discovered_servers(approximate_member_count);
CREATE INDEX IF NOT EXISTS idx_servers_saved ON discovered_servers(is_saved_to_leads);
CREATE INDEX IF NOT EXISTS idx_leads_status ON customer_leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_followup ON customer_leads(follow_up_due_at);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_logs(created_at DESC);

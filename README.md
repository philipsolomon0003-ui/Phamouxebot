# Famous Media Technologies — Discord AI Business Assistant

An executive, private, AI-powered Discord business assistant engineered for **Famous Media Technologies**. Designed specifically for a non-technical business owner to discover high-value IPTV communities, analyze customer buying signals, draft natural conversational messages, manage 11-stage sales pipelines, and maintain smart follow-up reminders—with 100% compliance with Discord's official APIs.

---

## 🏢 Business Profile & Core Catalog

| Setting | Value |
| :--- | :--- |
| **Business Name** | **Famous Media Technologies** |
| **Official Telegram** | **`@Phamouxetv`** |
| **IPTV Subscriptions** | 1 Month: **$15** \| 3 Months: **$35** \| 6 Months: **$55** \| 12 Months: **$80** |
| **Reseller Panels** | 120 Credits: **$350** *(Includes sub-reseller creation capability)* |
| **App Rebranding** | **$150** with panel integration *(XCIPTV, IPTV Smarters Pro, Purple Player, TiviMate with hardcoded DNS)* |
| **App Development** | Android TV, Firestick, iOS, Web *(Contact for requirements & custom quote)* |
| **Server Setup** | Nginx restream load balancers, Xtream UI cluster tuning, anti-freeze kernel caching *(Custom quote)* |
| **Pricing Policy** | **Strictly transparent & editable.** The assistant never quotes unlisted prices without operator approval. |

---

## 🎨 Visual Identity & Ergonomics
- **Background & Surfaces**: Deep charcoal and obsidian black (`#070a12`, `#0d1527`, `#111a30`).
- **Brand Accents**: Restrained, professional blue tones (`#2563eb`, `#3b82f6`, `#60a5fa`).
- **Typography**: Clean, highly readable Inter font with optimized hierarchy for desktop and mobile screens.
- **Workflow Philosophy**: **Drafts and reminders by default.** The application never sends unsolicited messages or automates private DMs. The operator maintains 100% review and approval control.

---

## 🚀 1-Click Launch (No Technical Knowledge Required)

1. Double-click **`Start-PHAMOUXE.bat`** in this folder.
2. The assistant initializes the local server and automatically launches your default web browser to:
   ```
   http://127.0.0.1:8080
   ```
3. On first launch, create your private **Master Password** to secure your CRM, notes, and research data.

---

## 🔑 Discord Developer Setup (3 Simple Steps)

The assistant uses Discord's official OAuth2 and Bot Gateway architecture. **Never enter personal passwords or user tokens.**

### Step 1: Create Your Application
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and log in with your Discord account.
2. Click **New Application** (top right) and name it **Famous Media Assistant**.

### Step 2: Configure OAuth2 (User Sign-In)
1. In the left menu, click **OAuth2** → **General**.
2. Click **Add Redirect** and paste:
   ```
   http://127.0.0.1:8080/api/auth/discord/callback
   ```
3. Copy your **Client ID** and **Client Secret**.

### Step 3: Configure Bot (Server Management & Channel Search)
1. In the left menu, click **Bot**.
2. Click **Reset Token** and copy the **Bot Token**.
3. Under **Privileged Gateway Intents**, enable **Server Members Intent** and **Message Content Intent**.
4. In the assistant dashboard, open **Discord Connections**, click **Configure Discord App**, paste your Client ID, Secret, and Bot Token, and click **Save & Connect Discord**.
5. Use the 1-click **Generate Official Bot Invite** link (`permissions=274878220352`) to add your bot to any server where you have administrative permission.

---

## 📑 Core Functional Modules

### 1. Connect Discord Account
- **Official OAuth2 Login**: Sign in securely using Discord's official authorization code grant (`identify`, `guilds`).
- **Account Status**: Displays your authenticated username, discriminator, avatar, and mutual servers.
- **1-Click Disconnect**: Instantly disconnects your account and revokes access tokens locally and upstream.
- **Access Boundary Matrix**: Clearly explains what permissions are needed and provides complete visibility into what the bot can and cannot see.
- **Zero Self-Bot Guarantee**: Does not use user token scrapers or violate Discord Terms of Service.

### 2. Discord Server Management
- **Authorized Server Inspector**: View all servers your bot has been authorized to join, complete with server icons, names, and member counts.
- **Bot Permissions Transparency**: Inspect exact permission flags in each server (e.g., View Channels, Read History, Send Messages).
- **Channel Selection & Monitoring Toggle**: Choose specific public channels the bot is permitted to read. Channels are only indexed when explicitly marked as **Monitored**.
- **Server Disconnect**: 1-click button to remove a server from your workspace cache and instruct the bot to leave if desired.

### 3. AI Research Assistant
- **Community Research Scanner**: Evaluates servers and channels for discussions related to IPTV providers, reseller panels, app rebranding, and custom player development.
- **Buying Signal Classifier**: Automatically analyzes messages to detect customer requirements and purchasing intent across all 5 Famous Media services:
  - *IPTV Subscriptions*: Trials, buffer complaints, Firestick inquiries, sports feeds.
  - *Reseller Panels*: 100/120 credits inquiries, sub-reseller panel requests, wholesale terms.
  - *App Rebranding*: Smarters Pro, XCIPTV, Purple Player, TiviMate DNS hardcoding.
  - *App Development*: Custom Android TV APK mods, ExoPlayer middleware, multi-DNS failover.
  - *Server Setup*: Nginx restream load balancers, Xtream UI tuning, anti-freeze kernel caching.
- **Relevance Scoring (0–100)**: Highlights high-potential opportunities first with direct jump links to original Discord messages.
- **1-Click Save to CRM**: Instantly converts any message author into an active lead, tagged with their stated interest and Discord source.

### 4. AI Message Writer
- **9 Tailored Messaging Scenarios**:
  1. *First message after friend request accepted*
  2. *Opening based on public interest or channel discussion*
  3. *Replies to prospects who respond to your outreach*
  4. *Explaining Famous Media Technologies services clearly*
  5. *Answering questions about subscription & panel pricing*
  6. *Handling price objections professionally with zero-risk trial emphasis*
  7. *Handling 'already have a provider/app' by positioning as a backup sports feed*
  8. *Gentle follow-up for prospects who showed interest but stopped replying*
  9. *Polite, respectful sign-off when someone is not interested*
- **Conversational Writing Style**: Friendly, natural, concise English. Zero generic AI clichés, aggressive marketing hype, or false promises.
- **Manual Review Staging**: Every message is presented as an editable draft in a dedicated staging window before copying.

### 5. Conversation Workspace (11-Stage CRM)
Organize and track all prospect relationships across 11 distinct stages:
1. `New Contact`
2. `Researching`
3. `First Message Ready`
4. `Conversation Started`
5. `Interested`
6. `Needs More Information`
7. `Price Discussed`
8. `Follow-up Due`
9. `Converted Customer`
10. `Not Interested`
11. `Archived`

- **Data Origin Distinction**: Clearly distinguishes verified Discord data (`discord_received`) from notes you entered yourself (`manual_entered`).
- **Lead Profile Drawer**: View Discord username, user ID, server origin, channel, stated interests, service interest, last interaction date, next suggested action, and private notes.
- **Search & Filters**: Filter by pipeline stage, service interest, or keyword search.

### 6. Smart Follow-Up System
- **2–3 Day Reminder Interval**: When you record sending an outreach message, schedule a gentle reminder for 2 or 3 days later.
- **Automatic Reply Detection**: When a prospect replies, recording their response immediately marks the pending follow-up as resolved and suggests an appropriate conversational response.
- **Duplicate Prevention**: Limits active reminders to one per contact to prevent accidental duplicate messages.
- **Opt-Out Protection**: If a contact is moved to `Not Interested` or `Archived`, all follow-ups are strictly blocked to respect their boundaries.
- **Anti-Annoyance Limit**: Automatically caps follow-ups at 2 reminders per contact to safeguard your business reputation.
- **4 Status Tabs**: Organized into `Today's Reminders`, `Overdue`, `Upcoming`, and `Completed`.

### 7. AI Conversation Coach
When viewing any conversation, open the **AI Coach** for real-time strategic guidance:
- **Situation Summary**: Concise summary of what has happened so far.
- **What They Are Asking For**: Pinpoints the prospect's underlying need (e.g., stream stability, trial line, panel credits, hardcoded DNS).
- **Recommended Next Step**: Actionable advice on how to guide the conversation forward.
- **3 Reply Options**:
  - *Recommended Reply*: Balanced, warm, conversational response.
  - *Direct & Fast*: Concise reply for fast-moving Discord chats.
  - *Consultative & Discovery*: Thoughtful response with technical discovery questions.
- **Discovery Questions**: Recommended questions to understand their player, device, and bandwidth setup.
- **Warning Signs**: Alerts against pushing too hard (e.g., trying to sell a rebrand to an admin who already loves their custom app).

### 8. AI Command Center
A natural language chat interface that answers questions using your live database:
- *"What are my follow-ups due today?"*
- *"Summarize my most promising opportunities this week."*
- *"What are Famous Media subscription prices?"*
- *"What is the price for reseller panels?"*
- *"Write an opening message for a reseller lead."*
- *"Prepare a professional response to a price objection."*

### 9. Business Profile & Privacy Settings
- **Editable Business Settings**: Update your business name, pricing tiers ($15–$80, $350 panel, $150 rebrand), and custom notes anytime.
- **AI Provider Flexibility**: Runs out-of-the-box with built-in deterministic templates. Optionally add a Gemini or OpenAI API key for LLM-enhanced drafting.
- **Data Erasure & Reset**: 1-click tools to clear research caches, export database dumps, or reset leads in compliance with privacy best practices.
- **PostgreSQL Parity**: Production DDL schema included at `data/schema_postgres.sql` for scaling to Supabase, Neon, or cloud PostgreSQL.

---

## 🧪 Verification & Automated Test Suite

The assistant includes comprehensive test suites. To execute all tests:

```powershell
# Run the complete 12-requirement end-to-end verification
& "C:\Users\USER\AppData\Local\Programs\Python\Python314\python.exe" tests/test_famous_assistant.py

# Run the backend database & CRM tests
& "C:\Users\USER\AppData\Local\Programs\Python\Python314\python.exe" tests/test_backend.py

# Run the authentication & security flow tests
& "C:\Users\USER\AppData\Local\Programs\Python\Python314\python.exe" tests/test_auth_flow.py
```

All tests run in-process and pass with 100% success.

---

## 🔒 Security & Privacy Commitments
1. **Zero Self-Bots**: We never automate personal Discord user tokens.
2. **Local Data Sovereignty**: All leads, notes, and channel message caches remain stored locally in your private SQLite database (`data/phamouxe.db`).
3. **Drafts by Default**: The operator always reviews and approves outreach before sending.
4. **Transparent Boundaries**: The bot only reads public text channels you explicitly designate as monitored.

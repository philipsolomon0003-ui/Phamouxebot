"""
PHAMOUXE Sovereign Discord Bot Engine
Official Discord Bot Integration utilizing discord.py v2.7+.
Strictly compliant with Discord Terms of Service (No self-bots, official bot gateway only).
"""

import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, Any, List
from app.database import get_servers, get_stats, sync_bot_guilds, get_leads

logger = logging.getLogger("phamouxe.bot")

# Imperial Gold Embed Color (Strict Luxury Palette, No Blue)
EMBED_COLOR_GOLD = 0xD4AF37
EMBED_COLOR_OLIVE = 0x5C664C

class PhamouxeBot(commands.Bot):
    def __init__(self, use_privileged_intents: bool = True):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        if use_privileged_intents:
            try:
                intents.message_content = True
            except Exception:
                pass
            try:
                intents.members = True
            except Exception:
                pass
        super().__init__(command_prefix="!px ", intents=intents)
        self.is_running = False
        self.last_error = None
        self.has_message_content_intent = False

    async def setup_hook(self):
        # Register and sync slash commands with Discord global API
        try:
            await self.tree.sync()
            logger.info("PHAMOUXE Slash Commands successfully synced with Discord.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")

    async def on_ready(self):
        self.is_running = True
        self.last_error = None
        self.has_message_content_intent = bool(getattr(self.intents, "message_content", False))
        logger.info(f"PHAMOUXE Bot logged in as {self.user} (ID: {self.user.id}, Message Content Intent: {self.has_message_content_intent})")
        
        # Sync connected guilds with PHAMOUXE database
        guild_data = []
        for g in self.guilds:
            icon_url = g.icon.url if g.icon else ""
            guild_data.append({
                "id": str(g.id),
                "name": g.name,
                "icon_url": icon_url,
                "member_count": g.member_count or 0
            })
        sync_bot_guilds(guild_data)

    async def on_guild_join(self, guild):
        logger.info(f"PHAMOUXE Bot invited to new server: {guild.name}")
        # Refresh guild cache
        guild_data = [{
            "id": str(g.id),
            "name": g.name,
            "icon_url": g.icon.url if g.icon else "",
            "member_count": g.member_count or 0
        } for g in self.guilds]
        sync_bot_guilds(guild_data)

# Singleton Instance
bot_instance: Optional[PhamouxeBot] = None
bot_task: Optional[asyncio.Task] = None

def get_bot() -> PhamouxeBot:
    global bot_instance
    if bot_instance is None:
        bot_instance = PhamouxeBot()
        register_slash_commands(bot_instance)
    return bot_instance

def register_slash_commands(bot: PhamouxeBot):
    @bot.tree.command(name="famous-pricing", description="Displays official Famous Media Technologies pricing and packages.")
    async def cmd_pricing(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Famous Media Technologies — Official Services & Pricing",
            description="Premium IPTV subscriptions, wholesale reseller panels, app rebranding, and server setup.",
            color=0x2563EB
        )
        embed.add_field(name="IPTV Subscriptions", value="• 1 Month: **$15**\n• 3 Months: **$35**\n• 6 Months: **$55**\n• 12 Months: **$80**", inline=False)
        embed.add_field(name="Reseller Panels", value="• 120 Credits: **$350** (Sub-reseller creation enabled)", inline=True)
        embed.add_field(name="App Rebranding", value="• With Panel: **$150** (Hardcoded DNS, custom logo/theme)", inline=True)
        embed.add_field(name="App Development & Servers", value="• Custom Android TV/Firestick APKs\n• Streaming load balancers & Nginx setups\n• *Contact for requirements & custom quote*", inline=False)
        embed.set_footer(text="Famous Media Technologies • Direct Telegram: @Phamouxetv")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="famous-stats", description="Displays active IPTV research & customer pipeline statistics.")
    async def cmd_famous_stats(interaction: discord.Interaction):
        stats = get_stats()
        embed = discord.Embed(
            title="Famous Media Technologies Intelligence",
            description="Executive IPTV Research & Customer Pipeline",
            color=0x2563EB
        )
        embed.add_field(name="Tracked Communities", value=f"**{stats['total_servers']}** servers", inline=True)
        embed.add_field(name="Customer Leads", value=f"**{stats['saved_leads']}** leads", inline=True)
        embed.add_field(name="Follow-Ups Due", value=f"**{stats['followups_due']}** contacts", inline=True)
        embed.add_field(name="Total Reach", value=f"**{stats['total_reach']:,}** members", inline=True)
        embed.set_footer(text="Famous Media Technologies Assistant • @Phamouxetv")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="famous-search", description="Search verified IPTV servers in the database.")
    @app_commands.describe(query="Keyword: e.g. smarters, reseller, xciptv, tivimate")
    async def cmd_famous_search(interaction: discord.Interaction, query: str):
        servers = get_servers(query=query)[:3]
        if not servers:
            await interaction.response.send_message(f"No verified communities matched: `{query}`.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"Famous Media Search: '{query}'",
            description=f"Top {len(servers)} matching communities from private database.",
            color=0x2563EB
        )
        for s in servers:
            members = f"{s['approximate_member_count']:,}"
            cat = s["category"]
            embed.add_field(
                name=f"🌐 {s['name']} ({cat})",
                value=f"**Members:** {members} | **Invite:** `discord.gg/{s['invite_code']}`\n*{s['description'][:140]}...*",
                inline=False
            )
        embed.set_footer(text="Famous Media Technologies Assistant")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="famous-lead", description="Lookup an active customer lead status.")
    @app_commands.describe(business_name="Name of the server or lead business")
    async def cmd_famous_lead(interaction: discord.Interaction, business_name: str):
        leads = get_leads(query=business_name)
        if not leads:
            await interaction.response.send_message(f"No customer leads found matching '{business_name}'.", ephemeral=True)
            return
        lead = leads[0]
        embed = discord.Embed(
            title=f"Customer Lead: {lead['business_name']}",
            color=0x2563EB
        )
        embed.add_field(name="Category", value=lead["category"], inline=True)
        embed.add_field(name="Pipeline Stage", value=f"**{lead.get('stage') or lead['status']}**", inline=True)
        embed.add_field(name="Contact Role", value=lead.get("contact_role", "Owner"), inline=True)
        embed.add_field(name="Notes", value=lead.get("notes") or "No notes", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Legacy Aliases
    @bot.tree.command(name="phamouxe-stats", description="Displays active IPTV research & customer pipeline statistics.")
    async def cmd_stats(interaction: discord.Interaction):
        await cmd_famous_stats(interaction)

    @bot.tree.command(name="phamouxe-search", description="Search verified IPTV servers in the PHAMOUXE database.")
    @app_commands.describe(query="Keyword: e.g. smarters, reseller, xciptv, tivimate")
    async def cmd_search(interaction: discord.Interaction, query: str):
        await cmd_famous_search(interaction, query)

    @bot.tree.command(name="phamouxe-lead", description="Lookup an active customer lead status.")
    @app_commands.describe(business_name="Name of the server or lead business")
    async def cmd_lead(interaction: discord.Interaction, business_name: str):
        await cmd_famous_lead(interaction, business_name)

async def start_discord_bot(token: str):
    """Starts the official Discord bot in the background."""
    global bot_task, bot_instance
    bot = get_bot()
    if bot.is_running:
        logger.info("Bot is already running.")
        return

    async def runner():
        nonlocal bot
        try:
            logger.info("Connecting Famous Media bot to Discord Gateway...")
            await bot.start(token)
        except discord.errors.PrivilegedIntentsRequired:
            logger.warning("PrivilegedIntentsRequired: Message Content Intent or Server Members Intent not enabled in Discord Developer Portal. Falling back to standard intents.")
            bot.last_error = "Message Content Intent is required in Discord Developer Portal > Bot > Privileged Gateway Intents to read message text."
            # Recreate bot without privileged intents so slash commands and server list still work
            bot_instance = PhamouxeBot(use_privileged_intents=False)
            register_slash_commands(bot_instance)
            try:
                await bot_instance.start(token)
            except Exception as e2:
                bot_instance.last_error = str(e2)
        except discord.LoginFailure:
            bot.last_error = "Invalid Discord Bot Token. Please verify in Developer Portal."
            logger.error(bot.last_error)
        except Exception as e:
            bot.last_error = str(e)
            logger.error(f"Error in Discord bot runner: {e}")
        finally:
            bot.is_running = False

    bot_task = asyncio.create_task(runner())

async def stop_discord_bot():
    """Stops the running bot connection."""
    global bot_task
    bot = get_bot()
    if bot and bot.is_running and not bot.is_closed():
        try:
            await bot.close()
        except Exception as e:
            logger.warning(f"Error closing bot: {e}")
    if bot_task:
        bot_task.cancel()
        bot_task = None
    bot.is_running = False

def get_bot_status() -> Dict[str, Any]:
    bot = get_bot()
    is_ready = bot.is_ready() and bot.is_running
    latency = round(bot.latency * 1000, 1) if is_ready else 0
    guilds = []
    if is_ready:
        for g in bot.guilds:
            guilds.append({
                "id": str(g.id),
                "name": g.name,
                "member_count": g.member_count or 0,
                "icon_url": g.icon.url if g.icon else ""
            })

    return {
        "is_connected": is_ready,
        "bot_username": str(bot.user) if is_ready else None,
        "bot_id": str(bot.user.id) if is_ready else None,
        "latency_ms": latency,
        "guild_count": len(guilds),
        "guilds": guilds,
        "last_error": bot.last_error
    }

async def fetch_and_cache_guild_members(guild_id: str, limit: int = 100) -> Dict[str, Any]:
    """
    Fetches real members for an authorized community where the official bot is installed.
    Requires Server Members Intent in Discord Developer Portal.
    """
    bot = get_bot()
    if not bot.is_ready():
        return {"success": False, "error": "Bot is not connected to Discord Gateway."}

    guild = bot.get_guild(int(guild_id))
    if not guild:
        return {"success": False, "error": f"Official bot is not currently a member of server ID {guild_id}."}

    try:
        members_data = []
        async for m in guild.fetch_members(limit=limit):
            roles = [r.name for r in m.roles if r.name != "@everyone"]
            tags = []
            role_text = " ".join(roles).lower()
            name_text = f"{m.name} {m.display_name}".lower()

            if any(k in role_text or k in name_text for k in ["admin", "owner", "mod", "founder", "lead"]):
                tags.append("Leadership")
            if any(k in role_text or k in name_text for k in ["reseller", "wholesale", "credits", "panel"]):
                tags.append("Reseller")
            if any(k in role_text or k in name_text for k in ["dev", "coder", "engineer", "apk"]):
                tags.append("Developer")
            if any(k in role_text or k in name_text for k in ["rebrand", "smarters", "xciptv", "tivimate"]):
                tags.append("Rebranding")
            if any(k in role_text or k in name_text for k in ["vip", "premium", "subscriber"]):
                tags.append("VIP Subscriber")

            members_data.append({
                "discord_user_id": str(m.id),
                "username": m.name,
                "display_name": m.display_name,
                "avatar_url": m.display_avatar.url if m.display_avatar else "",
                "roles": roles,
                "is_bot": m.bot,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                "business_tags": tags,
                "notes": ""
            })

        from app.database import save_server_members
        saved_count = save_server_members(str(guild.id), members_data)
        return {"success": True, "count": saved_count, "members": members_data}
    except discord.Forbidden:
        return {
            "success": False,
            "error": "Missing 'Server Members Intent'. Please enable 'Server Members Intent' under Privileged Gateway Intents in Discord Developer Portal."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# --------------------------------------------------------------------------
# Bot Invite & Official Authorization Link Generator
# --------------------------------------------------------------------------

def generate_bot_invite_url(client_id: Optional[str] = None, permissions_int: int = 2147551296, guild_id: Optional[str] = None) -> str:
    """
    Generates official Discord OAuth2 Bot Authorization URL with preconfigured permissions.
    Permissions: View Channels, Read Message History, Send Messages, Embed Links, Attach Files, Use Application Commands.
    """
    from app.database import get_bot_setting
    effective_id = (client_id or get_bot_setting("discord_client_id") or os.getenv("DISCORD_CLIENT_ID", "")).strip()
    if not effective_id:
        return ""
    url = f"https://discord.com/oauth2/authorize?client_id={effective_id}&scope=bot%20applications.commands&permissions={permissions_int}"
    if guild_id and str(guild_id).strip():
        url += f"&guild_id={str(guild_id).strip()}"
    return url

# --------------------------------------------------------------------------
# Guild Bot Permissions Inspector
# --------------------------------------------------------------------------

def get_guild_bot_permissions(guild_id: str) -> Dict[str, Any]:
    """
    Inspects official Discord bot permissions inside a connected server.
    Ensures complete transparency into authorized access boundaries.
    """
    bot = get_bot()
    if not bot.is_ready():
        return {
            "is_connected": False,
            "has_access": False,
            "error": "Bot gateway is offline."
        }

    try:
        guild = bot.get_guild(int(guild_id))
    except Exception:
        guild = None

    if not guild or not guild.me:
        return {
            "is_connected": True,
            "has_access": False,
            "error": f"Bot is not present in server ID {guild_id}."
        }

    perms = guild.me.guild_permissions
    details = {
        "is_connected": True,
        "has_access": True,
        "guild_name": guild.name,
        "guild_id": str(guild.id),
        "bot_nickname": guild.me.display_name,
        "is_admin": perms.administrator,
        "can_view_channels": perms.view_channel,
        "can_read_history": perms.read_message_history,
        "can_send_messages": perms.send_messages,
        "can_embed_links": perms.embed_links,
        "can_manage_messages": perms.manage_messages,
        "permissions_value": perms.value,
        "summary": (
            "Full Administrative Control" if perms.administrator
            else "Standard Channel Reader & History Access" if (perms.view_channel and perms.read_message_history)
            else "Restricted Access (Missing channel or history permissions)"
        )
    }
    return details

# --------------------------------------------------------------------------
# Guild Channels Fetch & Monitored Channel Management
# --------------------------------------------------------------------------

async def fetch_and_cache_guild_channels(guild_id: str) -> Dict[str, Any]:
    """
    Discovers all accessible public text/announcement channels in the server.
    """
    bot = get_bot()
    if not bot.is_ready():
        return {"success": False, "error": "Bot gateway is offline."}

    guild = bot.get_guild(int(guild_id))
    if not guild:
        return {"success": False, "error": f"Bot is not in server ID {guild_id}."}

    channels_data = []
    from app.database import get_server_channels, save_server_channels
    existing_channels = {c["channel_id"]: c for c in get_server_channels(guild_id)}

    for ch in guild.channels:
        if isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.ForumChannel)):
            # Check bot permissions in this specific channel
            perms = ch.permissions_for(guild.me)
            if not perms.view_channel:
                continue

            existing = existing_channels.get(str(ch.id))
            is_mon = bool(existing["is_monitored"]) if existing else False

            ch_type = "announcement" if getattr(ch, "is_news", lambda: False)() else "text"
            channels_data.append({
                "id": str(ch.id),
                "name": ch.name,
                "type": ch_type,
                "topic": getattr(ch, "topic", "") or "",
                "is_monitored": is_mon
            })

    saved_count = save_server_channels(str(guild.id), channels_data)
    return {
        "success": True,
        "guild_id": str(guild.id),
        "guild_name": guild.name,
        "channels": channels_data,
        "count": saved_count
    }

# --------------------------------------------------------------------------
# Message Analyzer & Buying Signal Classification
# --------------------------------------------------------------------------

def analyze_message_for_buying_signals(content: str) -> Dict[str, Any]:
    """
    Evaluates message text for customer requirements, questions, and buying signals
    matching Famous Media Technologies core services.
    """
    text = content.lower()
    signals = []
    detected_service = "General IPTV"
    score = 0

    # 1. IPTV Subscriptions
    sub_matches = [k for k in ["trial", "test line", "m3u", "sports 4k", "firestick stream", "buffering with current", "need a new provider", "good iptv", "stable streams", "sub price", "looking for sub"] if k in text]
    if sub_matches:
        signals.append(f"Inquiring about subscription / test lines: {', '.join(sub_matches[:3])}")
        detected_service = "IPTV Subscriptions"
        score += 35 + len(sub_matches) * 15

    # 2. Reseller Panels
    reseller_matches = [k for k in ["reseller", "credits", "wholesale", "sub reseller", "panel", "restream", "100 credits", "panel pricing", "xtream codes credit", "zapx", "1stream"] if k in text]
    if reseller_matches:
        signals.append(f"Wholesale reseller inquiry: {', '.join(reseller_matches[:3])}")
        detected_service = "Reseller Panels"
        score += 45 + len(reseller_matches) * 15

    # 3. App Rebranding
    rebrand_matches = [k for k in ["rebrand", "smarters pro", "xciptv", "tivimate rebrand", "dns hardcode", "custom player apk", "white label", "brand my player", "custom splash"] if k in text]
    if rebrand_matches:
        signals.append(f"App rebranding requirement: {', '.join(rebrand_matches[:3])}")
        detected_service = "App Rebranding"
        score += 50 + len(rebrand_matches) * 15

    # 4. App Development
    app_dev_matches = [k for k in ["custom app", "developer", "apk mod", "exoplayer", "firestick app dev", "webos app", "tizen app", "source code", "app build"] if k in text]
    if app_dev_matches:
        signals.append(f"Custom streaming app development need: {', '.join(app_dev_matches[:3])}")
        detected_service = "App Development"
        score += 45 + len(app_dev_matches) * 15

    # 5. Server Setup
    server_matches = [k for k in ["load balancer", "xtream ui setup", "nginx restream", "server freeze", "anti freeze kernel", "streaming server", "10gbps port", "restream server"] if k in text]
    if server_matches:
        signals.append(f"Server & load balancer infrastructure inquiry: {', '.join(server_matches[:3])}")
        detected_service = "Server Setup"
        score += 40 + len(server_matches) * 15

    has_signal = len(signals) > 0 or "?" in content
    if not signals and "?" in content and len(content.split()) > 3:
        signals.append("Asking general question in community channel")
        score = 25

    return {
        "has_buying_signal": has_signal,
        "buying_signal_details": "; ".join(signals) if signals else "",
        "detected_service": detected_service,
        "relevance_score": min(score, 100)
    }

# --------------------------------------------------------------------------
# Permitted Channel Message Reading & Indexing
# --------------------------------------------------------------------------

async def fetch_and_index_channel_messages(guild_id: str, channel_id: str, limit: int = 50) -> Dict[str, Any]:
    """
    Reads public channel history from authorized, monitored channels.
    Auto-enables monitoring upon operator's explicit request to read discussions.
    """
    bot = get_bot()
    if not bot.is_ready():
        return {"success": False, "error": "Bot gateway is offline. Please verify bot token on the Discord Connections tab."}

    channel = bot.get_channel(int(channel_id))
    if not channel:
        try:
            channel = await bot.fetch_channel(int(channel_id))
        except Exception:
            return {"success": False, "error": f"Channel ID {channel_id} is not accessible by the bot."}

    # Verify channel permissions
    if hasattr(channel, "guild") and channel.guild and channel.guild.me:
        perms = channel.permissions_for(channel.guild.me)
        if not perms.view_channel:
            return {"success": False, "error": f"Bot lacks 'View Channel' permission in #{channel.name}."}
        if not perms.read_message_history:
            return {"success": False, "error": f"Bot lacks 'Read Message History' permission in #{channel.name}."}

    from app.database import update_channel_monitoring, save_channel_messages
    # Operator reading discussions implies authorized monitoring permission
    update_channel_monitoring(guild_id, channel_id, True)

    try:
        messages_data = []
        raw_inspected = 0
        empty_content_count = 0

        async for m in channel.history(limit=limit):
            if m.author.bot:
                continue

            raw_inspected += 1
            content = m.content.strip() if m.content else ""

            if not content:
                empty_content_count += 1
                if m.attachments:
                    content = f"[Attachment: {m.attachments[0].filename}]"
                elif m.embeds:
                    content = f"[Embed: {m.embeds[0].title or 'Rich Media'}]"
                else:
                    content = "[No text content]"

            analysis = analyze_message_for_buying_signals(content)
            jump_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{m.id}"
            author_avatar = m.author.display_avatar.url if hasattr(m.author, "display_avatar") and m.author.display_avatar else "https://cdn.discordapp.com/embed/avatars/0.png"

            messages_data.append({
                "message_id": str(m.id),
                "author_id": str(m.author.id),
                "author_username": str(m.author.name),
                "author_display_name": getattr(m.author, "display_name", str(m.author.name)),
                "author_avatar": author_avatar,
                "content": content,
                "timestamp": m.created_at.isoformat() if m.created_at else None,
                "jump_url": jump_url,
                "has_buying_signal": analysis["has_buying_signal"],
                "buying_signal_details": analysis["buying_signal_details"],
                "detected_service": analysis["detected_service"],
                "relevance_score": analysis["relevance_score"]
            })

        saved_count = save_channel_messages(str(guild_id), str(channel_id), channel.name, messages_data)

        intent_warning = None
        if raw_inspected > 0 and empty_content_count == raw_inspected:
            intent_warning = "Discord returned empty text for all messages. To read message text, please enable 'Message Content Intent' in the Discord Developer Portal under Bot > Privileged Gateway Intents."

        return {
            "success": True,
            "count": saved_count,
            "channel_id": str(channel_id),
            "channel_name": channel.name,
            "buying_signals_found": sum(1 for m in messages_data if m["has_buying_signal"]),
            "messages": messages_data,
            "warning": intent_warning
        }
    except discord.Forbidden:
        return {
            "success": False,
            "error": f"Discord denied access to channel history in #{channel.name}. Check bot permissions."
        }
    except discord.HTTPException as e:
        if e.status == 429:
            return {"success": False, "error": "Discord rate limited message requests. Please wait a moment and retry."}
        return {"success": False, "error": f"Discord API error: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --------------------------------------------------------------------------
# Server Disconnect & Removal
# --------------------------------------------------------------------------

async def leave_guild(guild_id: str) -> Dict[str, Any]:
    """
    Disconnects official bot from server and cleans workspace cache.
    """
    bot = get_bot()
    guild_name = guild_id
    if bot.is_ready():
        guild = bot.get_guild(int(guild_id))
        if guild:
            guild_name = guild.name
            try:
                await guild.leave()
            except Exception as e:
                logger.warning(f"Could not leave guild via API: {e}")

    from app.database import remove_server_from_workspace, log_activity
    remove_server_from_workspace(str(guild_id))
    log_activity("server_removed", f"Removed Server from Workspace: {guild_name}", f"Guild ID: {guild_id}", "server", str(guild_id))

    return {"success": True, "message": f"Successfully disconnected and removed server '{guild_name}' from workspace."}

"""
PHAMOUXE Legitimate IPTV Community Discovery Engine
Uses official Discord API endpoints to resolve and inspect community invites.
Explains real discovery capabilities and API boundaries transparently.
"""

import re
import json
import logging
import aiohttp
from typing import Optional, Dict, Any, List
from app.database import save_or_update_server, get_connection

logger = logging.getLogger("phamouxe.discovery")

# Exact keyword sets requested
DISCOVERY_KEYWORDS = [
    "IPTV reseller",
    "IPTV app rebranding",
    "IPTV app development",
    "Streaming app developer",
    "Reseller panel",
    "Streaming service provider",
    "Android and iOS streaming applications",
    "IPTV website development"
]

CATEGORIES_RULES = {
    "IPTV reseller": [
        "reseller", "wholesale", "credits", "sub-reseller", "restream",
        "master reseller", "panel credits", "dealer", "super reseller"
    ],
    "IPTV app rebranding": [
        "rebrand", "rebranding", "white-label", "whitelabel", "smarters",
        "xciptv", "tivimate", "purple player", "dns hardcode", "custom player"
    ],
    "IPTV app development": [
        "app dev", "developer", "apk mod", "android studio", "middleware",
        "load balancer", "source code", "tizen", "webos", "exoplayer"
    ],
    "Streaming app developer": [
        "streaming app developer", "flutter iptv", "android tv dev", "firestick dev",
        "native player", "stb emu", "stalker portal"
    ],
    "Reseller panel": [
        "reseller panel", "xtream", "xtream codes", "zapx", "streamcreed", "1-stream",
        "credit allocation", "sub-reseller panel", "line generator"
    ],
    "Streaming service provider": [
        "streaming service provider", "subscription", "vip", "sports feed", "ppv",
        "4k stream", "fhd stream", "m3u8", "live tv", "vod library"
    ],
    "Android and iOS streaming applications": [
        "android and ios", "ios iptv", "apple tv", "testflight", "smarters ios",
        "swift iptv", "android tv apk", "firestick app", "smart tv app"
    ],
    "IPTV website development": [
        "iptv website development", "whmcs", "billing portal", "payment gateway",
        "landing page", "auto-delivery", "crypto billing", "wordpress iptv"
    ]
}

def clean_invite_code(raw_input: str) -> str:
    """Extracts raw invite code from varied Discord URL formats."""
    raw = raw_input.strip()
    match = re.search(r"(?:discord(?:app)?\.(?:gg|com/invite)/)?([a-zA-Z0-9\-_]{2,32})", raw)
    if match:
        return match.group(1)
    return raw

def evaluate_business_relevance(category: str, name: str, description: str, member_count: int) -> str:
    """Explains why a discovered community is strategically relevant to the operator's business."""
    text = f"{name} {description}".lower()

    if category == "IPTV app rebranding" or any(k in text for k in ["rebrand", "smarters", "xciptv", "tivimate"]):
        return (
            "Prime prospect for white-label player builds. Server admins benefit from hardcoded DNS "
            "and custom logo branding to eliminate user confusion and boost brand retention."
        )
    elif category == "IPTV app development" or category == "Streaming app developer" or any(k in text for k in ["app dev", "developer", "apk", "exoplayer"]):
        return (
            "Technical partnership opportunity. Community requires custom Android TV / Firestick APK mods, "
            "ExoPlayer buffer optimizations, or multi-DNS failover middleware."
        )
    elif category == "Reseller panel" or category == "IPTV reseller" or any(k in text for k in ["reseller", "credits", "wholesale", "panel"]):
        return (
            f"High-volume commercial lead ({member_count:,} audience reach). Potential client for bulk credit tiers, "
            "super-reseller sub-accounts, or restream capacity."
        )
    elif category == "IPTV website development" or any(k in text for k in ["website", "whmcs", "billing", "payment"]):
        return (
            "Commercial opportunity for automated WHMCS billing portals, instant line creation on payment, "
            "and high-converting landing pages."
        )
    elif category == "Streaming service provider" or any(k in text for k in ["vip", "streams", "4k", "sports"]):
        return (
            "B2C subscription operator needing stable tier-1 source feeds, 50fps live sports feeds, "
            "and backup server infrastructure."
        )
    else:
        return (
            "Relevant IPTV ecosystem with active audience. Opportunities exist for player rebranding, "
            "restream lines, or reseller partnerships."
        )

def classify_community(name: str, description: str, existing_tags: List[str] = None) -> Dict[str, Any]:
    text = f"{name} {description}".lower()
    
    assigned_category = "IPTV reseller"
    category_scores = {}

    for category, keywords in CATEGORIES_RULES.items():
        score = sum(1 for kw in keywords if kw in text)
        category_scores[category] = score

    best_cat = max(category_scores.items(), key=lambda x: x[1])
    if best_cat[1] > 0:
        assigned_category = best_cat[0]
    elif "rebrand" in text:
        assigned_category = "IPTV app rebranding"
    elif "dev" in text:
        assigned_category = "IPTV app development"
    elif "panel" in text:
        assigned_category = "Reseller panel"

    # Business services tags
    business_services = []
    if any(k in text for k in ["reseller", "wholesale", "credits"]):
        business_services.append("IPTV reseller")
    if any(k in text for k in ["rebrand", "smarters", "xciptv", "white-label"]):
        business_services.append("IPTV app rebranding")
    if any(k in text for k in ["dev", "apk", "source code", "developer", "android"]):
        business_services.append("IPTV app development")
    if any(k in text for k in ["streaming app", "exoplayer", "tizen", "webos"]):
        business_services.append("Streaming app developer")
    if any(k in text for k in ["panel", "xtream", "middleware", "zapx"]):
        business_services.append("Reseller panel")
    if any(k in text for k in ["subscription", "channels", "vod", "vip", "streams"]):
        business_services.append("Streaming service provider")
    if any(k in text for k in ["website", "whmcs", "billing", "payment"]):
        business_services.append("IPTV website development")

    if not business_services:
        business_services.append(assigned_category)

    # Generated tags
    found_tags = set(existing_tags or [])
    tag_keywords = [
        "iptv", "reseller", "rebrand", "smarters", "xciptv", "tivimate",
        "xtream", "wholesale", "android", "firestick", "vod", "sports",
        "4k", "apk", "middleware", "credits", "anti-freeze", "whmcs"
    ]
    for tk in tag_keywords:
        if tk in text:
            found_tags.add(tk)

    return {
        "category": assigned_category,
        "business_services": list(business_services),
        "tags": list(found_tags)
    }

async def fetch_discord_invite(invite_code: str) -> Optional[Dict[str, Any]]:
    """
    Queries Discord's official public API for invite and guild information.
    Zero bot token needed, official endpoint with member count and presence.
    """
    code = clean_invite_code(invite_code)
    if not code:
        return None

    api_url = f"https://discord.com/api/v10/invites/{code}?with_counts=true&with_expiration=true"
    
    headers = {
        "User-Agent": "PHAMOUXE-Intelligence/2.5 (Official API Compliance; +https://phamouxe.com)"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    guild = data.get("guild", {})
                    if not guild:
                        return None

                    guild_id = guild.get("id")
                    name = guild.get("name", "Unknown Server")
                    description = guild.get("description") or data.get("channel", {}).get("name", "")
                    icon_hash = guild.get("icon")
                    icon_url = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png" if icon_hash else ""

                    member_count = data.get("approximate_member_count", 0)
                    presence_count = data.get("approximate_presence_count", 0)
                    verification_level = str(guild.get("verification_level", "None"))
                    vanity_url = guild.get("vanity_url_code") or code

                    classification = classify_community(name, description or "")
                    relevance = evaluate_business_relevance(classification["category"], name, description or "", member_count)

                    server_dict = {
                        "guild_id": guild_id,
                        "name": name,
                        "description": description or f"Active IPTV community verified via invite discord.gg/{code}",
                        "icon_url": icon_url,
                        "invite_code": code,
                        "vanity_url": vanity_url,
                        "approximate_member_count": member_count,
                        "approximate_presence_count": presence_count,
                        "category": classification["category"],
                        "tags": json.dumps(classification["tags"]),
                        "business_services": json.dumps(classification["business_services"]),
                        "verification_level": verification_level,
                        "source": "official_invite_api",
                        "business_relevance": relevance,
                        "notes": ""
                    }
                    return server_dict
                elif resp.status == 404:
                    logger.warning(f"Discord invite '{code}' expired or not found (404).")
                    return None
                elif resp.status == 429:
                    logger.error("Rate limited by Discord API. Backing off.")
                    return None
                else:
                    logger.warning(f"Discord invite fetch returned status {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"Error querying Discord Invite API for code '{code}': {e}")
        return None

async def batch_fetch_discord_invites(raw_inputs: List[str]) -> Dict[str, Any]:
    """
    Accepts a list or batch string of invite codes/URLs.
    Extracts, deduplicates, and resolves multiple Discord servers concurrently.
    Saves resolved communities directly into the database.
    """
    cleaned_codes = []
    seen = set()
    for item in raw_inputs:
        if not item:
            continue
        # Split by commas or newlines if multiple codes in one string
        parts = re.split(r"[\r\n,;\s]+", item.strip())
        for part in parts:
            if not part:
                continue
            code = clean_invite_code(part)
            if code and code not in seen:
                seen.add(code)
                cleaned_codes.append(code)

    resolved = []
    invalid = []
    
    for code in cleaned_codes:
        server = await fetch_discord_invite(code)
        if server:
            save_or_update_server(server)
            resolved.append(server)
        else:
            invalid.append(code)

    return {
        "total_scanned": len(cleaned_codes),
        "resolved_count": len(resolved),
        "invalid_count": len(invalid),
        "resolved": resolved,
        "invalid": invalid
    }

async def discover_supported_communities() -> List[Dict[str, Any]]:
    """
    Returns curated and newly verified communities across the requested IPTV tags.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM discovered_servers
        ORDER BY approximate_member_count DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d.get("tags") or "[]")
        d["business_services"] = json.loads(d.get("business_services") or "[]")
        if not d.get("business_relevance"):
            d["business_relevance"] = evaluate_business_relevance(
                d.get("category", "IPTV reseller"),
                d.get("name", ""),
                d.get("description", ""),
                d.get("approximate_member_count", 0)
            )
        results.append(d)
    return results

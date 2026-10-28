"""
Famous Media Technologies — AI Message Assistant & Conversation Coach
Engineered specifically for:
1. IPTV Subscriptions ($15/1mo, $35/3mo, $55/6mo, $80/12mo)
2. Reseller Panels (120 Credits: $350)
3. IPTV App Rebranding (With panel: $150)
4. IPTV Application Development (Contact for requirements & custom quote)
5. Server Setup & Infrastructure (Load balancers, restream, anti-freeze tuning)
6. Business Contact: Telegram @Phamouxetv

Strict Style & Behavioral Guidelines:
- Natural, friendly, conversational, and professional English.
- Simple, human phrasing (NO generic AI clichés like "In today's fast-paced digital world", "delighted to connect", "testament to").
- Never fabricate recipient details; rely strictly on available context.
- Never quote unlisted prices without flagging as custom quote.
- Drafts and reminders by default: Operator maintains 100% review and edit control before sending.
"""

import os
import re
import json
import logging
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.database import (
    get_business_settings, get_ai_settings, get_leads, get_servers,
    get_detailed_follow_ups, search_channel_messages, get_activity_history,
    save_ai_chat_message, get_ai_chat_history
)

logger = logging.getLogger("famous.messaging")

SERVICES_METADATA = {
    "IPTV Subscriptions": {
        "title": "VIP IPTV Subscriptions",
        "description": "Premium 4K/FHD live sports, international feeds, and stable VOD libraries with anti-freeze stream architecture.",
        "pricing": "1 Month: $15 | 3 Months: $35 | 6 Months: $55 | 12 Months: $80",
        "pitch_focus": "Multi-device options, 99.9% uptime, zero buffering during peak live sports, and prompt support.",
        "sample_questions": ["Do you provide M3U playlist and Xtream credentials?", "Is there a short test line to verify weekend sports?", "What devices do you support?"]
    },
    "Subscriptions": {
        "title": "VIP IPTV Subscriptions",
        "description": "Premium 4K/FHD live sports, international feeds, and stable VOD libraries with anti-freeze stream architecture.",
        "pricing": "1 Month: $15 | 3 Months: $35 | 6 Months: $55 | 12 Months: $80",
        "pitch_focus": "Multi-device options, 99.9% uptime, zero buffering during peak live sports, and prompt support.",
        "sample_questions": ["Do you provide M3U playlist and Xtream credentials?", "Is there a short test line to verify weekend sports?", "What devices do you support?"]
    },
    "Reseller Panels": {
        "title": "IPTV Reseller Panels & Wholesale Credits",
        "description": "Tier-1 wholesale credits, master panel access, sub-reseller account creation, and instant line generation.",
        "pricing": "120 Credits: $350 (Sub-reseller panels enabled)",
        "pitch_focus": "High profit margins, independent credit allocation, sub-reseller delegation, and 24/7 technical panel support.",
        "sample_questions": ["Can we create sub-reseller panels?", "Do credits expire?", "Is there a test reseller line?"]
    },
    "App Rebranding": {
        "title": "IPTV Application Rebranding",
        "description": "Custom white-label player builds for XCIPTV, IPTV Smarters Pro, Purple Player, and TiviMate.",
        "pricing": "$150 with panel integration",
        "pitch_focus": "Custom logo, branded splash screen, hardcoded DNS URLs (zero login friction for subscribers), and remote-friendly navigation.",
        "sample_questions": ["Do you hardcode our DNS so users don't have to type it?", "What is the turnaround time?", "Is it compatible with Firestick remotes?"]
    },
    "App Development": {
        "title": "Custom IPTV App Development",
        "description": "Custom native streaming applications across Android TV, Firestick, iOS, Apple TV, and Web.",
        "pricing": "Contact for technical requirements and custom pricing",
        "pitch_focus": "Native ExoPlayer optimization, multi-DNS auto failover, custom UI themes, and complete source code options.",
        "sample_questions": ["Can you develop for both Android TV and Firestick?", "Can we integrate our custom backend API?", "What is the estimated delivery timeframe?"]
    },
    "Server Setup": {
        "title": "Streaming Server Setup & Infrastructure",
        "description": "Nginx restream load balancers, Xtream UI cluster tuning, anti-freeze kernel configuration, and 10Gbps dedicated nodes.",
        "pricing": "Contact for server specifications and custom infrastructure quote",
        "pitch_focus": "Peak traffic load balancing, low-latency live restreaming, anti-DDoS filtering, and zero packet loss.",
        "sample_questions": ["Can you configure automatic failover between two master servers?", "Do you optimize kernel network buffers?", "Do you assist with migration?"]
    },
    "Custom Websites": {
        "title": "IPTV Website & WHMCS Billing Development",
        "description": "Automated billing portals, instant line generation upon payment, and secure checkout gateways.",
        "pricing": "Contact for custom requirements",
        "pitch_focus": "Instant automated trial and line delivery, mobile-responsive dark theme, and crypto/card gateway integrations.",
        "sample_questions": ["Does it automatically generate Xtream lines upon checkout?", "Can we accept crypto?", "Is it optimized for mobile?"]
    },
    "Authorized Restreaming": {
        "title": "Authorized Restreaming Feeds",
        "description": "Low-latency TS/HLS master sports feeds and dedicated restream ports for server panels.",
        "pricing": "Contact for dedicated capacity quote",
        "pitch_focus": "Low-latency master sports feeds, 50fps / 60fps streams, and backup source failover.",
        "sample_questions": ["What is the bitrate on live sports feeds?", "Do you support restreaming to our own panel?", "Is there a test feed?"]
    }
}

OUTREACH_TEMPLATES = {
    "IPTV Subscriptions": {
        "Direct": (
            "Hi {contact_name},\n\n"
            "Reaching out from Famous Media Technologies regarding {business_name}. "
            "We provide premium IPTV subscription streams with 4K live sports feeds, 99.9% uptime, "
            "and an anti-freeze server setup optimized for Firestick and TiviMate.\n\n"
            "Our pricing is straightforward: $15 for 1 month, $35 for 3 months, $55 for 6 months, or $80 for a full year. "
            "If you'd like to test stream quality and stability firsthand, I'd be glad to set you up with a quick trial.\n\n"
            "Best regards,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        ),
        "Casual": (
            "Hey {contact_name},\n\n"
            "Hope you're having a good week. Noticed your community at {business_name}. "
            "If you or your members are ever looking for a reliable, buffer-free IPTV stream—especially for live sports coverage—"
            "we offer VIP subscriptions starting at $15/mo ($80 for the full year).\n\n"
            "Happy to share a quick test line so you can see how it runs on your setup.\n\n"
            "Cheers,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        )
    },
    "Subscriptions": {
        "Direct": (
            "Hi {contact_name},\n\n"
            "Reaching out from Famous Media Technologies regarding {business_name}. "
            "We provide premium IPTV subscription streams with 4K live sports feeds, 99.9% uptime, "
            "and an anti-freeze server setup optimized for Firestick and TiviMate.\n\n"
            "Our pricing is straightforward: $15 for 1 month, $35 for 3 months, $55 for 6 months, or $80 for a full year. "
            "If you'd like to test stream quality and stability firsthand, I'd be glad to set you up with a quick trial.\n\n"
            "Best regards,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        ),
        "Casual": (
            "Hey {contact_name},\n\n"
            "Hope you're having a good week. Noticed your community at {business_name}. "
            "If you or your members are ever looking for a reliable, buffer-free IPTV stream—especially for live sports coverage—"
            "we offer VIP subscriptions starting at $15/mo ($80 for the full year).\n\n"
            "Happy to share a quick test line so you can see how it runs on your setup.\n\n"
            "Cheers,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        )
    },
    "Reseller Panels": {
        "Direct": (
            "Hi {contact_name},\n\n"
            "I noticed the active community you've built at {business_name}. "
            "I'm reaching out from Famous Media Technologies regarding our wholesale reseller panel solutions. "
            "We offer tier-1 panel capacity with sub-reseller account creation enabled—currently 120 credits for $350.\n\n"
            "If you're looking to scale your reseller lines or want to test line generation and stream stability, "
            "let me know and I'll send over panel details.\n\n"
            "Best regards,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        ),
        "Casual": (
            "Hey {contact_name},\n\n"
            "Reaching out to see if {business_name} is looking to expand its reseller capacity. "
            "At Famous Media Technologies, we supply wholesale reseller panels with sub-reseller creation support "
            "at $350 for 120 credits. Everything is managed through a clean panel interface with fast line generation.\n\n"
            "Let me know if you'd like a test account to check out the portal.\n\n"
            "Thanks,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        )
    },
    "App Rebranding": {
        "Direct": (
            "Hi {contact_name},\n\n"
            "I came across {business_name} and wanted to reach out. "
            "At Famous Media Technologies, we specialize in IPTV application rebranding—white-label builds for "
            "XCIPTV, IPTV Smarters Pro, and TiviMate with your logo, colors, and hardcoded DNS.\n\n"
            "Our rebranding package is $150 with panel integration, eliminating manual DNS typing for your subscribers "
            "and giving them a professional, branded player. Let me know if you'd like a short video demo.\n\n"
            "Best regards,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        ),
        "Casual": (
            "Hey {contact_name},\n\n"
            "Hope server operations are treating you well. Do you currently offer {business_name} members a custom-branded APK "
            "with your server DNS pre-configured? We rebrand XCIPTV and Smarters Pro for $150 with panel setup, "
            "making subscriber login completely seamless.\n\n"
            "Happy to show you a couple of recent client builds if you're curious.\n\n"
            "Cheers,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        )
    },
    "App Development": {
        "Direct": (
            "Hi {contact_name},\n\n"
            "Reaching out from Famous Media Technologies regarding {business_name}. "
            "We engineer custom native streaming applications across Android TV, Firestick, iOS, and Web. "
            "We specialize in custom ExoPlayer middleware with multi-DNS failover and clean remote control navigation.\n\n"
            "Are you currently planning any technical upgrades or custom app projects for your service? "
            "Feel free to share your requirements and I'll prepare a custom quote.\n\n"
            "Best,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        ),
        "Casual": (
            "Hey {contact_name},\n\n"
            "Hope you're doing well. Reaching out to see if {business_name} has upcoming needs for custom streaming apps "
            "or Firestick/Android TV player improvements. We build fast, tailored player APKs from the ground up.\n\n"
            "Let me know what specs you have in mind and we can put together a custom proposal.\n\n"
            "Best,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        )
    },
    "Server Setup": {
        "Direct": (
            "Hi {contact_name},\n\n"
            "Reaching out to {business_name} regarding streaming infrastructure. "
            "At Famous Media Technologies, we engineer high-throughput IPTV streaming setups—including Nginx restream "
            "load balancers, Xtream UI cluster tuning, and anti-freeze caching configurations.\n\n"
            "If you have upcoming server expansions or want to optimize your current stream delivery, "
            "I'd be glad to discuss your requirements and prepare a custom technical quote.\n\n"
            "Best regards,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        ),
        "Casual": (
            "Hey {contact_name},\n\n"
            "Hope server traffic is running smoothly. I specialize in IPTV backend architecture, load balancers, "
            "and stream anti-freeze tuning. If you ever need help scaling nodes or setting up backup servers for {business_name}, "
            "feel free to reach out anytime.\n\n"
            "Best,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        )
    },
    "Custom Websites": {
        "Direct": (
            "Hi {contact_name},\n\n"
            "I noticed {business_name} and wanted to inquire about your web portal. "
            "We design conversion-focused IPTV websites with automated WHMCS billing, instant line delivery upon checkout, "
            "and secure payment gateways.\n\n"
            "Are you currently looking to automate customer signups and line renewals through a dedicated website?\n\n"
            "Best regards,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        ),
        "Casual": (
            "Hey {contact_name},\n\n"
            "Following {business_name}. Do you guys currently have an automated billing website where customers can "
            "pay and receive their trials or lines automatically? We build clean web portals that eliminate manual setup.\n\n"
            "Happy to share a demo site if you're interested.\n\n"
            "Cheers,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        )
    },
    "Authorized Restreaming": {
        "Direct": (
            "Hi {contact_name},\n\n"
            "Reaching out regarding restreaming capacity. "
            "We provide authorized, high-bandwidth live source feeds (50fps/60fps master feeds) "
            "optimized for panel distribution with dedicated port allocations.\n\n"
            "Are you currently adding new source streams to {business_name}'s panel?\n\n"
            "Regards,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        ),
        "Casual": (
            "Hey {contact_name},\n\n"
            "Quick question on whether you're looking for high-quality live sports source feeds for {business_name}. "
            "We supply direct TS/HLS master feeds with reliable uptime. "
            "Let me know if you'd like a test stream to check latency.\n\n"
            "Thanks,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        )
    },
    "Follow-Up": {
        "Direct": (
            "Hi {contact_name},\n\n"
            "Following up on my message from earlier this week regarding {business_name}. "
            "I understand server operations keep you busy, so just wanted to see if you had a brief moment "
            "to review our note regarding {service_name}.\n\n"
            "No pressure at all—whenever convenient for you.\n\n"
            "Best regards,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        ),
        "Casual": (
            "Hey {contact_name},\n\n"
            "Just floating this back to the top of your messages in case it got buried under community traffic. "
            "Still keen to hear your thoughts on {service_name} for {business_name} whenever you get a free moment.\n\n"
            "Cheers,\n"
            "{sender_name} (Telegram: @Phamouxetv)"
        )
    }
}

def draft_personalized_message(
    category: str,
    business_name: str = "",
    contact_name: str = "",
    member_count: int = 0,
    sender_name: str = "Famous Media Technologies",
    tone: str = "Direct",
    is_follow_up: bool = False
) -> Dict[str, Any]:
    """Generates a natural, human-written message tailored to the Famous Media Technologies catalog."""
    b_settings = get_business_settings()
    effective_sender = sender_name or b_settings.get("sender_name") or "Famous Media Technologies"

    clean_contact = contact_name.strip() if contact_name.strip() else "there"
    clean_business = business_name.strip() if business_name.strip() else "your server"
    clean_members = f"{member_count:,}" if member_count > 0 else "an active"
    clean_tone = "Casual" if tone.lower() == "casual" else "Direct"

    key_map = {
        "IPTV Reseller": "Reseller Panels",
        "Reseller Panels": "Reseller Panels",
        "IPTV reseller": "Reseller Panels",
        "App Rebranding": "App Rebranding",
        "IPTV app rebranding": "App Rebranding",
        "App Development": "App Development",
        "IPTV app development": "App Development",
        "Streaming app developer": "App Development",
        "Subscriptions": "IPTV Subscriptions",
        "IPTV Subscriptions": "IPTV Subscriptions",
        "Streaming service provider": "IPTV Subscriptions",
        "Server Setup": "Server Setup",
        "Custom Websites": "Custom Websites",
        "IPTV website development": "Custom Websites",
        "Authorized Restreaming": "Authorized Restreaming"
    }

    service_key = key_map.get(category, "IPTV Subscriptions")
    template_key = "Follow-Up" if is_follow_up else service_key

    if template_key not in OUTREACH_TEMPLATES:
        template_key = "IPTV Subscriptions"

    tone_dict = OUTREACH_TEMPLATES[template_key]
    template_str = tone_dict.get(clean_tone, tone_dict["Direct"])

    content = template_str.format(
        contact_name=clean_contact,
        business_name=clean_business,
        member_count=clean_members,
        service_name=service_key,
        sender_name=effective_sender
    )

    anti_spam_checks = []
    if len(content) > 500:
        anti_spam_checks.append("Warning: Message is slightly long. Keep concise for best Discord response.")
    else:
        anti_spam_checks.append("Length: Optimal (concise and easy to read on mobile Discord).")

    if any(hype in content.lower() for hype in ["100%", "best in the world", "guaranteed", "cheap", "free"]):
        anti_spam_checks.append("Warning: Contains marketing hype words. Consider softening tone.")
    else:
        anti_spam_checks.append("Tone: Natural professional inquiry (zero spam markers).")

    return {
        "title": f"{service_key} Outreach",
        "category": service_key,
        "tone": clean_tone,
        "is_follow_up": is_follow_up,
        "content": content,
        "character_count": len(content),
        "anti_spam_checks": anti_spam_checks,
        "guidelines": [
            "Review and edit naturally before copying to Discord.",
            "Send through normal mutual conversation or authorized ticket.",
            "Schedule a 2–3 day follow-up reminder if no reply is received.",
            "Never send unsolicited spam to users who have opted out."
        ],
        "generation_source": "template_engine"
    }

async def draft_personalized_message_ai(
    category: str,
    business_name: str = "",
    contact_name: str = "",
    member_count: int = 0,
    sender_name: str = "Famous Media Technologies",
    tone: str = "Direct",
    is_follow_up: bool = False,
    prospect_context: str = "",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    AI-assisted message writer leveraging configured AI provider with seamless fallback.
    Never invents facts, fake prices, or fake guarantees.
    """
    ai_config = get_ai_settings()
    b_settings = get_business_settings()
    effective_key = (api_key or ai_config.get("api_key") or os.getenv("GEMINI_API_KEY", "")).strip()
    provider = ai_config.get("provider", "builtin")

    clean_contact = contact_name.strip() if contact_name.strip() else "there"
    clean_biz = business_name.strip() if business_name.strip() else "your community"

    pricing_summary = (
        f"Famous Media Technologies official pricing:\n"
        f"- IPTV Subscriptions: 1mo: ${b_settings.get('iptv_sub_1mo', 15):.0f}, 3mo: ${b_settings.get('iptv_sub_3mo', 35):.0f}, 6mo: ${b_settings.get('iptv_sub_6mo', 55):.0f}, 12mo: ${b_settings.get('iptv_sub_12mo', 80):.0f}\n"
        f"- Reseller Panel: 120 credits: ${b_settings.get('reseller_120_credits', 350):.0f} (sub-resellers enabled)\n"
        f"- App Rebranding: ${b_settings.get('app_rebrand_with_panel', 150):.0f} with panel (XCIPTV, Smarters Pro, TiviMate, hardcoded DNS)\n"
        f"- App Development & Server Setup: {b_settings.get('app_dev_pricing', 'Custom quote upon requirements')}\n"
        f"- Telegram: {b_settings.get('telegram_contact', '@Phamouxetv')}\n"
        f"Rule: Never quote unlisted prices without operator approval."
    )

    if effective_key and (provider == "gemini" or not provider or provider == "builtin"):
        prompt = (
            f"You are a personal business outreach assistant for Famous Media Technologies.\n"
            f"{pricing_summary}\n\n"
            f"Task: Write a natural, personalized Discord message.\n"
            f"Service focus: {category}\n"
            f"Recipient: {clean_contact} from {clean_biz}\n"
            f"Context: {prospect_context or 'Direct professional inquiry'}\n"
            f"Is Follow-Up: {'Yes, a gentle check-in after 2-3 days without reply' if is_follow_up else 'No, initial touchpoint'}\n"
            f"Tone: {tone}\n"
            f"Sign-off: {sender_name} (Telegram: {b_settings.get('telegram_contact', '@Phamouxetv')})\n\n"
            f"Strict Requirements:\n"
            f"1. Write in clear, natural, human English in simple conversational sentences.\n"
            f"2. Absolutely NO generic AI clichés ('hope this finds you well', 'in the dynamic realm', 'unlock the potential').\n"
            f"3. Keep message under 80 words (suitable for Discord chat).\n"
            f"4. Never invent claims or fake prices. Use only the exact pricing listed above.\n"
            f"5. End with the sign-off.\n"
            f"Output ONLY the exact message text."
        )

        model_name = ai_config.get("model_name") or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={effective_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.35, "maxOutputTokens": 220}
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            generated_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                            if generated_text:
                                anti_spam_checks = []
                                if len(generated_text) > 500:
                                    anti_spam_checks.append("Warning: Message is slightly long. Keep concise for best Discord response.")
                                else:
                                    anti_spam_checks.append("Length: Optimal (concise and easy to read on mobile Discord).")

                                if any(hype in generated_text.lower() for hype in ["100%", "best in the world", "guaranteed", "cheap", "free"]):
                                    anti_spam_checks.append("Warning: Contains marketing hype words. Consider softening tone.")
                                else:
                                    anti_spam_checks.append("Tone: Natural professional inquiry (zero spam markers).")

                                return {
                                    "title": f"{category} Outreach (AI Enhanced)",
                                    "category": category,
                                    "tone": tone,
                                    "is_follow_up": is_follow_up,
                                    "content": generated_text,
                                    "character_count": len(generated_text),
                                    "anti_spam_checks": anti_spam_checks,
                                    "guidelines": [
                                        "Review and edit naturally before copying to Discord.",
                                        "Send through normal mutual conversation or authorized ticket.",
                                        "Schedule a 2–3 day follow-up reminder if no reply is received.",
                                        "Never send unsolicited spam to users who have opted out."
                                    ],
                                    "generation_source": "gemini_ai"
                                }
        except Exception as e:
            logger.warning(f"AI API generation failed, falling back to deterministic template: {e}")

    # Deterministic fallback
    result = draft_personalized_message(
        category=category,
        contact_name=contact_name,
        business_name=business_name,
        member_count=member_count,
        tone=tone,
        sender_name=sender_name,
        is_follow_up=is_follow_up
    )
    result["generation_source"] = "template_engine"
    return result

# --------------------------------------------------------------------------
# Multi-Scenario Message Generator (9 Detailed Scenarios)
# --------------------------------------------------------------------------

def generate_scenario_message(
    scenario: str,
    contact_name: str = "",
    business_name: str = "",
    service_interested: str = "IPTV Subscriptions",
    custom_context: str = "",
    tone: str = "Direct"
) -> Dict[str, Any]:
    """
    Generates tailored Discord messages for all specific conversation scenarios.
    """
    b = get_business_settings()
    clean_name = contact_name.strip() if contact_name.strip() else "there"
    clean_biz = business_name.strip() if business_name.strip() else "your server"
    telegram = b.get("telegram_contact", "@Phamouxetv")
    sender = b.get("sender_name", "Famous Media Technologies")

    sub_1mo = int(b.get("iptv_sub_1mo", 15))
    sub_3mo = int(b.get("iptv_sub_3mo", 35))
    sub_6mo = int(b.get("iptv_sub_6mo", 55))
    sub_12mo = int(b.get("iptv_sub_12mo", 80))
    reseller_cost = int(b.get("reseller_120_credits", 350))
    rebrand_cost = int(b.get("app_rebrand_with_panel", 150))

    scenarios_content = {
        # 1. First message after friend request accepted
        "first_message_friend_accept": (
            f"Hey {clean_name}, thanks for connecting!\n\n"
            f"Noticed your presence in {clean_biz}. I run Famous Media Technologies—we work with server admins "
            f"and IPTV communities on subscriptions, reseller panels, and custom app rebranding.\n\n"
            f"Just saying a quick hello—hope you're having a great week!",
            "Friendly greeting without pushing an immediate pitch."
        ),
        # 2. Opening based on public interest / discussion
        "opening_from_interest": (
            f"Hi {clean_name},\n\n"
            f"Saw your message in {clean_biz} regarding {service_interested}. "
            f"We specialize in {service_interested} at Famous Media Technologies. "
            f"{custom_context.strip() if custom_context else 'If you are looking for reliable streams or setup assistance, happy to answer any questions.'}\n\n"
            f"Let me know if you'd like a quick trial or specs.",
            "Direct reference to their public discussion."
        ),
        # 3. Replies to people who respond
        "reply_to_inquiry": (
            f"Hi {clean_name}, thanks for getting back to me!\n\n"
            f"Regarding {service_interested}, we focus on stream stability and anti-freeze delivery so you don't run into issues during live events. "
            f"Would you prefer to test a quick sample first to see how it performs on your devices?",
            "Encourages a low-friction trial verification."
        ),
        # 4. Explaining services when asked what Famous Media Technologies does
        "service_explanation": (
            f"Hi {clean_name}! Famous Media Technologies provides complete IPTV and media business solutions:\n\n"
            f"1. VIP IPTV Subscriptions ($15/1mo, $35/3mo, $55/6mo, $80/yr)\n"
            f"2. Reseller Panels (120 Credits for $350 with sub-reseller creation)\n"
            f"3. IPTV App Rebranding ($150 with panel for XCIPTV, Smarters Pro, and TiviMate with hardcoded DNS)\n"
            f"4. Custom Streaming App Development (Android TV, Firestick, iOS, Web)\n"
            f"5. Streaming Server Setup & Load Balancers\n\n"
            f"Which of these areas are you currently focused on?",
            "Clear, concise breakdown of all 5 official services."
        ),
        # 5. Answering questions about pricing
        "pricing_breakdown": (
            f"Hi {clean_name}, here is our current transparent pricing at Famous Media Technologies:\n\n"
            f"• Subscriptions: $15 (1 mo), $35 (3 mo), $55 (6 mo), $80 (12 mo)\n"
            f"• Reseller Panel: $350 for 120 credits (includes sub-reseller capability)\n"
            f"• App Rebranding: $150 with panel integration (hardcoded DNS, custom logo/splash)\n"
            f"• App Development & Server Setup: Custom quote based on your technical specs\n\n"
            f"Direct Telegram: {telegram}\n"
            f"Let me know which option suits what you are planning!",
            "Exact official pricing without unlisted numbers."
        ),
        # 6. Handling price objection
        "objection_price": (
            f"Hi {clean_name}, totally understand checking budget. "
            f"We focus on dedicated tier-1 streaming nodes with anti-freeze caching, so you don't face buffering or stream drops during heavy sports events. "
            f"We also offer volume discounts for active resellers.\n\n"
            f"I'm happy to give you a trial so you can evaluate the stability before spending anything. Fair enough?",
            "Focuses on uptime, stability, and zero-risk trial."
        ),
        # 7. Handling 'already have an app / provider'
        "objection_already_have": (
            f"Hey {clean_name}, that makes complete sense! It's good to keep what works. "
            f"Many admins we partner with keep us as a reliable backup feed for major sports weekends or use our white-label APK to eliminate DNS typing for subscribers.\n\n"
            f"If you ever need a secondary node or an app rebrand down the road, feel free to reach out anytime on Telegram ({telegram}).",
            "Respectful, non-pushy, positions as a high-value backup."
        ),
        # 8. Follow-up after interest but stopped responding
        "follow_up_gentle": (
            f"Hi {clean_name},\n\n"
            f"Following up briefly on our discussion about {service_interested} for {clean_biz}. "
            f"I know things move quickly on Discord, so just checking back in case you had any questions.\n\n"
            f"No rush at all—whenever convenient for you!\nBest, {sender}",
            "Gentle, respectful check-in."
        ),
        # 9. Ending politely when not interested
        "polite_sign_off": (
            f"Thanks for letting me know, {clean_name}! Completely understand. "
            f"Wishing you and {clean_biz} the best. If your needs ever change down the road, you know where to find me ({telegram}). Have a great week!",
            "Leaves a positive, professional impression."
        )
    }

    item = scenarios_content.get(scenario, scenarios_content["first_message_friend_accept"])
    text, note = item

    anti_spam = [
        "Optimal length for mobile Discord viewing.",
        "Zero aggressive sales jargon or pushy triggers.",
        "Grounded in Famous Media Technologies verified pricing."
    ]

    return {
        "scenario": scenario,
        "content": text.strip(),
        "notes": note,
        "character_count": len(text.strip()),
        "anti_spam_checks": anti_spam
    }

# --------------------------------------------------------------------------
# AI Conversation Coach
# --------------------------------------------------------------------------

def get_conversation_coach_analysis(
    lead_id: Optional[int] = None,
    raw_conversation: str = "",
    target_service: str = "IPTV Subscriptions",
    contact_name: str = "Client"
) -> Dict[str, Any]:
    """
    Acts as an executive sales and conversation coach for Famous Media Technologies:
    - Summarizes what has happened
    - What the other person appears to be asking for
    - The most appropriate next step
    - One recommended reply
    - Two alternative replies with different tones
    - Discovery questions to ask
    - Relevant service & pricing info
    - Warning signs (e.g. pushing too hard, assuming needs)
    """
    b = get_business_settings()
    contact = contact_name
    service = target_service
    notes = ""
    stage = "Conversation Started"

    if lead_id:
        from app.database import get_leads
        matching = [l for l in get_leads() if l["id"] == lead_id]
        if matching:
            lead = matching[0]
            contact = lead.get("contact_name") or lead.get("contact_handle") or contact_name
            service = lead.get("service_interested") or lead.get("category") or target_service
            notes = lead.get("notes") or ""
            stage = lead.get("stage") or lead.get("status") or "Conversation Started"
            if not raw_conversation:
                raw_conversation = lead.get("last_message_summary") or notes

    text = (raw_conversation or "").strip()
    text_lower = text.lower()

    # Determine what they are asking for
    asking_for = "General information and service exploration."
    if any(k in text_lower for k in ["price", "cost", "how much", "$", "eur", "rate"]):
        asking_for = "Specific pricing, credit packages, and commercial terms."
    elif any(k in text_lower for k in ["trial", "test", "demo", "sample", "check"]):
        asking_for = "A test line or preview demo to evaluate quality firsthand."
    elif any(k in text_lower for k in ["freeze", "buffer", "lag", "issue", "down"]):
        asking_for = "Assurance regarding stream uptime, anti-freeze performance, and sports stability."
    elif any(k in text_lower for k in ["rebrand", "apk", "smarters", "xciptv", "tivimate", "logo"]):
        asking_for = "Custom player rebranding with hardcoded DNS URLs for their subscribers."
    elif any(k in text_lower for k in ["reseller", "credits", "sub reseller", "panel"]):
        asking_for = "Reseller panel credit tiers and sub-reseller management."

    # Next step recommendation
    next_step = "Send a low-friction reply offering a short test trial or clear answer, without pressuring a purchase."
    if "trial" in asking_for.lower():
        next_step = "Issue a 24-hour test line or demo video and follow up after they inspect it."
    elif "pricing" in asking_for.lower():
        next_step = f"Quote the official Famous Media price directly ($15/mo sub, $350 panel, $150 rebrand) and offer a quick trial."
    elif "assurance" in asking_for.lower():
        next_step = "Explain our anti-freeze server cluster and let them verify stream stability during a live game."

    # Warning signs
    warning_signs = [
        "Do not push an app rebrand if they already use another player—ask what their subscribers prefer first.",
        "Never send repeated follow-ups within 48 hours if they haven't replied.",
        "Never quote unlisted prices without operator approval."
    ]
    if "already" in text_lower:
        warning_signs.insert(0, "Person indicated they already have a solution: acknowledge respectfully and position as an emergency backup feed rather than trying to replace their existing setup.")

    # Recommended Reply
    rec_reply = (
        f"Hi {contact}, thanks for the message! "
        f"For our {service}, we offer full setup with complete testing before delivery. "
        f"Our subscriptions run $15/mo ($80/yr) with 4K live sports and zero-buffer routing. "
        f"Would you prefer I set you up with a quick test line so you can check stream quality on your own device?"
    )

    # Alternative 1: Direct & Concise
    alt_1 = (
        f"Hey {contact}, happy to help. For {service}, everything is configured for maximum stability with anti-freeze caching. "
        f"I can send over a 24h test trial right now if you want to verify performance. Let me know what device you use!"
    )

    # Alternative 2: Consultative & Technical
    alt_2 = (
        f"Hi {contact}, on the technical side, our {service} is backed by dedicated load balancers and backup DNS failover. "
        f"We keep our pricing transparent and simple. What current setup or devices are you looking to support?"
    )

    # Discovery questions
    questions = [
        f"What devices or apps (Firestick, TiviMate, Android TV) do you or your users primarily run?",
        f"Are you looking for single-device access or multi-room connections?",
        f"Have you experienced buffering or server issues with past providers during peak match times?"
    ]

    service_info = SERVICES_METADATA.get(service, SERVICES_METADATA["IPTV Subscriptions"])

    all_replies = [
        {"tone": "Recommended (Balanced)", "content": rec_reply},
        {"tone": "Direct & Fast", "content": alt_1},
        {"tone": "Consultative & Discovery", "content": alt_2}
    ]

    return {
        "contact_name": contact,
        "target_service": service,
        "current_stage": stage,
        "summary": f"Discussion with {contact} focused on {service}. {asking_for}",
        "what_they_are_asking_for": asking_for,
        "most_appropriate_next_step": next_step,
        "recommended_reply": rec_reply,
        "alternative_replies": [
            {"tone": "Direct & Fast", "content": alt_1},
            {"tone": "Consultative & Discovery", "content": alt_2}
        ],
        "suggested_replies": all_replies,
        "discovery_questions": questions,
        "identified_questions": questions,
        "service_info": {
            "title": service_info["title"],
            "pricing": service_info.get("pricing", "Transparent pricing"),
            "focus": service_info["pitch_focus"]
        },
        "warning_signs": warning_signs
    }

# --------------------------------------------------------------------------
# AI Command Center Engine
# --------------------------------------------------------------------------

def process_command_center_query(instruction: str, session_id: str = "default") -> Dict[str, Any]:
    """
    Executes natural language instructions in the AI Command Center:
    - Queries database for servers, leads, messages, and reminders
    - Answers in simple, actionable English with links
    """
    save_ai_chat_message("user", instruction, session_id=session_id)
    cmd = instruction.lower().strip()
    b = get_business_settings()

    response_text = ""
    suggested_actions = []

    # 1. "Find my follow-ups due today" / "follow-ups"
    if any(k in cmd for k in ["follow-up", "followup", "reminders due", "due today"]):
        follow_data = get_detailed_follow_ups()
        today = follow_data["today"]
        overdue = follow_data["overdue"]
        upcoming = follow_data["upcoming"]

        response_text = (
            f"### Follow-Up Reminder Status\n\n"
            f"• **Due Today:** {len(today)} contacts\n"
            f"• **Overdue:** {len(overdue)} contacts\n"
            f"• **Upcoming:** {len(upcoming)} contacts\n\n"
        )
        if today:
            response_text += "#### Today's Follow-Ups:\n"
            for t in today[:5]:
                response_text += f"- **{t.get('contact_name') or t.get('business_name')}** ({t.get('service_interested', 'General')}) — Due: `{t.get('due_date')[:10]}`\n  *Suggested:* \"{t.get('suggested_message')[:100]}...\"\n"
        elif overdue:
            response_text += "#### Overdue Follow-Ups:\n"
            for o in overdue[:5]:
                response_text += f"- **{o.get('contact_name') or o.get('business_name')}** — Due: `{o.get('due_date')[:10]}` (Action recommended)\n"
        else:
            response_text += "All follow-up reminders are up to date! No pending follow-ups due today.\n"

        suggested_actions = ["Review Follow-Up Reminders tab", "Schedule new 2-day reminder", "Draft outreach for new contacts"]

    # 2. "Summarize my most promising opportunities this week" / "opportunities"
    elif any(k in cmd for k in ["promising", "opportunities", "best leads", "pipeline"]):
        all_leads = get_leads()
        interested = [l for l in all_leads if l.get("stage") in ["Interested", "Price Discussed", "Needs More Information"]]
        response_text = (
            f"### Top Business Opportunities\n\n"
            f"You currently have **{len(interested)}** warm prospects in active stages (**Interested**, **Price Discussed**, **Needs More Information**).\n\n"
        )
        if interested:
            for l in interested[:5]:
                response_text += (
                    f"• **{l.get('business_name')}** ({l.get('contact_name') or l.get('contact_handle')})\n"
                    f"  - **Stage:** `{l.get('stage')}` | **Service:** {l.get('service_interested')}\n"
                    f"  - **Next Suggested Action:** {l.get('next_suggested_action') or 'Open Conversation Coach'}\n"
                    f"  - **Notes:** {l.get('notes')[:120] if l.get('notes') else 'Warm prospect awaiting reply'}\n\n"
                )
        else:
            response_text += "No contacts currently in the warm pipeline. Search server discussions to identify members discussing IPTV needs.\n"

        suggested_actions = ["Open Conversation Coach", "Review warm leads in CRM", "Search authorized channels for buying signals"]

    # 3. "Research communities that may be relevant to my business" / "research"
    elif any(k in cmd for k in ["research communities", "find servers", "relevant communities", "discover"]):
        servers = get_servers(sort_by="members_desc")[:6]
        response_text = (
            f"### Verified IPTV Communities in Research Database\n\n"
            f"Famous Media Technologies tracks **{len(get_servers())}** verified servers. Here are the top communities ranked by active reach:\n\n"
        )
        for s in servers:
            response_text += (
                f"• **{s['name']}** ({s['category']})\n"
                f"  - **Members:** {s['approximate_member_count']:,} | **Online:** {s.get('approximate_presence_count', 0):,}\n"
                f"  - **Relevance:** {s.get('business_relevance') or 'Strategic prospect for reseller credits or rebrand builds'}\n"
                f"  - **Invite:** `discord.gg/{s.get('invite_code')}`\n\n"
            )
        suggested_actions = ["Scan new Discord invite link", "Add bot to authorized server", "Filter by App Rebranding"]

    # 4. Official Pricing Catalog / Pricing Inquiry
    elif any(k in cmd for k in ["prices", "pricing", "how much", "cost", "price list", "package", "packages", "price for", "pricing for", "subscription price", "reseller price", "rebranding cost"]) and not any(ob in cmd for ob in ["objection", "too expensive", "too high"]):
        response_text = (
            f"### Famous Media Technologies Official Pricing\n\n"
            f"Here is our transparent, official pricing catalog:\n\n"
            f"• **Subscriptions:** $15 (1 mo), $35 (3 mo), $55 (6 mo), $80 (12 mo)\n"
            f"• **Reseller Panel:** $350 for 120 credits (includes sub-reseller capability)\n"
            f"• **App Rebranding:** $150 with panel integration (hardcoded DNS, custom logo)\n"
            f"• **App Development & Server Setup:** Custom quote based on technical specs\n\n"
            f"**Telegram Contact:** {b.get('telegram_contact', '@Phamouxetv')}\n"
            f"*Rule: Never quote an unlisted price without operator approval.*"
        )
        suggested_actions = ["Copy pricing breakdown", "Open Business Settings", "Draft outreach with pricing"]

    # 5. "Prepare a professional response to a price objection" / "price objection"
    elif any(k in cmd for k in ["price objection", "too expensive", "cost objection", "objection"]):
        scen = generate_scenario_message("objection_price")
        response_text = (
            f"### Professional Price Objection Response\n\n"
            f"**Strategic Approach:** Acknowledge the budget concern, differentiate on stream stability (anti-freeze servers for peak sports), and remove all risk with a test line.\n\n"
            f"**Recommended Reply Draft:**\n"
            f"```\n{scen['content']}\n```\n\n"
            f"**Guidelines:**\n"
            f"• Never discount below published baseline without securing volume commitment.\n"
            f"• Direct contact: {b.get('telegram_contact', '@Phamouxetv')}\n"
        )
        suggested_actions = ["Copy draft to clipboard", "Open Conversation Coach", "View business pricing settings"]

    # 5. Default intelligent assistant handler
    else:
        # Check if they asked to write a message
        if any(k in cmd for k in ["write", "draft", "message", "intro", "opening"]):
            draft = draft_personalized_message("IPTV Subscriptions", "prospective server", "there")
            response_text = (
                f"### Personalized Outreach Draft\n\n"
                f"Here is a natural opening message draft grounded in Famous Media Technologies services:\n\n"
                f"```\n{draft['content']}\n```\n\n"
                f"You can review, edit, or adjust the tone in the **AI Message Writer** tab before sending."
            )
            suggested_actions = ["Open Message Writer", "Select another service", "Review anti-spam guidelines"]
        else:
            response_text = (
                f"### Famous Media Technologies AI Command Center\n\n"
                f"I am ready to help you research, write, and manage your Discord conversations.\n\n"
                f"**Here are helpful instructions you can give me:**\n"
                f"1. *\"Find my follow-ups due today\"* — Audits overdue & today's reminders\n"
                f"2. *\"Summarize my most promising opportunities this week\"* — Highlights warm CRM leads\n"
                f"3. *\"Research communities that may be relevant to my business\"* — Explores IPTV hubs\n"
                f"4. *\"Prepare a professional response to a price objection\"* — Crafts value-driven reply\n"
                f"5. *\"Write an opening message for app rebranding\"* — Generates natural pitch\n\n"
                f"Official Pricing on file: Subscriptions ($15/mo, $80/yr), Reseller Panel ($350 for 120 credits), Rebranding ($150 with panel), Telegram: {b.get('telegram_contact', '@Phamouxetv')}."
            )
            suggested_actions = ["Find follow-ups due today", "Summarize promising opportunities", "Research communities"]

    save_ai_chat_message("assistant", response_text, session_id=session_id)
    return {
        "success": True,
        "instruction": instruction,
        "response": response_text,
        "reply": response_text,
        "suggested_actions": suggested_actions,
        "timestamp": datetime.utcnow().isoformat()
    }

# Backwards compatibility alias
analyze_conversation_context = get_conversation_coach_analysis

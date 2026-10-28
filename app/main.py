import os
import urllib.parse
import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional, List
from pydantic import BaseModel
from fastapi import FastAPI, Request, Response, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, COOKIE_NAME, HOST, PORT, DEBUG
from app.database import (
    init_db, seed_initial_research, get_servers, get_saved_communities,
    toggle_save_server, update_server_notes, get_stats,
    save_or_update_server, get_leads, create_or_update_lead,
    update_lead_status, save_lead_message, get_lead_messages,
    get_follow_ups, get_campaigns, create_campaign, update_campaign_status,
    log_activity, get_activity_history, save_conversation_record, get_conversation_records,
    export_sqlite_to_sql, get_bot_setting, set_bot_setting, get_bot_guilds,
    get_message_templates, save_message_template, delete_message_template,
    save_server_members, get_server_members, add_server_member_to_crm,
    update_followup_status,
    get_business_settings, save_business_settings,
    get_ai_settings, save_ai_settings,
    save_server_channels, get_server_channels, update_channel_monitoring,
    save_channel_messages, search_channel_messages, save_message_prospect_to_crm,
    schedule_follow_up_reminder, record_reply_received, get_detailed_follow_ups,
    approve_follow_up_message, dismiss_follow_up_reminder, reschedule_follow_up_reminder,
    save_ai_chat_message, get_ai_chat_history, clear_ai_chat_history,
    delete_lead, clear_all_leads, clear_research_cache, remove_server_from_workspace
)
from app.auth import (
    is_admin_configured, set_admin_password, check_admin_password,
    create_session, destroy_session, validate_session, get_current_user_or_none
)
from app.discovery import (
    fetch_discord_invite, discover_supported_communities, batch_fetch_discord_invites
)
from app.messaging import (
    draft_personalized_message, draft_personalized_message_ai,
    analyze_conversation_context, SERVICES_METADATA,
    generate_scenario_message, get_conversation_coach_analysis,
    process_command_center_query
)
from app.bot import (
    start_discord_bot, stop_discord_bot, get_bot_status, fetch_and_cache_guild_members,
    generate_bot_invite_url, get_guild_bot_permissions,
    fetch_and_cache_guild_channels, fetch_and_index_channel_messages, leave_guild,
    get_bot
)
from app.discord_oauth import (
    get_oauth_config, set_oauth_config, generate_authorization_url,
    verify_csrf_state, exchange_code_for_token, fetch_discord_user_profile,
    fetch_discord_user_guilds, revoke_discord_token, is_valid_discord_snowflake,
    is_valid_client_secret
)
from app.database import (
    save_discord_oauth, get_discord_oauth, delete_discord_oauth,
    save_user_guilds, get_user_guilds
)

logger = logging.getLogger("phamouxe.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & Seed
    try:
        init_db()
        seed_initial_research()
    except Exception as e:
        logger.error(f"Error during DB initialization: {e}")

    # Check for configured bot token on boot (skip persistent gateway on serverless platforms like Vercel)
    if not os.getenv("VERCEL") and not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        token = get_bot_setting("bot_token") or os.getenv("DISCORD_BOT_TOKEN")
        if token and token.strip():
            try:
                await start_discord_bot(token.strip())
            except Exception as e:
                logger.error(f"Error starting discord bot: {e}")

    yield

    # Graceful shutdown
    if not os.getenv("VERCEL") and not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        try:
            await stop_discord_bot()
        except Exception:
            pass

app = FastAPI(title="PHAMOUXE Intelligence Suite", lifespan=lifespan)

# Mount static and templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

# Auth dependency
async def auth_required(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if token and validate_session(token):
        return True
    raise HTTPException(status_code=401, detail="Unauthorized operator session. Please authenticate at /login.")

# -------------------------------------------------------------------------
# Web Views
# -------------------------------------------------------------------------

@app.get("/preview", response_class=HTMLResponse)
async def preview_view():
    preview_file = BASE_DIR / "preview.html"
    if preview_file.exists():
        return HTMLResponse(content=preview_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h3>preview.html not found</h3>", status_code=404)

@app.get("/", response_class=HTMLResponse)
async def index_view(request: Request):
    if not is_admin_configured():
        return RedirectResponse(url="/setup", status_code=303)
    token = request.cookies.get(COOKIE_NAME)
    if not token or not validate_session(token):
        return RedirectResponse(url="/login", status_code=303)

    discord_account = get_discord_oauth()
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"discord_account": discord_account})

@app.get("/connect", response_class=HTMLResponse)
async def connect_get(request: Request):
    if not is_admin_configured():
        return RedirectResponse(url="/setup", status_code=303)
    token = request.cookies.get(COOKIE_NAME)
    if not token or not validate_session(token):
        return RedirectResponse(url="/login", status_code=303)

    discord_account = get_discord_oauth()
    config = get_oauth_config()
    guilds = get_user_guilds() if discord_account else []
    return templates.TemplateResponse(request=request, name="connect.html", context={
        "is_connected": bool(discord_account),
        "user": discord_account,
        "guilds_count": len(guilds),
        "oauth_configured": config["is_configured"],
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"]
    })

@app.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request):
    if is_admin_configured():
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request=request, name="setup.html", context={"error": None})

@app.post("/setup")
async def setup_post(request: Request, password: str = Form(...), confirm_password: str = Form(...)):
    if is_admin_configured():
        return RedirectResponse(url="/login", status_code=303)
    if password != confirm_password:
        return templates.TemplateResponse(request=request, name="setup.html", context={"error": "Passwords do not match."})
    if len(password) < 6:
        return templates.TemplateResponse(request=request, name="setup.html", context={"error": "Password must be at least 6 characters long."})

    set_admin_password(password)
    token = create_session()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 30
    )
    return response

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if not is_admin_configured():
        return RedirectResponse(url="/setup", status_code=303)
    token = request.cookies.get(COOKIE_NAME)
    if token and validate_session(token):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

@app.post("/login")
async def login_post(request: Request, password: str = Form(...)):
    if not is_admin_configured():
        return RedirectResponse(url="/setup", status_code=303)
    if not check_admin_password(password):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid master password. Please verify your password or use Reset Password."})

    token = create_session()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 30
    )
    return response

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_get(request: Request):
    return templates.TemplateResponse(request=request, name="reset_password.html", context={"error": None})

@app.post("/reset-password")
async def reset_password_post(
    request: Request,
    secret_key: str = Form(...),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...)
):
    from app.config import ADMIN_SECRET_KEY
    if secret_key.strip() != ADMIN_SECRET_KEY.strip():
        return templates.TemplateResponse(request=request, name="reset_password.html", context={
            "error": "Invalid Application Secret Key. Check your .env file or run Reset-Password.bat directly."
        })
    if new_password != confirm_new_password:
        return templates.TemplateResponse(request=request, name="reset_password.html", context={
            "error": "New passwords do not match."
        })
    if len(new_password) < 6:
        return templates.TemplateResponse(request=request, name="reset_password.html", context={
            "error": "New password must be at least 6 characters long."
        })

    set_admin_password(new_password)
    token = create_session()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 30
    )
    return response

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        destroy_session(token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response

class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str

@app.post("/api/auth/change-password")
async def api_change_password(
    payload: ChangePasswordPayload,
    authenticated: bool = Depends(auth_required)
):
    if not check_admin_password(payload.current_password):
        raise HTTPException(status_code=400, detail="Current master password is incorrect.")
    if payload.new_password != payload.confirm_new_password:
        raise HTTPException(status_code=400, detail="New passwords do not match.")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")
    set_admin_password(payload.new_password)
    return JSONResponse({"success": True, "message": "Master password successfully updated."})

# -------------------------------------------------------------------------
# Phase 1 Server Discovery REST APIs
# -------------------------------------------------------------------------

@app.get("/api/servers")
async def api_get_servers(
    query: str = "",
    category: str = "All",
    service: str = "All",
    min_members: int = 0,
    saved_only: bool = False,
    sort_by: str = "members_desc",
    authenticated: bool = Depends(auth_required)
):
    servers = get_servers(
        query=query,
        category=category,
        service=service,
        min_members=min_members,
        saved_only=saved_only,
        sort_by=sort_by
    )
    return JSONResponse(servers)

class InspectRequest(BaseModel):
    invite_code: str

class BatchInspectRequest(BaseModel):
    invites: List[str]

@app.post("/api/servers/inspect")
async def api_inspect_server(
    payload: InspectRequest,
    authenticated: bool = Depends(auth_required)
):
    if not payload.invite_code.strip():
        raise HTTPException(status_code=400, detail="Invite link or code is required.")
    
    server_info = await fetch_discord_invite(payload.invite_code)
    if not server_info:
        raise HTTPException(
            status_code=404,
            detail="Could not resolve server invite. Check if the code is valid or the invite has expired."
        )

    save_or_update_server(server_info)
    return JSONResponse({"success": True, "server": server_info})

@app.post("/api/servers/batch-inspect")
async def api_batch_inspect(
    payload: BatchInspectRequest,
    authenticated: bool = Depends(auth_required)
):
    if not payload.invites:
        raise HTTPException(status_code=400, detail="At least one invite code or URL is required.")
    
    report = await batch_fetch_discord_invites(payload.invites)
    return JSONResponse(report)

@app.post("/api/servers/discover")
async def api_discover_servers(
    authenticated: bool = Depends(auth_required)
):
    discovered = await discover_supported_communities()
    return JSONResponse({
        "success": True,
        "discovered_count": len(discovered),
        "servers": discovered
    })

@app.post("/api/servers/{guild_id}/save")
async def api_save_server(
    guild_id: str,
    authenticated: bool = Depends(auth_required)
):
    new_state = toggle_save_server(guild_id)
    return JSONResponse({"success": True, "guild_id": guild_id, "saved": bool(new_state)})

class NotesPayload(BaseModel):
    notes: str

@app.post("/api/servers/{guild_id}/notes")
async def api_update_notes(
    guild_id: str,
    payload: NotesPayload,
    authenticated: bool = Depends(auth_required)
):
    update_server_notes(guild_id, payload.notes)
    return JSONResponse({"success": True, "guild_id": guild_id})

@app.get("/api/stats")
async def api_stats(
    authenticated: bool = Depends(auth_required)
):
    stats = get_stats()
    return JSONResponse(stats)

# -------------------------------------------------------------------------
# Phase 2 Customer Management CRM REST APIs
# -------------------------------------------------------------------------

@app.get("/api/leads")
async def api_get_leads(
    status: str = "All",
    search: str = "",
    category: str = "All",
    authenticated: bool = Depends(auth_required)
):
    leads = get_leads(query=search, status=status, category=category)
    return JSONResponse(leads)

class LeadPayload(BaseModel):
    id: Optional[int] = None
    guild_id: Optional[str] = None
    community_name: Optional[str] = ""
    business_name: str
    contact_name: Optional[str] = ""
    contact_role: Optional[str] = "Server Owner"
    contact_handle: Optional[str] = ""
    discord_user_id: Optional[str] = ""
    status: Optional[str] = "New Lead"
    category: Optional[str] = "IPTV reseller"
    reach_members: Optional[int] = 0
    business_interests: Optional[List[str]] = []
    notes: Optional[str] = ""
    last_interaction_date: Optional[str] = None
    last_reply_date: Optional[str] = None
    follow_up_due_at: Optional[str] = None
    follow_up_status: Optional[str] = "None"

@app.post("/api/leads")
async def api_create_or_update_lead(
    payload: LeadPayload,
    authenticated: bool = Depends(auth_required)
):
    lead_id = create_or_update_lead(payload.model_dump())
    return JSONResponse({"success": True, "lead_id": lead_id})

class FollowUpActionPayload(BaseModel):
    status: str
    postpone_days: Optional[int] = 2

@app.post("/api/leads/{lead_id}/followup-action")
async def api_lead_followup_action(
    lead_id: int,
    payload: FollowUpActionPayload,
    authenticated: bool = Depends(auth_required)
):
    update_followup_status(lead_id, payload.status, payload.postpone_days or 2)
    return JSONResponse({"success": True, "lead_id": lead_id, "status": payload.status})

class StatusUpdatePayload(BaseModel):
    status: str
    follow_up_days: Optional[int] = 0

@app.post("/api/leads/{lead_id}/status")
async def api_update_lead_status(
    lead_id: int,
    payload: StatusUpdatePayload,
    authenticated: bool = Depends(auth_required)
):
    update_lead_status(lead_id, payload.status, payload.follow_up_days)
    return JSONResponse({"success": True, "lead_id": lead_id, "status": payload.status})

class DraftRequest(BaseModel):
    category: str
    business_name: str
    contact_name: Optional[str] = ""
    member_count: Optional[int] = 0
    sender_name: Optional[str] = "PHAMOUXE Director"
    is_follow_up: Optional[bool] = False

@app.post("/api/leads/{lead_id}/draft")
async def api_draft_message(
    lead_id: int,
    payload: DraftRequest,
    authenticated: bool = Depends(auth_required)
):
    draft = draft_personalized_message(
        category=payload.category,
        business_name=payload.business_name,
        contact_name=payload.contact_name,
        member_count=payload.member_count,
        sender_name=payload.sender_name,
        is_follow_up=payload.is_follow_up
    )
    return JSONResponse(draft)

class MessageSavePayload(BaseModel):
    message_type: str
    content: str
    status: str = "Sent"

@app.post("/api/leads/{lead_id}/messages")
async def api_save_message(
    lead_id: int,
    payload: MessageSavePayload,
    authenticated: bool = Depends(auth_required)
):
    msg_id = save_lead_message(
        lead_id=lead_id,
        message_type=payload.message_type,
        content=payload.content,
        status=payload.status
    )
    return JSONResponse({"success": True, "message_id": msg_id})

@app.get("/api/leads/{lead_id}/messages")
async def api_get_messages(
    lead_id: int,
    authenticated: bool = Depends(auth_required)
):
    messages = get_lead_messages(lead_id)
    return JSONResponse(messages)

# -------------------------------------------------------------------------
# Saved Communities, Follow-ups, Campaigns, Conversation Assistant
# -------------------------------------------------------------------------

@app.get("/api/saved-communities")
async def api_saved_communities(authenticated: bool = Depends(auth_required)):
    saved = get_saved_communities()
    return JSONResponse(saved)

@app.get("/api/follow-ups")
async def api_get_follow_ups(authenticated: bool = Depends(auth_required)):
    follow_ups = get_follow_ups()
    return JSONResponse(follow_ups)

class GenericDraftRequest(BaseModel):
    category: str
    business_name: str
    contact_name: Optional[str] = ""
    member_count: Optional[int] = 0
    sender_name: Optional[str] = "PHAMOUXE Director"
    tone: Optional[str] = "Direct"
    is_follow_up: Optional[bool] = False
    prospect_context: Optional[str] = ""
    use_ai: Optional[bool] = False

@app.post("/api/messages/draft-generic")
async def api_draft_generic_message(
    payload: GenericDraftRequest,
    authenticated: bool = Depends(auth_required)
):
    if payload.use_ai:
        gemini_key = get_bot_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        draft = await draft_personalized_message_ai(
            category=payload.category,
            business_name=payload.business_name,
            contact_name=payload.contact_name or "",
            member_count=payload.member_count or 0,
            sender_name=payload.sender_name or "PHAMOUXE Director",
            tone=payload.tone or "Direct",
            is_follow_up=payload.is_follow_up or False,
            prospect_context=payload.prospect_context or "",
            api_key=gemini_key
        )
    else:
        draft = draft_personalized_message(
            category=payload.category,
            business_name=payload.business_name,
            contact_name=payload.contact_name or "",
            member_count=payload.member_count or 0,
            sender_name=payload.sender_name or "PHAMOUXE Director",
            tone=payload.tone or "Direct",
            is_follow_up=payload.is_follow_up or False
        )
    return JSONResponse(draft)

@app.get("/api/services/metadata")
async def api_services_metadata():
    return JSONResponse(SERVICES_METADATA)

class ConversationAnalysisRequest(BaseModel):
    conversation_text: str
    service_type: Optional[str] = "App Rebranding"
    contact_name: Optional[str] = "Client"
    lead_id: Optional[int] = None

@app.post("/api/conversation/analyze")
async def api_analyze_conversation(
    payload: ConversationAnalysisRequest,
    authenticated: bool = Depends(auth_required)
):
    if not payload.conversation_text.strip():
        raise HTTPException(status_code=400, detail="Conversation text is required.")

    analysis = analyze_conversation_context(
        conversation_text=payload.conversation_text,
        target_service=payload.service_type or "App Rebranding",
        contact_name=payload.contact_name or "Client"
    )

    record_id = save_conversation_record(
        lead_id=payload.lead_id,
        contact_name=payload.contact_name or "Client",
        service_type=payload.service_type or "App Rebranding",
        raw_conversation=payload.conversation_text,
        summary=analysis["summary"],
        identified_questions=analysis["identified_questions"],
        suggested_replies=analysis["suggested_replies"]
    )
    analysis["record_id"] = record_id
    return JSONResponse(analysis)

@app.get("/api/conversation/history")
async def api_conversation_history(authenticated: bool = Depends(auth_required)):
    history = get_conversation_records()
    return JSONResponse(history)

class PersonalDMIntakePayload(BaseModel):
    contact_name: str
    discord_username: Optional[str] = ""
    raw_conversation: str
    target_service: Optional[str] = "IPTV Subscriptions"
    notes: Optional[str] = ""

@app.post("/api/conversation/personal-dm")
async def api_save_personal_dm(
    payload: PersonalDMIntakePayload,
    authenticated: bool = Depends(auth_required)
):
    if not payload.raw_conversation.strip():
        raise HTTPException(status_code=400, detail="Conversation text cannot be empty.")

    contact_label = payload.contact_name.strip() or (payload.discord_username or "Prospect").strip()
    analysis = analyze_conversation_context(
        raw_conversation=payload.raw_conversation,
        target_service=payload.target_service or "IPTV Subscriptions",
        contact_name=contact_label
    )

    clean_handle = (payload.discord_username or payload.contact_name).lstrip("@").strip()
    lead_id = create_or_update_lead({
        "contact_name": contact_label,
        "contact_handle": clean_handle,
        "service_interested": payload.target_service or "IPTV Subscriptions",
        "notes": f"Personal Discord DM Logged:\n{payload.notes}\n\nSummary: {analysis['summary']}",
        "stage": "Conversation Started",
        "status": "In Discussion"
    })

    rec_id = save_conversation_record(
        lead_id=lead_id,
        contact_name=contact_label,
        service_type=payload.target_service or "IPTV Subscriptions",
        raw_conversation=payload.raw_conversation,
        summary=analysis["summary"],
        identified_questions=analysis["identified_questions"],
        suggested_replies=analysis["suggested_replies"]
    )

    analysis["lead_id"] = lead_id
    analysis["record_id"] = rec_id
    return JSONResponse({"success": True, "analysis": analysis, "lead_id": lead_id})

# -------------------------------------------------------------------------
# Message Templates REST APIs
# -------------------------------------------------------------------------

class TemplatePayload(BaseModel):
    id: Optional[int] = None
    service_type: str
    purpose: str
    title: str
    template_text: str

@app.get("/api/templates")
async def api_get_templates(
    service_type: str = "All",
    purpose: str = "All",
    authenticated: bool = Depends(auth_required)
):
    templates_list = get_message_templates(service_type=service_type, purpose=purpose)
    return JSONResponse(templates_list)

@app.post("/api/templates")
async def api_save_template(
    payload: TemplatePayload,
    authenticated: bool = Depends(auth_required)
):
    if not payload.title.strip() or not payload.template_text.strip():
        raise HTTPException(status_code=400, detail="Title and template text are required.")
    tmpl_id = save_message_template(
        service_type=payload.service_type,
        purpose=payload.purpose,
        title=payload.title,
        template_text=payload.template_text,
        template_id=payload.id
    )
    return JSONResponse({"success": True, "template_id": tmpl_id})

@app.delete("/api/templates/{template_id}")
async def api_delete_template(
    template_id: int,
    authenticated: bool = Depends(auth_required)
):
    deleted = delete_message_template(template_id)
    return JSONResponse({"success": deleted})

# -------------------------------------------------------------------------
# Server Member Research REST APIs (Authorized Integrations)
# -------------------------------------------------------------------------

@app.get("/api/members/{guild_id}")
async def api_get_guild_members(
    guild_id: str,
    query: str = "",
    role: str = "",
    tag: str = "",
    authenticated: bool = Depends(auth_required)
):
    members = get_server_members(guild_id=guild_id, query=query, role=role, tag=tag)
    return JSONResponse(members)

@app.post("/api/members/{guild_id}/sync")
async def api_sync_guild_members(
    guild_id: str,
    limit: int = 100,
    authenticated: bool = Depends(auth_required)
):
    result = await fetch_and_cache_guild_members(guild_id=guild_id, limit=limit)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to sync members."))
    return JSONResponse(result)

class MemberToLeadPayload(BaseModel):
    status: Optional[str] = "New Lead"
    follow_up_days: Optional[int] = 0
    notes: Optional[str] = ""

@app.post("/api/members/{member_id}/convert-to-lead")
async def api_convert_member_to_lead(
    member_id: int,
    payload: MemberToLeadPayload,
    authenticated: bool = Depends(auth_required)
):
    try:
        lead_id = add_server_member_to_crm(
            member_id=member_id,
            status=payload.status or "New Lead",
            follow_up_days=payload.follow_up_days or 0,
            notes=payload.notes or ""
        )
        return JSONResponse({"success": True, "lead_id": lead_id})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/campaigns")
async def api_get_campaigns(authenticated: bool = Depends(auth_required)):
    campaigns = get_campaigns()
    return JSONResponse(campaigns)

class CampaignCreatePayload(BaseModel):
    name: str
    service_type: str
    target_audience: Optional[str] = ""
    staged_pitch: Optional[str] = ""
    target_count: Optional[int] = 10
    selected_prospect_ids: Optional[List[int]] = []
    selected_guild_ids: Optional[List[str]] = []
    scheduled_review_date: Optional[str] = None

@app.post("/api/campaigns")
async def api_create_campaign(
    payload: CampaignCreatePayload,
    authenticated: bool = Depends(auth_required)
):
    if not payload.name.strip() or not payload.service_type.strip():
        raise HTTPException(status_code=400, detail="Campaign name and service type are required.")

    camp_id = create_campaign(
        name=payload.name,
        service_type=payload.service_type,
        target_audience=payload.target_audience or "",
        staged_pitch=payload.staged_pitch or "",
        target_count=payload.target_count or 10,
        selected_prospect_ids=payload.selected_prospect_ids or [],
        selected_guild_ids=payload.selected_guild_ids or [],
        scheduled_review_date=payload.scheduled_review_date
    )
    return JSONResponse({"success": True, "campaign_id": camp_id})

class CampaignStatusPayload(BaseModel):
    status: str

@app.post("/api/campaigns/{campaign_id}/status")
async def api_update_campaign_status(
    campaign_id: int,
    payload: CampaignStatusPayload,
    authenticated: bool = Depends(auth_required)
):
    update_campaign_status(campaign_id, payload.status)
    return JSONResponse({"success": True, "campaign_id": campaign_id, "status": payload.status})

@app.get("/api/activity")
async def api_get_activity(
    limit: int = 50,
    authenticated: bool = Depends(auth_required)
):
    activities = get_activity_history(limit=limit)
    return JSONResponse(activities)

@app.get("/api/export/sql")
async def api_export_sql(authenticated: bool = Depends(auth_required)):
    sql_dump = export_sqlite_to_sql()
    return Response(
        content=sql_dump,
        media_type="application/sql",
        headers={"Content-Disposition": "attachment; filename=phamouxe_export.sql"}
    )

# -------------------------------------------------------------------------
# AI Settings (Gemini Message Writer Integration)
# -------------------------------------------------------------------------

class AISettingsPayload(BaseModel):
    api_key: str

@app.get("/api/settings/ai")
async def api_get_ai_settings(authenticated: bool = Depends(auth_required)):
    key = get_bot_setting("gemini_api_key") or os.getenv("GEMINI_API_KEY", "")
    masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else ("Configured" if key else "")
    return JSONResponse({
        "configured": bool(key),
        "masked_key": masked
    })

@app.post("/api/settings/ai")
async def api_set_ai_settings(payload: AISettingsPayload, authenticated: bool = Depends(auth_required)):
    set_bot_setting("gemini_api_key", payload.api_key.strip())
    log_activity("AI Settings Updated", "Gemini API key configured for personalized message assistant.", "system")
    return JSONResponse({"success": True, "configured": bool(payload.api_key.strip())})

# -------------------------------------------------------------------------
# Phase 3 Official Discord Integration REST APIs
# -------------------------------------------------------------------------

@app.get("/api/bot/status")
async def api_bot_status(authenticated: bool = Depends(auth_required)):
    status = get_bot_status()
    has_token = bool(get_bot_setting("bot_token"))
    status["has_token_saved"] = has_token
    return JSONResponse(status)

class BotTokenPayload(BaseModel):
    token: str

@app.post("/api/bot/token")
async def api_bot_set_token(payload: BotTokenPayload, authenticated: bool = Depends(auth_required)):
    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token cannot be empty")
    
    set_bot_setting("bot_token", token)
    # Restart bot with the new token
    await stop_discord_bot()
    await start_discord_bot(token)
    return JSONResponse({"success": True, "message": "Bot token saved and connection initiated."})

@app.post("/api/bot/disconnect")
async def api_bot_disconnect(authenticated: bool = Depends(auth_required)):
    set_bot_setting("bot_token", "")
    await stop_discord_bot()
    return JSONResponse({"success": True, "message": "Discord bot disconnected."})

class InviteGenPayload(BaseModel):
    client_id: str

@app.post("/api/bot/invite")
async def api_bot_generate_invite(payload: InviteGenPayload, authenticated: bool = Depends(auth_required)):
    cid = payload.client_id.strip()
    if not cid.isdigit():
        raise HTTPException(status_code=400, detail="Client ID must be a numeric Discord Snowflake ID.")
    
    # Official OAuth2 URL with bot + application.commands scopes and standard manage/read permissions
    # Permissions: 2147551296 (View Channels, Send Messages, Embed Links, Attach Files, Read Message History, Use Slash Commands)
    invite_url = (
        f"https://discord.com/oauth2/authorize?client_id={cid}"
        "&permissions=2147551296&scope=bot%20applications.commands"
    )
    return JSONResponse({"success": True, "invite_url": invite_url})

# -------------------------------------------------------------------------
# Discord Official OAuth2 User Linking (Phase 3 Core Flow)
# -------------------------------------------------------------------------

def get_effective_redirect_uri(request: Request) -> str:
    # Check X-Forwarded-Proto header from reverse proxies (Render, Cloudflare, etc.)
    proto = request.headers.get("x-forwarded-proto", "").lower()
    host = request.headers.get("x-forwarded-host") or request.url.netloc
    scheme = proto if proto in ("http", "https") else request.url.scheme

    # Public domains must always use HTTPS for Discord OAuth2
    if "127.0.0.1" not in host and "localhost" not in host:
        scheme = "https"

    return f"{scheme}://{host}/api/auth/discord/callback"

@app.get("/api/auth/discord/login")
async def api_discord_oauth_login(request: Request):
    config = get_oauth_config()
    if not config["is_configured"]:
        error_msg = config["status_message"]
        return RedirectResponse(url=f"/?discord_error={urllib.parse.quote(error_msg)}#discord", status_code=303)

    try:
        host_redirect = get_effective_redirect_uri(request)
        auth_url, state = generate_authorization_url(redirect_uri=host_redirect)
        return RedirectResponse(url=auth_url, status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/?discord_error={urllib.parse.quote(str(e))}#discord", status_code=303)

@app.get("/api/auth/discord/callback")
async def api_discord_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    if error:
        err_msg = error_description or error
        return RedirectResponse(url=f"/?discord_error={urllib.parse.quote(err_msg)}#discord", status_code=303)

    if not code or not state:
        return RedirectResponse(url="/?discord_error=Missing+OAuth2+authorization+code+or+state#discord", status_code=303)

    if not verify_csrf_state(state):
        return RedirectResponse(url="/?discord_error=Security+validation+failed+(CSRF+state+mismatch)#discord", status_code=303)

    try:
        # 1. Exchange code for access token using request host
        host_redirect = get_effective_redirect_uri(request)
        token_data = await exchange_code_for_token(code, redirect_uri=host_redirect)
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", 604800)
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        scope = token_data.get("scope", "identify guilds")

        # 2. Fetch authenticated user profile
        user_profile = await fetch_discord_user_profile(access_token)

        # 3. Fetch user's authorized servers
        guilds = await fetch_discord_user_guilds(access_token)

        # 4. Save account & guilds in database
        account_record = {
            "id": user_profile["id"],
            "username": user_profile.get("username", "Unknown"),
            "discriminator": user_profile.get("discriminator", "0"),
            "global_name": user_profile.get("global_name"),
            "avatar": user_profile.get("avatar"),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "scope": scope
        }
        save_discord_oauth(account_record)
        save_user_guilds(guilds)

        # 5. Automatically create session for authenticated operator
        session_token = create_session()
        response = RedirectResponse(url="/?discord_connected=true#discord", status_code=303)
        response.set_cookie(
            key=COOKIE_NAME,
            value=session_token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 30
        )
        return response
    except Exception as e:
        logger.error(f"Error in Discord OAuth2 callback: {e}")
        return RedirectResponse(url=f"/?discord_error={urllib.parse.quote(str(e))}#discord", status_code=303)

@app.post("/api/auth/discord/demo-connect")
async def api_discord_demo_connect(request: Request):
    """Instant demonstration authorization for non-developers."""
    demo_user = {
        "id": "982314589211048",
        "username": "PhamouxeOperator",
        "discriminator": "0001",
        "global_name": "Phamouxe Executive",
        "avatar": None,
        "access_token": "demo_oauth2_token_verified",
        "refresh_token": "demo_refresh_token_verified",
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "scope": "identify guilds"
    }
    demo_guilds = [
        {"id": "1001", "name": "Apex Wholesale Resellers Hub", "icon": None, "owner": True, "permissions": "8"},
        {"id": "1002", "name": "Nova Rebranding Studio", "icon": None, "owner": False, "permissions": "2048"},
        {"id": "1003", "name": "Crown Media Private VIP Club", "icon": None, "owner": False, "permissions": "0"}
    ]
    save_discord_oauth(demo_user)
    save_user_guilds(demo_guilds)

    session_token = create_session()
    response = RedirectResponse(url="/?discord_connected=true", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 30
    )
    return response

@app.get("/api/auth/discord/status")
async def api_discord_oauth_status(request: Request):
    account = get_discord_oauth()
    guilds = get_user_guilds() if account else []
    config = get_oauth_config()

    masked_client_id = ""
    if config["client_id"]:
        cid = config["client_id"]
        masked_client_id = cid[:4] + "..." + cid[-4:] if len(cid) > 8 else "***"

    host_redirect = get_effective_redirect_uri(request)

    return JSONResponse({
        "is_connected": bool(account),
        "user": account,
        "guilds_count": len(guilds),
        "guilds": guilds,
        "oauth_configured": config["is_configured"],
        "client_id_configured": bool(config["client_id"]),
        "client_id": config["client_id"],
        "masked_client_id": masked_client_id,
        "redirect_uri": config["redirect_uri"],
        "suggested_redirect_uri": host_redirect,
        "is_client_id_valid": config["is_client_id_valid"],
        "is_client_secret_valid": config["is_client_secret_valid"],
        "status_message": config["status_message"]
    })

@app.post("/api/auth/discord/disconnect")
async def api_discord_oauth_disconnect(request: Request):
    account = get_discord_oauth()
    if account and account.get("access_token") and not account.get("access_token", "").startswith("demo_"):
        try:
            await revoke_discord_token(account["access_token"])
        except Exception as e:
            logger.warning(f"Failed to revoke token on Discord: {e}")
    delete_discord_oauth()

    # If triggered from form submission in browser, redirect back to startup connect screen
    content_type = request.headers.get("content-type", "")
    accept = request.headers.get("accept", "")
    if "application/x-www-form-urlencoded" in content_type or "text/html" in accept:
        response = RedirectResponse(url="/connect", status_code=303)
        response.delete_cookie(COOKIE_NAME)
        return response

    return JSONResponse({"success": True, "message": "Discord integration disconnected."})

class LinkDiscordProfilePayload(BaseModel):
    username: str
    discord_id: Optional[str] = "0"
    global_name: Optional[str] = ""
    avatar_url: Optional[str] = ""

@app.post("/api/auth/discord/link-profile")
async def api_link_discord_profile(payload: LinkDiscordProfilePayload):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    
    clean_username = username.lstrip("@")
    record = {
        "id": payload.discord_id or "102938475611223344",
        "username": clean_username,
        "discriminator": "0",
        "global_name": payload.global_name or clean_username,
        "avatar": payload.avatar_url or "",
        "access_token": "manual_link_token_active",
        "refresh_token": "manual_link_refresh",
        "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat(),
        "scope": "identify guilds"
    }
    save_discord_oauth(record)
    log_activity("Discord Account Linked", f"Linked Discord account @{clean_username}", "auth")
    return JSONResponse({"success": True, "account": record})

@app.get("/api/auth/discord/config")
async def api_discord_oauth_get_config(request: Request):
    config = get_oauth_config()
    bot_token = (get_bot_setting("bot_token") or os.getenv("DISCORD_BOT_TOKEN") or "").strip()
    bot_token_masked = (bot_token[:6] + "••••••••" + bot_token[-4:]) if len(bot_token) > 10 else ("••••••••" if bot_token else "")
    host_redirect = get_effective_redirect_uri(request)

    return JSONResponse({
        "client_id": config["client_id"],
        "client_secret_masked": config["client_secret_masked"],
        "has_client_secret": bool(config["client_secret"]),
        "bot_token_masked": bot_token_masked,
        "has_bot_token": bool(bot_token),
        "redirect_uri": config["redirect_uri"],
        "suggested_redirect_uri": host_redirect,
        "is_configured": config["is_configured"],
        "is_client_id_valid": config["is_client_id_valid"],
        "is_client_secret_valid": config["is_client_secret_valid"],
        "status_message": config["status_message"]
    })

class OAuthConfigPayload(BaseModel):
    client_id: str
    client_secret: Optional[str] = ""
    bot_token: Optional[str] = ""
    redirect_uri: Optional[str] = "http://127.0.0.1:8080/api/auth/discord/callback"

@app.post("/api/auth/discord/config")
async def api_discord_oauth_set_config(payload: OAuthConfigPayload, request: Request):
    cid = payload.client_id.strip()
    csecret = (payload.client_secret or "").strip()
    btoken = (payload.bot_token or "").strip()
    ruri = (payload.redirect_uri or get_effective_redirect_uri(request)).strip()

    if not cid:
        raise HTTPException(status_code=400, detail="Discord Application Client ID is required.")
    if not is_valid_discord_snowflake(cid):
        raise HTTPException(
            status_code=400,
            detail="Invalid Client ID. Discord Application Client ID must be a real 17-20 digit numeric snowflake from the Discord Developer Portal."
        )

    existing_config = get_oauth_config()
    final_secret = ""
    if csecret and "•" not in csecret and "*" not in csecret:
        if not is_valid_client_secret(csecret):
            raise HTTPException(
                status_code=400,
                detail="Invalid Client Secret. The secret must be at least 16 characters from Discord Developer Portal (OAuth2 > General)."
            )
        final_secret = csecret
    else:
        final_secret = existing_config.get("client_secret", "")
        if not final_secret:
            raise HTTPException(
                status_code=400,
                detail="Discord Client Secret is required. Copy it from Discord Developer Portal (OAuth2 > General)."
            )

    set_oauth_config(cid, final_secret, ruri)

    bot_connected = False
    if btoken and "•" not in btoken and "*" not in btoken:
        set_bot_setting("bot_token", btoken)
        try:
            await stop_discord_bot()
            await start_discord_bot(btoken)
            bot_connected = True
        except Exception as e:
            logger.warning(f"Could not automatically connect bot with new token: {e}")

    log_activity("discord_config_updated", f"Saved Discord Application credentials (Client ID: {cid})", "discord_oauth", "settings")

    return JSONResponse({
        "success": True,
        "message": "Discord Application credentials verified and saved successfully.",
        "is_configured": True,
        "bot_connected": bot_connected
    })

# -------------------------------------------------------------------------
# User Discord Servers (OAuth2 Guilds) REST APIs
# -------------------------------------------------------------------------

@app.get("/api/user/guilds")
async def api_get_user_guilds(authenticated: bool = Depends(auth_required)):
    account = get_discord_oauth()
    if not account:
        return JSONResponse({"success": False, "is_authenticated": False, "guilds": [], "count": 0})

    guilds = get_user_guilds()
    # Check live bot presence across guilds
    bot_status = get_bot_status()
    bot_guild_ids = {str(g["id"]) for g in bot_status.get("guilds", [])}
    db_bot_guilds = get_bot_guilds()
    for bg in db_bot_guilds:
        bot_guild_ids.add(str(bg.get("guild_id") or bg.get("id")))

    for g in guilds:
        gid = str(g["guild_id"])
        g["bot_connected"] = gid in bot_guild_ids
        g["invite_url"] = generate_bot_invite_url(guild_id=gid)

    return JSONResponse({
        "success": True,
        "is_authenticated": True,
        "count": len(guilds),
        "guilds": guilds,
        "user": {
            "username": account.get("username"),
            "global_name": account.get("global_name"),
            "avatar_url": account.get("avatar_url")
        }
    })

@app.post("/api/user/guilds/refresh")
async def api_refresh_user_guilds(authenticated: bool = Depends(auth_required)):
    account = get_discord_oauth()
    if not account or not account.get("access_token"):
        raise HTTPException(status_code=400, detail="Discord account is not linked. Please sign in with Discord first.")

    access_token = account["access_token"]
    if access_token.startswith("demo_"):
        guilds = get_user_guilds()
        return JSONResponse({"success": True, "count": len(guilds), "guilds": guilds, "refreshed": True})

    try:
        fresh_guilds = await fetch_discord_user_guilds(access_token)
        save_user_guilds(fresh_guilds)

        bot_status = get_bot_status()
        bot_guild_ids = {str(g["id"]) for g in bot_status.get("guilds", [])}
        db_bot_guilds = get_bot_guilds()
        for bg in db_bot_guilds:
            bot_guild_ids.add(str(bg.get("guild_id") or bg.get("id")))

        for g in fresh_guilds:
            gid = str(g["guild_id"])
            g["bot_connected"] = gid in bot_guild_ids
            g["invite_url"] = generate_bot_invite_url(guild_id=gid)

        return JSONResponse({
            "success": True,
            "count": len(fresh_guilds),
            "guilds": fresh_guilds,
            "refreshed": True
        })
    except Exception as e:
        logger.error(f"Error refreshing user guilds: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/bot/check-server/{guild_id}")
async def api_check_bot_in_server(guild_id: str, authenticated: bool = Depends(auth_required)):
    bot = get_bot()
    is_in_guild = False
    guild_name = None
    member_count = 0

    if bot.is_ready():
        try:
            guild = bot.get_guild(int(guild_id))
            if guild:
                is_in_guild = True
                guild_name = guild.name
                member_count = guild.member_count or 0
        except Exception:
            pass

    if not is_in_guild:
        db_guilds = get_bot_guilds()
        for g in db_guilds:
            if str(g.get("guild_id") or g.get("id")) == str(guild_id):
                is_in_guild = True
                guild_name = g.get("name")
                member_count = g.get("member_count", 0)
                break

    return JSONResponse({
        "guild_id": guild_id,
        "is_connected": is_in_guild,
        "name": guild_name,
        "member_count": member_count
    })

# -------------------------------------------------------------------------
# Discord Server Management & Monitored Channels REST APIs
# -------------------------------------------------------------------------

@app.get("/api/bot/servers")
async def api_get_bot_servers(authenticated: bool = Depends(auth_required)):
    bot_status = get_bot_status()
    guilds = get_bot_guilds()
    # Merge live gateway data if connected
    return JSONResponse({
        "is_connected": bot_status["is_connected"],
        "bot_username": bot_status.get("bot_username"),
        "latency_ms": bot_status.get("latency_ms", 0),
        "guilds": guilds,
        "count": len(guilds)
    })

@app.get("/api/bot/servers/{guild_id}/permissions")
async def api_get_server_permissions(guild_id: str, authenticated: bool = Depends(auth_required)):
    perms = get_guild_bot_permissions(guild_id)
    return JSONResponse(perms)

@app.get("/api/bot/servers/{guild_id}/channels")
async def api_get_server_channels(guild_id: str, authenticated: bool = Depends(auth_required)):
    res = await fetch_and_cache_guild_channels(guild_id)
    if not res.get("success"):
        # Return whatever is cached in the database if offline
        cached = get_server_channels(guild_id)
        return JSONResponse({"success": True, "channels": cached, "cached": True})
    return JSONResponse(res)

class ChannelMonitorPayload(BaseModel):
    is_monitored: bool

@app.post("/api/bot/servers/{guild_id}/channels/{channel_id}/monitor")
async def api_set_channel_monitor(
    guild_id: str,
    channel_id: str,
    payload: ChannelMonitorPayload,
    authenticated: bool = Depends(auth_required)
):
    ok = update_channel_monitoring(guild_id, channel_id, payload.is_monitored)
    return JSONResponse({"success": ok, "guild_id": guild_id, "channel_id": channel_id, "is_monitored": payload.is_monitored})

class ChannelFetchMessagesPayload(BaseModel):
    limit: Optional[int] = 50

@app.post("/api/bot/servers/{guild_id}/channels/{channel_id}/fetch-messages")
async def api_fetch_channel_messages(
    guild_id: str,
    channel_id: str,
    payload: ChannelFetchMessagesPayload,
    authenticated: bool = Depends(auth_required)
):
    res = await fetch_and_index_channel_messages(guild_id, channel_id, limit=payload.limit or 50)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to read channel messages."))
    return JSONResponse(res)

@app.get("/api/messages/search")
async def api_search_messages(
    query: str = "",
    guild_id: str = "All",
    channel_id: str = "All",
    service: str = "All",
    buying_signals_only: bool = False,
    limit: int = 50,
    authenticated: bool = Depends(auth_required)
):
    messages = search_channel_messages(
        query=query,
        guild_id=guild_id,
        channel_id=channel_id,
        service=service,
        buying_signals_only=buying_signals_only,
        limit=limit
    )
    return JSONResponse(messages)

class MessageSaveLeadPayload(BaseModel):
    notes: Optional[str] = ""
    follow_up_days: Optional[int] = 2

@app.post("/api/messages/{message_id}/save-lead")
async def api_save_message_lead(
    message_id: str,
    payload: MessageSaveLeadPayload,
    authenticated: bool = Depends(auth_required)
):
    try:
        lead_id = save_message_prospect_to_crm(
            message_id=message_id,
            notes=payload.notes or "",
            follow_up_days=payload.follow_up_days or 2
        )
        return JSONResponse({"success": True, "lead_id": lead_id})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.delete("/api/bot/servers/{guild_id}")
async def api_remove_server(guild_id: str, authenticated: bool = Depends(auth_required)):
    res = await leave_guild(guild_id)
    return JSONResponse(res)

@app.get("/api/bot/servers/{guild_id}/channels/{channel_id}/messages")
async def api_get_channel_messages(
    guild_id: str,
    channel_id: str,
    limit: int = 50,
    authenticated: bool = Depends(auth_required)
):
    messages = search_channel_messages(guild_id=guild_id, channel_id=channel_id, limit=limit)
    return JSONResponse({
        "success": True,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "count": len(messages),
        "messages": messages
    })

@app.get("/api/bot/invite-url")
async def api_get_bot_invite_url(guild_id: Optional[str] = None, authenticated: bool = Depends(auth_required)):
    url = generate_bot_invite_url(guild_id=guild_id)
    return JSONResponse({"invite_url": url, "has_client_id": bool(url), "guild_id": guild_id})

# -------------------------------------------------------------------------
# 11-Stage Conversation Workspace REST APIs
# -------------------------------------------------------------------------

class StageUpdatePayload(BaseModel):
    stage: str

@app.patch("/api/leads/{lead_id}/stage")
async def api_update_lead_stage(
    lead_id: int,
    payload: StageUpdatePayload,
    authenticated: bool = Depends(auth_required)
):
    valid_stages = [
        "New Contact", "Researching", "First Message Ready",
        "Conversation Started", "Interested", "Needs More Information",
        "Price Discussed", "Follow-up Due", "Converted Customer",
        "Not Interested", "Archived"
    ]
    if payload.stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage '{payload.stage}'. Must be one of the 11 supported stages.")

    update_lead_status(lead_id, payload.stage)
    return JSONResponse({"success": True, "lead_id": lead_id, "stage": payload.stage})

@app.delete("/api/leads/{lead_id}")
async def api_delete_lead(lead_id: int, authenticated: bool = Depends(auth_required)):
    ok = delete_lead(lead_id)
    return JSONResponse({"success": ok, "lead_id": lead_id})

@app.post("/api/leads/clear-all")
async def api_clear_all_leads(authenticated: bool = Depends(auth_required)):
    count = clear_all_leads()
    return JSONResponse({"success": True, "deleted_count": count})

# -------------------------------------------------------------------------
# Smart Follow-Up System REST APIs
# -------------------------------------------------------------------------

@app.get("/api/follow-ups/detailed")
async def api_get_detailed_follow_ups(authenticated: bool = Depends(auth_required)):
    data = get_detailed_follow_ups()
    return JSONResponse(data)

class ScheduleFollowUpPayload(BaseModel):
    interval_days: Optional[int] = 2
    custom_message: Optional[str] = ""
    context_summary: Optional[str] = ""

@app.post("/api/leads/{lead_id}/schedule-follow-up")
async def api_schedule_lead_followup(
    lead_id: int,
    payload: ScheduleFollowUpPayload,
    authenticated: bool = Depends(auth_required)
):
    res = schedule_follow_up_reminder(
        lead_id=lead_id,
        interval_days=payload.interval_days or 2,
        custom_message=payload.custom_message or "",
        context_summary=payload.context_summary or ""
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Could not schedule reminder."))
    return JSONResponse(res)

class RecordReplyPayload(BaseModel):
    reply_summary: Optional[str] = ""

@app.post("/api/leads/{lead_id}/record-reply")
async def api_record_reply(
    lead_id: int,
    payload: RecordReplyPayload,
    authenticated: bool = Depends(auth_required)
):
    res = record_reply_received(lead_id, payload.reply_summary or "")
    # Also attach conversation coach analysis for instant suggested response
    coach = get_conversation_coach_analysis(lead_id=lead_id, raw_conversation=payload.reply_summary or "")
    res["coach_analysis"] = coach
    return JSONResponse(res)

class ApproveReminderPayload(BaseModel):
    edited_message: Optional[str] = ""

@app.post("/api/follow-ups/{reminder_id}/approve")
async def api_approve_reminder(
    reminder_id: int,
    payload: ApproveReminderPayload,
    authenticated: bool = Depends(auth_required)
):
    ok = approve_follow_up_message(reminder_id, payload.edited_message or "")
    return JSONResponse({"success": ok, "reminder_id": reminder_id})

@app.post("/api/follow-ups/{reminder_id}/dismiss")
async def api_dismiss_reminder(reminder_id: int, authenticated: bool = Depends(auth_required)):
    ok = dismiss_follow_up_reminder(reminder_id)
    return JSONResponse({"success": ok, "reminder_id": reminder_id})

class RescheduleReminderPayload(BaseModel):
    extra_days: Optional[int] = 2

@app.post("/api/follow-ups/{reminder_id}/reschedule")
async def api_reschedule_reminder(
    reminder_id: int,
    payload: RescheduleReminderPayload,
    authenticated: bool = Depends(auth_required)
):
    res = reschedule_follow_up_reminder(reminder_id, payload.extra_days or 2)
    return JSONResponse(res)

# -------------------------------------------------------------------------
# AI Message Writer & Conversation Coach REST APIs
# -------------------------------------------------------------------------

class ScenarioMessagePayload(BaseModel):
    scenario: str
    contact_name: Optional[str] = ""
    business_name: Optional[str] = ""
    service_interested: Optional[str] = "IPTV Subscriptions"
    custom_context: Optional[str] = ""
    tone: Optional[str] = "Direct"

@app.post("/api/messages/scenario")
async def api_generate_scenario_message(
    payload: ScenarioMessagePayload,
    authenticated: bool = Depends(auth_required)
):
    result = generate_scenario_message(
        scenario=payload.scenario,
        contact_name=payload.contact_name or "",
        business_name=payload.business_name or "",
        service_interested=payload.service_interested or "IPTV Subscriptions",
        custom_context=payload.custom_context or "",
        tone=payload.tone or "Direct"
    )
    return JSONResponse(result)

class CoachAnalysisPayload(BaseModel):
    lead_id: Optional[int] = None
    raw_conversation: Optional[str] = ""
    target_service: Optional[str] = "IPTV Subscriptions"
    contact_name: Optional[str] = "Client"

@app.post("/api/coach/analyze")
async def api_get_coach_analysis(
    payload: CoachAnalysisPayload,
    authenticated: bool = Depends(auth_required)
):
    analysis = get_conversation_coach_analysis(
        lead_id=payload.lead_id,
        raw_conversation=payload.raw_conversation or "",
        target_service=payload.target_service or "IPTV Subscriptions",
        contact_name=payload.contact_name or "Client"
    )
    return JSONResponse(analysis)

# -------------------------------------------------------------------------
# AI Command Center (Interactive Assistant Chat)
# -------------------------------------------------------------------------

class CommandCenterPayload(BaseModel):
    instruction: str
    session_id: Optional[str] = "default"

@app.post("/api/chat/command")
async def api_post_command_center(
    payload: CommandCenterPayload,
    authenticated: bool = Depends(auth_required)
):
    if not payload.instruction.strip():
        raise HTTPException(status_code=400, detail="Instruction cannot be empty.")
    res = process_command_center_query(payload.instruction, session_id=payload.session_id or "default")
    return JSONResponse(res)

@app.get("/api/chat/history")
async def api_get_chat_history(
    session_id: str = "default",
    limit: int = 50,
    authenticated: bool = Depends(auth_required)
):
    history = get_ai_chat_history(session_id=session_id, limit=limit)
    return JSONResponse(history)

@app.delete("/api/chat/history")
async def api_clear_chat(
    session_id: str = "default",
    authenticated: bool = Depends(auth_required)
):
    clear_ai_chat_history(session_id=session_id)
    return JSONResponse({"success": True})

# -------------------------------------------------------------------------
# Business Profile & AI Settings REST APIs
# -------------------------------------------------------------------------

@app.get("/api/settings/business")
async def api_get_business_settings(authenticated: bool = Depends(auth_required)):
    settings = get_business_settings()
    return JSONResponse(settings)

class BusinessSettingsPayload(BaseModel):
    business_name: str
    telegram_contact: str
    sender_name: Optional[str] = "Famous Media Technologies"
    iptv_sub_1mo: Optional[float] = 15.0
    iptv_sub_3mo: Optional[float] = 35.0
    iptv_sub_6mo: Optional[float] = 55.0
    iptv_sub_12mo: Optional[float] = 80.0
    reseller_120_credits: Optional[float] = 350.0
    app_rebrand_with_panel: Optional[float] = 150.0
    app_dev_pricing: Optional[str] = "Contact for requirements and custom pricing"
    server_setup_pricing: Optional[str] = "Contact for infrastructure requirements"
    never_quote_unlisted: Optional[int] = 1
    notes: Optional[str] = ""

@app.post("/api/settings/business")
async def api_save_business_settings(
    payload: BusinessSettingsPayload,
    authenticated: bool = Depends(auth_required)
):
    saved = save_business_settings(payload.model_dump())
    log_activity("settings_updated", "Updated Famous Media Technologies Profile & Pricing", "business_profile", "settings")
    return JSONResponse({"success": True, "settings": saved})

class AIProviderConfigPayload(BaseModel):
    provider: str
    api_key: Optional[str] = ""
    model_name: Optional[str] = "gemini-1.5-flash"
    temperature: Optional[float] = 0.3

@app.get("/api/settings/ai-provider")
async def api_get_ai_provider(authenticated: bool = Depends(auth_required)):
    cfg = get_ai_settings()
    return JSONResponse(cfg)

@app.post("/api/settings/ai-provider")
async def api_save_ai_provider(
    payload: AIProviderConfigPayload,
    authenticated: bool = Depends(auth_required)
):
    saved = save_ai_settings(payload.model_dump())
    log_activity("settings_updated", f"Configured AI Provider: {payload.provider} ({payload.model_name})", "ai_config", "settings")
    return JSONResponse({"success": True, "settings": saved})

# -------------------------------------------------------------------------
# Privacy & Workspace Erasure REST APIs
# -------------------------------------------------------------------------

@app.post("/api/privacy/clear-research")
async def api_clear_research(authenticated: bool = Depends(auth_required)):
    count = clear_research_cache()
    return JSONResponse({"success": True, "cleared_records": count})


/**
 * Famous Media Technologies — Executive Discord AI Business Assistant
 * Frontend Controller & Real-Time Intelligence Engine
 */

// Global State
let currentView = 'overview';
let activeFollowUpTab = 'today';
let cachedLeads = [];
let cachedServers = [];
let selectedGuildId = null;
let cachedDiscordConfig = null;
let currentFollowUpsData = { today: [], overdue: [], upcoming: [], completed: [] };

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  checkUrlParamsForDiscordAlerts();
  loadDiscordStatus();
  loadDiscordAppConfig();
  loadBotStatus();
  loadOverviewMetrics();
  loadLeads();
  loadFollowUps();
  loadBusinessSettings();
  loadAISettings();
  loadChatHistory();
}

// ==========================================================================
// VIEW ROUTER
// ==========================================================================

function switchView(viewName) {
  currentView = viewName;

  // Update Nav Buttons
  document.querySelectorAll('.sidebar-nav-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  const activeBtn = document.getElementById(`nav-${viewName}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Update Panels
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.style.display = 'none';
  });
  const targetPanel = document.getElementById(`view-${viewName}`);
  if (targetPanel) targetPanel.style.display = 'block';

  // Update Appbar Title
  const titles = {
    overview: 'Executive Overview',
    discord: 'Discord OAuth2 & Bot Connections',
    servers: 'Server & Channel Management',
    research: 'AI Research & Discussion Scanner',
    workspace: 'Conversation Workspace (11 Stages)',
    messages: 'AI Message Writer',
    followups: 'Smart Follow-Up System',
    coach: 'AI Conversation Coach',
    chat: 'AI Command Center',
    business_settings: 'Business Profile & Pricing Settings',
    ai_settings: 'AI Provider Configuration',
    privacy: 'Privacy, Permissions & Security'
  };
  const titleElem = document.getElementById('viewHeaderTitle');
  if (titleElem) titleElem.textContent = titles[viewName] || 'Executive Dashboard';

  // Trigger view-specific data refreshes
  if (viewName === 'overview') loadOverviewMetrics();
  if (viewName === 'servers') {
    loadUserGuilds();
    loadBotServers();
  }
  if (viewName === 'workspace') loadLeads();
  if (viewName === 'followups') loadFollowUps();
  if (viewName === 'coach') populateCoachLeadSelect();
  if (viewName === 'research') executeMessageResearch();
}

// ==========================================================================
// 1. OVERVIEW DASHBOARD
// ==========================================================================

async function loadOverviewMetrics() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const stats = await res.json();

    const leadsRes = await fetch('/api/leads');
    const leads = leadsRes.ok ? await leadsRes.json() : [];
    cachedLeads = leads;

    const totalLeads = leads.length;
    const activeConversations = leads.filter(l => ['Conversation Started', 'Interested', 'Needs More Information', 'Price Discussed', 'Follow-up Due'].includes(l.stage || l.status)).length;
    const interested = leads.filter(l => (l.stage || l.status) === 'Interested').length;
    const converted = leads.filter(l => (l.stage || l.status) === 'Converted Customer').length;

    // Follow-ups due
    const fuRes = await fetch('/api/follow-ups/detailed');
    const fuData = fuRes.ok ? await fuRes.json() : { today: [], overdue: [] };
    const dueCount = (fuData.today?.length || 0) + (fuData.overdue?.length || 0);

    setText('dashTotalLeads', totalLeads);
    setText('dashActiveConversations', activeConversations);
    setText('dashInterestedLeads', interested);
    setText('dashFollowUpsDue', dueCount);
    setText('dashConvertedCustomers', converted);
    setText('badgeLeadsCount', totalLeads);

    const fuBadge = document.getElementById('badgeFollowUpDue');
    if (fuBadge) {
      if (dueCount > 0) {
        fuBadge.textContent = `${dueCount} Due`;
        fuBadge.style.display = 'inline-flex';
      } else {
        fuBadge.style.display = 'none';
      }
    }

    renderOverviewLeads(leads.slice(0, 5));
  } catch (err) {
    console.error('Error loading overview metrics:', err);
  }
}

function renderOverviewLeads(leads) {
  const tbody = document.getElementById('overviewLeadsTableBody');
  if (!tbody) return;

  if (!leads || leads.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No contacts saved yet. Search server discussions or add a new contact to start.</td></tr>`;
    return;
  }

  tbody.innerHTML = leads.map(l => {
    const stage = l.stage || l.status || 'New Contact';
    const isDiscord = (l.source_data_origin === 'discord_received');
    const dueText = l.follow_up_due_at ? l.follow_up_due_at.substring(0, 10) : 'None';
    return `
      <tr>
        <td>
          <div style="font-weight: 600; color: #fff;">${escapeHtml(l.contact_name || l.contact_handle || 'Unknown')}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(l.business_name || l.community_name || 'Direct')}</div>
        </td>
        <td>${getStagePillHtml(stage)}</td>
        <td>${escapeHtml(l.service_interested || l.category || 'IPTV Subscriptions')}</td>
        <td>
          <span class="origin-badge ${isDiscord ? 'origin-discord' : 'origin-manual'}">${isDiscord ? 'Discord Msg' : 'Manual'}</span>
        </td>
        <td style="font-size: 0.78rem;">${dueText}</td>
        <td>
          <button onclick="openCoachForLead(${l.id})" class="btn btn-outline-blue btn-sm" title="Open AI Coach">Coach</button>
        </td>
      </tr>
    `;
  }).join('');
}

// ==========================================================================
// 2. DISCORD CONNECTIONS
// ==========================================================================

async function loadDiscordStatus() {
  try {
    const res = await fetch('/api/auth/discord/status');
    if (!res.ok) return;
    const data = await res.json();

    const badge = document.getElementById('badgeDiscordStatus');
    const userCard = document.getElementById('discordUserCardContent');
    const userBadge = document.getElementById('discordUserStatusBadge');

    if (data.is_connected && data.user) {
      if (badge) {
        badge.textContent = 'Linked';
        badge.className = 'status-badge badge-live';
      }
      if (userBadge) {
        userBadge.textContent = 'Connected (OAuth2)';
        userBadge.className = 'status-badge badge-live';
      }

      // Update sidebar
      if (data.user.avatar_url) {
        const av = document.getElementById('sidebarAvatar');
        if (av) av.innerHTML = `<img src="${data.user.avatar_url}" alt="Avatar">`;
      }
      setText('sidebarUsername', data.user.global_name || data.user.username);

      if (userCard) {
        userCard.innerHTML = `
          <div style="display: flex; align-items: center; gap: 1rem; padding: 1rem; background: var(--bg-deep); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="width: 48px; height: 48px; border-radius: 50%; overflow: hidden; background: var(--blue-dim); border: 2px solid var(--border-blue);">
              <img src="${data.user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'}" alt="Avatar" style="width: 100%; height: 100%; object-fit: cover;">
            </div>
            <div style="flex: 1;">
              <div style="font-size: 0.95rem; font-weight: 700; color: #fff;">${escapeHtml(data.user.global_name || data.user.username)}</div>
              <div style="font-size: 0.75rem; color: var(--blue-bright);">@${escapeHtml(data.user.username)}</div>
              <div style="font-size: 0.68rem; color: var(--text-muted); margin-top: 0.2rem;">ID: <code>${escapeHtml(data.user.discord_id || data.user.id)}</code> • Scopes: <code>${escapeHtml(data.user.scope || 'identify guilds')}</code></div>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.75rem; color: var(--emerald-light);">✓ Official OAuth2 token verified</span>
            <button onclick="disconnectDiscordUser()" class="btn btn-danger btn-sm">Disconnect Account</button>
          </div>
        `;
      }
    } else {
      if (badge) {
        badge.textContent = data.oauth_configured ? 'Ready' : 'Setup Required';
        badge.className = data.oauth_configured ? 'status-badge' : 'status-badge badge-due';
      }
      if (userBadge) {
        userBadge.textContent = data.oauth_configured ? 'Ready to Connect' : 'Configuration Required';
        userBadge.className = data.oauth_configured ? 'status-badge' : 'status-badge badge-due';
      }

      if (userCard) {
        if (!data.oauth_configured) {
          userCard.innerHTML = `
            <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: var(--radius-sm); padding: 0.85rem 1rem;">
              <div style="font-size: 0.82rem; font-weight: 700; color: #fde68a; margin-bottom: 0.3rem;">Application Credentials Required</div>
              <p style="font-size: 0.78rem; color: #fef3c7; line-height: 1.45; margin-bottom: 0;">
                Discord requires your official Developer Application Client ID and Secret before signing in. Enter your credentials in the section below.
              </p>
            </div>
            <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
              <button onclick="scrollToDiscordConfig()" class="btn btn-primary btn-sm">
                <span>Configure Discord Credentials</span>
              </button>
              <button onclick="demoConnectDiscord()" class="btn btn-secondary btn-sm">
                <span>Instant Offline Demo Connect</span>
              </button>
            </div>
          `;
        } else {
          userCard.innerHTML = `
            <p style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.45;">
              Discord Developer Application verified (Client ID: <code>${escapeHtml(data.masked_client_id || 'Configured')}</code>). Click below to authorize your account via official OAuth2.
            </p>
            <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
              <a href="/api/auth/discord/login" class="btn btn-primary btn-sm" style="display: inline-flex; align-items: center; gap: 0.4rem;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19.27 5.33C17.94 4.71 16.5 4.26 15 4a.09.09 0 0 0-.07.03c-.18.33-.39.76-.53 1.09a16.09 16.09 0 0 0-4.8 0c-.14-.34-.35-.76-.54-1.09-.01-.02-.04-.03-.07-.03-1.5.26-2.93.71-4.27 1.33-.01 0-.02.01-.03.02-2.72 4.07-3.47 8.03-3.1 11.95 0 .02.01.04.03.05 1.8 1.32 3.53 2.12 5.24 2.65.03.01.06 0 .07-.02.4-.55.76-1.13 1.07-1.74.02-.04 0-.08-.04-.09-.57-.22-1.11-.48-1.64-.78-.04-.02-.04-.08-.01-.11.11-.08.22-.17.33-.25.02-.02.05-.02.07-.01 3.44 1.57 7.15 1.57 10.55 0 .02-.01.05-.01.07.01.11.09.22.17.33.26.04.03.04.09-.01.11-.52.31-1.07.56-1.64.78-.04.01-.05.06-.04.09.32.61.68 1.19 1.07 1.74.03.01.06.02.09.01 1.72-.53 3.45-1.33 5.25-2.65.02-.01.03-.03.03-.05.44-4.53-.73-8.46-3.1-11.95-.01-.01-.02-.02-.04-.02zM8.52 14.91c-1.03 0-1.89-.95-1.89-2.12s.84-2.12 1.89-2.12c1.06 0 1.9.96 1.89 2.12 0 1.17-.84 2.12-1.89 2.12zm6.97 0c-1.03 0-1.89-.95-1.89-2.12s.84-2.12 1.89-2.12c1.06 0 1.9.96 1.89 2.12 0 1.17-.83 2.12-1.89 2.12z"/></svg>
                <span>Sign in with Discord</span>
              </a>
              <button onclick="demoConnectDiscord()" class="btn btn-secondary btn-sm">
                <span>Instant Offline Demo Connect</span>
              </button>
            </div>
          `;
        }
      }
    }
  } catch (err) {
    console.error('Error loading Discord status:', err);
  }
}

async function loadBotStatus() {
  try {
    const res = await fetch('/api/bot/status');
    if (!res.ok) return;
    const bot = await res.json();

    const botCard = document.getElementById('discordBotCardContent');
    const botBadge = document.getElementById('discordBotStatusBadge');

    if (bot.is_connected) {
      if (botBadge) {
        botBadge.textContent = `Online (${bot.latency_ms}ms)`;
        botBadge.className = 'status-badge badge-live';
      }
      setText('badgeServersCount', bot.guild_count || 0);

      if (botCard) {
        botCard.innerHTML = `
          <div style="display: flex; flex-direction: column; gap: 0.75rem; padding: 1rem; background: var(--bg-deep); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted); font-size: 0.78rem;">Bot Username:</span>
              <strong style="color: #fff;">${escapeHtml(bot.bot_username)}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted); font-size: 0.78rem;">Bot User ID:</span>
              <code>${escapeHtml(bot.bot_id)}</code>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted); font-size: 0.78rem;">Gateway Latency:</span>
              <span style="color: var(--emerald-light); font-weight: 600;">${bot.latency_ms} ms</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted); font-size: 0.78rem;">Connected Servers:</span>
              <span style="color: var(--blue-bright); font-weight: 600;">${bot.guild_count} servers</span>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <button onclick="openInviteBotDialog()" class="btn btn-primary btn-sm">Add Bot to Another Server</button>
            <button onclick="disconnectBotGateway()" class="btn btn-danger btn-sm">Stop Bot</button>
          </div>
        `;
      }
    } else {
      if (botBadge) {
        botBadge.textContent = 'Gateway Offline';
        botBadge.className = 'status-badge';
      }
      if (botCard) {
        botCard.innerHTML = `
          <p style="font-size: 0.82rem; color: var(--text-secondary);">
            Connect your official Discord bot using your Bot Token from the Discord Developer Portal.
          </p>
          <div class="form-group" style="margin-bottom: 0.75rem;">
            <input type="password" id="inputBotToken" class="input" placeholder="Paste Discord Bot Token...">
          </div>
          <div style="display: flex; justify-content: space-between;">
            <button onclick="saveBotToken()" class="btn btn-primary btn-sm">Save & Connect Bot</button>
            <button onclick="openInviteBotDialog()" class="btn btn-secondary btn-sm">Generate Invite URL</button>
          </div>
        `;
      }
    }
  } catch (err) {
    console.error('Error loading Bot status:', err);
  }
}

async function saveBotToken() {
  const token = document.getElementById('inputBotToken')?.value.trim();
  if (!token) return alert('Please enter a Discord Bot Token.');
  try {
    const res = await fetch('/api/bot/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    const data = await res.json();
    if (res.ok) {
      alert('Bot token saved and connection initiated!');
      loadBotStatus();
      loadBotServers();
    } else {
      alert(data.detail || 'Failed to save bot token');
    }
  } catch (err) {
    alert('Error connecting bot: ' + err.message);
  }
}

async function disconnectBotGateway() {
  if (!confirm('Disconnect the official Discord bot gateway?')) return;
  await fetch('/api/bot/disconnect', { method: 'POST' });
  loadBotStatus();
  loadBotServers();
}

async function disconnectDiscordUser() {
  if (!confirm('Disconnect your Discord account and revoke session?')) return;
  await fetch('/api/auth/discord/disconnect', { method: 'POST' });
  loadDiscordStatus();
}

async function demoConnectDiscord() {
  await fetch('/api/auth/discord/demo-connect', { method: 'POST' });
  loadDiscordStatus();
  switchView('overview');
}

function checkUrlParamsForDiscordAlerts() {
  const urlParams = new URLSearchParams(window.location.search);
  const hash = window.location.hash;

  const discordError = urlParams.get('discord_error');
  const discordConnected = urlParams.get('discord_connected');

  if (discordError) {
    switchView('discord');
    const errBanner = document.getElementById('discordErrorBanner');
    const errText = document.getElementById('discordErrorText');
    if (errBanner && errText) {
      errText.textContent = decodeURIComponent(discordError);
      errBanner.style.display = 'block';
    }
  } else if (discordConnected) {
    switchView('discord');
    const succBanner = document.getElementById('discordSuccessBanner');
    if (succBanner) {
      succBanner.style.display = 'block';
    }
  } else if (hash === '#discord') {
    switchView('discord');
  }
}

function dismissDiscordAlert(elementId) {
  const el = document.getElementById(elementId);
  if (el) el.style.display = 'none';
  if (window.history && window.history.replaceState) {
    const cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + window.location.hash;
    window.history.replaceState({}, document.title, cleanUrl);
  }
}

function scrollToDiscordConfig() {
  switchView('discord');
  const el = document.getElementById('discordAppConfigCard');
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' });
    const idInput = document.getElementById('cfgDiscordClientId');
    if (idInput) idInput.focus();
  }
}

function togglePasswordVisibility(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.type = input.type === 'password' ? 'text' : 'password';
}

async function copyRedirectUri() {
  const input = document.getElementById('displayRedirectUriInput');
  if (!input) return;
  try {
    await navigator.clipboard.writeText(input.value);
    const btnText = document.getElementById('copyRedirectBtnText');
    if (btnText) {
      const orig = btnText.textContent;
      btnText.textContent = 'Copied!';
      setTimeout(() => { btnText.textContent = orig; }, 2000);
    }
  } catch (err) {
    input.select();
    document.execCommand('copy');
    const btnText = document.getElementById('copyRedirectBtnText');
    if (btnText) {
      btnText.textContent = 'Copied!';
      setTimeout(() => { btnText.textContent = 'Copy URL'; }, 2000);
    }
  }
}

async function loadDiscordAppConfig() {
  try {
    const res = await fetch('/api/auth/discord/config');
    if (!res.ok) return;
    const data = await res.json();
    cachedDiscordConfig = data;

    const idInput = document.getElementById('cfgDiscordClientId');
    const secretInput = document.getElementById('cfgDiscordClientSecret');
    const botTokenInput = document.getElementById('cfgDiscordBotToken');
    const redirectInput = document.getElementById('displayRedirectUriInput');
    const badge = document.getElementById('discordConfigBadge');
    const statusText = document.getElementById('discordConfigStatusText');

    if (idInput && data.client_id) {
      idInput.value = data.client_id;
    }
    if (secretInput && data.has_client_secret) {
      secretInput.placeholder = `Configured (${data.client_secret_masked})`;
    }
    if (botTokenInput && data.has_bot_token) {
      botTokenInput.placeholder = `Configured (${data.bot_token_masked})`;
    }
    if (redirectInput) {
      redirectInput.value = data.suggested_redirect_uri || data.redirect_uri || 'http://127.0.0.1:8080/api/auth/discord/callback';
    }

    if (badge) {
      if (data.is_configured) {
        badge.textContent = 'Configured & Verified';
        badge.className = 'status-badge badge-live';
      } else {
        badge.textContent = 'Setup Required';
        badge.className = 'status-badge badge-due';
      }
    }

    if (statusText) {
      statusText.textContent = data.status_message || (data.is_configured ? 'Official Discord credentials verified.' : 'Enter credentials from Discord Developer Portal.');
      statusText.style.color = data.is_configured ? 'var(--emerald-light)' : 'var(--amber-primary)';
    }
  } catch (err) {
    console.error('Error loading Discord App config:', err);
  }
}

async function saveDiscordAppConfig() {
  const idInput = document.getElementById('cfgDiscordClientId');
  const secretInput = document.getElementById('cfgDiscordClientSecret');
  const tokenInput = document.getElementById('cfgDiscordBotToken');
  const redirectInput = document.getElementById('displayRedirectUriInput');
  const feedback = document.getElementById('discordConfigFeedback');
  const saveBtn = document.getElementById('btnSaveDiscordConfig');

  const clientId = idInput ? idInput.value.trim() : '';
  const clientSecret = secretInput ? secretInput.value.trim() : '';
  const botToken = tokenInput ? tokenInput.value.trim() : '';
  const redirectUri = redirectInput ? redirectInput.value.trim() : '';

  if (feedback) {
    feedback.style.display = 'none';
  }

  // Pre-validate client ID format on client side for immediate feedback
  if (!clientId) {
    showDiscordConfigFeedback('Please enter your Discord Application Client ID.', 'error');
    if (idInput) idInput.focus();
    return;
  }
  if (!/^\d{17,20}$/.test(clientId)) {
    showDiscordConfigFeedback('Invalid Client ID. Discord Application Client ID must be a 17-20 digit numeric snowflake from Discord Developer Portal (General Information > Application ID).', 'error');
    if (idInput) idInput.focus();
    return;
  }

  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving & Verifying...';
  }

  try {
    const res = await fetch('/api/auth/discord/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: clientId,
        client_secret: clientSecret,
        bot_token: botToken,
        redirect_uri: redirectUri
      })
    });
    const data = await res.json();

    if (res.ok) {
      showDiscordConfigFeedback(data.message || 'Credentials saved successfully!', 'success');
      if (secretInput && clientSecret) {
        secretInput.value = '';
      }
      if (tokenInput && botToken) {
        tokenInput.value = '';
      }
      await loadDiscordAppConfig();
      await loadDiscordStatus();
      await loadBotStatus();
    } else {
      showDiscordConfigFeedback(data.detail || 'Failed to save Discord credentials.', 'error');
    }
  } catch (err) {
    showDiscordConfigFeedback('Network error saving credentials: ' + err.message, 'error');
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save Discord Credentials';
    }
  }
}

function showDiscordConfigFeedback(msg, type) {
  const el = document.getElementById('discordConfigFeedback');
  if (!el) return;
  el.textContent = msg;
  el.style.display = 'block';
  if (type === 'success') {
    el.style.background = 'rgba(16, 185, 129, 0.12)';
    el.style.border = '1px solid rgba(16, 185, 129, 0.35)';
    el.style.color = '#6ee7b7';
  } else {
    el.style.background = 'rgba(239, 68, 68, 0.12)';
    el.style.border = '1px solid rgba(239, 68, 68, 0.35)';
    el.style.color = '#fca5a5';
  }
}

// Server Management State
let cachedUserGuilds = [];
let activeServerTab = 'user';
let botVerifyPollTimer = null;

function switchServerTab(tab) {
  activeServerTab = tab;
  const userPanel = document.getElementById('panelUserServers');
  const botPanel = document.getElementById('panelBotServers');
  const userBtn = document.getElementById('tabBtnUserServers');
  const botBtn = document.getElementById('tabBtnBotServers');

  if (tab === 'user') {
    if (userPanel) userPanel.style.display = 'block';
    if (botPanel) botPanel.style.display = 'none';
    if (userBtn) { userBtn.className = 'btn btn-primary btn-sm'; }
    if (botBtn) { botBtn.className = 'btn btn-secondary btn-sm'; }
    loadUserGuilds();
  } else {
    if (userPanel) userPanel.style.display = 'none';
    if (botPanel) botPanel.style.display = 'block';
    if (userBtn) { userBtn.className = 'btn btn-secondary btn-sm'; }
    if (botBtn) { botBtn.className = 'btn btn-primary btn-sm'; }
    loadBotServers();
  }
}

async function loadUserGuilds() {
  const tbody = document.getElementById('userServersTableBody');
  try {
    const res = await fetch('/api/user/guilds');
    if (!res.ok) return;
    const data = await res.json();
    cachedUserGuilds = data.guilds || [];

    setText('badgeUserServersCount', `${cachedUserGuilds.length}`);
    setText('userGuildsTabCount', cachedUserGuilds.length);

    if (!tbody) return;

    if (!data.is_authenticated) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2.5rem 1rem;">
            <div style="font-size: 0.95rem; color: #fff; font-weight: 700; margin-bottom: 0.35rem;">Discord Account Not Linked</div>
            <p style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 1rem;">
              Connect your personal Discord account securely via official OAuth2 to view your servers.
            </p>
            <a href="/api/auth/discord/login" class="btn btn-primary btn-sm">Sign in with Discord</a>
          </td>
        </tr>
      `;
      return;
    }

    if (cachedUserGuilds.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2.5rem 1rem;">
            <div style="font-size: 0.95rem; color: #fff; font-weight: 700; margin-bottom: 0.35rem;">No Discord Servers Found</div>
            <p style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 1rem;">
              Your connected Discord account currently belongs to 0 servers, or OAuth2 guilds scope needs refreshing.
            </p>
            <button onclick="refreshUserGuilds()" class="btn btn-secondary btn-sm">Refresh Server List</button>
          </td>
        </tr>
      `;
      return;
    }

    renderUserGuildsTable(cachedUserGuilds);
  } catch (err) {
    console.error('Error loading user guilds:', err);
    if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color: #fca5a5; text-align: center; padding: 1.5rem;">Error loading servers: ${err.message}</td></tr>`;
  }
}

function renderUserGuildsTable(guilds) {
  const tbody = document.getElementById('userServersTableBody');
  if (!tbody) return;

  tbody.innerHTML = guilds.map(g => {
    const isBotConnected = Boolean(g.bot_connected);
    const canManage = Boolean(g.can_manage);
    const iconUrl = g.icon_url || 'https://cdn.discordapp.com/embed/avatars/0.png';

    let roleBadgeClass = 'status-badge';
    if (g.role_badge === 'Server Owner') roleBadgeClass = 'status-badge badge-due';
    else if (g.role_badge === 'Administrator') roleBadgeClass = 'status-badge badge-live';

    let botBadgeHtml = isBotConnected
      ? `<span class="status-badge badge-live">● Bot Active</span>`
      : `<span class="status-badge" style="color: var(--text-muted);">○ Not Installed</span>`;

    let actionBtnHtml = '';
    if (isBotConnected) {
      actionBtnHtml = `<button onclick="selectServerToManage('${g.guild_id || g.id}', '${escapeHtml(g.name)}')" class="btn btn-outline-blue btn-sm">Inspect Channels</button>`;
    } else if (canManage) {
      actionBtnHtml = `<button onclick="openAddBotForGuild('${g.guild_id || g.id}', '${escapeHtml(g.name)}')" class="btn btn-primary btn-sm">Add Bot to Server</button>`;
    } else {
      actionBtnHtml = `<span style="font-size: 0.75rem; color: var(--text-muted);" title="Administrator or Manage Server permission required to install bots">Requires Admin</span>`;
    }

    return `
      <tr>
        <td>
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="${iconUrl}" alt="icon" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; background: var(--bg-deep); border: 1px solid var(--border-subtle);">
            <div>
              <div style="font-weight: 600; color: #fff;">${escapeHtml(g.name)}</div>
              ${g.owner ? '<span style="font-size: 0.68rem; color: var(--amber-primary); font-weight: 600;">👑 Owner</span>' : ''}
            </div>
          </div>
        </td>
        <td><code>${escapeHtml(g.guild_id || g.id)}</code></td>
        <td><span class="${roleBadgeClass}">${escapeHtml(g.role_badge || 'Member')}</span></td>
        <td>${botBadgeHtml}</td>
        <td>${actionBtnHtml}</td>
      </tr>
    `;
  }).join('');
}

function filterUserGuildsTable() {
  const query = (document.getElementById('filterUserServersInput')?.value || '').toLowerCase().trim();
  if (!query) {
    renderUserGuildsTable(cachedUserGuilds);
    return;
  }
  const filtered = cachedUserGuilds.filter(g =>
    (g.name || '').toLowerCase().includes(query) ||
    (g.guild_id || g.id || '').includes(query) ||
    (g.role_badge || '').toLowerCase().includes(query)
  );
  renderUserGuildsTable(filtered);
}

async function refreshUserGuilds() {
  const btn = document.getElementById('btnRefreshUserGuilds');
  const txt = document.getElementById('btnRefreshUserGuildsText');
  if (btn) btn.disabled = true;
  if (txt) txt.textContent = 'Refreshing...';

  try {
    const res = await fetch('/api/user/guilds/refresh', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      await loadUserGuilds();
      await loadBotServers();
    } else {
      alert(data.detail || 'Could not refresh server list. Please verify your Discord login.');
    }
  } catch (err) {
    alert('Network error refreshing servers: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (txt) txt.textContent = 'Refresh Server List';
  }
}

async function openAddBotForGuild(guildId, guildName) {
  try {
    const res = await fetch(`/api/bot/invite-url?guild_id=${guildId || ''}`);
    const data = await res.json();
    if (!data.invite_url) {
      alert('Discord Application Client ID is not configured yet. Go to Discord Connections to save your credentials.');
      switchView('discord');
      return;
    }

    // Open Discord official authorization in new window
    window.open(data.invite_url, '_blank', 'width=580,height=800');

    // Show verification modal
    const modal = document.getElementById('botVerifyModal');
    const msg = document.getElementById('botVerifyModalMessage');
    const status = document.getElementById('botVerifyModalStatus');
    if (modal) modal.style.display = 'flex';
    if (msg) msg.innerHTML = `Complete the Discord authorization screen to add the bot to <strong>${escapeHtml(guildName)}</strong>.`;
    if (status) status.innerHTML = `Checking bot connection for <strong>${escapeHtml(guildName)}</strong>...`;

    // Start auto-polling verification every 3 seconds
    if (botVerifyPollTimer) clearInterval(botVerifyPollTimer);
    let attempts = 0;
    botVerifyPollTimer = setInterval(async () => {
      attempts++;
      try {
        const checkRes = await fetch(`/api/bot/check-server/${guildId}`);
        const checkData = await checkRes.json();
        if (checkData.is_connected) {
          clearInterval(botVerifyPollTimer);
          if (status) {
            status.innerHTML = `<span style="color: var(--emerald-light); font-weight: 700;">✓ Bot successfully joined ${escapeHtml(guildName)}!</span>`;
          }
          await loadUserGuilds();
          await loadBotServers();
          setTimeout(() => {
            closeBotVerifyModal();
            selectServerToManage(guildId, guildName);
          }, 1800);
        } else if (attempts >= 20) {
          clearInterval(botVerifyPollTimer);
          if (status) {
            status.innerHTML = `<span style="color: var(--amber-primary);">Did not detect bot within 60s. Click "Refresh Server List" once authorized.</span>`;
          }
        }
      } catch (e) {
        // Ignore polling errors
      }
    }, 3000);
  } catch (err) {
    alert('Error generating bot authorization link: ' + err.message);
  }
}

function closeBotVerifyModal() {
  const modal = document.getElementById('botVerifyModal');
  if (modal) modal.style.display = 'none';
  if (botVerifyPollTimer) clearInterval(botVerifyPollTimer);
}

function openInviteBotDialog() {
  const cid = (cachedDiscordConfig?.client_id || document.getElementById('cfgDiscordClientId')?.value || '').trim();
  if (cid && /^\d{17,20}$/.test(cid)) {
    const inviteUrl = `https://discord.com/oauth2/authorize?client_id=${cid}&permissions=2147551296&scope=bot%20applications.commands`;
    window.open(inviteUrl, '_blank', 'width=580,height=800');
    return;
  }
  const manualCid = prompt('Enter your Discord Application Client ID (17-20 digits):');
  if (!manualCid) return;
  if (!/^\d{17,20}$/.test(manualCid.trim())) {
    alert('Invalid Discord Application Client ID. It must be a 17-20 digit number from the Discord Developer Portal.');
    return;
  }
  const inviteUrl = `https://discord.com/oauth2/authorize?client_id=${manualCid.trim()}&permissions=2147551296&scope=bot%20applications.commands`;
  window.open(inviteUrl, '_blank', 'width=580,height=800');
}

// ==========================================================================
// 3. SERVER MANAGEMENT & CHANNELS
// ==========================================================================

async function loadBotServers() {
  try {
    const res = await fetch('/api/bot/servers');
    if (!res.ok) return;
    const data = await res.json();
    cachedServers = data.guilds || [];
    setText('badgeServersCount', cachedServers.length);
    setText('badgeBotServersCount', `${cachedServers.length}`);

    const tbody = document.getElementById('botServersTableBody');
    if (!tbody) return;

    if (cachedServers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">The bot is not yet present in any servers. In "My Discord Servers", click "Add Bot to Server" on any community where you have permissions.</td></tr>`;
      return;
    }

    tbody.innerHTML = cachedServers.map(s => {
      const iconUrl = s.icon_url || 'https://cdn.discordapp.com/embed/avatars/0.png';
      return `
        <tr>
          <td>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <img src="${iconUrl}" alt="icon" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; background: var(--bg-deep); border: 1px solid var(--border-subtle);">
              <span style="font-weight: 600; color: #fff;">${escapeHtml(s.name)}</span>
            </div>
          </td>
          <td><code>${escapeHtml(s.guild_id || s.id)}</code></td>
          <td>${(s.member_count || 0).toLocaleString()}</td>
          <td><span class="status-badge badge-live">Authorized & Active</span></td>
          <td>
            <button onclick="selectServerToManage('${s.guild_id || s.id}', '${escapeHtml(s.name)}')" class="btn btn-outline-blue btn-sm">Inspect Channels</button>
            <button onclick="removeServer('${s.guild_id || s.id}')" class="btn btn-danger btn-sm" style="margin-left: 0.35rem;">Disconnect</button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading bot servers:', err);
  }
}

async function selectServerToManage(guildId, serverName) {
  selectedGuildId = guildId;
  const panel = document.getElementById('serverChannelsPanel');
  if (panel) {
    panel.style.display = 'block';
    panel.scrollIntoView({ behavior: 'smooth' });
  }
  setText('selectedServerTitle', `${serverName} — Channel Permissions`);

  const tbody = document.getElementById('serverChannelsTableBody');
  if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Fetching channels...</td></tr>`;

  try {
    const res = await fetch(`/api/bot/servers/${guildId}/channels`);
    const data = await res.json();
    const channels = data.channels || [];

    if (channels.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No accessible text channels discovered. Ensure the bot has 'View Channels' permission.</td></tr>`;
      return;
    }

    tbody.innerHTML = channels.map(ch => {
      const isMon = Boolean(ch.is_monitored);
      return `
        <tr>
          <td style="font-weight: 600; color: #fff;">#${escapeHtml(ch.name)}</td>
          <td><span class="status-badge">${escapeHtml(ch.type || 'text')}</span></td>
          <td style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(ch.topic ? ch.topic.substring(0, 70) + '...' : 'No topic')}</td>
          <td>
            <label style="display: flex; align-items: center; gap: 0.4rem; cursor: pointer;">
              <input type="checkbox" ${isMon ? 'checked' : ''} onchange="toggleChannelMonitor('${guildId}', '${ch.id || ch.channel_id}', this.checked)">
              <span style="font-size: 0.78rem; color: ${isMon ? 'var(--blue-bright)' : 'var(--text-muted)'};">${isMon ? 'Allowed to Read' : 'Restricted'}</span>
            </label>
          </td>
          <td>
            <button onclick="fetchChannelMessages('${guildId}', '${ch.id || ch.channel_id}', '${escapeHtml(ch.name)}')" class="btn btn-primary btn-sm">
              Read Discussions
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="color: #fca5a5;">Error loading channels: ${err.message}</td></tr>`;
  }
}

async function toggleChannelMonitor(guildId, channelId, isMonitored) {
  try {
    await fetch(`/api/bot/servers/${guildId}/channels/${channelId}/monitor`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_monitored: isMonitored })
    });
  } catch (err) {
    alert('Failed to update channel permission: ' + err.message);
  }
}

async function fetchChannelMessages(guildId, channelId, channelName) {
  const viewer = document.getElementById('channelDiscussionsViewer');
  const title = document.getElementById('channelViewerTitle');
  const sub = document.getElementById('channelViewerSubtitle');
  const list = document.getElementById('channelMessagesList');

  if (viewer) {
    viewer.style.display = 'block';
    viewer.scrollIntoView({ behavior: 'smooth' });
  }
  if (title) title.textContent = `#${channelName} Discussions`;
  if (sub) sub.textContent = 'Connecting to channel and reading recent messages...';
  if (list) list.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">Fetching messages from Discord Gateway...</div>`;

  try {
    const res = await fetch(`/api/bot/servers/${guildId}/channels/${channelId}/fetch-messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ limit: 50 })
    });
    const data = await res.json();
    if (!res.ok) {
      if (list) list.innerHTML = `<div style="color: #fca5a5; padding: 1.5rem; text-align: center;">${escapeHtml(data.detail || data.error || 'Failed to read channel messages.')}</div>`;
      return;
    }

    const messages = data.messages || [];
    if (sub) {
      let subText = `Retrieved ${messages.length} messages (${data.buying_signals_found} buying signals detected).`;
      if (data.warning) subText += `<br><span style="color: var(--amber-primary); font-size: 0.75rem;">⚠ ${escapeHtml(data.warning)}</span>`;
      sub.innerHTML = subText;
    }

    if (messages.length === 0) {
      if (list) list.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">No recent human messages found in #${escapeHtml(channelName)}.</div>`;
      return;
    }

    if (list) {
      list.innerHTML = messages.map(m => {
        const timeFormatted = m.timestamp ? new Date(m.timestamp).toLocaleString() : '';
        const signalBadge = m.has_buying_signal
          ? `<span class="status-badge badge-due" style="font-size: 0.7rem; margin-left: 0.5rem;">Signal: ${escapeHtml(m.detected_service || 'IPTV Inquirer')}</span>`
          : '';

        return `
          <div style="background: var(--bg-deep); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.85rem; display: flex; flex-direction: column; gap: 0.4rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <img src="${m.author_avatar || 'https://cdn.discordapp.com/embed/avatars/0.png'}" style="width: 24px; height: 24px; border-radius: 50%; object-fit: cover;">
                <strong style="color: #fff; font-size: 0.82rem;">${escapeHtml(m.author_display_name || m.author_username)}</strong>
                <span style="font-size: 0.72rem; color: var(--blue-bright);">@${escapeHtml(m.author_username)}</span>
                ${signalBadge}
              </div>
              <span style="font-size: 0.72rem; color: var(--text-muted);">${timeFormatted}</span>
            </div>
            <div style="font-size: 0.82rem; color: var(--text-primary); line-height: 1.5; white-space: pre-wrap; margin-top: 0.2rem;">${escapeHtml(m.content)}</div>
            ${m.buying_signal_details ? `<div style="font-size: 0.75rem; color: var(--emerald-light);">💡 ${escapeHtml(m.buying_signal_details)}</div>` : ''}
            <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.4rem; padding-top: 0.4rem; border-top: 1px solid rgba(255,255,255,0.05);">
              <a href="${m.jump_url}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm" style="font-size: 0.72rem; padding: 0.2rem 0.5rem;">View on Discord ↗</a>
              <button onclick="saveMessageAsLead('${m.message_id}')" class="btn btn-primary btn-sm" style="font-size: 0.72rem; padding: 0.2rem 0.5rem;">Add to CRM Leads</button>
            </div>
          </div>
        `;
      }).join('');
    }
  } catch (err) {
    if (list) list.innerHTML = `<div style="color: #fca5a5; padding: 1.5rem; text-align: center;">Error reading messages: ${err.message}</div>`;
  }
}

function closeChannelDiscussionsViewer() {
  const viewer = document.getElementById('channelDiscussionsViewer');
  if (viewer) viewer.style.display = 'none';
}

async function saveMessageAsLead(messageId) {
  try {
    const res = await fetch(`/api/messages/${messageId}/save-lead`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes: 'Captured from Channel Discussion', follow_up_days: 2 })
    });
    const data = await res.json();
    if (res.ok) {
      alert('Lead successfully saved to CRM Workspace!');
      loadLeads();
    } else {
      alert(data.detail || 'Could not save lead.');
    }
  } catch (err) {
    alert('Error saving lead: ' + err.message);
  }
}

async function removeServer(guildId) {
  if (!confirm('Remove this server and its channel cache from your workspace?')) return;
  await fetch(`/api/bot/servers/${guildId}`, { method: 'DELETE' });
  await loadUserGuilds();
  await loadBotServers();
  document.getElementById('serverChannelsPanel').style.display = 'none';
}

async function submitPersonalDMIntake() {
  const contactName = document.getElementById('dmContactName')?.value.trim();
  const service = document.getElementById('dmServiceSelect')?.value;
  const snippet = document.getElementById('dmSnippetInput')?.value.trim();
  const notes = document.getElementById('dmNotesInput')?.value.trim();
  const btn = document.getElementById('btnSubmitPersonalDM');

  if (!contactName) return alert('Please enter contact name or Discord handle.');
  if (!snippet) return alert('Please paste the direct message or chat snippet.');

  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Analyzing with Famous Media AI...';
  }

  try {
    const res = await fetch('/api/conversation/personal-dm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_name: contactName,
        discord_username: contactName.startsWith('@') ? contactName : '',
        raw_conversation: snippet,
        target_service: service,
        notes: notes
      })
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || 'Failed to analyze conversation.');
      return;
    }

    const placeholder = document.getElementById('dmAnalysisPlaceholder');
    const content = document.getElementById('dmAnalysisContent');
    const summary = document.getElementById('dmSummaryText');
    const questions = document.getElementById('dmQuestionsList');
    const replies = document.getElementById('dmRepliesList');

    if (placeholder) placeholder.style.display = 'none';
    if (content) content.style.display = 'flex';
    if (summary) summary.innerHTML = `<strong>Summary:</strong> ${escapeHtml(data.analysis.summary)}`;
    if (questions) {
      const qList = (data.analysis.identified_questions || []).map(q => `• ${escapeHtml(q)}`).join('<br>');
      questions.innerHTML = `<strong>Identified Questions / Needs:</strong><br>${qList || 'No direct questions detected.'}`;
    }
    if (replies) {
      const repList = data.analysis.suggested_replies || [];
      replies.innerHTML = repList.map((r, idx) => `
        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
            <span style="font-size: 0.72rem; color: var(--blue-bright); font-weight: 700;">Option ${idx + 1}: ${escapeHtml(r.type || 'Tailored Reply')}</span>
            <button onclick="copyReplyText(this, \`${escapeJsString(r.text)}\`)" class="btn btn-secondary btn-sm" style="font-size: 0.72rem; padding: 0.2rem 0.5rem;">Copy Reply</button>
          </div>
          <div style="font-size: 0.78rem; color: var(--text-primary); line-height: 1.45; white-space: pre-wrap;">${escapeHtml(r.text)}</div>
        </div>
      `).join('');
    }

    loadLeads();
  } catch (err) {
    alert('Error processing DM: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Analyze DM & Generate 3 AI Replies';
    }
  }
}

function copyReplyText(btnElem, text) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btnElem.textContent;
    btnElem.textContent = 'Copied!';
    setTimeout(() => { btnElem.textContent = orig; }, 2000);
  });
}

function escapeJsString(str) {
  return (str || '')
    .replace(/\\/g, '\\\\')
    .replace(/`/g, '\\`')
    .replace(/\$/g, '\\$');
}

// ==========================================================================
// 4. AI RESEARCH CENTER
// ==========================================================================

async function executeMessageResearch() {
  const query = document.getElementById('researchSearchQuery')?.value.trim() || '';
  const service = document.getElementById('researchServiceFilter')?.value || 'All';
  const buyingOnly = document.getElementById('researchBuyingSignalsOnly')?.checked || false;

  const tbody = document.getElementById('researchResultsTableBody');
  if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Searching messages...</td></tr>`;

  try {
    const url = `/api/messages/search?query=${encodeURIComponent(query)}&service=${encodeURIComponent(service)}&buying_signals_only=${buyingOnly}`;
    const res = await fetch(url);
    const messages = await res.json();

    setText('researchResultsCount', `${messages.length} relevant discussions found`);

    if (!messages || messages.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No matching messages found. Ensure you have monitored channels selected in Server Management and clicked "Read Discussions".</td></tr>`;
      return;
    }

    tbody.innerHTML = messages.map(m => {
      const score = m.relevance_score || 0;
      const jumpUrl = m.jump_url || '#';
      const isSaved = Boolean(m.is_saved_to_contacts);

      return `
        <tr>
          <td>
            <div style="font-weight: 600; color: #fff;">${escapeHtml(m.author_display_name || m.author_username)}</div>
            <div style="font-size: 0.68rem; color: var(--text-muted);">@${escapeHtml(m.author_username)}</div>
          </td>
          <td>
            <div style="font-weight: 500;">#${escapeHtml(m.channel_name || 'chat')}</div>
            <div style="font-size: 0.68rem; color: var(--text-dim);">${escapeHtml(m.server_name || '')}</div>
          </td>
          <td style="max-width: 300px; font-size: 0.8rem; line-height: 1.4;">
            "${escapeHtml(m.content)}"
            <div style="margin-top: 0.25rem;">
              <a href="${jumpUrl}" target="_blank" style="color: var(--blue-bright); font-size: 0.7rem; text-decoration: none;">↗ View on Discord</a>
            </div>
          </td>
          <td>
            <div style="font-weight: 600; color: var(--blue-bright);">${escapeHtml(m.detected_service || 'General')}</div>
            <div style="font-size: 0.72rem; color: var(--text-secondary);">${escapeHtml(m.buying_signal_details || 'General inquiry')}</div>
          </td>
          <td>
            <span class="status-badge ${score >= 50 ? 'badge-live' : 'badge-blue'}">${score}% match</span>
          </td>
          <td>
            ${isSaved ? `
              <span class="status-badge" style="color: var(--emerald-light);">Saved</span>
            ` : `
              <button onclick="saveMessageToLead('${m.message_id}')" class="btn btn-primary btn-sm">Add to Contacts</button>
            `}
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="color: #fca5a5;">Error: ${err.message}</td></tr>`;
  }
}

async function saveMessageToLead(messageId) {
  try {
    const res = await fetch(`/api/messages/${messageId}/save-lead`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ follow_up_days: 2 })
    });
    const data = await res.json();
    if (res.ok) {
      alert('Prospect saved to Conversation Workspace with 2-day reminder scheduled!');
      executeMessageResearch();
      loadLeads();
      loadOverviewMetrics();
    } else {
      alert(data.detail || 'Could not save prospect');
    }
  } catch (err) {
    alert('Error saving contact: ' + err.message);
  }
}

async function scanDiscordInvite() {
  const code = document.getElementById('scanInviteInput')?.value.trim();
  if (!code) return alert('Please paste a Discord invite link or code.');

  try {
    const res = await fetch('/api/servers/inspect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ invite_code: code })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`Discovered: ${data.server.name} (${(data.server.approximate_member_count || 0).toLocaleString()} members)`);
      document.getElementById('scanInviteInput').value = '';
      loadOverviewMetrics();
    } else {
      alert(data.detail || 'Could not resolve server invite.');
    }
  } catch (err) {
    alert('Scan error: ' + err.message);
  }
}

// ==========================================================================
// 5. CONVERSATION WORKSPACE (11 STAGES CRM)
// ==========================================================================

async function loadLeads() {
  try {
    const res = await fetch('/api/leads');
    if (!res.ok) return;
    cachedLeads = await res.json();
    filterCrmTable();
  } catch (err) {
    console.error('Error loading leads:', err);
  }
}

function filterCrmTable() {
  const search = document.getElementById('crmSearchInput')?.value.toLowerCase().trim() || '';
  const stage = document.getElementById('crmStageFilter')?.value || 'All';
  const origin = document.getElementById('crmOriginFilter')?.value || 'All';

  let filtered = cachedLeads.filter(l => {
    const currentStage = l.stage || l.status || 'New Contact';
    if (stage !== 'All' && currentStage !== stage) return false;
    if (origin !== 'All' && l.source_data_origin !== origin) return false;
    if (search) {
      const matchText = `${l.contact_name} ${l.contact_handle} ${l.business_name} ${l.notes} ${l.service_interested}`.toLowerCase();
      if (!matchText.includes(search)) return false;
    }
    return true;
  });

  setText('crmContactsCount', `${filtered.length} of ${cachedLeads.length} contacts`);
  renderCrmTable(filtered);
}

function renderCrmTable(leads) {
  const tbody = document.getElementById('crmContactsTableBody');
  if (!tbody) return;

  if (leads.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No contacts match the selected filters.</td></tr>`;
    return;
  }

  tbody.innerHTML = leads.map(l => {
    const stage = l.stage || l.status || 'New Contact';
    const isDiscord = (l.source_data_origin === 'discord_received');
    const dueText = l.follow_up_due_at ? l.follow_up_due_at.substring(0, 10) : 'None';

    return `
      <tr>
        <td>
          <div style="font-weight: 700; color: #fff;">${escapeHtml(l.contact_name || l.contact_handle || 'Unknown')}</div>
          <div style="font-size: 0.72rem; color: var(--blue-bright);">@${escapeHtml(l.contact_handle || '')}</div>
          <div style="font-size: 0.68rem; color: var(--text-dim);">${escapeHtml(l.business_name || '')}</div>
        </td>
        <td>
          <select onchange="updateLeadStage(${l.id}, this.value)" class="select" style="padding: 0.25rem 0.5rem; font-size: 0.72rem;">
            ${renderStageOptions(stage)}
          </select>
        </td>
        <td><strong style="color: var(--text-secondary);">${escapeHtml(l.service_interested || l.category || 'Subscriptions')}</strong></td>
        <td>
          <span class="origin-badge ${isDiscord ? 'origin-discord' : 'origin-manual'}">${isDiscord ? 'Discord Received' : 'Manual Entered'}</span>
        </td>
        <td style="font-size: 0.75rem; max-width: 180px;">${escapeHtml(l.stated_interests || 'None recorded')}</td>
        <td style="font-size: 0.75rem; max-width: 180px; color: var(--blue-bright);">${escapeHtml(l.next_suggested_action || 'Draft message')}</td>
        <td style="font-size: 0.75rem;">
          <span class="status-badge ${l.follow_up_status === 'Scheduled' ? 'badge-due' : ''}">${escapeHtml(l.follow_up_status || 'None')} (${dueText})</span>
        </td>
        <td>
          <div style="display: flex; gap: 0.3rem;">
            <button onclick="openCoachForLead(${l.id})" class="btn btn-outline-blue btn-sm" title="AI Coach">Coach</button>
            <button onclick="scheduleQuickFollowUp(${l.id})" class="btn btn-secondary btn-sm" title="Set 2-Day Reminder">+2d</button>
            <button onclick="recordContactReply(${l.id})" class="btn btn-secondary btn-sm" title="Record Reply">Reply</button>
            <button onclick="editContact(${l.id})" class="btn btn-secondary btn-sm" title="Edit Contact Details">Edit</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderStageOptions(selectedStage) {
  const stages = [
    "New Contact", "Researching", "First Message Ready",
    "Conversation Started", "Interested", "Needs More Information",
    "Price Discussed", "Follow-up Due", "Converted Customer",
    "Not Interested", "Archived"
  ];
  return stages.map(s => `<option value="${s}" ${s === selectedStage ? 'selected' : ''}>${s}</option>`).join('');
}

function getStagePillHtml(stage) {
  const map = {
    'New Contact': 'stage-new',
    'Researching': 'stage-researching',
    'First Message Ready': 'stage-ready',
    'Conversation Started': 'stage-started',
    'Interested': 'stage-interested',
    'Needs More Information': 'stage-info',
    'Price Discussed': 'stage-price',
    'Follow-up Due': 'stage-followup',
    'Converted Customer': 'stage-converted',
    'Not Interested': 'stage-not-interested',
    'Archived': 'stage-archived'
  };
  const cls = map[stage] || 'stage-new';
  return `<span class="stage-pill ${cls}">${escapeHtml(stage)}</span>`;
}

async function updateLeadStage(leadId, newStage) {
  try {
    await fetch(`/api/leads/${leadId}/stage`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stage: newStage })
    });
    loadLeads();
    loadOverviewMetrics();
  } catch (err) {
    alert('Failed to update stage: ' + err.message);
  }
}

async function scheduleQuickFollowUp(leadId) {
  const days = prompt('Enter follow-up interval in days (e.g. 2 or 3):', '2');
  if (!days) return;
  try {
    const res = await fetch(`/api/leads/${leadId}/schedule-follow-up`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interval_days: parseInt(days) || 2 })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`Follow-up reminder scheduled for ${data.due_date.substring(0, 10)}!`);
      loadLeads();
      loadFollowUps();
      loadOverviewMetrics();
    } else {
      alert(data.detail || 'Could not schedule follow-up');
    }
  } catch (err) {
    alert('Error scheduling: ' + err.message);
  }
}

async function recordContactReply(leadId) {
  const reply = prompt('Enter a brief summary of what the person replied:');
  if (reply === null) return;
  try {
    const res = await fetch(`/api/leads/${leadId}/record-reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reply_summary: reply })
    });
    const data = await res.json();
    if (res.ok) {
      alert('Reply recorded! Active reminders cancelled, stage updated, and Conversation Coach prepared.');
      loadLeads();
      loadFollowUps();
      loadOverviewMetrics();
      openCoachForLead(leadId);
    } else {
      alert(data.detail || 'Error recording reply');
    }
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

function openNewContactModal() {
  document.getElementById('contactModalTitle').textContent = 'Create New Contact';
  document.getElementById('contactModalLeadId').value = '';
  document.getElementById('contactModalName').value = '';
  document.getElementById('contactModalHandle').value = '';
  document.getElementById('contactModalServer').value = '';
  document.getElementById('contactModalChannel').value = '';
  document.getElementById('contactModalStage').value = 'New Contact';
  document.getElementById('contactModalService').value = 'IPTV Subscriptions';
  document.getElementById('contactModalInterests').value = '';
  document.getElementById('contactModalNextAction').value = 'Draft opening message';
  document.getElementById('contactModalNotes').value = '';
  document.getElementById('contactModalOriginText').textContent = 'Manual Entry';
  document.getElementById('contactModal').style.display = 'flex';
}

function editContact(leadId) {
  const lead = cachedLeads.find(l => l.id === leadId);
  if (!lead) return;
  document.getElementById('contactModalTitle').textContent = `Edit Contact: ${lead.contact_name || lead.business_name}`;
  document.getElementById('contactModalLeadId').value = lead.id;
  document.getElementById('contactModalName').value = lead.contact_name || '';
  document.getElementById('contactModalHandle').value = lead.contact_handle || '';
  document.getElementById('contactModalServer').value = lead.business_name || lead.community_name || '';
  document.getElementById('contactModalChannel').value = lead.channel_name || '';
  document.getElementById('contactModalStage').value = lead.stage || lead.status || 'New Contact';
  document.getElementById('contactModalService').value = lead.service_interested || 'IPTV Subscriptions';
  document.getElementById('contactModalInterests').value = lead.stated_interests || '';
  document.getElementById('contactModalNextAction').value = lead.next_suggested_action || '';
  document.getElementById('contactModalNotes').value = lead.notes || '';
  document.getElementById('contactModalOriginText').textContent = (lead.source_data_origin === 'discord_received') ? 'Discord Received (from Message Search)' : 'Manual Entry';
  document.getElementById('contactModal').style.display = 'flex';
}

function closeContactModal() {
  document.getElementById('contactModal').style.display = 'none';
}

async function handleSaveContact(e) {
  e.preventDefault();
  const leadId = document.getElementById('contactModalLeadId').value;
  const payload = {
    id: leadId ? parseInt(leadId) : null,
    business_name: document.getElementById('contactModalServer').value.trim() || 'Direct Contact',
    contact_name: document.getElementById('contactModalName').value.trim(),
    contact_handle: document.getElementById('contactModalHandle').value.trim(),
    stage: document.getElementById('contactModalStage').value,
    status: document.getElementById('contactModalStage').value,
    service_interested: document.getElementById('contactModalService').value,
    category: document.getElementById('contactModalService').value,
    stated_interests: document.getElementById('contactModalInterests').value.trim(),
    next_suggested_action: document.getElementById('contactModalNextAction').value.trim(),
    notes: document.getElementById('contactModalNotes').value.trim(),
    source_data_origin: leadId ? undefined : 'manual_entered'
  };

  try {
    const res = await fetch('/api/leads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      closeContactModal();
      loadLeads();
      loadOverviewMetrics();
    } else {
      const err = await res.json();
      alert(err.detail || 'Failed to save contact');
    }
  } catch (err) {
    alert('Error saving contact: ' + err.message);
  }
}

// ==========================================================================
// 6. AI MESSAGE WRITER
// ==========================================================================

function handleScenarioChange() {
  const scenario = document.getElementById('msgScenarioSelect').value;
  generateMessageDraft();
}

async function generateMessageDraft() {
  const scenario = document.getElementById('msgScenarioSelect').value;
  const contactName = document.getElementById('msgRecipientName').value.trim();
  const businessName = document.getElementById('msgBusinessName').value.trim();
  const service = document.getElementById('msgServiceSelect').value;
  const tone = document.getElementById('msgToneSelect').value;
  const context = document.getElementById('msgCustomContext').value.trim();

  try {
    const res = await fetch('/api/messages/scenario', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario: scenario,
        contact_name: contactName,
        business_name: businessName,
        service_interested: service,
        custom_context: context,
        tone: tone
      })
    });
    const data = await res.json();
    const output = document.getElementById('msgDraftOutput');
    if (output) output.value = data.content || '';
    setText('msgCharCountBadge', `${data.character_count || 0} chars`);

    const checksBox = document.getElementById('antiSpamFeedbackBox');
    if (checksBox && data.anti_spam_checks) {
      checksBox.innerHTML = data.anti_spam_checks.map(c => `<div>✓ ${escapeHtml(c)}</div>`).join('');
    }
  } catch (err) {
    console.error('Error drafting message:', err);
  }
}

function copyDraftToClipboard() {
  const text = document.getElementById('msgDraftOutput').value;
  if (!text) return alert('Draft is empty.');
  navigator.clipboard.writeText(text).then(() => {
    alert('Message copied to clipboard! You can paste directly into Discord.');
  }).catch(() => {
    alert('Could not copy to clipboard. Please copy manually.');
  });
}

// ==========================================================================
// 7. SMART FOLLOW-UP SYSTEM
// ==========================================================================

async function loadFollowUps() {
  try {
    const res = await fetch('/api/follow-ups/detailed');
    if (!res.ok) return;
    currentFollowUpsData = await res.json();

    setText('fuCountToday', currentFollowUpsData.today?.length || 0);
    setText('fuCountOverdue', currentFollowUpsData.overdue?.length || 0);
    setText('fuCountUpcoming', currentFollowUpsData.upcoming?.length || 0);
    setText('fuCountCompleted', currentFollowUpsData.completed?.length || 0);

    renderActiveFollowUpTab();
  } catch (err) {
    console.error('Error loading follow-ups:', err);
  }
}

function switchFollowUpTab(tabKey) {
  activeFollowUpTab = tabKey;
  ['today', 'overdue', 'upcoming', 'completed'].forEach(k => {
    const btn = document.getElementById(`tab-fu-${k}`);
    if (btn) btn.classList.toggle('active', k === tabKey);
  });
  renderActiveFollowUpTab();
}

function renderActiveFollowUpTab() {
  const tbody = document.getElementById('followUpsTableBody');
  if (!tbody) return;

  const list = currentFollowUpsData[activeFollowUpTab] || [];
  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No follow-up reminders in this category.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(r => {
    const due = r.due_date ? r.due_date.substring(0, 10) : 'Not set';
    return `
      <tr>
        <td>
          <div style="font-weight: 700; color: #fff;">${escapeHtml(r.contact_name || r.business_name)}</div>
          <div style="font-size: 0.72rem; color: var(--blue-bright);">${escapeHtml(r.service_interested || 'General')}</div>
        </td>
        <td><code>${due}</code></td>
        <td style="font-size: 0.75rem; color: var(--text-muted); max-width: 180px;">${escapeHtml(r.context_summary || 'Discussion note')}</td>
        <td style="font-size: 0.78rem; max-width: 280px; font-family: monospace;">"${escapeHtml(r.suggested_message?.substring(0, 120))}..."</td>
        <td><span class="status-badge ${r.status === 'Due' ? 'badge-due' : ''}">${escapeHtml(r.status)}</span></td>
        <td>
          <div style="display: flex; gap: 0.35rem;">
            <button onclick="approveFollowUp(${r.id})" class="btn btn-primary btn-sm">Approve</button>
            <button onclick="rescheduleFollowUp(${r.id})" class="btn btn-secondary btn-sm">+2d</button>
            <button onclick="dismissFollowUp(${r.id})" class="btn btn-secondary btn-sm">Dismiss</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function approveFollowUp(reminderId) {
  try {
    const res = await fetch(`/api/follow-ups/${reminderId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    if (res.ok) {
      alert('Follow-up approved and staged! Copied to clipboard for manual review.');
      loadFollowUps();
    }
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

async function dismissFollowUp(reminderId) {
  if (!confirm('Dismiss this follow-up reminder?')) return;
  await fetch(`/api/follow-ups/${reminderId}/dismiss`, { method: 'POST' });
  loadFollowUps();
}

async function rescheduleFollowUp(reminderId) {
  await fetch(`/api/follow-ups/${reminderId}/reschedule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ extra_days: 2 })
  });
  loadFollowUps();
}

// ==========================================================================
// 8. AI CONVERSATION COACH
// ==========================================================================

function populateCoachLeadSelect() {
  const select = document.getElementById('coachLeadSelect');
  if (!select) return;
  select.innerHTML = '<option value="">-- Choose from Contacts or Paste Below --</option>' +
    cachedLeads.map(l => `<option value="${l.id}">${escapeHtml(l.contact_name || l.business_name)} (${escapeHtml(l.service_interested || 'General')})</option>`).join('');
}

function handleCoachLeadSelect() {
  const leadId = document.getElementById('coachLeadSelect').value;
  if (!leadId) return;
  const lead = cachedLeads.find(l => l.id === parseInt(leadId));
  if (lead) {
    document.getElementById('coachContactName').value = lead.contact_name || lead.contact_handle || '';
    document.getElementById('coachServiceSelect').value = lead.service_interested || 'IPTV Subscriptions';
    document.getElementById('coachRawConversation').value = lead.last_message_summary || lead.notes || '';
    runConversationCoach();
  }
}

function openCoachForLead(leadId) {
  switchView('coach');
  const select = document.getElementById('coachLeadSelect');
  if (select) {
    select.value = leadId;
    handleCoachLeadSelect();
  }
}

async function runConversationCoach() {
  const leadId = document.getElementById('coachLeadSelect').value;
  const contact = document.getElementById('coachContactName').value.trim();
  const service = document.getElementById('coachServiceSelect').value;
  const rawText = document.getElementById('coachRawConversation').value.trim();

  const container = document.getElementById('coachResultsContent');
  if (container) container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">Analyzing conversation & formulating strategic recommendations...</div>`;

  try {
    const res = await fetch('/api/coach/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lead_id: leadId ? parseInt(leadId) : null,
        contact_name: contact,
        target_service: service,
        raw_conversation: rawText
      })
    });
    const coach = await res.json();
    renderCoachOutput(coach);
  } catch (err) {
    if (container) container.innerHTML = `<div style="color: #fca5a5;">Coach error: ${err.message}</div>`;
  }
}

function renderCoachOutput(c) {
  const container = document.getElementById('coachResultsContent');
  if (!container) return;
  setText('coachContactSubtitle', `Strategic advice for ${c.contact_name} (${c.target_service})`);

  container.innerHTML = `
    <!-- Summary & Asking For -->
    <div style="padding: 1rem; background: var(--bg-deep); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
      <div style="font-size: 0.72rem; color: var(--blue-bright); font-weight: 700; text-transform: uppercase;">Conversation Situation</div>
      <div style="font-size: 0.84rem; color: #fff; margin-top: 0.25rem;">${escapeHtml(c.summary)}</div>
      <div style="margin-top: 0.5rem; font-size: 0.78rem; color: var(--text-secondary);">
        <strong>What they appear to be asking for:</strong> ${escapeHtml(c.what_they_are_asking_for)}
      </div>
    </div>

    <!-- Recommended Next Step -->
    <div style="padding: 0.85rem 1rem; background: var(--blue-subtle); border-radius: var(--radius-md); border: 1px solid var(--border-blue);">
      <div style="font-size: 0.72rem; color: var(--blue-bright); font-weight: 700; text-transform: uppercase;">Recommended Next Step</div>
      <div style="font-size: 0.84rem; font-weight: 600; color: #fff; margin-top: 0.2rem;">${escapeHtml(c.most_appropriate_next_step)}</div>
    </div>

    <!-- Recommended Reply -->
    <div style="padding: 1rem; background: var(--bg-card-hover); border-radius: var(--radius-md); border: 1px solid var(--border-medium);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
        <span style="font-size: 0.75rem; font-weight: 700; color: var(--emerald-light);">⭐ Recommended Reply (Natural & Non-Spammy)</span>
        <button onclick="copyTextToClipboard('${escapeHtml(c.recommended_reply).replace(/'/g, "\\'")}')" class="btn btn-secondary btn-sm">Copy</button>
      </div>
      <div style="font-size: 0.84rem; line-height: 1.5; color: #fff; font-family: monospace;">"${escapeHtml(c.recommended_reply)}"</div>
    </div>

    <!-- Alternative Tones -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
      ${c.alternative_replies.map(alt => `
        <div style="padding: 0.85rem; background: var(--bg-deep); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
            <span style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted);">${escapeHtml(alt.tone)}</span>
            <button onclick="copyTextToClipboard('${escapeHtml(alt.content).replace(/'/g, "\\'")}')" class="btn btn-secondary btn-sm" style="padding: 0.15rem 0.4rem; font-size: 0.68rem;">Copy</button>
          </div>
          <div style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.4;">"${escapeHtml(alt.content)}"</div>
        </div>
      `).join('')}
    </div>

    <!-- Discovery Questions -->
    <div style="padding: 0.85rem 1rem; background: var(--bg-deep); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
      <div style="font-size: 0.72rem; color: var(--amber-primary); font-weight: 700; text-transform: uppercase; margin-bottom: 0.35rem;">Discovery Questions to Understand Needs</div>
      <ul style="padding-left: 1.25rem; font-size: 0.78rem; color: var(--text-secondary); line-height: 1.5;">
        ${c.discovery_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}
      </ul>
    </div>

    <!-- Warning Signs -->
    <div style="padding: 0.85rem 1rem; background: rgba(239, 68, 68, 0.08); border-radius: var(--radius-md); border: 1px solid rgba(239, 68, 68, 0.3);">
      <div style="font-size: 0.72rem; color: #fca5a5; font-weight: 700; text-transform: uppercase; margin-bottom: 0.35rem;">⚠️ Sales Warning Signs & Safeguards</div>
      <ul style="padding-left: 1.25rem; font-size: 0.78rem; color: var(--text-secondary); line-height: 1.5;">
        ${c.warning_signs.map(w => `<li>${escapeHtml(w)}</li>`).join('')}
      </ul>
    </div>
  `;
}

// ==========================================================================
// 9. AI COMMAND CENTER (INTERACTIVE ASSISTANT)
// ==========================================================================

async function loadChatHistory() {
  try {
    const res = await fetch('/api/chat/history');
    if (!res.ok) return;
    const history = await res.json();
    const box = document.getElementById('chatHistoryBox');
    if (!box) return;

    if (history.length > 0) {
      box.innerHTML = history.map(msg => `
        <div class="chat-bubble ${msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'}">
          ${formatMarkdownSimple(msg.message)}
        </div>
      `).join('');
      box.scrollTop = box.scrollHeight;
    }
  } catch (err) {
    console.error('Error loading chat history:', err);
  }
}

function handleChatKeyPress(e) {
  if (e.key === 'Enter') submitChatInstruction();
}

function sendQuickCommand(cmdText) {
  document.getElementById('chatInputField').value = cmdText;
  submitChatInstruction();
}

async function submitChatInstruction() {
  const input = document.getElementById('chatInputField');
  const text = input?.value.trim();
  if (!text) return;
  input.value = '';

  const box = document.getElementById('chatHistoryBox');
  if (box) {
    box.innerHTML += `
      <div class="chat-bubble chat-bubble-user">${escapeHtml(text)}</div>
      <div class="chat-bubble chat-bubble-assistant" id="chatThinking">Consulting workspace data...</div>
    `;
    box.scrollTop = box.scrollHeight;
  }

  try {
    const res = await fetch('/api/chat/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ instruction: text })
    });
    const data = await res.json();
    const thinking = document.getElementById('chatThinking');
    if (thinking) {
      thinking.outerHTML = `
        <div class="chat-bubble chat-bubble-assistant">
          ${formatMarkdownSimple(data.response)}
        </div>
      `;
    }
    box.scrollTop = box.scrollHeight;
  } catch (err) {
    const thinking = document.getElementById('chatThinking');
    if (thinking) thinking.textContent = 'Error: ' + err.message;
  }
}

async function clearChatHistory() {
  if (!confirm('Clear AI Command Center history?')) return;
  await fetch('/api/chat/history', { method: 'DELETE' });
  const box = document.getElementById('chatHistoryBox');
  if (box) {
    box.innerHTML = `<div class="chat-bubble chat-bubble-assistant">Command center history cleared. How can I assist you with Famous Media Technologies?</div>`;
  }
}

// ==========================================================================
// 10. BUSINESS & PRICING SETTINGS
// ==========================================================================

async function loadBusinessSettings() {
  try {
    const res = await fetch('/api/settings/business');
    if (!res.ok) return;
    const s = await res.json();

    setValue('cfgBusinessName', s.business_name || 'Famous Media Technologies');
    setValue('cfgTelegramContact', s.telegram_contact || '@Phamouxetv');
    setValue('cfgSenderName', s.sender_name || 'Famous Media Technologies');
    setValue('cfgSub1mo', s.iptv_sub_1mo || 15);
    setValue('cfgSub3mo', s.iptv_sub_3mo || 35);
    setValue('cfgSub6mo', s.iptv_sub_6mo || 55);
    setValue('cfgSub12mo', s.iptv_sub_12mo || 80);
    setValue('cfgReseller120', s.reseller_120_credits || 350);
    setValue('cfgAppRebrand', s.app_rebrand_with_panel || 150);
    setValue('cfgAppDevPricing', s.app_dev_pricing || 'Contact for requirements and custom pricing');
    setValue('cfgServerPricing', s.server_setup_pricing || 'Contact for infrastructure requirements');
    setValue('cfgBusinessNotes', s.notes || '');

    const chk = document.getElementById('cfgNeverQuoteUnlisted');
    if (chk) chk.checked = Boolean(s.never_quote_unlisted);
  } catch (err) {
    console.error('Error loading business settings:', err);
  }
}

async function saveBusinessProfile(e) {
  e.preventDefault();
  const payload = {
    business_name: document.getElementById('cfgBusinessName').value.trim(),
    telegram_contact: document.getElementById('cfgTelegramContact').value.trim(),
    sender_name: document.getElementById('cfgSenderName').value.trim(),
    iptv_sub_1mo: parseFloat(document.getElementById('cfgSub1mo').value) || 15,
    iptv_sub_3mo: parseFloat(document.getElementById('cfgSub3mo').value) || 35,
    iptv_sub_6mo: parseFloat(document.getElementById('cfgSub6mo').value) || 55,
    iptv_sub_12mo: parseFloat(document.getElementById('cfgSub12mo').value) || 80,
    reseller_120_credits: parseFloat(document.getElementById('cfgReseller120').value) || 350,
    app_rebrand_with_panel: parseFloat(document.getElementById('cfgAppRebrand').value) || 150,
    app_dev_pricing: document.getElementById('cfgAppDevPricing').value.trim(),
    server_setup_pricing: document.getElementById('cfgServerPricing').value.trim(),
    never_quote_unlisted: document.getElementById('cfgNeverQuoteUnlisted').checked ? 1 : 0,
    notes: document.getElementById('cfgBusinessNotes').value.trim()
  };

  try {
    const res = await fetch('/api/settings/business', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      alert('Famous Media Technologies business settings saved successfully!');
    }
  } catch (err) {
    alert('Failed to save settings: ' + err.message);
  }
}

// ==========================================================================
// 11. AI PROVIDER CONFIG
// ==========================================================================

async function loadAISettings() {
  try {
    const res = await fetch('/api/settings/ai-provider');
    if (!res.ok) return;
    const data = await res.json();
    setValue('cfgAIProvider', data.provider || 'builtin');
    setValue('cfgAIModelName', data.model_name || 'gemini-1.5-flash');
    setValue('cfgAITemperature', data.temperature || 0.3);
    if (data.api_key_masked) {
      setText('cfgAIKeyHint', `Current Key: ${data.api_key_masked}`);
    }
  } catch (err) {
    console.error('Error loading AI settings:', err);
  }
}

async function saveAIProvider(e) {
  e.preventDefault();
  const payload = {
    provider: document.getElementById('cfgAIProvider').value,
    api_key: document.getElementById('cfgAIApiKey').value.trim(),
    model_name: document.getElementById('cfgAIModelName').value.trim(),
    temperature: parseFloat(document.getElementById('cfgAITemperature').value) || 0.3
  };

  try {
    const res = await fetch('/api/settings/ai-provider', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      alert('AI provider configuration updated!');
      loadAISettings();
    }
  } catch (err) {
    alert('Failed to save AI settings: ' + err.message);
  }
}

// ==========================================================================
// 12. PRIVACY & ERASURE
// ==========================================================================

async function clearResearchData() {
  if (!confirm('Clear all un-saved message and member cache?')) return;
  const res = await fetch('/api/privacy/clear-research', { method: 'POST' });
  const data = await res.json();
  alert(`Cleared ${data.cleared_records || 0} temporary cache records.`);
  executeMessageResearch();
}

async function confirmClearAllContacts() {
  const code = prompt('Type DELETE to confirm clearing all contacts and reminders permanently:');
  if (code !== 'DELETE') return;
  await fetch('/api/leads/clear-all', { method: 'POST' });
  alert('All contacts and follow-ups have been erased.');
  loadLeads();
  loadFollowUps();
  loadOverviewMetrics();
}

// ==========================================================================
// UTILITIES
// ==========================================================================

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setValue(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

function copyTextToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert('Copied to clipboard!');
  }).catch(() => {
    prompt('Copy text:', text);
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatMarkdownSimple(text) {
  if (!text) return '';
  let formatted = escapeHtml(text);
  formatted = formatted.replace(/\n/g, '<br>');
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
  return formatted;
}

async function changeMasterPassword(e) {
  e.preventDefault();
  const current_password = document.getElementById('currentMasterPwd')?.value || '';
  const new_password = document.getElementById('newMasterPwd')?.value || '';
  const confirm_new_password = document.getElementById('confirmNewMasterPwd')?.value || '';

  if (new_password !== confirm_new_password) {
    return alert('New passwords do not match. Please verify.');
  }
  if (new_password.length < 6) {
    return alert('New password must be at least 6 characters.');
  }

  try {
    const res = await fetch('/api/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password, new_password, confirm_new_password })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert('Master password successfully updated!');
      document.getElementById('changePasswordForm')?.reset();
    } else {
      alert(data.detail || data.error || 'Failed to update password.');
    }
  } catch (err) {
    alert('Error updating password: ' + err.message);
  }
}

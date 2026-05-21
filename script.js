// Combined app script — includes Screen 3 implementation
// DOM Element References
const pageWelcome = document.getElementById('page-welcome');
const pageChat = document.getElementById('page-chat');
const startToInstructions = document.getElementById('start-to-instructions');
const chatWindow = document.getElementById('chat-window');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn') || document.getElementById('send-action');
const suggestionButtons = document.querySelectorAll('[data-suggestion]');

// Response Data for Chatbot (basic fallbacks)
const responses = [
  {
    keys: ['expense ratio', 'expense', 'ratio'],
    answer: 'The expense ratio for Mirae Asset Large Cap Fund is 1.98% per year. Expense ratios are the annual fund management charges disclosed in the AMC scheme information document.',
    source: 'https://www.miraeassetmf.co.in'
  },
  {
    keys: ['exit load', 'exit', 'load'],
    answer: 'Mirae Asset Large Cap Fund charges an exit load of 1% if redeemed within 1 year from the date of allotment. No exit load applies after 1 year.',
    source: 'https://www.miraeassetmf.co.in'
  },
  {
    keys: ['sip minimum', 'minimum sip', 'sip'],
    answer: 'The minimum SIP amount for Mirae Asset ELSS Tax Saver is ₹500 per month. SIP frequency can also be registered monthly, quarterly, or annually depending on the AMC offer.',
    source: 'https://www.miraeassetmf.co.in'
  },
  {
    keys: ['elss lock', 'lock-in', 'elss'],
    answer: 'ELSS funds have a mandatory lock-in period of 3 years from the date of allotment.',
    source: 'https://www.miraeassetmf.co.in'
  }
];

// --- SCREEN 3 DATA & CATEGORIES ---
const questionPool = [
  { text: "Expense ratio of Large Cap Fund?", full: "What is the expense ratio of Mirae Asset Large Cap Fund?" },
  { text: "Exit load on Flexi Cap Fund?", full: "What is the exit load for Mirae Asset Flexi Cap Fund?" },
  { text: "Minimum SIP for ELSS Tax Saver?", full: "What is the minimum SIP for Mirae Asset ELSS Tax Saver Fund?" },
  { text: "ELSS lock-in period?", full: "What is the lock-in period for Mirae Asset ELSS Tax Saver Fund?" },
  { text: "Benchmark index of Large Cap Fund?", full: "What is the benchmark index for Mirae Asset Large Cap Fund?" },
  { text: "Riskometer of Midcap Fund?", full: "What is the riskometer level of Mirae Asset Midcap Fund?" },
  { text: "Minimum lump sum for Flexi Cap?", full: "What is the minimum lump sum for Mirae Asset Flexi Cap Fund?" },
  { text: "Download capital gains statement?", full: "How do I download my capital gains statement for Mirae Asset funds?" },
  { text: "Exit load after 1 year?", full: "Is there an exit load after 1 year for Mirae Asset funds?" },
  { text: "SIP frequency for Large Cap?", full: "What are the SIP frequency options for Mirae Asset Large Cap Fund?" },
  { text: "Expense ratio of Midcap Fund?", full: "What is the expense ratio of Mirae Asset Midcap Fund?" },
  { text: "Minimum SIP for Large Cap Fund?", full: "What is the minimum SIP for Mirae Asset Large Cap Fund?" },
  { text: "Riskometer of ELSS Tax Saver?", full: "What is the riskometer level of Mirae Asset ELSS Tax Saver Fund?" },
  { text: "Exit load for ELSS Tax Saver?", full: "What is the exit load for Mirae Asset ELSS Tax Saver Fund?" },
  { text: "Minimum lump sum for Large Cap?", full: "What is the minimum lump sum for Mirae Asset Large Cap Fund?" },
  { text: "Benchmark of Midcap Fund?", full: "What is the benchmark index for Mirae Asset Midcap Fund?" }
];

const categories = {
  cost: [
    "Expense ratio of Large Cap Fund?",
    "Expense ratio of Midcap Fund?"
  ],
  load: [
    "Exit load on Flexi Cap Fund?",
    "Exit load after 1 year?",
    "Exit load for ELSS Tax Saver?"
  ],
  sip: [
    "Minimum SIP for ELSS Tax Saver?",
    "Minimum SIP for Large Cap Fund?",
    "SIP frequency for Large Cap?",
    "Minimum lump sum for Flexi Cap?",
    "Minimum lump sum for Large Cap?"
  ],
  info: [
    "ELSS lock-in period?",
    "Benchmark index of Large Cap Fund?",
    "Riskometer of Midcap Fund?",
    "Download capital gains statement?",
    "Riskometer of ELSS Tax Saver?",
    "Benchmark of Midcap Fund?"
  ]
};

// Screen 3 State
let hasWelcomeShown = false;
let isThinking = false;
const BACKEND_URL = "https://mffaqcb-production.up.railway.app";
let slowLoadTimeout = null;

// Sidebar suggestions container (expecting id sidebar-suggestions)
let sidebarSuggestions = document.getElementById('sidebar-suggestions');
if (!sidebarSuggestions) {
  const sidebar = document.querySelector('.chat-sidebar');
  if (sidebar) {
    sidebarSuggestions = document.createElement('div');
    sidebarSuggestions.id = 'sidebar-suggestions';
    // place it after branding
    const brand = sidebar.querySelector('.sidebar-brand');
    sidebar.insertBefore(sidebarSuggestions, brand.nextSibling);
  } else {
    sidebarSuggestions = document.createElement('div');
    sidebarSuggestions.id = 'sidebar-suggestions';
    document.body.insertBefore(sidebarSuggestions, document.body.firstChild);
  }
}

// Utilities
function pickRandom(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function findQuestionByText(shortText) { return questionPool.find(q => q.text === shortText) || null; }

// Scroll helper
function scrollToBottom() {
  if (!chatWindow) return;
  chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: 'smooth' });
}

// Render suggestions per spec
function renderSuggestions() {
  if (isThinking) return;
  const picks = [];
  for (const cat of ['cost','load','sip','info']) {
    const short = pickRandom(categories[cat]);
    const q = findQuestionByText(short);
    if (q) picks.push({ cat, item: q });
  }
  sidebarSuggestions.innerHTML = '';
  picks.forEach(({cat, item}) => {
    const row = document.createElement('div');
    row.className = 'suggestion-row';
    row.setAttribute('data-full-question', item.full);
    const icon = document.createElement('span');
    icon.innerHTML = (cat === 'cost')
      ? '<span class="sug-icon sug-icon-cost">₹</span>'
      : (cat === 'load')
      ? '<span class="sug-icon sug-icon-load">⇄</span>'
      : (cat === 'sip')
      ? '<span class="sug-icon sug-icon-sip">⊙</span>'
      : '<span class="sug-icon sug-icon-info">i</span>';
    const text = document.createElement('span'); text.className = 'suggestion-text'; text.textContent = item.text;
    row.appendChild(icon); row.appendChild(text);
    row.addEventListener('click', () => { chatInput.value = item.full; chatInput.focus(); setTimeout(() => sendMessage(), 200); });
    sidebarSuggestions.appendChild(row);
  });
}

// Welcome card render
function renderWelcomeMessage() {
  if (!chatWindow) return;
  const container = document.createElement('div');
  container.className = 'welcome-card-custom';
  const title = document.createElement('h3'); title.textContent = '👋 Welcome to FundBot';
  const desc = document.createElement('p');
  desc.textContent = 'Ask me factual questions about Mirae Asset funds — expense ratios, SIP minimums, exit loads, lock-in periods, and more. Every answer includes a source link.';
  container.appendChild(title); container.appendChild(desc);
  const chipRow = document.createElement('div'); chipRow.className = 'chip-row';
  const chipData = [
    { label: 'Expense ratio?', full: 'What is the expense ratio of Mirae Asset Large Cap Fund?' },
    { label: 'ELSS lock-in?', full: 'What is the lock-in period for Mirae Asset ELSS Tax Saver Fund?' },
    { label: 'Minimum SIP?', full: 'What is the minimum SIP for Mirae Asset ELSS Tax Saver Fund?' }
  ];
  chipData.forEach(cd => {
    const chip = document.createElement('span'); chip.className='welcome-chip'; chip.dataset.chipQuestion = cd.full; chip.textContent = cd.label;
    chipRow.appendChild(chip);
  });
  container.appendChild(chipRow);
  chatWindow.appendChild(container);
  scrollToBottom();
}

// Message builders
function appendUserMessage(text) {
  const row = document.createElement('div'); row.className = 'msg-row msg-user';
  const bubble = document.createElement('div'); bubble.className = 'bubble-user'; bubble.textContent = text;
  row.appendChild(bubble); chatWindow.appendChild(row); scrollToBottom();
}

function appendThinkingBubble() {
  isThinking = true;
  const row = document.createElement('div'); row.className = 'msg-row msg-bot'; row.id = 'thinking-bubble';
  const avatar = document.createElement('div'); avatar.className='bot-avatar'; avatar.textContent='F';
  const bubble = document.createElement('div'); bubble.className='bubble-bot bubble-thinking';
  const dot1 = document.createElement('span'); dot1.className='dot';
  const dot2 = document.createElement('span'); dot2.className='dot';
  const dot3 = document.createElement('span'); dot3.className='dot';
  bubble.appendChild(dot1); bubble.appendChild(dot2); bubble.appendChild(dot3);
  row.appendChild(avatar); row.appendChild(bubble); chatWindow.appendChild(row); scrollToBottom();
}
function removeThinkingBubble() { const t=document.getElementById('thinking-bubble'); if (t && t.parentNode) t.parentNode.removeChild(t); isThinking=false; }

function showMessage(answerText, sourceUrl) {
  appendBotAnswer(answerText, sourceUrl);
}

function appendBotAnswer(answerText, sourceUrl) {
  const row = document.createElement('div'); row.className='msg-row msg-bot';
  const avatar = document.createElement('div'); avatar.className='bot-avatar'; avatar.textContent='🤖';
  const bubble = document.createElement('div'); bubble.className='bubble-bot';
  const p = document.createElement('p'); p.className='bubble-answer'; p.textContent = answerText;
  const srcWrap = document.createElement('div'); srcWrap.className='bubble-source';
  const srcIcon = document.createElement('span'); srcIcon.className='source-icon'; srcIcon.textContent='🔗';
  const link = document.createElement('a'); link.className='source-link'; link.target='_blank'; link.rel='noopener noreferrer';
  let displayText = sourceUrl ? (new URL(sourceUrl, window.location.href).hostname + ' · Last updated from sources: June 2025') : 'localhost · Last updated from sources: June 2025';
  link.textContent = displayText; link.href = sourceUrl || 'http://localhost:5000';
  srcWrap.appendChild(srcIcon); srcWrap.appendChild(link);
  bubble.appendChild(p); bubble.appendChild(srcWrap);
  row.appendChild(avatar); row.appendChild(bubble); chatWindow.appendChild(row); scrollToBottom();
}

function appendRefusal(answerText, sourceUrl) {
  const row = document.createElement('div'); row.className='msg-row msg-bot';
  const avatar = document.createElement('div'); avatar.className='bot-avatar'; avatar.textContent='🤖';
  const bubble = document.createElement('div'); bubble.className='bubble-bot bubble-refused';
  const p = document.createElement('p'); p.className='bubble-answer'; p.textContent = answerText;
  const srcWrap = document.createElement('div'); srcWrap.className='bubble-source';
  const srcIcon = document.createElement('span'); srcIcon.className='source-icon'; srcIcon.textContent='📚';
  const link = document.createElement('a'); link.className='source-link'; link.target='_blank'; link.rel='noopener noreferrer'; link.href = sourceUrl || 'https://www.amfiindia.com';
  link.textContent = 'Learn more at amfiindia.com';
  srcWrap.appendChild(srcIcon); srcWrap.appendChild(link);
  bubble.appendChild(p); bubble.appendChild(srcWrap);
  row.appendChild(avatar); row.appendChild(bubble); chatWindow.appendChild(row); scrollToBottom();
}

function appendBackendErrorMessage() {
  const row = document.createElement('div'); row.className='msg-row msg-bot';
  const avatar = document.createElement('div'); avatar.className='bot-avatar'; avatar.textContent='🤖';
  const bubble = document.createElement('div'); bubble.className='bubble-bot error-backend';
  const p = document.createElement('p'); p.className='bubble-answer'; p.textContent = 'Backend not connected. Please make sure the Flask server is running by typing "python app.py" in your terminal.';
  bubble.appendChild(p);
  row.appendChild(avatar); row.appendChild(bubble); chatWindow.appendChild(row); scrollToBottom();
}

// sendMessage implementation per spec
function sendMessage() {
  if (!chatInput) return;
  const raw = chatInput.value || '';
  const userQuestion = raw.trim();
  if (!userQuestion) return;
  // clear input immediately
  chatInput.value = '';
  // disable controls
  if (sendBtn) sendBtn.disabled = true;
  chatInput.disabled = true;
  // append user bubble
  appendUserMessage(userQuestion);
  // thinking
  appendThinkingBubble();

  slowLoadTimeout = setTimeout(() => {
    const thinkingBubble = document.getElementById('thinking-bubble');
    if (thinkingBubble) {
      const bubble = thinkingBubble.querySelector('.bubble-thinking');
      if (bubble) bubble.textContent = 'Connecting to server, this may take up to 30 seconds on first load...';
    }
  }, 5000);

  fetch(BACKEND_URL + "/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: userQuestion })
  })
  .then(res => res.json())
  .then(data => {
      clearTimeout(slowLoadTimeout);
      removeThinkingBubble();
      if (data.error) {
          showMessage("Error: " + data.error);
      } else {
          showMessage(data.answer, data.source);
      }
  })
  .catch(() => {
      clearTimeout(slowLoadTimeout);
      removeThinkingBubble();
      appendBackendErrorMessage();
  })
  .finally(() => {
    if (sendBtn) sendBtn.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
    // refresh suggestions after bot reply
    renderSuggestions();
  });
}

// Event listeners for send controls
if (sendBtn) sendBtn.addEventListener('click', (e) => { e.preventDefault(); sendMessage(); });
if (chatInput) chatInput.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); sendMessage(); } });

// Feature strip clicks with data-question
function handleFeatureCardClick(questionText) {
  // Hide all screens
  document.getElementById('page-welcome').style.display = 'none';
  document.getElementById('page-chat').style.display = 'block';
  
  // Render suggestions and welcome if needed
  renderSuggestions();
  if (!hasWelcomeShown) {
    renderWelcomeMessage();
    hasWelcomeShown = true;
  }

  // Pre-fill and send after transition
  setTimeout(() => {
    document.getElementById('chat-input').value = questionText;
    sendMessage();
  }, 300);
}

document.querySelectorAll('[data-question]').forEach(card => {
  card.style.cursor = 'pointer';
  card.addEventListener('click', () => {
    handleFeatureCardClick(card.dataset.question);
  });
});

// Get Started button should open chat directly
if (startToInstructions) {
  startToInstructions.addEventListener('click', (e) => {
    e.preventDefault();
    if (pageChat) pageChat.style.display = 'block';
    renderSuggestions();
    if (!hasWelcomeShown) {
      renderWelcomeMessage();
      hasWelcomeShown = true;
    }
    if (chatInput) setTimeout(() => chatInput.focus(), 120);
  });
}

// Suggestions should be shown when chat becomes visible
function onChatVisible() { 
  renderSuggestions();
  if (!hasWelcomeShown) {
    renderWelcomeMessage();
    hasWelcomeShown = true;
  }
}
if (pageChat) {
  const mo = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.attributeName === 'class') {
        const el = m.target;
        if (el.classList.contains('active')) onChatVisible();
      }
    }
  });
  mo.observe(pageChat, { attributes: true });
  if (pageChat.classList.contains('active')) onChatVisible();
}

// Keep suggestions refreshed when bot messages are appended (skip thinking)
if (chatWindow) {
  const observer = new MutationObserver((mutations) => {
    for (const mut of mutations) {
      mut.addedNodes.forEach(node => {
        if (node.nodeType === 1 && node.classList.contains('msg-row')) {
          if (!node.id || node.id !== 'thinking-bubble') {
            if (node.classList.contains('msg-bot')) {
              setTimeout(() => renderSuggestions(), 150);
            }
          }
        }
      });
    }
  });
  observer.observe(chatWindow, { childList: true });
}

// Modal System (kept from earlier implementation)
function initializeModals() {
  const modalBackdrop = document.getElementById('modal-backdrop');
  const modalCloseButtons = document.querySelectorAll('.modal-close');
  const modalUnderstandButton = document.querySelector('.modal-action-button');
  const navbarLinks = document.querySelectorAll('.nav-links span');

  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal || !modalBackdrop) return;
    modalBackdrop.classList.add('active');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (!modalBackdrop) return;
    modalBackdrop.classList.remove('active');
    const openModalElement = modalBackdrop.querySelector('.modal.active');
    if (openModalElement) openModalElement.classList.remove('active');
    document.body.style.overflow = '';
  }

  navbarLinks.forEach((link) => {
    const text = link.textContent.trim().toLowerCase();
    if (text === 'about') link.addEventListener('click', () => openModal('modal-about'));
    else if (text === 'source') link.addEventListener('click', () => openModal('modal-source'));
    else if (text === 'disclaimer') link.addEventListener('click', () => openModal('modal-disclaimer'));
  });

  modalCloseButtons.forEach((button) => button.addEventListener('click', closeModal));
  if (modalUnderstandButton) modalUnderstandButton.addEventListener('click', closeModal);
  if (modalBackdrop) modalBackdrop.addEventListener('click', (e) => { if (e.target === modalBackdrop) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
}

document.addEventListener('DOMContentLoaded', () => {
  initializeModals();
});

// Delegated event listener for welcome chips
document.getElementById('chat-window').addEventListener('click', function(e) {
  if (e.target.classList.contains('welcome-chip')) {
    const question = e.target.dataset.chipQuestion;
    document.getElementById('chat-input').value = question;
    setTimeout(() => sendMessage(), 200);
  }
});

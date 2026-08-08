/**
 * FundBot frontend.
 *
 * Deliberately dependency-free and framework-free: the whole UI is static files
 * on a CDN, so there is no build step to run and nothing to keep in sync.
 *
 * One rule worth stating explicitly — this file contains no canned answers. An
 * earlier version shipped hardcoded fallback facts that were served whenever the
 * API was unreachable; they silently drifted out of step with the knowledge base
 * and started contradicting it. A visible error is the honest failure mode for a
 * bot whose entire value proposition is being factually correct.
 */
(function () {
  "use strict";

  var API_BASE = (window.API_BASE_URL || "/api").replace(/\/+$/, "");

  var pageWelcome = document.getElementById("page-welcome");
  var pageChat = document.getElementById("page-chat");
  var chatWindow = document.getElementById("chat-window");
  var chatInput = document.getElementById("chat-input");
  var sendAction = document.getElementById("send-action");
  var micButton = document.getElementById("mic-button");
  var sidebarSuggestions = document.getElementById("sidebar-suggestions");
  var startButton = document.getElementById("start-to-instructions");
  var statusDot = document.getElementById("status-dot");
  var statusText = document.getElementById("status-text");

  var isBusy = false;
  var welcomeShown = false;

  // --- Suggestion pool ----------------------------------------------------

  var SUGGESTIONS = {
    cost: [
      { short: "Expense ratio of Large Cap Fund?", full: "What is the expense ratio of Mirae Asset Large Cap Fund?" },
      { short: "Expense ratio of Midcap Fund?", full: "What is the expense ratio of Mirae Asset Midcap Fund?" },
      { short: "Direct vs Regular plan?", full: "What is the difference between a direct and a regular plan?" }
    ],
    load: [
      { short: "Exit load on Flexi Cap Fund?", full: "What is the exit load for Mirae Asset Flexi Cap Fund?" },
      { short: "Exit load on Midcap Fund?", full: "What is the exit load for Mirae Asset Midcap Fund?" },
      { short: "What is an exit load?", full: "What is an exit load?" }
    ],
    sip: [
      { short: "Minimum SIP for ELSS Tax Saver?", full: "What is the minimum SIP for Mirae Asset ELSS Tax Saver Fund?" },
      { short: "Minimum SIP for Large Cap Fund?", full: "What is the minimum SIP for Mirae Asset Large Cap Fund?" },
      { short: "SIP frequency for Large Cap?", full: "What SIP frequencies does Mirae Asset Large Cap Fund offer?" },
      { short: "Minimum lump sum for Flexi Cap?", full: "What is the minimum lump sum for Mirae Asset Flexi Cap Fund?" }
    ],
    info: [
      { short: "ELSS lock-in period?", full: "What is the lock-in period for Mirae Asset ELSS Tax Saver Fund?" },
      { short: "Benchmark of Large Cap Fund?", full: "What is the benchmark index for Mirae Asset Large Cap Fund?" },
      { short: "Riskometer of Midcap Fund?", full: "What is the riskometer level of Mirae Asset Midcap Fund?" },
      { short: "Download capital gains statement?", full: "How do I download my capital gains statement?" },
      { short: "How are equity funds taxed?", full: "How are equity mutual funds taxed?" }
    ]
  };

  var CATEGORY_ICONS = {
    cost: { glyph: "₹", className: "sug-icon-cost" },
    load: { glyph: "⇄", className: "sug-icon-load" },
    sip: { glyph: "⊙", className: "sug-icon-sip" },
    info: { glyph: "i", className: "sug-icon-info" }
  };

  function pickRandom(list) {
    return list[Math.floor(Math.random() * list.length)];
  }

  // --- DOM helpers --------------------------------------------------------

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function scrollToBottom() {
    if (chatWindow) chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: "smooth" });
  }

  function hostnameOf(url) {
    try {
      return new URL(url, window.location.href).hostname.replace(/^www\./, "");
    } catch (err) {
      return url;
    }
  }

  // --- Rendering ----------------------------------------------------------

  function renderSuggestions() {
    if (!sidebarSuggestions || isBusy) return;
    sidebarSuggestions.innerHTML = "";

    Object.keys(SUGGESTIONS).forEach(function (category) {
      var item = pickRandom(SUGGESTIONS[category]);
      var meta = CATEGORY_ICONS[category];

      var row = el("div", "suggestion-row");
      row.setAttribute("role", "button");
      row.setAttribute("tabindex", "0");

      var icon = el("span", "sug-icon " + meta.className, meta.glyph);
      row.appendChild(icon);
      row.appendChild(el("span", "suggestion-text", item.short));

      function fire() {
        if (isBusy) return;
        chatInput.value = item.full;
        sendMessage();
      }
      row.addEventListener("click", fire);
      row.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          fire();
        }
      });

      sidebarSuggestions.appendChild(row);
    });
  }

  function renderWelcomeCard() {
    if (!chatWindow || welcomeShown) return;
    welcomeShown = true;

    var card = el("div", "welcome-card-custom");
    card.appendChild(el("h3", null, "👋 Welcome to FundBot"));
    card.appendChild(
      el(
        "p",
        null,
        "Ask me factual questions about Mirae Asset funds — expense ratios, SIP minimums, exit loads, lock-in periods, and more. Every answer includes a source link."
      )
    );

    var chipRow = el("div", "chip-row");
    [
      { label: "Expense ratio?", full: "What is the expense ratio of Mirae Asset Large Cap Fund?" },
      { label: "ELSS lock-in?", full: "What is the lock-in period for Mirae Asset ELSS Tax Saver Fund?" },
      { label: "Minimum SIP?", full: "What is the minimum SIP for Mirae Asset ELSS Tax Saver Fund?" }
    ].forEach(function (chip) {
      var node = el("span", "welcome-chip", chip.label);
      node.dataset.chipQuestion = chip.full;
      chipRow.appendChild(node);
    });

    card.appendChild(chipRow);
    chatWindow.appendChild(card);
    scrollToBottom();
  }

  function appendUserMessage(text) {
    var row = el("div", "msg-row msg-user");
    row.appendChild(el("div", "bubble-user", text));
    chatWindow.appendChild(row);
    scrollToBottom();
  }

  function appendThinking() {
    var row = el("div", "msg-row msg-bot");
    row.id = "thinking-bubble";
    row.appendChild(el("div", "bot-avatar", "F"));

    var bubble = el("div", "bubble-bot bubble-thinking");
    for (var i = 0; i < 3; i++) bubble.appendChild(el("span", "dot"));
    row.appendChild(bubble);

    chatWindow.appendChild(row);
    scrollToBottom();
  }

  function removeThinking() {
    var node = document.getElementById("thinking-bubble");
    if (node && node.parentNode) node.parentNode.removeChild(node);
  }

  /**
   * Renders one bot reply. `kind` comes from the API and picks the styling:
   * a refusal and a real answer should not look identical.
   */
  function appendBotMessage(data) {
    var kind = data.kind || "answer";
    // Prefix match, so a new refusal kind added on the server is styled as a
    // refusal without needing a matching change here.
    var isRefusal = kind.indexOf("refusal_") === 0;
    var isUnknown = kind === "no_answer";

    var row = el("div", "msg-row msg-bot");
    row.appendChild(el("div", "bot-avatar", "🤖"));

    var bubbleClass = "bubble-bot";
    if (isRefusal || isUnknown) bubbleClass += " bubble-refused";
    var bubble = el("div", bubbleClass);
    bubble.appendChild(el("p", "bubble-answer", data.answer));

    if (data.source) {
      var sourceWrap = el("div", "bubble-source");
      sourceWrap.appendChild(el("span", "source-icon", isRefusal ? "📚" : "🔗"));

      var link = el("a", "source-link");
      link.href = data.source;
      link.target = "_blank";
      link.rel = "noopener noreferrer";

      var label = data.source_label || hostnameOf(data.source);
      link.textContent = data.last_updated ? label + " · updated " + data.last_updated : label;
      sourceWrap.appendChild(link);
      bubble.appendChild(sourceWrap);
    }

    row.appendChild(bubble);
    chatWindow.appendChild(row);
    scrollToBottom();
  }

  function appendError(message) {
    var row = el("div", "msg-row msg-bot");
    row.appendChild(el("div", "bot-avatar", "🤖"));
    var bubble = el("div", "bubble-bot error-backend");
    bubble.appendChild(el("p", "bubble-answer", message));
    row.appendChild(bubble);
    chatWindow.appendChild(row);
    scrollToBottom();
  }

  // --- Networking ---------------------------------------------------------

  function setBusy(busy) {
    isBusy = busy;
    if (chatInput) chatInput.disabled = busy;
    if (sendAction) sendAction.setAttribute("aria-disabled", String(busy));
  }

  function sendMessage() {
    if (!chatInput || isBusy) return;
    var question = (chatInput.value || "").trim();
    if (!question) return;

    chatInput.value = "";
    setBusy(true);
    appendUserMessage(question);
    appendThinking();

    var slowNotice = setTimeout(function () {
      var thinking = document.getElementById("thinking-bubble");
      var bubble = thinking && thinking.querySelector(".bubble-thinking");
      if (bubble) {
        bubble.classList.remove("bubble-thinking");
        bubble.textContent = "Still working — the language model is taking a moment…";
      }
    }, 6000);

    fetch(API_BASE + "/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question })
    })
      .then(function (response) {
        return response.json().then(function (body) {
          if (!response.ok) {
            throw new Error(body.error || "Request failed with status " + response.status);
          }
          return body;
        });
      })
      .then(function (data) {
        appendBotMessage(data);
      })
      .catch(function (error) {
        appendError(
          "I could not reach the FundBot API — " +
            (error && error.message ? error.message : "network error") +
            ". No answer is shown rather than a possibly outdated one. Please retry in a moment."
        );
      })
      .finally(function () {
        clearTimeout(slowNotice);
        removeThinking();
        setBusy(false);
        if (chatInput) chatInput.focus();
        renderSuggestions();
      });
  }

  function checkHealth() {
    if (!statusDot) return;
    fetch(API_BASE + "/health")
      .then(function (response) {
        return response.ok ? response.json() : Promise.reject(new Error("unhealthy"));
      })
      .then(function (data) {
        statusDot.classList.remove("status-dot-down");
        if (statusText && data.corpus) {
          statusText.textContent = data.corpus.documents + " sourced facts · Mirae Asset";
        }
      })
      .catch(function () {
        statusDot.classList.add("status-dot-down");
        if (statusText) statusText.textContent = "API unreachable";
      });
  }

  // --- Navigation ---------------------------------------------------------

  function openChat(prefillQuestion) {
    if (pageWelcome) pageWelcome.classList.remove("active");
    if (pageChat) pageChat.classList.add("active");

    renderWelcomeCard();
    renderSuggestions();

    if (prefillQuestion) {
      chatInput.value = prefillQuestion;
      sendMessage();
    } else if (chatInput) {
      setTimeout(function () {
        chatInput.focus();
      }, 100);
    }
  }

  // --- Speech input (free, browser-native; hidden where unsupported) -------

  function initSpeech() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition || !micButton) return;

    var recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    var listening = false;
    micButton.hidden = false;

    micButton.addEventListener("click", function () {
      if (listening) {
        recognition.stop();
        return;
      }
      try {
        recognition.start();
      } catch (err) {
        /* start() throws if called twice in a row; safe to ignore. */
      }
    });

    recognition.addEventListener("start", function () {
      listening = true;
      micButton.classList.add("mic-listening");
    });

    recognition.addEventListener("end", function () {
      listening = false;
      micButton.classList.remove("mic-listening");
    });

    recognition.addEventListener("result", function (event) {
      var transcript = event.results[0][0].transcript;
      chatInput.value = transcript;
      sendMessage();
    });

    recognition.addEventListener("error", function () {
      listening = false;
      micButton.classList.remove("mic-listening");
    });
  }

  // --- Modals -------------------------------------------------------------

  function initModals() {
    var backdrop = document.getElementById("modal-backdrop");
    if (!backdrop) return;

    function open(id) {
      var modal = document.getElementById(id);
      if (!modal) return;
      backdrop.classList.add("active");
      modal.classList.add("active");
      document.body.style.overflow = "hidden";
    }

    function close() {
      backdrop.classList.remove("active");
      var active = backdrop.querySelector(".modal.active");
      if (active) active.classList.remove("active");
      document.body.style.overflow = "";
    }

    // Keyed on data-modal rather than link text, so the same three modals can be
    // opened from the welcome navbar and from the chat sidebar without the label
    // wording having to match the element id.
    document.querySelectorAll("[data-modal]").forEach(function (trigger) {
      var target = "modal-" + trigger.dataset.modal;
      trigger.addEventListener("click", function () {
        open(target);
      });
      trigger.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          open(target);
        }
      });
    });

    backdrop.querySelectorAll(".modal-close, .modal-action-button").forEach(function (button) {
      button.addEventListener("click", close);
    });
    backdrop.addEventListener("click", function (event) {
      if (event.target === backdrop) close();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") close();
    });
  }

  // --- Wiring -------------------------------------------------------------

  if (sendAction) {
    sendAction.addEventListener("click", sendMessage);
    sendAction.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        sendMessage();
      }
    });
  }

  if (chatInput) {
    chatInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });
  }

  if (startButton) {
    startButton.addEventListener("click", function () {
      openChat(null);
    });
  }

  document.querySelectorAll("[data-question]").forEach(function (card) {
    card.style.cursor = "pointer";
    function fire() {
      openChat(card.dataset.question);
    }
    card.addEventListener("click", fire);
    card.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        fire();
      }
    });
  });

  if (chatWindow) {
    // Delegated so chips rendered later still work.
    chatWindow.addEventListener("click", function (event) {
      var chip = event.target.closest(".welcome-chip");
      if (!chip || isBusy) return;
      chatInput.value = chip.dataset.chipQuestion;
      sendMessage();
    });
  }

  initModals();
  initSpeech();
  checkHealth();
})();

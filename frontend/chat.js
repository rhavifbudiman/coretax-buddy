'use strict';

const toggleBtn = document.getElementById('chat-toggle-btn');
const chatPanel = document.getElementById('chat-panel');
const closeBtn  = document.getElementById('chat-close-btn');
const messagesEl = document.getElementById('chat-messages');
const inputEl   = document.getElementById('chat-input');
const sendBtn   = document.getElementById('chat-send-btn');

let isOpen = false;
let firstOpen = true;
let history = [];   // [{role:'user'|'assistant', content:'...'}]

// ── Toggle open/close ──────────────────────────────────────────────────────
function openChat() {
  isOpen = true;
  chatPanel.classList.add('open');
  toggleBtn.classList.add('active');
  if (firstOpen) {
    firstOpen = false;
    appendMessage('assistant', 'Halo! Saya Pajak Assistant 👋\n\nSaya bisa membantu Anda dengan pertanyaan seputar:\n• Lapor SPT Tahunan\n• NPPN (Norma Penghitungan Penghasilan Neto)\n• Bayar pajak & kode billing\n\nSilakan tanyakan apa saja!');
  }
  setTimeout(() => inputEl.focus(), 200);
}

function closeChat() {
  isOpen = false;
  chatPanel.classList.remove('open');
  toggleBtn.classList.remove('active');
}

toggleBtn.addEventListener('click', () => isOpen ? closeChat() : openChat());
closeBtn.addEventListener('click', closeChat);

// ── Send message ───────────────────────────────────────────────────────────
async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = '';
  inputEl.disabled = true;
  sendBtn.disabled = true;

  appendMessage('user', text);
  history.push({ role: 'user', content: text });

  const typingEl = showTyping();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: history.slice(-6)   // last 6 turns max
      })
    });

    removeTyping(typingEl);

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    appendMessage('assistant', data.reply, data.sources || []);
    history.push({ role: 'assistant', content: data.reply });

  } catch (err) {
    removeTyping(typingEl);
    appendMessage('error', 'Maaf, terjadi kesalahan. Silakan coba lagi.\n(' + err.message + ')');
  } finally {
    inputEl.disabled = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

sendBtn.addEventListener('click', sendMessage);
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// ── Render helpers ─────────────────────────────────────────────────────────
function appendMessage(role, text, sources = []) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role === 'error' ? 'error' : role}`;

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  bubble.textContent = text;
  wrapper.appendChild(bubble);

  if (sources.length > 0) {
    const tagsDiv = document.createElement('div');
    tagsDiv.className = 'source-tags';
    sources.forEach(src => {
      const tag = document.createElement('span');
      tag.className = 'source-tag';
      tag.textContent = src.replace('.md', '').replace(/_/g, ' ');
      tagsDiv.appendChild(tag);
    });
    wrapper.appendChild(tagsDiv);
  }

  const timeEl = document.createElement('div');
  timeEl.className = 'message-time';
  timeEl.textContent = now();
  wrapper.appendChild(timeEl);

  messagesEl.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function showTyping() {
  const wrapper = document.createElement('div');
  wrapper.className = 'message assistant';
  const indicator = document.createElement('div');
  indicator.className = 'typing-indicator';
  indicator.innerHTML = '<span></span><span></span><span></span>';
  wrapper.appendChild(indicator);
  messagesEl.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function removeTyping(el) {
  if (el && el.parentNode) el.parentNode.removeChild(el);
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function now() {
  return new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}

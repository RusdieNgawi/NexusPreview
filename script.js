// --- KONFIGURASI ---
const STORAGE_KEY = 'xanadium_chat_history';
let currentSessionId = Date.now();
let chatData = [];

// Cache DOM Elements
const els = {
    welcome: document.getElementById('welcome-screen'),
    chatWrap: document.getElementById('chat-wrapper'),
    msgList: document.getElementById('messages-list'),
    brand: document.getElementById('brand-small'),
    input: document.getElementById('user-input'),
    sendBtn: document.getElementById('send-btn'),
    menu: document.getElementById('dropdown-menu'),
    sidebar: document.getElementById('history-sidebar'),
    overlay: document.getElementById('overlay'),
    fileIn: document.getElementById('file-input'),
    previewBox: document.getElementById('preview-box'),
    imgPreview: document.getElementById('img-preview'),
    historyList: document.getElementById('history-list-container')
};

// --- LOGOUT & CHAT BARU ---
function logout() {
    window.location.href = '/logout';
}

function startNewChat() {
    if (chatData.length > 0) saveCurrentSessionToHistory();
    currentSessionId = Date.now();
    chatData = [];
    
    // Reset UI
    els.msgList.innerHTML = '';
    els.chatWrap.classList.add('opacity-0', 'translate-y-10');
    els.welcome.classList.remove('hidden-force');
    setTimeout(() => {
        els.welcome.style.opacity = '1';
        els.welcome.style.transform = 'translateY(0)';
    }, 50);
    els.brand.classList.remove('translate-y-0');
    els.brand.classList.add('opacity-0', '-translate-y-5');
    els.input.value = '';
    removeImage();
    closeAllMenus();
}

// --- HISTORY SYSTEM ---
function saveCurrentSessionToHistory() {
    const history = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    const firstMsg = chatData.find(m => m.role === 'user');
    const title = firstMsg ? (firstMsg.text.substring(0, 30) + '...') : 'Percakapan Baru';
    
    const sessionObj = {
        id: currentSessionId,
        title: title,
        timestamp: new Date().toLocaleString(),
        messages: chatData
    };
    
    const index = history.findIndex(h => h.id === currentSessionId);
    if (index > -1) history[index] = sessionObj;
    else history.unshift(sessionObj);
    
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

function loadHistoryToSidebar() {
    const history = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    els.historyList.innerHTML = '';

    if (history.length === 0) {
        els.historyList.innerHTML = '<p class="text-center text-gray-600 text-xs mt-10">Belum ada riwayat.</p>';
        return;
    }

    history.forEach(session => {
        const item = document.createElement('div');
        item.className = 'p-3 mb-2 rounded-lg bg-white/5 hover:bg-blue-600/20 cursor-pointer border border-transparent hover:border-blue-500/30 transition group';
        item.onclick = () => loadSession(session.id);
        item.innerHTML = `
            <div class="flex justify-between items-center">
                <span class="text-sm text-gray-300 font-medium truncate w-4/5">${session.title}</span>
                <button onclick="event.stopPropagation(); deleteSession(${session.id})" class="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition"><i class="fa-solid fa-trash text-xs"></i></button>
            </div>
            <p class="text-[10px] text-gray-500 mt-1">${session.timestamp}</p>
        `;
        els.historyList.appendChild(item);
    });
}

function loadSession(id) {
    const history = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    const session = history.find(s => s.id === id);
    if (session) {
        currentSessionId = session.id;
        chatData = session.messages;
        switchToChatUI();
        els.msgList.innerHTML = '';
        chatData.forEach(msg => els.msgList.appendChild(createBubble(msg.role === 'user', msg.text, msg.img)));
        closeAllMenus();
    }
}

function deleteSession(id) {
    if(!confirm('Hapus chat ini?')) return;
    const history = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    const newHistory = history.filter(s => s.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory));
    if (id === currentSessionId) startNewChat();
    else loadHistoryToSidebar();
}

// --- UI HELPERS ---
function toggleMenu() {
    if (els.menu.classList.contains('opacity-0')) {
        els.menu.classList.remove('opacity-0', 'pointer-events-none', 'scale-95');
        els.menu.classList.add('scale-100');
        els.overlay.classList.remove('hidden');
    } else closeAllMenus();
}

function toggleHistory() {
    loadHistoryToSidebar();
    els.menu.classList.add('opacity-0', 'pointer-events-none', 'scale-95');
    if (els.sidebar.classList.contains('translate-x-full')) {
        els.sidebar.classList.remove('translate-x-full');
        els.overlay.classList.remove('hidden');
    } else closeAllMenus();
}

function closeAllMenus() {
    els.menu.classList.add('opacity-0', 'pointer-events-none', 'scale-95');
    els.sidebar.classList.add('translate-x-full');
    els.overlay.classList.add('hidden');
}

function switchToChatUI() {
    els.welcome.style.opacity = '0';
    els.welcome.style.transform = 'translateY(-20px)';
    setTimeout(() => els.welcome.classList.add('hidden-force'), 500);
    els.chatWrap.classList.remove('opacity-0', 'translate-y-10');
    els.brand.classList.remove('opacity-0', '-translate-y-5');
    els.brand.classList.add('translate-y-0');
}

// --- MESSAGING ---
function createBubble(isUser, text, imgData = null) {
    const div = document.createElement('div');
    div.className = `flex gap-4 ${isUser ? 'flex-row-reverse' : ''} animate-slide-up mb-6`;
    const userPic = document.getElementById('user-avatar-source')?.src || '';
    const avatar = isUser ? `<img src="${userPic}" class="w-8 h-8 rounded-full border border-white/10 shrink-0">` : `<div class="w-8 h-8 rounded-full bg-blue-900/30 flex items-center justify-center shrink-0 border border-blue-500/30"><span class="text-xanadium-blue font-bold text-sm">X</span></div>`;
    const imgHtml = imgData ? `<img src="${imgData}" class="max-w-[280px] rounded-lg mb-3 border border-gray-700 shadow-lg">` : '';
    const style = isUser ? "bg-[#1e293b] border border-blue-900/40 text-gray-200 rounded-2xl rounded-tr-sm px-5 py-3" : "text-gray-300 w-full prose prose-invert prose-p:text-gray-300 max-w-none pt-1";
    div.innerHTML = `${avatar}<div class="flex flex-col max-w-[85%] ${isUser ? 'items-end' : 'items-start'}"><div class="${style}">${imgHtml}<div class="msg-content leading-relaxed">${isUser ? text : marked.parse(text)}</div></div></div>`;
    return div;
}

async function sendMessage() {
    const text = els.input.value.trim();
    const file = els.fileIn.files[0];
    if (!text && !file) return;
    
    els.sendBtn.disabled = true;
    switchToChatUI();
    
    let imgSrc = els.imgPreview.src !== window.location.href ? els.imgPreview.src : null;
    els.msgList.appendChild(createBubble(true, text, imgSrc));
    chatData.push({ role: 'user', text: text, img: imgSrc });
    saveCurrentSessionToHistory();
    
    els.input.value = '';
    removeImage();
    els.chatWrap.scrollTo({ top: els.chatWrap.scrollHeight, behavior: 'smooth' });
    
    const loadId = 'load-' + Date.now();
    const loader = document.createElement('div');
    loader.id = loadId;
    loader.className = "flex gap-4 animate-pulse mb-6";
    loader.innerHTML = `<div class="w-8 h-8 rounded-full bg-blue-900/30 flex items-center justify-center border border-blue-500/30">...</div><div class="text-gray-500 text-sm flex items-center">Mengetik...</div>`;
    els.msgList.appendChild(loader);
    els.chatWrap.scrollTop = els.chatWrap.scrollHeight;
    
    const fd = new FormData();
    fd.append('message', text);
    if (file) fd.append('file', file);
    
    try {
        const res = await fetch('/chat', { method: 'POST', body: fd });
        const data = await res.json();
        document.getElementById(loadId).remove();
        
        const botMsg = data.response || "Error.";
        els.msgList.appendChild(createBubble(false, botMsg));
        chatData.push({ role: 'assistant', text: botMsg, img: null });
        saveCurrentSessionToHistory();
    } catch (e) {
        document.getElementById(loadId)?.remove();
        els.msgList.appendChild(createBubble(false, "Koneksi terputus."));
    } finally {
        els.sendBtn.disabled = false;
        els.input.focus();
        els.chatWrap.scrollTop = els.chatWrap.scrollHeight;
    }
}

function autoResize(el) { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px'; }
function handleEnter(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }
function handleFile(input) { if (input.files[0]) { const r = new FileReader(); r.onload = e => { els.imgPreview.src = e.target.result; els.previewBox.classList.remove('hidden'); }; r.readAsDataURL(input.files[0]); } }
function removeImage() { els.fileIn.value = ''; els.previewBox.classList.add('hidden'); els.imgPreview.src = ''; }

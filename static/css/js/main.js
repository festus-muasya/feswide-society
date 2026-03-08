// ADVANCED MODAL SYSTEM
function showModal(type, title, message) {
    const overlay = document.getElementById('global-modal');
    const header = document.getElementById('modal-header');

    // Reset classes
    header.className = 'modal-header';
    if (type === 'success') header.classList.add('success');
    if (type === 'error') header.classList.add('error');

    document.getElementById('modal-title').innerText = title;
    document.getElementById('modal-message').innerText = message;

    overlay.classList.add('active');
}

function closeModal() {
    document.getElementById('global-modal').classList.remove('active');
}

// UI LOGIC
function switchTab(view) {
    document.getElementById('store').style.display = view == 'store' ? 'block' : 'none';
    document.getElementById('dash').style.display = view == 'dash' ? 'block' : 'none';
    document.getElementById('b-store').className = view == 'store' ? 'active' : '';
    document.getElementById('b-dash').className = view == 'dash' ? 'active' : '';
}

function searchModules() {
    let q = document.getElementById('sInput').value.toLowerCase();
    let cards = document.querySelectorAll('#store .card');
    cards.forEach(c => {
        let title = c.querySelector('.card-title').innerText.toLowerCase();
        c.style.display = title.includes(q) ? 'flex' : 'none';
    });
}

// API REQUESTS
async function submitUpload() {
    let file = document.getElementById('pfile').files[0];
    let pname = document.getElementById('pname').value;
    let pmpesa = document.getElementById('pmpesa').value;

    if (!file || !pname || !pmpesa) {
        showModal('error', 'VALIDATION FAILED', 'ALL FIELDS AND A PDF FILE ARE REQUIRED.');
        return;
    }

    let fd = new FormData();
    fd.append('file', file);
    fd.append('platform', document.getElementById('pform').value);
    fd.append('project_name', pname);
    fd.append('mpesa_number', pmpesa);

    try {
        let res = await fetch('/upload-answer', { method: 'POST', body: fd });
        let data = await res.json();

        if (data.status === 'success') {
            showModal('success', 'UPLOAD COMPLETE', data.message);
            document.getElementById('pname').value = '';
            document.getElementById('pfile').value = '';
        } else {
            showModal('error', 'UPLOAD FAILED', data.message);
        }
    } catch (e) {
        showModal('error', 'SYSTEM ERROR', 'SECURE CONNECTION FAILED. PLEASE TRY AGAIN.');
    }
}

async function submitVote() {
    let n = document.getElementById('vname').value;
    if (!n) { showModal('error', 'VALIDATION FAILED', 'PLEASE ENTER A TARGET PROJECT NAME.'); return; }

    try {
        await fetch('/request-project', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_name: n, platform: 'VOTE' }) });
        showModal('success', 'REQUEST LOGGED', 'FESWIDE SOCIETY WILL CRACK THIS MODULE IN LESS THAN 48 HOURS.');
        document.getElementById('vname').value = '';
    } catch (e) {
        showModal('error', 'SYSTEM ERROR', 'FAILED TO LOG REQUEST.');
    }
}

// CHATBOT LOGIC
function toggleChat() {
    let c = document.getElementById('chatbot');
    c.style.display = c.style.display == 'flex' ? 'none' : 'flex';
}

async function sendChatMsg() {
    let input = document.getElementById('cIn');
    let body = document.getElementById('chatBody');
    if (!input.value) return;

    body.innerHTML += `<div style="background:var(--white); color:#000; padding:10px; border:1px solid var(--border); width:85%; align-self:flex-end; margin-left:auto;"><b>YOU:</b> ${input.value}</div>`;

    let query = input.value;
    input.value = '';
    body.scrollTop = body.scrollHeight;

    try {
        let res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: query }) });
        let data = await res.json();

        setTimeout(() => {
            body.innerHTML += `<div style="background:var(--navy); color:var(--white); padding:10px; border:1px solid var(--border); width:85%;"><b>FAITH:</b> ${data.reply}</div>`;
            body.scrollTop = body.scrollHeight;
        }, 500);
    } catch (e) {
        body.innerHTML += `<div style="background:var(--maroon); color:var(--white); padding:10px; border:1px solid var(--border); width:85%;"><b>SYS:</b> CONNECTION ERROR.</div>`;
    }
}

// SECURITY
document.onkeydown = function (e) {
    if (e.keyCode == 123) return false; // F12
    if (e.ctrlKey && e.shiftKey && (e.keyCode == 73 || e.keyCode == 74)) return false; // Ctrl+Shift+I/J
    if (e.ctrlKey && e.keyCode == 85) return false; // Ctrl+U
};
// ==========================================
// 1. ADVANCED MODAL SYSTEM (REPLACES ALERTS)
// ==========================================
let pollInterval;

function showModal(title, body, showInput = false, confirmCallback = null) {
    document.getElementById('mTitle').innerText = title;
    document.getElementById('mBody').innerText = body;

    const input = document.getElementById('mInput');
    const confirmBtn = document.getElementById('mConfirm');

    if (showInput) {
        input.style.display = 'block';
        input.value = '';
    } else {
        input.style.display = 'none';
    }

    if (confirmCallback) {
        confirmBtn.style.display = 'block';
        confirmBtn.onclick = confirmCallback;
    } else {
        confirmBtn.style.display = 'none';
    }

    document.getElementById('global-modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('global-modal').style.display = 'none';
    if (pollInterval) clearInterval(pollInterval);
}

// ==========================================
// 2. UI NAVIGATION & SEARCH
// ==========================================
function switchTab(view) {
    document.getElementById('store').style.display = view === 'store' ? 'block' : 'none';
    document.getElementById('dash').style.display = view === 'dash' ? 'block' : 'none';
    document.getElementById('b-store').className = view === 'store' ? 'active' : '';
    document.getElementById('b-dash').className = view === 'dash' ? 'active' : '';
}

function searchModules() {
    let q = document.getElementById('sInput').value.toLowerCase();
    let cards = document.querySelectorAll('#store .card');
    cards.forEach(c => {
        let t = c.querySelector('.card-title').innerText.toLowerCase();
        c.style.display = t.includes(q) ? 'flex' : 'none';
    });
}

// ==========================================
// 3. M-PESA STK PUSH LOGIC
// ==========================================
function initiatePayment(productId, productName) {
    showModal('M-PESA CHECKOUT', `Enter your M-Pesa phone number to purchase ${productName}.`, true, async () => {
        let phone = document.getElementById('mInput').value;
        if (!phone) { showModal('ERROR', 'Phone number is required.'); return; }

        document.getElementById('mConfirm').style.display = 'none';
        document.getElementById('mInput').style.display = 'none';
        document.getElementById('mTitle').innerText = 'PROCESSING...';
        document.getElementById('mBody').innerText = 'Triggering STK Push. Check your phone for the PIN prompt...';

        try {
            let res = await fetch('/stk-push', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone: phone, product_id: productId })
            });
            let data = await res.json();

            if (data.status === 'success') {
                document.getElementById('mBody').innerText = 'Awaiting payment confirmation. Please do not close this window...';
                pollPayment(data.checkout_id);
            } else {
                showModal('ERROR', data.error);
            }
        } catch (e) {
            showModal('ERROR', 'Connection Error.');
        }
    });
}

function pollPayment(checkoutId) {
    pollInterval = setInterval(async () => {
        let res = await fetch('/check-payment/' + checkoutId);
        let data = await res.json();

        if (data.status === 'Paid') {
            clearInterval(pollInterval);
            document.getElementById('mTitle').innerText = 'PAYMENT SUCCESSFUL';
            document.getElementById('mBody').innerHTML = `
                <p style="margin-bottom:15px; color:#155724; font-weight:bold;">Transaction Verified!</p> 
                <a href="/secure-download/${data.download_token}" target="_blank" style="background:var(--navy); color:white; padding:12px 20px; text-decoration:none; border: 2px solid var(--black); display:inline-block; font-weight:bold; text-transform:uppercase;">DOWNLOAD SECURE PDF</a> 
                <p style="font-size:11px; margin-top:10px; color:var(--maroon); font-weight:bold;">This secure link expires after 3 uses to prevent sharing.</p>
            `;
        } else if (data.status === 'Failed') {
            clearInterval(pollInterval);
            showModal('PAYMENT FAILED', 'Transaction cancelled or failed.');
        }
    }, 3000); // Checks the database every 3 seconds
}

// ==========================================
// 4. CONTRIBUTOR UPLOADS & VOTING
// ==========================================
async function submitUpload() {
    let file = document.getElementById('pfile').files[0];
    let pname = document.getElementById('pname').value;
    let pmpesa = document.getElementById('pmpesa').value;

    if (!file || !pname || !pmpesa) {
        showModal('VALIDATION ERROR', 'All fields and a PDF document are required.');
        return;
    }

    let fd = new FormData();
    fd.append('file', file);
    fd.append('platform', document.getElementById('pform').value);
    fd.append('project_name', pname);
    fd.append('mpesa_number', pmpesa);

    try {
        let res = await fetch('/upload-answer', { method: 'POST', body: fd });
        let d = await res.json();
        showModal(d.status === 'success' ? 'SUCCESS' : 'ERROR', d.message);

        if (d.status === 'success') {
            document.getElementById('pname').value = '';
            document.getElementById('pfile').value = '';
        }
    } catch (e) {
        showModal('ERROR', 'Connection failed. Please check your internet.');
    }
}

async function submitVote() {
    let n = document.getElementById('vname').value;
    if (!n) { showModal('ERROR', 'Please enter a target project name.'); return; }

    try {
        await fetch('/request-project', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_name: n, platform: 'REQUEST' }) });
        showModal('REQUEST LOGGED', 'Feswide Society engineers will process this module in less than 48 hours.');
        document.getElementById('vname').value = '';
    } catch (e) {
        showModal('ERROR', 'Failed to log request.');
    }
}

// ==========================================
// 5. AGENT FAITH (CHATBOT LOGIC)
// ==========================================
function toggleChat() {
    let c = document.getElementById('chatbot');
    c.style.display = c.style.display === 'flex' ? 'none' : 'flex';
}

async function sendChatMsg() {
    let i = document.getElementById('cIn');
    let b = document.getElementById('chatBody');
    if (!i.value) return;

    let q = i.value;
    b.innerHTML += `<div class="chat-bubble chat-user">${q}</div>`;
    i.value = '';
    b.scrollTop = b.scrollHeight;

    try {
        let res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: q }) });
        let d = await res.json();

        setTimeout(() => {
            b.innerHTML += `<div class="chat-bubble chat-bot">${d.reply}</div>`;
            b.scrollTop = b.scrollHeight;
        }, 600);
    } catch (e) {
        setTimeout(() => {
            b.innerHTML += `<div class="chat-bubble chat-bot" style="color:var(--maroon); font-weight:bold;">NETWORK ERROR.</div>`;
            b.scrollTop = b.scrollHeight;
        }, 600);
    }
}

// ==========================================
// 6. EXTREME SECURITY: PREVENT INSPECTION
// ==========================================
function preventInspect(e) {
    e.preventDefault();
    alert("Access Denied");
    return false;
}

document.addEventListener('keydown', function (e) {
    // Blocks F12, Ctrl+Shift+I, Ctrl+Shift+J, and Ctrl+U
    if (e.keyCode == 123 || (e.ctrlKey && e.shiftKey && (e.keyCode == 73 || e.keyCode == 74)) || (e.ctrlKey && e.keyCode == 85)) {
        e.preventDefault();
        alert("Access Denied");
        return false;
    }
});
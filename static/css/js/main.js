let pollInterval;
let currentProductId = null;

// --- SEARCH FUNCTIONALITY ---
function searchModules() {
    let input = document.getElementById('sInput').value.toLowerCase();
    let cards = document.getElementsByClassName('card');

    for (let i = 0; i < cards.length; i++) {
        let title = cards[i].querySelector('.card-title').innerText.toLowerCase();
        if (title.includes(input)) {
            cards[i].style.display = "flex";
        } else {
            cards[i].style.display = "none";
        }
    }
}

// --- TAB SWITCHING ---
function switchTab(view) {
    document.getElementById('store').style.display = view === 'store' ? 'block' : 'none';
    document.getElementById('dash').style.display = view === 'dash' ? 'block' : 'none';
    document.getElementById('b-store').className = view === 'store' ? 'active' : '';
    document.getElementById('b-dash').className = view === 'dash' ? 'active' : '';
}

// --- CHATBOT FUNCTIONALITY ---
function toggleChat() {
    let c = document.getElementById('chatbot');
    c.style.display = (c.style.display === 'block') ? 'none' : 'block';
}

async function sendChatMsg() {
    let input = document.getElementById('cIn');
    let body = document.getElementById('chatBody');
    if (!input.value) return;

    let text = input.value;
    body.innerHTML += `<p style="text-align:right; background:#e0e0e0; padding:8px; border-radius:5px;">${text}</p>`;
    input.value = '';
    body.scrollTop = body.scrollHeight;

    try {
        let res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text }) });
        let data = await res.json();
        setTimeout(() => {
            body.innerHTML += `<p style="color:#002b5e; font-weight:bold;">Agent Faith: ${data.reply}</p>`;
            body.scrollTop = body.scrollHeight;
        }, 800);
    } catch (e) {
        body.innerHTML += `<p style="color:red;">Network Error.</p>`;
    }
}

// --- PAYMENT MODAL LOGIC ---
function showPaymentModal(productId, productName) {
    currentProductId = productId;

    document.getElementById('mTitle').innerText = productName;
    document.getElementById('mBody').innerHTML = `
        <label style="font-weight:bold; font-size:14px;">Select Network Provider:</label>
        <select id="networkSelect" onchange="handleNetworkChange()" style="width: 100%; padding: 12px; margin-top: 5px; margin-bottom: 15px; border: 1px solid #ccc;">
            <option value="safaricom">Safaricom (M-Pesa)</option>
            <option value="airtel">Airtel Money</option>
        </select>
        
        <div id="safaricom-flow">
            <input type="text" id="mInput" placeholder="Safaricom Number (07XXXXXXXX)" style="width: 100%; padding: 12px; border: 1px solid #ccc; box-sizing: border-box;">
        </div>
        
        <div id="airtel-flow" style="display: none; background: #f8f9fa; padding: 15px; border: 1px solid #ccc; font-size: 13px;">
            <p style="color: #8b0000; font-weight: bold; margin-top:0;">STK Push is unsupported for Airtel.</p>
            <p>1. Go to Airtel Money -> Send Money -> To M-Pesa.</p>
            <p>2. Till: <b>Use Feswide Till</b></p>
            <input type="text" id="aInput" placeholder="Enter Airtel Transaction ID" style="width: 100%; padding: 12px; margin-top:10px; border: 1px solid #ccc; box-sizing: border-box;">
        </div>
    `;

    let confirmBtn = document.getElementById('mConfirm');
    confirmBtn.style.display = 'block';
    confirmBtn.innerText = "PROCEED TO SECURE CHECKOUT";
    confirmBtn.onclick = processPaymentRoute;

    document.getElementById('global-modal').style.display = 'flex';
}

function handleNetworkChange() {
    let network = document.getElementById('networkSelect').value;
    document.getElementById('safaricom-flow').style.display = network === 'safaricom' ? 'block' : 'none';
    document.getElementById('airtel-flow').style.display = network === 'airtel' ? 'block' : 'none';
}

function closeModal() {
    document.getElementById('global-modal').style.display = 'none';
    if (pollInterval) clearInterval(pollInterval);
}

function processPaymentRoute() {
    let network = document.getElementById('networkSelect').value;
    if (network === 'safaricom') {
        let phone = document.getElementById('mInput').value;
        if (!phone) return alert('Safaricom number required.');
        triggerSTKPush(phone);
    } else {
        let txnId = document.getElementById('aInput').value;
        if (!txnId) return alert('Transaction ID required.');
        verifyManualPayment(txnId);
    }
}

async function triggerSTKPush(phone) {
    document.getElementById('mConfirm').style.display = 'none';
    document.getElementById('mBody').innerHTML = `<p style="font-weight:bold; color: #002b5e;">TRIGGERING SECURE STK PUSH...</p>`;

    try {
        let res = await fetch('/stk-push', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: phone, product_id: currentProductId })
        });
        let data = await res.json();

        if (data.status === 'success') {
            document.getElementById('mBody').innerHTML += '<p>Awaiting PIN confirmation on your device...</p>';
            pollPayment(data.checkout_id);
        } else {
            document.getElementById('mBody').innerHTML = `<p style="color: #8b0000; font-weight: bold;">ERROR: ${data.error}</p>`;
        }
    } catch (e) {
        document.getElementById('mBody').innerHTML = `<p style="color: #8b0000;">Network Error connecting to Safaricom.</p>`;
    }
}

async function verifyManualPayment(txnId) {
    document.getElementById('mConfirm').style.display = 'none';
    document.getElementById('mBody').innerHTML = `<p>Verifying Airtel Transaction <b>${txnId}</b>...</p>`;

    try {
        await fetch('/verify-manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ txn_id: txnId, product_id: currentProductId })
        });
        document.getElementById('mBody').innerHTML = `<p style="font-weight:bold; color: #002b5e;">VERIFICATION LOGGED.</p><p>A Feswide sub-admin will review and approve your transaction shortly.</p>`;
    } catch (e) {
        document.getElementById('mBody').innerHTML = `<p style="color: #8b0000;">Failed to send verification.</p>`;
    }
}

function pollPayment(checkoutId) {
    pollInterval = setInterval(async () => {
        let res = await fetch('/check-payment/' + checkoutId);
        let data = await res.json();

        if (data.status === 'Paid') {
            clearInterval(pollInterval);
            document.getElementById('mTitle').innerText = 'PAYMENT SUCCESSFUL';
            document.getElementById('mBody').innerHTML = `
                <a href="/secure-download/${data.download_token}" target="_blank" style="background: #155724; color: white; padding: 15px; text-decoration: none; display: block; font-weight: bold; text-align: center; font-size: 16px;">DOWNLOAD SECURE PDF</a>
                <p style="font-size: 12px; margin-top: 15px; color: #8b0000; font-weight: bold; text-align: center;">SECURITY NOTICE: This link is mathematically bound to your current IP address.</p>
            `;
        } else if (data.status === 'Failed') {
            clearInterval(pollInterval);
            document.getElementById('mBody').innerHTML = `<p style="color: #8b0000; font-weight: bold;">Transaction Failed or Cancelled.</p>`;
        }
    }, 4000);
}

// --- UPLOAD LOGIC ---
async function submitUpload() {
    let fileInput = document.getElementById('pfile');
    if (!fileInput.files[0]) return alert("Please select a PDF file.");

    let fd = new FormData();
    fd.append('file', fileInput.files[0]);
    fd.append('platform', document.getElementById('pform').value);
    fd.append('project_name', document.getElementById('pname').value);
    fd.append('mpesa_number', document.getElementById('pmpesa').value);

    let btn = document.querySelector('.upload-section button');
    let originalText = btn.innerText;
    btn.innerText = "UPLOADING...";

    try {
        let res = await fetch('/upload-answer', { method: 'POST', body: fd });
        let d = await res.json();
        alert(d.message);
    } catch (e) {
        alert("Upload failed. Check your network.");
    } finally {
        btn.innerText = originalText;
    }
}

// --- ANTI-INSPECTION OPSEC ---
document.addEventListener('contextmenu', event => event.preventDefault());
document.addEventListener('keydown', function (e) {
    if (e.keyCode == 123 || (e.ctrlKey && e.shiftKey && (e.keyCode == 73 || e.keyCode == 74)) || (e.ctrlKey && (e.keyCode == 85 || e.keyCode == 83))) {
        e.preventDefault();
        alert("Feswide Society: Inspection Disabled.");
        return false;
    }
});
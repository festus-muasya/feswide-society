let pollInterval; let currentProductId = null; let currentProductName = null;

function showPaymentModal(productId, productName) {
    currentProductId = productId; currentProductName = productName;
    document.getElementById('mTitle').innerText = `PURCHASE: ${productName}`;
    document.getElementById('mBody').innerHTML = `
        <select id="networkSelect" style="width: 100%; padding: 10px; margin-bottom: 15px; border: 2px solid var(--black); font-weight: bold; font-family: monospace;" onchange="handleNetworkChange()">
            <option value="safaricom">Safaricom (M-Pesa)</option>
            <option value="airtel">Airtel Money</option>
        </select>
        <div id="safaricom-flow"><input type="text" id="mInput" placeholder="Safaricom Number (07XXXXXXXX)" style="width: 100%; padding: 10px; border: 2px solid var(--black); font-family: monospace;"></div>
        <div id="airtel-flow" style="display: none; background: #f8f9fa; padding: 15px; border: 1px solid #ccc; font-size: 13px;">
            <p style="color: darkred; font-weight: bold;">STK Push unsupported for Airtel.</p>
            <p>1. Go to Airtel Money -> Send Money -> To M-Pesa.</p>
            <p>2. Till: <b>174379</b> | Amount: <b>KES 999</b></p>
            <input type="text" id="aInput" placeholder="Airtel Transaction ID" style="width: 100%; padding: 10px; margin-top:5px; border: 2px solid var(--black); font-family: monospace;">
        </div>
    `;
    document.getElementById('mConfirm').style.display = 'block';
    document.getElementById('mConfirm').onclick = processPaymentRoute;
    document.getElementById('global-modal').style.display = 'flex';
}

function handleNetworkChange() {
    let network = document.getElementById('networkSelect').value;
    document.getElementById('safaricom-flow').style.display = network === 'safaricom' ? 'block' : 'none';
    document.getElementById('airtel-flow').style.display = network === 'airtel' ? 'block' : 'none';
}

function closeModal() { document.getElementById('global-modal').style.display = 'none'; if (pollInterval) clearInterval(pollInterval); }

function processPaymentRoute() {
    let network = document.getElementById('networkSelect').value;
    if (network === 'safaricom') {
        let phone = document.getElementById('mInput').value;
        if (!phone) return alert('Number required.');
        triggerSTKPush(phone);
    } else {
        let txnId = document.getElementById('aInput').value;
        if (!txnId) return alert('Transaction ID required.');
        verifyManualPayment(txnId);
    }
}

async function triggerSTKPush(phone) {
    document.getElementById('mConfirm').style.display = 'none';
    document.getElementById('mBody').innerHTML = `<p style="font-weight:bold;">TRIGGERING SECURE STK PUSH...</p>`;
    try {
        let res = await fetch('/stk-push', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: phone, product_id: currentProductId }) });
        let data = await res.json();
        if (data.status === 'success') {
            document.getElementById('mBody').innerHTML += '<p>Awaiting PIN confirmation...</p>';
            pollPayment(data.checkout_id);
        } else { document.getElementById('mBody').innerHTML = `<p style="color:red;">ERROR: ${data.error}</p>`; }
    } catch (e) { document.getElementById('mBody').innerHTML = `<p style="color:red;">Network Error.</p>`; }
}

async function verifyManualPayment(txnId) {
    document.getElementById('mConfirm').style.display = 'none';
    document.getElementById('mBody').innerHTML = `<p>Verifying Airtel Transaction <b>${txnId}</b>...</p>`;
    try {
        await fetch('/verify-manual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ txn_id: txnId, product_id: currentProductId }) });
        document.getElementById('mBody').innerHTML = `<p style="font-weight:bold;">VERIFICATION LOGGED. A Feswide sub-admin will review shortly.</p>`;
    } catch (e) { document.getElementById('mBody').innerHTML = `<p style="color:red;">Failed to send.</p>`; }
}

function pollPayment(checkoutId) {
    pollInterval = setInterval(async () => {
        let res = await fetch('/check-payment/' + checkoutId);
        let data = await res.json();
        if (data.status === 'Paid') {
            clearInterval(pollInterval);
            document.getElementById('mTitle').innerText = 'PAYMENT SUCCESSFUL';
            document.getElementById('mBody').innerHTML = `<a href="/secure-download/${data.download_token}" target="_blank" style="background:#0a192f; color:white; padding:12px; text-decoration:none; border: 2px solid black; display:inline-block; font-weight:bold;">DOWNLOAD SECURE PDF</a><p style="font-size:11px; margin-top:10px; color:darkred;">SECURITY NOTICE: Link is strictly bound to your current IP address.</p>`;
        } else if (data.status === 'Failed') {
            clearInterval(pollInterval);
            document.getElementById('mBody').innerHTML = `<p style="color:red;">Transaction Failed.</p>`;
        }
    }, 4000);
}

function switchTab(view) {
    document.getElementById('store').style.display = view === 'store' ? 'block' : 'none';
    document.getElementById('dash').style.display = view === 'dash' ? 'block' : 'none';
}

async function submitUpload() {
    let fd = new FormData();
    fd.append('file', document.getElementById('pfile').files[0]);
    fd.append('platform', document.getElementById('pform').value);
    fd.append('project_name', document.getElementById('pname').value);
    fd.append('mpesa_number', document.getElementById('pmpesa').value);
    let res = await fetch('/upload-answer', { method: 'POST', body: fd });
    let d = await res.json(); alert(d.message);
}

document.addEventListener('contextmenu', event => event.preventDefault());
document.addEventListener('keydown', function (e) {
    if (e.keyCode == 123 || (e.ctrlKey && e.shiftKey && (e.keyCode == 73 || e.keyCode == 74)) || (e.ctrlKey && (e.keyCode == 85 || e.keyCode == 83))) {
        e.preventDefault(); alert("Security Block."); return false;
    }
});
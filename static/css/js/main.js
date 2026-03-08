function toggleView(view) {
    if (view === 'store') {
        document.getElementById('mainStore').style.display = 'block';
        document.getElementById('userDashboard').style.display = 'none';
    } else {
        document.getElementById('mainStore').style.display = 'none';
        document.getElementById('userDashboard').style.display = 'block';
    }
}

function toggleChat() {
    const chat = document.getElementById('chatbot-faith');
    chat.style.bottom = chat.style.bottom === '-320px' ? '20px' : '-320px';
}

function searchProjects() {
    const query = document.getElementById('searchInput').value;
    alert(`Searching Feswide database for: "${query}"...`);
}

async function uploadFile() {
    const fileInput = document.getElementById('answerUpload');
    if (fileInput.files.length === 0) {
        alert("Please select a PDF file first.");
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
        const response = await fetch('/upload-answer', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        alert(data.message);
    } catch (error) {
        alert("Upload failed. Please try again.");
    }
}

async function initiateSTK(itemName, amount) {
    let phone = prompt("Enter M-Pesa Number (e.g., 2547XXXXXXXX):");
    if (!phone) return;

    document.getElementById('displayItemName').innerText = itemName;
    document.getElementById('displayAmount').innerText = "KES " + amount;
    document.getElementById('paymentOverlay').style.display = 'flex';
    document.getElementById('stkMessage').innerText = "Requesting STK Push...";

    try {
        const response = await fetch('/pay-stk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: phone, item: itemName, amount: amount })
        });
        const data = await response.json();

        if (data.status === "PROMPTED") {
            document.getElementById('stkMessage').innerText = "Awaiting PIN Entry on your phone...";
            // Here you would typically start polling the server to check if Daraja callback arrived
        }
    } catch (err) {
        alert("Connection failed.");
        closeOverlay();
    }
}

function closeOverlay() {
    document.getElementById('paymentOverlay').style.display = 'none';
}
console.log("script.js loaded successfully");

const API_BASE_URL = "http://127.0.0.1:8000";
let activeReviewTransaction = null;
let editModalTrigger = null;

function formatCurrency(value) {
  return "₹" + Number(value || 0).toLocaleString("en-IN");
}

function appendTableCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value ?? "";
  row.appendChild(cell);
}

function createReviewButton(label, className, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

async function reviewTransaction(transactionId, decision, corrections = {}) {
  const response = await fetch(`${API_BASE_URL}/transactions/${transactionId}/review`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, ...corrections })
  });

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.detail || "Unable to review transaction");
  }

  return result;
}

async function approveReviewTransaction(transactionId) {
  try {
    await reviewTransaction(transactionId, "approve");
    await refreshDashboard();
  } catch (error) {
    alert(error.message);
  }
}

async function rejectReviewTransaction(transactionId) {
  if (!window.confirm("Reject this transaction? It will remain in the audit history.")) {
    return;
  }

  try {
    await reviewTransaction(transactionId, "reject");
    await refreshDashboard();
  } catch (error) {
    alert(error.message);
  }
}

async function editAndApproveReviewTransaction(transaction) {
  openEditReviewModal(transaction, document.activeElement);
}

function getEditModalElements() {
  return {
    modal: document.getElementById("editTransactionModal"),
    merchant: document.getElementById("editMerchant"),
    amount: document.getElementById("editAmount"),
    category: document.getElementById("editCategory"),
    error: document.getElementById("editModalError")
  };
}

function setEditModalError(message = "") {
  const { error } = getEditModalElements();
  error.textContent = message;
  error.hidden = !message;
}

function openEditReviewModal(transaction, trigger) {
  const { modal, merchant, amount, category } = getEditModalElements();
  activeReviewTransaction = transaction;
  editModalTrigger = trigger;
  merchant.value = transaction.merchant || "";
  amount.value = transaction.amount || "";
  category.value = transaction.category || "Others";
  setEditModalError();
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  merchant.focus();
}

function closeEditReviewModal() {
  const { modal } = getEditModalElements();
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  activeReviewTransaction = null;
  setEditModalError();
  if (editModalTrigger instanceof HTMLElement) {
    editModalTrigger.focus();
  }
  editModalTrigger = null;
}

async function saveEditedReviewTransaction() {
  if (!activeReviewTransaction) return;

  const { merchant, amount, category } = getEditModalElements();
  const correctedMerchant = merchant.value.trim();
  const correctedCategory = category.value.trim();
  const correctedAmount = Number(amount.value);

  if (!correctedMerchant || !correctedCategory) {
    setEditModalError("Merchant and category are required.");
    return;
  }

  if (!Number.isFinite(correctedAmount) || correctedAmount <= 0) {
    setEditModalError("Amount must be a positive number.");
    return;
  }

  try {
    await reviewTransaction(activeReviewTransaction._id, "approve", {
      merchant: correctedMerchant,
      amount: correctedAmount,
      category: correctedCategory,
      review_note: "Corrected during dashboard review"
    });
    closeEditReviewModal();
    await refreshDashboard();
  } catch (error) {
    setEditModalError(error.message);
  }
}

function downloadCsv() {
  window.open(`${API_BASE_URL}/export/csv`, "_blank");
}

function downloadJson() {
  window.open(`${API_BASE_URL}/export/json`, "_blank");
}

async function loadDashboardSummary() {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
    const result = await response.json();

    console.log("Dashboard summary response:", result);

    if (result.status !== "success") {
      console.error("Failed to load dashboard summary", result);
      return;
    }

    const summary = result.summary;

    document.getElementById("totalSpend").textContent = formatCurrency(summary.total_spend);
    document.getElementById("totalCredit").textContent = formatCurrency(summary.total_credit);
    document.getElementById("netBalance").textContent = formatCurrency(summary.net_balance);
    document.getElementById("totalTransactions").textContent = summary.total_transactions;
    document.getElementById("reviewRequired").textContent = summary.review_required_count + summary.review_log_count;
    document.getElementById("ignoredEmails").textContent = summary.ignored_email_count;

    renderCategorySummary(summary.category_summary);
    renderTopMerchants(summary.top_merchants);
    renderMonthlyTrend(summary.monthly_trend);
    renderSourceSummary(summary.source_summary);
    renderBillsDueCard(summary.bills_due_count);

  } catch (error) {
    console.error("Dashboard summary error:", error);
  }
}

function renderCategorySummary(categorySummary) {
  const container = document.getElementById("categorySummary");
  container.innerHTML = "";

  const entries = Object.entries(categorySummary || {});

  if (entries.length === 0) {
    container.innerHTML = "<p>No category data yet.</p>";
    return;
  }

  entries.forEach(([category, amount]) => {
    const item = document.createElement("div");
    item.className = "badge";
    item.textContent = `${category}: ${formatCurrency(amount)}`;
    container.appendChild(item);
  });
}

function renderTopMerchants(topMerchants) {
  const container = document.getElementById("topMerchants");
  container.innerHTML = "";

  if (!topMerchants || topMerchants.length === 0) {
    container.innerHTML = "<p>No merchant data yet.</p>";
    return;
  }

  topMerchants.forEach((item) => {
    const row = document.createElement("p");
    row.textContent = `${item.merchant}: ${formatCurrency(item.amount)}`;
    container.appendChild(row);
  });
}

function renderMonthlyTrend(monthlyTrend) {
  const container = document.getElementById("monthlyTrend");
  container.innerHTML = "";

  if (!monthlyTrend || monthlyTrend.length === 0) {
    container.innerHTML = "<p>No monthly data yet.</p>";
    return;
  }

  const maxAmount = Math.max(...monthlyTrend.map(item => item.amount), 1);

  monthlyTrend.forEach((item) => {
    const width = (item.amount / maxAmount) * 100;
    const row = document.createElement("div");
    row.className = "bar-row";
    const label = document.createElement("div");
    label.className = "bar-label";
    label.textContent = `${item.month}: ${formatCurrency(item.amount)}`;
    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${width}%`;
    track.appendChild(fill);
    row.append(label, track);
    container.appendChild(row);
  });
}

function renderSourceSummary(sourceSummary) {
  const container = document.getElementById("sourceSummary");
  container.innerHTML = "";

  const entries = Object.entries(sourceSummary || {});

  if (entries.length === 0) {
    container.innerHTML = "<p>No source data yet.</p>";
    return;
  }

  entries.forEach(([source, count]) => {
    const item = document.createElement("div");
    item.className = "badge";
    item.textContent = `${source}: ${count}`;
    container.appendChild(item);
  });
}

function renderBillsDueCard(count) {
  const container = document.getElementById("billsDueSummary");

  container.innerHTML = `
    <p><strong>${count || 0}</strong> bills are currently not marked as paid.</p>
  `;
}

async function loadLatestTransactions() {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/latest-transactions?limit=20`);
    const result = await response.json();

    console.log("Latest transactions response:", result);

    const table = document.getElementById("transactionsTable");
    table.innerHTML = "";

    if (result.status !== "success") {
      table.innerHTML = "<tr><td colspan='6'>Failed to load transactions</td></tr>";
      return;
    }

    if (!result.transactions || result.transactions.length === 0) {
      table.innerHTML = "<tr><td colspan='6'>No transactions found</td></tr>";
      return;
    }

    result.transactions.forEach((tx) => {
      const row = document.createElement("tr");
      appendTableCell(row, tx.date);
      appendTableCell(row, tx.merchant);
      appendTableCell(row, formatCurrency(tx.amount));
      appendTableCell(row, tx.category);
      appendTableCell(row, tx.source);
      appendTableCell(row, tx.status || "confirmed");
      table.appendChild(row);
    });

  } catch (error) {
    console.error("Latest transactions error:", error);
  }
}

async function loadGmailLogs() {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/gmail-logs?limit=20`);
    const result = await response.json();

    console.log("Gmail logs response:", result);

    const table = document.getElementById("gmailLogsTable");
    table.innerHTML = "";

    if (result.status !== "success") {
      table.innerHTML = "<tr><td colspan='3'>Failed to load Gmail logs</td></tr>";
      return;
    }

    if (!result.logs || result.logs.length === 0) {
      table.innerHTML = "<tr><td colspan='3'>No Gmail logs found</td></tr>";
      return;
    }

    result.logs.forEach((log) => {
      const row = document.createElement("tr");
      appendTableCell(row, log.subject);
      appendTableCell(row, log.status);
      appendTableCell(row, log.reason || log.error);
      table.appendChild(row);
    });

  } catch (error) {
    console.error("Gmail logs error:", error);
  }
}

async function loadReviewRequired() {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/review-required?limit=20`);
    const result = await response.json();

    console.log("Review required response:", result);

    const table = document.getElementById("reviewRequiredTable");
    table.innerHTML = "";

    if (result.status !== "success") {
      table.innerHTML = "<tr><td colspan='5'>Failed to load review data</td></tr>";
      return;
    }

    if (result.transactions) {
      result.transactions.forEach((tx) => {
        const row = document.createElement("tr");
        appendTableCell(row, "Transaction");
        appendTableCell(row, tx.merchant);
        appendTableCell(row, formatCurrency(tx.amount));
        appendTableCell(row, tx.ai_reason || tx.status);
        const actions = document.createElement("td");
        actions.append(
          createReviewButton("Approve", "review-approve", () => approveReviewTransaction(tx._id)),
          createReviewButton("Edit & Approve", "review-edit", () => editAndApproveReviewTransaction(tx)),
          createReviewButton("Reject", "review-reject", () => rejectReviewTransaction(tx._id))
        );
        row.appendChild(actions);
        table.appendChild(row);
      });
    }

    if (result.logs) {
      result.logs.forEach((log) => {
        const row = document.createElement("tr");
        appendTableCell(row, "Email Log");
        appendTableCell(row, log.subject);
        appendTableCell(row, "-");
        appendTableCell(row, log.reason || log.status);
        appendTableCell(row, "Review from Gmail log is not implemented yet");
        table.appendChild(row);
      });
    }

    if (!table.children.length) {
      table.innerHTML = "<tr><td colspan='5'>No review required items.</td></tr>";
    }

  } catch (error) {
    console.error("Review required error:", error);
  }
}

async function addTransaction() {
  try {
    const transaction = {
      date: document.getElementById("date").value,
      merchant: document.getElementById("merchant").value,
      amount: Number(document.getElementById("amount").value),
      category: document.getElementById("category").value,
      source: document.getElementById("source").value
    };

    const response = await fetch(`${API_BASE_URL}/transactions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(transaction)
    });

    const result = await response.json();

    alert(result.message || "Transaction added");

    await refreshDashboard();

  } catch (error) {
    console.error("Add transaction error:", error);
    alert("Failed to add transaction");
  }
}

async function syncGmailTransactions() {
  try {
    document.getElementById("syncResult").textContent = "Syncing Gmail...";

    const response = await fetch(`${API_BASE_URL}/gmail/sync?max_results=10`, {
      method: "POST"
    });

    const result = await response.json();

    console.log("Gmail sync response:", result);

    document.getElementById("syncResult").textContent = JSON.stringify(result, null, 2);

    await refreshDashboard();

  } catch (error) {
    console.error("Gmail sync error:", error);
    document.getElementById("syncResult").textContent = String(error);
  }
}

async function uploadReceipt() {
  try {
    const fileInput = document.getElementById("receiptFile");
    const resultBox = document.getElementById("receiptUploadResult");

    if (!fileInput.files || fileInput.files.length === 0) {
      alert("Please select a receipt image first.");
      return;
    }

    resultBox.textContent = "Uploading and processing receipt...";

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    const response = await fetch(`${API_BASE_URL}/receipts/upload`, {
      method: "POST",
      body: formData
    });

    const result = await response.json();

    resultBox.textContent = JSON.stringify(result, null, 2);

    await refreshDashboard();

  } catch (error) {
    console.error("Receipt upload error:", error);
    document.getElementById("receiptUploadResult").textContent = String(error);
  }
}

async function uploadBill() {
  try {
    const fileInput = document.getElementById("billFile");
    const resultBox = document.getElementById("billUploadResult");

    if (!fileInput.files || fileInput.files.length === 0) {
      alert("Please select a bill image first.");
      return;
    }

    resultBox.textContent = "Uploading and processing bill...";

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    const response = await fetch(`${API_BASE_URL}/bills/upload`, {
      method: "POST",
      body: formData
    });

    const result = await response.json();

    resultBox.textContent = JSON.stringify(result, null, 2);

    await refreshDashboard();

  } catch (error) {
    console.error("Bill upload error:", error);
    document.getElementById("billUploadResult").textContent = String(error);
  }
}

async function loadBills() {
  try {
    const response = await fetch(`${API_BASE_URL}/bills`);
    const result = await response.json();

    const table = document.getElementById("billsTable");
    table.innerHTML = "";

    if (result.status !== "success") {
      table.innerHTML = "<tr><td colspan='7'>Failed to load bills</td></tr>";
      return;
    }

    if (!result.bills || result.bills.length === 0) {
      table.innerHTML = "<tr><td colspan='7'>No bills uploaded yet</td></tr>";
      return;
    }

    result.bills.forEach((bill) => {
      const row = document.createElement("tr");
      appendTableCell(row, bill.provider);
      appendTableCell(row, bill.bill_type);
      appendTableCell(row, formatCurrency(bill.amount));
      appendTableCell(row, bill.due_date);
      appendTableCell(row, bill.status);
      appendTableCell(row, bill.ai_confidence);
      appendTableCell(row, bill.file_name);
      table.appendChild(row);
    });

  } catch (error) {
    console.error("Load bills error:", error);
  }
}

async function loadReceipts() {
  try {
    const response = await fetch(`${API_BASE_URL}/receipts`);
    const result = await response.json();

    const table = document.getElementById("receiptsTable");
    table.innerHTML = "";

    if (result.status !== "success") {
      table.innerHTML = "<tr><td colspan='4'>Failed to load receipts</td></tr>";
      return;
    }

    if (!result.receipts || result.receipts.length === 0) {
      table.innerHTML = "<tr><td colspan='4'>No receipts uploaded yet</td></tr>";
      return;
    }

    result.receipts.forEach((receipt) => {
      const preview = receipt.ocr_text
        ? receipt.ocr_text.substring(0, 120)
        : "";

      const row = document.createElement("tr");
      appendTableCell(row, receipt.transaction_id);
      appendTableCell(row, receipt.file_name);
      appendTableCell(row, receipt.status);
      appendTableCell(row, preview);
      table.appendChild(row);
    });

  } catch (error) {
    console.error("Load receipts error:", error);
  }
}

async function refreshDashboard() {
  await loadDashboardSummary();
  await loadLatestTransactions();
  await loadGmailLogs();
  await loadBills();
  await loadReceipts();
  await loadReviewRequired();
}

document.getElementById("closeEditModalBtn").addEventListener("click", closeEditReviewModal);
document.getElementById("cancelEditBtn").addEventListener("click", closeEditReviewModal);
document.getElementById("saveEditBtn").addEventListener("click", saveEditedReviewTransaction);
document.getElementById("editTransactionModal").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) closeEditReviewModal();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && activeReviewTransaction) closeEditReviewModal();
});

refreshDashboard();

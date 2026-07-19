import { useEffect, useState } from "react";
import type { FormEvent } from "react";

const navigation = ["Dashboard", "Transactions", "Reports", "Settings", "Help"];
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const TRANSACTIONS_PAGE_SIZE = 20;

type DashboardSummary = {
  total_spend: number;
  total_credit: number;
  net_balance: number;
  total_transactions: number;
  review_required_count: number;
  review_log_count: number;
  top_merchants: Array<{ merchant: string; amount: number }>;
  category_summary: Record<string, number>;
  monthly_trend: Array<{ month: string; amount: number }>;
};

type ReviewTransaction = {
  _id: string;
  merchant: string;
  amount: number;
  category: string;
  ai_reason?: string;
};

type TransactionRecord = {
  _id: string;
  date: string;
  merchant: string;
  amount: number;
  category: string;
  status?: string;
  review_decision?: string;
  review_note?: string;
  reviewed_at?: string;
};

type AIConfiguration = {
  provider: string;
  model: string;
  configured: boolean;
  supported_providers: string[];
};

type BillDue = {
  _id: string;
  provider: string;
  bill_type: string;
  amount: number;
  due_date?: string;
  status: string;
};

type GmailLog = {
  _id: string;
  subject?: string;
  status: string;
  reason?: string;
  error?: string;
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);

export default function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("theme") !== "light");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryError, setSummaryError] = useState("");
  const [reviewTransactions, setReviewTransactions] = useState<ReviewTransaction[]>([]);
  const [reviewError, setReviewError] = useState("");
  const [reviewingId, setReviewingId] = useState("");
  const [editingTransaction, setEditingTransaction] = useState<ReviewTransaction | null>(null);
  const [editMerchant, setEditMerchant] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [transactionStatus, setTransactionStatus] = useState("");
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [transactionsError, setTransactionsError] = useState("");
  const [transactionsPage, setTransactionsPage] = useState(0);
  const [transactionRefresh, setTransactionRefresh] = useState(0);
  const [newDate, setNewDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [newMerchant, setNewMerchant] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [transactionMessage, setTransactionMessage] = useState("");
  const [addingTransaction, setAddingTransaction] = useState(false);
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [receiptStatus, setReceiptStatus] = useState("");
  const [uploadingReceipt, setUploadingReceipt] = useState(false);
  const [billFile, setBillFile] = useState<File | null>(null);
  const [billStatus, setBillStatus] = useState("");
  const [uploadingBill, setUploadingBill] = useState(false);
  const [billsDue, setBillsDue] = useState<BillDue[]>([]);
  const [billsDueTotal, setBillsDueTotal] = useState(0);
  const [billsDueError, setBillsDueError] = useState("");
  const [billsRefresh, setBillsRefresh] = useState(0);
  const [syncStatus, setSyncStatus] = useState("");
  const [syncingGmail, setSyncingGmail] = useState(false);
  const [gmailLogs, setGmailLogs] = useState<GmailLog[]>([]);
  const [gmailLogsError, setGmailLogsError] = useState("");
  const [logsRefresh, setLogsRefresh] = useState(0);
  const [aiConfiguration, setAiConfiguration] = useState<AIConfiguration | null>(null);
  const [aiStatus, setAiStatus] = useState("");
  const [testingAI, setTestingAI] = useState(false);
  const maxMonthlySpend = Math.max(1, ...(summary?.monthly_trend.map((item) => item.amount) ?? []));

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? "dark" : "light";
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  useEffect(() => {
    if (activePage !== "Dashboard" && activePage !== "Reports") return;

    let cancelled = false;
    setSummaryError("");
    fetch(`${API_BASE_URL}/dashboard/summary`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load dashboard data");
        if (!cancelled) setSummary(result.summary);
      })
      .catch((error: Error) => !cancelled && setSummaryError(error.message));

    return () => { cancelled = true; };
  }, [activePage]);

  useEffect(() => {
    if (activePage !== "Dashboard") return;

    fetch(`${API_BASE_URL}/dashboard/bills-due?limit=10`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load bills due");
        setBillsDue(result.bills ?? []);
        setBillsDueTotal(result.total_due_amount ?? 0);
      })
      .catch((error: Error) => setBillsDueError(error.message));
  }, [activePage, billsRefresh]);

  useEffect(() => {
    if (activePage !== "Dashboard") return;

    fetch(`${API_BASE_URL}/dashboard/gmail-logs?limit=10`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load Gmail logs");
        setGmailLogs(result.logs ?? []);
      })
      .catch((error: Error) => setGmailLogsError(error.message));
  }, [activePage, logsRefresh]);

  useEffect(() => {
    if (activePage !== "Transactions") return;

    const parameters = new URLSearchParams({ limit: String(TRANSACTIONS_PAGE_SIZE), skip: String(transactionsPage * TRANSACTIONS_PAGE_SIZE) });
    if (transactionStatus) parameters.set("status", transactionStatus);
    setTransactionsError("");
    fetch(`${API_BASE_URL}/transactions?${parameters}`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load transactions");
        setTransactions(result.transactions ?? []);
      })
      .catch((error: Error) => setTransactionsError(error.message));
  }, [activePage, transactionStatus, transactionsPage, transactionRefresh]);

  useEffect(() => {
    if (activePage !== "Settings") return;

    setAiStatus("");
    fetch(`${API_BASE_URL}/ai/configuration`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load AI settings");
        setAiConfiguration(result);
      })
      .catch((error: Error) => setAiStatus(error.message));
  }, [activePage]);

  useEffect(() => {
    if (activePage !== "Dashboard") return;

    fetch(`${API_BASE_URL}/dashboard/review-required?limit=10`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load review queue");
        setReviewTransactions(result.transactions ?? []);
      })
      .catch((error: Error) => setReviewError(error.message));
  }, [activePage]);

  async function reviewTransaction(
    transactionId: string,
    decision: "approve" | "reject",
    corrections: Record<string, string | number> = {},
  ) {
    setReviewingId(transactionId);
    setReviewError("");
    try {
      const response = await fetch(`${API_BASE_URL}/transactions/${transactionId}/review`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, ...corrections }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Unable to save review decision");
      setReviewTransactions((items) => items.filter((item) => item._id !== transactionId));
      const summaryResponse = await fetch(`${API_BASE_URL}/dashboard/summary`);
      const summaryResult = await summaryResponse.json();
      if (summaryResponse.ok && summaryResult.status === "success") setSummary(summaryResult.summary);
      return true;
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Unable to save review decision");
      return false;
    } finally {
      setReviewingId("");
    }
  }

  function openEditReview(transaction: ReviewTransaction) {
    setEditingTransaction(transaction);
    setEditMerchant(transaction.merchant);
    setEditAmount(String(transaction.amount));
    setEditCategory(transaction.category);
    setReviewError("");
  }

  async function saveEditedReview() {
    if (!editingTransaction) return;
    const amount = Number(editAmount);
    if (!editMerchant.trim() || !editCategory.trim() || !Number.isFinite(amount) || amount <= 0) {
      setReviewError("Merchant, category, and a positive amount are required.");
      return;
    }
    const saved = await reviewTransaction(editingTransaction._id, "approve", {
      merchant: editMerchant.trim(), amount, category: editCategory.trim(), review_note: "Corrected during dashboard review",
    });
    if (saved) setEditingTransaction(null);
  }

  async function testAIProvider() {
    setTestingAI(true);
    setAiStatus("Testing provider...");
    try {
      const response = await fetch(`${API_BASE_URL}/ai/test`, { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Provider test failed");
      setAiStatus(`Connected: ${result.provider} (${result.model})`);
    } catch (error) {
      setAiStatus(error instanceof Error ? error.message : "Provider test failed");
    } finally {
      setTestingAI(false);
    }
  }

  async function addTransaction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const amount = Number(newAmount);
    if (!newDate || !newMerchant.trim() || !newCategory.trim() || !Number.isFinite(amount) || amount <= 0) {
      setTransactionMessage("Enter a date, merchant, category, and positive amount.");
      return;
    }
    setAddingTransaction(true);
    setTransactionMessage("");
    try {
      const response = await fetch(`${API_BASE_URL}/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: newDate, merchant: newMerchant.trim(), amount, category: newCategory.trim(), source: "manual" }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Unable to add transaction");
      setTransactionMessage("Transaction added successfully.");
      setNewMerchant(""); setNewAmount(""); setNewCategory("");
      setTransactionsPage(0);
      setTransactionRefresh((value) => value + 1);
    } catch (error) {
      setTransactionMessage(error instanceof Error ? error.message : "Unable to add transaction");
    } finally {
      setAddingTransaction(false);
    }
  }

  async function uploadReceipt() {
    if (!receiptFile) {
      setReceiptStatus("Choose a receipt image first.");
      return;
    }
    setUploadingReceipt(true);
    setReceiptStatus("Uploading and analyzing receipt...");
    try {
      const formData = new FormData();
      formData.append("file", receiptFile);
      const response = await fetch(`${API_BASE_URL}/receipts/upload`, { method: "POST", body: formData });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Receipt upload failed");
      setReceiptStatus(`Receipt processed: ${result.merchant} · ${formatCurrency(result.amount)} · ${result.review_status}`);
      setReceiptFile(null);
      const summaryResponse = await fetch(`${API_BASE_URL}/dashboard/summary`);
      const summaryResult = await summaryResponse.json();
      if (summaryResponse.ok && summaryResult.status === "success") setSummary(summaryResult.summary);
    } catch (error) {
      setReceiptStatus(error instanceof Error ? error.message : "Receipt upload failed");
    } finally {
      setUploadingReceipt(false);
    }
  }

  async function uploadBill() {
    if (!billFile) {
      setBillStatus("Choose a bill image first.");
      return;
    }
    setUploadingBill(true);
    setBillStatus("Uploading and analyzing bill...");
    try {
      const formData = new FormData();
      formData.append("file", billFile);
      const response = await fetch(`${API_BASE_URL}/bills/upload`, { method: "POST", body: formData });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Bill upload failed");
      setBillStatus(`Bill processed: ${result.provider} · ${formatCurrency(result.amount)} · ${result.review_status}`);
      setBillFile(null);
      setBillsRefresh((value) => value + 1);
    } catch (error) {
      setBillStatus(error instanceof Error ? error.message : "Bill upload failed");
    } finally {
      setUploadingBill(false);
    }
  }

  async function syncGmail() {
    setSyncingGmail(true);
    setSyncStatus("Syncing Gmail...");
    try {
      const response = await fetch(`${API_BASE_URL}/gmail/sync?max_results=10`, { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Gmail sync failed");
      const syncSummary = result.summary;
      setSyncStatus(`Sync complete: ${syncSummary.inserted_transactions} added, ${syncSummary.review_required} pending review, ${syncSummary.ignored_emails} ignored.`);
      setLogsRefresh((value) => value + 1);
      const summaryResponse = await fetch(`${API_BASE_URL}/dashboard/summary`);
      const summaryResult = await summaryResponse.json();
      if (summaryResponse.ok && summaryResult.status === "success") setSummary(summaryResult.summary);
    } catch (error) {
      setSyncStatus(error instanceof Error ? error.message : "Gmail sync failed");
    } finally {
      setSyncingGmail(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`} aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">₹</span>
          <span>FinSight</span>
        </div>

        <nav>
          {navigation.map((item) => (
            <button
              className={`nav-item ${activePage === item ? "nav-active" : ""}`}
              key={item}
              onClick={() => {
                setActivePage(item);
                setSidebarOpen(false);
              }}
              type="button"
            >
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">Private by design<br />Your finance data stays yours.</div>
      </aside>

      {sidebarOpen && <button className="backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close navigation" />}

      <main className="content">
        <header className="topbar">
          <button className="menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation">☰</button>
          <div>
            <p className="page-kicker">Personal finance workspace</p>
            <h1>{activePage}</h1>
          </div>
          <button className="theme-toggle" onClick={() => setDarkMode((value) => !value)} type="button">
            {darkMode ? "Light mode" : "Dark mode"}
          </button>
        </header>

        {activePage === "Dashboard" && <>
        <section className="welcome-card" aria-labelledby="welcome-title">
          <div>
            <p className="eyebrow">Modern finance, one place</p>
            <h2 id="welcome-title">Your financial picture, clearly organized.</h2>
            <p>{summaryError ? `Dashboard data unavailable: ${summaryError}` : "Live data is loaded from your FastAPI backend."}</p>
          </div>
          <div className="insight-pill"><span aria-hidden="true">✦</span> AI-ready</div>
        </section>

        <section className="metric-card" aria-labelledby="gmail-sync-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Email ingestion</p>
          <h2 id="gmail-sync-title">Sync Gmail transactions</h2>
          <p style={{ marginTop: 10 }}>Import recent transaction alerts from your connected Gmail account.</p>
          <button className="theme-toggle" disabled={syncingGmail} onClick={syncGmail} style={{ marginTop: 18 }} type="button">{syncingGmail ? "Syncing..." : "Sync Gmail"}</button>
          {syncStatus && <p role="status" style={{ marginTop: 16 }}>{syncStatus}</p>}
        </section>

        <section className="metric-card" aria-labelledby="gmail-logs-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Sync activity</p>
          <h2 id="gmail-logs-title">Gmail processing logs</h2>
          {gmailLogsError && <p role="alert">{gmailLogsError}</p>}
          {!gmailLogsError && gmailLogs.length === 0 && <p>No Gmail processing logs yet.</p>}
          <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
            {gmailLogs.map((log) => (
              <article key={log._id} style={{ padding: 14, border: "1px solid #e0e7f1", borderRadius: 12 }}>
                <strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{log.subject || "No subject"}</strong>
                <p style={{ marginTop: 6 }}>{log.status}{log.reason || log.error ? ` · ${log.reason || log.error}` : ""}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="placeholder-grid" aria-label="Dashboard preview">
          {[
            ["Total spend", summary ? formatCurrency(summary.total_spend) : "Loading..."],
            ["Total credit", summary ? formatCurrency(summary.total_credit) : "Loading..."],
            ["Net balance", summary ? formatCurrency(summary.net_balance) : "Loading..."],
            ["Transactions", summary ? String(summary.total_transactions) : "Loading..."],
            ["Pending review", summary ? String(summary.review_required_count + summary.review_log_count) : "Loading..."],
          ].map(([label, value]) => (
            <article className="metric-card" key={label}>
              <p>{label}</p><strong>{value}</strong>
            </article>
          ))}
        </section>

        <section className="metric-card" aria-labelledby="top-merchants-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Spending patterns</p>
          <h2 id="top-merchants-title">Top merchants</h2>
          {!summary && <p>Loading merchants...</p>}
          {summary?.top_merchants.length === 0 && <p>No merchant data yet.</p>}
          <ol style={{ margin: "20px 0 0", paddingLeft: 22, display: "grid", gap: 10 }}>
            {summary?.top_merchants.slice(0, 5).map((merchant) => (
              <li key={merchant.merchant} style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                <span>{merchant.merchant}</span>
                <strong>{formatCurrency(merchant.amount)}</strong>
              </li>
            ))}
          </ol>
        </section>

        <section className="metric-card" aria-labelledby="category-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Where your money goes</p>
          <h2 id="category-title">Spend by category</h2>
          {!summary && <p>Loading categories...</p>}
          {summary && Object.keys(summary.category_summary).length === 0 && <p>No category data yet.</p>}
          <ol style={{ margin: "20px 0 0", paddingLeft: 22, display: "grid", gap: 10 }}>
            {summary && Object.entries(summary.category_summary)
              .sort(([, firstAmount], [, secondAmount]) => secondAmount - firstAmount)
              .map(([category, amount]) => (
                <li key={category} style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                  <span>{category}</span>
                  <strong>{formatCurrency(amount)}</strong>
                </li>
              ))}
          </ol>
        </section>

        <section className="metric-card" aria-labelledby="review-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Human verification</p>
          <h2 id="review-title">Review required</h2>
          {reviewError && <p role="alert">{reviewError}</p>}
          {!reviewError && reviewTransactions.length === 0 && <p>No pending transaction reviews.</p>}
          <div style={{ display: "grid", gap: 12, marginTop: 20 }}>
            {reviewTransactions.map((transaction) => (
              <article key={transaction._id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: 16, border: "1px solid #e0e7f1", borderRadius: 12 }}>
                <div>
                  <strong>{transaction.merchant}</strong>
                  <p style={{ margin: "5px 0 0", color: "#64748b" }}>{formatCurrency(transaction.amount)} · {transaction.category} · {transaction.ai_reason || "Needs confirmation"}</p>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="theme-toggle" disabled={reviewingId === transaction._id} onClick={() => reviewTransaction(transaction._id, "approve")} type="button">Approve</button>
                  <button className="theme-toggle" disabled={reviewingId === transaction._id} onClick={() => openEditReview(transaction)} type="button">Edit & Approve</button>
                  <button className="theme-toggle" disabled={reviewingId === transaction._id} onClick={() => reviewTransaction(transaction._id, "reject")} type="button">Reject</button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="metric-card" aria-labelledby="bills-due-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Upcoming payments</p>
          <h2 id="bills-due-title">Bills due</h2>
          <p style={{ marginTop: 10 }}>Total due: <span style={{ color: "inherit", fontWeight: 800 }}>{formatCurrency(billsDueTotal)}</span></p>
          {billsDueError && <p role="alert">{billsDueError}</p>}
          {!billsDueError && billsDue.length === 0 && <p>No unpaid bills found.</p>}
          <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
            {billsDue.map((bill) => (
              <article key={bill._id} style={{ display: "flex", justifyContent: "space-between", gap: 16, padding: 14, border: "1px solid #e0e7f1", borderRadius: 12 }}>
                <div><strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{bill.provider}</strong><p style={{ marginTop: 5 }}>{bill.bill_type}{bill.due_date ? ` · Due ${bill.due_date}` : ""}</p></div>
                <span style={{ fontWeight: 800 }}>{formatCurrency(bill.amount)}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="metric-card" aria-labelledby="export-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Your data</p>
          <h2 id="export-title">Export transactions</h2>
          <p style={{ marginTop: 10 }}>Download a copy of your transaction data for analysis or backup.</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 20 }}>
            <button className="theme-toggle" onClick={() => window.open(`${API_BASE_URL}/export/csv`, "_blank", "noopener,noreferrer")} type="button">Download CSV</button>
            <button className="theme-toggle" onClick={() => window.open(`${API_BASE_URL}/export/json`, "_blank", "noopener,noreferrer")} type="button">Download JSON</button>
          </div>
        </section>

        <section className="metric-card" aria-labelledby="receipt-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">OCR and AI enrichment</p>
          <h2 id="receipt-title">Upload receipt</h2>
          <p style={{ marginTop: 10 }}>Upload a JPEG, PNG, or WebP receipt image for extraction and review.</p>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, marginTop: 20 }}>
            <input accept="image/jpeg,image/png,image/webp" onChange={(event) => setReceiptFile(event.target.files?.[0] ?? null)} type="file" />
            <button className="theme-toggle" disabled={!receiptFile || uploadingReceipt} onClick={uploadReceipt} type="button">{uploadingReceipt ? "Processing..." : "Upload receipt"}</button>
          </div>
          {receiptStatus && <p role="status" style={{ marginTop: 16 }}>{receiptStatus}</p>}
        </section>

        <section className="metric-card" aria-labelledby="bill-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Bill management</p>
          <h2 id="bill-title">Upload bill</h2>
          <p style={{ marginTop: 10 }}>Upload a JPEG, PNG, or WebP bill image for provider, amount, and due-date extraction.</p>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, marginTop: 20 }}>
            <input accept="image/jpeg,image/png,image/webp" onChange={(event) => setBillFile(event.target.files?.[0] ?? null)} type="file" />
            <button className="theme-toggle" disabled={!billFile || uploadingBill} onClick={uploadBill} type="button">{uploadingBill ? "Processing..." : "Upload bill"}</button>
          </div>
          {billStatus && <p role="status" style={{ marginTop: 16 }}>{billStatus}</p>}
        </section>
        </>}

        {activePage === "Transactions" && (
          <section className="metric-card" aria-labelledby="transactions-title">
            <p className="eyebrow">Review history and records</p>
            <h2 id="transactions-title">Transactions</h2>
            <form onSubmit={addTransaction} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginTop: 24 }}>
              <label>Date<input required type="date" value={newDate} onChange={(event) => setNewDate(event.target.value)} /></label>
              <label>Merchant<input required value={newMerchant} onChange={(event) => setNewMerchant(event.target.value)} /></label>
              <label>Amount<input required min="0.01" step="0.01" type="number" value={newAmount} onChange={(event) => setNewAmount(event.target.value)} /></label>
              <label>Category<input required value={newCategory} onChange={(event) => setNewCategory(event.target.value)} /></label>
              <div style={{ alignSelf: "end" }}><button className="theme-toggle" disabled={addingTransaction} type="submit">{addingTransaction ? "Adding..." : "Add transaction"}</button></div>
            </form>
            {transactionMessage && <p role="status">{transactionMessage}</p>}
            <label style={{ display: "inline-grid", gap: 6, marginTop: 20 }}>
              Status filter
              <select value={transactionStatus} onChange={(event) => { setTransactionStatus(event.target.value); setTransactionsPage(0); }}>
                <option value="">All transactions</option>
                <option value="review_required">Pending review</option>
                <option value="confirmed">Confirmed</option>
                <option value="rejected">Rejected</option>
              </select>
            </label>
            {transactionsError && <p role="alert">{transactionsError}</p>}
            {!transactionsError && transactions.length === 0 && <p>No transactions found for this filter.</p>}
            <div style={{ overflowX: "auto", marginTop: 20 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
                <thead><tr><th>Date</th><th>Merchant</th><th>Amount</th><th>Category</th><th>Status</th><th>Review history</th></tr></thead>
                <tbody>{transactions.map((transaction) => {
                  const status = transaction.status || "confirmed";
                  const colors = status === "rejected" ? ["#fee2e2", "#991b1b"] : status === "review_required" ? ["#fef3c7", "#92400e"] : ["#dcfce7", "#166534"];
                  return <tr key={transaction._id}>
                    <td>{transaction.date}</td><td>{transaction.merchant}</td><td>{formatCurrency(transaction.amount)}</td><td>{transaction.category}</td>
                    <td><span style={{ display: "inline-block", padding: "4px 8px", borderRadius: 999, color: colors[1], background: colors[0], fontSize: ".75rem", fontWeight: 800 }}>{status.replace("_", " ")}</span></td>
                    <td>{transaction.review_decision ? `${transaction.review_decision}${transaction.review_note ? ` — ${transaction.review_note}` : ""}` : "Not reviewed"}</td>
                  </tr>;
                })}</tbody>
              </table>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 20 }}>
              <button className="theme-toggle" disabled={transactionsPage === 0} onClick={() => setTransactionsPage((page) => page - 1)} type="button">Previous</button>
              <span>Page {transactionsPage + 1}</span>
              <button className="theme-toggle" disabled={transactions.length < TRANSACTIONS_PAGE_SIZE} onClick={() => setTransactionsPage((page) => page + 1)} type="button">Next</button>
            </div>
          </section>
        )}

        {activePage === "Reports" && (
          <section className="metric-card" aria-labelledby="reports-title">
            <p className="eyebrow">Monthly spending</p>
            <h2 id="reports-title">Spend trend</h2>
            {summaryError && <p role="alert">{summaryError}</p>}
            {!summary && !summaryError && <p>Loading report...</p>}
            {summary?.monthly_trend.length === 0 && <p>No monthly spending data yet.</p>}
            <div style={{ display: "grid", gap: 16, marginTop: 24 }}>
              {summary?.monthly_trend.map((item) => (
                <div key={item.month}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 16, marginBottom: 7 }}><strong>{item.month}</strong><span>{formatCurrency(item.amount)}</span></div>
                  <div style={{ height: 12, overflow: "hidden", borderRadius: 999, background: "#e0f2fe" }}>
                    <div style={{ width: `${(item.amount / maxMonthlySpend) * 100}%`, height: "100%", borderRadius: "inherit", background: "#0284c7" }} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {activePage === "Settings" && (
          <section className="metric-card" aria-labelledby="settings-title">
            <p className="eyebrow">AI configuration</p>
            <h2 id="settings-title">Provider settings</h2>
            {!aiConfiguration && !aiStatus && <p>Loading provider settings...</p>}
            {aiConfiguration && <div style={{ display: "grid", gap: 12, marginTop: 20 }}>
              <p>Provider <span style={{ color: "inherit", fontWeight: 800 }}>{aiConfiguration.provider}</span></p>
              <p>Model <span style={{ color: "inherit", fontWeight: 800 }}>{aiConfiguration.model}</span></p>
              <p>Status <span style={{ color: "inherit", fontWeight: 800 }}>{aiConfiguration.configured ? "Configured" : "Not configured"}</span></p>
              <p>Supported providers: {aiConfiguration.supported_providers.join(", ")}</p>
              <p style={{ color: "#64748b" }}>Update keys and provider selection in <code>backend/.env</code>; secrets are never shown here.</p>
              <div><button className="theme-toggle" disabled={!aiConfiguration.configured || testingAI} onClick={testAIProvider} type="button">{testingAI ? "Testing..." : "Test AI Provider"}</button></div>
            </div>}
            {aiStatus && <p role="status" style={{ marginTop: 20 }}>{aiStatus}</p>}
          </section>
        )}

        {activePage === "Help" && (
          <section className="metric-card" aria-labelledby="help-title">
            <p className="eyebrow">Getting started</p>
            <h2 id="help-title">Help and onboarding</h2>
            <ol style={{ display: "grid", gap: 12, marginTop: 24, paddingLeft: 22 }}>
              <li>Start the FastAPI backend on port 8000.</li>
              <li>Start this React frontend with <code>npm run dev</code>.</li>
              <li>Add transactions manually, sync Gmail, or upload receipts.</li>
              <li>Review low-confidence transactions before they affect your records.</li>
            </ol>
            <div style={{ display: "grid", gap: 14, marginTop: 28 }}>
              <details><summary>Where do I configure my AI provider?</summary><p>Use <code>backend/.env</code>, then restart FastAPI. The Settings page can test the configured provider.</p></details>
              <details><summary>Why is my transaction pending review?</summary><p>Low-confidence AI or OCR extraction requires a human approval, correction, or rejection.</p></details>
              <details><summary>Where can I download data?</summary><p>The legacy dashboard includes CSV and JSON exports. Export controls will be added to this React frontend in a later step.</p></details>
            </div>
          </section>
        )}

        {activePage === "Dashboard" && editingTransaction && (
          <div role="presentation" style={{ position: "fixed", inset: 0, zIndex: 30, display: "grid", placeItems: "center", padding: 20, background: "rgba(15, 23, 42, .58)" }}>
            <section aria-labelledby="edit-review-title" aria-modal="true" role="dialog" style={{ width: "min(100%, 520px)", padding: 24, borderRadius: 16, color: "#172033", background: "#fff", boxShadow: "0 24px 56px rgba(0,0,0,.28)" }}>
              <p className="eyebrow">Review correction</p>
              <h2 id="edit-review-title">Edit and approve</h2>
              {reviewError && <p role="alert" style={{ color: "#b91c1c" }}>{reviewError}</p>}
              <label style={{ display: "grid", gap: 6, marginTop: 20 }}>Merchant<input value={editMerchant} onChange={(event) => setEditMerchant(event.target.value)} /></label>
              <label style={{ display: "grid", gap: 6, marginTop: 14 }}>Amount<input min="0.01" step="0.01" type="number" value={editAmount} onChange={(event) => setEditAmount(event.target.value)} /></label>
              <label style={{ display: "grid", gap: 6, marginTop: 14 }}>Category<input value={editCategory} onChange={(event) => setEditCategory(event.target.value)} /></label>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
                <button className="theme-toggle" onClick={() => setEditingTransaction(null)} type="button">Cancel</button>
                <button className="theme-toggle" disabled={reviewingId === editingTransaction._id} onClick={saveEditedReview} type="button">Save & Approve</button>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

const navigation = ["Dashboard", "Transactions", "Reports", "Profile", "Settings", "Help"];
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const TRANSACTIONS_PAGE_SIZE = 20;
const gmailStatusLabels: Record<string, string> = {
  transaction_inserted: "Transaction added",
  review_required_not_inserted: "Needs review",
  duplicate_skipped: "Already processed",
  processing_failed: "Could not process",
  gemini_rejected: "Not a transaction",
  ignore: "Ignored",
  unknown: "Needs attention",
};

const formatGmailStatus = (status: string) =>
  gmailStatusLabels[status] ?? `Ignored (${status.replaceAll("_", " ")})`;

const kpiIcons: Record<string, string> = {
  Income: "↗",
  Expenses: "↙",
  Investments: "◈",
  Refunds: "↩",
  Transfers: "⇄",
  "Net cash flow": "◎",
  Transactions: "≡",
  "Pending review": "!",
};

type DashboardSummary = {
  total_spend: number;
  total_credit: number;
  net_balance: number;
  total_income?: number;
  total_expenses?: number;
  total_refunds?: number;
  total_investments?: number;
  total_transfers?: number;
  net_cash_flow?: number;
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
  transaction_type?: string;
  ai_reason?: string;
};

type ReviewLog = {
  _id: string;
  subject?: string;
  from?: string;
  reason?: string;
  error?: string;
  created_at?: string;
  proposed_transaction?: { date?: string; merchant?: string; amount?: number; category?: string; transaction_type?: string };
};

type TransactionRecord = {
  _id: string;
  date: string;
  merchant: string;
  amount: number;
  category: string;
  transaction_type?: string;
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

type GeneratedInsight = {
  headline: string;
  insights: string[];
  disclaimer: string;
  provider: string;
  model: string;
};

type InsightHistoryItem = GeneratedInsight & {
  _id: string;
  created_at: string;
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
  created_at?: string;
};

type GmailSyncRun = {
  _id: string;
  source: "manual" | "scheduled";
  status: "success" | "failed";
  summary?: { inserted_transactions?: number; review_required?: number; ignored_emails?: number };
  created_at: string;
};

type Receipt = {
  _id: string;
  transaction_id?: string;
  file_name: string;
  status: string;
  ocr_text?: string;
};

type Bill = {
  _id: string;
  provider: string;
  bill_type: string;
  amount: number;
  due_date?: string;
  status: string;
  file_name: string;
};

type CurrentBudget = {
  month: string;
  overall: { limit: number; spent: number; remaining: number; percent_used: number } | null;
  categories: Array<{ category: string; limit: number; spent: number; remaining: number; percent_used: number }>;
};

type ProfileForm = {
  display_name: string;
  email: string;
  currency: string;
  timezone: string;
  monthly_income_target: string;
  savings_goal: string;
  investment_goal: string;
  starting_balance: string;
  priorities: string;
  account_labels: string;
  gmail_sync_frequency: string;
};

type ScheduledSyncDetails = {
  ranAt: string;
  status: string;
};

const emptyProfileForm: ProfileForm = {
  display_name: "", email: "", currency: "INR", timezone: "Asia/Kolkata", monthly_income_target: "", savings_goal: "", investment_goal: "", starting_balance: "", priorities: "", account_labels: "", gmail_sync_frequency: "manual",
};

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);

export default function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("theme") !== "light");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryError, setSummaryError] = useState("");
  const [reportMonth, setReportMonth] = useState("");
  const [reportDateFrom, setReportDateFrom] = useState("");
  const [reportDateTo, setReportDateTo] = useState("");
  const [reviewTransactions, setReviewTransactions] = useState<ReviewTransaction[]>([]);
  const [reviewLogs, setReviewLogs] = useState<ReviewLog[]>([]);
  const [reviewError, setReviewError] = useState("");
  const [reviewingId, setReviewingId] = useState("");
  const [editingTransaction, setEditingTransaction] = useState<ReviewTransaction | null>(null);
  const [editingGmailLog, setEditingGmailLog] = useState<ReviewLog | null>(null);
  const [editMerchant, setEditMerchant] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editDate, setEditDate] = useState("");
  const [editTransactionType, setEditTransactionType] = useState("expense");
  const [transactionStatus, setTransactionStatus] = useState("");
  const [transactionTypeFilter, setTransactionTypeFilter] = useState("");
  const [transactionDateFrom, setTransactionDateFrom] = useState("");
  const [transactionDateTo, setTransactionDateTo] = useState("");
  const [transactionSearch, setTransactionSearch] = useState("");
  const [transactionCategory, setTransactionCategory] = useState("");
  const [transactionSort, setTransactionSort] = useState("newest");
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [transactionsError, setTransactionsError] = useState("");
  const [transactionsPage, setTransactionsPage] = useState(0);
  const [transactionRefresh, setTransactionRefresh] = useState(0);
  const [newDate, setNewDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [newMerchant, setNewMerchant] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [newTransactionType, setNewTransactionType] = useState("expense");
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
  const [gmailSyncRuns, setGmailSyncRuns] = useState<GmailSyncRun[]>([]);
  const [gmailSyncRunsError, setGmailSyncRunsError] = useState("");
  const [logsRefresh, setLogsRefresh] = useState(0);
  const [gmailConnected, setGmailConnected] = useState<boolean | null>(null);
  const [gmailConnectionMessage, setGmailConnectionMessage] = useState("");
  const [connectedGmailAddress, setConnectedGmailAddress] = useState("");
  const [disconnectingGmail, setDisconnectingGmail] = useState(false);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [receiptsError, setReceiptsError] = useState("");
  const [receiptsRefresh, setReceiptsRefresh] = useState(0);
  const [bills, setBills] = useState<Bill[]>([]);
  const [billsError, setBillsError] = useState("");
  const [billsHistoryRefresh, setBillsHistoryRefresh] = useState(0);
  const [billHistoryStatus, setBillHistoryStatus] = useState("");
  const [billSearch, setBillSearch] = useState("");
  const [billSort, setBillSort] = useState("recent");
  const [aiConfiguration, setAiConfiguration] = useState<AIConfiguration | null>(null);
  const [aiStatus, setAiStatus] = useState("");
  const [testingAI, setTestingAI] = useState(false);
  const [generatedInsight, setGeneratedInsight] = useState<GeneratedInsight | null>(null);
  const [aiInsightError, setAiInsightError] = useState("");
  const [generatingInsight, setGeneratingInsight] = useState(false);
  const [insightHistory, setInsightHistory] = useState<InsightHistoryItem[]>([]);
  const [insightHistoryError, setInsightHistoryError] = useState("");
  const [insightHistoryRefresh, setInsightHistoryRefresh] = useState(0);
  const [currentBudget, setCurrentBudget] = useState<CurrentBudget | null>(null);
  const [budgetError, setBudgetError] = useState("");
  const [monthlyBudgetInput, setMonthlyBudgetInput] = useState("");
  const [budgetStatus, setBudgetStatus] = useState("");
  const [savingBudget, setSavingBudget] = useState(false);
  const [categoryBudgetName, setCategoryBudgetName] = useState("");
  const [categoryBudgetLimit, setCategoryBudgetLimit] = useState("");
  const [profileForm, setProfileForm] = useState<ProfileForm>(emptyProfileForm);
  const [scheduledSyncDetails, setScheduledSyncDetails] = useState<ScheduledSyncDetails | null>(null);
  const [profileStatus, setProfileStatus] = useState("");
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const maxMonthlySpend = Math.max(1, ...(summary?.monthly_trend.map((item) => item.amount) ?? []));
  const visibleBills = bills
    .filter((bill) => !billHistoryStatus || bill.status === billHistoryStatus)
    .filter((bill) => `${bill.provider} ${bill.bill_type} ${bill.file_name}`.toLowerCase().includes(billSearch.trim().toLowerCase()))
    .sort((first, second) => {
      if (billSort === "amount_high") return second.amount - first.amount;
      if (billSort === "amount_low") return first.amount - second.amount;
      if (billSort === "due_soon") return (first.due_date ?? "9999-12-31").localeCompare(second.due_date ?? "9999-12-31");
      return 0;
    });
  const visibleBillsTotal = visibleBills.reduce((total, bill) => total + bill.amount, 0);
  const visibleTransactions = transactions
    .filter((transaction) => !transactionCategory || transaction.category === transactionCategory)
    .filter((transaction) => `${transaction.merchant} ${transaction.category}`.toLowerCase().includes(transactionSearch.trim().toLowerCase()))
    .sort((first, second) => {
      if (transactionSort === "amount_high") return second.amount - first.amount;
      if (transactionSort === "amount_low") return first.amount - second.amount;
      if (transactionSort === "oldest") return first.date.localeCompare(second.date);
      return second.date.localeCompare(first.date);
    });
  const visibleTransactionTotal = visibleTransactions.reduce((total, transaction) => total + transaction.amount, 0);
  const categoryEntries = Object.entries(summary?.category_summary ?? {}).sort(([, firstAmount], [, secondAmount]) => secondAmount - firstAmount);
  const maxCategorySpend = Math.max(1, ...categoryEntries.map(([, amount]) => amount));
  const topCategory = categoryEntries[0];

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? "dark" : "light";
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  useEffect(() => {
    if (activePage !== "Dashboard" && activePage !== "Reports") return;

    let cancelled = false;
    setSummaryError("");
    const reportParameters = new URLSearchParams();
    if (activePage === "Reports" && reportMonth) reportParameters.set("month", reportMonth);
    if (activePage === "Reports" && reportDateFrom) reportParameters.set("date_from", reportDateFrom);
    if (activePage === "Reports" && reportDateTo) reportParameters.set("date_to", reportDateTo);
    const summaryUrl = reportParameters.size ? `${API_BASE_URL}/dashboard/summary?${reportParameters}` : `${API_BASE_URL}/dashboard/summary`;
    fetch(summaryUrl)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load dashboard data");
        if (!cancelled) setSummary(result.summary);
      })
      .catch((error: Error) => !cancelled && setSummaryError(error.message));

    return () => { cancelled = true; };
  }, [activePage, reportMonth, reportDateFrom, reportDateTo]);

  useEffect(() => {
    if (activePage !== "Dashboard") return;

    fetch(`${API_BASE_URL}/receipts`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load receipts");
        setReceipts(result.receipts ?? []);
      })
      .catch((error: Error) => setReceiptsError(error.message));
  }, [activePage, receiptsRefresh]);

  useEffect(() => {
    if (activePage !== "Dashboard") return;

    fetch(`${API_BASE_URL}/bills`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load bills");
        setBills(result.bills ?? []);
      })
      .catch((error: Error) => setBillsError(error.message));
  }, [activePage, billsHistoryRefresh]);

  useEffect(() => {
    if (activePage !== "Dashboard") return;

    fetch(`${API_BASE_URL}/ai/insights/history?limit=5`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load insight history");
        setInsightHistory(result.insights ?? []);
      })
      .catch((error: Error) => setInsightHistoryError(error.message));
  }, [activePage, insightHistoryRefresh]);

  useEffect(() => {
    if (activePage !== "Dashboard" && activePage !== "Reports") return;
    if (activePage === "Reports" && (reportDateFrom || reportDateTo)) {
      setCurrentBudget(null);
      setBudgetError("");
      return;
    }

    const budgetUrl = activePage === "Reports" && reportMonth ? `${API_BASE_URL}/budgets/${encodeURIComponent(reportMonth)}` : `${API_BASE_URL}/budgets/current`;
    fetch(budgetUrl)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load budget");
        setCurrentBudget(result);
        setMonthlyBudgetInput(result.overall ? String(result.overall.limit) : "");
      })
      .catch((error: Error) => setBudgetError(error.message));
  }, [activePage, reportMonth, reportDateFrom, reportDateTo]);

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
    if (activePage !== "Dashboard" && activePage !== "Profile") return;

    fetch(`${API_BASE_URL}/dashboard/gmail-logs?limit=${activePage === "Profile" ? 5 : 10}`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load Gmail logs");
        setGmailLogs(result.logs ?? []);
      })
      .catch((error: Error) => setGmailLogsError(error.message));
  }, [activePage, logsRefresh]);

  useEffect(() => {
    if (activePage !== "Profile") return;

    fetch(`${API_BASE_URL}/dashboard/gmail-sync-runs?limit=5`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load Gmail sync history");
        setGmailSyncRuns(result.runs ?? []);
      })
      .catch((error: Error) => setGmailSyncRunsError(error.message));
  }, [activePage, logsRefresh]);

  useEffect(() => {
    if (activePage !== "Dashboard" && activePage !== "Profile") return;

    fetch(`${API_BASE_URL}/gmail/status`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Unable to check Gmail connection");
        setGmailConnected(result.connected);
        setConnectedGmailAddress(result.connected ? result.email_address ?? "" : "");
        setGmailConnectionMessage(result.message);
      })
      .catch((error: Error) => setGmailConnectionMessage(error.message));
  }, [activePage]);

  useEffect(() => {
    if (activePage !== "Profile" && activePage !== "Dashboard") return;

    setLoadingProfile(true);
    setProfileStatus("");
    fetch(`${API_BASE_URL}/profile`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load profile");
        if (result.profile) {
          const profile = result.profile;
          setProfileForm({
            display_name: profile.display_name ?? "", email: profile.email ?? "", currency: profile.currency ?? "INR", timezone: profile.timezone ?? "Asia/Kolkata",
            monthly_income_target: profile.monthly_income_target ? String(profile.monthly_income_target) : "", savings_goal: profile.savings_goal ? String(profile.savings_goal) : "",
            investment_goal: profile.investment_goal ? String(profile.investment_goal) : "", starting_balance: profile.starting_balance !== undefined && profile.starting_balance !== null ? String(profile.starting_balance) : "",
            priorities: (profile.priorities ?? []).join(", "), account_labels: (profile.account_labels ?? []).join(", "), gmail_sync_frequency: profile.gmail_sync_frequency ?? "manual",
          });
          setScheduledSyncDetails(profile.last_gmail_scheduled_sync_at ? {
            ranAt: profile.last_gmail_scheduled_sync_at,
            status: profile.last_gmail_scheduled_sync_status ?? "unknown",
          } : null);
        } else {
          setScheduledSyncDetails(null);
        }
      })
      .catch((error: Error) => setProfileStatus(error.message))
      .finally(() => setLoadingProfile(false));
  }, [activePage]);

  useEffect(() => {
    if (activePage !== "Transactions") return;

    const parameters = new URLSearchParams({ limit: String(TRANSACTIONS_PAGE_SIZE), skip: String(transactionsPage * TRANSACTIONS_PAGE_SIZE) });
    if (transactionStatus) parameters.set("status", transactionStatus);
    if (transactionTypeFilter) parameters.set("transaction_type", transactionTypeFilter);
    if (transactionDateFrom) parameters.set("date_from", transactionDateFrom);
    if (transactionDateTo) parameters.set("date_to", transactionDateTo);
    setTransactionsError("");
    fetch(`${API_BASE_URL}/transactions?${parameters}`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to load transactions");
        setTransactions(result.transactions ?? []);
      })
      .catch((error: Error) => setTransactionsError(error.message));
  }, [activePage, transactionStatus, transactionTypeFilter, transactionDateFrom, transactionDateTo, transactionsPage, transactionRefresh]);

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
        setReviewLogs(result.logs ?? []);
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

  async function resolveGmailReviewLog(logId: string, decision: "approve" | "reject", corrections: Record<string, string | number> = {}) {
    setReviewingId(logId);
    setReviewError("");
    try {
      const response = await fetch(`${API_BASE_URL}/gmail-review-logs/${logId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, ...corrections }),
      });
      const result = await response.json();
      if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to resolve Gmail review item");
      setReviewLogs((items) => items.filter((item) => item._id !== logId));
      setSummary((current) => current ? { ...current, review_log_count: Math.max(0, current.review_log_count - 1), total_transactions: decision === "approve" ? current.total_transactions + 1 : current.total_transactions } : current);
      if (decision === "approve") setTransactionRefresh((value) => value + 1);
      return true;
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Unable to resolve Gmail review item");
      return false;
    } finally {
      setReviewingId("");
    }
  }

  function openEditGmailReview(log: ReviewLog) {
    const proposal = log.proposed_transaction;
    setEditingGmailLog(log);
    setEditDate(proposal?.date || new Date().toISOString().slice(0, 10));
    setEditMerchant(proposal?.merchant || log.subject || "");
    setEditAmount(proposal?.amount ? String(proposal.amount) : "");
    setEditCategory(proposal?.category || "Others");
    setEditTransactionType(["debit", "credit", "income", "expense", "investment", "transfer", "refund"].includes(proposal?.transaction_type || "") ? proposal?.transaction_type || "expense" : "expense");
    setReviewError("");
  }

  async function saveEditedGmailReview() {
    if (!editingGmailLog) return;
    const amount = Number(editAmount);
    if (!editDate || !editMerchant.trim() || !editCategory.trim() || !Number.isFinite(amount) || amount <= 0) {
      setReviewError("Date, merchant, category, and a positive amount are required.");
      return;
    }
    const saved = await resolveGmailReviewLog(editingGmailLog._id, "approve", {
      date: editDate, merchant: editMerchant.trim(), amount, category: editCategory.trim(), transaction_type: editTransactionType, review_note: "Corrected during Gmail review",
    });
    if (saved) setEditingGmailLog(null);
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

  async function generateAIInsight() {
    setGeneratingInsight(true);
    setAiInsightError("");
    try {
      const response = await fetch(`${API_BASE_URL}/ai/insights`, { method: "POST" });
      const result = await response.json();
      if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to generate AI insights");
      setGeneratedInsight({ ...result.insight, provider: result.provider, model: result.model });
      setInsightHistoryRefresh((value) => value + 1);
    } catch (error) {
      setAiInsightError(error instanceof Error ? error.message : "Unable to generate AI insights");
    } finally {
      setGeneratingInsight(false);
    }
  }

  async function saveBudgetConfiguration(monthlyLimit: number | null, categoryLimits: Record<string, number>, successMessage: string) {
    setSavingBudget(true);
    setBudgetStatus("");
    try {
      const response = await fetch(`${API_BASE_URL}/budgets/current`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ monthly_limit: monthlyLimit, category_limits: categoryLimits }),
      });
      const result = await response.json();
      if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to save budget");
      setCurrentBudget(result);
      setMonthlyBudgetInput(result.overall ? String(result.overall.limit) : "");
      setBudgetStatus(successMessage);
    } catch (error) {
      setBudgetStatus(error instanceof Error ? error.message : "Unable to save budget");
    } finally {
      setSavingBudget(false);
    }
  }

  async function saveMonthlyBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const monthlyLimit = monthlyBudgetInput.trim() ? Number(monthlyBudgetInput) : null;
    if (monthlyLimit !== null && (!Number.isFinite(monthlyLimit) || monthlyLimit <= 0)) {
      setBudgetStatus("Enter a positive monthly budget, or clear the field to remove it.");
      return;
    }
    const categoryLimits = Object.fromEntries((currentBudget?.categories ?? []).map((item) => [item.category, item.limit]));
    await saveBudgetConfiguration(monthlyLimit, categoryLimits, monthlyLimit === null ? "Monthly budget removed." : "Monthly budget saved.");
  }

  async function saveCategoryBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const category = categoryBudgetName.trim();
    const limit = Number(categoryBudgetLimit);
    if (!category || !Number.isFinite(limit) || limit <= 0) {
      setBudgetStatus("Enter a category and a positive category budget.");
      return;
    }
    const categoryLimits = Object.fromEntries((currentBudget?.categories ?? []).map((item) => [item.category, item.limit]));
    categoryLimits[category] = limit;
    await saveBudgetConfiguration(currentBudget?.overall?.limit ?? null, categoryLimits, `${category} budget saved.`);
    setCategoryBudgetName("");
    setCategoryBudgetLimit("");
  }

  async function removeCategoryBudget(category: string) {
    const categoryLimits = Object.fromEntries((currentBudget?.categories ?? []).filter((item) => item.category !== category).map((item) => [item.category, item.limit]));
    await saveBudgetConfiguration(currentBudget?.overall?.limit ?? null, categoryLimits, `${category} budget removed.`);
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profileForm.display_name.trim()) {
      setProfileStatus("Display name is required.");
      return;
    }
    const optionalNumber = (value: string) => value.trim() ? Number(value) : null;
    const values = [profileForm.monthly_income_target, profileForm.savings_goal, profileForm.investment_goal];
    if (values.some((value) => value.trim() && (!Number.isFinite(Number(value)) || Number(value) <= 0)) || (profileForm.starting_balance.trim() && !Number.isFinite(Number(profileForm.starting_balance)))) {
      setProfileStatus("Goals must be positive numbers; starting balance can be positive or negative.");
      return;
    }
    setSavingProfile(true);
    setProfileStatus("");
    try {
      const response = await fetch(`${API_BASE_URL}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: profileForm.display_name.trim(), email: profileForm.email.trim() || null, currency: profileForm.currency.trim() || "INR", timezone: profileForm.timezone.trim() || "Asia/Kolkata",
          monthly_income_target: optionalNumber(profileForm.monthly_income_target), savings_goal: optionalNumber(profileForm.savings_goal), investment_goal: optionalNumber(profileForm.investment_goal), starting_balance: optionalNumber(profileForm.starting_balance),
          priorities: profileForm.priorities.split(",").map((item) => item.trim()).filter(Boolean), account_labels: profileForm.account_labels.split(",").map((item) => item.trim()).filter(Boolean), gmail_sync_frequency: profileForm.gmail_sync_frequency,
        }),
      });
      const result = await response.json();
      if (!response.ok || result.status !== "success") throw new Error(result.detail || "Unable to save profile");
      setProfileStatus("Profile saved successfully.");
    } catch (error) {
      setProfileStatus(error instanceof Error ? error.message : "Unable to save profile");
    } finally {
      setSavingProfile(false);
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
        body: JSON.stringify({ date: newDate, merchant: newMerchant.trim(), amount, category: newCategory.trim(), transaction_type: newTransactionType, source: "manual" }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Unable to add transaction");
      setTransactionMessage("Transaction added successfully.");
      setNewMerchant(""); setNewAmount(""); setNewCategory(""); setNewTransactionType("expense");
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
      setReceiptsRefresh((value) => value + 1);
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
      setBillsHistoryRefresh((value) => value + 1);
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

  async function disconnectGmail() {
    if (!window.confirm("Disconnect Gmail? Existing transactions will not be deleted.")) return;
    setDisconnectingGmail(true);
    try {
      const response = await fetch(`${API_BASE_URL}/gmail/disconnect`, { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Unable to disconnect Gmail");
      setGmailConnected(false);
      setGmailConnectionMessage("Gmail disconnected");
      setSyncStatus("");
    } catch (error) {
      setGmailConnectionMessage(error instanceof Error ? error.message : "Unable to disconnect Gmail");
    } finally {
      setDisconnectingGmail(false);
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
            <h2 id="welcome-title">{profileForm.display_name ? `Welcome back, ${profileForm.display_name}.` : "Your financial picture, clearly organized."}</h2>
            <p>{summaryError ? `Dashboard data unavailable: ${summaryError}` : profileForm.savings_goal && Number.isFinite(Number(profileForm.savings_goal)) ? `Your savings goal is ${formatCurrency(Number(profileForm.savings_goal))}.` : "Live data is loaded from your FastAPI backend."}</p>
          </div>
          <div className="insight-pill"><span aria-hidden="true">✦</span> AI-ready</div>
        </section>

        <section className="placeholder-grid kpi-grid" aria-label="Financial overview">
          {[
            ["Income", summary ? formatCurrency(summary.total_income ?? summary.total_credit) : "Loading..."],
            ["Expenses", summary ? formatCurrency(summary.total_expenses ?? summary.total_spend) : "Loading..."],
            ["Investments", summary ? formatCurrency(summary.total_investments ?? 0) : "Loading..."],
            ["Refunds", summary ? formatCurrency(summary.total_refunds ?? 0) : "Loading..."],
            ["Transfers", summary ? formatCurrency(summary.total_transfers ?? 0) : "Loading..."],
            ["Net cash flow", summary ? formatCurrency(summary.net_cash_flow ?? summary.net_balance) : "Loading..."],
            ["Transactions", summary ? String(summary.total_transactions) : "Loading..."],
            ["Pending review", summary ? String(summary.review_required_count + summary.review_log_count) : "Loading..."],
          ].map(([label, value]) => (
            <article className={`metric-card kpi-card kpi-${label.toLowerCase().replaceAll(" ", "-")}`} key={label}>
              <div className="kpi-heading"><span className="kpi-icon" aria-hidden="true">{kpiIcons[label]}</span><p>{label}</p></div><strong>{value}</strong>
              <span className="kpi-caption">Current recorded total</span>
            </article>
          ))}
        </section>

        <details className="metric-card expandable-card" style={{ marginTop: 24 }}>
          <summary><span><span className="eyebrow">Email ingestion</span><strong id="gmail-sync-title">Gmail transaction sync</strong></span><span className="details-count">{gmailConnected ? "On" : "Off"}</span></summary>
          <div className="expandable-content">
            <p>{gmailConnectionMessage || "Checking Gmail connection..."}</p>
            {gmailConnected === false && <button className="theme-toggle" onClick={() => window.location.assign(`${API_BASE_URL}/auth/google`)} style={{ marginTop: 18 }} type="button">Connect Gmail</button>}
            {gmailConnected && <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 18 }}>
              <button className="theme-toggle" disabled={syncingGmail || disconnectingGmail} onClick={syncGmail} type="button">{syncingGmail ? "Syncing..." : "Sync Gmail"}</button>
              <button className="theme-toggle" disabled={syncingGmail || disconnectingGmail} onClick={disconnectGmail} type="button">{disconnectingGmail ? "Disconnecting..." : "Disconnect Gmail"}</button>
            </div>}
            {syncStatus && <p role="status" style={{ marginTop: 16 }}>{syncStatus}</p>}
          </div>
        </details>

        <details className="metric-card expandable-card" style={{ marginTop: 24 }}>
          <summary><span><span className="eyebrow">Sync activity</span><strong id="gmail-logs-title">Gmail processing logs</strong></span><span className="details-count">{gmailLogs.length}</span></summary>
          <div className="expandable-content">
            {gmailLogsError && <p role="alert">{gmailLogsError}</p>}
            {!gmailLogsError && gmailLogs.length === 0 && <p>No Gmail processing logs yet.</p>}
            <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
              {gmailLogs.map((log) => (
                <article className="timeline-item" key={log._id}>
                  <strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{log.subject || "No subject"}</strong>
                  <p style={{ marginTop: 6 }}>{formatGmailStatus(log.status)}{log.reason || log.error ? ` · ${log.reason || log.error}` : ""}</p>
                </article>
              ))}
            </div>
          </div>
        </details>

        <section className="analytics-grid" aria-label="Interactive financial analytics">
          <article className="metric-card chart-card" aria-labelledby="cashflow-chart-title">
            <div className="card-title-row"><div><p className="eyebrow">Cash flow</p><h2 id="cashflow-chart-title">Monthly spending trend</h2></div><span className="chart-legend"><i className="legend-dot" /> Expenses</span></div>
            {!summary && <div className="chart-empty">Loading chart data…</div>}
            {summary && summary.monthly_trend.length === 0 && <div className="chart-empty">No spending trend available yet.</div>}
            {summary && summary.monthly_trend.length > 0 && <div className="bar-chart" role="img" aria-label="Monthly spending bar chart">
              {summary.monthly_trend.map((item) => <button className="chart-column" key={item.month} onClick={() => { setReportMonth(item.month); setActivePage("Reports"); }} title={`${item.month}: ${formatCurrency(item.amount)}`} type="button">
                <span className="chart-bar" style={{ height: `${Math.max(8, (item.amount / maxMonthlySpend) * 100)}%` }} />
                <span className="chart-value">{formatCurrency(item.amount)}</span><span className="chart-label">{item.month.slice(5)}</span>
              </button>)}
            </div>}
            <p className="chart-hint">Select a month to open its full report.</p>
          </article>
          <article className="metric-card chart-card" aria-labelledby="category-chart-title">
            <div className="card-title-row"><div><p className="eyebrow">Distribution</p><h2 id="category-chart-title">Top expense categories</h2></div><span className="chart-legend"><i className="legend-dot legend-dot-alt" /> Share of spend</span></div>
            {summary && categoryEntries.length === 0 && <div className="chart-empty">No category data available yet.</div>}
            <div className="category-chart">
              {categoryEntries.slice(0, 5).map(([category, amount], index) => <button className="category-row" key={category} onClick={() => { setTransactionCategory(category); setTransactionsPage(0); setActivePage("Transactions"); }} title={`View ${category} transactions`} type="button">
                <span className={`category-swatch category-swatch-${index}`} /><span className="category-name">{category}</span><span className="category-rail"><span style={{ width: `${(amount / maxCategorySpend) * 100}%` }} /></span><strong>{formatCurrency(amount)}</strong>
              </button>)}
            </div>
            <p className="chart-hint">Select a category to inspect its transactions.</p>
          </article>
        </section>

        <section className="metric-card" aria-labelledby="budget-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Monthly planning</p>
          <h2 id="budget-title">Budget</h2>
          {budgetError && <p role="alert">{budgetError}</p>}
          {!budgetError && !currentBudget && <p>Loading budget...</p>}
          {currentBudget && <>
            <form onSubmit={saveMonthlyBudget} style={{ display: "flex", flexWrap: "wrap", alignItems: "end", gap: 12, marginTop: 20 }}>
              <label style={{ display: "grid", gap: 6, flex: "1 1 220px" }}>
                Monthly expense budget
                <input min="0.01" placeholder="For example, 30000" step="0.01" type="number" value={monthlyBudgetInput} onChange={(event) => setMonthlyBudgetInput(event.target.value)} />
              </label>
              <button className="theme-toggle" disabled={savingBudget} type="submit">{savingBudget ? "Saving..." : "Save budget"}</button>
            </form>
            {budgetStatus && <p role="status" style={{ marginTop: 12 }}>{budgetStatus}</p>}
            {!currentBudget.overall && <p style={{ marginTop: 18 }}>Set a monthly expense budget to receive spending alerts.</p>}
            {currentBudget.overall && <div style={{ display: "grid", gap: 12, marginTop: 20 }}>
              <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 12 }}><strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{formatCurrency(currentBudget.overall.spent)} spent of {formatCurrency(currentBudget.overall.limit)}</strong><span>{currentBudget.month} · {currentBudget.overall.percent_used}% used</span></div>
              <div className="budget-progress" aria-label={`${currentBudget.overall.percent_used}% of monthly budget used`}><span className={currentBudget.overall.percent_used >= 100 ? "budget-danger" : currentBudget.overall.percent_used >= 80 ? "budget-warning" : "budget-healthy"} style={{ width: `${Math.min(currentBudget.overall.percent_used, 100)}%` }} /></div>
              <p className={currentBudget.overall.percent_used >= 100 ? "budget-danger-text" : currentBudget.overall.percent_used >= 80 ? "budget-warning-text" : "budget-healthy-text"}>{currentBudget.overall.percent_used >= 100 ? `Budget exceeded by ${formatCurrency(Math.abs(currentBudget.overall.remaining))}.` : currentBudget.overall.percent_used >= 80 ? `Budget warning: only ${formatCurrency(currentBudget.overall.remaining)} remains.` : `${formatCurrency(currentBudget.overall.remaining)} remains this month.`}</p>
            </div>}
            <div style={{ marginTop: 28 }}>
              <h3 style={{ margin: 0, fontSize: "1rem" }}>Category budgets</h3>
              <form onSubmit={saveCategoryBudget} style={{ display: "flex", flexWrap: "wrap", alignItems: "end", gap: 12, marginTop: 14 }}>
                <label style={{ display: "grid", gap: 6, flex: "1 1 180px" }}>Category<input placeholder="For example, Food" value={categoryBudgetName} onChange={(event) => setCategoryBudgetName(event.target.value)} /></label>
                <label style={{ display: "grid", gap: 6, flex: "1 1 160px" }}>Limit<input min="0.01" placeholder="For example, 6000" step="0.01" type="number" value={categoryBudgetLimit} onChange={(event) => setCategoryBudgetLimit(event.target.value)} /></label>
                <button className="theme-toggle" disabled={savingBudget} type="submit">Add or update</button>
              </form>
              {currentBudget.categories.length === 0 && <p style={{ marginTop: 16 }}>No category limits yet.</p>}
              <div style={{ display: "grid", gap: 14, marginTop: 16 }}>
                {currentBudget.categories.map((item) => <article className="insight-card" key={item.category}>
                  <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 12 }}><strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{item.category}</strong><button className="theme-toggle" disabled={savingBudget} onClick={() => removeCategoryBudget(item.category)} type="button">Remove</button></div>
                  <p style={{ marginTop: 10 }}>{formatCurrency(item.spent)} of {formatCurrency(item.limit)} · {item.percent_used}% used</p>
                  <div className="budget-progress" style={{ marginTop: 10 }}><span className={item.percent_used >= 100 ? "budget-danger" : item.percent_used >= 80 ? "budget-warning" : "budget-healthy"} style={{ width: `${Math.min(item.percent_used, 100)}%` }} /></div>
                  <p className={item.percent_used >= 100 ? "budget-danger-text" : item.percent_used >= 80 ? "budget-warning-text" : "budget-healthy-text"} style={{ marginTop: 8 }}>{item.percent_used >= 100 ? `Exceeded by ${formatCurrency(Math.abs(item.remaining))}.` : `${formatCurrency(item.remaining)} remains.`}</p>
                </article>)}
              </div>
            </div>
          </>}
        </section>

        <section className="metric-card" aria-labelledby="insights-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Smart, data-driven guidance</p>
          <h2 id="insights-title">Money insights</h2>
          {!summary && <p>Loading insights...</p>}
          {summary && <div style={{ display: "grid", gap: 12, marginTop: 20 }}>
            {topCategory && <article className="insight-card">
              Your largest spending category is <strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{topCategory[0]}</strong> at {formatCurrency(topCategory[1])}.
            </article>}
            <article className="insight-card">
              {summary.net_balance >= 0 ? `Your recorded balance is positive at ${formatCurrency(summary.net_balance)}.` : `Your recorded balance is negative at ${formatCurrency(summary.net_balance)}. Review recent spending and credits.`}
            </article>
            {(summary.review_required_count + summary.review_log_count) > 0 && <article className="insight-alert">
              <span><strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{summary.review_required_count + summary.review_log_count}</strong> item(s) need review before they affect your records.</span>
              <button className="theme-toggle" onClick={() => document.getElementById("review-title")?.scrollIntoView({ behavior: "smooth", block: "start" })} type="button">Review now</button>
            </article>}
            {billsDue.length > 0 && <article className="insight-card">
              You have {billsDue.length} upcoming bill{billsDue.length === 1 ? "" : "s"} totaling {formatCurrency(billsDueTotal)}.
            </article>}
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12, marginTop: 4 }}>
              <button className="theme-toggle" disabled={generatingInsight} onClick={generateAIInsight} type="button">{generatingInsight ? "Generating..." : "Generate AI insights"}</button>
              <span className="insight-helper">Uses your configured provider and aggregate data only.</span>
            </div>
            {aiInsightError && <p role="alert">{aiInsightError}</p>}
            {generatedInsight && <article aria-live="polite" className="ai-insight-result">
              <strong>{generatedInsight.headline}</strong>
              <ul style={{ margin: "12px 0", paddingLeft: 20, display: "grid", gap: 8 }}>
                {generatedInsight.insights.map((insight, index) => <li key={`${insight}-${index}`}>{insight}</li>)}
              </ul>
              <p className="ai-insight-disclaimer">{generatedInsight.disclaimer}</p>
              <p className="ai-insight-provider">Generated by {generatedInsight.provider} · {generatedInsight.model}</p>
            </article>}
            <div style={{ marginTop: 10 }}>
              <h3 style={{ margin: 0, fontSize: "1rem" }}>Recent AI insights</h3>
              {insightHistoryError && <p role="alert">{insightHistoryError}</p>}
              {!insightHistoryError && insightHistory.length === 0 && <p style={{ marginTop: 8 }}>No saved AI insights yet.</p>}
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                {insightHistory.map((insight) => <article className="insight-card" key={insight._id}>
                  <strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{insight.headline}</strong>
                  <p style={{ marginTop: 6 }}>{insight.insights[0]}</p>
                  <p className="ai-insight-provider">{new Date(insight.created_at).toLocaleString()} · {insight.provider} · {insight.model}</p>
                </article>)}
              </div>
            </div>
          </div>}
        </section>

        <section className="dashboard-detail-grid" aria-label="Detailed spending analysis">
          <details className="metric-card expandable-card">
            <summary><span><span className="eyebrow">Spending patterns</span><strong id="top-merchants-title">Top merchants</strong></span><span className="details-count">{summary?.top_merchants.length ?? 0}</span></summary>
            <div className="expandable-content">
              {!summary && <p>Loading merchants...</p>}
              {summary?.top_merchants.length === 0 && <p>No merchant data yet.</p>}
              <ol className="ranked-list">
                {summary?.top_merchants.slice(0, 5).map((merchant) => (
                  <li key={merchant.merchant}><span>{merchant.merchant}</span><strong>{formatCurrency(merchant.amount)}</strong></li>
                ))}
              </ol>
            </div>
          </details>
          <details className="metric-card expandable-card">
            <summary><span><span className="eyebrow">Where your money goes</span><strong id="category-title">Spend by category</strong></span><span className="details-count">{categoryEntries.length}</span></summary>
            <div className="expandable-content">
              {!summary && <p>Loading categories...</p>}
              {summary && Object.keys(summary.category_summary).length === 0 && <p>No category data yet.</p>}
              <ol className="ranked-list">
                {categoryEntries.map(([category, amount]) => (
                  <li key={category}><span>{category}</span><strong>{formatCurrency(amount)}</strong></li>
                ))}
              </ol>
            </div>
          </details>
        </section>

        <section className="metric-card" aria-labelledby="review-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Human verification</p>
          <h2 id="review-title">Review required</h2>
          {reviewError && <p role="alert">{reviewError}</p>}
          {!reviewError && reviewTransactions.length === 0 && reviewLogs.length === 0 && <p>No pending reviews.</p>}
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
          {reviewLogs.length > 0 && <div style={{ display: "grid", gap: 12, marginTop: 16 }}>
            <h3 style={{ margin: 0, fontSize: "1rem" }}>Email items needing confirmation</h3>
            <p style={{ margin: 0 }}>These emails were not added as transactions because the extracted details need confirmation. They do not affect your records.</p>
            {reviewLogs.map((log) => {
              const proposal = log.proposed_transaction;
              const canApprove = Boolean(proposal?.date && proposal.merchant && proposal.amount && proposal.category && ["debit", "credit", "income", "expense", "investment", "transfer", "refund"].includes(proposal.transaction_type || ""));
              return <article key={log._id} style={{ padding: 16, border: "1px solid #e0e7f1", borderRadius: 12 }}>
                <strong>{log.subject || "Transaction email"}</strong>
                <p style={{ margin: "5px 0 0", color: "#64748b" }}>{log.from || "Unknown sender"}{log.reason || log.error ? ` · ${log.reason || log.error}` : ""}{log.created_at ? ` · ${new Date(log.created_at).toLocaleString()}` : ""}</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                  {canApprove && <button className="theme-toggle" disabled={reviewingId === log._id} onClick={() => resolveGmailReviewLog(log._id, "approve")} type="button">Approve & add</button>}
                  <button className="theme-toggle" disabled={reviewingId === log._id} onClick={() => openEditGmailReview(log)} type="button">Edit & add</button>
                  <button className="theme-toggle" disabled={reviewingId === log._id} onClick={() => resolveGmailReviewLog(log._id, "reject")} type="button">Ignore email</button>
                </div>
              </article>;
            })}
          </div>}
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

        <section className="metric-card" aria-labelledby="receipt-history-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Upload history</p>
          <h2 id="receipt-history-title">Recent receipts</h2>
          {receiptsError && <p role="alert">{receiptsError}</p>}
          {!receiptsError && receipts.length === 0 && <p>No receipts uploaded yet.</p>}
          <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
            {receipts.slice(0, 10).map((receipt) => (
              <article key={receipt._id} style={{ padding: 14, border: "1px solid #e0e7f1", borderRadius: 12 }}>
                <strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{receipt.file_name}</strong>
                <p style={{ marginTop: 6 }}>{receipt.status}{receipt.ocr_text ? ` · ${receipt.ocr_text.slice(0, 90)}` : ""}</p>
              </article>
            ))}
          </div>
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

        <section className="metric-card" aria-labelledby="bill-history-title" style={{ marginTop: 24 }}>
          <p className="eyebrow">Upload history</p>
          <h2 id="bill-history-title">Recent bills</h2>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "end", gap: 12, marginTop: 16 }}>
            <label style={{ display: "grid", gap: 6, flex: "1 1 220px" }}>
              Search bills
              <input placeholder="Provider, bill type, or filename" value={billSearch} onChange={(event) => setBillSearch(event.target.value)} />
            </label>
            <label style={{ display: "grid", gap: 6 }}>
              Status filter
              <select value={billHistoryStatus} onChange={(event) => setBillHistoryStatus(event.target.value)}>
                <option value="">All bills</option>
                {[...new Set(bills.map((bill) => bill.status))].filter(Boolean).map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </label>
            <label style={{ display: "grid", gap: 6 }}>
              Sort by
              <select value={billSort} onChange={(event) => setBillSort(event.target.value)}>
                <option value="recent">Upload order</option>
                <option value="due_soon">Due date</option>
                <option value="amount_high">Amount: high to low</option>
                <option value="amount_low">Amount: low to high</option>
              </select>
            </label>
            <button className="theme-toggle" onClick={() => { setBillSearch(""); setBillHistoryStatus(""); setBillSort("recent"); }} type="button">Clear</button>
          </div>
          {billsError && <p role="alert">{billsError}</p>}
          {!billsError && <p style={{ marginTop: 16 }}>{visibleBills.length} matching bill{visibleBills.length === 1 ? "" : "s"} · {formatCurrency(visibleBillsTotal)}</p>}
          {!billsError && visibleBills.length === 0 && <p>{bills.length === 0 ? "No bills uploaded yet." : "No bills found for this search or filter."}</p>}
          <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
            {visibleBills.slice(0, 10).map((bill) => (
              <article key={bill._id} style={{ display: "flex", justifyContent: "space-between", gap: 16, padding: 14, border: "1px solid #e0e7f1", borderRadius: 12 }}>
                <div><strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{bill.provider}</strong><p style={{ marginTop: 6 }}>{bill.bill_type} · {bill.status}{bill.due_date ? ` · Due ${bill.due_date}` : ""}</p></div>
                <span style={{ fontWeight: 800 }}>{formatCurrency(bill.amount)}</span>
              </article>
            ))}
          </div>
        </section>
        </>}

        {activePage === "Transactions" && (
          <section className="metric-card workspace-card" aria-labelledby="transactions-title">
            <div className="workspace-heading"><div><p className="eyebrow">Review history and records</p><h2 id="transactions-title">Transactions ledger</h2><p>Capture, filter, and review every financial movement in one place.</p></div><span className="workspace-stat">{transactions.length} loaded</span></div>
            <form className="data-entry-form" onSubmit={addTransaction}>
              <label>Date<input required type="date" value={newDate} onChange={(event) => setNewDate(event.target.value)} /></label>
              <label>Merchant<input required value={newMerchant} onChange={(event) => setNewMerchant(event.target.value)} /></label>
              <label>Amount<input required min="0.01" step="0.01" type="number" value={newAmount} onChange={(event) => setNewAmount(event.target.value)} /></label>
              <label>Category<input required value={newCategory} onChange={(event) => setNewCategory(event.target.value)} /></label>
              <label>Type<select value={newTransactionType} onChange={(event) => setNewTransactionType(event.target.value)}><option value="expense">Expense</option><option value="income">Income</option><option value="investment">Investment</option><option value="transfer">Transfer</option><option value="refund">Refund</option></select></label>
              <div style={{ alignSelf: "end" }}><button className="theme-toggle" disabled={addingTransaction} type="submit">{addingTransaction ? "Adding..." : "Add transaction"}</button></div>
            </form>
            {transactionMessage && <p role="status">{transactionMessage}</p>}
            <div className="filter-toolbar">
              <label style={{ display: "grid", gap: 6, flex: "1 1 220px" }}>
                Search transactions
                <input placeholder="Merchant or category" value={transactionSearch} onChange={(event) => setTransactionSearch(event.target.value)} />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                Status filter
                <select value={transactionStatus} onChange={(event) => { setTransactionStatus(event.target.value); setTransactionsPage(0); }}>
                  <option value="">All transactions</option>
                  <option value="review_required">Pending review</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="rejected">Rejected</option>
                </select>
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                Financial type
                <select value={transactionTypeFilter} onChange={(event) => { setTransactionTypeFilter(event.target.value); setTransactionsPage(0); }}>
                  <option value="">All types</option>
                  <option value="income">Income</option>
                  <option value="expense">Expense</option>
                  <option value="investment">Investment</option>
                  <option value="transfer">Transfer</option>
                  <option value="refund">Refund</option>
                  <option value="debit">Debit (legacy)</option>
                  <option value="credit">Credit (legacy)</option>
                </select>
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                From date
                <input type="date" value={transactionDateFrom} onChange={(event) => { setTransactionDateFrom(event.target.value); setTransactionsPage(0); }} />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                To date
                <input type="date" value={transactionDateTo} onChange={(event) => { setTransactionDateTo(event.target.value); setTransactionsPage(0); }} />
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                Category
                <select value={transactionCategory} onChange={(event) => setTransactionCategory(event.target.value)}>
                  <option value="">All categories</option>
                  {[...new Set(transactions.map((transaction) => transaction.category))].filter(Boolean).sort().map((category) => <option key={category} value={category}>{category}</option>)}
                </select>
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                Sort by
                <select value={transactionSort} onChange={(event) => setTransactionSort(event.target.value)}>
                  <option value="newest">Date: newest first</option>
                  <option value="oldest">Date: oldest first</option>
                  <option value="amount_high">Amount: high to low</option>
                  <option value="amount_low">Amount: low to high</option>
                </select>
              </label>
              <button className="theme-toggle filter-clear" onClick={() => { setTransactionSearch(""); setTransactionStatus(""); setTransactionTypeFilter(""); setTransactionDateFrom(""); setTransactionDateTo(""); setTransactionCategory(""); setTransactionSort("newest"); setTransactionsPage(0); }} type="button">Clear filters</button>
            </div>
            {transactionsError && <p role="alert">{transactionsError}</p>}
            {!transactionsError && <div className="ledger-summary"><span>{visibleTransactions.length} transaction{visibleTransactions.length === 1 ? "" : "s"} on this page</span><strong>{formatCurrency(visibleTransactionTotal)}</strong></div>}
            {!transactionsError && visibleTransactions.length === 0 && <p>No transactions found for this search or filter.</p>}
            <div className="ledger-table-wrap">
              <table className="ledger-table">
                <thead><tr><th>Date</th><th>Merchant</th><th>Amount</th><th>Category</th><th>Type</th><th>Status</th><th>Review history</th></tr></thead>
                <tbody>{visibleTransactions.map((transaction) => {
                  const status = transaction.status || "confirmed";
                  const colors = status === "rejected" ? ["#fee2e2", "#991b1b"] : status === "review_required" ? ["#fef3c7", "#92400e"] : ["#dcfce7", "#166534"];
                  return <tr key={transaction._id}>
                    <td>{transaction.date}</td><td>{transaction.merchant}</td><td>{formatCurrency(transaction.amount)}</td><td>{transaction.category}</td><td>{(transaction.transaction_type || "debit").replace("_", " ")}</td>
                    <td><span style={{ display: "inline-block", padding: "4px 8px", borderRadius: 999, color: colors[1], background: colors[0], fontSize: ".75rem", fontWeight: 800 }}>{status.replace("_", " ")}</span></td>
                    <td>{transaction.review_decision ? `${transaction.review_decision}${transaction.review_note ? ` — ${transaction.review_note}` : ""}` : "Not reviewed"}</td>
                  </tr>;
                })}</tbody>
              </table>
            </div>
            <div className="pager">
              <button className="theme-toggle" disabled={transactionsPage === 0} onClick={() => setTransactionsPage((page) => page - 1)} type="button">Previous</button>
              <span>Page {transactionsPage + 1}</span>
              <button className="theme-toggle" disabled={transactions.length < TRANSACTIONS_PAGE_SIZE} onClick={() => setTransactionsPage((page) => page + 1)} type="button">Next</button>
            </div>
          </section>
        )}

        {activePage === "Reports" && <>
          <section className="metric-card" aria-labelledby="reports-title">
            <p className="eyebrow">Financial report</p>
            <h2 id="reports-title">Overview</h2>
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "end", gap: 12, marginTop: 18 }}>
              <label style={{ display: "grid", gap: 6 }}>
                Report month
                <input type="month" value={reportMonth} onChange={(event) => { setReportMonth(event.target.value); setReportDateFrom(""); setReportDateTo(""); }} />
              </label>
              <label style={{ display: "grid", gap: 6 }}>From date<input type="date" value={reportDateFrom} onChange={(event) => { setReportDateFrom(event.target.value); setReportMonth(""); }} /></label>
              <label style={{ display: "grid", gap: 6 }}>To date<input type="date" value={reportDateTo} onChange={(event) => { setReportDateTo(event.target.value); setReportMonth(""); }} /></label>
              <button className="theme-toggle" disabled={!reportMonth && !reportDateFrom && !reportDateTo} onClick={() => { setReportMonth(""); setReportDateFrom(""); setReportDateTo(""); }} type="button">All time</button>
              <span className="insight-helper">{reportMonth ? `Showing ${reportMonth}` : reportDateFrom || reportDateTo ? `Showing ${reportDateFrom || "earliest"} to ${reportDateTo || "latest"}` : "Showing all recorded transactions"}</span>
            </div>
            {summaryError && <p role="alert">{summaryError}</p>}
            {!summary && !summaryError && <p>Loading report...</p>}
            {summary && <>
              <div className="placeholder-grid" style={{ marginTop: 20 }}>
                <article className="metric-card"><p>Income</p><strong>{formatCurrency(summary.total_income ?? summary.total_credit)}</strong></article>
                <article className="metric-card"><p>Expenses</p><strong>{formatCurrency(summary.total_expenses ?? summary.total_spend)}</strong></article>
                <article className="metric-card"><p>Investments</p><strong>{formatCurrency(summary.total_investments ?? 0)}</strong></article>
                <article className="metric-card"><p>Net cash flow</p><strong>{formatCurrency(summary.net_cash_flow ?? summary.net_balance)}</strong></article>
                <article className="metric-card"><p>Transactions</p><strong>{summary.total_transactions}</strong></article>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 24 }}>
                <button className="theme-toggle" onClick={() => window.open(`${API_BASE_URL}/export/csv`, "_blank", "noopener,noreferrer")} type="button">Export CSV</button>
                <button className="theme-toggle" onClick={() => window.open(`${API_BASE_URL}/export/json`, "_blank", "noopener,noreferrer")} type="button">Export JSON</button>
              </div>
            </>}
          </section>

          <section className="metric-card" aria-labelledby="report-budget-title" style={{ marginTop: 24 }}>
            <p className="eyebrow">Monthly planning</p>
            <h2 id="report-budget-title">Budget performance</h2>
            {(reportDateFrom || reportDateTo) && <p>Budget performance is available for a selected month, not a custom date range.</p>}
            {!reportDateFrom && !reportDateTo && <>{budgetError && <p role="alert">{budgetError}</p>}
            {!budgetError && !currentBudget && <p>Loading budget performance...</p>}
            {currentBudget && !currentBudget.overall && <p>No overall monthly budget is set. Add one from Dashboard to track progress here.</p>}
            {currentBudget?.overall && <div style={{ display: "grid", gap: 14, marginTop: 20 }}>
              <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 12 }}><strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{formatCurrency(currentBudget.overall.spent)} of {formatCurrency(currentBudget.overall.limit)}</strong><span>{currentBudget.month} · {currentBudget.overall.percent_used}% used</span></div>
              <div className="budget-progress"><span className={currentBudget.overall.percent_used >= 100 ? "budget-danger" : currentBudget.overall.percent_used >= 80 ? "budget-warning" : "budget-healthy"} style={{ width: `${Math.min(currentBudget.overall.percent_used, 100)}%` }} /></div>
              <p className={currentBudget.overall.percent_used >= 100 ? "budget-danger-text" : currentBudget.overall.percent_used >= 80 ? "budget-warning-text" : "budget-healthy-text"}>{currentBudget.overall.percent_used >= 100 ? `Overall budget exceeded by ${formatCurrency(Math.abs(currentBudget.overall.remaining))}.` : `${formatCurrency(currentBudget.overall.remaining)} remains.`}</p>
              {currentBudget.categories.map((item) => <article className="insight-card" key={item.category}>
                <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 12 }}><strong style={{ display: "inline", margin: 0, fontSize: "inherit" }}>{item.category}</strong><span>{formatCurrency(item.spent)} of {formatCurrency(item.limit)}</span></div>
                <div className="budget-progress" style={{ marginTop: 10 }}><span className={item.percent_used >= 100 ? "budget-danger" : item.percent_used >= 80 ? "budget-warning" : "budget-healthy"} style={{ width: `${Math.min(item.percent_used, 100)}%` }} /></div>
                <p className={item.percent_used >= 100 ? "budget-danger-text" : item.percent_used >= 80 ? "budget-warning-text" : "budget-healthy-text"} style={{ marginTop: 8 }}>{item.percent_used}% used · {item.percent_used >= 100 ? `exceeded by ${formatCurrency(Math.abs(item.remaining))}` : `${formatCurrency(item.remaining)} remains`}</p>
              </article>)}
            </div>}</>}
          </section>

          <section className="metric-card" aria-labelledby="trend-title" style={{ marginTop: 24 }}>
            <p className="eyebrow">Monthly spending</p>
            <h2 id="trend-title">Spend trend</h2>
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

          <section className="metric-card" aria-labelledby="report-category-title" style={{ marginTop: 24 }}>
            <p className="eyebrow">Spending distribution</p>
            <h2 id="report-category-title">Category breakdown</h2>
            {summary && categoryEntries.length === 0 && <p>No category data yet.</p>}
            <div style={{ display: "grid", gap: 16, marginTop: 24 }}>
              {categoryEntries.map(([category, amount]) => (
                <div key={category}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 16, marginBottom: 7 }}><strong>{category}</strong><span>{formatCurrency(amount)} · {summary?.total_spend ? Math.round((amount / summary.total_spend) * 100) : 0}%</span></div>
                  <div style={{ height: 12, overflow: "hidden", borderRadius: 999, background: "#ede9fe" }}>
                    <div style={{ width: `${(amount / maxCategorySpend) * 100}%`, height: "100%", borderRadius: "inherit", background: "#7c3aed" }} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>}

        {activePage === "Profile" && (
          <section className="metric-card" aria-labelledby="profile-title">
            <p className="eyebrow">Single-user setup</p>
            <h2 id="profile-title">Profile & financial preferences</h2>
            <p style={{ marginTop: 10 }}>Save your preferences and goals. Do not enter passwords, card numbers, PINs, or bank credentials.</p>
            {loadingProfile && <p>Loading profile...</p>}
            <form onSubmit={saveProfile} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 16, marginTop: 24 }}>
              <label>Display name<input required value={profileForm.display_name} onChange={(event) => setProfileForm((form) => ({ ...form, display_name: event.target.value }))} /></label>
              <label>Gmail address (optional)<input placeholder="you@gmail.com" type="email" value={profileForm.email} onChange={(event) => setProfileForm((form) => ({ ...form, email: event.target.value }))} /></label>
              <label>Currency<input maxLength={3} value={profileForm.currency} onChange={(event) => setProfileForm((form) => ({ ...form, currency: event.target.value.toUpperCase() }))} /></label>
              <label>Time zone<input value={profileForm.timezone} onChange={(event) => setProfileForm((form) => ({ ...form, timezone: event.target.value }))} /></label>
              <label>Monthly income target<input min="0.01" step="0.01" type="number" value={profileForm.monthly_income_target} onChange={(event) => setProfileForm((form) => ({ ...form, monthly_income_target: event.target.value }))} /></label>
              <label>Savings goal<input min="0.01" step="0.01" type="number" value={profileForm.savings_goal} onChange={(event) => setProfileForm((form) => ({ ...form, savings_goal: event.target.value }))} /></label>
              <label>Investment goal<input min="0.01" step="0.01" type="number" value={profileForm.investment_goal} onChange={(event) => setProfileForm((form) => ({ ...form, investment_goal: event.target.value }))} /></label>
              <label>Starting balance (optional)<input step="0.01" type="number" value={profileForm.starting_balance} onChange={(event) => setProfileForm((form) => ({ ...form, starting_balance: event.target.value }))} /></label>
              <label>Gmail sync preference<select value={profileForm.gmail_sync_frequency} onChange={(event) => setProfileForm((form) => ({ ...form, gmail_sync_frequency: event.target.value }))}><option value="manual">Manual only</option><option value="daily">Daily</option><option value="weekly">Weekly</option></select></label>
              <label style={{ gridColumn: "1 / -1" }}>Financial priorities (comma-separated)<input placeholder="Save more, Control spending, Build emergency fund" value={profileForm.priorities} onChange={(event) => setProfileForm((form) => ({ ...form, priorities: event.target.value }))} /></label>
              <label style={{ gridColumn: "1 / -1" }}>Account labels (comma-separated)<input placeholder="Savings Account, Credit Card, Investment Account" value={profileForm.account_labels} onChange={(event) => setProfileForm((form) => ({ ...form, account_labels: event.target.value }))} /></label>
              <div style={{ gridColumn: "1 / -1" }}><button className="theme-toggle" disabled={savingProfile} type="submit">{savingProfile ? "Saving..." : "Save profile"}</button></div>
            </form>
            {profileStatus && <p role="status" style={{ marginTop: 18 }}>{profileStatus}</p>}

            <section className="insight-card" aria-labelledby="profile-gmail-title" style={{ marginTop: 28 }}>
              <h3 id="profile-gmail-title" style={{ margin: 0, fontSize: "1rem" }}>Gmail transaction connection</h3>
              <p style={{ marginTop: 10 }}>{gmailConnectionMessage || "Checking Gmail connection..."}</p>
              {gmailConnected === false && <button className="theme-toggle" onClick={() => window.location.assign(`${API_BASE_URL}/auth/google`)} style={{ marginTop: 8 }} type="button">Connect Gmail securely</button>}
              {gmailConnected && <p className="budget-healthy-text" style={{ marginTop: 10 }}>Gmail is connected{connectedGmailAddress ? ` as ${connectedGmailAddress}` : ""}. You can sync transaction emails from Dashboard.</p>}
              {profileForm.gmail_sync_frequency !== "manual" && <p style={{ marginTop: 10 }}>Automatic {profileForm.gmail_sync_frequency} sync runs while the backend is running. The scheduler checks every 15 minutes.</p>}
              {profileForm.gmail_sync_frequency !== "manual" && !scheduledSyncDetails && <p style={{ marginTop: 10 }}>No automatic sync has run yet.</p>}
              {scheduledSyncDetails && <p role="status" style={{ marginTop: 10 }}>Last automatic sync: {new Date(scheduledSyncDetails.ranAt).toLocaleString()} ({scheduledSyncDetails.status === "success" ? "completed" : "failed"}).</p>}
              <div style={{ marginTop: 18 }}>
                <h4 style={{ margin: 0, fontSize: "0.95rem" }}>Recent sync runs</h4>
                {gmailSyncRunsError && <p role="alert" style={{ marginTop: 8 }}>{gmailSyncRunsError}</p>}
                {!gmailSyncRunsError && gmailSyncRuns.length === 0 && <p style={{ marginTop: 8 }}>No Gmail sync runs yet.</p>}
                <div style={{ display: "grid", gap: 8, marginTop: 10 }}>
                  {gmailSyncRuns.map((run) => <p key={run._id} style={{ margin: 0 }}>{run.source === "scheduled" ? "Automatic" : "Manual"} sync · {run.status === "success" ? "Completed" : "Failed"} · {new Date(run.created_at).toLocaleString()}{run.status === "success" ? ` · ${run.summary?.inserted_transactions ?? 0} added, ${run.summary?.review_required ?? 0} need review` : ""}</p>)}
                </div>
              </div>
              <div style={{ marginTop: 18 }}>
                <h4 style={{ margin: 0, fontSize: "0.95rem" }}>Recent Gmail processing</h4>
                {gmailLogsError && <p role="alert" style={{ marginTop: 8 }}>{gmailLogsError}</p>}
                {!gmailLogsError && gmailLogs.length === 0 && <p style={{ marginTop: 8 }}>No Gmail processing activity yet.</p>}
                <div style={{ display: "grid", gap: 8, marginTop: 10 }}>
                  {gmailLogs.map((log) => <p key={log._id} style={{ margin: 0 }}>{formatGmailStatus(log.status)}{log.subject ? ` · ${log.subject}` : ""}{log.created_at ? ` · ${new Date(log.created_at).toLocaleString()}` : ""}</p>)}
                </div>
              </div>
            </section>
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

        {activePage === "Dashboard" && editingGmailLog && (
          <div role="presentation" style={{ position: "fixed", inset: 0, zIndex: 30, display: "grid", placeItems: "center", padding: 20, background: "rgba(15, 23, 42, .58)" }}>
            <section aria-labelledby="edit-gmail-review-title" aria-modal="true" role="dialog" style={{ width: "min(100%, 520px)", padding: 24, borderRadius: 16, color: "#172033", background: "#fff", boxShadow: "0 24px 56px rgba(0,0,0,.28)" }}>
              <p className="eyebrow">Gmail review</p>
              <h2 id="edit-gmail-review-title">Edit and add transaction</h2>
              {reviewError && <p role="alert" style={{ color: "#b91c1c" }}>{reviewError}</p>}
              <label style={{ display: "grid", gap: 6, marginTop: 20 }}>Date<input type="date" value={editDate} onChange={(event) => setEditDate(event.target.value)} /></label>
              <label style={{ display: "grid", gap: 6, marginTop: 14 }}>Merchant<input value={editMerchant} onChange={(event) => setEditMerchant(event.target.value)} /></label>
              <label style={{ display: "grid", gap: 6, marginTop: 14 }}>Amount<input min="0.01" step="0.01" type="number" value={editAmount} onChange={(event) => setEditAmount(event.target.value)} /></label>
              <label style={{ display: "grid", gap: 6, marginTop: 14 }}>Category<input value={editCategory} onChange={(event) => setEditCategory(event.target.value)} /></label>
              <label style={{ display: "grid", gap: 6, marginTop: 14 }}>Transaction type<select value={editTransactionType} onChange={(event) => setEditTransactionType(event.target.value)}><option value="expense">Expense</option><option value="income">Income</option><option value="investment">Investment</option><option value="transfer">Transfer</option><option value="refund">Refund</option><option value="debit">Debit</option><option value="credit">Credit</option></select></label>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
                <button className="theme-toggle" onClick={() => setEditingGmailLog(null)} type="button">Cancel</button>
                <button className="theme-toggle" disabled={reviewingId === editingGmailLog._id} onClick={saveEditedGmailReview} type="button">Add transaction</button>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

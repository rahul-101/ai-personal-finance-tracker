# Backend Schema

MongoDB database name defaults to `finance_tracker`. `_id` is MongoDB `ObjectId` and is serialized to a string for API clients.

## Collections

### `transactions`

Core finance record.

| Field | Type | Notes |
|---|---|---|
| `date` | ISO date string | Required |
| `merchant` | string | Required, normalized |
| `amount` | number | Positive |
| `category` | string | Required |
| `source` | enum | `manual`, `email`, `receipt`, `bill` |
| `transaction_type` | enum | `income`, `expense`, `investment`, `transfer`, `refund`, legacy `debit`/`credit` |
| `status` | enum | `confirmed`, `review_required`, `rejected` |
| `created_at`, `reviewed_at` | datetime | Lifecycle timestamps |
| `review_decision`, `review_note` | string | Optional review audit |
| `gmail_message_id` | string | Unique/sparse when email-derived |
| `email_sender`, `notes` | string | Optional context |

Indexes: `created_at` descending, `date` descending, unique sparse `gmail_message_id`.

### `gmail_logs`

Per-email processing/audit record. Relevant statuses include `transaction_inserted`, `review_required_not_inserted`, `review_approved`, `review_rejected`, `duplicate_skipped`, and `processing_failed`.

Important fields: `gmail_message_id`, `from`, `subject`, `reason`, `error`, `ai_confidence`, `proposed_transaction`, `transaction_id`, `created_at`, `reviewed_at`.

`proposed_transaction` contains only the candidate date, merchant, amount, category, and transaction type needed for human review.

### `gmail_sync_runs`

One safe audit record per manual or scheduled sync: `source`, `status`, compact `summary`, truncated `error`, `created_at`.

### `gmail_tokens`

Encrypted Gmail OAuth token material keyed by user/provider. Treat as secret; never expose through frontend APIs.

### `oauth_states`

Short-lived OAuth state records with `expires_at`; MongoDB TTL index removes expired records.

### `budgets`

One document per `scope` + `month`.

| Field | Type |
|---|---|
| `scope` | `single_user` |
| `month` | `YYYY-MM` |
| `monthly_limit` | positive number or null |
| `category_limits` | map of category to positive limit |

Unique index: `scope`, `month`.

### `profile`

One single-user preference document: display name, optional email, currency, timezone, targets/goals, priorities, account labels, Gmail sync frequency, and last scheduled-sync metadata. Never store passwords, PINs, card numbers, or bank credentials.

### `receipts`, `bills`, `ai_insights`

- Receipts: upload/OCR metadata and optional transaction relationship.
- Bills: provider, bill type, amount, due date, status, file metadata.
- AI insights: validated generated insight, provider/model metadata, creation time.

## Key API groups

| Group | Examples |
|---|---|
| Transactions | `POST/GET /transactions`, `PATCH /transactions/{id}/review` |
| Gmail | `/auth/google`, `/gmail/status`, `/gmail/sync`, `/gmail-review-logs/{id}` |
| Dashboard | `/dashboard/summary`, `/dashboard/review-required`, `/dashboard/gmail-sync-runs` |
| Budget/Profile | `/budgets/current`, `/budgets/{month}`, `/profile` |
| AI | `/ai/configuration`, `/ai/test`, `/ai/insights` |
| Uploads/Export | `/receipts/upload`, `/bills/upload`, `/export/csv`, `/export/json` |

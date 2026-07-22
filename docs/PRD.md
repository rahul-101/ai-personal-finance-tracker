# Product Requirements Document (PRD)

## Product

**Name:** FinSight — AI Personal Finance Tracker  
**Audience:** One individual managing their own finances.  
**Problem:** Financial activity is fragmented across transaction emails, receipts, bills, and manual records. The user needs one private place to understand cash flow and act on uncertain data.

## Goals

1. Give the user an accurate financial picture across income, expenses, investments, transfers, and refunds.
2. Reduce manual work by importing Gmail transaction alerts and extracting receipt/bill data.
3. Keep AI assistance provider-agnostic and human-reviewed for uncertain data.
4. Make financial data understandable through visual, responsive dashboards and reports.
5. Keep the product private, single-user, and safe by default.
6. Financial, tax, investment, or credit advice.

## Non-goals

- Multi-user accounts, teams, role management, or billing.
- Bank credential storage or direct bank-account access.
- Autonomous posting of low-confidence AI interpretations.

## User stories

- As the user, I can add a transaction and classify its financial type.
- As the user, I can connect Gmail and sync transaction-related email alerts.
- As the user, I can approve, correct, or ignore uncertain email-derived records.
- As the user, I can upload receipts and bills for extraction.
- As the user, I can view cash flow, spending categories, merchants, budgets, reports, and AI insights.
- As the user, I can choose an AI provider without changing finance workflows.
- As the user, I can filter, review, and export my own data.

## Functional requirements

| Area         | Requirement                                                                           | Status      |
| ------------ | ------------------------------------------------------------------------------------- | ----------- |
| Transactions | Create, list, paginate, filter by status/type/date/category, and search               | Implemented |
| Review       | Approve/edit/reject transaction reviews and Gmail log-only reviews                    | Implemented |
| Gmail        | OAuth, encrypted token storage, manual sync, status, disconnect, scheduled local sync | Implemented |
| AI           | Provider configuration, provider test, validated classification and insights          | Implemented |
| Documents    | Receipt/bill upload, OCR, enrichment, history, due bills                              | Implemented |
| Planning     | Monthly overall/category budgets and report performance                               | Implemented |
| Reports      | Month or custom-range financial summaries and exports                                 | Implemented |
| Profile      | Single-user preferences, goals, currency, timezone, Gmail preference                  | Implemented |
| UI           | Responsive React dashboard, dark mode, visual KPIs/charts, accessible controls        | Implemented |

## Success criteria

- A user can reach a trusted transaction record from email, review, receipt, bill, or manual entry.
- Low-confidence imports never affect financial totals until explicitly resolved.
- Provider changes require configuration only, not frontend/business-logic changes.
- The dashboard remains understandable on desktop and mobile.

## Product metrics for future measurement

- Share of imported records resolved without correction.
- Time from Gmail sync to review resolution.
- Number of active filters/reports/export actions.
- Budget threshold and AI-insight engagement.

## Risks and mitigations

| Risk                    | Mitigation                                                                    |
| ----------------------- | ----------------------------------------------------------------------------- |
| AI misclassification    | Strict validation, confidence threshold, human review workflow                |
| Sensitive data exposure | Encryption, masked email evidence, no secret display, local single-user scope |
| Gmail OAuth expiry      | Explicit reconnect status and secure reconnect workflow                       |
| Misleading reports      | Date/month validation and clear monthly-budget limitation for custom ranges   |

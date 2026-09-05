# KAPA Bank — Bank Transaction Management System & Multi-User Portal

**Academic DBMS Project**  
**Database:** Oracle Autonomous Database (Enterprise Cloud / PDB)  
**Backend:** Python Flask 3.1.3  
**Security:** Role-Based Access Control (RBAC), Customer Isolation (IDOR Prevention), CSRF Tokens, Werkzeug Password Hashing  
**Statements:** On-Demand PDF (`fpdf2`) & CSV Ledger Generation  

---

## 1. Project Overview

**KAPA Bank** is a web-based banking management system designed to demonstrate core Database Management System (DBMS) principles through a realistic, multi-user banking application. 

The application implements a strict two-tier role architecture:
1. **Self-Service Customer Portal:** Allows authenticated customers to manage their accounts, execute cash deposits and withdrawals, perform atomic inter-account fund transfers, search transaction histories, and download official PDF/CSV bank statements.
2. **Administrative Console (`/admin`):** Provides bank administrators with system-wide analytics, customer provisioning, account blocking/activation, system transaction monitoring, high-level SQL aggregate reports, an immutable security audit trail, and an interactive ACID transaction control laboratory.

---

## 2. Key Architecture & DBMS Concepts Demonstrated

### A. Atomicity & ACID Guarantees (`COMMIT`, `ROLLBACK`, `SAVEPOINT`)
- **Domestic Fund Transfers:** Transfers execute atomically across two accounts using a double-entry ledger pattern (`TRANSFER_OUT` from sender, `TRANSFER_IN` to recipient). Both balance updates and transfer records succeed together, or the entire transaction rolls back.
- **Savepoints:** Used during multi-step financial operations so that partial failure allows rollback to a known intermediate savepoint without corrupting prior state.
- **Interactive Laboratory (`/admin/transaction-control`):** An administrative demo page that lets evaluators execute live `COMMIT`, `ROLLBACK`, `SAVEPOINT`, and `RESET` commands on a designated demonstration account (`DEMO_ACCOUNT_ID = 21`) to observe database memory buffer vs datafile persistence.

### B. Deadlock-Free Concurrency Control (`SELECT ... FOR UPDATE`)
- When transferring funds between Account A and Account B, row-level exclusive locks are acquired in strictly ascending numeric order:
  ```python
  first_acc_id = min(from_account, to_account)
  second_acc_id = max(from_account, to_account)
  # Lock first_acc_id, then lock second_acc_id
  ```
- This mathematically breaks the Coffman cyclic wait condition, preventing database deadlocks even under high concurrent load.

### C. Strict Customer Data Isolation & IDOR Prevention
- Browser-supplied customer IDs or account IDs are never trusted blindly.
- Every financial query checks ownership directly against the authenticated user's session:
  ```sql
  SELECT balance, status FROM bank_accounts 
  WHERE account_id = :aid AND customer_id = :cid FOR UPDATE
  ```
- Attempting to inspect or transact on an account belonging to another customer results in an immediate authorization rejection (`403 Forbidden`).

### D. Advanced SQL Aggregations & Views
- Demonstrates conditional aggregations using `SUM(CASE WHEN ... THEN ... ELSE 0 END)`.
- Multi-table `JOIN` operations connecting `bank_transactions`, `bank_accounts`, and `customers`.
- Grouping distributions via `GROUP BY account_type` and `GROUP BY transaction_type`.
- Sorting and limiting via `ORDER BY balance DESC FETCH FIRST 5 ROWS ONLY`.
- Pre-compiled database views: `account_summary` and `transaction_history`.

### E. Financial Arithmetic with Fixed-Point Precision
- All monetary transactions strictly utilize Python's `decimal.Decimal` with 2 decimal places to eliminate floating-point representation drift.

---

## 3. Database Schema

The system uses 6 core relational tables in Oracle Autonomous Database:

| Table Name | Description | Key Constraints |
|---|---|---|
| `CUSTOMERS` | Customer personal profiles | `PK: customer_id`, `UQ: email`, `UQ: phone` |
| `USERS` | Authentication credentials & roles | `PK: user_id`, `FK: customer_id`, `UQ: email`, `CHK: role IN ('CUSTOMER', 'ADMIN')` |
| `BANK_ACCOUNTS` | Deposit & current accounts | `PK: account_id`, `FK: customer_id`, `UQ: account_number`, `CHK: balance >= 0` |
| `BANK_TRANSACTIONS` | Detailed ledger entries | `PK: transaction_id`, `FK: account_id`, `CHK: amount > 0`, `CHK: status` |
| `BANK_TRANSFERS` | Inter-account payment records | `PK: transfer_id`, `FK: from_account`, `FK: to_account`, `CHK: from <> to` |
| `AUDIT_LOG` | Immutable security audit log | `PK: audit_id`, `FK: user_id`, `timestamp` |

---

## 4. Evaluation Credentials

The database comes pre-seeded with the following credentials for testing and evaluation:

### System Administrator
- **Email:** `admin@kapabank.com`
- **Password:** `Admin@Kapa2026`
- **Access:** Complete access to `/admin`, Customer Management, Account Status Controls, System Monitoring, Reports, Audit Trail, and ACID Demo.

### Customer 1 (Rahul Kumar)
- **Email:** `rahul@example.com`
- **Password:** `Customer@123`
- **Access:** Personal Customer Portal, My Accounts, Instant Deposits/Withdrawals, Domestic Transfers, PDF Statements.

### Customer 2 (Kanishka)
- **Email:** `saikanish2007@gmail.com`
- **Password:** `Customer@123`
- **Access:** Personal Customer Portal (Used to verify customer data isolation against Customer 1).

*Note: You can also register a brand-new customer account anytime via the "Open Account" button (`/register`).*

---

## 5. Local Setup & Execution

### Prerequisites
- Python 3.10+ (Recommended: Python 3.12 or 3.14)
- Oracle Client / Oracle Cloud Wallet credentials
- Virtual Environment (`venv`)

### Installation Steps

1. **Activate Virtual Environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables (`.env`):**
   ```env
   ORACLE_USER=SYSTEMS
   ORACLE_PASSWORD=your_database_password
   ORACLE_DSN=kapabank_low
   ORACLE_WALLET_PATH=/path/to/oracle_wallet/KAPABank
   ORACLE_WALLET_PASSWORD=your_wallet_password
   FLASK_SECRET_KEY=generate_random_secret_key_here
   PORT=5001
   ```

4. **Run Database Migrations (Additive):**
   ```bash
   python3 run_migration.py
   python3 bootstrap_admin.py
   ```

5. **Run Test Suites:**
   ```bash
   python3 test_system.py
   python3 test_banking_operations.py
   ```

6. **Start Application Server:**
   ```bash
   python3 app.py
   ```
   Open `http://localhost:5001` in your browser.

---

## 6. Vercel Cloud Deployment

The application is deployed on Vercel:
- Production URL: `https://kapa-bank.vercel.app`
- Cloud Wallet Reconstruction: In serverless environments, Vercel decodes `ORACLE_TNSNAMES` and `ORACLE_EWALLET_PEM` from Base64 into `/tmp/kapa_oracle_wallet` on-the-fly.
- Static assets are served via `public/style.css` (synchronized with `static/style.css`).

---

## 7. Compliance & Security Notice
This software is developed strictly for academic demonstration and laboratory evaluation of DBMS concepts at Vellore Institute of Technology. Passwords are stored exclusively as one-way scrypt/pbkdf2 hashes via Werkzeug. CSRF tokens protect all state-modifying requests.

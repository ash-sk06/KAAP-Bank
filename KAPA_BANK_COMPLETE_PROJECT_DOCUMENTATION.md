# KAPA Bank — Complete Project Documentation, ER Model, ER &rarr; Relational Mapping & DBMS Analysis

---

## 1. Project Overview & Objective

### 1.1 Project Identification
- **Project Name:** KAPA Bank
- **Domain:** Bank Transaction Management System / Academic DBMS Application
- **Course Context:** DBMS Laboratory Project Evaluation at Vellore Institute of Technology (VIT)
- **Database Engine:** Oracle Autonomous Database Cloud (`kapabank_low`)
- **Backend Framework:** Python 3.14 / Flask 3.1
- **Live Cloud Deployment:** [`https://kapa-dbms.vercel.app`](https://kapa-dbms.vercel.app)

### 1.2 Academic Project Objective
KAPA Bank is an academic database management application developed to demonstrate fundamental and advanced database concepts:
1. **Relational Data Modeling:** Designing and normalizing database relations across customers, bank accounts, transaction histories, transfers, and security audit logs.
2. **ACID Transactions:** Demonstrating Atomicity, Consistency, Isolation, and Durability across real-world banking operations (deposits, debits, inter-account transfers).
3. **Transaction Control Language (TCL):** Providing a dedicated, live interactive sandbox demonstrating `COMMIT`, `ROLLBACK`, and `SAVEPOINT`.
4. **Concurrency Control:** Implementing canonical row-level locking (`SELECT ... FOR UPDATE`) to prevent lost updates, race conditions, and deadlocks during concurrent fund transfers.
5. **Data Isolation & Access Governance:** Enforcing strict Role-Based Access Control (RBAC) and customer-level data isolation where customers can only query and download statements for accounts they own.

> [!NOTE]
> **Academic Simulation Notice:** KAPA Bank is an educational laboratory demonstration and coursework evaluation project. It is **not** a licensed financial institution or commercial banking service.

---

## 2. Complete Technology Stack Inventory

| Component | Technology | Specific Version | Architectural Role |
|---|---|---|---|
| **Programming Language** | Python | 3.14.7 | Server-side execution and business logic |
| **Web Framework** | Flask | 3.1.3 | HTTP routing, session management, and template rendering |
| **Database** | Oracle Autonomous Database | Oracle Cloud 19c/23ai | Multi-model relational persistence, integrity constraints, and ACID transactions |
| **Database Driver** | python-oracledb | 4.0.2 | Native thin driver connecting to Oracle Cloud via encrypted TLS wallet |
| **Template Engine** | Jinja2 | 3.1.6 | Dynamic HTML rendering with server-side variable interpolation and filters |
| **PDF Generation** | fpdf2 | 2.8.8 | Server-side vector generation of downloadable bank account statements (`%PDF-`) |
| **Security & Hashing** | Werkzeug | 3.1.8 | One-way cryptographic password hashing using the `Scrypt` key-derivation function |
| **Frontend Styling** | Vanilla CSS3 | Custom System | Accessible, responsive banking stylesheet with WCAG 2.2 AA compliance |
| **Cloud Hosting** | Vercel Serverless | Python Runtime | Serverless deployment connected to Oracle Autonomous Cloud Database |

---

## 3. System Architecture

```text
USER / CLIENT BROWSER
       |
       |  (HTTPS / TLS Requests)
       v
VERCEL EDGE ROUTING & REVERSE PROXY
       |
       |  (WSGI Request Context)
       v
FLASK APPLICATION SERVER (app.py)
  +-------------------------------------------------------------+
  |  - Session & CSRF Validation (auth.py)                      |
  |  - RBAC Decorators (@login_required, @admin_required)       |
  |  - Data Validation (validate_positive_amount, Decimal)       |
  |  - ReportLab / fpdf2 Statement Engine (reports.py)          |
  +-------------------------------------------------------------+
       |
       |  (Parameterized SQL Queries / Bound Parameters)
       v
DATABASE ACCESS LAYER (database.py)
  +-------------------------------------------------------------+
  |  - python-oracledb thin client                             |
  |  - Encrypted Oracle Cloud Wallet (ewallet.pem, tnsnames.ora)|
  |  - Dictionary cursor formatters (dictfetchall, dictfetchone)|
  +-------------------------------------------------------------+
       |
       |  (Encrypted TCPS over Port 1522)
       v
ORACLE AUTONOMOUS CLOUD DATABASE
  +-------------------------------------------------------------+
  |  - Relations: CUSTOMERS, BANK_ACCOUNTS, BANK_TRANSACTIONS,   |
  |               BANK_TRANSFERS, USERS, AUDIT_LOG              |
  |  - Constraints: PK, FK, UNIQUE, CHECK, IDENTITY SEQUENCES   |
  |  - Transaction Engine: Row Locks, Undo Blocks, Redo Logs    |
  +-------------------------------------------------------------+
```

### Architectural Pipeline Explanation:
1. **Request Intake & CSRF Protection:** Incoming POST requests pass through `validate_csrf()`, comparing the submitted form token with the session's secret token using constant-time string comparison (`secrets.compare_digest`).
2. **Authentication & Authorization:** Routes decorated with `@customer_required` verify `session['customer_id']` and enforce strict ownership checks before query execution. Routes decorated with `@admin_required` reject non-admin users with HTTP 403.
3. **Database Connection & Execution:** `database.get_connection()` acquires a connection to the Oracle Cloud schema. All queries use bound bind variables (`:1, :2`), preventing SQL injection vulnerabilities.
4. **Transaction Demarcation:** Atomic actions execute within explicit `try...except...finally` blocks where successes issue `connection.commit()` and failures execute `connection.rollback()`.
5. **PDF Statement Pipeline:** `reports.generate_pdf_statement()` queries the customer's transaction ledger, builds a binary PDF document in memory using `io.BytesIO`, and streams it as a direct download.

---

## 4. Complete System Functionality

### 4.1 Public & Unauthenticated Features
- **Landing Redirection:** Unauthenticated users accessing `/` are automatically redirected to `/login`.
- **Academic Evaluation Banner:** Every screen renders an academic coursework notice.
- **Dynamic Credentials Directory (`/credentials`):** Evaluators can review active login credentials dynamically fetched from the database.
- **Customer Self-Registration (`/register`):** New users can create a customer profile, establish a user login, and automatically provision a zero-balance `SAVINGS` or `CURRENT` bank account.

### 4.2 Customer Banking Features
- **Personal Dashboard (`/dashboard`):** Real-time aggregation of total balance, owned accounts, and 5 most recent transactions.
- **Account Management (`/accounts` & `/accounts/<id>`):** Detailed view of book balances, account status, and transaction history.
- **Atomic Deposits (`/deposit`):** Deposit funds into active accounts with real-time balance increments.
- **Atomic Withdrawals (`/withdraw`):** Safe debiting with checks against insufficient funds and negative balance prevention.
- **Inter-Account Transfers (`/transfer`):** Transfer money between two bank accounts with deadlock-free row locking.
- **Transaction History (`/transactions`):** Full ledger with filtering by transaction type (`DEPOSIT`, `WITHDRAWAL`, `TRANSFER_IN`, `TRANSFER_OUT`) and status (`COMMITTED`, `ROLLED_BACK`).
- **Statement Generation (`/statements`):** Download official bank statements as vector PDFs or CSV exports.
- **Profile & Password Management (`/profile`):** View customer details and update passwords with real-time database synchronization.

### 4.3 Demo Role Restrictions (TCL Sandbox Only)
- Dedicated demo account (`demo@kapabank.com`) is strictly isolated to `/transaction-control`.
- Blocked from real banking routes (`/transfer`, `/deposit`, `/withdraw`) to preserve sandbox integrity.
- Interactive execution of `COMMIT`, `ROLLBACK`, `SAVEPOINT` (partial rollback), and `RESET` (restores demo account balance to ₹10,000.00).

### 4.4 Administrator Features
- **Operations & Governance Dashboard (`/admin`):** Bank-wide metrics including total core deposits, active accounts count, and transaction volumes.
- **Customer Registry (`/admin/customers`):** Search customer profiles by legal name or email, view linked accounts, and inspect authentication status.
- **Account Provisioning & Security (`/admin/accounts`):** Open new accounts and update operational status (`ACTIVE` &harr; `BLOCKED` &harr; `CLOSED`).
- **System-Wide Transaction Monitoring (`/admin/transactions`):** Monitor all ledger entries across the institution.
- **SQL Aggregate Reports (`/admin/reports`):** Analytic dashboards driven by SQL queries (`GROUP BY`, `SUM CASE`, `ORDER BY ... FETCH FIRST`).
- **Security Audit Trail (`/admin/audit-log`):** Immutable logging of administrative actions, user logins, and status modifications with IP addresses and timestamps.

---

## 5. Complete Database Entities & Relational Schema

The physical schema in the Oracle Autonomous Cloud Database consists of 6 core tables:

### Table 1: `CUSTOMERS`
- **Purpose:** Stores legal identity and contact details for banking patrons.
- **Primary Key:** `customer_id` (NUMBER, Generated Identity)
- **Candidate Keys:** `email` (Unique), `phone` (Unique)
- **Attributes:**
  - `customer_id`: `NUMBER` (PK, Not Null)
  - `name`: `VARCHAR2(100)` (Not Null)
  - `email`: `VARCHAR2(100)` (Unique, Not Null)
  - `phone`: `VARCHAR2(15)` (Unique, Not Null)
  - `address`: `VARCHAR2(200)` (Nullable)

### Table 2: `USERS`
- **Purpose:** Manages authentication credentials, password hashes, and RBAC roles.
- **Primary Key:** `user_id` (NUMBER, Generated Identity)
- **Candidate Keys:** `email` (Unique)
- **Foreign Key:** `customer_id` &rarr; `CUSTOMERS.customer_id` (`ON DELETE CASCADE`, Nullable for Admins)
- **Attributes:**
  - `user_id`: `NUMBER` (PK, Not Null)
  - `email`: `VARCHAR2(100)` (Unique, Not Null)
  - `password_hash`: `VARCHAR2(255)` (Not Null)
  - `display_password`: `VARCHAR2(100)` (Nullable, evaluation aid)
  - `role`: `VARCHAR2(20)` (`DEFAULT 'CUSTOMER'`, `CHECK (role IN ('CUSTOMER', 'ADMIN'))`)
  - `customer_id`: `NUMBER` (FK, Nullable)
  - `is_active`: `NUMBER(1)` (`DEFAULT 1`, `CHECK (is_active IN (0, 1))`)
  - `last_login`: `TIMESTAMP` (Nullable)
  - `created_at`: `TIMESTAMP` (`DEFAULT SYSTIMESTAMP`, Not Null)

### Table 3: `BANK_ACCOUNTS`
- **Purpose:** Stores monetary balances, account types, and operating states.
- **Primary Key:** `account_id` (NUMBER, Generated Identity)
- **Candidate Keys:** `account_number` (Unique)
- **Foreign Key:** `customer_id` &rarr; `CUSTOMERS.customer_id` (Not Null)
- **Attributes:**
  - `account_id`: `NUMBER` (PK, Not Null)
  - `customer_id`: `NUMBER` (FK, Not Null)
  - `account_number`: `VARCHAR2(20)` (Unique, Not Null)
  - `account_type`: `VARCHAR2(20)` (`CHECK (account_type IN ('SAVINGS', 'CURRENT'))`)
  - `balance`: `NUMBER(15,2)` (`DEFAULT 0`, `CHECK (balance >= 0)`)
  - `status`: `VARCHAR2(20)` (`DEFAULT 'ACTIVE'`, `CHECK (status IN ('ACTIVE', 'BLOCKED', 'CLOSED'))`)
  - `created_date`: `DATE` (`DEFAULT SYSDATE`, Not Null)

### Table 4: `BANK_TRANSACTIONS`
- **Purpose:** Immutable ledger of all deposits, withdrawals, and transfer credits/debits.
- **Primary Key:** `transaction_id` (NUMBER, Generated Identity)
- **Foreign Key:** `account_id` &rarr; `BANK_ACCOUNTS.account_id` (Not Null)
- **Attributes:**
  - `transaction_id`: `NUMBER` (PK, Not Null)
  - `account_id`: `NUMBER` (FK, Not Null)
  - `transaction_type`: `VARCHAR2(20)` (`CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT'))`)
  - `amount`: `NUMBER(15,2)` (`CHECK (amount > 0)`)
  - `transaction_date`: `TIMESTAMP` (`DEFAULT SYSTIMESTAMP`, Not Null)
  - `status`: `VARCHAR2(20)` (`DEFAULT 'COMMITTED'`, `CHECK (status IN ('COMMITTED', 'ROLLED_BACK', 'FAILED'))`)

### Table 5: `BANK_TRANSFERS`
- **Purpose:** Captures the end-to-end relationship between two accounts involved in a fund transfer.
- **Primary Key:** `transfer_id` (NUMBER, Generated Identity)
- **Foreign Keys:**
  - `from_account` &rarr; `BANK_ACCOUNTS.account_id` (Sender Role)
  - `to_account` &rarr; `BANK_ACCOUNTS.account_id` (Receiver Role)
- **Attributes:**
  - `transfer_id`: `NUMBER` (PK, Not Null)
  - `from_account`: `NUMBER` (FK, Not Null)
  - `to_account`: `NUMBER` (FK, Not Null)
  - `amount`: `NUMBER(15,2)` (`CHECK (amount > 0)`)
  - `transfer_date`: `TIMESTAMP` (`DEFAULT SYSTIMESTAMP`, Not Null)
  - `status`: `VARCHAR2(20)` (`DEFAULT 'COMMITTED'`, `CHECK (status IN ('COMMITTED', 'ROLLED_BACK', 'FAILED'))`)
- **Table Constraint:** `CONSTRAINT chk_different_accounts CHECK (from_account <> to_account)`

### Table 6: `AUDIT_LOG`
- **Purpose:** System security audit trail recording administrative and transactional actions.
- **Primary Key:** `audit_id` (NUMBER, Generated Identity)
- **Foreign Key:** `user_id` &rarr; `USERS.user_id` (`ON DELETE SET NULL`, Nullable)
- **Attributes:**
  - `audit_id`: `NUMBER` (PK, Not Null)
  - `user_id`: `NUMBER` (FK, Nullable)
  - `action`: `VARCHAR2(50)` (Not Null)
  - `entity_type`: `VARCHAR2(50)` (Nullable)
  - `entity_id`: `NUMBER` (Nullable)
  - `details`: `VARCHAR2(500)` (Nullable)
  - `ip_address`: `VARCHAR2(45)` (Nullable)
  - `created_at`: `TIMESTAMP` (`DEFAULT SYSTIMESTAMP`, Not Null)

---

## 6. Conceptual ER Model & Analysis of Special Cases

### 6.1 Entity Classification
- **`CUSTOMER`:** **Strong Entity.** Possesses independent existence and natural business keys (`email`, `phone`).
- **`BANK_ACCOUNT`:** **Strong Entity.** Uniquely identifiable via its surrogate `account_id` and business key `account_number`.
- **`USER`:** **Strong Entity.** Represents authentication identity; exists independently of whether it is linked to a customer.
- **`BANK_TRANSACTION`:** **Weak / History Entity.** Conceptually dependent on `BANK_ACCOUNT`. A transaction cannot exist without an account.
- **`BANK_TRANSFERS`:** **Associative / Relationship Entity.** Models the M:N transfer relationship between bank accounts where the same entity type participates in two distinct roles (`from_account` and `to_account`).
- **`AUDIT_LOG`:** **Observability Entity.** Stores an immutable historical log of operations.

### 6.2 Special Case: Transfers vs. Transactions
A key question in DBMS viva examinations is: **"Why does KAPA Bank maintain both `BANK_TRANSFERS` and `BANK_TRANSACTIONS`?"**

1. **`BANK_TRANSFERS`** represents the **relational interaction between two accounts**:
   - It captures the transfer agreement: Sender (`from_account`), Receiver (`to_account`), transfer amount, and transfer timestamp.
   - It answers: *"Who sent money to whom, and when?"*
2. **`BANK_TRANSACTIONS`** represents the **individual account ledger entries**:
   - A single transfer generates **two** transactions:
     - A `TRANSFER_OUT` debit record linked to the sender's `account_id`.
     - A `TRANSFER_IN` credit record linked to the receiver's `account_id`.
   - It answers: *"What is the chronological history of debits and credits on this specific account?"*
3. **Data Integrity & Reporting:**
   - Account statements (PDF/CSV) only need to query `BANK_TRANSACTIONS WHERE account_id = :id`.
   - Governance monitoring can inspect `BANK_TRANSFERS` to audit inter-account flows.
   - Both are created atomically within the **same database transaction**.

---

## 7. Database Transactions, Concurrency & ACID Implementation

### 7.1 ACID Properties in KAPA Bank

| ACID Property | Implementation in KAPA Bank | DBMS Mechanism |
|---|---|---|
| **Atomicity** | In a fund transfer, the debit of Account A, credit of Account B, creation of the transfer record, and generation of two transaction records occur as an indivisible unit. If any check fails, the entire transaction is rolled back via `connection.rollback()`. | Oracle Undo Segments & `ROLLBACK` |
| **Consistency** | Database constraints enforce valid state transitions: balances cannot drop below 0 (`CHK_ACCOUNT_BALANCE`), transfer amounts must be positive (`CHK_TRANSFER_AMOUNT`), and source cannot equal destination (`CHK_DIFFERENT_ACCOUNTS`). | Schema Constraints & Triggers |
| **Isolation** | Row-level exclusive locking via `SELECT ... FOR UPDATE` prevents simultaneous transactions from reading stale balances or causing race conditions. | Oracle Multi-Version Concurrency Control (MVCC) & Row Locks |
| **Durability** | Once `connection.commit()` is issued, changes are committed to Oracle Cloud Redo Logs and persist permanently, surviving server restarts and network interruptions. | Oracle Redo Log Buffers & Disk Flushes |

### 7.2 Canonical Deadlock-Free Row Locking
When transferring funds between Account A (ID 1) and Account B (ID 2), concurrent transfers in opposite directions (A &rarr; B and B &rarr; A) can cause a **database deadlock** if locking order is random.

KAPA Bank implements **canonical locking order**:
```python
# app.py: Canonical Deadlock Prevention
acc_first = min(from_account_id, to_account_id)
acc_second = max(from_account_id, to_account_id)

# Acquire exclusive row-level lock on lower ID first
cursor.execute("SELECT account_id, balance, status FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (acc_first,))

# Acquire exclusive row-level lock on higher ID second
cursor.execute("SELECT account_id, balance, status FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (acc_second,))
```
Because all concurrent processes acquire locks in the exact same numerical sequence, circular wait conditions are eliminated, guaranteeing **deadlock-free transfers**.

---

## 8. Functional Dependencies & Normalization Analysis

### 8.1 Functional Dependencies (FDs)
- **`CUSTOMERS`:**
  - $\text{customer\_id} \rightarrow \text{name, email, phone, address}$
  - $\text{email} \rightarrow \text{customer\_id, name, phone, address}$
  - $\text{phone} \rightarrow \text{customer\_id, name, email, address}$
- **`BANK_ACCOUNTS`:**
  - $\text{account\_id} \rightarrow \text{customer\_id, account\_number, account\_type, balance, status, created\_date}$
  - $\text{account\_number} \rightarrow \text{account\_id, customer\_id, account\_type, balance, status, created\_date}$
- **`BANK_TRANSACTIONS`:**
  - $\text{transaction\_id} \rightarrow \text{account\_id, transaction\_type, amount, transaction\_date, status}$
- **`BANK_TRANSFERS`:**
  - $\text{transfer\_id} \rightarrow \text{from\_account, to\_account, amount, transfer\_date, status}$
- **`USERS`:**
  - $\text{user\_id} \rightarrow \text{email, password\_hash, display\_password, role, customer\_id, is\_active, last\_login, created\_at}$
  - $\text{email} \rightarrow \text{user\_id, password\_hash, display\_password, role, customer\_id, is\_active, last\_login, created\_at}$
- **`AUDIT_LOG`:**
  - $\text{audit\_id} \rightarrow \text{user\_id, action, entity\_type, entity\_id, details, ip_address, created\_at}$

### 8.2 Normal Form Derivation
- **1NF:** Satisfied because all column attributes store atomic values and there are no repeating groups.
- **2NF:** Satisfied because every table uses a single-attribute surrogate key. No partial functional dependencies exist.
- **3NF:** Satisfied because all non-prime attributes are directly dependent on the candidate keys. There are no transitive dependencies between non-prime attributes (e.g. customer name is not stored in `BANK_ACCOUNTS`; instead, a foreign key `customer_id` is used).
- **BCNF (Boyce-Codd Normal Form):** Satisfied because for every functional dependency $X \rightarrow Y$, the determinant $X$ is a superkey.

---

## 9. Key SQL Queries Implemented in the Application

### 9.1 Atomic Deposit with Row-Level Lock
```sql
SAVEPOINT before_deposit;

-- Lock account row
SELECT balance, status, account_number 
FROM bank_accounts 
WHERE account_id = :1 
FOR UPDATE;

-- Update balance
UPDATE bank_accounts 
SET balance = :1 
WHERE account_id = :2;

-- Record in ledger
INSERT INTO bank_transactions (account_id, transaction_type, amount, status)
VALUES (:1, 'DEPOSIT', :2, 'COMMITTED');

COMMIT;
```

### 9.2 Inter-Account Transfer with Canonical Locking
```sql
SAVEPOINT before_transfer;

-- Canonical row locking (e.g. min ID then max ID)
SELECT balance, status FROM bank_accounts WHERE account_id = :1 FOR UPDATE;
SELECT balance, status FROM bank_accounts WHERE account_id = :2 FOR UPDATE;

-- Update source balance (debit)
UPDATE bank_accounts SET balance = balance - :amount WHERE account_id = :from_account;

-- Update destination balance (credit)
UPDATE bank_accounts SET balance = balance + :amount WHERE account_id = :to_account;

-- Record transfer
INSERT INTO bank_transfers (from_account, to_account, amount, status)
VALUES (:from_account, :to_account, :amount, 'COMMITTED');

-- Record ledger debits & credits
INSERT INTO bank_transactions (account_id, transaction_type, amount, status)
VALUES (:from_account, 'TRANSFER_OUT', :amount, 'COMMITTED');

INSERT INTO bank_transactions (account_id, transaction_type, amount, status)
VALUES (:to_account, 'TRANSFER_IN', :amount, 'COMMITTED');

COMMIT;
```

### 9.3 SQL Aggregate Analytics & Reporting (`/admin/reports`)
```sql
-- 1. Conditional Aggregates (SUM CASE)
SELECT 
    NVL(SUM(CASE WHEN transaction_type = 'DEPOSIT' THEN amount ELSE 0 END), 0) AS total_deposits,
    NVL(SUM(CASE WHEN transaction_type = 'WITHDRAWAL' THEN amount ELSE 0 END), 0) AS total_withdrawals,
    NVL(SUM(CASE WHEN transaction_type IN ('TRANSFER_IN', 'TRANSFER_OUT') THEN amount ELSE 0 END) / 2, 0) AS total_transfers
FROM bank_transactions 
WHERE status = 'COMMITTED';

-- 2. Breakdown by Transaction Type (GROUP BY)
SELECT transaction_type, COUNT(*) AS count, SUM(amount) AS total
FROM bank_transactions
WHERE status = 'COMMITTED'
GROUP BY transaction_type
ORDER BY total DESC;

-- 3. Top 5 Accounts by Balance (JOIN & Sorting)
SELECT a.account_number, c.name AS customer_name, a.balance
FROM bank_accounts a
JOIN customers c ON a.customer_id = c.customer_id
WHERE a.status = 'ACTIVE'
ORDER BY a.balance DESC
FETCH FIRST 5 ROWS ONLY;
```

---

## 10. DBMS Viva Examination Preparation (30 Key Questions & Answers)

1. **Q: What is the primary purpose of the KAPA Bank system?**  
   *A:* To demonstrate end-to-end relational database management concepts—including ACID properties, concurrency control, transaction isolation, normalization, and security auditing—using Oracle Cloud and Python Flask.
2. **Q: What are the database entities in this project?**  
   *A:* `CUSTOMERS`, `USERS`, `BANK_ACCOUNTS`, `BANK_TRANSACTIONS`, `BANK_TRANSFERS`, and `AUDIT_LOG`.
3. **Q: What is the primary key of `CUSTOMERS`?**  
   *A:* `customer_id`, an auto-incrementing identity column serving as a surrogate primary key.
4. **Q: Why use a surrogate key instead of `email` as the primary key?**  
   *A:* Numeric surrogate keys offer superior indexing performance, stable immutable references, and lower storage overhead in foreign key tables compared to variable-length character strings (`VARCHAR2`).
5. **Q: What is the relationship between `CUSTOMER` and `BANK_ACCOUNT`?**  
   *A:* A 1:M (one-to-many) relationship. One customer can own multiple accounts, but each account belongs to exactly one customer.
6. **Q: How is referential integrity enforced between accounts and customers?**  
   *A:* Through the foreign key constraint `fk_account_customer` in `BANK_ACCOUNTS(customer_id)` referencing `CUSTOMERS(customer_id)`.
7. **Q: Why is `BANK_TRANSFERS` separate from `BANK_TRANSACTIONS`?**  
   *A:* `BANK_TRANSFERS` models the high-level transfer relationship between two accounts (sender and receiver). `BANK_TRANSACTIONS` stores individual account ledger debits and credits needed for statements.
8. **Q: What is an associative entity in this schema?**  
   *A:* `BANK_TRANSFERS` acts as an associative entity capturing the M:N transfer interaction between bank accounts with distinct role names (`from_account` and `to_account`).
9. **Q: In what normal form is the database?**  
   *A:* The schema satisfies Third Normal Form (3NF) and Boyce-Codd Normal Form (BCNF).
10. **Q: Why is there no partial dependency in any relation?**  
    *A:* Because all candidate keys in every relation consist of single attributes. Partial dependency requires a composite key.
11. **Q: What CHECK constraints are implemented?**  
    *A:* `balance >= 0` (no overdraft), `amount > 0` (positive monetary flows), `from_account <> to_account` (prevent self-transfers), and domain checks for `account_type`, `status`, and `role`.
12. **Q: What does `SELECT ... FOR UPDATE` do?**  
    *A:* It acquires an exclusive row-level lock on the selected tuples in Oracle DB, preventing concurrent processes from modifying or reading them until the transaction commits or rolls back.
13. **Q: How does KAPA Bank prevent lost updates?**  
    *A:* By locking the account row with `SELECT FOR UPDATE` before checking the balance and calculating the new balance.
14. **Q: How does the system prevent deadlocks during transfers?**  
    *A:* Canonical lock ordering. The application sorts account IDs and always locks `min(from_account, to_account)` before `max(from_account, to_account)`.
15. **Q: How is Atomicity demonstrated in fund transfers?**  
    *A:* If either account update fails or a constraint is violated, `connection.rollback()` executes, reverting all debit, credit, transfer, and transaction insertions.
16. **Q: What is the role of `SAVEPOINT`?**  
    *A:* A savepoint marks a checkpoint within an open transaction. It allows partial rollbacks (`ROLLBACK TO SAVEPOINT`) without aborting preceding statements.
17. **Q: How does the Transaction Control demo work?**  
    *A:* A dedicated demo account (`account_id = 21`) allows users to test raw `COMMIT`, `ROLLBACK`, and `SAVEPOINT` operations interactively.
18. **Q: What hashing algorithm is used for passwords?**  
    *A:* Werkzeug's implementation of `Scrypt`, providing strong resistance against brute-force and hardware-accelerated attacks.
19. **Q: How is customer data isolation enforced?**  
    *A:* Backend authorization. Every customer query filters by `session['customer_id']`, preventing users from tampering with account IDs in requests.
20. **Q: What is CSRF and how is it mitigated?**  
    *A:* Cross-Site Request Forgery is mitigated by generating a cryptographically secure token stored in the session and requiring it on all state-changing POST requests.
21. **Q: What is the role of `AUDIT_LOG`?**  
    *A:* It records an immutable security audit trail documenting logins, fund transfers, and administrative actions with IP addresses and timestamps.
22. **Q: How are PDF statements generated?**  
    *A:* The `reports.py` module uses `fpdf2` to build vector PDF documents containing customer headers, account summaries, and tabular transaction histories in memory (`BytesIO`).
23. **Q: What SQL joins are used in the application?**  
    *A:* `INNER JOIN` (linking accounts to customers and transactions) and `LEFT JOIN` (retrieving account counts per customer).
24. **Q: Why use bind variables (`:1, :2`) instead of string interpolation?**  
    *A:* To eliminate SQL injection attacks and enable Oracle's cursor sharing and query plan caching for high performance.
25. **Q: How does the system handle database exceptions?**  
    *A:* `safe_error_message()` intercepts Oracle errors, maps constraint violations to friendly messages, logs the technical trace, and rolls back the transaction.
26. **Q: What happens if a user tries to withdraw more than their balance?**  
    *A:* The application checks `balance < amount` and aborts. Even if bypassed, Oracle's `CHK_ACCOUNT_BALANCE` constraint rejects negative balances.
27. **Q: What does `is_active` in `USERS` represent?**  
    *A:* A soft-disable flag (1 = active, 0 = disabled) enabling administrators to suspend compromised or deactivated accounts without deleting audit history.
28. **Q: Why are `email` and `phone` marked UNIQUE in `CUSTOMERS`?**  
    *A:* To enforce business constraints preventing multiple registrations with identical contact details.
29. **Q: What role do identity columns play in Oracle?**  
    *A:* `GENERATED BY DEFAULT AS IDENTITY` automatically provides sequential, unique integer primary keys managed internally by Oracle sequences.
30. **Q: Why is KAPA Bank suitable as a DBMS coursework project?**  
    *A:* It demonstrates the full lifecycle: conceptual ER modeling, relational mapping, database normalization, integrity constraints, ACID transaction management, concurrency controls, and security auditing connected to a live cloud database.

---

## 11. Presentation Explanation (Pitch Scripts)

### 30-Second Elevator Pitch
> *"KAPA Bank is a full-stack banking management system built with Python, Flask, and Oracle Autonomous Database Cloud. It demonstrates core DBMS principles—including ACID transactions, canonical row-level locking to prevent transfer deadlocks, and third normal form schema design. It features multi-role access control for Customers and Admins, real-time PDF statement generation, and an interactive TCL sandbox demonstrating COMMIT, ROLLBACK, and SAVEPOINT."*

### 1-Minute Project Overview
> *"Good morning. KAPA Bank is an academic database transaction system designed to demonstrate enterprise relational database concepts. The architecture couples a Flask web layer with Oracle Autonomous Database in the cloud. We designed a normalized schema consisting of six tables: Customers, Users, Accounts, Transactions, Transfers, and Audit Logs. 
> 
> The application showcases transaction control: deposits, withdrawals, and inter-account transfers execute atomically using `SELECT FOR UPDATE` row locks to prevent race conditions and deadlocks. We also implemented strict Role-Based Access Control and customer data isolation, dynamic PDF statement generation, and a live Transaction Control simulator for evaluation. The system is fully deployed on Vercel and backed by Oracle Cloud."*

---

## 12. Final ER & Relational Consistency Verification

- **Schema Check:** All 6 relations (`CUSTOMERS`, `USERS`, `BANK_ACCOUNTS`, `BANK_TRANSACTIONS`, `BANK_TRANSFERS`, `AUDIT_LOG`) exist in both the ER model and the physical Oracle Cloud instance.
- **Foreign Key Check:** Every foreign key in the relational schema maps to an explicit binary or associative relationship in the ER model.
- **Constraint Consistency:** All CHECK and UNIQUE constraints documented match the Oracle Data Dictionary definitions.

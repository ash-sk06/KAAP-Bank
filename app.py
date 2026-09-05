from flask import Flask, render_template, request
from decimal import Decimal, InvalidOperation
from database import get_connection, dictfetchall, dictfetchone
import logging
import oracledb

app = Flask(__name__)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

DEMO_ACCOUNT_ID = 21

def validate_required(value, field_name):
    if not value or not str(value).strip():
        return f"{field_name} is required."
    return None

def validate_positive_amount(value):
    try:
        amount = Decimal(str(value))
        if amount <= Decimal('0'):
            return None, "Amount must be strictly positive."
        return amount, None
    except (InvalidOperation, ValueError, TypeError):
        return None, "Invalid amount format."

def safe_error_message(e):
    logger.error("Database error occurred: %s", str(e), exc_info=True)
    error_msg = str(e)
    if "UQ_CUSTOMER_EMAIL" in error_msg:
        return "A customer with this email already exists."
    if "UQ_CUSTOMER_PHONE" in error_msg:
        return "A customer with this phone number already exists."
    if "UQ_ACCOUNT_NUMBER" in error_msg:
        return "An account with this account number already exists."
    return "An unexpected error occurred. Please try again later."

def render_success(title, message, **kwargs):
    kwargs.setdefault('transaction_demo', False)
    kwargs.setdefault('back_url', '/')
    kwargs.setdefault('back_label', 'Dashboard')
    kwargs.setdefault('transaction_status', 'COMMITTED')
    return render_template("success.html", title=title, message=message, **kwargs)

def render_error(title, message, back_url='/accounts', back_label='Back to Accounts'):
    return render_template("error.html", title=title, message=message, back_url=back_url, back_label=back_label)

@app.route("/")
def index():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COUNT(*) AS count FROM customers")
        customer_count = dictfetchone(cursor)['count']

        cursor.execute("SELECT COUNT(*) AS count FROM bank_accounts")
        account_count = dictfetchone(cursor)['count']

        cursor.execute("SELECT NVL(SUM(balance), 0) AS total FROM bank_accounts WHERE status = 'ACTIVE'")
        total_balance = Decimal(str(dictfetchone(cursor)['total']))

        cursor.execute("SELECT COUNT(*) AS count FROM bank_transactions")
        transaction_count = dictfetchone(cursor)['count']

        cursor.execute("""
            SELECT 
                t.transaction_id, 
                t.account_id, 
                a.account_number, 
                t.transaction_type, 
                t.amount, 
                TO_CHAR(FROM_TZ(t.transaction_date, 'UTC') AT TIME ZONE 'Asia/Kolkata', 'DD-MM-YYYY') AS display_date,
                TO_CHAR(FROM_TZ(t.transaction_date, 'UTC') AT TIME ZONE 'Asia/Kolkata', 'HH12:MI AM') AS display_time,
                t.status
            FROM bank_transactions t
            JOIN bank_accounts a ON t.account_id = a.account_id
            ORDER BY t.transaction_date DESC
            FETCH FIRST 5 ROWS ONLY
        """)
        recent_transactions = dictfetchall(cursor)

        cursor.execute("""
            SELECT account_type, COUNT(*) AS count
            FROM bank_accounts
            GROUP BY account_type
        """)
        account_type_data = dictfetchall(cursor)
        account_type_counts = {row['account_type']: row['count'] for row in account_type_data}
        if 'SAVINGS' not in account_type_counts: account_type_counts['SAVINGS'] = 0
        if 'CURRENT' not in account_type_counts: account_type_counts['CURRENT'] = 0

    except Exception as e:
        logger.error("Dashboard error: %s", str(e), exc_info=True)
        return render_error("Dashboard Error", "Failed to load dashboard data.", "/", "Retry")
    finally:
        cursor.close()
        connection.close()

    return render_template(
        "index.html",
        customer_count=customer_count,
        account_count=account_count,
        total_balance=total_balance,
        transaction_count=transaction_count,
        recent_transactions=recent_transactions,
        account_type_counts=account_type_counts
    )


@app.route("/customers")
def customers():
    search_query = request.args.get('q', '').strip()
    connection = get_connection()
    cursor = connection.cursor()
    try:
        sql = """
            SELECT c.customer_id, c.name, c.email, c.phone, c.address, COUNT(a.account_id) AS account_count
            FROM customers c
            LEFT JOIN bank_accounts a ON c.customer_id = a.customer_id
        """
        params = {}
        if search_query:
            sql += " WHERE LOWER(c.name) LIKE LOWER(:q) OR LOWER(c.email) LIKE LOWER(:q)"
            params['q'] = f"%{search_query}%"
        sql += " GROUP BY c.customer_id, c.name, c.email, c.phone, c.address ORDER BY c.name ASC"
        
        cursor.execute(sql, params)
        customers_list = dictfetchall(cursor)
    except Exception as e:
        logger.error("Customers list error: %s", str(e), exc_info=True)
        customers_list = []
    finally:
        cursor.close()
        connection.close()

    return render_template("customers.html", customers=customers_list, search_query=search_query)

@app.route("/add-customer", methods=["POST"])
def add_customer():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    
    if err := validate_required(name, "Name"):
        return render_error("Validation Error", err, "/customers", "Back to Customers")
    if err := validate_required(email, "Email"):
        return render_error("Validation Error", err, "/customers", "Back to Customers")
    if err := validate_required(phone, "Phone"):
        return render_error("Validation Error", err, "/customers", "Back to Customers")

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO customers (name, email, phone, address)
            VALUES (:1, :2, :3, :4)
        """, (name, email, phone, address))
        connection.commit()
        return render_success(
            "Customer Added Successfully", 
            f"Customer {name} has been registered successfully.", 
            back_url="/customers", 
            back_label="Back to Customers"
        )
    except Exception as e:
        connection.rollback()
        return render_error("Customer Creation Failed", safe_error_message(e), "/customers", "Back to Customers")
    finally:
        cursor.close()
        connection.close()

@app.route("/customers/<int:customer_id>")
def customer_detail(customer_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT customer_id, name, email, phone, address FROM customers WHERE customer_id = :1", (customer_id,))
        customer = dictfetchone(cursor)
        if not customer:
            return render_error("Not Found", "Customer not found.", "/customers", "Back to Customers")

        cursor.execute("""
            SELECT account_id, account_number, account_type, balance, status, created_date
            FROM bank_accounts
            WHERE customer_id = :1
            ORDER BY created_date DESC
        """, (customer_id,))
        accounts = dictfetchall(cursor)

        cursor.execute("""
            SELECT COUNT(t.transaction_id) AS tx_count
            FROM bank_transactions t
            JOIN bank_accounts a ON t.account_id = a.account_id
            WHERE a.customer_id = :1
        """, (customer_id,))
        transaction_count = dictfetchone(cursor)['tx_count']
        
    except Exception as e:
        logger.error("Customer detail error: %s", str(e), exc_info=True)
        return render_error("Error", "Failed to load customer details.", "/customers", "Back to Customers")
    finally:
        cursor.close()
        connection.close()

    return render_template("customer_detail.html", customer=customer, accounts=accounts, transaction_count=transaction_count)

@app.route("/accounts")
def accounts():
    search_query = request.args.get('q', '').strip()
    filter_type = request.args.get('type', '').strip()
    filter_status = request.args.get('status', '').strip()

    connection = get_connection()
    cursor = connection.cursor()
    try:
        sql = """
            SELECT a.account_id, a.customer_id, c.name AS customer_name, a.account_number, a.account_type, a.balance, a.status, a.created_date
            FROM bank_accounts a
            JOIN customers c ON a.customer_id = c.customer_id
            WHERE 1=1
        """
        params = {}
        if search_query:
            sql += " AND (LOWER(a.account_number) LIKE LOWER(:q) OR LOWER(c.name) LIKE LOWER(:q))"
            params['q'] = f"%{search_query}%"
        if filter_type:
            sql += " AND a.account_type = :ft"
            params['ft'] = filter_type
        if filter_status:
            sql += " AND a.status = :fs"
            params['fs'] = filter_status
            
        sql += " ORDER BY a.created_date DESC"
        cursor.execute(sql, params)
        accounts_list = dictfetchall(cursor)

        cursor.execute("SELECT customer_id, name FROM customers ORDER BY name ASC")
        customers_list = dictfetchall(cursor)
    except Exception as e:
        logger.error("Accounts list error: %s", str(e), exc_info=True)
        accounts_list = []
        customers_list = []
    finally:
        cursor.close()
        connection.close()

    return render_template("accounts.html", accounts=accounts_list, search_query=search_query, filter_type=filter_type, filter_status=filter_status, customers=customers_list)

@app.route("/add-account", methods=["POST"])
def add_account():
    customer_id_str = request.form.get("customer_id", "").strip()
    account_number = request.form.get("account_number", "").strip()
    account_type = request.form.get("account_type", "").strip()
    
    if not customer_id_str.isdigit():
        return render_error("Validation Error", "Invalid customer selection.", "/accounts", "Back to Accounts")
    customer_id = int(customer_id_str)
    
    if err := validate_required(account_number, "Account Number"):
        return render_error("Validation Error", err, "/accounts", "Back to Accounts")
    if account_type not in ["SAVINGS", "CURRENT"]:
        return render_error("Validation Error", "Invalid account type.", "/accounts", "Back to Accounts")

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO bank_accounts (customer_id, account_number, account_type, balance, status)
            VALUES (:1, :2, :3, 0, 'ACTIVE')
        """, (customer_id, account_number, account_type))
        connection.commit()
        return render_success("Bank Account Created", f"Account {account_number} has been created successfully.", back_url="/accounts", back_label="Back to Accounts")
    except Exception as e:
        connection.rollback()
        return render_error("Account Creation Failed", safe_error_message(e), "/accounts", "Back to Accounts")
    finally:
        cursor.close()
        connection.close()

@app.route("/accounts/<int:account_id>")
def account_detail(account_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT a.account_id, a.customer_id, c.name AS customer_name, a.account_number, a.account_type, a.balance, a.status, a.created_date
            FROM bank_accounts a
            JOIN customers c ON a.customer_id = c.customer_id
            WHERE a.account_id = :1
        """, (account_id,))
        account = dictfetchone(cursor)
        if not account:
            return render_error("Not Found", "Account not found.", "/accounts", "Back to Accounts")

        cursor.execute("""
            SELECT transaction_id, transaction_type, amount,
                TO_CHAR(FROM_TZ(transaction_date, 'UTC') AT TIME ZONE 'Asia/Kolkata', 'DD-MM-YYYY') AS display_date,
                TO_CHAR(FROM_TZ(transaction_date, 'UTC') AT TIME ZONE 'Asia/Kolkata', 'HH12:MI AM') AS display_time,
                status
            FROM bank_transactions
            WHERE account_id = :1
            ORDER BY transaction_date DESC
        """, (account_id,))
        transactions = dictfetchall(cursor)

        cursor.execute("""
            SELECT 
                NVL(SUM(CASE WHEN transaction_type IN ('DEPOSIT', 'TRANSFER_IN') THEN amount ELSE 0 END), 0) AS total_deposits,
                NVL(SUM(CASE WHEN transaction_type IN ('WITHDRAWAL', 'TRANSFER_OUT') THEN amount ELSE 0 END), 0) AS total_withdrawals
            FROM bank_transactions
            WHERE account_id = :1 AND status = 'COMMITTED'
        """, (account_id,))
        totals = dictfetchone(cursor)
        total_deposits = Decimal(str(totals['total_deposits']))
        total_withdrawals = Decimal(str(totals['total_withdrawals']))

    except Exception as e:
        logger.error("Account detail error: %s", str(e), exc_info=True)
        return render_error("Error", "Failed to load account details.", "/accounts", "Back to Accounts")
    finally:
        cursor.close()
        connection.close()

    return render_template("account_detail.html", account=account, transactions=transactions, total_deposits=total_deposits, total_withdrawals=total_withdrawals)

@app.route("/deposit", methods=["POST"])
def deposit():
    account_id = request.form.get("account_id")
    amount_str = request.form.get("amount")
    
    amount, err = validate_positive_amount(amount_str)
    if err:
        return render_error("Invalid Amount", err, "/accounts", "Back to Accounts")
    
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SAVEPOINT before_deposit")
        cursor.execute("SELECT balance, status FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (account_id,))
        account = dictfetchone(cursor)
        
        if not account:
            connection.rollback()
            return render_error("Account Not Found", "The specified account does not exist.", "/accounts", "Back to Accounts")
            
        old_balance = Decimal(str(account['balance']))
        if account['status'] != 'ACTIVE':
            connection.rollback()
            return render_error("Account Not Active", "Deposits can only be made to active accounts.", "/accounts", "Back to Accounts")
            
        new_balance = old_balance + amount
        
        cursor.execute("UPDATE bank_accounts SET balance = :1 WHERE account_id = :2", (new_balance, account_id))
        cursor.execute("INSERT INTO bank_transactions (account_id, transaction_type, amount, status) VALUES (:1, 'DEPOSIT', :2, 'COMMITTED')", (account_id, amount))
        connection.commit()
        
        return render_success("Deposit Successful", f"₹{amount} has been deposited successfully.", amount=amount, old_balance=old_balance, new_balance=new_balance, back_url="/accounts", back_label="Back to Accounts")
    except Exception as e:
        connection.rollback()
        return render_error("Deposit Failed", safe_error_message(e), "/accounts", "Back to Accounts")
    finally:
        cursor.close()
        connection.close()

@app.route("/withdraw", methods=["POST"])
def withdraw():
    account_id = request.form.get("account_id")
    amount_str = request.form.get("amount")
    
    amount, err = validate_positive_amount(amount_str)
    if err:
        return render_error("Invalid Amount", err, "/accounts", "Back to Accounts")
    
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SAVEPOINT before_withdraw")
        cursor.execute("SELECT balance, status FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (account_id,))
        account = dictfetchone(cursor)
        
        if not account:
            connection.rollback()
            return render_error("Account Not Found", "The specified account does not exist.", "/accounts", "Back to Accounts")
            
        old_balance = Decimal(str(account['balance']))
        if account['status'] != 'ACTIVE':
            connection.rollback()
            return render_error("Account Not Active", "Withdrawals can only be made from active accounts.", "/accounts", "Back to Accounts")
            
        if old_balance < amount:
            connection.rollback()
            return render_error("Insufficient Balance", f"Withdrawal of ₹{amount} cannot be completed. Available balance is ₹{old_balance}.", "/accounts", "Back to Accounts")
            
        new_balance = old_balance - amount
        
        cursor.execute("UPDATE bank_accounts SET balance = :1 WHERE account_id = :2", (new_balance, account_id))
        cursor.execute("INSERT INTO bank_transactions (account_id, transaction_type, amount, status) VALUES (:1, 'WITHDRAWAL', :2, 'COMMITTED')", (account_id, amount))
        connection.commit()
        
        return render_success("Withdrawal Successful", f"₹{amount} has been withdrawn successfully.", amount=amount, old_balance=old_balance, new_balance=new_balance, back_url="/accounts", back_label="Back to Accounts")
    except Exception as e:
        connection.rollback()
        return render_error("Withdrawal Failed", safe_error_message(e), "/accounts", "Back to Accounts")
    finally:
        cursor.close()
        connection.close()

@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "GET":
        try:
            cursor.execute("""
                SELECT a.account_id, a.account_number, c.name AS customer_name, a.balance, a.status
                FROM bank_accounts a
                JOIN customers c ON a.customer_id = c.customer_id
                WHERE a.status = 'ACTIVE'
                ORDER BY a.account_number ASC
            """)
            accounts = dictfetchall(cursor)
            return render_template("transfer.html", accounts=accounts)
        finally:
            cursor.close()
            connection.close()

    try:
        from_account = int(request.form.get("from_account", "0"))
        to_account = int(request.form.get("to_account", "0"))
        amount_str = request.form.get("amount")
        
        amount, err = validate_positive_amount(amount_str)
        if err:
            return render_error("Invalid Amount", err, "/transfer", "Back to Transfer")
            
        if from_account == to_account:
            return render_error("Invalid Transfer", "Source and destination accounts must be different.", "/transfer", "Back to Transfer")
            
        cursor.execute("SAVEPOINT before_transfer")
        
        first_account = min(from_account, to_account)
        second_account = max(from_account, to_account)
        
        cursor.execute("SELECT account_id, balance, status FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (first_account,))
        first_row = dictfetchone(cursor)
        
        cursor.execute("SELECT account_id, balance, status FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (second_account,))
        second_row = dictfetchone(cursor)
        
        if not first_row or not second_row:
            connection.rollback()
            return render_error("Account Not Found", "One of the specified accounts does not exist.", "/transfer", "Back to Transfer")
            
        if first_row['account_id'] == from_account:
            sender = first_row
            receiver = second_row
        else:
            sender = second_row
            receiver = first_row
            
        if sender['status'] != 'ACTIVE' or receiver['status'] != 'ACTIVE':
            connection.rollback()
            return render_error("Transfer Failed", "Both accounts must be active.", "/transfer", "Back to Transfer")
            
        sender_balance = Decimal(str(sender['balance']))
        if sender_balance < amount:
            connection.rollback()
            return render_error("Insufficient Balance", f"Transfer of ₹{amount} cannot be completed. Available balance is ₹{sender_balance}.", "/transfer", "Back to Transfer")
            
        cursor.execute("UPDATE bank_accounts SET balance = balance - :1 WHERE account_id = :2", (amount, from_account))
        cursor.execute("UPDATE bank_accounts SET balance = balance + :1 WHERE account_id = :2", (amount, to_account))
        
        cursor.execute("INSERT INTO bank_transfers (from_account, to_account, amount, status) VALUES (:1, :2, :3, 'COMMITTED')", (from_account, to_account, amount))
        cursor.execute("INSERT INTO bank_transactions (account_id, transaction_type, amount, status) VALUES (:1, 'TRANSFER_OUT', :2, 'COMMITTED')", (from_account, amount))
        cursor.execute("INSERT INTO bank_transactions (account_id, transaction_type, amount, status) VALUES (:1, 'TRANSFER_IN', :2, 'COMMITTED')", (to_account, amount))
        
        connection.commit()
        return render_success("Transfer Successful", f"₹{amount} has been transferred successfully.", amount=amount, from_account=from_account, to_account=to_account, back_url="/transactions", back_label="View Transactions")
    except Exception as e:
        connection.rollback()
        return render_error("Transfer Failed", safe_error_message(e), "/transfer", "Back to Transfer")
    finally:
        cursor.close()
        connection.close()

@app.route("/transactions")
def transactions():
    search_query = request.args.get('q', '').strip()
    filter_type = request.args.get('type', '').strip()
    filter_status = request.args.get('status', '').strip()

    connection = get_connection()
    cursor = connection.cursor()
    try:
        sql = """
            SELECT t.transaction_id, t.account_id, a.account_number, t.transaction_type, t.amount,
                TO_CHAR(FROM_TZ(t.transaction_date, 'UTC') AT TIME ZONE 'Asia/Kolkata', 'DD-MM-YYYY') AS display_date,
                TO_CHAR(FROM_TZ(t.transaction_date, 'UTC') AT TIME ZONE 'Asia/Kolkata', 'HH12:MI AM') AS display_time,
                t.status
            FROM bank_transactions t
            JOIN bank_accounts a ON t.account_id = a.account_id
            WHERE 1=1
        """
        params = {}
        if search_query:
            sql += " AND LOWER(a.account_number) LIKE LOWER(:q)"
            params['q'] = f"%{search_query}%"
        if filter_type:
            sql += " AND t.transaction_type = :ft"
            params['ft'] = filter_type
        if filter_status:
            sql += " AND t.status = :fs"
            params['fs'] = filter_status
            
        sql += " ORDER BY t.transaction_date DESC"
        cursor.execute(sql, params)
        transactions_list = dictfetchall(cursor)
    except Exception as e:
        logger.error("Transactions list error: %s", str(e), exc_info=True)
        transactions_list = []
    finally:
        cursor.close()
        connection.close()

    return render_template("transactions.html", transactions=transactions_list, search_query=search_query, filter_type=filter_type, filter_status=filter_status)

@app.route("/transaction-control")
def transaction_control():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT account_id, account_number, balance FROM bank_accounts WHERE account_id = :1", (DEMO_ACCOUNT_ID,))
        account = dictfetchone(cursor)
        if not account:
            return render_error("Demo Error", "Demo account not found.", "/", "Dashboard")
    except Exception as e:
        logger.error("Transaction control error: %s", str(e), exc_info=True)
        return render_error("Error", "Failed to load demo account.", "/", "Dashboard")
    finally:
        cursor.close()
        connection.close()

    return render_template("transaction_control.html", account=account)

@app.route("/transaction-control/commit", methods=["POST"])
def transaction_control_commit():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT balance FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (DEMO_ACCOUNT_ID,))
        account = dictfetchone(cursor)
        old_balance = Decimal(str(account['balance']))
        
        cursor.execute("SAVEPOINT before_demo")
        new_balance = old_balance + Decimal('1000')
        
        cursor.execute("UPDATE bank_accounts SET balance = :1 WHERE account_id = :2", (new_balance, DEMO_ACCOUNT_ID))
        cursor.execute("INSERT INTO bank_transactions (account_id, transaction_type, amount, status) VALUES (:1, 'DEPOSIT', 1000, 'COMMITTED')", (DEMO_ACCOUNT_ID,))
        
        connection.commit()
        return render_success("Commit Successful", "The transaction was committed to the database.", old_balance=old_balance, new_balance=new_balance, transaction_status='COMMITTED', back_url="/transaction-control", back_label="Back to Transaction Control", transaction_demo=True)
    except Exception as e:
        connection.rollback()
        return render_error("Commit Failed", safe_error_message(e), "/transaction-control", "Back to Transaction Control")
    finally:
        cursor.close()
        connection.close()

@app.route("/transaction-control/rollback", methods=["POST"])
def transaction_control_rollback():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT balance FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (DEMO_ACCOUNT_ID,))
        account = dictfetchone(cursor)
        old_balance = Decimal(str(account['balance']))
        
        cursor.execute("UPDATE bank_accounts SET balance = balance + 2000 WHERE account_id = :1", (DEMO_ACCOUNT_ID,))
        connection.rollback()
        
        return render_success("Rollback Successful", "The transaction was rolled back. No changes were saved.", old_balance=old_balance, new_balance=old_balance, transaction_status='ROLLED_BACK', back_url="/transaction-control", back_label="Back to Transaction Control", transaction_demo=True)
    except Exception as e:
        connection.rollback()
        return render_error("Rollback Failed", safe_error_message(e), "/transaction-control", "Back to Transaction Control")
    finally:
        cursor.close()
        connection.close()

@app.route("/transaction-control/savepoint", methods=["POST"])
def transaction_control_savepoint():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT balance FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (DEMO_ACCOUNT_ID,))
        account = dictfetchone(cursor)
        old_balance = Decimal(str(account['balance']))
        
        cursor.execute("UPDATE bank_accounts SET balance = balance + 1000 WHERE account_id = :1", (DEMO_ACCOUNT_ID,))
        cursor.execute("SAVEPOINT intermediate_state")
        cursor.execute("UPDATE bank_accounts SET balance = balance + 2000 WHERE account_id = :1", (DEMO_ACCOUNT_ID,))
        
        cursor.execute("ROLLBACK TO SAVEPOINT intermediate_state")
        cursor.execute("INSERT INTO bank_transactions (account_id, transaction_type, amount, status) VALUES (:1, 'DEPOSIT', 1000, 'COMMITTED')", (DEMO_ACCOUNT_ID,))
        
        connection.commit()
        return render_success("Savepoint Rollback Successful", "The second operation was rolled back to the savepoint, but the first operation was committed.", old_balance=old_balance, new_balance=old_balance + Decimal('1000'), transaction_status='COMMITTED', back_url="/transaction-control", back_label="Back to Transaction Control", transaction_demo=True)
    except Exception as e:
        connection.rollback()
        return render_error("Savepoint Failed", safe_error_message(e), "/transaction-control", "Back to Transaction Control")
    finally:
        cursor.close()
        connection.close()

@app.route("/transaction-control/reset", methods=["POST"])
def transaction_control_reset():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT balance FROM bank_accounts WHERE account_id = :1 FOR UPDATE", (DEMO_ACCOUNT_ID,))
        cursor.execute("UPDATE bank_accounts SET balance = 10000 WHERE account_id = :1", (DEMO_ACCOUNT_ID,))
        cursor.execute("DELETE FROM bank_transactions WHERE account_id = :1", (DEMO_ACCOUNT_ID,))
        connection.commit()
        
        return render_success("Demo Account Reset", "The demo account balance has been reset to 10000 and its transactions cleared.", transaction_demo=True, back_url="/transaction-control", back_label="Back to Transaction Control")
    except Exception as e:
        connection.rollback()
        return render_error("Reset Failed", safe_error_message(e), "/transaction-control", "Back to Transaction Control")
    finally:
        cursor.close()
        connection.close()

@app.route("/reports")
def reports():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT 
                NVL(SUM(CASE WHEN transaction_type = 'DEPOSIT' THEN amount ELSE 0 END), 0) AS total_deposits,
                NVL(SUM(CASE WHEN transaction_type = 'WITHDRAWAL' THEN amount ELSE 0 END), 0) AS total_withdrawals,
                NVL(SUM(CASE WHEN transaction_type = 'TRANSFER_OUT' THEN amount ELSE 0 END), 0) AS total_transfers
            FROM bank_transactions WHERE status = 'COMMITTED'
        """)
        totals = dictfetchone(cursor)
        total_deposits = Decimal(str(totals['total_deposits']))
        total_withdrawals = Decimal(str(totals['total_withdrawals']))
        total_transfers = Decimal(str(totals['total_transfers']))

        cursor.execute("""
            SELECT transaction_type, COUNT(*) AS count, NVL(SUM(amount), 0) AS total
            FROM bank_transactions
            WHERE status = 'COMMITTED'
            GROUP BY transaction_type
        """)
        transaction_type_counts = dictfetchall(cursor)

        cursor.execute("""
            SELECT account_type, COUNT(*) AS count, NVL(SUM(balance), 0) AS total_balance
            FROM bank_accounts
            GROUP BY account_type
        """)
        account_type_counts = dictfetchall(cursor)

        cursor.execute("""
            SELECT a.account_number, c.name AS customer_name, a.balance
            FROM bank_accounts a
            JOIN customers c ON a.customer_id = c.customer_id
            ORDER BY a.balance DESC
            FETCH FIRST 5 ROWS ONLY
        """)
        top_accounts = dictfetchall(cursor)

        cursor.execute("SELECT COUNT(*) AS count FROM customers")
        customer_count = dictfetchone(cursor)['count']

        cursor.execute("SELECT COUNT(*) AS count FROM bank_accounts")
        account_count = dictfetchone(cursor)['count']

        cursor.execute("SELECT NVL(SUM(balance), 0) AS total FROM bank_accounts WHERE status = 'ACTIVE'")
        total_balance = Decimal(str(dictfetchone(cursor)['total']))
        
    except Exception as e:
        logger.error("Reports error: %s", str(e), exc_info=True)
        return render_error("Error", "Failed to load reports.", "/", "Dashboard")
    finally:
        cursor.close()
        connection.close()

    return render_template(
        "reports.html",
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        total_transfers=total_transfers,
        transaction_type_counts=transaction_type_counts,
        account_type_counts=account_type_counts,
        top_accounts=top_accounts,
        customer_count=customer_count,
        account_count=account_count,
        total_balance=total_balance
    )

@app.errorhandler(404)
def page_not_found(e):
    return render_error("Page Not Found", "The page you are looking for does not exist.", "/", "Dashboard"), 404

if __name__ == '__main__':
    import os
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, host="127.0.0.1", port=port)
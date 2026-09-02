from flask import Flask, render_template, request
from database import get_connection

app = Flask(__name__)


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def index():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Number of customers
        cursor.execute("""
            SELECT COUNT(*)
            FROM customers
        """)
        customer_count = cursor.fetchone()[0]

        # Number of accounts
        cursor.execute("""
            SELECT COUNT(*)
            FROM bank_accounts
        """)
        account_count = cursor.fetchone()[0]

        # Total balance
        cursor.execute("""
            SELECT NVL(SUM(balance), 0)
            FROM bank_accounts
            WHERE status = 'ACTIVE'
        """)
        total_balance = cursor.fetchone()[0]

        # Number of transactions
        cursor.execute("""
            SELECT COUNT(*)
            FROM bank_transactions
        """)
        transaction_count = cursor.fetchone()[0]

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "index.html",
        customer_count=customer_count,
        account_count=account_count,
        total_balance=total_balance,
        transaction_count=transaction_count
    )


# =========================================================
# CUSTOMERS
# =========================================================

@app.route("/customers")
def customers():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                customer_id,
                name,
                email,
                phone,
                address
            FROM customers
            ORDER BY customer_id
        """)

        customers = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "customers.html",
        customers=customers
    )


# =========================================================
# ADD CUSTOMER
# =========================================================

@app.route("/add-customer", methods=["POST"])
def add_customer():

    connection = get_connection()
    cursor = connection.cursor()

    try:
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        address = request.form.get("address", "").strip()

        cursor.execute("""
            INSERT INTO customers
            (
                name,
                email,
                phone,
                address
            )
            VALUES
            (
                :1,
                :2,
                :3,
                :4
            )
        """, (
            name,
            email,
            phone,
            address
        ))

        connection.commit()

        return render_template(
            "success.html",
            title="Customer Added Successfully",
            message=f"Customer {name} has been registered successfully.",
            transaction_demo=False
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "error.html",
            title="Customer Creation Failed",
            message=f"Unable to add the customer. {e}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================================================
# ACCOUNTS
# =========================================================

@app.route("/accounts")
def accounts():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                account_id,
                customer_id,
                account_number,
                account_type,
                balance,
                status,
                created_date
            FROM bank_accounts
            ORDER BY account_id
        """)

        accounts = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "accounts.html",
        accounts=accounts
    )


# =========================================================
# CREATE BANK ACCOUNT
# =========================================================

@app.route("/add-account", methods=["POST"])
def add_account():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        customer_id = int(request.form["customer_id"])
        account_number = request.form["account_number"].strip()
        account_type = request.form["account_type"]

        cursor.execute("""
            INSERT INTO bank_accounts
            (
                customer_id,
                account_number,
                account_type,
                balance,
                status
            )
            VALUES
            (
                :1,
                :2,
                :3,
                0,
                'ACTIVE'
            )
        """, (
            customer_id,
            account_number,
            account_type
        ))

        connection.commit()

        return render_template(
            "success.html",
            title="Bank Account Created",
            message=f"Account {account_number} has been created successfully.",
            transaction_demo=False
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "error.html",
            title="Account Creation Failed",
            message=f"Unable to create the bank account. {e}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================================================
# DEPOSIT MONEY
# =========================================================

@app.route("/deposit", methods=["POST"])
def deposit():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        account_id = int(request.form["account_id"])
        amount = float(request.form["amount"])

        if amount <= 0:
            return render_template(
                "error.html",
                title="Invalid Amount",
                message="Deposit amount must be greater than zero."
            )

        # Create a savepoint
        cursor.execute("""
            SAVEPOINT before_deposit
        """)

        # Lock account before modifying it
        cursor.execute("""
            SELECT balance, status
            FROM bank_accounts
            WHERE account_id = :1
            FOR UPDATE
        """, (account_id,))

        account = cursor.fetchone()

        if account is None:

            connection.rollback()

            return render_template(
                "error.html",
                title="Account Not Found",
                message="The specified account does not exist."
            )

        old_balance = float(account[0])
        status = account[1]

        if status != "ACTIVE":

            connection.rollback()

            return render_template(
                "error.html",
                title="Account Not Active",
                message="Deposits can only be made to active accounts."
            )

        # Update balance
        cursor.execute("""
            UPDATE bank_accounts
            SET balance = balance + :1
            WHERE account_id = :2
        """, (
            amount,
            account_id
        ))

        # Record transaction
        cursor.execute("""
            INSERT INTO bank_transactions
            (
                account_id,
                transaction_type,
                amount,
                status
            )
            VALUES
            (
                :1,
                'DEPOSIT',
                :2,
                'COMMITTED'
            )
        """, (
            account_id,
            amount
        ))

        # Commit transaction
        connection.commit()

        return render_template(
            "success.html",
            title="Deposit Successful",
            message=f"₹{amount:.2f} has been deposited successfully.",
            amount=amount,
            transaction_demo=False
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "error.html",
            title="Deposit Failed",
            message=f"The deposit could not be completed. {e}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================================================
# WITHDRAW MONEY
# =========================================================

@app.route("/withdraw", methods=["POST"])
def withdraw():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        account_id = int(request.form["account_id"])
        amount = float(request.form["amount"])

        if amount <= 0:
            return render_template(
                "error.html",
                title="Invalid Amount",
                message="Withdrawal amount must be greater than zero."
            )

        # Create savepoint
        cursor.execute("""
            SAVEPOINT before_withdrawal
        """)

        # Lock account
        cursor.execute("""
            SELECT balance, status
            FROM bank_accounts
            WHERE account_id = :1
            FOR UPDATE
        """, (account_id,))

        account = cursor.fetchone()

        if account is None:

            connection.rollback()

            return render_template(
                "error.html",
                title="Account Not Found",
                message="The specified account does not exist."
            )

        old_balance = float(account[0])
        status = account[1]

        if status != "ACTIVE":

            connection.rollback()

            return render_template(
                "error.html",
                title="Account Not Active",
                message="Withdrawals can only be made from active accounts."
            )

        # Check sufficient balance
        if old_balance < amount:

            connection.rollback()

            return render_template(
                "error.html",
                title="Insufficient Balance",
                message=(
                    f"Withdrawal of ₹{amount:.2f} cannot be completed. "
                    f"Available balance is ₹{old_balance:.2f}."
                )
            )

        # Update balance
        cursor.execute("""
            UPDATE bank_accounts
            SET balance = balance - :1
            WHERE account_id = :2
        """, (
            amount,
            account_id
        ))

        # Record transaction
        cursor.execute("""
            INSERT INTO bank_transactions
            (
                account_id,
                transaction_type,
                amount,
                status
            )
            VALUES
            (
                :1,
                'WITHDRAWAL',
                :2,
                'COMMITTED'
            )
        """, (
            account_id,
            amount
        ))

        # Commit
        connection.commit()

        return render_template(
            "success.html",
            title="Withdrawal Successful",
            message=f"₹{amount:.2f} has been withdrawn successfully.",
            amount=amount,
            transaction_demo=False
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "error.html",
            title="Withdrawal Failed",
            message=f"The withdrawal could not be completed. {e}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================================================
# FUND TRANSFER
# =========================================================

@app.route("/transfer", methods=["GET", "POST"])
def transfer():

    # Show transfer page
    if request.method == "GET":
        return render_template("transfer.html")

    connection = get_connection()
    cursor = connection.cursor()

    try:

        from_account = int(request.form["from_account"])
        to_account = int(request.form["to_account"])
        amount = float(request.form["amount"])

        if amount <= 0:

            return render_template(
                "error.html",
                title="Invalid Amount",
                message="Transfer amount must be greater than zero."
            )

        if from_account == to_account:

            return render_template(
                "error.html",
                title="Invalid Transfer",
                message="Source and destination accounts must be different."
            )

        # -------------------------------------------------
        # SAVEPOINT
        # -------------------------------------------------

        cursor.execute("""
            SAVEPOINT before_transfer
        """)

        # -------------------------------------------------
        # LOCK ACCOUNTS
        # -------------------------------------------------

        # Lock in consistent order to reduce deadlock risk
        first_account = min(from_account, to_account)
        second_account = max(from_account, to_account)

        cursor.execute("""
            SELECT account_id, balance, status
            FROM bank_accounts
            WHERE account_id = :1
            FOR UPDATE
        """, (first_account,))

        first_row = cursor.fetchone()

        if first_row is None:

            connection.rollback()

            return render_template(
                "error.html",
                title="Account Not Found",
                message="One of the specified accounts does not exist."
            )

        cursor.execute("""
            SELECT account_id, balance, status
            FROM bank_accounts
            WHERE account_id = :1
            FOR UPDATE
        """, (second_account,))

        second_row = cursor.fetchone()

        if second_row is None:

            connection.rollback()

            return render_template(
                "error.html",
                title="Account Not Found",
                message="One of the specified accounts does not exist."
            )

        # Determine sender and receiver
        if first_row[0] == from_account:

            sender = first_row
            receiver = second_row

        else:

            sender = second_row
            receiver = first_row

        sender_balance = float(sender[1])
        sender_status = sender[2]
        receiver_status = receiver[2]

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if sender_status != "ACTIVE":

            connection.rollback()

            return render_template(
                "error.html",
                title="Transfer Failed",
                message="The sender account is not active."
            )

        if receiver_status != "ACTIVE":

            connection.rollback()

            return render_template(
                "error.html",
                title="Transfer Failed",
                message="The receiver account is not active."
            )

        if sender_balance < amount:

            connection.rollback()

            return render_template(
                "error.html",
                title="Insufficient Balance",
                message=(
                    f"Transfer of ₹{amount:.2f} cannot be completed. "
                    f"Available balance is ₹{sender_balance:.2f}."
                )
            )

        # -------------------------------------------------
        # UPDATE SENDER
        # -------------------------------------------------

        cursor.execute("""
            UPDATE bank_accounts
            SET balance = balance - :1
            WHERE account_id = :2
        """, (
            amount,
            from_account
        ))

        # -------------------------------------------------
        # UPDATE RECEIVER
        # -------------------------------------------------

        cursor.execute("""
            UPDATE bank_accounts
            SET balance = balance + :1
            WHERE account_id = :2
        """, (
            amount,
            to_account
        ))

        # -------------------------------------------------
        # RECORD TRANSFER
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO bank_transfers
            (
                from_account,
                to_account,
                amount,
                status
            )
            VALUES
            (
                :1,
                :2,
                :3,
                'COMMITTED'
            )
        """, (
            from_account,
            to_account,
            amount
        ))

        # -------------------------------------------------
        # RECORD SENDER TRANSACTION
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO bank_transactions
            (
                account_id,
                transaction_type,
                amount,
                status
            )
            VALUES
            (
                :1,
                'TRANSFER_OUT',
                :2,
                'COMMITTED'
            )
        """, (
            from_account,
            amount
        ))

        # -------------------------------------------------
        # RECORD RECEIVER TRANSACTION
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO bank_transactions
            (
                account_id,
                transaction_type,
                amount,
                status
            )
            VALUES
            (
                :1,
                'TRANSFER_IN',
                :2,
                'COMMITTED'
            )
        """, (
            to_account,
            amount
        ))

        # -------------------------------------------------
        # COMMIT EVERYTHING
        # -------------------------------------------------

        connection.commit()

        return render_template(
            "success.html",
            title="Transfer Successful",
            message=f"₹{amount:.2f} has been transferred successfully.",
            amount=amount,
            from_account=from_account,
            to_account=to_account,
            transaction_demo=False
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "error.html",
            title="Transfer Failed",
            message=f"The transfer could not be completed. {e}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================================================
# TRANSACTION HISTORY
# =========================================================

@app.route("/transactions")
def transactions():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                b.transaction_id,
                b.account_id,
                b.transaction_type,
                b.amount,

                TO_CHAR(
                    FROM_TZ(b.transaction_date, 'UTC')
                    AT TIME ZONE 'Asia/Kolkata',
                    'DD-MM-YYYY'
                ) AS display_date,

                TO_CHAR(
                    FROM_TZ(b.transaction_date, 'UTC')
                    AT TIME ZONE 'Asia/Kolkata',
                    'HH24:MI:SS'
                ) AS display_time,

                b.status

            FROM bank_transactions b

            ORDER BY b.transaction_date DESC
        """)

        transactions = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "transactions.html",
        transactions=transactions
    )

# =========================================================
# TRANSACTION CONTROL DEMO
# =========================================================

DEMO_ACCOUNT_ID = 21


@app.route("/transaction-control")
def transaction_control():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            SELECT
                account_number,
                balance
            FROM bank_accounts
            WHERE account_id = :1
        """, (DEMO_ACCOUNT_ID,))

        account = cursor.fetchone()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "transaction_control.html",
        account=account
    )


# =========================================================
# COMMIT DEMO
# =========================================================

@app.route("/transaction-control/commit", methods=["POST"])
def commit_demo():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        amount = 1000

        # Lock demo account
        cursor.execute("""
            SELECT balance
            FROM bank_accounts
            WHERE account_id = :1
            FOR UPDATE
        """, (DEMO_ACCOUNT_ID,))

        account = cursor.fetchone()

        if account is None:

            connection.rollback()

            return render_template(
                "error.html",
                title="Demo Account Not Found",
                message="The transaction control demo account could not be found."
            )

        # Create savepoint
        cursor.execute("""
            SAVEPOINT before_commit_demo
        """)

        # Add money
        cursor.execute("""
            UPDATE bank_accounts
            SET balance = balance + :1
            WHERE account_id = :2
        """, (
            amount,
            DEMO_ACCOUNT_ID
        ))

        # Permanently save the change
        connection.commit()

        return render_template(
            "success.html",
            title="COMMIT Successful",
            message="The ₹1,000 demo deposit was committed successfully.",
            amount=amount,
            transaction_demo=True
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "error.html",
            title="COMMIT Failed",
            message=f"The demo transaction was rolled back. {e}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================================================
# ROLLBACK DEMO
# =========================================================

@app.route("/transaction-control/rollback", methods=["POST"])
def rollback_demo():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        amount = 2000

        # Lock demo account
        cursor.execute("""
            SELECT balance
            FROM bank_accounts
            WHERE account_id = :1
            FOR UPDATE
        """, (DEMO_ACCOUNT_ID,))

        account = cursor.fetchone()

        if account is None:

            connection.rollback()

            return render_template(
                "error.html",
                title="Demo Account Not Found",
                message="The transaction control demo account could not be found."
            )

        # Create savepoint
        cursor.execute("""
            SAVEPOINT before_rollback_demo
        """)

        # Temporarily modify balance
        cursor.execute("""
            UPDATE bank_accounts
            SET balance = balance + :1
            WHERE account_id = :2
        """, (
            amount,
            DEMO_ACCOUNT_ID
        ))

        # Undo the change
        connection.rollback()

        return render_template(
            "success.html",
            title="ROLLBACK Successful",
            message="The ₹2,000 demo deposit was rolled back. The account balance remains unchanged.",
            amount=amount,
            transaction_demo=True
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "error.html",
            title="ROLLBACK Demo Failed",
            message=f"The rollback demonstration could not be completed. {e}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================================================
# SAVEPOINT DEMO
# =========================================================

@app.route("/transaction-control/savepoint", methods=["POST"])
def savepoint_demo():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        first_amount = 1000
        second_amount = 2000

        # Lock demo account
        cursor.execute("""
            SELECT balance
            FROM bank_accounts
            WHERE account_id = :1
            FOR UPDATE
        """, (DEMO_ACCOUNT_ID,))

        account = cursor.fetchone()

        if account is None:

            connection.rollback()

            return render_template(
                "error.html",
                title="Demo Account Not Found",
                message="The transaction control demo account could not be found."
            )

        # -------------------------------------------------
        # FIRST OPERATION
        # -------------------------------------------------

        cursor.execute("""
            UPDATE bank_accounts
            SET balance = balance + :1
            WHERE account_id = :2
        """, (
            first_amount,
            DEMO_ACCOUNT_ID
        ))

        # -------------------------------------------------
        # CREATE SAVEPOINT
        # -------------------------------------------------

        cursor.execute("""
            SAVEPOINT after_first_operation
        """)

        # -------------------------------------------------
        # SECOND OPERATION
        # -------------------------------------------------

        cursor.execute("""
            UPDATE bank_accounts
            SET balance = balance + :1
            WHERE account_id = :2
        """, (
            second_amount,
            DEMO_ACCOUNT_ID
        ))

        # -------------------------------------------------
        # ROLLBACK ONLY SECOND OPERATION
        # -------------------------------------------------

        cursor.execute("""
            ROLLBACK TO SAVEPOINT after_first_operation
        """)

        # -------------------------------------------------
        # COMMIT FIRST OPERATION
        # -------------------------------------------------

        connection.commit()

        return render_template(
            "success.html",
            title="SAVEPOINT Successful",
            message=(
                "The second operation was rolled back to the "
                "SAVEPOINT, while the first operation was committed."
            ),
            amount=first_amount,
            transaction_demo=True
        )

    except Exception as e:

        connection.rollback()

        return render_template(
            "error.html",
            title="SAVEPOINT Demo Failed",
            message=f"The SAVEPOINT demonstration could not be completed. {e}"
        )

    finally:
        cursor.close()
        connection.close()


# =========================================================
# ERROR HANDLER
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "error.html",
        title="Page Not Found",
        message="The page you are looking for does not exist."
    ), 404


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)
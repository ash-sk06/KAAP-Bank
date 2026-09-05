"""
KAPA Bank Statement Generation Module
Generates professional PDF statements using fpdf2 and CSV statement exports.
"""
import io
import csv
from datetime import datetime
from decimal import Decimal
from fpdf import FPDF

class BankStatementPDF(FPDF):
    def __init__(self, account_number, customer_name):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.account_number = account_number
        self.customer_name = customer_name
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # Top banner
        self.set_fill_color(30, 41, 59) # #1e293b dark slate
        self.rect(0, 0, 210, 25, 'F')

        self.set_xy(15, 6)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "KAPA BANK", new_x="LMARGIN", new_y="NEXT")

        self.set_xy(15, 14)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(148, 163, 184) # #94a3b8
        self.cell(0, 5, "Official Account Statement | Secure Banking Services", new_x="LMARGIN", new_y="NEXT")

        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        page_str = f"Page {self.page_no()}/{{nb}} | KAPA Bank Transaction Management System"
        self.cell(0, 10, page_str, align="C")


def generate_pdf_statement(customer, account, transactions, date_from=None, date_to=None):
    """
    Generates a professional PDF statement for a specific customer bank account.
    Returns bytes of the PDF file.
    """
    pdf = BankStatementPDF(account['account_number'], customer['name'])
    pdf.alias_nb_pages()
    pdf.add_page()

    # Meta Section
    pdf.set_text_color(15, 23, 42) # #0f172a
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, f"Account Statement: {account['account_number']}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    period_str = f"{date_from or 'Start'} to {date_to or 'Present'}" if (date_from or date_to) else "Complete Account History"
    generated_on = datetime.now().strftime("%d %b %Y, %I:%M %p")
    pdf.cell(0, 5, f"Statement Period: {period_str}  |  Generated On: {generated_on}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Customer & Account Info Box (2 Columns)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(15, pdf.get_y(), 180, 28, 'DF')
    start_y = pdf.get_y()

    # Column 1: Customer Details
    pdf.set_xy(20, start_y + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(85, 5, "ACCOUNT HOLDER", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(20)
    pdf.cell(85, 5, str(customer.get('name', 'N/A')), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.set_x(20)
    pdf.cell(85, 4, f"Email: {customer.get('email', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.cell(85, 4, f"Phone: {customer.get('phone', 'N/A')}", new_x="LMARGIN", new_y="NEXT")

    # Column 2: Account Details
    pdf.set_xy(110, start_y + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(80, 5, "ACCOUNT OVERVIEW", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(71, 85, 105)
    pdf.set_x(110)
    pdf.cell(80, 4, f"Account Type: {account.get('account_type', 'SAVINGS')}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(110)
    pdf.cell(80, 4, f"Status: {account.get('status', 'ACTIVE')}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(110)
    bal_val = Decimal(str(account.get('balance', 0)))
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(5, 150, 105) # green
    pdf.cell(80, 6, f"Current Balance: INR {bal_val:,.2f}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(start_y + 34)

    # Calculate Totals
    total_credits = Decimal('0.00')
    total_debits = Decimal('0.00')
    for t in transactions:
        if t.get('status') == 'COMMITTED':
            amt = Decimal(str(t.get('amount', 0)))
            if t.get('transaction_type') in ['DEPOSIT', 'TRANSFER_IN']:
                total_credits += amt
            else:
                total_debits += amt

    # Summary Row
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(60, 8, f"Total Credits: INR {total_credits:,.2f}", border=1, fill=True, align="C")
    pdf.cell(60, 8, f"Total Debits: INR {total_debits:,.2f}", border=1, fill=True, align="C")
    net_val = total_credits - total_debits
    pdf.cell(60, 8, f"Net Flow: INR {net_val:,.2f}", border=1, fill=True, align="C")
    pdf.ln(12)

    # Table Header
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(20, 7, "Txn ID", border=0, fill=True, align="C")
    pdf.cell(38, 7, "Date & Time", border=0, fill=True, align="L")
    pdf.cell(35, 7, "Type", border=0, fill=True, align="L")
    pdf.cell(32, 7, "Amount (INR)", border=0, fill=True, align="R")
    pdf.cell(25, 7, "Status", border=0, fill=True, align="C")
    pdf.cell(30, 7, "Flow", border=0, fill=True, align="C")
    pdf.ln()

    # Table Body
    pdf.set_font("Helvetica", "", 8)
    fill_row = False
    for t in transactions:
        pdf.set_fill_color(248, 250, 252) if fill_row else pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(241, 245, 249)
        pdf.set_text_color(15, 23, 42)

        is_credit = t.get('transaction_type') in ['DEPOSIT', 'TRANSFER_IN']
        flow_str = "+ CREDIT" if is_credit else "- DEBIT"

        amt_val = Decimal(str(t.get('amount', 0)))
        dt_str = f"{t.get('display_date', '')} {t.get('display_time', '')}"

        pdf.cell(20, 7, f"#{t.get('transaction_id')}", border="B", fill=True, align="C")
        pdf.cell(38, 7, dt_str, border="B", fill=True, align="L")
        pdf.cell(35, 7, str(t.get('transaction_type')), border="B", fill=True, align="L")

        pdf.set_font("Helvetica", "B", 8)
        if is_credit:
            pdf.set_text_color(5, 150, 105)
        else:
            pdf.set_text_color(220, 38, 38)
        pdf.cell(32, 7, f"{amt_val:,.2f}", border="B", fill=True, align="R")

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(25, 7, str(t.get('status', 'COMMITTED')), border="B", fill=True, align="C")
        pdf.cell(30, 7, flow_str, border="B", fill=True, align="C")
        pdf.ln()
        fill_row = not fill_row

    if not transactions:
        pdf.set_text_color(148, 163, 184)
        pdf.cell(180, 12, "No transactions recorded for this account period.", border="B", fill=False, align="C")
        pdf.ln()

    return bytes(pdf.output())


def generate_csv_statement(customer, account, transactions):
    """
    Generates a CSV string of transactions for a specific account.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header metadata
    writer.writerow(["KAPA BANK - ACCOUNT TRANSACTION STATEMENT"])
    writer.writerow(["Customer Name", customer.get('name')])
    writer.writerow(["Email", customer.get('email')])
    writer.writerow(["Account Number", account.get('account_number')])
    writer.writerow(["Account Type", account.get('account_type')])
    writer.writerow(["Current Balance", f"{Decimal(str(account.get('balance', 0))):.2f}"])
    writer.writerow(["Exported On", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([]) # blank line

    # Data columns
    writer.writerow(["Transaction ID", "Date", "Time", "Type", "Amount (INR)", "Flow", "Status"])
    for t in transactions:
        is_credit = t.get('transaction_type') in ['DEPOSIT', 'TRANSFER_IN']
        flow_str = "CREDIT" if is_credit else "DEBIT"
        writer.writerow([
            t.get('transaction_id'),
            t.get('display_date', ''),
            t.get('display_time', ''),
            t.get('transaction_type'),
            f"{Decimal(str(t.get('amount', 0))):.2f}",
            flow_str,
            t.get('status')
        ])

    return output.getvalue()

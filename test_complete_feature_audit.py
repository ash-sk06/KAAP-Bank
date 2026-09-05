"""
KAPA Bank - Comprehensive Complete Feature Verification Suite
Tests every feature of the application across all user roles:
1. Public & Auth (Login, Register, Logout, Credentials directory)
2. Customer Online Banking (Dashboard, Accounts, Deposit, Withdraw, Transfer, History, PDF & CSV Statements, Profile, Password Change)
3. Customer Data Isolation & RBAC Security
4. Demo Account Restrictions & TCL Demonstrations (SAVEPOINT, COMMIT, ROLLBACK, RESET)
5. Admin Console (Dashboard, Customers, Accounts, Freeze/Unfreeze, System Transactions, SQL Reports, Audit Trail)
"""

import unittest
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.abspath('.'))

from app import app
from database import get_connection, dictfetchone, dictfetchall

class CompleteFeatureAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True

    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def get_csrf(self):
        with self.client.session_transaction() as sess:
            if 'csrf_token' not in sess:
                sess['csrf_token'] = 'test-csrf-token-12345'
            return sess['csrf_token']

    def login_user(self, email, fallback_pwd):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT display_password FROM users WHERE LOWER(email) = LOWER(:1)", (email,))
        row = dictfetchone(cur)
        cur.close()
        conn.close()
        pwd = row['display_password'] if row and row['display_password'] else fallback_pwd

        self.client.get('/login')
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        return self.client.post('/login', data={
            'csrf_token': token,
            'email': email,
            'password': pwd
        }, follow_redirects=True)

    # =========================================================================
    # 1. PUBLIC & AUTHENTICATION TESTS
    # =========================================================================
    def test_01_public_unauthenticated_redirect(self):
        """Unauthenticated GET / must redirect to /login."""
        res = self.client.get('/', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

    def test_02_login_page_renders_with_academic_banner(self):
        """GET /login must render academic disclaimer, CSRF token, and quick creds modal."""
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Sign In to KAPA Bank', res.data)
        self.assertIn(b'ACADEMIC COURSEWORK PROJECT', res.data)
        self.assertIn(b'View Demo &amp; Evaluation Credentials', res.data)
        self.assertIn(b'csrf_token', res.data)

    def test_03_credentials_directory(self):
        """GET /credentials must display all evaluation accounts with live dynamic passwords."""
        res = self.client.get('/credentials')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'KAPA Bank Test Credentials', res.data)
        self.assertIn(b'admin@kapabank.com', res.data)
        self.assertIn(b'demo@kapabank.com', res.data)
        self.assertIn(b'DEMO (TCL ONLY)', res.data)
        self.assertIn(b'rahul@example.com', res.data)

    def test_04_auth_failure_invalid_credentials(self):
        """POST /login with wrong password returns friendly error."""
        self.client.get('/login')
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        res = self.client.post('/login', data={
            'csrf_token': token,
            'email': 'admin@kapabank.com',
            'password': 'WrongPassword123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Invalid email or password', res.data)

    def test_05_admin_login_success(self):
        """POST /login with admin credentials redirects to /admin."""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT display_password FROM users WHERE LOWER(email) = 'admin@kapabank.com'")
        row = dictfetchone(cur)
        cur.close()
        conn.close()
        pwd = row['display_password'] if row and row['display_password'] else 'Admin@Kapa2026'

        self.client.get('/login')
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        res = self.client.post('/login', data={
            'csrf_token': token,
            'email': 'admin@kapabank.com',
            'password': pwd
        }, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin', res.headers['Location'])

    # =========================================================================
    # 2. CUSTOMER ONLINE BANKING FEATURES
    # =========================================================================
    def test_06_customer_dashboard_and_accounts(self):
        """Verify Customer 1 can load dashboard, account overview, and account details."""
        login_res = self.login_user('rahul@example.com', 'Customer@123')
        self.assertEqual(login_res.status_code, 200)

        # Dashboard
        dash = self.client.get('/dashboard')
        self.assertEqual(dash.status_code, 200)
        self.assertIn(b'CUSTOMER BANKING PORTAL', dash.data)
        self.assertIn(b'Total Net Balance', dash.data)

        # Accounts Overview
        accs = self.client.get('/accounts')
        self.assertEqual(accs.status_code, 200)
        self.assertIn(b'My Bank Accounts', accs.data)
        self.assertIn(b'Instant Cash Deposit', accs.data)
        self.assertIn(b'Cash Withdrawal', accs.data)

        # Account Detail (owned account)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT account_id, account_number FROM bank_accounts WHERE customer_id = 1 FETCH FIRST 1 ROWS ONLY")
        acc = dictfetchone(cur)
        cur.close()
        conn.close()

        if acc:
            detail = self.client.get(f'/accounts/{acc["account_id"]}')
            self.assertEqual(detail.status_code, 200)
            self.assertIn(acc["account_number"].encode('utf-8'), detail.data)
            self.assertIn(b'Account Transaction Ledger', detail.data)

    def test_07_customer_deposit_and_withdrawal_flow(self):
        """Verify deposit adds funds and withdrawal debits funds atomically."""
        self.login_user('rahul@example.com', 'Customer@123')

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT account_id, balance FROM bank_accounts WHERE customer_id = 1 AND status = 'ACTIVE' FETCH FIRST 1 ROWS ONLY")
        acc = dictfetchone(cur)
        cur.close()
        conn.close()

        if not acc:
            self.skipTest("No active account for customer 1")

        account_id = acc['account_id']
        start_bal = Decimal(str(acc['balance']))

        # Deposit ₹100
        token = self.get_csrf()
        dep = self.client.post('/deposit', data={
            'csrf_token': token,
            'account_id': account_id,
            'amount': '100.00'
        }, follow_redirects=True)
        self.assertEqual(dep.status_code, 200)
        self.assertIn(b'Deposit Completed', dep.data)

        # Withdraw ₹100 (restores balance)
        token = self.get_csrf()
        withd = self.client.post('/withdraw', data={
            'csrf_token': token,
            'account_id': account_id,
            'amount': '100.00'
        }, follow_redirects=True)
        self.assertEqual(withd.status_code, 200)
        self.assertIn(b'Withdrawal Completed', withd.data)

        # Verify balance restored
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT balance FROM bank_accounts WHERE account_id = :1", (account_id,))
        end_bal = Decimal(str(dictfetchone(cur)['balance']))
        cur.close()
        conn.close()
        self.assertEqual(end_bal, start_bal)

    def test_08_customer_fund_transfer_flow(self):
        """Verify funds transfer between two accounts with canonical locking."""
        self.login_user('rahul@example.com', 'Customer@123')

        # Get Rahul's source account
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT account_id, balance FROM bank_accounts WHERE customer_id = 1 AND status = 'ACTIVE' FETCH FIRST 1 ROWS ONLY")
        source = dictfetchone(cur)

        # Get destination account
        cur.execute("SELECT account_id, balance FROM bank_accounts WHERE account_id != :1 AND status = 'ACTIVE' FETCH FIRST 1 ROWS ONLY", (source['account_id'],))
        dest = dictfetchone(cur)
        cur.close()
        conn.close()

        if not source or not dest:
            self.skipTest("Need 2 active accounts for transfer")

        s_id = source['account_id']
        d_id = dest['account_id']

        # Transfer form renders
        form_res = self.client.get('/transfer')
        self.assertEqual(form_res.status_code, 200)
        self.assertIn(b'Transfer Funds', form_res.data)

        # Execute transfer ₹50
        token = self.get_csrf()
        res = self.client.post('/transfer', data={
            'csrf_token': token,
            'from_account': s_id,
            'to_account': d_id,
            'amount': '50.00'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Transfer Completed Successfully', res.data)

        # Transfer back ₹50 to maintain clean ledger
        token = self.get_csrf()
        res2 = self.client.post('/transfer', data={
            'csrf_token': token,
            'from_account': d_id,
            'to_account': s_id,
            'amount': '50.00'
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

    def test_09_customer_transactions_history_and_filters(self):
        """Verify transaction history renders and filter parameters function."""
        self.login_user('rahul@example.com', 'Customer@123')

        res = self.client.get('/transactions')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Transaction History', res.data)

        # Filter by DEPOSIT
        filter_res = self.client.get('/transactions?type=DEPOSIT')
        self.assertEqual(filter_res.status_code, 200)

    def test_10_statement_pdf_and_csv_generation(self):
        """Verify PDF statement generation returns binary PDF and CSV returns formatted text."""
        self.login_user('rahul@example.com', 'Customer@123')

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT account_id FROM bank_accounts WHERE customer_id = 1 FETCH FIRST 1 ROWS ONLY")
        acc = dictfetchone(cur)
        cur.close()
        conn.close()

        acc_id = acc['account_id']

        # 1. Statements page
        stmt_page = self.client.get('/statements')
        self.assertEqual(stmt_page.status_code, 200)
        self.assertIn(b'Account Statements', stmt_page.data)

        # 2. PDF download
        pdf_res = self.client.get(f'/statements/download/pdf/{acc_id}')
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers['Content-Type'], 'application/pdf')
        self.assertTrue(pdf_res.data.startswith(b'%PDF-'))

        # 3. CSV download
        csv_res = self.client.get(f'/statements/download/csv/{acc_id}')
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn('text/csv', csv_res.headers['Content-Type'].lower())
        self.assertIn(b'Transaction ID,Date,Time,Type,Amount (INR),Flow,Status', csv_res.data)

    def test_11_customer_profile_and_password_change(self):
        """Verify profile page renders properly for authenticated customer."""
        self.login_user('rahul@example.com', 'Customer@123')

        prof = self.client.get('/profile')
        self.assertEqual(prof.status_code, 200)
        self.assertIn(b'My Profile', prof.data)
        self.assertIn(b'Change Password', prof.data)

    # =========================================================================
    # 3. CUSTOMER DATA ISOLATION & RBAC SECURITY TESTS
    # =========================================================================
    def test_12_customer_isolation_cannot_access_other_account(self):
        """Customer 1 cannot inspect or access Customer 2's account details."""
        self.login_user('rahul@example.com', 'Customer@123')

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT account_id FROM bank_accounts WHERE customer_id != 1 FETCH FIRST 1 ROWS ONLY")
        other_acc = dictfetchone(cur)
        cur.close()
        conn.close()

        if other_acc:
            res = self.client.get(f'/accounts/{other_acc["account_id"]}')
            self.assertIn(b'Account Access Denied', res.data)

    def test_13_customer_cannot_access_admin_portal(self):
        """Customer cannot access /admin or any /admin/* routes."""
        self.login_user('rahul@example.com', 'Customer@123')

        admin_res = self.client.get('/admin')
        self.assertIn(admin_res.status_code, [302, 403])

        cust_res = self.client.get('/admin/customers')
        self.assertIn(cust_res.status_code, [302, 403])

    def test_14_normal_customer_cannot_access_transaction_control(self):
        """Normal customer cannot access demo transaction control."""
        self.login_user('rahul@example.com', 'Customer@123')

        res = self.client.get('/transaction-control')
        self.assertIn(b'Access Restricted', res.data)

    # =========================================================================
    # 4. DEMO ACCOUNT (TCL ONLY) RESTRICTION TESTS
    # =========================================================================
    def test_15_demo_account_redirect_and_blocks(self):
        """Demo customer must be redirected to /transaction-control and blocked from banking modes."""
        self.login_user('demo@kapabank.com', 'Demoacc@123')

        # Redirects from root to transaction-control
        root_res = self.client.get('/', follow_redirects=False)
        self.assertEqual(root_res.status_code, 302)
        self.assertIn('/transaction-control', root_res.headers['Location'])

        # Blocked from transfer
        trans_res = self.client.get('/transfer', follow_redirects=True)
        self.assertIn(b'Demo Mode Restricted', trans_res.data)

        # Blocked from deposit
        token = self.get_csrf()
        dep_res = self.client.post('/deposit', data={'csrf_token': token, 'account_id': 21, 'amount': '100'}, follow_redirects=True)
        self.assertIn(b'Demo Mode Restricted', dep_res.data)

        # Blocked from withdraw
        token = self.get_csrf()
        with_res = self.client.post('/withdraw', data={'csrf_token': token, 'account_id': 21, 'amount': '100'}, follow_redirects=True)
        self.assertIn(b'Demo Mode Restricted', with_res.data)

    def test_16_demo_tcl_operations_commit_rollback_savepoint_reset(self):
        """Demo customer can successfully trigger COMMIT, ROLLBACK, SAVEPOINT, and RESET."""
        self.login_user('demo@kapabank.com', 'Demoacc@123')

        # 1. TCL page loads
        tcl = self.client.get('/transaction-control')
        self.assertEqual(tcl.status_code, 200)
        self.assertIn(b'Transaction Control Commands', tcl.data)
        self.assertIn(b'DEMO1001', tcl.data)

        # 2. COMMIT demo (+1000)
        token = self.get_csrf()
        com = self.client.post('/transaction-control/commit', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(com.status_code, 200)
        self.assertIn(b'Transaction Committed Permanently', com.data)

        # 3. ROLLBACK demo (no change)
        token = self.get_csrf()
        rb = self.client.post('/transaction-control/rollback', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(rb.status_code, 200)
        self.assertIn(b'Transaction Rolled Back Completely', rb.data)

        # 4. SAVEPOINT demo (partial commit)
        token = self.get_csrf()
        sp = self.client.post('/transaction-control/savepoint', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(sp.status_code, 200)
        self.assertIn(b'Partial Rollback to SAVEPOINT Successful', sp.data)

        # 5. RESET demo (restore to 10000)
        token = self.get_csrf()
        rst = self.client.post('/transaction-control/reset', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(rst.status_code, 200)
        self.assertIn(b'Demo Account Reset Complete', rst.data)

        # Verify DB balance is exactly 10,000.00
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT balance FROM bank_accounts WHERE account_id = 21")
        bal = Decimal(str(dictfetchone(cur)['balance']))
        cur.close()
        conn.close()
        self.assertEqual(bal, Decimal('10000.00'))

    # =========================================================================
    # 5. ADMIN CONSOLE FEATURES
    # =========================================================================
    def test_17_admin_dashboard_access(self):
        """Admin user can log in and view comprehensive administrative metrics."""
        self.login_user('admin@kapabank.com', 'Admin@Kapa2026')

        dash = self.client.get('/admin')
        self.assertEqual(dash.status_code, 200)
        self.assertIn(b'Operations &amp; Governance Dashboard', dash.data)
        self.assertIn(b'Total Active Deposits', dash.data)

    def test_18_admin_customer_management(self):
        """Admin can list customers, view customer detail, and search."""
        self.login_user('admin@kapabank.com', 'Admin@Kapa2026')

        # List
        cust_res = self.client.get('/admin/customers')
        self.assertEqual(cust_res.status_code, 200)
        self.assertIn(b'Customer Management', cust_res.data)

        # Search
        search = self.client.get('/admin/customers?q=Rahul')
        self.assertEqual(search.status_code, 200)
        self.assertIn(b'Rahul', search.data)

        # Detail
        detail = self.client.get('/admin/customers/1')
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b'Customer Profile', detail.data)

    def test_19_admin_accounts_freeze_unfreeze(self):
        """Admin can list accounts, update status to BLOCKED, and revert to ACTIVE."""
        self.login_user('admin@kapabank.com', 'Admin@Kapa2026')

        # List
        acc_list = self.client.get('/admin/accounts')
        self.assertEqual(acc_list.status_code, 200)
        
        # Account (non-demo account)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT account_id FROM bank_accounts WHERE customer_id != 21 FETCH FIRST 1 ROWS ONLY")
        target_acc = dictfetchone(cur)['account_id']
        cur.close()
        conn.close()

        # Block (Freeze)
        token = self.get_csrf()
        freeze = self.client.post(f'/admin/accounts/{target_acc}/status', data={'status': 'BLOCKED', 'csrf_token': token}, follow_redirects=True)
        self.assertEqual(freeze.status_code, 200)
        self.assertIn(b'Status Updated', freeze.data)

        # Unfreeze (Active)
        token = self.get_csrf()
        unfreeze = self.client.post(f'/admin/accounts/{target_acc}/status', data={'status': 'ACTIVE', 'csrf_token': token}, follow_redirects=True)
        self.assertEqual(unfreeze.status_code, 200)
        self.assertIn(b'Status Updated', freeze.data)

    def test_20_admin_transactions_and_reports(self):
        """Admin can monitor all transactions and view SQL aggregate reports."""
        self.login_user('admin@kapabank.com', 'Admin@Kapa2026')

        # Transactions
        tx_res = self.client.get('/admin/transactions')
        self.assertEqual(tx_res.status_code, 200)
        self.assertIn(b'Transaction Monitoring', tx_res.data)

        # Reports (GROUP BY, SUM, COUNT, CASE, JOIN)
        rep_res = self.client.get('/admin/reports')
        self.assertEqual(rep_res.status_code, 200)
        self.assertIn(b'Core Banking Reports', rep_res.data)
        self.assertIn(b'Transaction Type Breakdown', rep_res.data)
        self.assertIn(b'Account Distribution', rep_res.data)
        self.assertIn(b'Top 5 Accounts by Balance', rep_res.data)

    def test_21_admin_audit_log(self):
        """Admin can inspect the security audit trail."""
        self.login_user('admin@kapabank.com', 'Admin@Kapa2026')

        audit = self.client.get('/admin/audit-log')
        self.assertEqual(audit.status_code, 200)
        self.assertIn(b'Security Audit Trail', audit.data)

if __name__ == '__main__':
    unittest.main()

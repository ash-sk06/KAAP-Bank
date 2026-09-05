"""
Banking Operations & Financial Integrity Test Suite
Verifies Deposit, Withdrawal, Transfer, ACID transaction controls, and balance calculations.
"""
import unittest
from decimal import Decimal
from app import app
from database import get_connection, dictfetchone

class BankingOperationsTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_01_customer_deposit_and_withdraw(self):
        """Verify atomic deposit and withdrawal updates balances correctly."""
        # 1. Login as Rahul (customer_id = 1)
        self.client.get('/login')
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        login_res = self.client.post('/login', data={
            'csrf_token': token,
            'email': 'rahul@example.com',
            'password': 'Customer@123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # 2. Get an account owned by Rahul
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT account_id, balance, account_number FROM bank_accounts WHERE customer_id = 1 AND status = 'ACTIVE' FETCH FIRST 1 ROWS ONLY")
        acc = dictfetchone(cur)
        cur.close()
        conn.close()

        if not acc:
            self.skipTest("No active account for customer 1")

        account_id = acc['account_id']
        initial_balance = Decimal(str(acc['balance']))

        # 3. Perform Deposit of 500
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        dep_res = self.client.post('/deposit', data={
            'csrf_token': token,
            'account_id': account_id,
            'amount': '500.00'
        }, follow_redirects=True)
        self.assertEqual(dep_res.status_code, 200)
        self.assertIn(b'Deposit Completed', dep_res.data)

        # Verify balance in DB
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT balance FROM bank_accounts WHERE account_id = :1", (account_id,))
        new_balance = Decimal(str(dictfetchone(cur)['balance']))
        self.assertEqual(new_balance, initial_balance + Decimal('500.00'))

        # 4. Perform Withdrawal of 500 (restores initial balance)
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        with_res = self.client.post('/withdraw', data={
            'csrf_token': token,
            'account_id': account_id,
            'amount': '500.00'
        }, follow_redirects=True)
        self.assertEqual(with_res.status_code, 200)
        self.assertIn(b'Withdrawal Completed', with_res.data)

        cur.execute("SELECT balance FROM bank_accounts WHERE account_id = :1", (account_id,))
        final_balance = Decimal(str(dictfetchone(cur)['balance']))
        self.assertEqual(final_balance, initial_balance)
        cur.close()
        conn.close()

    def test_02_admin_acid_tcl_operations(self):
        """Verify Admin COMMIT, ROLLBACK, SAVEPOINT, and RESET operations."""
        # 1. Login as Admin
        self.client.get('/login')
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        self.client.post('/login', data={
            'csrf_token': token,
            'email': 'admin@kapabank.com',
            'password': 'Admin@Kapa2026'
        }, follow_redirects=True)

        # 2. Reset Demo Account (DEMO_ACCOUNT_ID = 21)
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        reset_res = self.client.post('/admin/transaction-control/reset', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(reset_res.status_code, 200)
        self.assertIn(b'Demo Account Reset Complete', reset_res.data)

        # 3. Test ROLLBACK (+2000 tentative, rolled back)
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        rb_res = self.client.post('/admin/transaction-control/rollback', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(rb_res.status_code, 200)
        self.assertIn(b'Transaction Rolled Back Completely', rb_res.data)

        # 4. Test COMMIT (+1000)
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        commit_res = self.client.post('/admin/transaction-control/commit', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(commit_res.status_code, 200)
        self.assertIn(b'Transaction Committed Permanently', commit_res.data)

        # 5. Test SAVEPOINT (+1000 committed, +2000 discarded)
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        sp_res = self.client.post('/admin/transaction-control/savepoint', data={'csrf_token': token}, follow_redirects=True)
        self.assertEqual(sp_res.status_code, 200)
        self.assertIn(b'Partial Rollback to SAVEPOINT Successful', sp_res.data)

        # Final Reset to keep demo account clean
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')
        self.client.post('/admin/transaction-control/reset', data={'csrf_token': token}, follow_redirects=True)

if __name__ == '__main__':
    unittest.main()

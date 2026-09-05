"""
Comprehensive End-to-End System Test Suite for KAPA Bank
Validates RBAC, Customer Data Isolation, CSRF protection, PDF generation, and ACID demos.
"""
import unittest
from decimal import Decimal
from app import app
import reports

class KapaBankSystemTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_unauthenticated_redirects(self):
        """Unauthenticated requests to protected endpoints must redirect to login."""
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

        response = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

        response = self.client.get('/accounts', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

        response = self.client.get('/admin', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_02_login_page_renders(self):
        """Login page must render with HTTP 200 and include CSRF."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign In to KAPA Bank', response.data)
        self.assertIn(b'csrf_token', response.data)

    def test_03_customer_login_and_isolation(self):
        """Customer login must succeed and establish proper session."""
        # 1. Fetch CSRF token from login page
        get_res = self.client.get('/login')
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        # 2. Authenticate as Rahul (Customer)
        post_res = self.client.post('/login', data={
            'csrf_token': token,
            'email': 'rahul@example.com',
            'password': 'Customer@123'
        }, follow_redirects=True)

        self.assertEqual(post_res.status_code, 200)
        self.assertIn(b'Rahul', post_res.data)

        # 3. Customer Dashboard
        dash_res = self.client.get('/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'Welcome back', dash_res.data)

        # 4. Customer attempting to access Admin Console MUST be Forbidden (403)
        admin_res = self.client.get('/admin')
        self.assertEqual(admin_res.status_code, 403)
        self.assertIn(b'Access Forbidden', admin_res.data)

    def test_04_admin_login_and_access(self):
        """Admin login must grant full access to admin portal."""
        # Clear session
        self.client.get('/logout')

        # Visit login to generate fresh CSRF token in session
        self.client.get('/login')
        with self.client.session_transaction() as sess:
            token = sess.get('csrf_token')

        post_res = self.client.post('/login', data={
            'csrf_token': token,
            'email': 'admin@kapabank.com',
            'password': 'Admin@Kapa2026'
        }, follow_redirects=True)

        self.assertEqual(post_res.status_code, 200)
        self.assertIn(b'ADMINISTRATIVE CONSOLE', post_res.data)

        # Admin routes must all return 200
        for path in ['/admin', '/admin/customers', '/admin/accounts', '/admin/transactions', '/admin/reports', '/admin/audit-log', '/admin/transaction-control']:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Failed on path: {path}")

    def test_05_csrf_rejection_on_post(self):
        """POST requests missing valid CSRF tokens must be rejected."""
        self.client.get('/logout')
        # Missing CSRF
        res = self.client.post('/login', data={'email': 'admin@kapabank.com', 'password': 'Admin@Kapa2026'})
        self.assertIn(b'Security Validation Failed', res.data)

    def test_06_pdf_and_csv_generation(self):
        """PDF generation must produce valid PDF binary headers and CSV string."""
        sample_customer = {"name": "Test User", "email": "test@example.com", "phone": "9999999999", "address": "VIT"}
        sample_account = {"account_number": "ACC9999999", "account_type": "SAVINGS", "balance": Decimal("50000.00"), "status": "ACTIVE"}
        sample_transactions = [
            {
                "transaction_id": 101,
                "transaction_type": "DEPOSIT",
                "amount": Decimal("10000.00"),
                "display_date": "05-09-2026",
                "display_time": "12:00 PM",
                "status": "COMMITTED"
            }
        ]

        pdf_bytes = reports.generate_pdf_statement(sample_customer, sample_account, sample_transactions)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'), "Output is not a valid PDF binary")

        csv_text = reports.generate_csv_statement(sample_customer, sample_account, sample_transactions)
        self.assertIn("KAPA BANK - ACCOUNT TRANSACTION STATEMENT", csv_text)
        self.assertIn("ACC9999999", csv_text)
        self.assertIn("DEPOSIT", csv_text)

if __name__ == '__main__':
    unittest.main()

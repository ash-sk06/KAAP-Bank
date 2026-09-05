"""
KAPA Bank Admin & Customer Bootstrap Script
Creates initial administrator account and provisions logins for existing customers.
"""
import os
import logging
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from database import get_connection, dictfetchall, dictfetchone

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def bootstrap():
    admin_email = os.getenv("ADMIN_EMAIL", "admin@kapabank.com").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@Kapa2026").strip()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # 1. Check/create Administrator account
        cursor.execute("SELECT user_id, email, role FROM users WHERE LOWER(email) = :1", (admin_email,))
        admin_user = dictfetchone(cursor)

        if not admin_user:
            hashed_pwd = generate_password_hash(admin_password)
            cursor.execute("""
                INSERT INTO users (email, password_hash, role, customer_id, is_active)
                VALUES (:1, :2, 'ADMIN', NULL, 1)
            """, (admin_email, hashed_pwd))
            
            # Retrieve generated user_id
            cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = :1", (admin_email,))
            admin_row = dictfetchone(cursor)
            admin_uid = admin_row['user_id'] if admin_row else None

            cursor.execute("""
                INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, ip_address)
                VALUES (:1, 'BOOTSTRAP_ADMIN', 'USER', :2, 'Initial administrator account provisioned', '127.0.0.1')
            """, (admin_uid, admin_uid))

            logger.info("Admin account created successfully:")
            logger.info("  Email: %s", admin_email)
            logger.info("  Role:  ADMIN")
        else:
            logger.info("Admin account already exists for %s (User ID: %s)", admin_email, admin_user['user_id'])

        # 2. Provision user logins for any existing customers who do not have one
        cursor.execute("SELECT customer_id, name, email FROM customers")
        all_customers = dictfetchall(cursor)

        default_customer_pwd = os.getenv("DEFAULT_CUSTOMER_PASSWORD", "Customer@123")
        customer_pwd_hash = generate_password_hash(default_customer_pwd)

        for cust in all_customers:
            cust_email = cust['email'].strip().lower()
            cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = :1", (cust_email,))
            existing_user = dictfetchone(cursor)

            if not existing_user:
                cursor.execute("""
                    INSERT INTO users (email, password_hash, role, customer_id, is_active)
                    VALUES (:1, :2, 'CUSTOMER', :3, 1)
                """, (cust_email, customer_pwd_hash, cust['customer_id']))

                logger.info("Provisioned customer user: %s (Email: %s, Default Pwd: %s)",
                            cust['name'], cust_email, default_customer_pwd)

        connection.commit()
        logger.info("Bootstrap process completed successfully!")

    except Exception as e:
        connection.rollback()
        logger.error("Bootstrap failed: %s", str(e), exc_info=True)
        raise
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    bootstrap()

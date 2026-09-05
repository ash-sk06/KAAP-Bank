import os
import base64
from pathlib import Path

import oracledb
from dotenv import load_dotenv

load_dotenv()


def get_wallet_path():
    local_wallet_path = os.getenv("ORACLE_WALLET_PATH")

    if local_wallet_path:
        return local_wallet_path

    wallet_dir = Path("/tmp/kapa_oracle_wallet")
    wallet_dir.mkdir(parents=True, exist_ok=True)

    tnsnames_data = os.getenv("ORACLE_TNSNAMES")
    ewallet_data = os.getenv("ORACLE_EWALLET_PEM")

    if not tnsnames_data or not ewallet_data:
        raise RuntimeError(
            "Oracle wallet environment variables are missing."
        )

    tnsnames_file = wallet_dir / "tnsnames.ora"
    ewallet_file = wallet_dir / "ewallet.pem"

    if not tnsnames_file.exists():
        tnsnames_file.write_bytes(
            base64.b64decode(tnsnames_data)
        )

    if not ewallet_file.exists():
        ewallet_file.write_bytes(
            base64.b64decode(ewallet_data)
        )

    return str(wallet_dir)


def get_connection():

    wallet_path = get_wallet_path()

    connection = oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN"),
        config_dir=wallet_path,
        wallet_location=wallet_path,
        wallet_password=os.getenv("ORACLE_WALLET_PASSWORD")
    )

    return connection


def dictfetchall(cursor):
    """Converts cursor results to list of dicts with lowercase column names"""
    if cursor.description is None:
        return []
    columns = [col[0].lower() for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def dictfetchone(cursor):
    """Converts single row to dict, returns None if no row"""
    if cursor.description is None:
        return None
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [col[0].lower() for col in cursor.description]
    return dict(zip(columns, row))
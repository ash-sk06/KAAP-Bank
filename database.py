import os
import oracledb
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    connection = oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN"),
        config_dir=os.getenv("ORACLE_WALLET_PATH"),
        wallet_location=os.getenv("ORACLE_WALLET_PATH"),
        wallet_password=os.getenv("ORACLE_WALLET_PASSWORD")
    )

    return connection
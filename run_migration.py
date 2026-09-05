"""
KAPA Bank Database Migration V2 Runner
Executes additive DDL statements safely.
"""
import re
import logging
from database import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    connection = get_connection()
    cursor = connection.cursor()
    
    with open("database/migration_v2.sql", "r") as f:
        sql_content = f.read()

    # Split by semicolon, clean up comments and empty statements
    statements = [s.strip() for s in sql_content.split(";") if s.strip()]
    
    for stmt in statements:
        # Strip leading comments
        clean_stmt = re.sub(r"^--.*$", "", stmt, flags=re.MULTILINE).strip()
        if not clean_stmt:
            continue
        try:
            logger.info("Executing: %s...", clean_stmt[:60].replace("\n", " "))
            cursor.execute(clean_stmt)
            logger.info("  -> Success")
        except Exception as e:
            err_str = str(e)
            if "ORA-00955" in err_str or "already used" in err_str:
                logger.warning("  -> Object already exists, skipping.")
            elif "ORA-01408" in err_str or "such column list already indexed" in err_str:
                logger.warning("  -> Index already exists, skipping.")
            else:
                logger.error("  -> Failed: %s", err_str)
                raise
                
    connection.commit()
    cursor.close()
    connection.close()
    logger.info("Migration V2 completed successfully!")

if __name__ == "__main__":
    run_migration()

import os

import psycopg2
from dotenv import load_dotenv


"""
Simple script to test a raw connection to a Postgres database
(e.g. Neon, Railway, Render, etc.).

Make sure your `.env` in this folder contains something like:

    DB_USER=...
    DB_PASSWORD=...
    DB_HOST=...
    DB_PORT=5432
    DB_NAME=...

Then run (from this folder, with venv active):

    python test_db_connection.py
"""


def main() -> None:
    load_dotenv()

    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "postgres")
    sslmode = os.getenv("DB_SSLMODE", "require")

    try:
        connection = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            dbname=dbname,
            sslmode=sslmode,
        )
        print("Connection successful!")

        cursor = connection.cursor()
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        print("Current Time:", result)

        cursor.close()
        connection.close()
        print("Connection closed.")
    except Exception as e:  # noqa: BLE001
        print(f"Failed to connect: {e}")


if __name__ == "__main__":
    main()


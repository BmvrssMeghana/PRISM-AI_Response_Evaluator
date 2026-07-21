"""
PRISM — Database Setup Script
Creates the prism_db PostgreSQL database if it doesn't exist.
Run once before starting the server:
    python setup_db.py
"""
import asyncio
import asyncpg
import sys

async def create_database():
    # Connect to the default 'postgres' database first
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="root",
        database="postgres",  # connect to default db first
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", "prism_db"
        )
        if exists:
            print("[OK] Database 'prism_db' already exists.")
        else:
            await conn.execute("CREATE DATABASE prism_db")
            print("[OK] Database 'prism_db' created successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(create_database())
        print("[OK] Database setup complete. You can now start the server.")
    except Exception as e:
        print(f"[ERROR] {e}")
        print("\nMake sure PostgreSQL is running and credentials are correct.")
        print("Expected: host=localhost, port=5432, user=postgres, password=root")
        sys.exit(1)

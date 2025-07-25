import os
from psycopg2 import connect
from psycopg2.errors import OperationalError


class PGDatabase:
    _instance = None

    def __init__(self, dsn: str):
        try:
            self.connection = connect(dsn=dsn)
        except OperationalError as e:
            raise Exception(f"Failed to connect to database with dsn {dsn}: {e}")
        self.cursor = self.connection.cursor()

    @staticmethod
    def connect_to_db():
        if PGDatabase._instance is None:
            PGDatabase._instance = PGDatabase(
                dsn=os.getenv("DATABASE_URI"),
            )
        return PGDatabase._instance

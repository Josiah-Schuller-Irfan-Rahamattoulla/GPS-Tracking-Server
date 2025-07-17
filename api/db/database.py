import os
from psycopg2 import connect


class PGDatabase:
    _instance = None

    def __init__(self, dsn: str):
        self.connection = connect(
            dsn=dsn
        )
        self.cursor = self.connection.cursor()

    @staticmethod
    def connect_to_db():
        if PGDatabase._instance is None:
            PGDatabase._instance = PGDatabase(
                dsn=os.getenv("DATABASE_URI"),
            )
        return PGDatabase._instance

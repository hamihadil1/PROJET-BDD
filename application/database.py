# database.py - VERSION CORRIGÉE
import os
import psycopg2
import pandas as pd
import warnings
warnings.filterwarnings('ignore')


class DatabaseConnection:
    def __init__(self):
        self.conn = None
        # VOTRE URL RENDER
        self.connection_string = "postgresql://university_db_8ajz_user:7QBiINNF1yJ8Ppq3Df8KS2aLtmnPtZ48@dpg-d5n8la94tr6s73d3n30g-a.virginia-postgres.render.com/university_db_8ajz"

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                self.connection_string,
                sslmode="require"
            )
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion : {e}")
            return False

    def execute_query(self, query, params=None):
        try:
            if not self.conn:
                self.connect()
            
            # Version simple sans warning
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
        except Exception as e:
            print(f"❌ Erreur dans la requête : {e}")
            return pd.DataFrame()



db = DatabaseConnection()
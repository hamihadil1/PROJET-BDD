# database.py
# Connexion directe à PostgreSQL avec psycopg2 et Pandas

import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd


class DatabaseConnection:
    """
    Classe permettant de gérer la connexion à une base de données PostgreSQL,
    d'exécuter des requêtes SQL, d'appeler des fonctions et des procédures stockées.
    """

    def __init__(self):
        # Objet de connexion (initialement vide)
        self.conn = None

        # Configuration de la base de données
        self.config = {
            "dbname": "unuversity",
            "user": "postgres",
            "password": "0000",
            "host": "localhost",
            "port": "5433"
        }

    def connect(self):
        """
        Établir une connexion avec la base de données PostgreSQL
        :return: True si la connexion réussit, False sinon
        """
        try:
            self.conn = psycopg2.connect(**self.config)
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion : {e}")
            return False

    def execute_query(self, query, params=None):
        """
        Exécuter une requête SQL (SELECT) et retourner le résultat
        sous forme de DataFrame Pandas.

        :param query: requête SQL
        :param params: paramètres optionnels
        :return: pandas.DataFrame
        """
        try:
            # Vérifier la connexion
            if not self.conn:
                self.connect()

            # Exécuter la requête et charger le résultat dans un DataFrame
            df = pd.read_sql_query(query, self.conn, params=params)
            return df

        except Exception as e:
            print(f"❌ Erreur dans la requête : {e}")
            return pd.DataFrame()

    def call_function(self, function_name, params=None):
        """
        Appeler une fonction PostgreSQL et retourner le résultat
        sous forme de DataFrame.

        :param function_name: nom de la fonction PostgreSQL
        :param params: paramètres de la fonction
        :return: pandas.DataFrame
        """
        try:
            if not self.conn:
                self.connect()

            cursor = self.conn.cursor(cursor_factory=RealDictCursor)

            if params:
                placeholders = ', '.join(['%s'] * len(params))
                query = f"SELECT * FROM {function_name}({placeholders})"
                cursor.execute(query, params)
            else:
                cursor.execute(f"SELECT * FROM {function_name}()")

            results = cursor.fetchall()
            cursor.close()

            return pd.DataFrame(results)

        except Exception as e:
            print(f"❌ Erreur lors de l'appel de la fonction : {e}")
            return pd.DataFrame()

    def execute_procedure(self, procedure_name, params=None):
        """
        Exécuter une procédure stockée PostgreSQL (INSERT, UPDATE, DELETE).

        :param procedure_name: nom de la procédure
        :param params: paramètres de la procédure
        :return: True si succès, False sinon
        """
        try:
            if not self.conn:
                self.connect()

            cursor = self.conn.cursor()

            if params:
                placeholders = ', '.join(['%s'] * len(params))
                query = f"CALL {procedure_name}({placeholders})"
                cursor.execute(query, params)
            else:
                cursor.execute(f"CALL {procedure_name}()")

            # Valider la transaction
            self.conn.commit()
            cursor.close()

            return True

        except Exception as e:
            print(f"❌ Erreur lors de l'exécution de la procédure : {e}")
            return False

    def close(self):
        """
        Fermer la connexion à la base de données
        """
        if self.conn:
            self.conn.close()
            self.conn = None


# Instance globale de la connexion
db = DatabaseConnection()

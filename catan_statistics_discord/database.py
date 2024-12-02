import enum
import sqlite3

connection = sqlite3.connect("data/catan.db")

cursor = connection.cursor()


class Expansions(enum.Enum):
    seafarers = 1
    cities_and_knights = 2


expansion_query = "select uuid, name from expansions;"
db_expansions = cursor.execute(expansion_query).fetchall()

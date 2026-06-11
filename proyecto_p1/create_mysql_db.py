from pymongo import MongoClient
from config import Config


def create_database():
    client = None
    try:
        client = MongoClient(Config.MONGO_URI)
        db = client[Config.MONGO_DB]
        db.users.create_index("email", unique=True)
        db.users.create_index("id", unique=True)
        print(f"Base de datos MongoDB `{Config.MONGO_DB}` preparada.")
    except Exception as exc:
        print("No se pudo conectar a MongoDB. Verifica que el servidor esté en ejecución y que la configuración en config.py sea correcta.")
        print(exc)
        raise
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    create_database()

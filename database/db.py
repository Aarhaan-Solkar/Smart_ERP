# database/db.py
# This file is currently not in use as the application
# has been switched to use dummy data instead of MongoDB.

# import pymongo

# # --- Configuration ---
# MONGO_URI = "mongodb://localhost:27017/"
# DB_NAME = "SmartERP"

# def init_db():
#     """
#     Initializes and returns a connection to the MongoDB database.
#     """
#     try:
#         client = pymongo.MongoClient(MONGO_URI)
#         client.admin.command('ismaster')
#         db = client[DB_NAME]
#         return db
#     except pymongo.errors.ConnectionFailure as e:
#         print(f"Could not connect to MongoDB: {e}")
#         raise

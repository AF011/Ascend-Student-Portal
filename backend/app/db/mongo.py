from pymongo import MongoClient
import certifi
from app.config import settings

# MongoDB Client
client = None
db = None


def connect_to_mongo():
    """Connect to MongoDB"""
    global client, db
    try:
        # Add SSL certificate for MongoDB Atlas - THIS FIXES THE SSL ERROR
        client = MongoClient(
            settings.MONGODB_URL,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000
        )
        
        # Test connection
        client.admin.command('ping')
        
        db = client[settings.DATABASE_NAME]
        print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")
        
        # Create indexes
        db.users.create_index("email", unique=True)
        db.users.create_index("google_id", unique=True, sparse=True)
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        raise


def close_mongo_connection():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("✅ MongoDB connection closed")


def get_database():
    """Get database instance"""
    return db
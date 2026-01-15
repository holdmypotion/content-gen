import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

from config import settings
from utils.auth import hash_password, verify_password

logger = logging.getLogger(__name__)


class UsersDB:
    """Users collection management."""
    
    def __init__(self, db):
        self.db = db
        self._create_indexes()
    
    def _create_indexes(self):
        """Create indexes for users collection."""
        try:
            self.db.users.create_index("email", unique=True)
            self.db.users.create_index("username", unique=True)
            logger.info("User indexes created successfully")
        except Exception as e:
            logger.warning(f"Failed to create user indexes: {str(e)}")
    
    def create_user(self, email: str, username: str, password: str) -> str:
        """
        Create a new user.
        
        Args:
            email: User email
            username: User username
            password: Plain text password
            
        Returns:
            str: User ID
        """
        try:
            # Check if user exists
            if self.db.users.find_one({"email": email}):
                raise ValueError("Email already registered")
            
            if self.db.users.find_one({"username": username}):
                raise ValueError("Username already taken")
            
            user_data = {
                "email": email,
                "username": username,
                "password": hash_password(password),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = self.db.users.insert_one(user_data)
            logger.info(f"User created with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        try:
            user = self.db.users.find_one({"email": email})
            if user:
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            raise
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        try:
            user = self.db.users.find_one({"username": username})
            if user:
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            logger.error(f"Error getting user by username: {str(e)}")
            raise
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            user = self.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user['_id'] = str(user['_id'])
            return user
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            raise
    
    def verify_user(self, email_or_username: str, password: str) -> Optional[str]:
        """
        Verify user credentials.
        
        Args:
            email_or_username: User email or username
            password: Plain text password
            
        Returns:
            str: User ID if credentials are correct, None otherwise
        """
        try:
            user = self.db.users.find_one({
                "$or": [
                    {"email": email_or_username},
                    {"username": email_or_username}
                ]
            })
            
            if not user:
                return None
            
            if verify_password(password, user['password']):
                return str(user['_id'])
            return None
        except Exception as e:
            logger.error(f"Error verifying user: {str(e)}")
            return None

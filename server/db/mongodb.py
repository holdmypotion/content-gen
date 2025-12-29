import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId

from config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    """MongoDB client wrapper for content generation tasks."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
    
    def connect(self):
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000
            )
            # Verify connection
            self.client.admin.command('ping')
            self.db = self.client[settings.MONGODB_DB_NAME]
            logger.info(f"Connected to MongoDB database: {settings.MONGODB_DB_NAME}")
            self._create_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    def _create_indexes(self):
        """Create necessary indexes for collections."""
        try:
            # Index for timestamps to enable TTL and sorting
            self.db.contents.create_index("timestamp")
            self.db.contents.create_index("provider")
            self.db.contents.create_index("type")
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.warning(f"Failed to create indexes: {str(e)}")
    
    def save_content(self, data: Dict[str, Any]) -> str:
        """
        Save content data to MongoDB.
        
        Args:
            data: Dictionary containing content data
            
        Returns:
            str: The inserted document ID
        """
        try:
            # Ensure timestamp is set
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            
            result = self.db.contents.insert_one(data)
            logger.info(f"Document saved to MongoDB with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {str(e)}")
            raise
    
    def update_content(self, document_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update existing content document.
        
        Args:
            document_id: MongoDB document ID
            update_data: Dictionary with fields to update
            
        Returns:
            bool: True if update was successful
        """
        try:
            update_data['updated_at'] = datetime.now().isoformat()
            result = self.db.contents.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                logger.info(f"Document {document_id} updated successfully")
                return True
            else:
                logger.warning(f"No document found with ID: {document_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating document {document_id}: {str(e)}")
            raise
    
    def get_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve content by ID.
        
        Args:
            document_id: MongoDB document ID
            
        Returns:
            dict: The document data or None if not found
        """
        try:
            doc = self.db.contents.find_one({"_id": ObjectId(document_id)})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {str(e)}")
            raise
    
    def get_all_contents(
        self,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "timestamp",
        descending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all content documents with pagination.
        
        Args:
            skip: Number of documents to skip
            limit: Maximum documents to return
            sort_by: Field to sort by
            descending: Sort in descending order if True
            
        Returns:
            list: List of documents
        """
        try:
            sort_order = -1 if descending else 1
            documents = list(
                self.db.contents.find()
                .sort(sort_by, sort_order)
                .skip(skip)
                .limit(limit)
            )
            # Convert ObjectId to string
            for doc in documents:
                logger.info(f"Document _id before conversion: {doc.get('_id')} (type: {type(doc.get('_id'))})")
                doc['_id'] = str(doc['_id'])
                logger.info(f"Document _id after conversion: {doc.get('_id')}")
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            raise
    
    def get_contents_by_type(
        self,
        content_type: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve content documents by type (idea, post, etc).
        
        Args:
            content_type: Type of content to retrieve
            skip: Number of documents to skip
            limit: Maximum documents to return
            
        Returns:
            list: List of documents
        """
        try:
            documents = list(
                self.db.contents.find({"type": content_type})
                .sort("timestamp", -1)
                .skip(skip)
                .limit(limit)
            )
            for doc in documents:
                doc['_id'] = str(doc['_id'])
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents by type: {str(e)}")
            raise
    
    def delete_content(self, document_id: str) -> bool:
        """
        Delete a content document.
        
        Args:
            document_id: MongoDB document ID
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            result = self.db.contents.delete_one({"_id": ObjectId(document_id)})
            if result.deleted_count > 0:
                logger.info(f"Document {document_id} deleted successfully")
                return True
            else:
                logger.warning(f"No document found with ID: {document_id}")
                return False
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            raise
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


# Global instance
_db_instance: Optional[MongoDB] = None


def get_db() -> MongoDB:
    """Get or create MongoDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = MongoDB()
    return _db_instance


def close_db():
    """Close MongoDB connection."""
    global _db_instance
    if _db_instance:
        _db_instance.close()
        _db_instance = None
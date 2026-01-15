#!/usr/bin/env python3
"""
Script to attach existing posts to a user.
Useful for migrating content when implementing user authentication.

Usage:
    python attach_posts_to_user.py <user_id>
    
Example:
    python attach_posts_to_user.py 69692cc3b0e627f3359b8ae3
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_db


def attach_posts_to_user(user_id: str):
    """Attach all posts without user_id to the specified user."""
    try:
        db = get_db()
        
        # Find all content documents without user_id
        print(f"\n🔍 Searching for posts without user_id...")
        unattached_posts = list(db.db.contents.find({"user_id": {"$exists": False}}))
        
        if not unattached_posts:
            print("✅ No posts found without user_id. All posts are already attached to users.")
            return
        
        print(f"📊 Found {len(unattached_posts)} posts without user_id")
        
        # Confirm action
        print(f"\n⚠️  This will attach {len(unattached_posts)} posts to user: {user_id}")
        confirm = input("Continue? (yes/no): ").strip().lower()
        
        if confirm != "yes":
            print("❌ Cancelled")
            return
        
        # Update all posts
        result = db.db.contents.update_many(
            {"user_id": {"$exists": False}},
            {
                "$set": {
                    "user_id": user_id,
                    "attached_at": datetime.now().isoformat()
                }
            }
        )
        
        print(f"\n✅ Success!")
        print(f"   Modified: {result.modified_count} posts")
        print(f"   User ID: {user_id}")
        
        # Show sample of updated posts
        sample = list(db.db.contents.find({"user_id": user_id}).limit(3))
        print(f"\n📋 Sample of attached posts:")
        for i, post in enumerate(sample, 1):
            title = post.get('reference_keywords', 'Unknown')
            if len(title) > 50:
                title = title[:50] + "..."
            print(f"   {i}. {title}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python attach_posts_to_user.py <user_id>")
        print("\nExample:")
        print("  python attach_posts_to_user.py 69692cc3b0e627f3359b8ae3")
        sys.exit(1)
    
    user_id = sys.argv[1]
    attach_posts_to_user(user_id)

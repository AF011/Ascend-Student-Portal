"""
Student Service - Enhanced with Array Management
Path: backend/app/services/student_service.py

FINAL FIXED VERSION: Handles date string to datetime conversion for MongoDB

Handles student profile CRUD operations including:
- Complete profile management
- Array operations (education, experience, projects, skills, certifications)
- Embedding generation
- Date string to datetime object conversion (MongoDB compatible)
"""

from bson import ObjectId
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from app.db.mongo import get_database


def prepare_profile_data_for_storage(profile_data: dict) -> dict:
    """
    Prepare profile data for MongoDB storage by converting date strings to datetime objects
    MongoDB can store datetime but not date objects, so we convert date -> datetime
    """
    import copy
    data = copy.deepcopy(profile_data)
    
    # Convert date_of_birth string to datetime (MongoDB compatible)
    if data.get('date_of_birth'):
        if isinstance(data['date_of_birth'], str):
            try:
                # Parse string date and convert to datetime at midnight
                parsed_date = datetime.strptime(data['date_of_birth'], '%Y-%m-%d')
                data['date_of_birth'] = parsed_date  # Store as datetime
            except Exception as e:                
                data['date_of_birth'] = None
        elif isinstance(data['date_of_birth'], date):
            # Convert date object to datetime
            data['date_of_birth'] = datetime.combine(data['date_of_birth'], datetime.min.time())
    
    # Convert availability_date in preferences
    if 'preferences' in data and isinstance(data['preferences'], dict):
        if data['preferences'].get('availability_date'):
            if isinstance(data['preferences']['availability_date'], str):
                try:
                    parsed_date = datetime.strptime(data['preferences']['availability_date'], '%Y-%m-%d')
                    data['preferences']['availability_date'] = parsed_date  # Store as datetime
                except Exception as e:                    
                    data['preferences']['availability_date'] = None
            elif isinstance(data['preferences']['availability_date'], date):
                # Convert date object to datetime
                data['preferences']['availability_date'] = datetime.combine(
                    data['preferences']['availability_date'], 
                    datetime.min.time()
                )
    
    return data


class StudentService:
    """Service layer for student-related operations"""
    
    def get_database(self):
        """Helper to get database instance"""
        db = get_database()
        if db is None:
            raise Exception("Database not connected")
        return db
    
    async def get_student_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get student profile by user ID"""
        db = self.get_database()
        user = db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return None
        
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
            "full_name": user.get("full_name"),
            "profile_picture": user.get("profile_picture"),
            "profile_completed": user.get("profile_completed", False),
            "profile_data": user.get("profile_data"),
            "has_embedding": user.get("profile_embedding") is not None,
            "embedding_generated_at": user.get("embedding_generated_at"),
            "created_at": user["created_at"],
            "updated_at": user["updated_at"]
        }
    
    async def complete_student_profile(
        self, 
        user_id: str, 
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete student profile and generate embedding
        
        Args:
            user_id: User ID
            profile_data: Profile information
            
        Returns:
            Updated profile information with embedding status
        """
        db = self.get_database()
        
        print("🔧 Preparing data for storage...")
        # Prepare data for storage (convert dates to datetime for MongoDB)
        prepared_data = prepare_profile_data_for_storage(profile_data)
        print("✅ Data prepared successfully")
        
        print("💾 Updating MongoDB...")
        # Update user profile
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "profile_data": prepared_data,
                    "profile_completed": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise ValueError("User not found or profile not updated")
        
        print("✅ Profile saved to MongoDB")
        
        # ============ GENERATE EMBEDDING ============
        from app.services.embedding_service import embedding_service
        
        embedding_generated = False
        embedding_error = None
        
        try:
            print("🧠 Generating profile embedding...")
            # Generate embedding from profile data
            embedding = await embedding_service.generate_profile_embedding(profile_data)
            
            # Store embedding in database
            await self.update_profile_embedding(user_id, embedding, embedding_service.model_name)
            
            embedding_generated = True
            print("✅ Embedding generated successfully")
        except Exception as e:
            # Log the error but don't fail the profile creation
            embedding_error = str(e)
            print(f"⚠️ Warning: Failed to generate embedding: {embedding_error}")
        # ============================================
        
        return {
            "message": "Profile completed successfully",
            "profile_completed": True,
            "embedding_generated": embedding_generated,
            "embedding_error": embedding_error if not embedding_generated else None
        }
    
    async def update_student_profile(
        self, 
        user_id: str, 
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update student profile and regenerate embedding
        
        Args:
            user_id: User ID
            profile_data: Updated profile information
            
        Returns:
            Success message with embedding status
        """
        db = self.get_database()
        
        # Prepare data for storage (convert dates to datetime for MongoDB)
        prepared_data = prepare_profile_data_for_storage(profile_data)
        
        # Update profile data
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "profile_data": prepared_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise ValueError("User not found or profile not updated")
        
        # ============ REGENERATE EMBEDDING ============
        from app.services.embedding_service import embedding_service
        
        embedding_generated = False
        embedding_error = None
        
        try:
            # Regenerate embedding from updated profile data
            embedding = await embedding_service.generate_profile_embedding(profile_data)
            
            # Update embedding in database
            await self.update_profile_embedding(user_id, embedding, embedding_service.model_name)
            
            embedding_generated = True
        except Exception as e:
            # Log the error but don't fail the profile update
            embedding_error = str(e)
            print(f"Warning: Failed to regenerate embedding: {embedding_error}")
        # ==============================================
        
        return {
            "message": "Profile updated successfully",
            "embedding_updated": embedding_generated,
            "embedding_error": embedding_error if not embedding_generated else None
        }
    
    # ============================================
    # NEW: ARRAY MANAGEMENT METHODS
    # ============================================
    
    async def add_to_array(
        self,
        user_id: str,
        field_name: str,
        item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add item to an array field (education, experience, projects, etc.)
        
        Args:
            user_id: User ID
            field_name: Array field name (e.g., "education", "experience")
            item: Item to add
            
        Returns:
            Success message
        """
        db = self.get_database()
        
        # Build the field path
        array_path = f"profile_data.{field_name}"
        
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$push": {array_path: item},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count == 0:
            raise ValueError("User not found or item not added")
        
        # Regenerate embedding after update
        await self._regenerate_embedding_after_update(user_id)
        
        return {
            "message": f"{field_name.capitalize()} added successfully",
            "success": True
        }
    
    async def update_array_item(
        self,
        user_id: str,
        field_name: str,
        index: int,
        updated_item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update item in an array by index
        
        Args:
            user_id: User ID
            field_name: Array field name
            index: Array index
            updated_item: Updated item data
            
        Returns:
            Success message
        """
        db = self.get_database()
        
        # Get current profile
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found")
        
        profile_data = user.get("profile_data", {})
        array_data = profile_data.get(field_name, [])
        
        if index < 0 or index >= len(array_data):
            raise ValueError(f"Invalid index {index} for {field_name}")
        
        # Update the specific item
        array_data[index] = updated_item
        profile_data[field_name] = array_data
        
        # Save updated profile
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "profile_data": profile_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise ValueError("Update failed")
        
        # Regenerate embedding
        await self._regenerate_embedding_after_update(user_id)
        
        return {
            "message": f"{field_name.capitalize()} updated successfully",
            "success": True
        }
    
    async def delete_array_item(
        self,
        user_id: str,
        field_name: str,
        index: int
    ) -> Dict[str, Any]:
        """
        Delete item from array by index
        
        Args:
            user_id: User ID
            field_name: Array field name
            index: Array index to delete
            
        Returns:
            Success message
        """
        db = self.get_database()
        
        # Get current profile
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise ValueError("User not found")
        
        profile_data = user.get("profile_data", {})
        array_data = profile_data.get(field_name, [])
        
        if index < 0 or index >= len(array_data):
            raise ValueError(f"Invalid index {index} for {field_name}")
        
        # Remove the item
        array_data.pop(index)
        profile_data[field_name] = array_data
        
        # Save updated profile
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "profile_data": profile_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise ValueError("Delete failed")
        
        # Regenerate embedding
        await self._regenerate_embedding_after_update(user_id)
        
        return {
            "message": f"{field_name.capitalize()} deleted successfully",
            "success": True
        }
    
    async def _regenerate_embedding_after_update(self, user_id: str):
        """
        Helper to regenerate embedding after profile updates
        Silently fails to not block the update operation
        """
        try:
            db = self.get_database()
            user = db.users.find_one({"_id": ObjectId(user_id)})
            
            if user and user.get("profile_data"):
                from app.services.embedding_service import embedding_service
                
                embedding = await embedding_service.generate_profile_embedding(
                    user["profile_data"]
                )
                
                await self.update_profile_embedding(
                    user_id,
                    embedding,
                    embedding_service.model_name
                )
        except Exception as e:
            print(f"Warning: Failed to regenerate embedding: {e}")
    
    # ============================================
    # EMBEDDING METHODS (Unchanged)
    # ============================================
    
    async def update_profile_embedding(
        self, 
        user_id: str, 
        embedding: list,
        model_name: str = "all-MiniLM-L6-v2"
    ) -> bool:
        """Update user's profile embedding"""
        db = self.get_database()
        
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "profile_embedding": embedding,
                    "embedding_generated_at": datetime.utcnow(),
                    "embedding_model": model_name
                }
            }
        )
        
        return result.modified_count > 0
    
    async def regenerate_profile_embedding(self, user_id: str) -> Dict[str, Any]:
        """Manually regenerate profile embedding for a user"""
        db = self.get_database()
        
        user = db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            raise ValueError("User not found")
        
        if not user.get("profile_completed") or not user.get("profile_data"):
            raise ValueError("Profile not completed. Cannot generate embedding.")
        
        profile_data = user.get("profile_data")
        
        from app.services.embedding_service import embedding_service
        
        try:
            embedding = await embedding_service.generate_profile_embedding(profile_data)
            
            success = await self.update_profile_embedding(user_id, embedding, embedding_service.model_name)
            
            if not success:
                raise Exception("Failed to update embedding in database")
            
            return {
                "message": "Embedding regenerated successfully",
                "success": True,
                "generated_at": datetime.utcnow(),
                "embedding_dimension": len(embedding),
                "model_used": embedding_service.model_name
            }
        except Exception as e:
            raise Exception(f"Failed to regenerate embedding: {str(e)}")


# Singleton instance
student_service = StudentService()
"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional

# Chat app schemas

class Chat(BaseModel):
    """
    Chats collection schema
    Collection name: "chat"
    """
    title: str = Field(..., description="Chat title shown in the sidebar")

class Message(BaseModel):
    """
    Messages collection schema
    Collection name: "message"
    """
    chat_id: str = Field(..., description="Reference to the chat this message belongs to")
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message text content")

# Example schemas (kept for reference; not used by the chat app directly)
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

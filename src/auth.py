# src/auth.py
"""Authentication manager."""

import bcrypt
from sqlmodel import Session, select
from src.db.models import User


class AuthManager:
    """Handle user authentication."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    @staticmethod
    def authenticate(session: Session, username: str, password: str) -> User | None:
        """Authenticate user."""
        stmt = select(User).where(User.username == username)
        user = session.exec(stmt).first()
        
        if user and AuthManager.verify_password(password, user.hashed_password):
            return user
        return None
    
    @staticmethod
    def create_user(session: Session, username: str, email: str, password: str) -> tuple:
        """Create new user. Returns (success, message)."""
        
        # Check if user exists
        stmt = select(User).where(User.username == username)
        if session.exec(stmt).first():
            return False, "Username already exists"
        
        stmt = select(User).where(User.email == email)
        if session.exec(stmt).first():
            return False, "Email already exists"
        
        # Create user
        hashed_pw = AuthManager.hash_password(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_pw,
        )
        session.add(user)
        session.commit()
        
        return True, "User created successfully"

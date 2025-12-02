from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import hashlib, re, secrets, smtplib, os
from email.mime.text import MIMEText
from typing import Annotated

from database import get_db
from models import User, ResetToken
from schemas import (
    UserSignup, UserLogin, PasswordResetRequest, PasswordReset, 
    Token, UserUpdate, UserResponse, AdminAddUser, ChangePassword
)

router = APIRouter()
security = HTTPBearer()

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def validate_email(email: str) -> bool:
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))

def validate_password(password: str) -> bool:
    return (
        len(password) >= 8
        and re.search(r'[A-Z]', password)
        and re.search(r'[a-z]', password)
        and re.search(r'\d', password)
        and re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
    )

def create_token(data: dict, minutes: int = 2500):
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    data.update({"exp": expire})
    return jwt.encode(data, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM"))

def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_EMAIL")
    msg["To"] = to_email

    server = smtplib.SMTP_SSL(os.getenv("SMTP_SERVER"), 465)
    server.login(os.getenv("SMTP_EMAIL"), os.getenv("SMTP_PASSWORD"))
    server.send_message(msg)
    server.quit()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                     db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, os.getenv("SECRET_KEY"),
                             algorithms=[os.getenv("ALGORITHM")])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email, User.status == "Active").first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def get_analyst_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "Analyst":
        raise HTTPException(status_code=403, detail="Analyst access required")
    return current_user

def create_default_admin():
    """Create default admin user"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        admin_email = "admin@gmail.com"
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        
        if not existing_admin:
            admin_user = User(
                full_name="Super Admin",
                email=admin_email,
                password_hash=hash_password("Admin@124"),
                role="Admin",
                status="Active"
            )
            db.add(admin_user)
            db.commit()
            print("Default admin user created")
        else:
            print("Admin user already exists")
    finally:
        db.close()

# Authentication Routes
@router.post("/signup")
def signup(user: UserSignup, db: Session = Depends(get_db)):
    if not validate_email(user.email):
        raise HTTPException(status_code=400, detail="Invalid email")
    if not validate_password(user.password):
        raise HTTPException(status_code=400, detail="Weak password")
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    db.add(User(full_name=user.full_name.strip(),
                email=user.email,
                password_hash=hash_password(user.password)))
    db.commit()
    return {"message": "User created successfully"}

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if db_user.status == "Inactive":
        raise HTTPException(status_code=403, detail="Account is inactive. Please contact administrator.")

    token = create_token({"sub": db_user.email})
    
    if db_user.role == "Admin":
        message = "Login successful! Redirecting to Admin Dashboard..."
    else:
        message = "Login successful! Redirecting to Analyst Dashboard..."
    
    return {
        "access_token": token, 
        "token_type": "bearer",
        "message": message,
        "role": db_user.role,
        "status": db_user.status
    }

@router.post("/reset-password-request")
def reset_password_request(req: PasswordResetRequest, db: Session = Depends(get_db)):
    if not validate_email(req.email):
        raise HTTPException(status_code=400, detail="Invalid email")

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.add(ResetToken(email=req.email, token=token, expires_at=expires))
    db.commit()

    reset_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"
    body = f"Click to reset your password: {reset_link}\n\nThis link expires in 1 hour."

    try:
        send_email(req.email, "Password Reset", body)
    except Exception as e:
        print("Email error:", e)

    return {"message": "Password reset email sent"}

@router.post("/reset-password")
def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    token_data = db.query(ResetToken).filter(
        ResetToken.token == data.token,
        ResetToken.expires_at > datetime.now(timezone.utc),
        ResetToken.used == False
    ).first()

    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if not validate_password(data.new_password):
        raise HTTPException(status_code=400, detail="Weak password")

    user = db.query(User).filter(User.email == token_data.email).first()
    user.password_hash = hash_password(data.new_password)
    token_data.used = True
    db.commit()

    return {"message": "Password reset successful"}

@router.get("/profile")
def profile(current_user: User = Depends(get_current_user)):
    return {"full_name": current_user.full_name, "email": current_user.email, "role": current_user.role, "status": current_user.status}

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully"}

@router.post("/change-password")
def change_password(password_data: ChangePassword, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    
    if not validate_password(password_data.new_password):
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters with uppercase, lowercase, number, and special character")
    
    if password_data.old_password == password_data.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from old password")
    
    current_user.password_hash = hash_password(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}

# User Management APIs (Admin Only)
@router.get("/users")
def get_all_users(admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.email != "admin@gmail.com").all()
    return users

@router.put("/users/{user_id}")
def update_user(user_id: int, user_data: UserUpdate, admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email == "admin@gmail.com":
        raise HTTPException(status_code=403, detail="Cannot edit super admin account")
    
    if user_data.email != user.email:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    if user_data.role not in ["Admin", "Analyst"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    if user_data.status not in ["Active", "Inactive"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    user.full_name = user_data.full_name.strip()
    user.email = user_data.email
    user.role = user_data.role
    user.status = user_data.status
    
    db.commit()
    return {"message": "User updated successfully"}

@router.post("/admin/add-user")
def admin_add_user(user_data: AdminAddUser, admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    if not validate_email(user_data.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    
    if user_data.role not in ["Admin", "Analyst"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be Admin or Analyst")
    if user_data.status not in ["Active", "Inactive"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be Active or Inactive")
    
    default_password = os.getenv("DEFAULT_USER_PASSWORD")
    
    new_user = User(
        full_name=user_data.full_name.strip(),
        email=user_data.email,
        password_hash=hash_password(default_password),
        role=user_data.role,
        status=user_data.status
    )
    
    db.add(new_user)
    db.commit()
    
    return {
        "message": f"User '{user_data.full_name}' created successfully",
        "default_password": default_password,
    }

@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.email == "admin@gmail.com":
        raise HTTPException(status_code=403, detail="Cannot delete super admin account")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
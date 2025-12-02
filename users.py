from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import hashlib, re, secrets, smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Annotated
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
try:
    from main import (
        SECRET_KEY, ALGORITHM, SMTP_EMAIL, SMTP_PASSWORD, 
        SMTP_SERVER, FRONTEND_URL, DEFAULT_USER_PASSWORD
    )
except ImportError:
    # Fallback values if import fails
    SECRET_KEY = "my-super-secret-jwt-key-2024-auth-system"
    ALGORITHM = "HS256"
    SMTP_EMAIL = "adeelfateh33@gmail.com"
    SMTP_PASSWORD = "ptnr vhac mlsl qrru"
    SMTP_SERVER = "smtp.gmail.com"
    FRONTEND_URL = "https://obsecureiq-frontend-v1.vercel.app"
    DEFAULT_USER_PASSWORD = "Test@123"

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
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def send_email(to_email: str, subject: str, body: str, html_body: str = None):
    if html_body:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email
        
        text_part = MIMEText(body, "plain")
        html_part = MIMEText(html_body, "html")
        
        msg.attach(text_part)
        msg.attach(html_part)
    else:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email

    server = smtplib.SMTP_SSL(SMTP_SERVER, 465)
    server.login(SMTP_EMAIL, SMTP_PASSWORD)
    server.send_message(msg)
    server.quit()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                     db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY,
                             algorithms=[ALGORITHM])
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

    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    
    # Plain text version
    text_body = f"Click to reset your password: {reset_link}\n\nThis link expires in 1 hour."
    
    # HTML version
    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Password Reset - ObscureIQ</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 0; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #010F3C 0%, #1a2b5c 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <div style="width: 60px; height: 60px; background-color: rgba(255,255,255,0.1); border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px;">
                    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14,2 14,8 20,8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10,9 9,9 8,9"></polyline>
                    </svg>
                </div>
                <h1 style="color: white; margin: 0; font-size: 28px; font-weight: bold;">ObscureIQ</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 10px 0 0 0; font-size: 16px;">Password Reset Request</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 40px 30px;">
                <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 24px;">Reset Your Password</h2>
                <p style="color: #666666; line-height: 1.6; margin: 0 0 25px 0; font-size: 16px;">
                    We received a request to reset your password. Click the button below to create a new password for your account.
                </p>
                
                <!-- Reset Button -->
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{reset_link}" style="display: inline-block; background: linear-gradient(135deg, #010F3C 0%, #1a2b5c 100%); color: white; text-decoration: none; padding: 15px 35px; border-radius: 8px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 15px rgba(1, 15, 60, 0.3); transition: all 0.3s ease;">Reset Password</a>
                </div>
                
                <div style="background-color: #f8f9fa; border-left: 4px solid #010F3C; padding: 20px; margin: 30px 0; border-radius: 4px;">
                    <p style="color: #666666; margin: 0; font-size: 14px; line-height: 1.5;">
                        <strong>Security Notice:</strong> This link will expire in <strong>1 hour</strong> for your security. If you didn't request this password reset, please ignore this email.
                    </p>
                </div>
                
                <p style="color: #666666; line-height: 1.6; margin: 25px 0 0 0; font-size: 14px;">
                    If the button doesn't work, you can copy and paste this link into your browser:
                </p>
                <p style="color: #010F3C; word-break: break-all; font-size: 14px; margin: 10px 0;">
                    {reset_link}
                </p>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 30px; text-align: center; border-radius: 0 0 8px 8px; border-top: 1px solid #e9ecef;">
                <p style="color: #999999; margin: 0; font-size: 14px;">
                    This email was sent by ObscureIQ. If you have any questions, please contact our support team.
                </p>
                <p style="color: #999999; margin: 10px 0 0 0; font-size: 12px;">
                    © 2024 ObscureIQ. All rights reserved.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        send_email(req.email, "Reset Your Password - ObscureIQ", text_body, html_body)
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
    
    default_password = DEFAULT_USER_PASSWORD
    
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

# FastAPI Authentication System

A complete authentication system with FastAPI including signup, login, password reset, and email functionality.

## Features

- User signup with username, email, password, and confirm password
- Login with username or email
- JWT token-based authentication
- Password reset via email
- SMTP email integration
- SQLite database for user storage
- Secure password hashing with bcrypt

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
   - Set your `SECRET_KEY` (generate a secure random key)
   - Configure SMTP settings for your email provider
   - Set `FRONTEND_URL` for password reset links

3. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

- `POST /signup` - Create new user account
- `POST /login` - User login (returns JWT token)
- `POST /reset-password-request` - Request password reset email
- `POST /reset-password` - Reset password with token
- `GET /profile` - Get current user profile (requires authentication)
- `GET /` - Root endpoint

## Authentication

Include the JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## Database

The application uses SQLite database (`auth.db`) which is created automatically on first run.
# Authentication Service

Handles user authentication, authorization, and session management.

## Features
- **Login**: Email/phone + password authentication
- **OTP**: SMS and email-based one-time passwords
- **MFA**: Multi-factor authentication for officers and admins
- **Session Management**: JWT-based sessions with refresh tokens

## Security
- Passwords hashed with bcrypt (12 rounds)
- JWT tokens with short expiry (15 min access, 7 day refresh)
- Account lockout after 5 failed attempts
- Session invalidation on password change

## Port: 8001

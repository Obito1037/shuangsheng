# EchoLearn Auth Design

User authentication includes:

- Register with email/password.
- Password stored with PBKDF2-SHA256 and random salt.
- Login issues access token and refresh token.
- Access token is HMAC-signed and short lived.
- Refresh token is random, stored only as SHA-256 hash, and revocable.
- Logout revokes refresh token.
- Protected API routes use `get_current_user`.

Never log plaintext passwords, refresh tokens, Authorization headers, or provider AppKey values.


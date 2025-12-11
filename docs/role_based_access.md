# Role Based Access

- JWT token should include 'role' claim: 'user' or 'admin'.
- Use `backend/auth.py`'s `require_role` helper to decorate endpoints needing admin privileges.
- Example JWT payload: { "sub": "user@example.com", "role": "admin", "exp": <timestamp> }

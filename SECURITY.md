# Security Notes

## Default credentials
On first install, a default admin account is created:
- Username: `admin`
- Password: `admin123`

The setup wizard runs on first launch and **requires** you to change this password
before the app becomes usable. The default credentials are only a bootstrapping
mechanism and should never be used in production.

## Data storage
All school data is stored locally in `~/.gradevault/gradevault.db` on the user's
machine. No data is sent to any server. The application works fully offline.

## Passwords
All passwords are hashed using bcrypt before being stored in the database.
Plain-text passwords are never stored or logged.

## Reporting issues
If you find a security issue, please open a private GitHub issue or contact
the maintainer directly.

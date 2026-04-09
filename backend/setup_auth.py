"""
Run this script ONCE locally to authenticate with Gmail.
It will open a browser window for you to log in as andrew@mindaptive.ai.
After completing the flow, a token.json is saved to credentials/token.json.

Usage:
    cd backend
    pip install -r requirements.txt
    python setup_auth.py

Then copy credentials/token.json to your DigitalOcean droplet.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.gmail.client import GmailClient

if __name__ == "__main__":
    print("Starting Gmail OAuth flow...")
    print("A browser window will open — log in as andrew@mindaptive.ai\n")
    client = GmailClient()
    client.authenticate()
    history_id = client.get_current_history_id()
    print(f"\nAuthentication successful!")
    print(f"Current history ID: {history_id}")
    print(f"Token saved to: credentials/token.json")
    print("\nNext steps:")
    print("  1. Copy credentials/token.json to your DigitalOcean droplet")
    print("  2. Run: docker-compose up -d")

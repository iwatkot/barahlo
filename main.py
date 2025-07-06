#!/usr/bin/env python3
"""
Telegram Chat Parser - Monitors keywords and forwards matching messages

USAGE:
1. Copy .env.example to .env and fill in your credentials
2. Run once for authentication: python main.py
   (uncomment test_telegram_connection)
3. Run for hourly monitoring: python main.py (default mode)

The script will:
- Check NSbaraholka every hour for new messages
- Search for keywords from your .env file
- Forward matching messages to your specified user
- Track forwarded messages to prevent duplicates
"""

import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from datetime import datetime, timedelta, timezone
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

# Keywords to search for in messages
KEYWORDS = os.getenv("KEYWORDS", "").split(",")

# Your username to forward messages to
FORWARD_TO_USERNAME = os.getenv("FORWARD_TO_USERNAME")

# File to store forwarded message IDs
FORWARDED_MESSAGES_FILE = "forwarded_messages.json"


def load_forwarded_messages():
    """Load the list of already forwarded message IDs"""
    if os.path.exists(FORWARDED_MESSAGES_FILE):
        try:
            with open(FORWARDED_MESSAGES_FILE, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError):
            return set()
    return set()


def save_forwarded_messages(forwarded_ids):
    """Save the list of forwarded message IDs to file"""
    with open(FORWARDED_MESSAGES_FILE, "w") as f:
        json.dump(list(forwarded_ids), f)


def add_forwarded_message(forwarded_ids, message_id):
    """Add a message ID to the forwarded list and save to file"""
    forwarded_ids.add(message_id)
    save_forwarded_messages(forwarded_ids)


async def get_chat_messages_by_time(chat_username, hours_back=6):
    """Get messages from a specific chat from the last N hours and forward matching ones"""

    print(f"🔄 Getting messages from {chat_username} from last {hours_back} hours...")
    print(f"🔍 Looking for keywords: {', '.join(KEYWORDS)}")

    # Calculate the cutoff time
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    print(f"📅 Getting messages since: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Create client
    client = TelegramClient("test_session", API_ID, API_HASH)

    # Load already forwarded message IDs
    forwarded_message_ids = load_forwarded_messages()
    print(f"📝 Loaded {len(forwarded_message_ids)} previously forwarded message IDs")

    try:
        # Connect to Telegram
        await client.connect()

        # Check if we're logged in
        if not await client.is_user_authorized():
            print("❌ Not logged in! Run the script with authentication first.")
            return

        # Get chat entity
        try:
            chat = await client.get_entity(chat_username)
            print(f"✅ Found chat: {chat.title}")
        except Exception as e:
            print(f"❌ Could not find chat '{chat_username}': {e}")
            return

        # Get the target user to forward messages to
        try:
            target_user = await client.get_entity(FORWARD_TO_USERNAME)
            print(f"✅ Found target user: {target_user.first_name}")
        except Exception as e:
            print(f"❌ Could not find user '{FORWARD_TO_USERNAME}': {e}")
            return

        # Get messages
        messages = []
        matching_messages = []
        skipped_messages = 0

        async for message in client.iter_messages(chat):
            # Stop if we've gone too far back
            if message.date < cutoff_time:
                break

            if message.text:  # Only get text messages for now
                message_data = {
                    "id": message.id,
                    "date": message.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "text": message.text,
                    "sender_name": "Unknown",
                }

                # Try to get sender name
                if message.sender:
                    if hasattr(message.sender, "first_name"):
                        name_parts = [message.sender.first_name or ""]
                        if message.sender.last_name:
                            name_parts.append(message.sender.last_name)
                        message_data["sender_name"] = " ".join(name_parts).strip()
                    elif hasattr(message.sender, "title"):
                        message_data["sender_name"] = message.sender.title

                messages.append(message_data)

                # Check if message contains any of our keywords
                message_text_lower = message.text.lower()
                matching_keywords = []
                for keyword in KEYWORDS:
                    if keyword.lower() in message_text_lower:
                        matching_keywords.append(keyword)

                if matching_keywords:
                    # Check if we already forwarded this message
                    if message.id in forwarded_message_ids:
                        print(f"⏩ SKIP! Message {message.id} already forwarded")
                        skipped_messages += 1
                        continue

                    message_data["matching_keywords"] = matching_keywords
                    matching_messages.append(message_data)
                    print(f"🎯 MATCH! Found keywords {matching_keywords}")

                    # Forward the original message directly
                    try:
                        # Calculate time difference
                        now = datetime.now(timezone.utc)
                        time_diff = now - message.date

                        # Format relative time
                        if time_diff.days > 0:
                            time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                        elif time_diff.seconds >= 3600:
                            hours = time_diff.seconds // 3600
                            time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
                        elif time_diff.seconds >= 60:
                            minutes = time_diff.seconds // 60
                            time_ago = (
                                f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                            )
                        else:
                            time_ago = "just now"

                        # Send a header message first
                        header_text = f"🔥 Keyword match: {', '.join(matching_keywords)} ({time_ago})"
                        await client.send_message(target_user, header_text)

                        # Forward the original message
                        await client.forward_messages(target_user, message)
                        print(f"✅ Forwarded to @{FORWARD_TO_USERNAME}")

                        # Track the forwarded message ID
                        add_forwarded_message(forwarded_message_ids, message.id)

                    except Exception as e:
                        print(f"❌ Failed to forward: {e}")

        print(f"📨 Processed {len(messages)} messages from last {hours_back} hours")
        print(f"🎯 Found {len(matching_messages)} new matching messages")
        if skipped_messages > 0:
            print(f"⏩ Skipped {skipped_messages} already forwarded messages")

        if not matching_messages and skipped_messages == 0:
            print(
                "😔 No messages found with your keywords in the specified time period"
            )

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await client.disconnect()


async def test_telegram_connection():
    """Test if we can connect to Telegram with our credentials"""

    # Check if credentials are set
    if not API_ID or not API_HASH or not PHONE_NUMBER:
        print("❌ ERROR: You need to set up your Telegram API credentials!")
        print()
        print("📋 Instructions:")
        print("1. Go to https://my.telegram.org/auth")
        print("2. Log in with your phone number")
        print("3. Go to 'API Development tools'")
        print("4. Create a new application (any name/description)")
        print("5. Copy the API ID and API Hash")
        print("6. Update the variables in this script")
        print()
        print("Then run the script again!")
        return

    print("🔄 Testing Telegram connection...")
    print(f"Using phone number: {PHONE_NUMBER}")

    # Create client
    client = TelegramClient("test_session", API_ID, API_HASH)

    try:
        # Connect to Telegram
        print("📡 Connecting to Telegram...")
        await client.connect()

        # Check if we're already logged in
        if await client.is_user_authorized():
            print("✅ Already logged in!")

            # Get some basic info about the account
            me = await client.get_me()
            print(f"👤 Logged in as: {me.first_name} {me.last_name or ''}")
            print(f"📞 Phone: {me.phone}")

        else:
            print("🔐 Authentication required...")

            # Request verification code
            print("📲 Sending verification code to your phone...")
            await client.send_code_request(PHONE_NUMBER)

            # Get code from user
            code = input("📱 Enter the verification code from Telegram: ")

            try:
                # Sign in with the code
                await client.sign_in(PHONE_NUMBER, code)
                print("✅ Authentication successful!")

            except SessionPasswordNeededError:
                # Handle 2FA
                print("🔒 Two-factor authentication is enabled")
                password = input("🔑 Enter your 2FA password: ")
                await client.sign_in(password=password)
                print("✅ Authentication successful!")

            # Get account info
            me = await client.get_me()
            print(f"👤 Logged in as: {me.first_name} {me.last_name or ''}")
            print(f"📞 Phone: {me.phone}")

        print()
        print("🎉 Success! Your credentials work fine.")
        print("🚀 You're ready to parse Telegram chats!")

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("💡 Common issues:")
        print("- Wrong API_ID or API_HASH")
        print("- Wrong phone number format (should include country code)")
        print("- Network connection issues")

    finally:
        # Always disconnect
        await client.disconnect()
        print("🔌 Disconnected from Telegram")


async def run_scheduler():
    """Run the chat monitoring every hour"""
    print("🕐 Starting hourly chat monitoring...")
    print("🔄 Will check NSbaraholka every hour for new messages")
    print("⏹️  Press Ctrl+C to stop")

    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n🕐 [{current_time}] Running scheduled check...")

            # Run the chat parsing
            await get_chat_messages_by_time("NSbaraholka", 1)  # Last hour

            print("💤 Sleeping for 1 hour...")
            await asyncio.sleep(3600)  # Sleep for 1 hour (3600 seconds)

        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in scheduler: {e}")
            print("💤 Sleeping for 10 minutes...")
            await asyncio.sleep(600)


if __name__ == "__main__":
    # First time setup: uncomment to test connection and authenticate
    asyncio.run(test_telegram_connection())

    # Run the scheduler (checks every hour)
    asyncio.run(run_scheduler())

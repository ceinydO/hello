import asyncio
from pyrogram import Client, filters
from pyrogram.errors import PeerIdInvalid, SlowmodeWait
import configparser
import os
import sys
from datetime import datetime
import shutil

# Global variables
stop_spamming = False  # For /skurwysyn to control spam loop

# Helper functions
def get_user_directory(user_id):
    """Get or create the user's directory."""
    user_dir = str(user_id)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

def load_api_ini():
    """Load all api.ini files to validate credentials."""
    for folder in os.listdir():
        if os.path.isdir(folder):
            config_path = os.path.join(folder, "api.ini")
            if os.path.isfile(config_path):
                config = configparser.ConfigParser()
                config.read(config_path, encoding="utf-8")
                yield folder, config

def check_license(license_date):
    """Check if the license is still valid."""
    if not license_date:
        return False
    current_date = datetime.now()
    license_expiry = datetime.strptime(license_date, "%d.%m.%Y")
    return current_date <= license_expiry

def authenticate_user():
    """Authenticate or register a new user."""
    while True:
        password = input("Enter your password: ").strip()
        for folder, config in load_api_ini():
            if "API" in config and config["API"].get("Password") == password:
                license_date = config["API"].get("License") or config["API"].get("license_date")
                if check_license(license_date):
                    print(f"User found: {folder}")
                    return folder, config["API"]["API_ID"], config["API"]["API_HASH"]
                else:
                    print(f"License for user ID {folder} has expired. Contact support.")
                    exit()

        print("No matching user found. Starting registration.")
        user_id = input("Enter new user ID to register: ").strip()
        if os.path.exists(user_id):
            print("User ID already exists. Restarting program.")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        os.makedirs(user_id)
        api_id = input("Enter new API ID: ").strip()
        api_hash = input("Enter new API Hash: ").strip()
        password = input("Set a password (8 characters): ").strip()
        while len(password) < 8 or any(config["API"].get("Password") == password for _, config in load_api_ini()):
            print("Invalid or duplicate password. Try again.")
            password = input("Set a password (8 characters): ").strip()
        license_date = ""  # Admin sets this manually later
        with open(os.path.join(user_id, "api.ini"), "w", encoding="utf-8") as file:
            config = configparser.ConfigParser()
            config["API"] = {"API_ID": api_id, "API_HASH": api_hash, "Password": password, "License": license_date}
            config.write(file)
        print("Registration complete. Restarting.")
        os.execv(sys.executable, [sys.executable] + sys.argv)

# Authenticate and initialize client
user_id, api_id, api_hash = authenticate_user()

# Initialize the Pyrogram client dynamically for the authenticated user
app = Client(name=user_id, api_id=int(api_id), api_hash=api_hash)

# Commands
@app.on_message(filters.command("groups"))
async def show_groups(client, message):
    user_dir = get_user_directory(user_id)
    config_path = os.path.join(user_dir, "config.ini")
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    
    # Validate group IDs and filter out invalid ones
    groups = config["Groups"] if "Groups" in config else {}
    valid_groups = {}

    # Check if group IDs are valid
    for group_id, group_name in groups.items():
        try:
            # Attempt to fetch the group (just to validate if it's accessible)
            await client.get_chat(int(group_id))
            valid_groups[group_id] = group_name
        except (PeerIdInvalid, ValueError) as e:
            print(f"Invalid group ID {group_id}. Error: {e}. Skipping...")

    if valid_groups:
        group_info = "\n".join([f"ID: {gid}, Name: {name}" for gid, name in valid_groups.items()])
        await message.reply_text(group_info)
    else:
        await message.reply_text("No valid groups found.")

@app.on_message(filters.command("cwel"))
async def save_group(client, message):
    chat_id = str(message.chat.id)
    chat_title = message.chat.title or "Unnamed Group"
    user_dir = get_user_directory(user_id)
    config_path = os.path.join(user_dir, "config.ini")
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    
    if "Groups" not in config:
        config["Groups"] = {}
    if chat_id not in config["Groups"]:
        config["Groups"][chat_id] = chat_title
        with open(config_path, "w", encoding="utf-8") as file:
            config.write(file)

    print(f"Group saved: {chat_title}")
    await message.delete()

@app.on_message(filters.command("skurwysyn") & filters.reply)
async def start_spamming(client, message):
    global stop_spamming
    stop_spamming = False
    user_dir = get_user_directory(user_id)
    config_path = os.path.join(user_dir, "config.ini")
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    
    # Validate and filter out invalid group IDs
    group_ids = config["Groups"] if "Groups" in config else {}
    valid_groups = {}

    for group_id, group_name in group_ids.items():
        try:
            # Check if the group is accessible and valid
            group_chat = await client.get_chat(int(group_id))
            valid_groups[group_id] = group_name
        except PeerIdInvalid as e:
            print(f"Invalid peer ID: {group_id}. Skipping. Error: {e}")
        except ValueError as e:
            print(f"ValueError occurred with group {group_id}. Skipping. Error: {e}")
        except Exception as e:
            print(f"Unexpected error occurred with group {group_id}. Skipping. Error: {e}")

    if not valid_groups:
        print("No valid groups found. Cannot start spamming.")
        await message.reply_text("No valid groups to spam.")
        return
    
    print(f"Valid groups: {valid_groups}")

    spam_message = message.reply_to_message
    if not spam_message:
        print("Reply to a message to spam.")
        await message.delete()
        return

    print("Spamming started. Use /analiaorali to stop.")
    await message.delete()

    while not stop_spamming:
        for group_id, group_name in valid_groups.items():
            if stop_spamming:
                break
            try:
                # Now that we've validated the group ID, proceed with forwarding the message
                await spam_message.forward(int(group_id))
                print(f"Message posted to group {group_name} (ID: {group_id}).")

                for remaining in range(20, 0, -1):
                    if stop_spamming:
                        break
                    print(f"Next message in: {remaining} seconds", end="\r")
                    await asyncio.sleep(1)

            except SlowmodeWait as e:
                print(f"Slowmode in group {group_name} (ID: {group_id}) is active. Skipping. Error: {e}")
                continue

        if not stop_spamming:
            print("\nCompleted one cycle of spamming. Starting next loop...")
        else:
            print("\nSpamming stopped.")


@app.on_message(filters.command("analiaorali"))
async def stop_spam(client, message):
    global stop_spamming
    stop_spamming = True
    await message.reply_text("Spam stopped.")

@app.on_message(filters.command("chiefkiev"))
async def send_custom_message(client, message):
    await message.reply_text("Custom message: Glory to the heroes!")

@app.on_message(filters.command("misiek1312"))
async def delete_user_directory(client, message):
    """Delete the entire user directory."""
    user_dir = get_user_directory(user_id)
    if os.path.exists(user_dir):
        try:
            shutil.rmtree(user_dir)
            await message.reply_text("Your directory has been deleted.")
        except Exception as e:
            await message.reply_text(f"An error occurred while deleting the directory: {e}")
    else:
        await message.reply_text("No user directory found.")

@app.on_message(filters.command("mordoczlowie"))
async def send_mp3(client, message):
    """Send the specific MP3 file from the user's directory."""
    user_dir = get_user_directory(user_id)
    mp3_file = os.path.join(user_dir, "ODYNIEC +MORDOCZLOWIE _-!AHOHBALLADA.mp3")

    if os.path.exists(mp3_file):
        await message.reply_audio(audio=mp3_file)
        print(f"Sent: {mp3_file}")
    else:
        await message.reply_text("The MP3 file 'ODYNIEC +MORDOCZLOWIE _-!AHOHBALLADA' was not found in your directory.")
        print(f"File not found: {mp3_file}")

# Start the client
app.run()

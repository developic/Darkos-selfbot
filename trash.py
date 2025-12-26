import json
import os

# Folder path
folder = "data"

# Make sure folder exists
if not os.path.exists(folder):
    os.makedirs(folder)

# Function to create conversation
def create_conversation(turns=10):
    convo = []
    bot = 1
    for _ in range(turns):
        convo.append({"bot": bot, "msg": ""})
        bot = 2 if bot == 1 else 1
    return convo

# Generate conversation
conversation = create_conversation(100)

# File path
file_path = os.path.join(folder, "conversation.json")

# Write JSON to file
with open(file_path, "w") as f:
    json.dump(conversation, f, indent=2)

print(f"Conversation JSON created at: {file_path}")

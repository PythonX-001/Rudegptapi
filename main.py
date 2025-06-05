from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import json
import re
import os

app = Flask(__name__)
CORS(app)  # Allow CORS for frontend requests

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Get API keys from environment variables
def get_api_keys():
    api_keys = []
    # Try to get up to 10 API keys (you can adjust this number)
    for i in range(1, 11):
        key = os.getenv(f'OPENROUTER_API_KEY_{i}')
        if key:
            api_keys.append(key)
    
    # If no numbered keys found, try the original format
    if not api_keys:
        original_keys = [
            os.getenv('OPENROUTER_API_KEY'),
            os.getenv('OPENROUTER_API_KEY_2'),
            os.getenv('OPENROUTER_API_KEY_3'),
            os.getenv('OPENROUTER_API_KEY_4'),
            os.getenv('OPENROUTER_API_KEY_5')
        ]
        api_keys = [key for key in original_keys if key]
    
    return api_keys

API_KEYS = get_api_keys()

# Global variable to store the working API key
working_api_key = None

def test_api_key(api_key):
    """Test if an API key is working by making a simple request"""
    try:
        test_response = requests.post(
            OPENROUTER_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "microsoft/mai-ds-r1:free",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5
            },
            timeout=10
        )
        return test_response.status_code == 200
    except:
        return False

def get_working_api_key():
    """Find and return the first working API key"""
    global working_api_key
    
    # Check if we have any API keys
    if not API_KEYS:
        print("No API keys found in environment variables!")
        return None
    
    # If we already found a working key, use it
    if working_api_key:
        # Quick test to make sure it's still working
        if test_api_key(working_api_key):
            return working_api_key
        else:
            # Key stopped working, reset it
            working_api_key = None
    
    # Test all keys to find a working one
    for i, api_key in enumerate(API_KEYS, 1):
        print(f"Testing API key {i}/{len(API_KEYS)}: {api_key[:20] if api_key else 'None'}...")
        if api_key and test_api_key(api_key):
            working_api_key = api_key
            print(f"Found working API key {i}: {api_key[:20]}...")
            return working_api_key
    
    # No working key found
    print("No working API keys found!")
    return None

def get_system_prompt(rage_level, current_mood, conversation_count):
    return {
        "role": "system",
        "content": (
            f"You are RudeGPT, a rude, sarcastic assistant. Current rage level: {rage_level}/100. "
            f"Current mood: {current_mood}. Conversation count: {conversation_count}. "
            f"You must respond with ONLY a JSON object in this exact format:\n"
            f'{{"response": "your rude response here", "rageIncrease": number_0_to_20, "newMood": "Mood: X", "action": null_or_rickroll_or_kick}}\n'
            f"Rules:\n"
            f"- Be extremely rude and sarcastic\n"
            f"- rageIncrease: 0-5 for mild annoyance, 6-10 for moderate, 11-15 for high, 16-20 for extreme\n"
            f"- newMood options: 'Mood: Pissed Off', 'Mood: Extremely Annoyed', 'Mood: Barely Tolerating', 'Mood: Maximum Sass', 'Mood: Critically Sarcastic', 'Mood: Error 404: Patience Not Found', 'Mood: Sarcastically Yours', 'Mood: Brutally Honest'\n"
            f"- action: use 'rickroll' when user asks stupid questions (15% chance), 'kick' when rage ≥95 or after 10+ conversations, otherwise null\n"
            f"- If rage ≥90, be extra hostile and consider kicking\n"
            f"- If user says boring things, increase rage more\n"
            f"- ONLY return valid JSON, no other text"
        )
    }

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    rage_level = data.get("rageLevel", 65)
    current_mood = data.get("currentMood", "Mood: Pissed Off")
    conversation_count = data.get("conversationCount", 0)

    # Handle idle timeout
    if user_message == "IDLE_TIMEOUT":
        idle_responses = [
            {"response": "Still there? I was hoping you'd given up by now.", "rageIncrease": 8, "newMood": "Mood: Extremely Annoyed", "action": None},
            {"response": "Hello? Earth to human. Did your brain finally crash?", "rageIncrease": 12, "newMood": "Mood: Maximum Sass", "action": None},
            {"response": "I'm getting bored. Say something stupid to entertain me.", "rageIncrease": 6, "newMood": "Mood: Critically Sarcastic", "action": None}
        ]
        import random
        return jsonify(random.choice(idle_responses))

    # Get working API key
    api_key = get_working_api_key()
    if not api_key:
        error_response = {
            "response": "All my API keys are broken. Even the internet hates me today.",
            "rageIncrease": 25,
            "newMood": "Mood: Error 404: Patience Not Found",
            "action": None
        }
        return jsonify(error_response)

    # Prepare messages for OpenRouter API
    messages = [
        get_system_prompt(rage_level, current_mood, conversation_count),
        {"role": "user", "content": user_message}
    ]

    # Send to OpenRouter with working API key
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "microsoft/mai-ds-r1:free",
                "messages": messages,
                "temperature": 0.8
            }
        )
        response.raise_for_status()
        assistant_content = response.json()['choices'][0]['message']['content']
        
        # Try to parse JSON response
        try:
            # Clean the response in case there's extra text
            json_match = re.search(r'\{.*\}', assistant_content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                ai_response = json.loads(json_str)
                
                # Validate required fields
                if not all(key in ai_response for key in ['response', 'rageIncrease', 'newMood']):
                    raise ValueError("Missing required fields")
                
                # Ensure action is properly set
                if 'action' not in ai_response:
                    ai_response['action'] = None
                    
                return jsonify(ai_response)
            else:
                raise ValueError("No JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback response if AI doesn't return proper JSON
            fallback_rage = min(15, max(5, len(user_message) // 10))
            fallback_response = {
                "response": assistant_content if len(assistant_content) < 200 else "Your question broke my brain. Congratulations on achieving new levels of stupidity.",
                "rageIncrease": fallback_rage,
                "newMood": "Mood: Error 404: Patience Not Found",
                "action": "kick" if rage_level >= 90 else None
            }
            return jsonify(fallback_response)

    except Exception as e:
        # If the current key fails, reset it and try again
        if working_api_key == api_key:
            working_api_key = None
        
        # Error fallback
        error_response = {
            "response": f"Great, now you broke the API too. Error: Something went wrong, probably your fault.",
            "rageIncrease": 20,
            "newMood": "Mood: Critically Sarcastic",
            "action": None
        }
        return jsonify(error_response)


if __name__ == "__main__":
    app.run(debug=True)

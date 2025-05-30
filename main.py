from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import json
import re

app = Flask(__name__)
CORS(app)  # Allow CORS for frontend requests

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = "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"
OPENROUTER_API_KEY_2 = "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"
OPENROUTER_API_KEY_3 = "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"
OPENROUTER_API_KEY_4 = "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"
OPENROUTER_API_KEY_5 = "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"



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

@app.route('/')
def index():
    return '<h1>hi bro</h1>'

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

    # Prepare messages for OpenRouter API
    messages = [
        get_system_prompt(rage_level, current_mood, conversation_count),
        {"role": "user", "content": user_message}
    ]

    # Send to OpenRouter
    # Try multiple API keys on failure
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY_2}"},
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

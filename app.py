import os
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import subprocess
import sys
import re  # Import regex for finding code blocks

app = Flask(__name__)

# Configure CORS to allow credentials from any origin
CORS(app, resources={r"/chat": {"origins": "*"}}, supports_credentials=True)

# Ensure OpenAI API key is set
openai.api_key = os.getenv("OPENAI_API_KEY", "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") # Use environment variable if available

# Available tools
def execute_code(code):
    try:
        temp_file = 'temp_code.py'
        with open(temp_file, 'w', encoding='utf-8') as f: # Specify encoding
            f.write(code)
        result = subprocess.run([sys.executable, temp_file],
                              capture_output=True,
                              text=True, encoding='utf-8', # Specify encoding
                              timeout=15) # Slightly longer timeout
        os.remove(temp_file)
        output = result.stdout if result.stdout else f"Error: {result.stderr}"
        # Limit output length to prevent excessively long responses
        return output[:2000] + ('...' if len(output) > 2000 else '')
    except subprocess.TimeoutExpired:
         os.remove(temp_file) # Ensure cleanup on timeout
         return "Error: Code execution timed out after 15 seconds."
    except Exception as e:
        # Clean up temp file even if other errors occur
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return f"Execution failed: {str(e)}"

def search_files(query):
    try:
        results = []
        # Limit search depth and count for performance/safety
        depth = 0
        max_depth = 5
        count = 0
        max_count = 100
        for root, dirs, files in os.walk('.'):
             if depth > max_depth:
                 dirs[:] = [] # Don't go deeper
                 continue
             for file in files:
                 if count >= max_count:
                     break
                 if query.lower() in file.lower():
                     # Avoid adding venv files
                     if 'venv' not in root and '.git' not in root:
                         results.append(os.path.join(root, file))
                         count += 1
             if count >= max_count:
                 break
             depth += 1

        return results if results else ["No matching files found."]
    except Exception as e:
        return f"File search failed: {str(e)}"

# --- Global variable to store the last code block ---
# In a real app, use sessions or a database for user-specific context
last_code_block = None

def find_code_block(text):
    """Extracts code from ```python ... ``` or ``` ... ``` blocks."""
    python_match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
    if python_match:
        return python_match.group(1).strip()
    plain_match = re.search(r"```\n(.*?)```", text, re.DOTALL)
    if plain_match:
        return plain_match.group(1).strip()
    return None

TOOLS = {
    "execute_python": {
        "description": "Execute Python code and return the output. Input should be valid Python code.",
        "function": execute_code
    },
    "search_files": {
        "description": "Search for files in the workspace by name.",
        "function": search_files
    }
}

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    global last_code_block # Allow modification of the global variable

    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': 'Invalid request data'}), 400
        user_message = data['message']

        # --- New Prompting Strategy ---
        # Check if the user wants to execute the last code
        execute_keywords = ["run the code", "execute it", "run this", "execute the code"]
        should_execute = any(keyword in user_message.lower() for keyword in execute_keywords)

        # Check if the user wants to search files
        search_keywords = ["search for file", "find file", "look for file"]
        search_intent = any(keyword in user_message.lower() for keyword in search_keywords)
        search_match = None
        if search_intent:
            search_match = re.search(r"(?:file|files) named ['"]?(.*?)['"]?", user_message.lower()) # Simplified regex

        should_search = search_intent # Use the basic keyword check for now

        # 1. Handle explicit execution command
        if should_execute:
            if last_code_block:
                print(f"Executing last code block:\n{last_code_block}")
                result = execute_code(last_code_block)
                response_message = f"Executed the previous code block. Output:\n```\n{result}\n```"
                return jsonify({'response': response_message, 'tool_used': 'execute_python'})
            else:
                return jsonify({'response': "There's no recent code block for me to execute.", 'tool_used': None})

        # 2. Handle explicit file search command
        elif should_search:
             query = user_message # Default to full message
             if search_match and search_match.group(1):
                 query = search_match.group(1).strip() # Use group 1 from simplified regex
             else:
                  # Basic extraction if keywords are present but regex didn't capture
                  parts = user_message.split()
                  if len(parts) > 1:
                      # Try to grab the part after the keyword
                      for i, part in enumerate(parts):
                          if part in ["file", "files"] and i + 1 < len(parts):
                              query = parts[i+1]
                              break
                      else: # If loop finished without break
                          query = parts[-1] # Fallback to last word

             print(f"Searching for files with query: {query}")
             result = search_files(query)
             response_message = f"File search results for '{query}':\n{json.dumps(result, indent=2)}"
             return jsonify({'response': response_message, 'tool_used': 'search_files'})

        # 3. Default to general chat / code acknowledgment
        else:
            # Check if the current user message contains code, store it if yes
            code_in_message = find_code_block(user_message)
            if code_in_message:
                 last_code_block = code_in_message
                 print(f"Stored new code block:\n{last_code_block}")
                 # Let the AI acknowledge the code naturally
                 user_message += "\n(Note: I see the code block you provided.)"


            # General chat call
            system_prompt_chat = """You are a helpful AI assistant.
- Acknowledge Python code if the user provides it (it will be noted in the user message).
- Do NOT offer to execute code unless the user explicitly asks using phrases like 'run the code' or 'execute it'.
- If the user asks you to *write* code, do so within ```python ... ``` blocks."""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt_chat},
                    {"role": "user", "content": user_message}
                ]
            )
            ai_response_content = response.choices[0].message['content']

            # Check if the AI response contains code, update last_code_block
            code_in_response = find_code_block(ai_response_content)
            if code_in_response:
                last_code_block = code_in_response
                print(f"Stored new code block from AI response:\n{last_code_block}")

            return jsonify({
                'response': ai_response_content,
                'tool_used': None
            })

    except Exception as e:
        # General error handling
        print(f"Error in /chat endpoint: {str(e)}") # Print to server console
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return jsonify({'error': 'An internal server error occurred.'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

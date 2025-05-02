import os
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import subprocess
import sys
import traceback

app = Flask(__name__)

# More permissive CORS configuration
CORS(app, 
     resources={r"/*": {
         "origins": "*",
         "methods": ["GET", "POST", "OPTIONS"],
         "allow_headers": "*",
         "expose_headers": "*",
         "supports_credentials": True
     }},
     supports_credentials=True)

# Set OpenAI API key
openai.api_key = "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"

def execute_code(code):
    try:
        # Create a temporary file to execute the code
        temp_file = 'temp_code.py'
        with open(temp_file, 'w') as f:
            f.write(code)
        
        # Execute the code and capture output
        result = subprocess.run([sys.executable, temp_file], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        
        # Clean up the temporary file
        os.remove(temp_file)
        
        if result.stdout:
            return result.stdout
        elif result.stderr:
            return f"Error: {result.stderr}"
        return "Code executed successfully (no output)"
    except Exception as e:
        return f"Error: {str(e)}"

def search_files(query):
    results = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if query.lower() in file.lower():
                results.append(os.path.join(root, file))
    return results

TOOLS = {
    "execute_python": {
        "description": "Execute Python code and return the output",
        "function": execute_code
    },
    "search_files": {
        "description": "Search for files in the workspace",
        "function": search_files
    }
}

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        user_message = data.get('message')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # First, ask GPT what tool (if any) to use
        tool_selection_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"""You are an agentic AI assistant with access to the following tools:
                {json.dumps(TOOLS, default=lambda x: x['description'] if isinstance(x, dict) else str(x), indent=2)}
                
                If the user's request requires using a tool, respond with the tool name and parameters.
                If no tool is needed, respond with 'NO_TOOL_NEEDED'."""},
                {"role": "user", "content": user_message}
            ]
        )

        tool_decision = tool_selection_response.choices[0].message['content']
        
        # Process the tool decision
        if "NO_TOOL_NEEDED" in tool_decision:
            # Regular chat response
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant with agentic capabilities."},
                    {"role": "user", "content": user_message}
                ]
            )
            return jsonify({
                'response': response.choices[0].message['content'],
                'tool_used': None
            })
        else:
            # Try to parse the tool request
            try:
                if "execute_python" in tool_decision.lower():
                    # Extract Python code from the message
                    if "```python" in user_message:
                        # Extract code between ```python and ```
                        code = user_message.split("```python")[1].split("```")[0].strip()
                    else:
                        # If no code block, treat the entire message as code
                        code = user_message.strip()
                    
                    result = TOOLS['execute_python']['function'](code)
                    return jsonify({
                        'response': f"I executed the code and here's the output:\n{result}",
                        'tool_used': 'execute_python'
                    })
                elif "search_files" in tool_decision.lower():
                    # Extract search query
                    result = TOOLS['search_files']['function'](user_message)
                    return jsonify({
                        'response': f"I found these files:\n{json.dumps(result, indent=2)}",
                        'tool_used': 'search_files'
                    })
            except Exception as e:
                print(f"Tool execution error: {str(e)}")
                print(traceback.format_exc())
                return jsonify({
                    'response': f"I tried to use a tool but encountered an error: {str(e)}",
                    'tool_used': None,
                    'error': str(e)
                })

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

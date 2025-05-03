import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from agents import Agent, Runner

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "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"

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Create the agent
agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant. You can execute Python code and answer questions.",
)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")
    if not user_input:
        return jsonify({"response": "No message provided."}), 400
    try:
        result = Runner.run_sync(agent, user_input)
        return jsonify({"response": result.final_output})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

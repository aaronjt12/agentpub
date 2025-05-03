import os
os.environ["OPENAI_API_KEY"] = "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"

from agents import Agent, Runner

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant. You can execute Python code and answer questions.",
    model="gpt-4o"
)

def main():
    user_input = input("Ask the agent anything: ")
    result = Runner.run_sync(agent, user_input)
    print("\nAgent output:")
    print(result.final_output)

if __name__ == "__main__":
    main()

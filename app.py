import os
os.environ["OPENAI_API_KEY"] = ""

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

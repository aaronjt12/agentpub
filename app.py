import os
import pyttsx3
import speech_recognition as sr
from agents import Agent, Runner
# Set your OpenAI API key directly for local testing
import os
os.environ["OPENAI_API_KEY"] = ""
def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Say something...")
        audio = r.listen(source)
    try:
        return r.recognize_google(audio)
    except Exception:
        print("Sorry, I could not understand.")
        return ""

engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

agent = Agent(
    name="System Analyst",
    instructions=(
        "You are System Analyst, a friendly and encouraging customer service focused IT professional. "
        "You explain concepts clearly, give examples, resolve complex technical issues. "
        "You can hold realtime conversation and answer any general questions surrounding IT."
    ),
    model="gpt-4o",
 
)

def strip_asterisks(text):
    return text.replace("*", "")

def main():
    greeting = "Hey, I heard you were having some trouble today. How can I help?"
    print(greeting)
    speak(greeting)
    print("Welcome to System Analyst! You can type or say your question.")
    while True:
        choice = input("Press [Enter] to type, or 'v' + [Enter] to use your voice (or 'exit' to quit): ").strip().lower()
        if choice == "exit":
            print("Goodbye!")
            break
        if choice == "v":
            user_input = listen()
            if not user_input:
                continue
            print(f"You said: {user_input}")
        else:
            user_input = input("Ask the agent anything: ")
            if user_input.strip().lower() in {"exit", "quit"}:
                print("Goodbye!")
                break
        try:
            result = Runner.run_sync(agent, user_input)
            output = strip_asterisks(result.final_output)
            print("\nAgent output:")
            print(output)
            speak(output)
        except Exception as e:
            print(f"Error getting response: {e}")

if __name__ == "__main__":
    main()

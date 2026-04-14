import os
from dotenv import load_dotenv
import vertexai
from agents.orchestrator import DOMAIN_PERSONAS, get_metis_orchestrator
from halo import Halo
import time

# Load environment variables
load_dotenv()

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION")

# Initialize Vertex AI
if (
    not os.getenv("OPENROUTER_API_KEY")
    and project_id
    and location
    and project_id != "XXXX"
    and location != "XXXX"
):
    vertexai.init(
        project=project_id,
        location=location
    )

def display_menu():
    print("\n--- Metis: Trend-to-Content Intelligence ---")
    print("Please select a high-signal domain to research:")
    for key, (name, _) in DOMAIN_PERSONAS.items():
        print(f"{key}. {name}")
    print("--------------------------------------------------")

def run_metis():
    """
    Run the Metis trend-to-content process with an animated icon.
    """
    display_menu()
    raw_input = input("Enter your choice (1-9): ").strip()
    
    # Split the input to check if they provided the domain on the same line (e.g., '9 Claude code')
    parts = raw_input.split(maxsplit=1)
    if not parts:
        print("No selection made. Exiting.")
        return
        
    choice = parts[0]
    
    if choice not in DOMAIN_PERSONAS:
        print(f"'{choice}' is an invalid selection. Please enter a number between 1 and 9.")
        return

    custom_domain = None
    if choice == "9":
        if len(parts) > 1:
            # User provided the domain on the same line
            custom_domain = parts[1]
        else:
            # Prompt for the domain on a new line
            custom_domain = input("Enter your custom domain: ").strip()
        
        if not custom_domain:
            print("Custom domain cannot be empty. Exiting.")
            return
    
    # Initialize the Metis Orchestrator for the chosen domain
    metis = get_metis_orchestrator(choice, custom_domain)
    
    topic = DOMAIN_PERSONAS.get(choice, DOMAIN_PERSONAS["9"])[0]
    if choice == "9":
        topic = custom_domain

    print(f"\n--- Starting Metis Discovery for: {topic} ---")
    
    # Use Halo for an animated 'wisdom' icon while Metis is processing
    spinner = Halo(text=f' Metis is synthesizing wisdom for {topic}...', spinner='dots', color='cyan')
    spinner.start()
    
    try:
        # Run the orchestration process
        response = metis.ask(f"Discover high-signal trends in {topic} and draft a synthesis report.")
        spinner.succeed(" Metis has found the signal.")
    except Exception as e:
        spinner.fail(" Metis encountered an error in the noise.")
        print(f"Error: {e}")
        return

    # Print the final output
    print("\n--- Final High-Signal Report ---\n")
    final_text = response if isinstance(response, str) else response.text
    try:
        print(final_text)
    except UnicodeEncodeError:
        # Windows cmd.exe often uses cp1252; avoid hard crash on unsupported glyphs.
        print(final_text.encode("cp1252", errors="replace").decode("cp1252"))
    print("\n--- Metis Process Complete ---")

if __name__ == "__main__":
    run_metis()

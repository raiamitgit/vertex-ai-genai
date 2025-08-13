import json
from helpers import gemini_helper

def get_user_history(user_id: str) -> list:
    """
    Reads user_history.json and returns the chat history for the given user ID.
    """
    with open('static/user_history.json', 'r') as f:
        history_data = json.load(f)
    return history_data.get(user_id, {}).get('history', [])

def generate_starter_prompts(user_id: str) -> list:
    """
    Generates a list of starter prompts for the user.
    If the user has no history, returns default prompts.
    Otherwise, it uses Gemini to generate contextual prompts.
    """
    history = get_user_history(user_id)
    if not history:
        return [
            "Compare the Enclave and the Envision",
            "What are the latest offers on the Encore GX?",
            "Schedule a test drive"
        ]
    else:
        # Create a concise summary of the history for the prompt
        history_summary = " ".join([item['content'] for item in history if 'content' in item])
        
        # Create a prompt for Gemini
        prompt = f"""Based on the following user chat history, generate 3 concise and relevant starter prompts for a car dealership website. The prompts should be in a list format, like ["prompt 1", "prompt 2", "prompt 3"].
        
        Chat History: "{history_summary}"
        
        Generated Prompts:
        """
        
        # Generate prompts using Gemini
        generated_prompts_str = gemini_helper.generate_text(prompt)
        
        try:
            # The model might return a string representation of a list
            prompts = json.loads(generated_prompts_str)
            if isinstance(prompts, list) and len(prompts) > 0:
                return prompts
        except (json.JSONDecodeError, TypeError):
            # Fallback if the response is not a valid JSON list
            # Or if it's just a plain string with newlines
            prompts = [p.strip() for p in generated_prompts_str.split('\n') if p.strip()]
            if prompts:
                return prompts

        # Default fallback if generation or parsing fails
        return [
            "How does the warranty compare to competitors?",
            "What financing options are available?",
            "Tell me more about the safety features."
        ]

if __name__ == '__main__':
    # This block will only execute when the script is run directly
    # You can use this for testing the module's functions
    print("--- Testing user_manager.py ---")

    # Test case 1: User with history
    user_with_history = "111"
    print(f"\n--- Testing for user: {user_with_history} (has history) ---")
    
    # Test get_user_history
    history = get_user_history(user_with_history)
    print(f"History found: {len(history)} items")
    # print(history) # Uncomment for detailed history view

    # Test generate_starter_prompts
    starter_prompts = generate_starter_prompts(user_with_history)
    print("Generated Starter Prompts:")
    for prompt in starter_prompts:
        print(f"- {prompt}")

    print("-" * 20)

    # Test case 2: New user (no history)
    new_user = "000"
    print(f"\n--- Testing for user: {new_user} (new user) ---")
    
    # Test get_user_history
    history = get_user_history(new_user)
    print(f"History found: {len(history)} items")

    # Test generate_starter_prompts
    starter_prompts = generate_starter_prompts(new_user)
    print("Generated Starter Prompts (Default):")
    for prompt in starter_prompts:
        print(f"- {prompt}")
        
    print("\n--- Testing complete ---")

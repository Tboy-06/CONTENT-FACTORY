import os
import google.generativeai as genai
import PIL.Image

def analyze_screenshot():
    # Load API key from .env
    env_path = r"D:\CONTENT-FACTORY\.env"
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('GEMINI_API_KEY='):
                genai.configure(api_key=line.strip().split('=', 1)[1])
                break
                
    file_path = r"C:\Users\User\OneDrive\Pictures\Screenshots\Screenshot 2026-09-05 114135.png"
    img = PIL.Image.open(file_path)
    
    prompt = """
    Look at this screenshot of the n8n-style dashboard I just built.
    The user said: "the information there is wrong secondly loook at the agent tab there is not enough space it is cramped"
    
    1. Look at the Agent Tab on the left. What looks cramped? Are texts overlapping or cut off?
    2. What "information is wrong"? Look at the agent names, the pipeline stages, the top bar, the status bar, or anything else. List what specifically looks factually wrong or out of place based on the CONTENT-FACTORY context.
    """
    
    print("Analyzing...")
    model = genai.GenerativeModel('gemini-3.6-flash')
    response = model.generate_content([img, prompt])
    print("--- ANALYSIS ---")
    print(response.text)
    print("--- ANALYSIS ---")
    print(response.text)

if __name__ == "__main__":
    analyze_screenshot()

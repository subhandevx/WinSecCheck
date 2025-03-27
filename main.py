import subprocess
import os
from flask import Flask, render_template, send_file

app = Flask(__name__)

def run_command_and_get_output(cmd):
    """Runs the given command in PowerShell and returns the output."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Command error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error running command: {e}")
        return None

def run_ollama_with_prompt(output_from_cmd):
    """Passes the output from PowerShell to Mistral via Ollama and returns the result."""
    try:
        # Prepare the full prompt to send to Mistral
        full_prompt = f"{output_from_cmd}\n\n tell pin point status, one point of recommendation if any"
        
        result = subprocess.run(
            ["ollama", "run", "mistral", full_prompt],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Mistral command error: {result.stderr}")
            raise Exception("Error running Mistral.")
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def save_output_to_file(output, filename="output.txt"):
    """Saves the output from Mistral to a file."""
    try:
        with open(filename, "w") as file:
            file.write(output)
        print(f"Output saved to {filename}")
    except Exception as e:
        print(f"Error saving file: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/run_command', methods=['POST'])
def run_and_display_output():
    """Handles running the command and displaying the output on the page."""
    # PowerShell command to run
    cmd = "Get-Service | Where-Object { $_.StartType -eq 'Auto' -and $_.Status -ne 'Running' } | Select-Object Name, Status | Format-Table -AutoSize"

    # Step 1: Run the PowerShell command and get the output
    output_from_cmd = run_command_and_get_output(cmd)
    if output_from_cmd is None:
        return "No output from PowerShell command."

    # Step 2: Pass the output to Mistral and get the result
    mistral_output = run_ollama_with_prompt(output_from_cmd)
    if mistral_output is None:
        return "No output from Mistral."

    # Step 3: Save the final output to a file
    save_output_to_file(mistral_output)

    return render_template('output.html', output=mistral_output)

if __name__ == "__main__":
    app.run(debug=True)

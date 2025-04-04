import subprocess
import os
import time
from flask import Flask, render_template
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Create output directory
output_dir = "outputs"
os.makedirs(output_dir, exist_ok=True)

# Define output files
output_files = {
    "defender_status": os.path.join(output_dir, "defender_status.txt"),
    "audit_policy": os.path.join(output_dir, "audit_policy.txt")
}

result_files = {
    "defender_status": os.path.join(output_dir, "mistral_defender.txt"),
    "audit_policy": os.path.join(output_dir, "mistral_audit.txt")
}

# ✅ Ensure all output files exist before execution
for file in list(output_files.values()) + list(result_files.values()):
    if not os.path.exists(file):
        open(file, "w").close()  # Create an empty file

# Define PowerShell commands
commands = {
    "defender_status": 'powershell -ExecutionPolicy Bypass -NoProfile -Command "Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, DefenderSignaturesOutOfDate, AntivirusSignatureLastUpdated, RebootRequired"',
    "audit_policy": 'powershell -ExecutionPolicy Bypass -NoProfile -Command "auditpol /get /category:*"'
}

# Run PowerShell command
def run_powershell_command(cmd, file_name):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
        # Format output with proper line breaks for readability
        formatted_output = result.stdout.replace("\n", "\n<br>")  # Add <br> for HTML line breaks
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(formatted_output)
    except Exception as e:
        print(f"PowerShell error: {e}")

# Function to run Mistral after ensuring the file exists
def run_mistral(output_file, result_file, prompt):
    time.sleep(2)  # Small delay to ensure PowerShell writes output

    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as file:
            output_from_cmd = file.read()

        full_prompt = f"{output_from_cmd}\n\n{prompt}"

        result = subprocess.run(
            ["ollama", "run", "mistral", full_prompt],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        with open(result_file, "w", encoding="utf-8") as file:
            file.write(result.stdout)

    except Exception as e:
        print(f"Mistral error: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/security_posture')
def security_posture():
    # Run PowerShell commands in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(run_powershell_command, commands["defender_status"], output_files["defender_status"])
        executor.submit(run_powershell_command, commands["audit_policy"], output_files["audit_policy"])

    time.sleep(3)  # Wait for PowerShell output before running Mistral

    # Sensible prompt to check the system security posture
    mistral_prompts = {
        "defender_status": "4 lines output Based on the results of the Defender status and antivirus settings, assess the system's security health. If any settings are not optimal or the antivirus signatures are outdated, tell specifically.",
        "audit_policy": "4 lines output Based on the output of the auditing policy, identify if any security auditing configurations are missing or require attention. Suggest specific changes for improving security monitoring."
    }

    # Run Mistral in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(run_mistral, output_files["defender_status"], result_files["defender_status"], mistral_prompts["defender_status"])
        executor.submit(run_mistral, output_files["audit_policy"], result_files["audit_policy"], mistral_prompts["audit_policy"])

    # Read and display results
    outputs = {}
    for key in result_files:
        with open(result_files[key], "r", encoding="utf-8", errors="ignore") as file:
            outputs[key] = file.read()

    return render_template('output.html', output=outputs)

if __name__ == "__main__":
    app.run(debug=True)

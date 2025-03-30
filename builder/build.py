import subprocess
import os
import shutil

UNITY_PATH_VAR = os.getenv("INPUT_UNITY_PATH_VAR")
UNITY_PATH = os.getenv(UNITY_PATH_VAR)
PROJECT_PATH = os.getenv("INPUT_PROJECT_PATH")
OUTPUT_PATH = os.getenv("INPUT_OUTPUT_PATH")
PLATFORM = os.getenv("INPUT_PLATFORM")
EXECUTE_METHOD = os.getenv("INPUT_EXECUTE_METHOD", "JNI.Editor.CI.CIBuild.Build")
IL2CPP = os.getenv("INPUT_IL2CPP", "false")

assert(UNITY_PATH_VAR)
assert(UNITY_PATH)
assert(PROJECT_PATH)
assert(OUTPUT_PATH)
assert(PLATFORM in ["StandaloneWindows64", "StandaloneWindows", "StandaloneLinux64"])

PROJECT_PATH = os.path.abspath(os.path.join(os.getcwd(), PROJECT_PATH))
OUTPUT_PATH = os.path.abspath(os.path.join(os.getcwd(), OUTPUT_PATH))

args = [
    UNITY_PATH,
    "-batchmode",
    "-quit",
    "-nographics",
    "-logfile", "-",
    "-projectPath", PROJECT_PATH,
    "-executeMethod", EXECUTE_METHOD,
    "-unityBuildTarget", PLATFORM,
    "-target", PLATFORM,
    "-il2cpp", IL2CPP,
    "-output", OUTPUT_PATH
]

if os.path.exists(OUTPUT_PATH):
    print(f"Deleting existing output directory: {OUTPUT_PATH}")
    shutil.rmtree(OUTPUT_PATH)

print("Starting Unity build...")
process = subprocess.Popen(
    args,
    stdout = subprocess.PIPE,
    stderr = subprocess.STDOUT,
    bufsize = 1,
    universal_newlines = True
)

for line in process.stdout:
    print(line, end = "")

process.wait()

print(f"\n{"[SUCCESS]" if process.returncode == 0 else "[ERROR]"} Unity exited with code {process.returncode}")
exit(process.returncode)

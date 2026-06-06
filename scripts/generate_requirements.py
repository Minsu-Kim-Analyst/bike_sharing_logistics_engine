import importlib.metadata
import sys

# 1. Define the strict top-level dependencies for the Bike Share Engine
TARGET_PACKAGES = [
    "pandas",
    "numpy",
    "xgboost",
    "scikit-learn",
    "joblib",
    "python-dotenv",
    "psycopg2-binary"
]

def generate_requirements(packages, filename="requirements.txt"):
    print(f"Auditing local environment and generating {filename}...\n")
    
    with open(filename, "w") as file:
        file.write("# --- Automated Enterprise Requirements ---\n")
        file.write("# Generated via scripts/generate_requirements.py\n\n")
        
        file.write("# Data Engineering & Database\n")
        for pkg in packages[:2] + packages[5:]: # pandas, numpy, dotenv, psycopg2
            _write_package_version(file, pkg)
            
        file.write("\n# Machine Learning\n")
        for pkg in packages[2:5]: # xgboost, scikit-learn, joblib
            _write_package_version(file, pkg)
                
    print(f"\nSuccess! {filename} has been updated with strict version pinning.")

def _write_package_version(file, pkg):
    try:
        # Fetch the exact version installed in the active environment
        version = importlib.metadata.version(pkg)
        line = f"{pkg}=={version}\n"
        file.write(line)
        print(f"✅ Locked: {line.strip()}")
    except importlib.metadata.PackageNotFoundError:
        print(f"❌ WARNING: '{pkg}' is not installed in this environment.")

if __name__ == "__main__":
    generate_requirements(TARGET_PACKAGES)

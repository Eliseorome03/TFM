import sys
import os
import glob
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    test_files = []
    for cat in ["cat1_nlu", "cat2_drools", "cat3_security"]:
        cat_dir = os.path.join(BASE_DIR, cat)
        files = glob.glob(os.path.join(cat_dir, "test_*.py"))
        test_files.extend(sorted(files))
        
    print(f"Se van a ejecutar {len(test_files)} tests secuencialmente...")
    for i, test_file in enumerate(test_files):
        print(f"\n[{i+1}/{len(test_files)}] Ejecutando: {os.path.basename(test_file)}")
        subprocess.run([sys.executable, test_file], cwd=BASE_DIR)

if __name__ == "__main__":
    main()

import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import run_reflection

if __name__ == "__main__":
    run_reflection()
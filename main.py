import sys
from dotenv import load_dotenv
from src.monitor      import run_monitor
from src.paper_trader import print_scorecard

load_dotenv()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scores":
        print_scorecard()
    else:
        run_monitor()
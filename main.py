import sys
from app import FindAApp
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    app = FindAApp(sys.argv)
    sys.exit(app.exec_())

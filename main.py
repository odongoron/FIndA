import sys
from app import FindAApp

if __name__ == "__main__":
    app = FindAApp(sys.argv)
    sys.exit(app.exec_())

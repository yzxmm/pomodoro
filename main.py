import sys
from PySide6 import QtWidgets
from pomodoro_widget import PomodoroWidget

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = PomodoroWidget()
    window.start_app()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

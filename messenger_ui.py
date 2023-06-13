import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt
from messenger_ui import Ui_MainWindow


class MessengerApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    messenger = MessengerApp()
    messenger.show()
    sys.exit(app.exec_())
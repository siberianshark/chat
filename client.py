import socket
import threading
import dis
import sqlite3
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListWidget, QTextEdit, QLineEdit, QPushButton

PEER_IP = '127.0.0.1'
PEER_PORT = 7777
class ClientDatabase:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                sender TEXT,
                receiver TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()
    def add_contact(self, username):
        self.cursor.execute("""
            INSERT INTO contacts (username) VALUES (?)
        """, (username,))
        self.connection.commit()
    def get_contacts(self):
        self.cursor.execute("""
            SELECT username FROM contacts
        """)
        return self.cursor.fetchall()
    def add_message(self, sender, receiver, message):
        self.cursor.execute("""
            INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)
        """, (sender, receiver, message))
        self.connection.commit()
    def get_messages(self, sender, receiver):
        self.cursor.execute("""
            SELECT sender, receiver, message, timestamp FROM messages
            WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
            ORDER BY timestamp ASC
        """, (sender, receiver, receiver, sender))
        return self.cursor.fetchall()
    def close(self):
        self.connection.close()
class ClientVerifier(type):
    def __init__(cls, name, bases, attrs):
        cls._verify_sockets(attrs)
        super().__init__(name, bases, attrs)
    @staticmethod
    def _verify_sockets(attrs):
        for attr_name, attr_value in attrs.items():
            if isinstance(attr_value, socket.socket):
                raise TypeError(
                    f"Socket creation not allowed in class attribute '{attr_name}'")
            if callable(attr_value):
                bytecode = dis.Bytecode(attr_value)
                for instruction in bytecode:
                    if instruction.opname in ("CALL_FUNCTION", "CALL_METHOD") and isinstance(instruction.argval, socket.socket):
                        raise TypeError(
                            f"Socket method calls not allowed in function '{attr_name}'")
class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self._socket = None
    def connect(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.host, self.port))
    def send(self, data):
        if not self._socket:
            raise RuntimeError(
                "Socket is not connected. Call connect() method first.")
        self._socket.sendall(data.encode())
    def receive(self, buffer_size=1024):
        if not self._socket:
            raise RuntimeError(
                "Socket is not connected. Call connect() method first.")
        data = self._socket.recv(buffer_size)
        return data.decode()
    def close(self):
        if self._socket:
            self._socket.close()
            self._socket = None


class ChatApplication(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Application")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Отображение списка контактов
        self.contact_list = QListWidget()
        self.contact_list.doubleClicked.connect(self.open_chat)
        layout.addWidget(self.contact_list)

        self.chat_history = QTextEdit()
        layout.addWidget(self.chat_history)

        self.message_input = QLineEdit()
        layout.addWidget(self.message_input)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        self.setLayout(layout)

    def open_chat(self, item):
        selected_contact = item.text()
        self.chat_history.clear()
        self.chat_history.append(f"Opened chat with {selected_contact}")

    def send_message(self):
        message = self.message_input.text()
        self.chat_history.append(f"Sent message: {message}")
        self.message_input.clear()


def main():
    client = Client(PEER_IP, PEER_PORT)
    client.connect()
    client.send("Hello, server!")
    response = client.receive()
    print(response)
    client.close()
import dis
import socket
import threading
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from messenger_ui import MessengerApp
import os
import hashlib
from server_admin_ui import ServerAdminApp
import hmac


Base = declarative_base()
HOST = '0.0.0.0'
PORT = 7777
clients = []


def login_required(f):
    def decor(*args, **kwargs):
        if not 'user_id' or 'passw':
            return ValueError
        return f(*args, **kwargs)
    return decor


class PortDescriptor:
    def __init__(self, default_port=7777):
        self._default_port = default_port
        self._value = None
    def __get__(self, instance, owner):
        if self._value is None:
            return self._default_port
        return self._value
    def __set__(self, instance, value):
        if not isinstance(value, int):
            raise TypeError("Port number must be an integer.")
        if value < 0:
            raise ValueError(
                "Port number must be greater than or equal to zero.")
        self._value = value
class ServerVerifier(type):
    def __init__(cls, name, bases, attrs):
        cls._verify_sockets(attrs)
        super().__init__(name, bases, attrs)
    @staticmethod
    def _verify_sockets(attrs):
        for attr_name, attr_value in attrs.items():
            if callable(attr_value):
                bytecode = dis.Bytecode(attr_value)
                for instruction in bytecode:
                    if instruction.opname == "CALL_METHOD" and isinstance(instruction.argval, socket.socket) and instruction.argval.type != socket.SOCK_STREAM:
                        raise TypeError(
                            f"Socket method calls not allowed in function '{attr_name}'")
                    if instruction.opname == "LOAD_METHOD" and instruction.argval == "connect":
                        raise TypeError(
                            f"Socket 'connect' method calls not allowed in function '{attr_name}'")
class Server(metaclass=ServerVerifier):
    port = PortDescriptor()
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self._socket = None
    def start(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self.host, self.port))
        self._socket.listen(1)
        while True:
            client_socket, client_address = self._socket.accept()
            self.handle_client(client_socket, client_address)
    def handle_client(self, client_socket, client_address):
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    clients.remove(client_socket)
                    client_socket.close()
                    print(
                        f"Connection with {client_address}  has been refused")
                    break
                for c in clients:
                    if c != client_socket:
                        c.send(data)
            except:
                clients.remove(client_socket)
                client_socket.close()
                print(f"Connection with {client_address} has been refused")
                break
    def close(self):
        if self._socket:
            self._socket.close()
            self._socket = None
class Client(Base):
    __tablename__ = 'client'
    id = Column(Integer, primary_key=True)
    login = Column(String)
    info = Column(String)
    passw = hashlib.md5(Column(String))


class ClientHistory(Base):
    __tablename__ = 'client_history'
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer)
    login_time = Column(DateTime)
    ip_address = Column(String)
class ContactList(Base):
    __tablename__ = 'contact_list'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer)
    client_id = Column(Integer)


@login_required
def server_authenticate(connection, secret_key):
    message = os.urandom(32)
    connection.send(message)
    hash = hmac.new(secret_key, message)
    digest = hash.digest()
    response = connection.recv(len(digest))
    return hmac.compare_digest(digest, response)


def client_authenticate(connection, secret_key):
    message = connection.recv(32)
    hash = hmac.new(secret_key, message)
    digest = hash.digest()
    connection.send(digest)


class Storage:
    def __init__(self, db_path):
        engine = create_engine(f'sqlite://.{db_path}')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()
    def add_client(self, login, info):
        client = Client(login=login, info=info)
        self.session.add(client)
        self.session.commit()
    def add_client_history(self, client_id, login_time, ip_address):
        client_history = ClientHistory(
            client_id=client_id, login_time=login_time, ip_address=ip_address)
        self.session.add(client_history)
        self.session.commit()
    def add_contact(self, owner_id, client_id):
        contact = ContactList(owner_id=owner_id, client_id=client_id)
        self.session.add(contact)
        self.session.commit()
    def get_client_by_login(self, login):
        return self.session.query(Client).filter_by(login=login).first()
    def get_client_history_by_client_id(self, client_id):
        return self.session.query(ClientHistory).filter_by(client_id=client_id).all()
    def get_contacts_by_owner_id(self, owner_id):
        return self.session.query(ContactList).filter_by(owner_id=owner_id).all()
class ContactStorage:
    def __init__(self):
        self.contacts = []
    def get_contacts(self, user_login):
        return {
            "response": "202",
            "alert": self.contacts
        }
    def add_contact(self, user_id):
        if user_id not in self.contacts:
            self.contacts.append(user_id)
            return {"response": 200}
        else:
            return {"response": 409}
    def del_contact(self, user_id):
        if user_id in self.contacts:
            self.contacts.remove(user_id)
            return {"response": 200}
        else:
            return {"response": 404}
class MyServer(Server):
    def handle_client(self, client_socket, client_address):
        data = client_socket.recv(1024)
        response = "Received: " + data.decode()
        client_socket.sendall(response.encode())
        client_socket.close()
server_app = ServerAdminApp()
messenger_app = MessengerApp()
my_server = MyServer(HOST, PORT)
storage = Storage('db.sqlite3')
my_server.start()
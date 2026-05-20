
import socket

def get_free_port(start=10000, end=20000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        puerto= s.getsockname()[1]
    return puerto
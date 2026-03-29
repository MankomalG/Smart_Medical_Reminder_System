import socket
import json
import requests

HOST = "0.0.0.0"
PORT = 9000

FLASK_EVENTS_URL = "http://127.0.0.1:5000/api/events"

def handle_client(conn):
    print("Client connected")

    buffer = ""

    while True:
        data = conn.recv(1024)
        if not data:
            break

        buffer += data.decode()

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()

            if not line:
                continue

            print("RX TCP:", line)

            try:
                msg = json.loads(line)

                # Only handle dispense for now
                if msg.get("type") == "dispense_verification":
                    requests.post(FLASK_EVENTS_URL, json=msg)

            except Exception as e:
                print("Parse error:", e)

    conn.close()
    print("Client disconnected")


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(1)

    print(f"TCP server listening on {HOST}:{PORT}")

    while True:
        conn, addr = s.accept()
        print("Connection from", addr)
        handle_client(conn)


if __name__ == "__main__":
    main()
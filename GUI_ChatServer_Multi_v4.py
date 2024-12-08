import os
from socket import *
from threading import *

class MultiChatServer:
    def __init__(self):
        self.clients = []  # 접속된 클라이언트 소켓 목록
        self.s_sock = socket(AF_INET, SOCK_STREAM)
        self.ip = ''
        self.port = 2500
        self.s_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.s_sock.bind((self.ip, self.port))
        print("클라이언트 대기 중 ...")
        self.s_sock.listen(100)
        self.accept_client()

    def accept_client(self):
        while True:
            c_socket, (ip, port) = self.s_sock.accept()
            if c_socket not in self.clients:
                self.clients.append(c_socket)
                print(ip, ':', str(port), '가 연결되었습니다.')
                cth = Thread(target=self.receive_messages, args=(c_socket,))
                cth.start()

    def receive_messages(self, c_socket):
        while True:
            try:
                incoming_message = c_socket.recv(1024).decode('utf-8')
                if not incoming_message:
                    break

                # 파일 전송 요청 처리
                if incoming_message.startswith("FILE:"):
                    filename = incoming_message[5:]
                    self.receive_file(c_socket, filename)
                # 파일 다운로드 요청 처리
                elif incoming_message.startswith("DOWNLOAD:"):
                    filename = incoming_message[9:]
                    self.send_file(c_socket, filename)
                # 타이핑 상태 처리
                elif incoming_message.startswith("TYPING:"):
                    self.broadcast_message(c_socket, incoming_message)  # 타이핑 상태 브로드캐스트
                elif incoming_message.startswith("TYPING_STOP:"):
                    self.broadcast_message(c_socket, incoming_message)  # 타이핑 중단 브로드캐스트
                # 일반 메시지 처리
                else:
                    self.broadcast_message(c_socket, incoming_message)
            except Exception as e:
                print(f"오류 발생: {e}")
                continue
        c_socket.close()



    def receive_file(self, c_socket, filename):
        try:
            with open(filename, "wb") as f:
                while True:
                    data = c_socket.recv(1024)
                    if b"END_OF_FILE" in data:
                        f.write(data.split(b"END_OF_FILE")[0])  # 종료 신호 이전 데이터 저장
                        break
                    f.write(data)
            print(f"{filename} 파일이 저장되었습니다.")
            self.broadcast_message(c_socket, f"NEW_FILE:{filename}")
        except Exception as e:
            print(f"파일 수신 중 오류 발생: {e}")

    def send_file(self, c_socket, filename):
        if os.path.exists(filename):
            try:
                c_socket.send(f"FILE_START:{filename}".encode('utf-8'))
                with open(filename, "rb") as f:
                    while chunk := f.read(1024):
                        c_socket.send(chunk)
                c_socket.send(b"END_OF_FILE")  # 종료 신호 전송
                print(f"{filename} 파일이 클라이언트에 전송되었습니다.")
            except Exception as e:
                print(f"파일 전송 중 오류 발생: {e}")
        else:
            c_socket.send(b"FILE_NOT_FOUND")



    def broadcast_message(self, senders_socket, message):
        for client in self.clients:
            if client is not senders_socket:
                try:
                    client.sendall(message.encode())
                except:
                    self.clients.remove(client)

if __name__ == "__main__":
    MultiChatServer()
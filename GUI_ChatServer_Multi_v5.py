import os
from socket import *
from threading import *

class MultiChatServer:
    def __init__(self):
        self.clients = []  # 접속된 클라이언트 소켓 목록
        self.s_sock = socket(AF_INET, SOCK_STREAM) # TCP 소켓 생성
        self.ip = '' # 모든 IP로부터 연결을 허용
        self.port = 2500  # 서버 포트 번호
        self.s_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1) # 소켓 재사용 옵션 설정
        self.s_sock.bind((self.ip, self.port)) # IP와 포트를 소켓에 바인딩
        print("클라이언트 대기 중 ...")
        self.s_sock.listen(100) # 최대 100명의 클라이언트 연결 허용
        self.accept_client() # 클라이언트 연결을 수락하는 메서드 호출

    def accept_client(self):
        """클라이언트의 연결을 수락하고, 각 클라이언트와 통신할 스레드를 생성합니다."""
        while True:
            c_socket, (ip, port) = self.s_sock.accept() # 클라이언트 연결 수락
            if c_socket not in self.clients: # 연결 수락한 클라이언트가 현재 clients에 없으면 
                self.clients.append(c_socket) # 새로운 클라이언트 추가
                print(ip, ':', str(port), '가 연결되었습니다.')
                cth = Thread(target=self.receive_messages, args=(c_socket,)) # 클라이언트와 통신할 스레드 생성
                cth.start() # 스레드 시작

    def receive_messages(self, c_socket):
        while True:
            try:
                incoming_message = c_socket.recv(1024).decode('utf-8') # 1024 바이트 데이터 수신 및 UTF-8 디코딩
                if not incoming_message: # 클라이언트 연결이 끊어졌다면
                    break 

                # 파일 전송 요청 처리
                if incoming_message.startswith("FILE:"):
                    filename = incoming_message[5:] # "FILE:" 이후의 파일명 추출
                    self.receive_file(c_socket, filename) # 파일 수신 시작
                # 파일 다운로드 요청 처리
                elif incoming_message.startswith("DOWNLOAD:"):
                    filename = incoming_message[9:] # "DOWNLOAD:" 이후의 파일명 추출
                    self.send_file(c_socket, filename) # 파일 전송 시작
                # 타이핑 상태 처리
                elif incoming_message.startswith("TYPING:"):
                    self.broadcast_message(c_socket, incoming_message)  # 타이핑 상태 브로드캐스트
                elif incoming_message.startswith("TYPING_STOP:"):
                    self.broadcast_message(c_socket, incoming_message)  # 타이핑 중단 브로드캐스트
                # 일반 메시지 처리
                else:
                    self.broadcast_message(c_socket, incoming_message) # 일반 메시지를 브로드캐스트
            except Exception as e:
                print(f"오류 발생: {e}")
                continue
        c_socket.close()



    def receive_file(self, c_socket, filename):
        try:
            with open(filename, "wb") as f: # 파일을 바이너리 모드로 엽니다.
                while True:
                    data = c_socket.recv(1024) # 1024 바이트씩 수신
                    if b"END_OF_FILE" in data: # 파일 전송 종료 신호 확인
                        f.write(data.split(b"END_OF_FILE")[0])  # 종료 신호 이전 데이터 저장
                        break
                    f.write(data)
            print(f"{filename} 파일이 저장되었습니다.")
            self.broadcast_message(c_socket, f"NEW_FILE:{filename}") # 새로운 파일이 생성되었음을 알림
        except Exception as e:
            print(f"파일 수신 중 오류 발생: {e}") # 오류 메시지 출력

    def send_file(self, c_socket, filename):
        if os.path.exists(filename): # 파일이 존재하면
            try:
                c_socket.send(f"FILE_START:{filename}".encode('utf-8')) # 파일 전송 시작 신호 전송
                with open(filename, "rb") as f: # 파일을 바이너리 모드로 엽니다.
                    while chunk := f.read(1024): # 1024 바이트씩 읽기
                        c_socket.send(chunk) # 파일 조각 전송
                c_socket.send(b"END_OF_FILE")  # 파일 전송 종료 신호 전송
                print(f"{filename} 파일이 클라이언트에 전송되었습니다.")
            except Exception as e:
                print(f"파일 전송 중 오류 발생: {e}")
        else:
            c_socket.send(b"FILE_NOT_FOUND")



    def broadcast_message(self, senders_socket, message):
        """한 클라이언트가 보낸 메시지를 모든 클라이언트에게 브로드캐스트합니다."""
        for client in self.clients:  # 연결된 모든 클라이언트에 대해
            if client is not senders_socket: # 메시지를 보낸 클라이언트는 제외
                try:
                    client.sendall(message.encode()) # 메시지를 전송
                except:
                    self.clients.remove(client) # 연결이 끊어진 클라이언트를 제거

if __name__ == "__main__":
    MultiChatServer() # 서버 인스턴스 생성 및 실행
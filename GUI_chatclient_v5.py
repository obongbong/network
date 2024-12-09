from tkinter import *
from tkinter.scrolledtext import ScrolledText
from tkinter.filedialog import askopenfilename, asksaveasfilename
from threading import *
from socket import *
from tkinter.font import Font
import time
import os

# 이모지 코드와 유니코드 매핑
EMOJI_MAP = {
    ":thumbs_up:": "👍",
    ":heart:": "❤️",
}

class ChatClient:
    def __init__(self, ip, port):
        self.client_socket = None  # 클라이언트 소켓
        self.initialize_socket(ip, port)  # 서버 연결
        self.initialize_gui()  # GUI 초기화
        self.listen_thread()  # 서버로부터 메시지를 받는 스레드 시작
        self.typing_statuses = set()  # 현재 입력 중인 사용자 목록 관리
        self.downloading = False  # 파일 다운로드 중 상태 관리
        self.typing_status = False  # 현재 클라이언트의 타이핑 상태

    def initialize_socket(self, ip, port):
        """서버와 소켓 연결을 초기화합니다."""
        self.client_socket = socket(AF_INET, SOCK_STREAM) #TCP 소켓 생성
        self.client_socket.connect((ip, port)) # 서버 연결

    def send_chat(self):
        """입력한 채팅 메시지를 서버로 전송합니다."""
        senders_name = self.name_widget.get().strip() #이름 입력
        data = self.enter_text_widget.get(1.0, 'end').strip() #채팅 입력

        # 이모지 코드 변환
        for code, emoji in EMOJI_MAP.items(): #이모지 코드 변환
            data = data.replace(code, emoji)

        # 메시지 전송
        if data:
            message = f"{senders_name}: {data}" #메시지 포맷
            self.client_socket.send(message.encode('utf-8')) # 메시지 서버로 전송

            # 채팅창에 본인이 보낸 메시지 표시
            self.chat_transcript_area.insert('end', message + '\n')
            self.chat_transcript_area.yview(END)

            # 입력창 초기화
            self.enter_text_widget.delete(1.0, 'end')

            # 메시지 전송 후 입력창이 비었으므로 타이핑 중단 메시지 전송 필요 여부 체크
            current_text = self.enter_text_widget.get(1.0, 'end').strip()
            if not current_text and self.typing_status:
                self.typing_status = False
                sender_name = self.name_widget.get().strip()
                self.client_socket.send(f"TYPING_STOP:{sender_name}".encode('utf-8'))

    def add_emoji_to_text(self, emoji_code):
        """텍스트 입력 위젯에 이모지 코드를 추가합니다."""
        current_text = self.enter_text_widget.get(1.0, 'end').strip()
        new_text = f"{current_text} {emoji_code}"
        self.enter_text_widget.delete(1.0, 'end')
        self.enter_text_widget.insert('end', new_text)

    def send_file(self):
        """파일을 선택하여 서버로 전송합니다."""
        filepath = askopenfilename() #파일 탐색기 창을 열어 파일 경로를 선택
        if not filepath:
            return
        filename = filepath.split("/")[-1] #파일 경로에서 파일명만 추출
        self.client_socket.send(f"FILE:{filename}".encode('utf-8')) #서버에 "FILE:파일명" 메시지를 보냄
        with open(filepath, "rb") as f: #파일을 이진 모드로 열기(읽기 전용)
            while chunk := f.read(1024): #파일의 내용을 1024바이트 단위로 읽기 (메모리 효율을 위해 잘라서 보냄)
                self.client_socket.send(chunk) #서버에 파일 조각을 전송
        self.client_socket.send(b"END_OF_FILE")  # 서버에 END_OF_FILE 종료 신호 전송
        self.chat_transcript_area.insert('end', f"파일 {filename} 전송 완료\n")
        self.chat_transcript_area.yview(END)

    def download_file(self, filename):
        """서버로부터 파일을 다운로드합니다."""
        if self.downloading: #이미 다운중이면 리턴
            return
        self.downloading = True #아니면 다운로드 상태를 True로 변경

        save_path = asksaveasfilename(initialfile=filename) # 저장할 파일 경로 선택
        if not save_path: #사용자가 파일 경로를 선택하지 않고 취소를 눌렀다면
            self.downloading = False #다운로드 상태 해제
            return # 함수 종료

        self.client_socket.send(f"DOWNLOAD:{filename}".encode('utf-8')) # 서버에 파일 다운로드 요청
        try:
            with open(save_path, "wb") as f: # 저장할 파일을 바이너리 모드로 엽니다.
                buffer = b"" # 파일 데이터를 임시로 보관하는 버퍼
                while True:
                    data = self.client_socket.recv(1024) # 서버로부터 1024바이트 데이터 수신
                    if not data: # 데이터가 없으면 연결 종료
                        break
                    buffer += data # 버퍼에 데이터 추가
                    if b"END_OF_FILE" in buffer: # "END_OF_FILE" 신호가 수신되었다면
                        idx = buffer.index(b"END_OF_FILE") # END_OF_FILE의 인덱스를 찾고
                        f.write(buffer[:idx]) # END_OF_FILE 이전의 파일 데이터를 파일에 씁니다.
                        break
            self.chat_transcript_area.insert('end', f"파일 {filename} 다운로드 완료\n")
            self.chat_transcript_area.yview(END)
        except Exception as e:
            self.chat_transcript_area.insert('end', f"파일 다운로드 중 오류 발생: {e}\n")
        finally:
            self.downloading = False # 다운로드 상태 해제 (다른 파일 다운로드 가능)

    def handle_enter_key(self, event):
        """엔터키 입력 시 메시지를 전송하고 기본 동작(줄바꿈)을 막습니다."""
        self.send_chat()
        return "break"  # 기본 줄바꿈 동작을 방해

    def initialize_gui(self):
        """클라이언트 GUI를 초기화합니다."""
        self.root = Tk()
        self.root.title("Chat Client")

        custom_font = Font(family="Arial Unicode MS", size=12)
        fr = [Frame(self.root) for _ in range(6)]
        for f in fr:
            f.pack(fill=BOTH)

        # 이름 및 메시지 수신 영역
        self.name_label = Label(fr[0], text='이름:', font=custom_font)
        self.name_widget = Entry(fr[0], width=15, font=custom_font)
        self.recv_label = Label(fr[1], text='받은 메시지:', font=custom_font)
        self.chat_transcript_area = ScrolledText(fr[2], height=20, width=60, font=custom_font)

        # 전송 및 파일 버튼
        self.send_btn = Button(fr[4], text='전송', command=self.send_chat, font=custom_font)
        self.file_btn = Button(fr[4], text='파일 전송', command=self.send_file, font=custom_font)

        # 이모지 버튼 영역
        self.emoji_frame = Frame(fr[3])
        self.emoji_frame.pack(fill=BOTH)
        self.emoji_thumbsup_btn = Button(self.emoji_frame, text="👍", font=custom_font, command=lambda: self.add_emoji_to_text(":thumbs_up:"))
        self.emoji_heart_btn = Button(self.emoji_frame, text="❤️", font=custom_font, command=lambda: self.add_emoji_to_text(":heart:"))
        self.emoji_thumbsup_btn.pack(side=LEFT, padx=5)
        self.emoji_heart_btn.pack(side=LEFT, padx=5)

        # 타이핑 상태 레이블
        self.typing_status_label = Label(fr[5], text='', font=custom_font, fg="blue")
        self.typing_status_label.pack(side=TOP, fill=BOTH, padx=5, pady=2)

        # 메시지 입력 영역
        self.enter_text_widget = ScrolledText(fr[5], height=5, width=60, font=custom_font)

        # 키 입력 시 타이핑 상태 업데이트
        self.enter_text_widget.bind("<KeyPress>", self.notify_typing) # 위젯.bind(이벤트, 이벤트 발생 시 호출할 함수)

        # **엔터 키를 이용한 메시지 전송**  
        # 텍스트 위젯에서 엔터 키를 누르면 handle_enter_key가 호출되도록 바인딩
        self.enter_text_widget.bind("<Return>", self.handle_enter_key) # 위젯.bind(이벤트, 이벤트 발생 시 호출할 함수)

        self.name_label.pack(side=LEFT)
        self.name_widget.pack(side=LEFT)
        self.recv_label.pack(side=LEFT)
        self.send_btn.pack(side=RIGHT, padx=5)
        self.file_btn.pack(side=RIGHT, padx=5)
        self.chat_transcript_area.pack(side=LEFT, padx=5, pady=5)
        self.enter_text_widget.pack(side=LEFT, padx=5, pady=5)

    def notify_typing(self, event=None):
        """키를 누를 때마다 텍스트 유무를 확인해 타이핑 상태를 갱신합니다."""
        current_text = self.enter_text_widget.get(1.0, 'end').strip()
        sender_name = self.name_widget.get().strip()

        # 입력창에 문자가 있고, 현재 타이핑 상태가 아니라면 TYPING 전송
        if current_text and not self.typing_status:
            self.typing_status = True
            self.client_socket.send(f"TYPING:{sender_name}".encode('utf-8'))

        # 입력창이 비어있고, 현재 타이핑 상태라면 TYPING_STOP 전송
        elif not current_text and self.typing_status:
            self.typing_status = False
            self.client_socket.send(f"TYPING_STOP:{sender_name}".encode('utf-8'))

    def listen_thread(self):
        """서버로부터 수신하는 스레드를 시작합니다."""
        t = Thread(target=self.receive_message, args=(self.client_socket,))
        t.daemon = True
        t.start()

    def receive_file(self, so, filename):
        """파일 수신 처리 (파일 시작 신호 이후 호출)."""
        save_path = asksaveasfilename(initialfile=filename) # 사용자에게 파일 저장 경로와 파일명을 선택하게 함
        if not save_path: # 사용자가 경로를 선택하지 않고 취소를 누르면
            self.discard_file_data(so) # 서버로부터 더 이상 데이터 받지 않고 버림
            return
        try:
            with open(save_path, "wb") as f: # 저장할 파일을 바이너리 모드로 엽니다.
                buffer = b"" # 수신한 데이터를 임시로 저장하는 버퍼
                while True: 
                    data = so.recv(1024) # 서버로부터 1024 바이트씩 수신
                    if not data: # 데이터가 없으면 연결이 종료되었다고 판단
                        break
                    buffer += data # 수신한 데이터를 버퍼에 추가
                    if b"END_OF_FILE" in buffer: # END_OF_FILE 신호가 수신되었다면
                        idx = buffer.index(b"END_OF_FILE") # END_OF_FILE 위치 찾기
                        f.write(buffer[:idx]) # END_OF_FILE 이전의 데이터만 파일에 씁니다.
                        break
                self.chat_transcript_area.insert('end', f"파일 {filename} 다운로드 완료\n")
                self.chat_transcript_area.yview(END)
        except Exception as e:
            self.chat_transcript_area.insert('end', f"파일 다운로드 중 오류 발생: {e}\n")
        finally:
            print(f"파일 다운로드 완료: {filename}")

    def discard_file_data(self, so):
        """파일 저장 취소 시 파일 데이터를 소진하기 위한 함수."""
        buffer = b"" # 수신한 데이터를 누적할 버퍼
        while True:
            data = so.recv(1024) # 1024 바이트씩 수신
            if not data: # 데이터가 비어 있으면 (서버 연결 종료)
                break
            buffer += data # 수신한 데이터를 버퍼에 추가
            if b"END_OF_FILE" in buffer: # END_OF_FILE 신호가 발견되면
                break # 루프 종료

    def update_typing_status(self):
        """현재 입력 중인 클라이언트 목록을 바탕으로 상태 레이블을 업데이트합니다."""
        if not self.typing_statuses: 
            self.typing_status_label.config(text="") # 상태 레이블을 비웁니다.
            return # 함수 종료

        count = len(self.typing_statuses)
        if count == 1:
            user = list(self.typing_statuses)[0] # 입력 중인 사용자 중 첫 번째 사용자
            self.typing_status_label.config(text=f"{user}님이 입력 중...") # 상태 레이블에 메시지 설정
        elif count <= 3:
            users = " ".join([f"{u}님" for u in self.typing_statuses]) # 모든 사용자 이름을 "님"으로 포맷
            self.typing_status_label.config(text=f"{users} 입력 중...") # 상태 레이블에 메시지 설정
        else:
            users = list(self.typing_statuses) # 집합(set)을 리스트로 변환
            first_user = users[0] # 첫 번째 사용자
            others_count = count - 1 # 나머지 사용자 수
            self.typing_status_label.config(text=f"{first_user}님 외 {others_count}명 입력 중...") # 상태 메시지

    def receive_message(self, so):
        """서버로부터 메시지를 수신하고, 그에 따라 UI를 업데이트합니다."""
        while True:
            try:
                buf = so.recv(1024) # 1024 바이트씩 서버로부터 데이터를 수신
                if not buf: # 서버로부터 받은 데이터가 없으면 (연결이 끊어진 경우)
                    break

                if buf.startswith(b"FILE_START:"): # FILE_START: 파일명 분리
                    header, filename = buf.decode('utf-8').split(":")
                    filename = filename.strip() # 파일명 앞뒤 공백 제거
                    self.chat_transcript_area.insert('end', f"{filename} 다운로드 중...\n") # 채팅창에 알림
                    self.chat_transcript_area.yview(END) # 스크롤 아래로 이동
                    self.receive_file(so, filename) # 파일 다운로드 메서드 호출
                else:
                    try:
                        decoded_msg = buf.decode('utf-8') # 수신한 데이터를 UTF-8로 디코딩
                        if decoded_msg.startswith("NEW_FILE:"):
                            filename = decoded_msg.split(":")[1] # NEW_FILE: 파일명
                            self.chat_transcript_area.insert('end', f"새 파일 수신: {filename} (클릭하여 다운로드)\n")
                            self.chat_transcript_area.tag_add(filename, "end-2l", "end-1l")
                            self.chat_transcript_area.tag_bind(
                                filename, "<Button-1>", lambda e, fname=filename: self.client_socket.send(f"DOWNLOAD:{fname}".encode('utf-8'))
                            )
                        elif decoded_msg.startswith("TYPING:"):
                            sender_name = decoded_msg.split(":")[1] # 입력 중인 사용자 이름 추출
                            self.typing_statuses.add(sender_name) # 입력 중인 사용자 추가
                            self.update_typing_status() # UI 상태 업데이트
                        elif decoded_msg.startswith("TYPING_STOP:"): # TYPING_STOP 신호를 받으면, 입력 중인 사용자 목록에서 해당 사용자를 제거합니다.
                            sender_name = decoded_msg.split(":")[1]
                            if sender_name in self.typing_statuses:
                                self.typing_statuses.remove(sender_name) # 입력 중단
                            self.update_typing_status()
                        else: # 일반적인 채팅 메시지는 그대로 채팅창에 출력
                            self.chat_transcript_area.insert('end', decoded_msg + '\n')
                            self.chat_transcript_area.yview(END)
                    except UnicodeDecodeError:
                        pass
            except Exception as e:
                print(f"receive_message 오류: {e}")
                break


if __name__ == "__main__":
    ip = '127.0.0.1'
    port = 2500
    ChatClient(ip, port)
    mainloop()

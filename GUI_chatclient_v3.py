from tkinter import *
from tkinter.scrolledtext import ScrolledText
from tkinter.filedialog import askopenfilename, asksaveasfilename
from threading import *
from socket import *
from tkinter.font import Font

# 이모지 코드와 유니코드 매핑
EMOJI_MAP = {
    ":thumbs_up:": "👍",
    ":heart:": "❤️",
}

class ChatClient:
    def __init__(self, ip, port):
        self.client_socket = None
        self.initialize_socket(ip, port)
        self.initialize_gui()
        self.listen_thread()

    def initialize_socket(self, ip, port):
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect((ip, port))

    def send_chat(self):
        senders_name = self.name_widget.get().strip()
        data = self.enter_text_widget.get(1.0, 'end').strip()

        # 이모지 코드 변환
        for code, emoji in EMOJI_MAP.items():
            data = data.replace(code, emoji)

        message = f"{senders_name}: {data}"
        self.client_socket.send(message.encode('utf-8'))
        self.chat_transcript_area.insert('end', message + '\n')
        self.chat_transcript_area.yview(END)
        self.enter_text_widget.delete(1.0, 'end')

    def add_emoji_to_text(self, emoji_code):
        """텍스트 입력 위젯에 이모지 코드를 추가합니다."""
        current_text = self.enter_text_widget.get(1.0, 'end').strip()
        new_text = f"{current_text} {emoji_code}"
        self.enter_text_widget.delete(1.0, 'end')
        self.enter_text_widget.insert('end', new_text)

    def send_file(self):
        filepath = askopenfilename()
        if not filepath:
            return
        filename = filepath.split("/")[-1]
        self.client_socket.send(f"FILE:{filename}".encode('utf-8'))
        with open(filepath, "rb") as f:
            while chunk := f.read(1024):
                self.client_socket.send(chunk)
        self.client_socket.send(b"END_OF_FILE")
        self.chat_transcript_area.insert('end', f"파일 {filename} 전송 완료\n")
        self.chat_transcript_area.yview(END)

    def download_file(self, filename):
        # 다운로드 플래그 추가
        if hasattr(self, 'downloading') and self.downloading:
            return  # 이미 다운로드 중이면 중복 실행 방지

        self.downloading = True  # 다운로드 상태 설정
        save_path = asksaveasfilename(initialfile=filename)
        if not save_path:
            self.downloading = False  # 다운로드 취소 시 상태 초기화
            return

        self.client_socket.send(f"DOWNLOAD:{filename}".encode('utf-8'))
        try:
            with open(save_path, "wb") as f:
                while True:
                    data = self.client_socket.recv(1024)
                    if b"END_OF_FILE" in data:
                        f.write(data.split(b"END_OF_FILE")[0])  # 종료 신호 이전 데이터 저장
                        break
                    f.write(data)
            self.chat_transcript_area.insert('end', f"파일 {filename} 다운로드 완료\n")
            self.chat_transcript_area.yview(END)
        except Exception as e:
            self.chat_transcript_area.insert('end', f"파일 다운로드 중 오류 발생: {e}\n")
            self.chat_transcript_area.yview(END)
        finally:
            self.downloading = False  # 다운로드 상태 초기화



    def initialize_gui(self):
        self.root = Tk()
        self.root.title("Chat Client")

        custom_font = Font(family="Arial Unicode MS", size=12)
        fr = [Frame(self.root) for _ in range(6)]
        for f in fr:
            f.pack(fill=BOTH)

        self.name_label = Label(fr[0], text='이름:', font=custom_font)
        self.name_widget = Entry(fr[0], width=15, font=custom_font)
        self.recv_label = Label(fr[1], text='받은 메시지:', font=custom_font)
        self.send_btn = Button(fr[4], text='전송', command=self.send_chat, font=custom_font)
        self.file_btn = Button(fr[4], text='파일 전송', command=self.send_file, font=custom_font)

        self.chat_transcript_area = ScrolledText(fr[2], height=20, width=60, font=custom_font)
        self.enter_text_widget = ScrolledText(fr[5], height=5, width=60, font=custom_font)

        # 이모지 버튼 추가
        self.emoji_frame = Frame(fr[3])
        self.emoji_frame.pack(fill=BOTH)
        self.emoji_thumbsup_btn = Button(self.emoji_frame, text="👍", font=custom_font, command=lambda: self.add_emoji_to_text(":thumbs_up:"))
        self.emoji_heart_btn = Button(self.emoji_frame, text="❤️", font=custom_font, command=lambda: self.add_emoji_to_text(":heart:"))
        self.emoji_thumbsup_btn.pack(side=LEFT, padx=5)
        self.emoji_heart_btn.pack(side=LEFT, padx=5)

        self.name_label.pack(side=LEFT)
        self.name_widget.pack(side=LEFT)
        self.recv_label.pack(side=LEFT)
        self.send_btn.pack(side=RIGHT, padx=5)
        self.file_btn.pack(side=RIGHT, padx=5)
        self.chat_transcript_area.pack(side=LEFT, padx=5, pady=5)
        self.enter_text_widget.pack(side=LEFT, padx=5, pady=5)

    def listen_thread(self):
        t = Thread(target=self.receive_message, args=(self.client_socket,))
        t.start()

    def receive_message(self, so):
        while True:
            buf = so.recv(1024)
            if not buf:
                break
            try:
                decoded_msg = buf.decode('utf-8')

                # 파일 데이터 시작 신호 확인
                if decoded_msg.startswith("FILE_START:"):
                    filename = decoded_msg.split(":")[1]
                    if not hasattr(self, 'downloading') or not self.downloading:
                        self.chat_transcript_area.insert('end', f"{filename} 다운로드 중...\n")
                        self.chat_transcript_area.yview(END)
                        self.download_file(filename)
                # 새 파일 알림 처리
                elif decoded_msg.startswith("NEW_FILE:"):
                    filename = decoded_msg.split(":")[1]
                    self.chat_transcript_area.insert('end', f"새 파일 수신: {filename} (클릭하여 다운로드)\n")
                    self.chat_transcript_area.tag_add(filename, "end-2l", "end-1l")
                    self.chat_transcript_area.tag_bind(filename, "<Button-1>", lambda e, fname=filename: self.download_file(fname))
                else:
                    # 일반 메시지 처리
                    self.chat_transcript_area.insert('end', decoded_msg + '\n')
                self.chat_transcript_area.yview(END)
            except UnicodeDecodeError:
                # 파일 데이터가 아닌 경우 무시
                continue



if __name__ == "__main__":
    ip = '127.0.0.1'
    port = 2500
    ChatClient(ip, port)
    mainloop()

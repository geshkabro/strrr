import customtkinter as tk
from tkinter import messagebox
import numpy as np
import cv2
from mss import mss
import time
import websocket
import threading
import socket

def convert(x):
    c = x >> 8 & 255
    f = x & 255
    return (c, f)

def SendData(data, ws):
    chunk_size = 10500
    ws.send('1')
    for i in range(0, len(data), chunk_size):
        try:
            ws.send_binary(data[i:i + chunk_size])
        except (websocket.WebSocketConnectionClosedException, websocket.WebSocketException) as e:
            messagebox.showerror('Ошибка отправки данных', str(e))  # теперь ошибка будет выводиться правильно
            break  # выход из цикла при ошибке
    ws.send('0')

def start_streaming():
    threading.Thread(target=streaming_thread).start()

def streaming_thread():
    try:
        pc_width = int(pc_width_entry.get())
        pc_height = int(pc_height_entry.get())
        esp_url = esp_url_entry.get()
        esp_width = int(esp_width_entry.get())
        esp_height = int(esp_height_entry.get())
        bounding_box = {'top': 0, 'left': 0, 'width': pc_width, 'height': pc_height}
        sct = mss()
        frame = 0
        time_start = time.time()
        ws = websocket.WebSocket()
    except Exception as e:
        messagebox.showerror('Ошибка инициализации', str(e))
    else:
        try:
            ws.connect('ws://' + esp_url + ':81/')
        except (websocket.WebSocketConnectionClosedException, websocket.WebSocketException, socket.error) as e:
            messagebox.showerror('Ошибка подключения', str(e))
            return  # выход из функции при ошибке
        else:
            while True:  # заменил break на продолжение потока
                time_process = time.time()
                sct_img = sct.grab(bounding_box)
                timenow = time.time()
                frame += 1
                img = cv2.resize(np.array(sct_img), (esp_width, esp_height), interpolation=cv2.INTER_AREA)
                img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB)
                print('Time to Process frame: ', (time.time() - time_process) * 1000, 'ms')
                time_process = time.time()
                resizedimg = img.astype(np.uint16)
                B5 = (resizedimg[..., 0] >> 3).astype(np.uint16) << 11
                G6 = (resizedimg[..., 1] >> 2).astype(np.uint16) << 5
                R5 = (resizedimg[..., 2] >> 3).astype(np.uint16)
                RGB565 = R5 | G6 | B5
                RGB565_flat = RGB565.flatten()
                Eight_BitData = np.zeros(RGB565_flat.size * 2, dtype=np.uint8)
                Eight_BitData[::2] = RGB565_flat >> 8
                Eight_BitData[1::2] = RGB565_flat & 255
                print('Time to Convert frame: ', (time.time() - time_process) * 1000, 'ms')
                time_process = time.time()
                SendData(Eight_BitData, ws)
                print('Time to Send frame: ', (time.time() - time_process) * 1000, 'ms')
                cv2.imshow('Screen', img)
                if frame > 100:
                    print('FPS: ', frame / (timenow - time_start))
                    frame = 0
                    time_start = time.time()
                if cv2.waitKey(1) & 255 == 27:  # код выхода по клавише Esc
                    cv2.destroyAllWindows()
                    break  # теперь правильно завершается поток

root = tk.CTk()
root.title('Настройки WindowStreamer')
root.resizable(False, False)

tk.CTkLabel(root, text='Ширина экрана ПК:').grid(row=0, column=0, padx=10, pady=5)
pc_width_entry = tk.CTkEntry(root)
pc_width_entry.grid(row=0, column=1, padx=10, pady=5)
pc_width_entry.insert(0, '1920')

tk.CTkLabel(root, text='Высота экрана ПК:').grid(row=1, column=0, padx=10, pady=5)
pc_height_entry = tk.CTkEntry(root)
pc_height_entry.grid(row=1, column=1, padx=10, pady=5)
pc_height_entry.insert(0, '1080')

tk.CTkLabel(root, text='IP адрес:').grid(row=2, column=0, padx=10, pady=5)
esp_url_entry = tk.CTkEntry(root)
esp_url_entry.grid(row=2, column=1, padx=10, pady=5)
esp_url_entry.insert(0, '192.168.0.106')

tk.CTkLabel(root, text='Ширина экрана устройства:').grid(row=3, column=0, padx=10, pady=5)
esp_width_entry = tk.CTkEntry(root)
esp_width_entry.grid(row=3, column=1, padx=10, pady=5)
esp_width_entry.insert(0, '240')

tk.CTkLabel(root, text='Высота экрана устройства:').grid(row=4, column=0, padx=10, pady=5)
esp_height_entry = tk.CTkEntry(root)
esp_height_entry.grid(row=4, column=1, padx=10, pady=5)
esp_height_entry.insert(0, '135')

start_button = tk.CTkButton(root, text='Запустить стриминг!', command=start_streaming)
start_button.grid(row=5, columnspan=2, padx=10, pady=(10, 0))

exit_label = tk.CTkLabel(root, text='Нажмите Esc чтобы закрыть')
exit_label.grid(row=6, columnspan=2, padx=10, pady=10)

def close_window(event):
    root.destroy()

root.bind('<Escape>', close_window)

root.mainloop()

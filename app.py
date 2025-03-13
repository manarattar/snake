import eventlet
eventlet.monkey_patch()

import threading
import random
import base64
import numpy as np
import cv2
import pygame
import time  # For frame rate control

from flask import Flask, render_template
from flask_socketio import SocketIO

# Flask & SocketIO initialization
app = Flask(__name__)
socketio = SocketIO(app)

# Global variable to store direction
direction = "RIGHT"

def game_loop():
    global direction
    pygame.init()
    
    # Lower resolution: adjust these values as needed.
    width, height = 400, 300
    screen = pygame.Surface((width, height))
    clock = pygame.time.Clock()
    
    snake_block = 20
    snake_speed = 15  # You can lower this value to reduce frame frequency.
    
    x1, y1 = width // 2, height // 2
    x1_change, y1_change = 0, 0
    snake_list = []
    initial_length = 5
    for i in range(initial_length):
        snake_list.append([x1 - i * snake_block, y1])
    length_of_snake = initial_length
    
    foodx = random.randrange(0, width - snake_block, snake_block)
    foody = random.randrange(0, height - snake_block, snake_block)
    wall_list = [[random.randrange(0, width - snake_block, snake_block),
                  random.randrange(0, height - snake_block, snake_block)]]
    
    current_direction = direction
    last_emit_time = time.time()
    emit_interval = 1 / 15.0  # Emit at 15 FPS
    
    running = True
    while running:
        new_direction = direction
        if (current_direction == "LEFT" and new_direction == "RIGHT") or \
           (current_direction == "RIGHT" and new_direction == "LEFT") or \
           (current_direction == "UP" and new_direction == "DOWN") or \
           (current_direction == "DOWN" and new_direction == "UP"):
            new_direction = current_direction
        current_direction = new_direction
        
        if current_direction == "LEFT":
            x1_change, y1_change = -snake_block, 0
        elif current_direction == "RIGHT":
            x1_change, y1_change = snake_block, 0
        elif current_direction == "UP":
            x1_change, y1_change = 0, -snake_block
        elif current_direction == "DOWN":
            x1_change, y1_change = 0, snake_block

        x1 += x1_change
        y1 += y1_change

        if x1 >= width:
            x1 = 0
        elif x1 < 0:
            x1 = width - snake_block
        if y1 >= height:
            y1 = 0
        elif y1 < 0:
            y1 = height - snake_block

        snake_head = [x1, y1]
        snake_list.append(snake_head)
        if len(snake_list) > length_of_snake:
            del snake_list[0]

        for wall in wall_list:
            if x1 == wall[0] and y1 == wall[1]:
                running = False

        if x1 == foodx and y1 == foody:
            length_of_snake += 1
            foodx = random.randrange(0, width - snake_block, snake_block)
            foody = random.randrange(0, height - snake_block, snake_block)
            wall_list.append([random.randrange(0, width - snake_block, snake_block),
                              random.randrange(0, height - snake_block, snake_block)])

        screen.fill((0, 0, 0))
        pygame.draw.rect(screen, (255, 0, 0), (foodx, foody, snake_block, snake_block))
        for wall in wall_list:
            pygame.draw.rect(screen, (0, 0, 255), (wall[0], wall[1], snake_block, snake_block))
        for segment in snake_list:
            pygame.draw.rect(screen, (0, 255, 0), (segment[0], segment[1], snake_block, snake_block))

        # Emit the frame only if the emit interval has passed.
        current_time = time.time()
        if current_time - last_emit_time >= emit_interval:
            data = pygame.image.tostring(screen, 'RGB')
            img = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            ret, jpeg = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if ret:
                encoded = base64.b64encode(jpeg.tobytes()).decode('utf-8')
                socketio.emit('game_frame', {'image': encoded})
            last_emit_time = current_time

        clock.tick(snake_speed)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('direction')
def handle_direction(data):
    global direction
    new_dir = data.get('direction', "")
    if new_dir:
        direction = new_dir

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    game_thread = threading.Thread(target=game_loop)
    game_thread.daemon = True
    game_thread.start()
    socketio.run(app, host='0.0.0.0', port=port)

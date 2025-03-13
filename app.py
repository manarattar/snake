import threading
import random
import base64
import io
import numpy as np
import cv2
import pygame

from flask import Flask, render_template
from flask_socketio import SocketIO

# Initialize Flask and SocketIO.
app = Flask(__name__)
socketio = SocketIO(app)

# Global variable to store the latest direction command.
direction = "RIGHT"

# Global variable to hold the latest JPEG-encoded game frame.
game_frame = None

def game_loop():
    """Main game loop running on the server."""
    global direction, game_frame

    # Initialize Pygame with an off-screen surface.
    pygame.init()
    width, height = 600, 400
    # Instead of a window, we use a Surface.
    screen = pygame.Surface((width, height))
    clock = pygame.time.Clock()
    
    # Game parameters.
    snake_block = 20
    snake_speed = 15

    # Initialize snake state.
    x1, y1 = width // 2, height // 2
    x1_change, y1_change = 0, 0
    snake_list = []
    initial_length = 5
    for i in range(initial_length):
        snake_list.append([x1 - i * snake_block, y1])
    length_of_snake = initial_length

    # Initialize food and wall.
    foodx = random.randrange(0, width - snake_block, snake_block)
    foody = random.randrange(0, height - snake_block, snake_block)
    wall_list = [[random.randrange(0, width - snake_block, snake_block),
                  random.randrange(0, height - snake_block, snake_block)]]

    current_direction = direction

    running = True
    while running:
        # Apply the latest direction command (with a directional lock to avoid reversal).
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

        # Implement wrapping.
        if x1 >= width:
            x1 = 0
        elif x1 < 0:
            x1 = width - snake_block
        if y1 >= height:
            y1 = 0
        elif y1 < 0:
            y1 = height - snake_block

        # Update snake's body.
        snake_head = [x1, y1]
        snake_list.append(snake_head)
        if len(snake_list) > length_of_snake:
            del snake_list[0]

        # Check collision with any wall obstacle.
        for wall in wall_list:
            if x1 == wall[0] and y1 == wall[1]:
                running = False

        # Check if food is eaten.
        if x1 == foodx and y1 == foody:
            length_of_snake += 1
            foodx = random.randrange(0, width - snake_block, snake_block)
            foody = random.randrange(0, height - snake_block, snake_block)
            # Add a new wall obstacle.
            wall_list.append([random.randrange(0, width - snake_block, snake_block),
                              random.randrange(0, height - snake_block, snake_block)])

        # Draw game state on the off-screen surface.
        screen.fill((0, 0, 0))
        pygame.draw.rect(screen, (255, 0, 0), (foodx, foody, snake_block, snake_block))
        for wall in wall_list:
            pygame.draw.rect(screen, (0, 0, 255), (wall[0], wall[1], snake_block, snake_block))
        for segment in snake_list:
            pygame.draw.rect(screen, (0, 255, 0), (segment[0], segment[1], snake_block, snake_block))

        # Convert the Pygame surface to an image that can be sent to clients.
        data = pygame.image.tostring(screen, 'RGB')
        img = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))
        # Convert from RGB to BGR for JPEG encoding.
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        ret, jpeg = cv2.imencode('.jpg', img)
        if ret:
            game_frame = jpeg.tobytes()
            # Emit the frame to connected clients (encoded in base64 for transport).
            socketio.emit('game_frame', {
                'image': base64.b64encode(game_frame).decode('utf-8')
            })
        
        clock.tick(snake_speed)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('direction')
def handle_direction(data):
    global direction
    # Update the global direction based on client input.
    new_dir = data.get('direction', "")
    if new_dir:
        direction = new_dir

if __name__ == '__main__':
    # Start the game loop in a separate thread.
    game_thread = threading.Thread(target=game_loop)
    game_thread.daemon = True
    game_thread.start()
    # Run the Flask application.
    socketio.run(app, host='0.0.0.0', port=5000)

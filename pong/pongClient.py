# =================================================================================================
# Contributing Authors:	    Example Author
# Email Addresses:          example@uky.edu
# Date:                     November 6, 2025
# Purpose:                  Client implementation for the multiplayer Pong game. This client handles
#                          user input, displays the game state, and communicates with the server.
# =================================================================================================

import pygame
import tkinter as tk
import sys
import socket
import json
import os
from typing import Optional, Dict, Any, Tuple

from assets.code.helperCode import *

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Author:  Example Author
# Purpose: Main game loop that handles game display and network communication
# Pre:     Connection to server established, screen dimensions and paddle side assigned
# Post:    Game runs until completion or user exits
def playGame(screenWidth: int, screenHeight: int, playerPaddle: str, client: socket.socket) -> None:
    """Main game loop handling both game logic and network communication."""
    
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Declare score variables that will be updated from network
    global lScore, rScore
    
    # Constants
    WHITE = (255,255,255)
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font(os.path.join(SCRIPT_DIR, "assets", "fonts", "pong-score.ttf"), 32)
    winFont = pygame.font.Font(os.path.join(SCRIPT_DIR, "assets", "fonts", "visitor.ttf"), 48)
    pointSound = pygame.mixer.Sound(os.path.join(SCRIPT_DIR, "assets", "sounds", "point.wav"))
    bounceSound = pygame.mixer.Sound(os.path.join(SCRIPT_DIR, "assets", "sounds", "bounce.wav"))

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    winMessage = pygame.Rect(0,0,0,0)
    topWall = pygame.Rect(-10,0,screenWidth+20, 10)
    bottomWall = pygame.Rect(-10, screenHeight-10, screenWidth+20, 10)
    centerLine = []
    for i in range(0, screenHeight, 10):
        centerLine.append(pygame.Rect((screenWidth/2)-5,i,5,5))

    # Paddle properties and init
    paddleHeight = 50
    paddleWidth = 10
    paddleStartPosY = (screenHeight/2)-(paddleHeight/2)
    leftPaddle = Paddle(pygame.Rect(10,paddleStartPosY, paddleWidth, paddleHeight))
    rightPaddle = Paddle(pygame.Rect(screenWidth-20, paddleStartPosY, paddleWidth, paddleHeight))

    ball = Ball(pygame.Rect(screenWidth/2, screenHeight/2, 5, 5), -5, 0)

    if playerPaddle == "left":
        opponentPaddleObj = rightPaddle
        playerPaddleObj = leftPaddle
    else:
        opponentPaddleObj = leftPaddle
        playerPaddleObj = rightPaddle

    lScore = 0
    rScore = 0

    sync = 0

    while True:
        # Wiping the screen
        screen.fill((0,0,0))

        # Getting keypress events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    playerPaddleObj.moving = "down"

                elif event.key == pygame.K_UP:
                    playerPaddleObj.moving = "up"

            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""

        # =========================================================================================
        # Send game state update to server
        try:
            # Prepare update for server
            game_update = {
                "paddle_pos": playerPaddleObj.rect.y,
                "paddle_moving": playerPaddleObj.moving,
                "sync": sync
            }
            
            # Send update to server
            client.send(json.dumps(game_update).encode())
            
            # Receive server response
            data = client.recv(1024).decode()
            server_state = json.loads(data)
            
            # Update opponent paddle position
            opponentPaddleObj.rect.y = server_state["paddles"]["right" if playerPaddle == "left" else "left"]["position"]
            opponentPaddleObj.moving = server_state["paddles"]["right" if playerPaddle == "left" else "left"]["moving"]
            
            # Update ball position if we're behind
            if server_state["sync"] > sync:
                ball.rect.x = server_state["ball"]["x"]
                ball.rect.y = server_state["ball"]["y"]
                ball.xVel = server_state["ball"]["x_vel"]
                ball.yVel = server_state["ball"]["y_vel"]
                sync = server_state["sync"]
                
                # Update scores from server state
                if "scores" in server_state:
                    if lScore != server_state["scores"]["left"] or rScore != server_state["scores"]["right"]:
                        lScore = server_state["scores"]["left"]
                        rScore = server_state["scores"]["right"]
                        pointSound.play()
                    
        except Exception as e:
            print(f"Network error: {str(e)}")
            pygame.quit()
            sys.exit()
        # =========================================================================================

        # Update the player paddle and opponent paddle's location on the screen
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            if paddle.moving == "down":
                if paddle.rect.bottomleft[1] < screenHeight-10:
                    paddle.rect.y += paddle.speed
            elif paddle.moving == "up":
                if paddle.rect.topleft[1] > 10:
                    paddle.rect.y -= paddle.speed

        # If the game is over, display the win message
        if lScore > 4 or rScore > 4:
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)
        else:

            # ==== Ball Logic =====================================================================
            ball.updatePos()

            # If the ball makes it past the edge of the screen, update score, etc.
            if ball.rect.x > screenWidth:
                lScore += 1
                pointSound.play()
                ball.reset(nowGoing="left")
            elif ball.rect.x < 0:
                rScore += 1
                pointSound.play()
                ball.reset(nowGoing="right")
                
            # If the ball hits a paddle
            if ball.rect.colliderect(playerPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(playerPaddleObj.rect.center[1])
            elif ball.rect.colliderect(opponentPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(opponentPaddleObj.rect.center[1])
                
            # If the ball hits a wall
            if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                bounceSound.play()
                ball.hitWall()
            
            pygame.draw.rect(screen, WHITE, ball)
            # ==== End Ball Logic =================================================================

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        
        # Drawing the player's new location
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle)

        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
        
        # Update the entire display instead of just specific rectangles to prevent trails
        pygame.display.flip()
        clock.tick(60)
        
        # This number should be synchronized between you and your opponent.  If your number is larger
        # then you are ahead of them in time, if theirs is larger, they are ahead of you, and you need to
        # catch up (use their info)
        sync += 1
        # =========================================================================================
        # Send your server update here at the end of the game loop to sync your game with your
        # opponent's game

        # =========================================================================================




# Author:  Example Author
# Purpose: Connect to the Pong game server and start the game
# Pre:     Valid IP address and port number provided
# Post:    Client connects to server and starts game, or shows error
def joinServer(ip: str, port: str, errorLabel: tk.Label, app: tk.Tk) -> None:
    """
    Connect to the game server and initialize the game with received configuration.
    """
    try:
        # Create a socket and connect to the server
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((ip, int(port)))
        
        # Get initial configuration from server
        data = client.recv(1024).decode()
        config = json.loads(data)
        
        # Extract configuration
        screenWidth = config["screen_width"]
        screenHeight = config["screen_height"]
        playerPaddle = config["paddle"]
        
        # Update UI to show connection success
        errorLabel.config(text=f"Connected successfully! You are the {playerPaddle} paddle.")
        errorLabel.update()
        
        # Start the game
        app.withdraw()     # Hide the window
        playGame(screenWidth, screenHeight, playerPaddle, client)
        app.quit()         # Kill the window
        
    except Exception as e:
        # Show error message to user
        errorLabel.config(text=f"Error connecting to server: {str(e)}")
        errorLabel.update()
        
        # Close socket if connection failed
        try:
            client.close()
        except:
            pass


# This displays the opening screen, you don't need to edit this (but may if you like)
def startScreen():
    app = tk.Tk()
    app.title("Server Info")

    image = tk.PhotoImage(file=os.path.join(SCRIPT_DIR, "assets", "images", "logo.png"))

    titleLabel = tk.Label(image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    ipLabel = tk.Label(text="Server IP:")
    ipLabel.grid(column=0, row=1, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.grid(column=1, row=1)

    portLabel = tk.Label(text="Server Port:")
    portLabel.grid(column=0, row=2, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.grid(column=1, row=2)

    errorLabel = tk.Label(text="")
    errorLabel.grid(column=0, row=4, columnspan=2)

    joinButton = tk.Button(text="Join", command=lambda: joinServer(ipEntry.get(), portEntry.get(), errorLabel, app))
    joinButton.grid(column=0, row=3, columnspan=2)

    app.mainloop()

if __name__ == "__main__":
    startScreen()
    
    # Debug/demo line removed - we want to use the proper connection flow
    # through startScreen() and joinServer()
# =================================================================================================
# Contributing Authors:	    Ghaleb Abualsoud, Mustafa Akhtar
# Email Addresses:          gab230@uky.edu, maak222@uky.edu
# Date:                     November 6, 2025
# Purpose:                  Client implementation for the multiplayer Pong game. This client handles
#                          user input, displays the game state, and communicates with the server.
# =================================================================================================

import pygame
import tkinter as tk
import sys
import socket
import threading
import json
import traceback
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
    # UI font for short text (uses a font that includes letters/symbols)
    uiFont = pygame.font.Font(os.path.join(SCRIPT_DIR, "assets", "fonts", "visitor.ttf"), 24)
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

    # Shared networking state between main thread (render/input) and network thread
    net_state = {
        "send": {"paddle_pos": playerPaddleObj.rect.y, "paddle_moving": playerPaddleObj.moving, "sync": sync},
        "recv": None,
        "last_server_sync": -1,
        "lock": threading.Lock(),
        "running": True,
        # rematch_request: None = no vote yet, True = requested
        "rematch_request": None
    }
    # local UI state
    game_over_local = False
    winner_local: Optional[str] = None
    rematch_requested_local = False

    def network_thread(sock: socket.socket, state: dict) -> None:
        buf = ""
        while state["running"]:
            # prepare and send latest paddle state
            with state["lock"]:
                to_send = state["send"].copy()
                # include rematch request flag only if player explicitly voted
                if state.get("rematch_request") is not None:
                    to_send["rematch"] = state.get("rematch_request")
            try:
                sock.send((json.dumps(to_send) + "\n").encode())
            except socket.timeout:
                # skip this send; try again next tick
                pass
            except ConnectionResetError:
                print("Network thread: connection reset by peer")
                state["running"] = False
                break
            except Exception as e:
                print(f"Network thread send exception: {e}")
                traceback.print_exc()
                # don't stop immediately; allow transient errors to recover
                try:
                    threading.Event().wait(0.05)
                except Exception:
                    pass

            # read any available data (non-blocking via timeout)
            try:
                data = sock.recv(8192).decode()
            except socket.timeout:
                data = ""
            except ConnectionResetError:
                print("Network thread: connection reset by peer (recv)")
                state["running"] = False
                break
            except Exception as e:
                print(f"Network thread recv exception: {e}")
                traceback.print_exc()
                try:
                    threading.Event().wait(0.05)
                except Exception:
                    pass
                continue

            if data:
                buf += data
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if not line:
                        continue
                    try:
                        server_state = json.loads(line)
                    except Exception:
                        continue
                    with state["lock"]:
                        state["recv"] = server_state
                        try:
                            state["last_server_sync"] = int(server_state.get("sync", state.get("last_server_sync", -1)))
                        except Exception:
                            pass
                    print(f"Network thread: received server sync={state.get('last_server_sync')} ball={server_state.get('ball')}")

            # sleep a bit to avoid tight loop; match ~30-60Hz
            time_sleep = 1.0 / 60.0
            try:
                threading.Event().wait(time_sleep)
            except Exception:
                pass

    # start network thread
    net_thread = threading.Thread(target=network_thread, args=(client, net_state), daemon=True)
    net_thread.start()

    recv_buffer = ""

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
                elif event.key == pygame.K_r:
                    # request rematch when game over
                    if game_over_local:
                        with net_state["lock"]:
                            net_state["rematch_request"] = True
                        rematch_requested_local = True
                elif event.key == pygame.K_q:
                    # quit
                    pygame.quit()
                    sys.exit()

            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""

        # =========================================================================================
        # Update shared send state for network thread
        with net_state["lock"]:
            net_state["send"]["paddle_pos"] = playerPaddleObj.rect.y
            net_state["send"]["paddle_moving"] = playerPaddleObj.moving
            net_state["send"]["sync"] = sync

        # Read latest server state (if any) provided by network thread and apply only when
        # the server sync counter has advanced since last applied state.
        server_state = None
        server_sync = -1
        with net_state["lock"]:
            server_state = net_state.get("recv")
            server_sync = net_state.get("last_server_sync", -1)

        if server_state is not None and server_sync != -1:
            # apply only if this is a new server update
            if server_sync != sync:
                try:
                    prev_game_over = game_over_local
                    opponent_key = "right" if playerPaddle == "left" else "left"
                    opponentPaddleObj.rect.y = server_state["paddles"][opponent_key]["position"]
                    opponentPaddleObj.moving = server_state["paddles"][opponent_key]["moving"]

                    # Update ball
                    ball.rect.x = server_state["ball"]["x"]
                    ball.rect.y = server_state["ball"]["y"]
                    ball.xVel = server_state["ball"].get("x_vel", ball.xVel)
                    ball.yVel = server_state["ball"].get("y_vel", ball.yVel)

                    # Update scores
                    if "scores" in server_state:
                        if lScore != server_state["scores"]["left"] or rScore != server_state["scores"]["right"]:
                            lScore = server_state["scores"]["left"]
                            rScore = server_state["scores"]["right"]
                            pointSound.play()

                    # set local sync to server sync so we don't reapply
                    sync = server_sync
                    # mark the server update as consumed so we don't reapply the same state
                    with net_state["lock"]:
                        net_state["last_server_sync"] = sync
                        net_state["recv"] = None
                    # capture game over / winner info for UI
                    game_over_local = bool(server_state.get("game_over", False))
                    winner_local = server_state.get("winner")
                    # if rematch was requested, show feedback
                    if rematch_requested_local:
                        print("Main: rematch requested; waiting for other player...")

                    # If we transitioned from game_over -> not game_over, the server restarted the game.
                    # Clear any local rematch request so we don't keep voting automatically for subsequent matches.
                    if prev_game_over and not game_over_local:
                        rematch_requested_local = False
                        with net_state["lock"]:
                            net_state["rematch_request"] = None

                    print(f"Main: applied server sync={sync} ball=({ball.rect.x},{ball.rect.y}) scores=({lScore},{rScore}) game_over={game_over_local} winner={winner_local}")
                except Exception:
                    # malformed server data; ignore this frame
                    pass
        # =========================================================================================

        # Update the player paddle and opponent paddle's location on the screen
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            if paddle.moving == "down":
                if paddle.rect.bottomleft[1] < screenHeight-10:
                    paddle.rect.y += paddle.speed
            elif paddle.moving == "up":
                if paddle.rect.topleft[1] > 10:
                    paddle.rect.y -= paddle.speed

        # If the game is over, display the win message + rematch options
        if game_over_local:
            if winner_local is not None:
                winText = "You Win!" if (winner_local == playerPaddle) else "You Lose!"
            else:
                winText = "Game Over"
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2 - 24)
            winMessage = screen.blit(textSurface, textRect)

            # rematch instructions
            remText = "Press R to request rematch, Q to quit"
            remSurface = uiFont.render(remText, False, WHITE, (0,0,0))
            remRect = remSurface.get_rect()
            remRect.center = ((screenWidth/2), screenHeight/2 + 24)
            screen.blit(remSurface, remRect)
        else:

            # Server authoritative ball: render only. Ball state is received from server
            # when `server_state["sync"]` advances; between updates we render the
            # last known ball position from the server.
            pygame.draw.rect(screen, WHITE, ball)

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
        # Use a short timeout so the Pygame main loop does not block waiting for network I/O
        # increase slightly to reduce spurious timeouts during bursts
        client.settimeout(0.1)
        
        # Get initial configuration from server (newline-delimited JSON)
        recv_buf = ""
        while True:
            try:
                chunk = client.recv(4096).decode()
            except socket.timeout:
                continue
            if not chunk:
                raise ConnectionError("Server closed connection before sending config")
            recv_buf += chunk
            if "\n" in recv_buf:
                line, _ = recv_buf.split("\n", 1)
                config = json.loads(line)
                break
        
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
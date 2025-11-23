# =================================================================================================
# Contributing Authors:	    Ghaleb Abualsoud, Mustafa Akhtar
# Email Addresses:          gab230@uky.edu, maak222@uky.edu
# Date:                     November 6, 2025
# Purpose:                  Server implementation for the multiplayer Pong game. This server handles
#                          multiple client connections, manages game state, and coordinates
#                          communication between players.
# =================================================================================================

import socket
import threading
import json
import time
import traceback
from typing import Dict, List, Optional, Tuple, Any

class PongServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 12345) -> None:
        """
        # Author:  Example Author
        # Purpose: Initialize the Pong game server
        # Pre:     Port specified should be available for binding
        # Post:    Server is initialized with empty game state
        """
        self.host: str = host
        self.port: int = port
        self.server: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(2)
        self.lock = threading.Lock()
        self.screen_width = 640
        self.screen_height = 480
        self.paddle_width = 10
        self.paddle_height = 50
        self.win_score = 5
        self.game_over: bool = False
        self.winner: Optional[str] = None
        self.rematch_votes: Dict[str, Optional[bool]] = {"left": None, "right": None}
        self.rematch_wait_seconds = 30
        self.server_shutting_down = False
        
        # Game state
        self.clients: List[socket.socket] = []
        # Track consecutive send failures per client to avoid dropping clients on a
        # single transient timeout.
        self.client_failures: Dict[socket.socket, int] = {}
        self.paddles: Dict[str, Dict[str, Any]] = {
            "left": {"position": 240, "moving": ""}, 
            "right": {"position": 240, "moving": ""}
        }
        self.ball: Dict[str, Any] = {"x": 320, "y": 240, "x_vel": -5, "y_vel": 0}
        self.scores: Dict[str, int] = {"left": 0, "right": 0}
        self.sync_counter: int = 0
        
        print(f"Server started on {host}:{port}")

    def handle_client(self, client_socket: socket.socket, player_side: str) -> None:
        """
        # Author:  Example Author
        # Purpose: Handle communication with a connected client
        # Pre:     Client should be successfully connected and player_side assigned
        # Post:    Maintains continuous communication with client until disconnect
        """
        recv_buffer = ""
        while True:
            try:
                try:
                    data = client_socket.recv(4096).decode()
                except (socket.timeout, TimeoutError):
                    # No data available this iteration; continue waiting without
                    # treating this as a fatal error.
                    continue
                except OSError as e:
                    # Socket closed or invalid (e.g. closed by shutdown from
                    # another thread). If server is shutting down, exit quietly.
                    if getattr(self, "server_shutting_down", False):
                        break
                    print(f"OSError in recv from {player_side}: {e}")
                    traceback.print_exc()
                    break

                if not data:
                    break

                recv_buffer += data

                # Process all complete JSON messages (newline-delimited)
                while "\n" in recv_buffer:
                    line, recv_buffer = recv_buffer.split("\n", 1)
                    if not line:
                        continue
                    try:
                        client_update = json.loads(line)
                    except Exception as e:
                        print(f"JSON decode error from {player_side}: {e}")
                        continue

                    # Update paddle state from client
                    with self.lock:
                        self.paddles[player_side]["position"] = client_update.get("paddle_pos", self.paddles[player_side]["position"])
                        self.paddles[player_side]["moving"] = client_update.get("paddle_moving", self.paddles[player_side]["moving"])
                    # Handle rematch vote if present
                    if "rematch" in client_update:
                        # Only accept rematch votes after the game is over
                        with self.lock:
                            if self.game_over:
                                self.rematch_votes[player_side] = bool(client_update.get("rematch", False))
                                print(f"Rematch vote from {player_side}: {self.rematch_votes[player_side]}")
                            else:
                                # ignore rematch requests during active game
                                pass

                    game_state = {
                        "ball": self.ball,
                        "paddles": self.paddles,
                        "scores": self.scores,
                        "sync": self.sync_counter
                    }

                    # Do not send authoritative game state from the client handler.
                    # Broadcasting is handled centrally in `game_loop` to avoid
                    # concurrent sends on the same socket which can cause timeouts
                    # and race conditions. The handler only updates paddle state.

            except Exception as e:
                # If server is shutting down, suppress socket errors during close
                if getattr(self, "server_shutting_down", False):
                    break
                print(f"Error handling client {player_side}: {str(e)}")
                traceback.print_exc()
                break
        
        with self.lock:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
        client_socket.close()

    def handle_initial_connection(self, client_socket: socket.socket) -> str:
        """
        # Author:  Example Author
        # Purpose: Handle initial client connection and assign player side
        # Pre:     Client socket should be connected and less than 2 players connected
        # Post:    Client is assigned a side and receives initial game configuration
        """
        player_side = "left" if len(self.clients) == 0 else "right"
        config = {
            "screen_width": 640,
            "screen_height": 480,
            "paddle": player_side
        }
        client_socket.send((json.dumps(config) + "\n").encode())
        return player_side

    def reset_ball(self, nowGoing: str = "left") -> None:
        # reset_ball is expected to be called while the caller holds `self.lock`
        # to avoid deadlocks. Do not acquire the lock here.
        self.ball["x"] = self.screen_width // 2
        self.ball["y"] = self.screen_height // 2
        speed = 5
        if nowGoing == "left":
            self.ball["x_vel"] = -speed
        else:
            self.ball["x_vel"] = speed
        self.ball["y_vel"] = 0

    def broadcast_state(self) -> None:
        """Send current authoritative game state to all connected clients."""
        # Snapshot authoritative state under lock to ensure consistency
        with self.lock:
            # only include rematch_votes when game is over
            rematch_info = dict(self.rematch_votes) if self.game_over else None
            game_state = {
                "ball": dict(self.ball),
                "paddles": {k: dict(v) for k, v in self.paddles.items()},
                "scores": dict(self.scores),
                "sync": int(self.sync_counter),
                "game_over": bool(self.game_over),
                "winner": self.winner,
                "rematch_votes": rematch_info
            }
        dead_clients = []
        # Iterate over a snapshot of the client list while holding the lock
        with self.lock:
            clients_snapshot = list(self.clients)

        for c in clients_snapshot:
                try:
                    c.send((json.dumps(game_state) + "\n").encode())
                    # reset failure count on success
                    if c in self.client_failures:
                        self.client_failures[c] = 0
                except Exception as e:
                    # During server shutdown we often see socket errors as
                    # handler threads are exiting and sockets are being closed.
                    # Suppress noisy tracebacks in that case.
                    if getattr(self, "server_shutting_down", False):
                        self.client_failures[c] = self.client_failures.get(c, 0) + 1
                        continue
                    print(f"Error broadcasting to client: {e}")
                    traceback.print_exc()
                    self.client_failures[c] = self.client_failures.get(c, 0) + 1
                # Only mark as dead after several consecutive failures
                if self.client_failures.get(c, 0) > 5:
                    dead_clients.append(c)

        if dead_clients:
            with self.lock:
                for d in dead_clients:
                    if d in self.clients:
                        try:
                            d.close()
                        except:
                            pass
                        self.clients.remove(d)
                        if d in self.client_failures:
                            del self.client_failures[d]

    def game_loop(self) -> None:
        """Authoritative server game loop: moves the ball, checks collisions, updates scores."""
        # lower tick rate to reduce network/broadcast pressure
        tick_rate = 30.0
        tick_delay = 1.0 / tick_rate
        while True:
            start = time.time()
            with self.lock:
                # Move ball
                self.ball["x"] += self.ball["x_vel"]
                self.ball["y"] += self.ball["y_vel"]

                # Top/bottom wall collision
                if self.ball["y"] <= 0:
                    self.ball["y"] = 0
                    self.ball["y_vel"] = -self.ball["y_vel"]
                    print(f"Bounce top: y={self.ball['y']} y_vel={self.ball['y_vel']}")
                elif self.ball["y"] >= self.screen_height:
                    self.ball["y"] = self.screen_height
                    self.ball["y_vel"] = -self.ball["y_vel"]
                    print(f"Bounce bottom: y={self.ball['y']} y_vel={self.ball['y_vel']}")

                # Paddle collision rectangles
                left_rect = {
                    "x": 10,
                    "y": self.paddles["left"]["position"],
                    "w": self.paddle_width,
                    "h": self.paddle_height
                }
                right_rect = {
                    "x": self.screen_width - 20,
                    "y": self.paddles["right"]["position"],
                    "w": self.paddle_width,
                    "h": self.paddle_height
                }

                bx = self.ball["x"]
                by = self.ball["y"]

                # Check left paddle collision
                if (left_rect["x"] <= bx <= left_rect["x"] + left_rect["w"] and
                        left_rect["y"] <= by <= left_rect["y"] + left_rect["h"] and
                        self.ball["x_vel"] < 0):
                    self.ball["x_vel"] = -self.ball["x_vel"]
                    offset = (by - (left_rect["y"] + left_rect["h"]/2)) / (left_rect["h"]/2)
                    self.ball["y_vel"] = int(offset * 5)

                # Check right paddle collision
                if (right_rect["x"] <= bx <= right_rect["x"] + right_rect["w"] and
                        right_rect["y"] <= by <= right_rect["y"] + right_rect["h"] and
                        self.ball["x_vel"] > 0):
                    self.ball["x_vel"] = -self.ball["x_vel"]
                    offset = (by - (right_rect["y"] + right_rect["h"]/2)) / (right_rect["h"]/2)
                    self.ball["y_vel"] = int(offset * 5)

                # Score checks
                if self.ball["x"] > self.screen_width:
                    self.scores["left"] += 1
                    print(f"Score left: {self.scores}")
                    # check for win
                    if self.scores["left"] >= self.win_score:
                        self.game_over = True
                        self.winner = "left"
                        # center ball and prepare to broadcast final state
                        self.reset_ball(nowGoing="right")
                    else:
                        self.reset_ball(nowGoing="right")
                elif self.ball["x"] < 0:
                    self.scores["right"] += 1
                    print(f"Score right: {self.scores}")
                    # check for win
                    if self.scores["right"] >= self.win_score:
                        self.game_over = True
                        self.winner = "right"
                        self.reset_ball(nowGoing="left")
                    else:
                        self.reset_ball(nowGoing="left")

                self.sync_counter += 1

            # Broadcast authoritative state to clients
            self.broadcast_state()

            # If game is over, enter rematch/waiting state
            if self.game_over:
                print(f"Game over! Winner={self.winner}. Waiting for rematch votes...")
                # reset rematch votes
                with self.lock:
                    self.rematch_votes = {"left": None, "right": None}

                # Broadcast until rematch decision or timeout
                deadline = time.time() + self.rematch_wait_seconds
                while time.time() < deadline and not self.server_shutting_down:
                    self.broadcast_state()
                    # check votes
                    with self.lock:
                        left_vote = self.rematch_votes.get("left")
                        right_vote = self.rematch_votes.get("right")
                    # both agreed -> restart immediately
                    if left_vote is True and right_vote is True:
                        print("Both players requested rematch. Restarting game.")
                        with self.lock:
                            self.scores = {"left": 0, "right": 0}
                            self.sync_counter = 0
                            self.game_over = False
                            self.winner = None
                            self.reset_ball(nowGoing="left")
                            # clear rematch votes so next match doesn't inherit votes
                            self.rematch_votes = {"left": None, "right": None}
                        break
                    # both voted and at least one declined -> shut down server
                    if (left_vote is not None and right_vote is not None) and (left_vote is False or right_vote is False):
                        print("Rematch declined by one or both players. Shutting down server.")
                        self.server_shutting_down = True
                        break
                    time.sleep(0.5)

                # If the inner rematch loop exited because we restarted the game
                # (i.e. `self.game_over` was cleared), skip the shutdown/timeout
                # logic and continue the main game loop.
                if not self.game_over:
                    # game was restarted via rematch; continue main loop
                    continue

                # deadline reached or shutdown requested
                if self.server_shutting_down:
                    with self.lock:
                        clients_copy = list(self.clients)
                    # attempt graceful shutdown: shutdown sockets first so handler threads unblock
                    for c in clients_copy:
                        try:
                            c.shutdown(socket.SHUT_RDWR)
                        except Exception:
                            pass
                        try:
                            c.close()
                        except Exception:
                            pass
                    with self.lock:
                        self.clients.clear()
                    return
                else:
                    # deadline expired: treat any None as decline
                    with self.lock:
                        left_vote = self.rematch_votes.get("left")
                        right_vote = self.rematch_votes.get("right")
                    if left_vote is True and right_vote is True:
                        print("Both players requested rematch at deadline. Restarting game.")
                        with self.lock:
                            self.scores = {"left": 0, "right": 0}
                            self.sync_counter = 0
                            self.game_over = False
                            self.winner = None
                            self.reset_ball(nowGoing="left")
                            self.rematch_votes = {"left": None, "right": None}
                    else:
                        print("Rematch timeout or incomplete votes — shutting down server.")
                        with self.lock:
                            clients_copy = list(self.clients)
                        for c in clients_copy:
                            try:
                                c.shutdown(socket.SHUT_RDWR)
                            except Exception:
                                pass
                            try:
                                c.close()
                            except Exception:
                                pass
                        with self.lock:
                            self.clients.clear()
                        return
            # Sleep to maintain tick rate
            elapsed = time.time() - start
            to_sleep = tick_delay - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)

    def start(self) -> None:
        """
        # Author:  Example Author
        # Purpose: Start the server and begin accepting client connections
        # Pre:     Server should be initialized and bound to port
        # Post:    Server runs indefinitely, handling client connections
        """
        print("Waiting for players to connect...")

        try:
            while len(self.clients) < 2:
                client_socket, addr = self.server.accept()
                print(f"Connection from {addr}")

                # Make client sockets use a short timeout so broadcast/send won't block
                client_socket.settimeout(0.1)

                player_side = self.handle_initial_connection(client_socket)
                with self.lock:
                    self.clients.append(client_socket)

                thread = threading.Thread(target=self.handle_client,
                                          args=(client_socket, player_side))
                thread.daemon = True
                thread.start()

                print(f"Player {player_side} connected")

            print("Both players connected! Game starting...")

            # Start the authoritative game loop in its own thread
            game_thread = threading.Thread(target=self.game_loop)
            game_thread.daemon = True
            game_thread.start()

            # Keep server running to service clients
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nServer shutting down...")
            with self.lock:
                for client in list(self.clients):
                    try:
                        client.close()
                    except:
                        pass
                self.server.close()

if __name__ == "__main__":
    server = PongServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        with server.lock:
            for client in list(server.clients):
                try:
                    client.close()
                except:
                    pass
        try:
            server.server.close()
        except:
            pass
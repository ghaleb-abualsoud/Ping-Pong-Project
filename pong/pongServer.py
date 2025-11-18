# =================================================================================================
# Contributing Authors:	    Example Author
# Email Addresses:          example@uky.edu
# Date:                     November 6, 2025
# Purpose:                  Server implementation for the multiplayer Pong game. This server handles
#                          multiple client connections, manages game state, and coordinates
#                          communication between players.
# =================================================================================================

import socket
import threading
import json
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
        
        # Game state
        self.clients: List[socket.socket] = []
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
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                
                client_update = json.loads(data)
                self.paddles[player_side]["position"] = client_update["paddle_pos"]
                self.paddles[player_side]["moving"] = client_update["paddle_moving"]
                
                game_state = {
                    "ball": self.ball,
                    "paddles": self.paddles,
                    "scores": self.scores,
                    "sync": self.sync_counter
                }
                
                client_socket.send(json.dumps(game_state).encode())
                self.sync_counter += 1
                
            except Exception as e:
                print(f"Error handling client {player_side}: {str(e)}")
                break
        
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
        client_socket.send(json.dumps(config).encode())
        return player_side

    def start(self) -> None:
        """
        # Author:  Example Author
        # Purpose: Start the server and begin accepting client connections
        # Pre:     Server should be initialized and bound to port
        # Post:    Server runs indefinitely, handling client connections
        """
        print("Waiting for players to connect...")
        
        while len(self.clients) < 2:
            client_socket, addr = self.server.accept()
            print(f"Connection from {addr}")
            
            player_side = self.handle_initial_connection(client_socket)
            self.clients.append(client_socket)
            
            thread = threading.Thread(target=self.handle_client, 
                                   args=(client_socket, player_side))
            thread.daemon = True
            thread.start()
            
            print(f"Player {player_side} connected")
            
        print("Both players connected! Game starting...")

if __name__ == "__main__":
    server = PongServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        for client in server.clients:
            client.close()
        server.server.close()
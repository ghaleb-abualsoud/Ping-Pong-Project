# Multiplayer Pong Game
https://github.com/ghaleb-abualsoud/Ping-Pong-Project

A networked implementation of the classic Pong game using Python and Pygame, featuring client-server architecture for multiplayer gameplay.

## Requirements

- Python 3.7 or higher
- Pygame 2.5.2
- Network connectivity between server and clients

## Installation

1. Clone this repository or extract the provided zip file

   (Might not have to do this) 
3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Game

### Starting the Server

1. Navigate to the pong directory:
```bash
cd pong
```
2. Run the server:
```bash
python pongServer.py
```
The server will start and display its IP address and port number (default: 12345).

### Starting the Clients

1. Open a new terminal for each client (you need two players)
2. Navigate to the pong directory:
```bash
cd pong
```
3. Run the client:
```bash
python pongClient.py
```
3. Enter the server's IP address and port number in the connection window
4. Wait for both players to connect

## How to Play

- Use the UP and DOWN arrow keys to move your paddle
- The left player serves first
- Score points by getting the ball past your opponent's paddle
- First player to score 5 points wins

## Network Requirements

- The server must be reachable by both clients
- If playing across the internet (not on the same network):
  - The server must have port 12345 open and forwarded
  - Clients must use the server's public IP address
- For LAN play:
  - Use the server's local IP address
  - No port forwarding required

## Troubleshooting

1. Connection Issues:
   - Verify the server is running
   - Check the IP address and port
   - Ensure no firewall is blocking the connection

2. Game Synchronization Issues:
   - The game includes automatic sync mechanisms
   - If severe desync occurs, restart both clients

## Implementation Details

- The game uses TCP sockets for reliable communication
- Threading is implemented for handling multiple clients
- Game state synchronization is managed through a sync counter
- All game logic is processed on the server side

## Known Limitations

- Currently supports exactly two players
- No reconnection mechanism if a client disconnects
- Server must be restarted for a new game

## Server Behavior & Rematch

- Server is authoritative: all physics (ball movement, collisions, scoring) are computed on the server. Clients render the authoritative state and only send paddle inputs.
- Rematch flow: after a player reaches the win score, the server enters a rematch voting period (default 30 seconds). Both players must press `R` to agree to a rematch. If both agree the game restarts; if either player declines or the deadline expires the server will shut down. Rematch votes are cleared when a rematch restarts.

## Running & Testing Notes

- Run the server from the `pong` folder to ensure asset paths resolve correctly:
```powershell
cd pong
python pongServer.py
```
- Local test: open two terminals, run `python pongClient.py` in each, and connect both clients to `127.0.0.1:12345`.
- To exercise rematch behavior: play until one side wins, then press `R` on each client to vote for a rematch; check the server console for `Rematch vote` and `Game over` log lines.

## Troubleshooting Additions

- Garbled or symbol text for rematch instructions: ensure the fonts in `assets/fonts` are present and you're running the client from the `pong` directory (the client uses `SCRIPT_DIR` to find assets). The client now uses a UI font that supports letters.
- If the Pygame window becomes "Not Responding", ensure the client is running the network thread (it does network I/O off the main thread) and that sockets are not blocked; restarting the client usually resolves transient issues.
- If you see JSON parse errors like `Extra data`, confirm both client and server are up-to-date and using newline-delimited JSON framing (current code sends newline-terminated JSON and buffers on receive).

## Development & Changelog


See `development_log.txt` for a recent summary of implemented features, bug fixes, and testing notes (entry updated Nov 22, 2025).


# Multiplayer Pong Game

A networked implementation of the classic Pong game using Python and Pygame, featuring client-server architecture for multiplayer gameplay.

# Contact Info
============

Group Members & Email Addresses:

    Person 1, person1@uky.edu
    Person 2, person2@uky.edu


Github Link: 

## Requirements

- Python 3.7 or higher (3.11 is ideal to prevent error with getting requirements to build wheel)
- Pygame 2.5.2
- Network connectivity between server and clients

## Installation

1. Clone this repository or extract the provided zip file
2. Install the required dependencies:
```bash
pip install -r requirements.txt

or 

py -3 -m pip install -r requirements.txt

Or, if `python` is on your PATH:

python -m pip install -r requirements.txt
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

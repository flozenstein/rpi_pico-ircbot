import os
import wifi
import socketpool
import sys
import time
import random

server = "irc.service.net"  # settings
channel = "#channel"
botnick = "BotName"
chanceToSpeak = 0.75

# A simple Markov Chain Generator class
class MarkovChain:
    def __init__(self, n=2):
        self.n = n
        self.model = {}

    def train(self, text):
        # Prepare the text and split into words
        words = text.split()
        for i in range(len(words) - self.n):
            key = tuple(words[i:i + self.n])
            next_word = words[i + self.n]
            if key not in self.model:
                self.model[key] = []
            self.model[key].append(next_word)

    def generate(self, length=50):
        # Pick a random starting point
        current_key = random.choice(list(self.model.keys()))
        result = list(current_key)
        
        for _ in range(length - self.n):
            if current_key in self.model:
                next_word = random.choice(self.model[current_key])
                result.append(next_word)
                current_key = tuple(result[-self.n:])
            else:
                break
        
        return " ".join(result)

print()
print("Connecting to WiFi")

# connect to your SSID
try:
    wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
except TypeError:
    print("Could not find WiFi info. Check your settings.toml file!")
    raise

print("Connected to WiFi")

pool = socketpool.SocketPool(wifi.radio)

# Create a socket using the socketpool
sock = pool.socket(pool.AF_INET, pool.SOCK_STREAM)

# prints IP address to REPL
print("My IP address is: ", wifi.radio.ipv4_address)

print("init Markov generator")
markov_chain = MarkovChain(n=2)

print("Connecting to:", server)
sock.connect((server, 6667))

# Send user authentication
sock.send("USER " + botnick + " " + botnick + " " + botnick + " :spacktastic!\n")
sock.send("NICK " + botnick + "\n")  # Set nickname
sock.send("PRIVMSG nickserv :iNOOPE\r\n")  # Auth with NickServ
sock.send("JOIN " + channel + "\n")  # Join the channel

# Create a buffer to receive data
response = bytearray(2048)  # Buffer size can be adjusted

while True:
    try:
        # Receive data into the buffer
        bytes_received = sock.recv_into(response)
        
        # If no data was received, log the empty response and continue the loop
        if bytes_received == 0:
            print("No data received, continuing the loop...")
            time.sleep(0.1)  # Small delay to avoid busy-waiting
            continue

        # If data is received and it's not empty
        if bytes_received > 0:
            # Decode the received data and strip any unnecessary whitespace
            received_text = response[:bytes_received].decode().strip()

            # Log received text for debugging
            print(f"Received data: {received_text}")

            # If no valid data was received, skip this loop iteration
            if not received_text:
                print("Received empty message, skipping...")
                continue

            # Handle different types of IRC messages
            if "PING" in received_text:
                # Ensure there is a second part to the PING message
                parts = received_text.split()
                if len(parts) > 1:
                    pong_response = f"PONG {parts[1]}\r\n"
                    sock.send(pong_response.encode())  # Send the PONG response back to the server
                    print(f"Sent PONG response: {pong_response}")
            elif "NOTICE" in received_text:
                # Log notice messages for debugging, but ignore them for now
                print(f"Received NOTICE: {received_text}")
                continue  # Skip further processing for NOTICE messages
            elif "PRIVMSG" in received_text and channel in received_text:
                # Try to extract the message content after the colon
                parts = received_text.split(":", 2)
                if len(parts) > 2:
                    message_content = parts[2].strip()
                    if message_content:
                        print("Training Markov Chain with message:", message_content)
                        markov_chain.train(message_content)

            # Generate a response based on the Markov chain (50% chance to respond)
            if random.random() < chanceToSpeak:  # 50% chance to generate a response
                generated_message = markov_chain.generate(length=10)
                response_message = f"PRIVMSG {channel} :{generated_message}\r\n"
                sock.send(response_message.encode())
                print("Generated Markov Chain message:", generated_message)

    except Exception as e:
        #print(f"Error receiving or processing data: {e}")
        continue  # Continue loop even after an exception to avoid complete failure

    # Add a small delay to avoid blocking the CPU completely
    time.sleep(0.1)

# Close the socket (This will likely never be reached in this infinite loop)
sock.close()
print("Connection closed.")

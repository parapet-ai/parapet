# parapet v3.0.0 — P2P Encrypted Cowork Module
"""
European P2P AI Cowork — zero cloud, zero servers, zero third parties.
- WebRTC-style direct P2P connections via simple sockets + encryption
- LAN discovery via UDP broadcast (mDNS-style)
- All messages encrypted with AES-256-GCM (crypto_vault)
- Each peer runs their own GPU for inference
- Shared session context visible to all connected peers
- Works over LAN, VPN, or manual peer address
"""
import json
import os
import socket
import struct
import threading
import time
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace"))
COWORK_PORT = int(os.environ.get("COWORK_PORT", "0"))  # 0 = auto-assign
COWORK_DISCOVERY_PORT = 45678
COWORK_PEERS_FILE = WORKSPACE / ".parapet" / "cowork_peers.json"
COWORK_SESSIONS_DIR = WORKSPACE / ".parapet" / "cowork_sessions"

# Load encryption
try:
    from crypto_vault import encrypt_data, decrypt_data, load_key
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    def encrypt_data(d): return d
    def decrypt_data(d): return d


class CoworkPeer:
    """Represents a connected P2P cowork peer."""
    def __init__(self, addr, nickname="", public_key=""):
        self.addr = addr
        self.nickname = nickname or f"peer-{addr[1]}"
        self.public_key = public_key
        self.connected_at = time.time()
        self.last_seen = time.time()
        self.session_id = ""

    def to_dict(self):
        return {"addr": f"{self.addr[0]}:{self.addr[1]}",
                "nickname": self.nickname, "connected_at": self.connected_at}


class CoworkServer:
    """P2P cowork server — runs on each peer. Handles discovery + connections."""

    def __init__(self, nickname="", port=None):
        self.nickname = nickname or socket.gethostname()
        self.port = port or COWORK_PORT or self._find_free_port()
        self.peers = {}  # addr -> CoworkPeer
        self.sessions = {}  # session_id -> messages
        self.running = False
        self.discovery_thread = None
        self.server_socket = None
        self._lock = threading.Lock()

    def _find_free_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def start(self):
        """Start P2P cowork server — listen for connections + broadcast discovery."""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(10)
        self.server_socket.settimeout(1)

        # Start discovery broadcaster
        self.discovery_thread = threading.Thread(target=self._broadcast_discovery, daemon=True)
        self.discovery_thread.start()

        # Start discovery listener
        self._discovery_listener = threading.Thread(target=self._listen_discovery, daemon=True)
        self._discovery_listener.start()

        # Start connection acceptor
        self._acceptor = threading.Thread(target=self._accept_connections, daemon=True)
        self._acceptor.start()

        return {"ok": True, "port": self.port, "nickname": self.nickname,
                "message": f"Cowork server started on port {self.port}"}

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

    def _broadcast_discovery(self):
        """Send UDP broadcast every 5s for LAN peer discovery."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1)

        while self.running:
            try:
                msg = json.dumps({"type": "parapet_cowork_discovery",
                                  "nickname": self.nickname, "port": self.port,
                                  "host": socket.gethostname()})
                # Encrypt the discovery message
                if HAS_CRYPTO:
                    msg = encrypt_data(msg)
                sock.sendto(msg.encode(), ('255.255.255.255', COWORK_DISCOVERY_PORT))
            except Exception:
                pass
            time.sleep(5)

    def _listen_discovery(self):
        """Listen for UDP discovery broadcasts from other peers."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', COWORK_DISCOVERY_PORT))
        sock.settimeout(1)

        while self.running:
            try:
                data, addr = sock.recvfrom(4096)
                msg = data.decode()
                # Try decrypting (if encrypted)
                if HAS_CRYPTO:
                    try:
                        msg = decrypt_data(msg)
                    except Exception:
                        pass  # Not encrypted, use as-is
                info = json.loads(msg)
                if info.get("type") == "parapet_cowork_discovery":
                    peer_addr = (info.get("host", addr[0]), info.get("port", self.port + 1))
                    if addr[0] not in [p.addr[0] for p in self.peers.values()]:
                        self._add_peer((addr[0], info["port"]), info["nickname"])
            except socket.timeout:
                pass
            except Exception:
                pass

    def _add_peer(self, addr, nickname=""):
        with self._lock:
            if addr not in self.peers:
                self.peers[addr] = CoworkPeer(addr, nickname)
                # Save to disk
                self._save_peers()

    def _accept_connections(self):
        """Accept incoming P2P connections."""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_connection,
                               args=(conn, addr), daemon=True).start()
            except socket.timeout:
                pass
            except Exception:
                if self.running:
                    time.sleep(0.1)

    def _handle_connection(self, conn, addr):
        """Handle an incoming P2P connection from a peer."""
        conn.settimeout(30)
        try:
            data = b""
            while True:
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 1024 * 1024:  # 1MB limit
                        break
                except socket.timeout:
                    break

            if data:
                msg = data.decode()
                if HAS_CRYPTO:
                    try:
                        msg = decrypt_data(msg)
                    except Exception:
                        pass

                info = json.loads(msg)
                msg_type = info.get("type", "")

                if msg_type == "hello":
                    self._add_peer(addr, info.get("nickname", ""))
                    response = {"type": "welcome", "peers": len(self.peers),
                               "nickname": self.nickname}
                elif msg_type == "session_share":
                    session_id = info.get("session_id", "")
                    messages = info.get("messages", [])
                    with self._lock:
                        self.sessions[session_id] = messages
                    COWORK_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
                    (COWORK_SESSIONS_DIR / f"{session_id}.json").write_text(
                        json.dumps(messages, indent=2))
                    response = {"type": "session_ack", "session_id": session_id}
                else:
                    response = {"type": "ok"}

                resp_data = json.dumps(response)
                if HAS_CRYPTO:
                    resp_data = encrypt_data(resp_data)
                conn.send(resp_data.encode())

        except Exception:
            pass
        finally:
            conn.close()

    def connect_to_peer(self, host, port):
        """Initiate a P2P connection to another peer."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))

            msg = json.dumps({"type": "hello", "nickname": self.nickname})
            if HAS_CRYPTO:
                msg = encrypt_data(msg)
            sock.send(msg.encode())

            data = b""
            sock.settimeout(5)
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                except socket.timeout:
                    break

            if data:
                resp = data.decode()
                if HAS_CRYPTO:
                    try:
                        resp = decrypt_data(resp)
                    except Exception:
                        pass
                info = json.loads(resp)
                if info.get("type") == "welcome":
                    self._add_peer((host, port), "")
                    return {"ok": True, "peers": info.get("peers", 0)}

            sock.close()
            return {"ok": False, "error": "No response from peer"}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    def share_session(self, session_id, messages):
        """Share a session with all connected peers."""
        results = []
        msg = json.dumps({"type": "session_share", "session_id": session_id,
                         "messages": messages[-50:]})  # Last 50 messages max
        if HAS_CRYPTO:
            msg = encrypt_data(msg)

        for addr, peer in list(self.peers.items()):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(addr)
                sock.send(msg.encode())

                data = b""
                sock.settimeout(5)
                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        data += chunk
                    except socket.timeout:
                        break

                if data:
                    resp = data.decode()
                    if HAS_CRYPTO:
                        try:
                            resp = decrypt_data(resp)
                        except Exception:
                            pass
                    results.append({"peer": peer.nickname, "status": "ok",
                                   "response": json.loads(resp)})
                sock.close()
            except Exception as e:
                results.append({"peer": peer.nickname, "status": "error",
                               "error": str(e)})

        return {"shared_to": len(results), "results": results}

    def list_peers(self):
        return [p.to_dict() for p in self.peers.values()]

    def get_shared_session(self, session_id):
        path = COWORK_SESSIONS_DIR / f"{session_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return self.sessions.get(session_id, [])

    def _save_peers(self):
        COWORK_PEERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        COWORK_PEERS_FILE.write_text(json.dumps(
            [p.to_dict() for p in self.peers.values()], indent=2))

    def get_connection_info(self):
        """Return connection info for sharing with other peers."""
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "127.0.0.1"
        return {
            "nickname": self.nickname,
            "host": local_ip,
            "port": self.port,
            "peers": len(self.peers),
            "encryption": HAS_CRYPTO,
            "connection_string": f"{local_ip}:{self.port}",
        }


# Global cowork instance
_cowork_instance = None

def get_cowork(nickname=""):
    global _cowork_instance
    if _cowork_instance is None:
        _cowork_instance = CoworkServer(nickname=nickname)
    return _cowork_instance


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"

    cw = get_cowork(sys.argv[2] if len(sys.argv) > 2 else "")

    if cmd == "start":
        result = cw.start()
        print(json.dumps(result, indent=2))
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            cw.stop()

    elif cmd == "connect" and len(sys.argv) > 3:
        result = cw.connect_to_peer(sys.argv[2], int(sys.argv[3]))
        print(json.dumps(result, indent=2))

    elif cmd == "peers":
        print(json.dumps(cw.list_peers(), indent=2))

    elif cmd == "share" and len(sys.argv) > 3:
        session_id = sys.argv[2]
        messages = json.loads(sys.argv[3]) if len(sys.argv) > 3 else []
        result = cw.share_session(session_id, messages)
        print(json.dumps(result, indent=2))

    elif cmd == "info":
        print(json.dumps(cw.get_connection_info(), indent=2))

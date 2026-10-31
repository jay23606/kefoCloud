from pathlib import Path
import re
import socket
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TalkTurnPortsTest(unittest.TestCase):
    def test_talk_and_snikket_turn_listeners_bind_together(self):
        compose = (ROOT / "modules/nextcloud/docker-compose.yml").read_text()
        turn = (ROOT / "modules/nextcloud/talk/turnserver.conf.example").read_text()
        snikket_run = (ROOT / "modules/snikket/coturn-run").read_text()

        relay = compose.split("  relay:\n", 1)[1].split("\n  notify_push:", 1)[0]
        talk_ports = {int(port) for port in re.findall(r'^\s+- "(\d+):\d+/(?:udp|tcp)"$', relay, re.M)}
        plain = re.search(r'--listening-port "\$\{SNIKKET_TWEAK_TURNSERVER_PORT:-([0-9]+)\}"', snikket_run)
        self.assertIsNotNone(plain, "could not find Snikket coturn plain listener port")
        snikket_ports = {int(plain.group(1)), 5349}
        turn_ports = {int(port) for port in re.findall(r"^(?:listening-port|tls-listening-port)=(\d+)$", turn, re.M)}
        self.assertTrue(turn_ports, "could not find Talk coturn listener ports")
        self.assertTrue(turn_ports <= talk_ports, "Talk coturn listener ports are not published")
        self.assertTrue(talk_ports.isdisjoint(snikket_ports), "Talk and Snikket TURN published ports overlap")

        # Bind the configured TURN and TURNS listener sockets for both services
        # together, as the host-networked Snikket coturn and Talk relay do.
        sockets = []
        try:
            for port in sorted(turn_ports | snikket_ports):
                for sock_type in (socket.SOCK_DGRAM, socket.SOCK_STREAM):
                    sock = socket.socket(socket.AF_INET, sock_type)
                    sockets.append(sock)
                    sock.bind(("127.0.0.1", port))
                    if sock_type == socket.SOCK_STREAM:
                        sock.listen()
        finally:
            for sock in sockets:
                sock.close()


if __name__ == "__main__":
    unittest.main()

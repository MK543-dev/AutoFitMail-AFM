"""SMTP backend that avoids unreachable IPv6 routes.

Some shared/campus networks advertise IPv6 addresses for smtp.gmail.com that
have no working route; Python then fails with "network is unreachable"
(WinError 10051). This backend asks DNS for IPv4 first and falls back to the
normal behaviour if the IPv4 attempt fails.

Select it in .env with:
    EMAIL_BACKEND=config.email_backend.IPv4SMTPBackend
"""
import socket

from django.core.mail.backends.smtp import EmailBackend as _SMTPBackend


class IPv4SMTPBackend(_SMTPBackend):
    def _open_attempt(self, ipv4_only):
        original = socket.getaddrinfo

        def ipv4_first(host, port, family=0, type=0, proto=0, flags=0):
            try:
                return original(host, port, socket.AF_INET, type, proto, flags)
            except socket.gaierror:
                return original(host, port, family, type, proto, flags)

        if ipv4_only:
            socket.getaddrinfo = ipv4_first
        try:
            return super().open()
        finally:
            socket.getaddrinfo = original

    def open(self):
        try:
            return self._open_attempt(ipv4_only=True)
        except OSError:
            # IPv4 route failed as well - retry with the default resolution.
            if self.connection is not None:
                try:
                    self.connection.close()
                except Exception:  # noqa: BLE001
                    pass
                self.connection = None
            return self._open_attempt(ipv4_only=False)

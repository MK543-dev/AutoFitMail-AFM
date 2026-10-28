"""Quick SMTP connectivity/credential check for AutoFitMail.

Run inside afm/:   python check_smtp.py

It reads afm/.env directly (no Django needed) and reports exactly which
step fails: TCP connect -> TLS -> login. The password is only used for
the login attempt and is never printed.
"""
import smtplib
import socket
import ssl
import sys
from pathlib import Path


def load_env():
    env = {}
    env_path = Path(__file__).resolve().parent / '.env'
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env[key.strip()] = value.strip()
    return env


def _connect(host, port, use_ssl):
    """Connect preferring IPv4; shared/campus networks often advertise IPv6
    addresses for smtp.gmail.com that have no working route."""
    original = socket.getaddrinfo

    def ipv4_first(host, port, family=0, type=0, proto=0, flags=0):
        try:
            return original(host, port, socket.AF_INET, type, proto, flags)
        except socket.gaierror:
            return original(host, port, family, type, proto, flags)

    socket.getaddrinfo = ipv4_first
    try:
        if use_ssl:
            return smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context())
        server = smtplib.SMTP(host, port, timeout=30)
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        return server
    finally:
        socket.getaddrinfo = original


def main():
    env = load_env()
    host = env.get('EMAIL_HOST', 'smtp.gmail.com')
    port = int(env.get('EMAIL_PORT', '587'))
    use_ssl = env.get('EMAIL_USE_SSL', 'False').lower() == 'true'
    user = env.get('EMAIL_HOST_USER', '')
    password = env.get('EMAIL_HOST_PASSWORD', '')

    print(f'0. Resolving {host} ...')
    try:
        socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        print(f'   FAILED at DNS: {exc}')
        print('   -> Your machine could not look up the mail server address (DNS).')
        print('      Fixes: "ipconfig /flushdns", set DNS to 8.8.8.8 / 1.1.1.1,')
        print('      try a phone hotspot, check the hosts file / antivirus web-shield.')
        print('      Browsers may still work because they use their own DNS (DoH).')
        sys.exit(1)
    print('   OK - DNS resolved.')

    print(f'1. Connecting to {host}:{port} (ssl={use_ssl}) ...')
    try:
        server = _connect(host, port, use_ssl)
    except Exception as exc:  # noqa: BLE001
        print(f'   FAILED at connect/TLS: {type(exc).__name__}: {exc}')
        print('   -> Your network appears to block or filter SMTP to Gmail.')
        print('      Try: port 465 + EMAIL_USE_SSL=True, a different network')
        print('      (e.g. phone hotspot), or check antivirus mail-shield / firewall.')
        sys.exit(1)
    print('   OK - connected, TLS established.')

    if user:
        clean_password = password.replace(' ', '')
        if len(clean_password) != 16:
            print('   Hint: a Google app password is exactly 16 letters. The value in')
            print('   .env is not 16 characters - if it is your normal account password,')
            print('   it will NOT work; create an app password (steps printed below).')
        print(f'2. Logging in as {user} ...')
        try:
            server.login(user, clean_password)
        except Exception as exc:  # noqa: BLE001
            print(f'   FAILED at login: {type(exc).__name__}: {exc}')
            print('   -> Gmail refused or cut the login. Check, in this order:')
            print('      1) The value is a FRESH app password for THIS exact account')
            print('         (Google Account -> Security -> App passwords; 2-Step')
            print('         Verification must be ON). Delete old ones, create a new')
            print('         one, paste all 16 letters - never your account password.')
            print('      2) Sign in to that Gmail in this browser, then approve any')
            print('         "blocked sign-in attempt" alert: check the inbox or')
            print('         https://myaccount.google.com/notifications ("Yes, it was me").')
            print('      3) Retry on a different network (phone hotspot): shared or')
            print('         campus networks are sometimes flagged by Gmail.')
            print('      4) After repeated failures Gmail pauses app logins for')
            print('         30-60 minutes - wait, then run this check again.')
            server.close()
            sys.exit(1)
        print('   OK - credentials accepted.')
    server.quit()
    print('Everything works: AFM can send mail with these settings.')


if __name__ == '__main__':
    main()

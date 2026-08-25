#!/usr/bin/env python3
"""


eml(x, y) = exp(x) - ln(y)

Building blocks:
    exp(x)      = eml(x, 1)                          since ln(1) = 0
    ln(x)       = eml(1, eml(eml(1, x), 1))           = e - ln(e^e / x)
    0           = ln(1)
    x - y       = eml(ln(x), e^y)
    -y          = (1 - y) - 1     (built with the x-y rule twice, x=1)
    x + y       = x - (-y)
    x * y       = exp(ln(x) + ln(y))

Numerical safety notes for this specific challenge (x in [-10000,10000],
a,b in [-100,100], numpy raises on float overflow/underflow):
    - ln(v) is safe for ANY v != 0, even huge |v|, because it only needs
      log(v) which grows very slowly.
    - exp(v) is only safe when |v| is small (roughly <= 700).
    - eml(ln(x), y) safely reproduces x - y for arbitrarily large x, because
      exp(ln(x)) = x exactly without ever computing exp of the raw x.
    - So constants are built with repeated +1 (bounded, tiny), and a*x is
      built as exp(ln(a) + ln(x)) (sum of two SMALL logs, then a single
      safe exp) instead of ever exponentiating x or a*x directly.


"""
import sys
import re
import socket
import ssl
import subprocess

sys.setrecursionlimit(100_000)




def EML(a, b):
    return f"eml({a},{b})"


def EXPF(v):
    return EML(v, "1")


def LOG(v):
    return EML("1", EML(EML("1", v), "1"))


def ZERO():
    return LOG("1")


def SUB(p, q):
    """p - q  (requires p != 0; q must stay numerically small, <~700)"""
    return EML(LOG(p), EXPF(q))


def ONEMINUS(w):
    return SUB("1", w)


def NEG(w):
    return SUB(ONEMINUS(w), "1")


def ADD(u, w):
    return SUB(u, NEG(w))


def CONST(n):
    if n == 0:
        return ZERO()
    if n > 0:
        e = "1"
        for _ in range(n - 1):
            e = ADD(e, "1")
        return e
    return NEG(CONST(-n))


def MUL(a, xexpr="x"):
    """a * x, for a nonzero integer constant a, via exp(ln a + ln x)."""
    s = ADD(LOG(CONST(a)), LOG(xexpr))
    return EXPF(s)


def LINEAR(a, b):
    """Build an eml-grammar expression equal to a*x + b for all x."""
    if a == 0:
        return CONST(b)
    m = MUL(a)
    if b == 0:
        return m
    return ADD(m, CONST(b))



class Conn:
    def __init__(self, sock=None, proc=None):
        self.sock = sock
        self.proc = proc
        self.buf = b""

    def _fill(self):
        if self.sock is not None:
            chunk = self.sock.recv(4096)
        else:
            chunk = self.proc.stdout.read(1)
        if not chunk:
            raise EOFError("connection closed. buffer so far:\n" + self.buf.decode(errors="replace"))
        self.buf += chunk

    def recvuntil(self, pattern):
        pat = re.compile(pattern)
        while True:
            m = pat.search(self.buf)
            if m:
                data = self.buf[:m.end()]
                self.buf = self.buf[m.end():]
                return data
            self._fill()

    def sendline(self, data):
        if isinstance(data, str):
            data = data.encode()
        data += b"\n"
        if self.sock is not None:
            self.sock.sendall(data)
        else:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()

    def close(self):
        if self.sock is not None:
            self.sock.close()
        if self.proc is not None:
            self.proc.stdin.close()
            self.proc.wait()


def connect_remote(host, port, use_ssl=True):
    raw = socket.create_connection((host, port))
    if use_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        s = ctx.wrap_socket(raw, server_hostname=host)
    else:
        s = raw
    return Conn(sock=s)


def connect_local(path="eml.py"):
    proc = subprocess.Popen(
        ["python3", "-u", path],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return Conn(proc=proc)



def main():
    args = sys.argv[1:]
    if len(args) >= 2:
        host, port = args[0], int(args[1])
        use_ssl = not (len(args) >= 3 and args[2] == "nossl")
        io = connect_remote(host, port, use_ssl=use_ssl)
    else:
        io = connect_local()

    prompt = re.compile(rb"(-?\d+)x \+ (-?\d+) = ")
    for i in range(20):
        chunk = io.recvuntil(prompt)
        m = prompt.search(chunk)
        if not m:
            print("Couldn't find prompt in:", chunk)
            sys.exit(1)
        a, b = int(m.group(1)), int(m.group(2))
        expr = LINEAR(a, b)
        io.sendline(expr)
        result = io.recvuntil(rb"\n")
        print(i + 1, a, b, "->", result.strip().decode())
        if b"Wrong" in result:
            print("FAILED at round", i + 1)
            sys.exit(1)

    print(io.buf.decode(errors="replace"))
    try:
        while True:
            io._fill()
    except EOFError as e:
        print(str(e))


if __name__ == "__main__":
    main()

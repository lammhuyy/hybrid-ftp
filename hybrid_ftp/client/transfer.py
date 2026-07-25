import sys


class Progress:
    def __init__(self, total=None):
        self.total = total
        self.received = 0

    def update(self, n):
        self.received += n
        if self.total and self.total > 0:
            pct = min(100, int(self.received * 100 / self.total))
            bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
            sys.stdout.write(f"\r  [{bar}] {pct}% ({self.received}/{self.total} bytes)")
            sys.stdout.flush()

    def done(self):
        if self.total:
            print()
            print(f"  Completed: {self.received} bytes transferred.")


def read_file_chunks(path, chunk_size=1024):
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

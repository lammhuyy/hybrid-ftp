from threading import Lock


class Session:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.authenticated = False
        self.username = ""
        self.root = ""
        self.cwd = "/"
        self.type = "A"
        self.data_mode = "NONE"
        self.peer_addr = None
        self.data_socket = None
        self.rename_pending = None
        self.file_locks = {}
        self.last_cmd_time = 0

    def get_abs_path(self, path):
        from pathlib import Path
        if path.startswith("/"):
            rel = path[1:]
        else:
            rel = str(Path(self.cwd) / path).replace("\\", "/").lstrip("/")
        full = str((Path(self.root) / rel).resolve())
        root_real = str(Path(self.root).resolve())
        if not full.startswith(root_real):
            raise PermissionError("Path traversal denied")
        return full

    def get_lock(self, filepath):
        if filepath not in self.file_locks:
            self.file_locks[filepath] = Lock()
        return self.file_locks[filepath]

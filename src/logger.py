import datetime

class Logger:
    def __init__(self):
        self.logs = []

    def log(self, agent, message):
        timestamp = datetime.datetime.utcnow().isoformat()
        entry = f"[{timestamp}] [{agent}] {message}"
        self.logs.append(entry)
        print(entry)  # Optional: print to console

    def export(self, filepath="mission_log.txt"):
        with open(filepath, "w") as f:
            f.write("\n".join(self.logs))

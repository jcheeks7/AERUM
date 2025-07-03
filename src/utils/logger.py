from datetime import datetime

class Logger:
    def __init__(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = f"logs/mission_log_{timestamp}.txt"
        
        # Create logs directory if it doesn't exist
        import os
        os.makedirs("logs", exist_ok=True)

    def log(self, agent, message):
        timestamp = datetime.now().isoformat()
        full_message = f"[{timestamp}] [{agent}] {message}"
        print(full_message)
        with open(self.log_file, "a") as f:
            f.write(full_message + "\n")

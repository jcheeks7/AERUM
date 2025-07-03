class MessageBus:
    def __init__(self):
        self.messages = []

    def send(self, sender, recipient, content):
        self.messages.append({"from": sender, "to": recipient, "content": content})

    def fetch(self, agent_name):
        inbox = [m for m in self.messages if m["to"] == agent_name]
        self.messages = [m for m in self.messages if m["to"] != agent_name]  # Remove delivered
        return inbox

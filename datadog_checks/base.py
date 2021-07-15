
class AgentCheck():
    def gauge(self, name, value, tags=None):
        print("gauge", name, value, tags)

    def monotonic_count(self, name, value, tags=None):
        print("monotonic_count", name, value, tags)
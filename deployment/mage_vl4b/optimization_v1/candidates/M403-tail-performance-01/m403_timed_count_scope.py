"""Close the verified one-request count binding inside the original stream timer."""
from m402_count_scope import VideoCountScope


class TimedVideoCountScope(VideoCountScope):
    def count(self, tokens, generated):
        answer = super().count(tokens, generated)
        # M276 calls this after numerical inference, before yielding complete.
        # Keep the same binding identity required by the original close barrier.
        self.close()
        return answer


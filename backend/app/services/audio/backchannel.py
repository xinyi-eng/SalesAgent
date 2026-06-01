"""
Backchannel sound manager
Inserts brief acknowledgment sounds when user pauses during conversation
"""
import random
from typing import Optional


class BackchannelManager:
    """Manages backchannel acknowledgment responses"""

    # Brief acknowledgment texts
    BACKCHANNEL_TEXTS = [
        "嗯",
        "好的",
        "我明白了",
        "继续说",
        "是吗",
        "哦",
        "这样啊",
        "嗯嗯"
    ]

    def __init__(self):
        self.last_index = 0

    def generate_backchannel_text(self) -> str:
        """Generate a backchannel text response (rotating through options)"""
        text = self.BACKCHANNEL_TEXTS[self.last_index % len(self.BACKCHANNEL_TEXTS)]
        self.last_index += 1
        return text

    def generate_random_backchannel(self) -> str:
        """Generate a random backchannel text"""
        return random.choice(self.BACKCHANNEL_TEXTS)

    def should_respond(self, context: list) -> bool:
        """
        Determine if backchannel should be inserted.
        Called when user pauses during speaking.
        """
        if not context:
            return False

        # Only respond if last message was from user
        last_msg = context[-1]
        if last_msg.get("role") != "user":
            return False

        return True


# Global instance
backchannel_manager = BackchannelManager()
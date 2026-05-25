"""Content generator for message diversity to avoid detection."""
import random
import re
from typing import List, Optional


class ContentGenerator:
    """Generates diverse message content to avoid detection patterns.

    Features:
    - Message template variation
    - Random emoji injection
    - Synonym replacement
    - Sentence structure variation
    """

    # Common emoji sets for different contexts
    EMOJI_SETS = {
        "positive": ["😊", "😄", "🙂", "👍", "❤️", "🎉", "✨", "💪", "🤗", "😉"],
        "neutral": ["👌", "👍", "💫", "📌", "✅", "🔹", "➡️", "📝"],
        "greeting": ["👋", "🙋", "🌞", "🌟", "✨", "🎈"],
        "question": ["❓", "🤔", "💭", "👀", "📢"],
        "emphasis": ["🔥", "💥", "⭐", "🌈", "🦄", "🎊"],
    }

    # Synonym mappings for common words
    SYNONYMS = {
        "谢谢": ["谢谢", "感谢", "多谢", "感激", "谢啦"],
        "好的": ["好的", "好", "行", "OK", "没问题", "没问题"],
        "是的": ["是的", "对", "嗯", "对的", "是"],
        "哈哈": ["哈哈", "哈哈哈", "hhhh", "笑死", "笑死我了"],
        "你好": ["你好", "嗨", "hi", "你好呀", "您好"],
        "再见": ["再见", "拜拜", "下次见", "走了", "回头见"],
        "收到": ["收到", "好的收到", "好的", "明白", "了解"],
        "可以": ["可以", "行", "没问题", "OK", "好"],
    }

    # Suffixes that can be added to messages
    SUFFIXES = [
        "",
        "~",
        "啦",
        "呀",
        "哦",
        "哈",
        "~",
        "！",
        "😉",
        "😊",
        "👍",
    ]

    # Prefixes for variation
    PREFIXES = [
        "",
        "",
        "",
        "嗯 ",
        "好的 ",
        "收到 ",
        "OK ",
    ]

    def __init__(self, emoji_probability: float = 0.3):
        """Initialize the content generator.

        Args:
            emoji_probability: Probability of adding emoji (0-1).
        """
        self.emoji_probability = emoji_probability

    def add_emoji(self, content: str, context: str = "neutral") -> str:
        """Add random emoji to content.

        Args:
            content: Original message content.
            context: Emoji context (positive, neutral, greeting, etc.).

        Returns:
            Content with optional emoji added.
        """
        if random.random() > self.emoji_probability:
            return content

        emoji_set = self.EMOJI_SETS.get(context, self.EMOJI_SETS["neutral"])
        emoji = random.choice(emoji_set)

        # Add emoji at a random position
        position = random.choice(["start", "end", "end"])
        if position == "start":
            return f"{emoji} {content}"
        else:
            return f"{content} {emoji}"

    def replace_synonyms(self, content: str) -> str:
        """Replace words with synonyms for diversity.

        Args:
            content: Original message content.

        Returns:
            Content with some words replaced by synonyms.
        """
        result = content
        for word, synonyms in self.SYNONYMS.items():
            if word in result and random.random() > 0.5:
                result = result.replace(word, random.choice(synonyms), 1)
        return result

    def add_suffix(self, content: str) -> str:
        """Add a random suffix to the content.

        Args:
            content: Original message content.

        Returns:
            Content with random suffix.
        """
        # Don't add suffix if content already ends with punctuation
        if content and content[-1] in "!?。！？":
            return content

        suffix = random.choice(self.SUFFIXES)
        return content + suffix

    def add_prefix(self, content: str) -> str:
        """Add a random prefix to the content.

        Args:
            content: Original message content.

        Returns:
            Content with random prefix.
        """
        prefix = random.choice(self.PREFIXES)
        if not prefix:
            return content
        return prefix + content

    def vary_sentence_structure(self, content: str) -> str:
        """Vary sentence structure for diversity.

        Args:
            content: Original message content.

        Returns:
            Content with varied structure.
        """
        # Add slight variation to sentence endings
        variations = [
            lambda s: s,
            lambda s: s + "～",
            lambda s: s.replace("。", "～"),
            lambda s: s.replace("。", ",,"),
        ]
        return random.choice(variations)(content)

    def process(
        self,
        content: str,
        add_emoji: bool = True,
        replace_synonyms: bool = True,
        add_suffix: bool = True,
        add_prefix: bool = False,
    ) -> str:
        """Process content with all enabled transformations.

        Args:
            content: Original message content.
            add_emoji: Whether to add emoji.
            replace_synonyms: Whether to replace synonyms.
            add_suffix: Whether to add suffix.
            add_prefix: Whether to add prefix.

        Returns:
            Processed content with diversity improvements.
        """
        if not content:
            return content

        result = content

        if add_prefix:
            result = self.add_prefix(result)

        if replace_synonyms:
            result = self.replace_synonyms(result)

        if add_suffix:
            result = self.add_suffix(result)

        if add_emoji:
            result = self.add_emoji(result, self._detect_context(content))

        result = self.vary_sentence_structure(result)

        return result

    def _detect_context(self, content: str) -> str:
        """Detect the context of the message for emoji selection.

        Args:
            content: Message content.

        Returns:
            Context string.
        """
        positive_words = ["谢谢", "好", "棒", "喜欢", "开心", "高兴", "nice", "good"]
        greeting_words = ["你好", "嗨", "hi", "早上", "晚上", "中午"]

        if any(word in content for word in positive_words):
            return "positive"
        if any(word in content for word in greeting_words):
            return "greeting"
        if "?" in content or "？" in content:
            return "question"
        return "neutral"

    def generate_reply(
        self,
        templates: List[str],
        variables: Optional[dict] = None,
    ) -> str:
        """Generate a reply from templates with variable substitution.

        Args:
            templates: List of template strings with {var} placeholders.
            variables: Dictionary of variables to substitute.

        Returns:
            Generated reply string.
        """
        if not templates:
            return ""

        template = random.choice(templates)
        if variables:
            try:
                content = template.format(**variables)
            except KeyError:
                content = template
        else:
            content = template

        return self.process(content)


# Global content generator instance
content_generator = ContentGenerator()
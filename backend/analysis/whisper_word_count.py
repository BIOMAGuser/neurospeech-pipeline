"""
Raw word counting based directly on Whisper transcript.
This ensures every single word transcribed by Whisper is counted, including filler words.
"""


def raw_word_count(transcript: str) -> int:
    """
    Count ALL words in the Whisper transcript, including filler words like 'äh', 'ähm'.

    Splits on whitespace and counts everything that looks like a word,
    ensuring no word from Whisper's transcription is missed.
    """
    if not transcript or not transcript.strip():
        return 0

    return len(transcript.split())

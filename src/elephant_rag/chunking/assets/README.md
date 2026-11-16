# Offline tokenizer vocabulary

`cl100k_base.tiktoken` is the tokenizer rank vocabulary used for deterministic chunk budgets. It is bundled so preparation never downloads tokenizer data at runtime. This is vocabulary data, not neural model weights.

`cl100k_base.json` records the canonical source URL, SHA-256, regex pattern, and special-token mapping from the installed `tiktoken` constructor. `tokenizer.py` verifies the vocabulary checksum before building an encoding and treats special-token strings in PDFs as ordinary text.

The vocabulary originates from OpenAI's public `cl100k_base` encoding distributed with [tiktoken](https://github.com/openai/tiktoken). The upstream MIT license is included as `LICENSE.tiktoken`. If updating this vocabulary, update its pinned metadata and verify the checksum and offline tokenizer tests together.

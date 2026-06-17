from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def normalize(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "", text)
    return text


def char_ngrams(text: str, n_values=(1, 2)):
    text = normalize(text)
    for n in n_values:
        if len(text) < n:
            continue
        for i in range(len(text) - n + 1):
            yield text[i : i + n]


def load_jsonl(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def build_vocab(texts, min_count=1):
    counts = {}
    for text in texts:
        for token in char_ngrams(text):
            counts[token] = counts.get(token, 0) + 1
    vocab = ["<unk>"] + sorted(k for k, v in counts.items() if v >= min_count)
    return {token: idx for idx, token in enumerate(vocab)}


def vectorize(text: str, vocab: dict[str, int]):
    x = np.zeros(len(vocab), dtype=np.float32)
    seen = 0
    for token in char_ngrams(text):
        x[vocab.get(token, 0)] += 1.0
        seen += 1
    if seen:
        x /= max(float(seen), 1.0)
    return x


def softmax(logits):
    logits = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)


@dataclass
class TinyChatModel:
    vocab: dict[str, int]
    intents: list[str]
    w1: np.ndarray
    b1: np.ndarray
    w2: np.ndarray
    b2: np.ndarray

    def predict_proba(self, text: str):
        x = vectorize(text, self.vocab)[None, :]
        h = np.tanh(x @ self.w1 + self.b1)
        logits = h @ self.w2 + self.b2
        return softmax(logits)[0]

    def predict(self, text: str):
        probs = self.predict_proba(text)
        idx = int(probs.argmax())
        return self.intents[idx], float(probs[idx])

    def save(self, path: Path):
        np.savez_compressed(
            path,
            vocab=json.dumps(self.vocab, ensure_ascii=False),
            intents=json.dumps(self.intents, ensure_ascii=False),
            w1=self.w1,
            b1=self.b1,
            w2=self.w2,
            b2=self.b2,
        )

    @classmethod
    def load(cls, path: Path):
        data = np.load(path, allow_pickle=False)
        return cls(
            vocab=json.loads(str(data["vocab"])),
            intents=json.loads(str(data["intents"])),
            w1=data["w1"],
            b1=data["b1"],
            w2=data["w2"],
            b2=data["b2"],
        )


def train_model(rows, hidden_dim=48, epochs=900, lr=0.45, seed=7):
    rng = np.random.default_rng(seed)
    texts = [row["text"] for row in rows]
    vocab = build_vocab(texts)
    intents = sorted({row["intent"] for row in rows})
    intent_to_id = {name: idx for idx, name in enumerate(intents)}

    x = np.stack([vectorize(text, vocab) for text in texts])
    y = np.array([intent_to_id[row["intent"]] for row in rows], dtype=np.int64)
    n, input_dim = x.shape
    output_dim = len(intents)

    w1 = rng.normal(0, 0.12, size=(input_dim, hidden_dim)).astype(np.float32)
    b1 = np.zeros(hidden_dim, dtype=np.float32)
    w2 = rng.normal(0, 0.12, size=(hidden_dim, output_dim)).astype(np.float32)
    b2 = np.zeros(output_dim, dtype=np.float32)

    for epoch in range(1, epochs + 1):
        h = np.tanh(x @ w1 + b1)
        logits = h @ w2 + b2
        probs = softmax(logits)
        loss = -np.log(probs[np.arange(n), y] + 1e-9).mean()

        pred = probs.argmax(axis=1)
        grad_logits = probs.copy()
        grad_logits[np.arange(n), y] -= 1.0
        grad_logits /= n

        grad_w2 = h.T @ grad_logits
        grad_b2 = grad_logits.sum(axis=0)
        grad_h = grad_logits @ w2.T
        grad_z1 = grad_h * (1.0 - h * h)
        grad_w1 = x.T @ grad_z1
        grad_b1 = grad_z1.sum(axis=0)

        w2 -= lr * grad_w2
        b2 -= lr * grad_b2
        w1 -= lr * grad_w1
        b1 -= lr * grad_b1

        if epoch % 150 == 0 or epoch == 1:
            acc = float((pred == y).mean())
            print(f"epoch={epoch:04d} loss={loss:.4f} train_acc={acc:.3f}")

    return TinyChatModel(vocab=vocab, intents=intents, w1=w1, b1=b1, w2=w2, b2=b2)

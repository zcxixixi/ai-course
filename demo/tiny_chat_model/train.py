from pathlib import Path

from tiny_model import load_jsonl, train_model


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "dialogues.jsonl"
MODEL = ROOT / "model.npz"


def main():
    rows = load_jsonl(DATA)
    model = train_model(rows)
    model.save(MODEL)
    print(f"saved: {MODEL}")


if __name__ == "__main__":
    main()

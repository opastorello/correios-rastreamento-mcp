"""
Avalia a acurácia do modelo CRNN contra as amostras salvas em data/.

Uso:
    python -m app.captcha.evaluate
    python -m app.captcha.evaluate --samples 5000
    python -m app.captcha.evaluate --model app/captcha/captcha_model.pt
"""
import argparse
import random
from pathlib import Path

import torch
import torchvision.transforms as T
from PIL import Image
from app.captcha.model import CaptchaModel, decode_greedy, IMG_H, IMG_W

DATA_DIR = Path(__file__).parent / "data"
MODEL_PATH = Path(__file__).parent / "captcha_model.pt"


def evaluate(model_path: Path, samples: int | None = None) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = CaptchaModel().to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    transform = T.Compose([
        T.Grayscale(),
        T.Resize((IMG_H, IMG_W)),
        T.ToTensor(),
        T.Normalize([0.5], [0.5]),
    ])

    files = list(DATA_DIR.glob("*.png"))
    if not files:
        print(f"Nenhuma amostra em {DATA_DIR}.")
        return

    if samples and samples < len(files):
        files = random.sample(files, samples)

    print(f"Avaliando {len(files)} amostras com {model_path.name} em {device}...")

    correct_full = correct_char = total_char = 0
    errors = []

    total = len(files)
    with torch.no_grad():
        for i, path in enumerate(files, 1):
            if i % 1000 == 0 or i == total:
                print(f"  {i}/{total}", end="\r", flush=True)
            label = path.stem.rsplit("_", 1)[0]
            img = transform(Image.open(path).convert("RGB")).unsqueeze(0).to(device)
            log_probs = torch.log_softmax(model(img), dim=2)
            pred = decode_greedy(log_probs)[0]

            if pred == label:
                correct_full += 1
            else:
                errors.append((label, pred))

            for p, t in zip(pred, label):
                correct_char += int(p == t)
            total_char += len(label)

    acc_full = correct_full / len(files)
    acc_char = correct_char / max(total_char, 1)

    print(f"\nResultados sobre {len(files)} amostras:")
    print(f"  Acurácia por sequência : {acc_full:.4%}  ({correct_full}/{len(files)})")
    print(f"  Acurácia por caractere : {acc_char:.4%}")

    if errors:
        print(f"\nExemplos de erro ({min(10, len(errors))} de {len(errors)}):")
        for label, pred in errors[:10]:
            print(f"  esperado={label!r:12s}  predito={pred!r}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=str(MODEL_PATH),
                        help="Caminho para o .pt a avaliar")
    parser.add_argument("--samples", type=int, default=None,
                        help="Quantidade de amostras aleatórias (padrão: todas)")
    args = parser.parse_args()
    evaluate(Path(args.model), args.samples)

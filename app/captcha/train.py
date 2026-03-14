"""
Treino do modelo CRNN para o CAPTCHA do Correios.

Uso:
    python -m app.captcha.train --epochs 80 --batch 128 --lr 1e-3
"""
import argparse
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from app.captcha.dataset import CaptchaDataset, collate_fn
from app.captcha.model import CaptchaModel, decode_greedy, CHARSET
from app.captcha.registry import save_version

DATA_DIR = Path(__file__).parent / "data"
MODEL_PATH = Path(__file__).parent / "captcha_model.pt"


def char_accuracy(preds, targets_flat, target_lengths):
    correct = total = 0
    offset = 0
    for pred, length in zip(preds, target_lengths):
        target_chars = targets_flat[offset:offset + length].tolist()
        pred_chars = [CHARSET.index(c) for c in pred if c in CHARSET]
        for p, t in zip(pred_chars, target_chars):
            correct += int(p == t)
        total += length
        offset += length
    return correct / max(total, 1)


def train(epochs=80, batch_size=128, lr=1e-3):
    dataset = CaptchaDataset(DATA_DIR, augment=True)
    if len(dataset) == 0:
        print(f"Nenhuma amostra em {DATA_DIR}. Execute o collector primeiro.")
        sys.exit(1)

    val_size = max(1, int(len(dataset) * 0.1))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])

    # num_workers=0 no Windows (limitação do PyTorch com CUDA)
    nw = 0 if sys.platform == "win32" else 4
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                              collate_fn=collate_fn, num_workers=nw)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                            collate_fn=collate_fn, num_workers=nw)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device} | Amostras: {len(dataset)} (train={train_size}, val={val_size})")

    model = CaptchaModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    ctc_loss = nn.CTCLoss(blank=len(CHARSET), zero_infinity=True)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    best_val_loss = float("inf")
    patience = 20
    no_improve = 0

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for imgs, targets, lengths in train_loader:
            imgs, targets = imgs.to(device), targets.to(device)
            optimizer.zero_grad()
            with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
                logits = model(imgs)
                log_probs = torch.log_softmax(logits, dim=2)
                T, B, _ = log_probs.shape
                input_lengths = torch.full((B,), T, dtype=torch.long)
                loss = ctc_loss(log_probs, targets, input_lengths, lengths)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            train_loss += loss.item()
        scheduler.step()

        model.eval()
        val_loss = val_acc = 0.0
        with torch.no_grad():
            for imgs, targets, lengths in val_loader:
                imgs, targets = imgs.to(device), targets.to(device)
                logits = model(imgs)
                log_probs = torch.log_softmax(logits, dim=2)
                T, B, _ = log_probs.shape
                input_lengths = torch.full((B,), T, dtype=torch.long)
                loss = ctc_loss(log_probs, targets, input_lengths, lengths)
                val_loss += loss.item()
                preds = decode_greedy(log_probs)
                val_acc += char_accuracy(preds, targets.cpu(), lengths.cpu())

        val_loss /= len(val_loader)
        val_acc /= len(val_loader)
        print(f"Epoch {epoch:3d}/{epochs} | train_loss={train_loss/len(train_loader):.4f} "
              f"| val_loss={val_loss:.4f} | val_acc={val_acc:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            no_improve = 0
            torch.save(model.state_dict(), MODEL_PATH)
            print(f"  -> Modelo salvo (val_loss={val_loss:.4f})")
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"Early stopping (sem melhora por {patience} épocas)")
                break

    save_version(epochs=epoch, batch=batch_size, lr=lr,
                 samples=len(dataset), val_acc=val_acc, val_loss=best_val_loss)
    print(f"Treino concluído. Modelo: {MODEL_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()
    train(args.epochs, args.batch, args.lr)

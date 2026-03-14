"""
Versionamento de modelos treinados.

Uso:
    python -m app.captcha.registry
"""
import json
from datetime import datetime
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent / "registry.json"
MODEL_PATH = Path(__file__).parent / "captcha_model.pt"


def _load() -> list:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return []


def save_version(epochs, batch, lr, samples, val_acc, val_loss):
    versions = _load()
    version = len(versions) + 1
    versions.append({
        "version": version,
        "date": datetime.now().isoformat(timespec="seconds"),
        "samples": samples,
        "epochs": epochs,
        "batch": batch,
        "lr": lr,
        "val_acc": round(float(val_acc), 4),
        "val_loss": round(float(val_loss), 4),
        "active": True,
    })
    # Marca todas as anteriores como inativas
    for v in versions[:-1]:
        v["active"] = False
    REGISTRY_PATH.write_text(json.dumps(versions, indent=2))
    print(f"Versão {version} registrada.")


def list_versions():
    versions = _load()
    if not versions:
        print("Nenhuma versão registrada.")
        return
    header = f"{'Ver':>4}  {'Data':>20}  {'Amostras':>8}  {'Epochs':>6}  {'Batch':>5}  {'LR':>8}  {'val_acc':>7}  {'val_loss':>8}"
    print(header)
    for v in versions:
        active = " *" if v.get("active") else ""
        print(f"{v['version']:>4}  {v['date']:>20}  {v['samples']:>8}  {v['epochs']:>6}  "
              f"{v['batch']:>5}  {v['lr']:>8}  {v['val_acc']:>7.4f}  {v['val_loss']:>8.4f}{active}")


if __name__ == "__main__":
    list_versions()

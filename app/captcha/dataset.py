from pathlib import Path

import torch
import torchvision.transforms as T
from PIL import Image
from torch.utils.data import Dataset

from app.captcha.model import CHARSET, IMG_H, IMG_W


class CaptchaDataset(Dataset):
    def __init__(self, data_dir, augment=False):
        self.samples = []
        for p in Path(data_dir).glob("*.png"):
            label = "_".join(p.stem.split("_")[:-1])
            if all(c in CHARSET for c in label) and 3 <= len(label) <= 7:
                self.samples.append((p, label))

        base = [T.Grayscale(), T.Resize((IMG_H, IMG_W)), T.ToTensor(), T.Normalize([0.5], [0.5])]
        if augment:
            base = [
                T.Grayscale(), T.Resize((IMG_H, IMG_W)),
                T.RandomRotation(5),
                T.RandomAffine(degrees=0, shear=5, translate=(0.02, 0.02)),
                T.ColorJitter(brightness=0.4, contrast=0.4),
                T.GaussianBlur(kernel_size=3, sigma=(0.1, 1.5)),
                T.ToTensor(), T.Normalize([0.5], [0.5]),
                T.RandomErasing(p=0.2, scale=(0.01, 0.05)),
            ]
        self.transform = T.Compose(base)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = self.transform(Image.open(path).convert("RGB"))
        target = torch.tensor([CHARSET.index(c) for c in label], dtype=torch.long)
        return img, target, len(label)


def collate_fn(batch):
    imgs, targets, lengths = zip(*batch)
    return torch.stack(imgs), torch.cat(targets), torch.tensor(lengths, dtype=torch.long)

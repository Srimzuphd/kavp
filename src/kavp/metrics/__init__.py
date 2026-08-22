"""KAVP metrics: utility, system, compliance, and unlearning metrics.

This subpackage requires optional dependencies (numpy, scikit-learn, torch).
Install with: pip install "kavp[ml]"
"""
from __future__ import annotations
import time
import threading
from typing import Optional

import numpy as np

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

try:
    from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                                 f1_score, roc_auc_score, log_loss)
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


def cls_metrics(model, X, y, device: str = "cpu"):
    if not _TORCH_AVAILABLE:
        raise RuntimeError("This feature requires the 'ml' optional dependencies. Install them with: pip install 'kavp[ml]'")
    model.eval()
    with torch.no_grad():
        Xt = torch.tensor(X, dtype=torch.float32, device=device)
        logits = model(Xt).cpu().numpy()
    probs = torch.softmax(torch.tensor(logits), dim=1).numpy()
    pred = probs.argmax(1)
    out = {
        "acc": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
    }
    try:
        out["auc"] = float(roc_auc_score(y, probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]))
    except Exception:
        out["auc"] = 0.5
    try:
        out["loss"] = float(log_loss(y, probs, labels=list(range(probs.shape[1]))))
    except Exception:
        out["loss"] = float("nan")
    return out


def inference_time_ms(model, X, repeats: int = 30):
    if not _TORCH_AVAILABLE:
        raise RuntimeError("This feature requires the 'ml' optional dependencies. Install them with: pip install 'kavp[ml]'")
    model.eval()
    Xt = torch.tensor(X, dtype=torch.float32)
    with torch.no_grad():
        for _ in range(3):
            _ = model(Xt[:1])
        t0 = time.perf_counter()
        for _ in range(repeats):
            _ = model(Xt[:1])
        return (time.perf_counter() - t0) / repeats * 1000.0


def membership_inference_attack(model, X_member, y_member, X_nonmember, y_nonmember):
    if not _TORCH_AVAILABLE:
        raise RuntimeError("This feature requires the 'ml' optional dependencies. Install them with: pip install 'kavp[ml]'")
    model.eval()
    with torch.no_grad():
        def losses(X, y):
            Xt = torch.tensor(X, dtype=torch.float32)
            logits = model(Xt)
            lp = torch.log_softmax(logits, dim=1).numpy()
            return -lp[np.arange(len(y)), y]
        lm = losses(X_member, y_member)
        ln = losses(X_nonmember, y_nonmember)
    scores = np.concatenate([-lm, -ln])
    labels = np.concatenate([np.ones_like(lm), np.zeros_like(ln)])
    try:
        from sklearn.metrics import roc_auc_score
        return float(roc_auc_score(labels, scores))
    except Exception:
        return 0.5


class MemTracker:
    def __init__(self):
        import resource
        self.r = resource
        self.start = self.r.getrusage(self.r.RUSAGE_SELF).ru_maxrss

    def peak_mb(self):
        return (self.r.getrusage(self.r.RUSAGE_SELF).ru_maxrss) / 1024.0


def influence_norm(theta_with: np.ndarray, theta_without: np.ndarray) -> float:
    diff = np.concatenate([a.ravel() - b.ravel() for a, b in zip(theta_with, theta_without)])
    return float(np.linalg.norm(diff))

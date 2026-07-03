"""UT-ENC4 — Build Phase 4 encoder package (baseline, autoencoder, data, train)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.encoder.base import build_encoder
from src.encoder.baseline import BaselineEncoder
from src.encoder.data import N_PATCH_FEATURES, patch_tokens_for_window
from src.encoder.train import auroc, load_quality_labels
from src.features.vibration import rms

FS = 2000.0
TOKEN_DIM = 30


def _tokens(n: int = 64, dim: int = TOKEN_DIM, seed: int = 0,
            outlier_rows: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, (n, dim)).astype("float32")
    if outlier_rows:
        x[-outlier_rows:] += 25.0
    return x


# ------------------------------------------------------------------ tokens (D13)
def test_patch_tokens_shape_and_one_path_rms():
    t_rel = np.arange(-8.0, 8.0, 1.0 / FS)
    rng = np.random.default_rng(1)
    waveform = pd.DataFrame({
        "t_rel_s": t_rel,
        "ax": rng.normal(0, 1, len(t_rel)),
        "ay": rng.normal(0, 1, len(t_rel)),
        "az": rng.normal(0, 1, len(t_rel)) - 1015.0,
    })
    tokens = patch_tokens_for_window(waveform, -8.0, 4.0, FS)
    assert tokens.shape == (95, 3 * N_PATCH_FEATURES)
    # First feature per channel must equal rms() of that channel's first patch
    # (I-3: one feature path), after per-channel DC removal.
    window = waveform.iloc[:24000][["ax", "ay", "az"]].to_numpy()
    window = window - np.median(window, axis=0)
    assert tokens[0, 0] == pytest.approx(rms(window[:500, 0].tolist()), rel=1e-5)
    assert tokens[0, N_PATCH_FEATURES] == pytest.approx(
        rms(window[:500, 1].tolist()), rel=1e-5)


# ------------------------------------------------------------------ baseline
def test_baseline_shapes_and_determinism():
    x = _tokens()
    a = BaselineEncoder(TOKEN_DIM, dim=8, seed=7)
    b = BaselineEncoder(TOKEN_DIM, dim=8, seed=7)
    a.fit(x)
    b.fit(x)
    np.testing.assert_array_equal(a.encode(x), b.encode(x))
    np.testing.assert_array_equal(a.anomaly_scores(x), b.anomaly_scores(x))
    assert a.encode(x).shape == (len(x), 8)
    assert a.anomaly_scores(x).shape == (len(x),)


def test_baseline_flags_outliers():
    x = _tokens(outlier_rows=4)
    enc = BaselineEncoder(TOKEN_DIM, dim=8, seed=7)
    enc.fit(x[:-4])                                   # fit on inliers only
    scores = enc.anomaly_scores(x)
    assert scores[-4:].min() > scores[:-4].mean()


def test_baseline_requires_fit():
    enc = BaselineEncoder(TOKEN_DIM, dim=8)
    with pytest.raises(RuntimeError):
        enc.encode(_tokens(4))


# ------------------------------------------------------------------ autoencoder
def _ae(**kwargs):
    pytest.importorskip("torch")
    defaults = dict(kind="autoencoder", token_dim=TOKEN_DIM, dim=8, hidden=16,
                    seed=7, device="cpu", epochs=25, batch_size=16, lr=1e-2)
    defaults.update(kwargs)
    return build_encoder(**defaults)


def test_autoencoder_loss_decreases_and_shapes():
    x = _tokens(n=128)
    enc = _ae()
    metrics = enc.fit(x)
    assert metrics["final_epoch_loss"] < metrics["first_epoch_loss"]
    assert enc.encode(x).shape == (128, 8)
    scores = enc.anomaly_scores(x)
    assert scores.shape == (128,) and scores.min() >= 0.0 and scores.max() <= 1.0


def test_autoencoder_is_seed_deterministic():
    x = _tokens(n=64)
    a = _ae()
    a.fit(x)
    b = _ae()
    b.fit(x)
    np.testing.assert_allclose(a.encode(x), b.encode(x), rtol=0, atol=0)
    np.testing.assert_allclose(a.anomaly_scores(x), b.anomaly_scores(x),
                               rtol=0, atol=0)


def test_autoencoder_flags_regime_shift():
    x_train = _tokens(n=128, seed=1)
    x_shift = _tokens(n=16, seed=2) + 10.0            # unseen regime
    enc = _ae()
    enc.fit(x_train)
    # Scores normalize by the train q99, so unseen regimes saturate near 1.0
    # while train scores center well below it.
    shift_scores = enc.anomaly_scores(x_shift)
    train_scores = enc.anomaly_scores(x_train)
    assert shift_scores.min() > 0.95
    assert shift_scores.mean() > train_scores.mean() + 0.3


# ------------------------------------------------------------------ quarantine (I-4)
def test_load_tokens_refuses_test_split(tmp_path):
    from src.encoder.data import load_tokens
    with pytest.raises(PermissionError):
        load_tokens(object(), ("train", "test"))


# ------------------------------------------------------------------ diagnostics
def test_auroc_known_orderings():
    labels = np.array([0, 0, 1, 1])
    assert auroc(np.array([0.1, 0.2, 0.8, 0.9]), labels) == 1.0
    assert auroc(np.array([0.9, 0.8, 0.2, 0.1]), labels) == 0.0
    assert auroc(np.array([0.5, 0.5, 0.5, 0.5]), labels) == 0.5
    assert np.isnan(auroc(np.array([0.5, 0.6]), np.array([1, 1])))


def test_load_quality_labels_parses_jsonl(tmp_path):
    path = tmp_path / "q.jsonl"
    path.write_text('{"incident_id": "a", "quality": "bad", "run_id": "r"}\n'
                    '{"incident_id": "b", "quality": "good", "run_id": "s"}\n',
                    encoding="utf-8")
    assert load_quality_labels(path) == {"a": 1, "b": 0}

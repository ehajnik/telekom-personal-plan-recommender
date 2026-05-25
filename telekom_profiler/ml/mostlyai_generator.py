"""MOSTLY AI-backed synthetic panel generation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from telekom_profiler.ml.features import build_subscriber_features
from telekom_profiler.ml.schema import MONTH_COL, RAW_NUMERIC_COLS, SUBSCRIBER_ID_COL

_REQUIRED_PANEL_COLS = (SUBSCRIBER_ID_COL, MONTH_COL, *RAW_NUMERIC_COLS)
_RATIO_COLS = ("night_usage_ratio", "weekend_usage_ratio")
_COUNTISH_COLS = ("sms_count", "countries_visited", "plan_tier", "lines_total", "lines_active")


def build_mostlyai_context(panel: pd.DataFrame) -> pd.DataFrame:
    """Build a subscriber-level context table for sequential MOSTLY AI training."""
    features = build_subscriber_features(panel)
    month_counts = (
        panel.groupby(SUBSCRIBER_ID_COL, sort=True)
        .size()
        .rename("months_observed")
        .reset_index()
    )
    context = features.merge(month_counts, on=SUBSCRIBER_ID_COL, how="left")
    context["months_observed"] = context["months_observed"].fillna(0).astype(int)
    return context


def load_mostlyai_engine() -> Any:
    """Import the optional MOSTLY AI engine with a clear setup error."""
    try:
        from mostlyai import engine
    except ImportError as exc:
        raise RuntimeError(
            "MOSTLY AI support requires the optional dependency 'mostlyai-engine'. "
            "Install it with: pip install -r requirements-mostlyai.txt"
        ) from exc
    return engine


def generate_panel_with_mostlyai(
    source_panel: pd.DataFrame,
    *,
    n_subscribers: int,
    months: int = 12,
    seed: int = 42,
    max_training_time: int = 2,
    workspace_dir: Path,
) -> pd.DataFrame:
    """Train a sequential MOSTLY AI model and return a repaired monthly panel."""
    _validate_source_panel(source_panel)
    if n_subscribers < 1:
        raise ValueError("n_subscribers must be >= 1")
    if months < 2:
        raise ValueError("months must be >= 2")

    engine = load_mostlyai_engine()
    workspace_dir.mkdir(parents=True, exist_ok=True)
    context = build_mostlyai_context(source_panel)

    engine.init_logging()
    engine.split(
        workspace_dir=workspace_dir,
        tgt_data=source_panel.copy(),
        ctx_data=context,
        tgt_context_key=SUBSCRIBER_ID_COL,
        ctx_primary_key=SUBSCRIBER_ID_COL,
        model_type="TABULAR",
    )
    engine.analyze(workspace_dir=workspace_dir)
    engine.encode(workspace_dir=workspace_dir)
    engine.train(workspace_dir=workspace_dir, max_training_time=max_training_time)

    try:
        engine.generate(workspace_dir=workspace_dir, sample_size=n_subscribers)
    except TypeError:
        # Older engine builds may not accept sample_size for all workflows.
        engine.generate(workspace_dir=workspace_dir)

    raw_panel = _load_generated_target(workspace_dir)
    return normalize_generated_panel(
        raw_panel,
        n_subscribers=n_subscribers,
        months=months,
        seed=seed,
    )


def normalize_generated_panel(
    panel: pd.DataFrame,
    *,
    n_subscribers: int,
    months: int = 12,
    seed: int = 42,
) -> pd.DataFrame:
    """Repair MOSTLY AI output into a stable 12-month training panel."""
    if n_subscribers < 1:
        raise ValueError("n_subscribers must be >= 1")
    if months < 2:
        raise ValueError("months must be >= 2")

    missing = [col for col in _REQUIRED_PANEL_COLS if col not in panel.columns]
    if missing:
        raise ValueError(f"Generated panel missing columns: {missing}")

    working = panel.loc[:, list(_REQUIRED_PANEL_COLS)].copy()
    for col in (MONTH_COL, *RAW_NUMERIC_COLS):
        working[col] = pd.to_numeric(working[col], errors="coerce")
    working[SUBSCRIBER_ID_COL] = working[SUBSCRIBER_ID_COL].astype(str)
    working = working.dropna(subset=[MONTH_COL, *RAW_NUMERIC_COLS]).reset_index(drop=True)
    if working.empty:
        raise ValueError("Generated panel has no valid rows after numeric coercion")

    rng = np.random.default_rng(seed)
    subscriber_ids = working[SUBSCRIBER_ID_COL].drop_duplicates().tolist()
    if not subscriber_ids:
        raise ValueError("Generated panel has no subscriber ids")

    chosen_ids = _choose_source_ids(subscriber_ids, n_subscribers=n_subscribers, rng=rng)
    repaired_rows: list[pd.DataFrame] = []

    for idx, source_id in enumerate(chosen_ids, start=1):
        group = (
            working[working[SUBSCRIBER_ID_COL] == source_id]
            .sort_values(MONTH_COL, kind="stable")
            .reset_index(drop=True)
        )
        if group.empty:
            continue

        if len(group) >= months:
            group = group.head(months).copy()
        else:
            extra_idx = rng.choice(group.index.to_numpy(), size=months - len(group), replace=True)
            group = pd.concat([group, group.iloc[extra_idx]], ignore_index=True)
            group = group.sort_values(MONTH_COL, kind="stable").reset_index(drop=True)

        group = group.loc[:, [MONTH_COL, *RAW_NUMERIC_COLS]].copy()
        group.insert(0, SUBSCRIBER_ID_COL, f"SUB{idx:05d}")
        group[MONTH_COL] = np.arange(1, months + 1, dtype=int)
        repaired_rows.append(group)

    if not repaired_rows:
        raise ValueError("Generated panel could not be normalized into subscriber sequences")

    repaired = pd.concat(repaired_rows, ignore_index=True)
    return _clip_panel_values(repaired)


def _validate_source_panel(panel: pd.DataFrame) -> None:
    missing = [col for col in _REQUIRED_PANEL_COLS if col not in panel.columns]
    if missing:
        raise ValueError(f"Source panel missing columns: {missing}")


def _choose_source_ids(
    subscriber_ids: list[str],
    *,
    n_subscribers: int,
    rng: np.random.Generator,
) -> list[str]:
    ids = np.asarray(subscriber_ids, dtype=object)
    if len(subscriber_ids) >= n_subscribers:
        selected = rng.choice(ids, size=n_subscribers, replace=False)
    else:
        selected = rng.choice(ids, size=n_subscribers, replace=True)
    return [str(sid) for sid in selected.tolist()]


def _clip_panel_values(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel.copy()
    out["data_gb"] = out["data_gb"].clip(lower=0.0)
    out["voice_min"] = out["voice_min"].clip(lower=0.0)
    out["sms_count"] = out["sms_count"].clip(lower=0.0)
    out["roaming_days"] = out["roaming_days"].clip(lower=0.0, upper=31.0)
    out["countries_visited"] = out["countries_visited"].clip(lower=0.0)
    out["avg_session_mb"] = out["avg_session_mb"].clip(lower=1.0)
    out["active_days"] = out["active_days"].clip(lower=1.0, upper=31.0)
    out["plan_tier"] = out["plan_tier"].clip(lower=1.0, upper=5.0)
    out["lines_total"] = out["lines_total"].clip(lower=1.0)
    out["lines_active"] = out["lines_active"].clip(lower=0.0)

    for col in _RATIO_COLS:
        out[col] = out[col].clip(lower=0.0, upper=1.0)

    for col in _COUNTISH_COLS:
        out[col] = np.rint(out[col]).clip(lower=0.0)

    out["countries_visited"] = np.minimum(
        out["countries_visited"],
        np.floor(out["roaming_days"].clip(lower=0.0)),
    )
    out["lines_total"] = out["lines_total"].clip(lower=1.0)
    out["lines_active"] = np.minimum(out["lines_active"], out["lines_total"])
    out[MONTH_COL] = out[MONTH_COL].astype(int)
    return out.loc[:, list(_REQUIRED_PANEL_COLS)]


def _load_generated_target(workspace_dir: Path) -> pd.DataFrame:
    synthetic_root = workspace_dir / "SyntheticData"
    if not synthetic_root.exists():
        raise FileNotFoundError(f"MOSTLY AI output not found under {synthetic_root}")

    for path in [synthetic_root, *sorted(synthetic_root.rglob("*"))]:
        if not path.is_dir():
            continue
        try:
            frame = pd.read_parquet(path)
        except Exception:
            continue
        if set(_REQUIRED_PANEL_COLS).issubset(frame.columns):
            return frame

    raise FileNotFoundError(
        f"Could not locate a parquet dataset with expected panel columns under {synthetic_root}"
    )

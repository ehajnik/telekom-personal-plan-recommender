"""ML-backed profile provider using trained K-Means artifacts."""

from __future__ import annotations

from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.domain.profiling import render_ml_profile_report
from telekom_profiler.ml.features import features_from_usage
from telekom_profiler.ml.inference import (
    get_profile,
    load_artifacts,
    predict_from_features,
    predict_subscriber,
    scoring_result_from_prediction,
)
from telekom_profiler.runtime_context import subscriber_id_var


class MlProfileProvider:
    """Profile from K-Means segmentation + metric-backed narrative."""

    source = "ml_kmeans"

    def profile(self, usage: CustomerUsage) -> ProfileResult:
        sid = subscriber_id_var.get()
        if sid:
            pred = predict_subscriber(str(sid), usage_override=usage)
        else:
            pred = predict_from_features(features_from_usage(usage))

        scoring = scoring_result_from_prediction(pred)
        bundle = load_artifacts()
        profile = get_profile(bundle.profile_characteristics, pred.primary_label)
        markdown = render_ml_profile_report(
            pred.primary_label,
            pred.metrics,
            pred.overlays,
            profile=profile,
        )
        return ProfileResult(
            markdown=markdown,
            usage=usage,
            scoring=scoring,
            source=self.source,
            metadata={
                "subscriber_id": sid,
                "metrics": pred.metrics,
                "cluster_idx": pred.cluster_idx,
            },
        )

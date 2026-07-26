"""
Multi-factor aggregator module for the Institutional Signal Intelligence Engine.

Consumes standardized SignalResult objects from the SignalRegistry and 
synthesizes them into a single, actionable FinalSignal.
"""

from typing import List

from core.logger import LoggerFactory
from models import FeatureSnapshot
from signal.signal_models import FinalSignal, SignalDecision, SignalDirection, SignalResult
from signal.signal_registry import SignalRegistry


class MultiFactorAggregator:
    """
    Synthesizes multiple SignalResult objects into a unified FinalSignal 
    based on weighted scoring and directional consensus.
    """

    def __init__(self, registry: SignalRegistry) -> None:
        """
        Args:
            registry: The SignalRegistry containing all enabled providers.
        """
        self._logger = LoggerFactory().get_logger(__name__)
        self._registry = registry

    def aggregate(self, features: FeatureSnapshot) -> FinalSignal:
        """
        Evaluates all enabled signal providers and aggregates their results.
        """
        providers = self._registry.get_enabled()
        results: List[SignalResult] = []

        # 1. Gather results from all enabled providers
        for provider in providers:
            try:
                result = provider.generate(features)
                results.append(result)
            except Exception as e:
                self._logger.error(f"Signal provider '{provider.name}' failed during aggregation: {e}")

        # 2. Calculate weighted scores
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = sum(res.weight for res in results)
        
        supporting_signals = []
        reasons = []

        for res in results:
            if res.direction == SignalDirection.BULLISH:
                bullish_score += res.score * res.weight
                supporting_signals.append(res.signal_name)
                reasons.append(f"[{res.signal_name}] {res.metadata.get('reason', '')}")
            elif res.direction == SignalDirection.BEARISH:
                bearish_score += res.score * res.weight
                supporting_signals.append(res.signal_name)
                reasons.append(f"[{res.signal_name}] {res.metadata.get('reason', '')}")

        # Normalize scores to a 0-100 scale based on total possible weight
        if total_weight > 0:
            bullish_score = (bullish_score / total_weight) * 100.0
            bearish_score = (bearish_score / total_weight) * 100.0

        # 3. Determine final decision based on thresholds
        # Require a minimum score and a clear divergence between bullish/bearish
        divergence_threshold = 15.0 
        
        if bullish_score >= 60.0 and (bullish_score - bearish_score) >= divergence_threshold:
            decision = SignalDecision.BUY
        elif bearish_score >= 60.0 and (bearish_score - bullish_score) >= divergence_threshold:
            decision = SignalDecision.SELL
        else:
            decision = SignalDecision.NO_TRADE

        # Confidence is the strength of the winning side, or 0 if no trade
        confidence = max(bullish_score, bearish_score) if decision != SignalDecision.NO_TRADE else 0.0

        reason_summary = " | ".join(reasons) if reasons else "No strong directional signals detected."

        self._logger.debug(
            f"Aggregated Signal: {decision.name} | Bullish: {bullish_score:.1f} | "
            f"Bearish: {bearish_score:.1f} | Confidence: {confidence:.1f}"
        )

        return FinalSignal(
            timestamp=features.timestamp,
            decision=decision,
            bullish_score=round(bullish_score, 2),
            bearish_score=round(bearish_score, 2),
            confidence=round(confidence, 2),
            reason_summary=reason_summary,
            supporting_signals=supporting_signals
        )

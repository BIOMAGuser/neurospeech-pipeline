"""
Closed-form Bayesian helpers for cohort statistics.

For each (cell, feature) we maintain a Normal-Inverse-Gamma posterior:
    μ ~ N(μ₀, σ²/κ₀),   σ² ~ InvGamma(α₀, β₀)

After observing n samples with mean x̄ and SS = Σ(xᵢ - x̄)², the posterior is

    κₙ = κ₀ + n
    μₙ = (κ₀·μ₀ + n·x̄) / κₙ
    αₙ = α₀ + n/2
    βₙ = β₀ + SS/2 + (κ₀·n·(x̄ - μ₀)²) / (2·κₙ)

The posterior predictive for a new observation x* is Student-t:

    x* ~ t_{2·αₙ}(loc = μₙ,  scale² = βₙ·(κₙ + 1) / (αₙ·κₙ))

No MCMC, no fitting — everything is one-shot algebra.
"""

from dataclasses import dataclass
from math import isfinite

import numpy as np
from scipy.stats import t as student_t


@dataclass(frozen=True)
class NIGParams:
    """Posterior Normal-Inverse-Gamma parameters."""
    mu: float
    kappa: float
    alpha: float
    beta: float
    n: int  # observation count (for diagnostics)

    @property
    def df(self) -> float:
        """Degrees of freedom of the posterior predictive Student-t."""
        return 2.0 * self.alpha

    @property
    def predictive_scale(self) -> float:
        """Scale (σ) of the posterior predictive Student-t."""
        var = self.beta * (self.kappa + 1.0) / (self.alpha * self.kappa)
        return float(np.sqrt(max(var, 1e-12)))


# Weakly informative prior — proper but lets data dominate after a handful of samples.
NIG_DEFAULT = NIGParams(mu=0.0, kappa=1.0, alpha=1.0, beta=1.0, n=0)


def posterior_nig(observations: np.ndarray, prior: NIGParams = NIG_DEFAULT) -> NIGParams:
    """Conjugate update of NIG with a vector of real-valued observations."""
    obs = np.asarray(observations, dtype=np.float64)
    obs = obs[np.isfinite(obs)]
    n = obs.size
    if n == 0:
        return prior

    x_bar = float(obs.mean())
    ss = float(((obs - x_bar) ** 2).sum())

    kappa_n = prior.kappa + n
    mu_n = (prior.kappa * prior.mu + n * x_bar) / kappa_n
    alpha_n = prior.alpha + n / 2.0
    beta_n = (
        prior.beta
        + ss / 2.0
        + (prior.kappa * n * (x_bar - prior.mu) ** 2) / (2.0 * kappa_n)
    )
    return NIGParams(mu=mu_n, kappa=kappa_n, alpha=alpha_n, beta=beta_n, n=prior.n + n)


def predictive_logpdf(nig: NIGParams, x: float) -> float:
    """log p(x | NIG) under the posterior predictive Student-t."""
    if not isfinite(x):
        return float("-inf")
    return float(student_t.logpdf(x, df=nig.df, loc=nig.mu, scale=nig.predictive_scale))


def predictive_cdf(nig: NIGParams, x: float) -> float:
    """CDF of the posterior predictive at x — i.e. percentile of x in the cohort."""
    if not isfinite(x):
        return float("nan")
    return float(student_t.cdf(x, df=nig.df, loc=nig.mu, scale=nig.predictive_scale))


def sigmoid(z: float) -> float:
    if z >= 0:
        ez = np.exp(-z)
        return float(1.0 / (1.0 + ez))
    ez = np.exp(z)
    return float(ez / (1.0 + ez))


def voice_age_score(
    target_features: dict[str, float],
    control_nig: dict[str, NIGParams],
    pd_nig: dict[str, NIGParams],
    weights: dict[str, float] | None = None,
) -> dict:
    """
    Compute PD_Voice_Age_Score = sigmoid(Σ_f w_f · [log p(x|PD) - log p(x|Control)]).

    Returns dict with score, log_likelihood_ratio, and the per-feature contributions.
    Features missing in either posterior dict are skipped.
    """
    weights = weights or {}
    contributions: dict[str, dict] = {}
    llr_total = 0.0
    used = 0

    for feat, value in target_features.items():
        c = control_nig.get(feat)
        p = pd_nig.get(feat)
        if c is None or p is None or not isfinite(value):
            continue
        w = float(weights.get(feat, 1.0))
        log_p_pd = predictive_logpdf(p, value)
        log_p_ctrl = predictive_logpdf(c, value)
        if not (isfinite(log_p_pd) and isfinite(log_p_ctrl)):
            continue
        ll_ratio = log_p_pd - log_p_ctrl
        contributions[feat] = {
            "value": float(value),
            "log_p_control": log_p_ctrl,
            "log_p_pd": log_p_pd,
            "weighted_llr": w * ll_ratio,
        }
        llr_total += w * ll_ratio
        used += 1

    if used == 0:
        return {"score": None, "log_likelihood_ratio": None, "contributions": {}, "n_features_used": 0}

    return {
        "score": sigmoid(llr_total),
        "log_likelihood_ratio": llr_total,
        "contributions": contributions,
        "n_features_used": used,
    }

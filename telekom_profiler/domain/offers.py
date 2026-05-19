"""Rule-based B2C plan and add-on recommendations (Telekom Deutschland catalog)."""

from __future__ import annotations

from telekom_profiler.config.thresholds import (
    ARCHETYPE_CHATTERBOX,
    ARCHETYPE_ESSENTIAL,
    ARCHETYPE_MESSENGER,
    ARCHETYPE_ROAMER,
    ARCHETYPE_STREAMER,
    OFFER_DATA_BOOST_GB,
    OFFER_DATA_L_GB,
    OFFER_DATA_M_GB,
    OFFER_DATA_PREPAID_MAX_GB,
    OFFER_DATA_XL_GB,
    OFFER_MULTISIM_DATA_GB,
    OFFER_ROAMING_ADDON_DAYS,
    OFFER_VOICE_PREPAID_MAX,
)
from telekom_profiler.domain.models import ScoringResult

_ML_LIGHT = "Light / occasional user"
_ML_STREAMING = "Streaming & data-heavy"
_ML_VOICE = "Voice-centric"
_ML_ROAMING = "Roaming / travel-heavy"
_ML_UNDER = "Underutilized / overspending"

_TARIFF_XL = (
    "MagentaMobil XL (MM-XL-001)",
    "€84.95",
    "Unbegrenzt DE; für sehr hohes Datenvolumen und Streaming.",
)
_TARIFF_L = (
    "MagentaMobil L (MM-L-001)",
    "€59.95",
    "100 GB; inkl. 5 GB Roaming LG 2/3 und unbegrenzte Sprache EU/CH/GB/TR.",
)
_TARIFF_M = (
    "MagentaMobil M (MM-M-001)",
    "€49.95",
    "50 GB; ausgewogen für Daten und Flat Voice DE.",
)
_TARIFF_S = (
    "MagentaMobil S (MM-S-001)",
    "€39.95",
    "30 GB; Einstieg Postpaid mit Flat Voice/SMS DE.",
)
_TARIFF_XS = (
    "MagentaMobil XS (MM-XS-001)",
    "€29.95",
    "20 GB; günstigster MagentaMobil Postpaid.",
)
_TARIFF_PREPAID_S = (
    "MagentaMobil Prepaid S (MP-PP-S-001)",
    "€4.95 / 4 Wochen",
    "1 GB; für sehr geringe Nutzung ohne Bindung.",
)
_TARIFF_PREPAID_M = (
    "MagentaMobil Prepaid M (MP-PP-M-001)",
    "€9.95 / 4 Wochen",
    "13 GB; flexibel, Datenmitnahme, HotSpot Flat.",
)
_TARIFF_PREPAID_L = (
    "MagentaMobil Prepaid L (MP-PP-L-001)",
    "€14.95 / 4 Wochen",
    "25 GB; Alternative zu Postpaid bei moderater Nutzung.",
)
_TARIFF_PLUS = (
    "MagentaMobil PlusKarte (MM-PLUS-001)",
    "€19.95",
    "Zweitvertrag mit Datenpool wie Hauptvertrag (bis 5×).",
)


def _select_tariff(
    data: dict[str, float],
    scoring: ScoringResult | None,
) -> tuple[str, str, str]:
    """Pick base tariff from usage thresholds, biased by primary archetype when known."""
    primary = scoring.primary_name if scoring else None

    if primary == _ML_LIGHT or (
        primary == ARCHETYPE_ESSENTIAL and data["data_gb"] < OFFER_DATA_M_GB
    ):
        if data["data_gb"] < 3 and data["voice_min"] < OFFER_VOICE_PREPAID_MAX:
            return _TARIFF_PREPAID_S
        if data["data_gb"] < OFFER_DATA_PREPAID_MAX_GB:
            return _TARIFF_PREPAID_M
        return _TARIFF_XS if data["data_gb"] < 15 else _TARIFF_S
    if primary == _ML_STREAMING or primary == ARCHETYPE_STREAMER:
        return _TARIFF_XL if data["data_gb"] >= OFFER_DATA_L_GB else _TARIFF_L
    if primary == _ML_VOICE or primary == ARCHETYPE_CHATTERBOX:
        return _TARIFF_M if data["data_gb"] >= OFFER_DATA_M_GB else _TARIFF_S
    if primary == _ML_ROAMING or primary == ARCHETYPE_ROAMER:
        return _TARIFF_L if data["data_gb"] >= OFFER_DATA_M_GB else _TARIFF_M
    if primary == _ML_UNDER:
        if data["data_gb"] < OFFER_DATA_PREPAID_MAX_GB:
            return _TARIFF_PREPAID_M
        return _TARIFF_XS if data["data_gb"] < OFFER_DATA_M_GB else _TARIFF_S

    if primary == ARCHETYPE_ESSENTIAL and data["data_gb"] < OFFER_DATA_M_GB:
        return _TARIFF_PREPAID_M if data["data_gb"] < OFFER_DATA_PREPAID_MAX_GB else _TARIFF_XS
    if primary == ARCHETYPE_CHATTERBOX and data["data_gb"] < OFFER_DATA_L_GB:
        return _TARIFF_M
    if primary == ARCHETYPE_STREAMER or data["data_gb"] >= OFFER_DATA_XL_GB:
        return _TARIFF_XL
    if primary == ARCHETYPE_ROAMER and data["data_gb"] >= OFFER_DATA_M_GB:
        return _TARIFF_L
    if primary == ARCHETYPE_MESSENGER and OFFER_DATA_M_GB <= data["data_gb"] < OFFER_DATA_L_GB:
        return _TARIFF_M

    if data["data_gb"] >= OFFER_DATA_XL_GB:
        return _TARIFF_XL
    if data["data_gb"] >= OFFER_DATA_L_GB:
        return _TARIFF_L
    if data["data_gb"] >= OFFER_DATA_M_GB:
        return _TARIFF_M
    if data["data_gb"] < OFFER_DATA_PREPAID_MAX_GB and data["voice_min"] < OFFER_VOICE_PREPAID_MAX:
        return _TARIFF_PREPAID_M
    if data["data_gb"] < OFFER_DATA_M_GB:
        return _TARIFF_XS
    return _TARIFF_S


def render_offer_report(
    _profile_text: str,
    data: dict[str, float],
    *,
    scoring: ScoringResult | None = None,
) -> str:
    """Build offer markdown aligned with ``prompts/templates/run_offer.md``."""
    tariff = _select_tariff(data, scoring)
    primary_note = ""
    if scoring:
        primary_note = f" Primary archetype: **{scoring.primary_name}**."

    addons: list[tuple[str, str, str]] = []
    roaming_threshold = OFFER_ROAMING_ADDON_DAYS
    if scoring and scoring.primary_name == ARCHETYPE_ROAMER:
        roaming_threshold = max(4.0, OFFER_ROAMING_ADDON_DAYS - 2)

    primary_name = scoring.primary_name if scoring else None
    if data["roaming_days"] >= roaming_threshold or primary_name in (
        _ML_ROAMING,
        ARCHETYPE_ROAMER,
    ):
        addons.append(
            (
                "Travel & Surf 4-WeekPass (ADD-TS-4W-001)",
                "ab €49.95",
                f"{data['roaming_days']:.0f} Roaming-Tage/Monat — Daten LG 2/3 (pass.telekom.de).",
            )
        )
        if data["roaming_days"] >= 12:
            addons.append(
                (
                    "Travel Mobil Basic (ADD-TMB-001)",
                    "€14.95 / Buchung",
                    "Sprach-/SMS-/Datenpaket für längere Nicht-EU-Aufenthalte.",
                )
            )
    if data["data_gb"] >= OFFER_DATA_BOOST_GB and tariff[0] != _TARIFF_XL[0]:
        addons.append(
            (
                "Travel & Surf WeekPass (ADD-TS-WEEK-001)",
                "ab €15.95",
                "Kurzfristiger Datenpuffer bei Spitzenlast außerhalb EU.",
            )
        )
    if data["data_gb"] >= OFFER_MULTISIM_DATA_GB and "PlusKarte" not in tariff[0]:
        addons.append(
            (
                "MagentaMobil PlusKarte (MM-PLUS-001)",
                "€19.95",
                "Zweites Gerät mit gleichem Datenvolumen wie Hauptvertrag.",
            )
        )

    is_prepaid = "Prepaid" in tariff[0]
    channel = (
        "**Prepaid (MagentaMobil Prepaid)** — Abrechnung alle 4 Wochen, keine "
        "Mindestlaufzeit; ideal bei schwankender Nutzung."
        if is_prepaid
        else "**Postpaid (MagentaMobil)** — planbare monatliche Rechnung; "
        "typisch 24 Monate Bindung (oder **Flex** ohne Bindung, nur ohne Handy)."
    )

    addon_rows = "\n".join(
        f"| {name} | {price} | {note} |" for name, price, note in addons
    ) or "| — | — | Keine Zusatzoption zwingend erforderlich |"

    addon_bullets = (
        "\n".join(f"- **{a[0]}** ({a[1]}): {a[2]}" for a in addons)
        if addons
        else "- Keine Pflicht-Optionen; Nutzung zum Vertragsende prüfen."
    )

    return f"""### 1. Recommended main tariff
**{tariff[0]}** — {tariff[2]}{primary_note}

### 2. Recommended add-ons and options
{addon_bullets}

### 3. Contract and channel notes
{channel}
- **MeinMagenta App** / Shop: Tarifwechsel und Travel-&-Surf-Buchung.
- **MagentaMobil Young** (18–27): prüfen, wenn Kunde berechtigt — günstigerer Grundpreis, mehr GB.
- **MagentaEINS**: Kombi-Rabatt mit MagentaZuhause in CRM prüfen.

### 4. Indicative pricing
| Product | Monthly price (brutto) | Notes |
|---------|------------------------|-------|
| {tariff[0]} | {tariff[1]} | Haupttarif |
{addon_rows}

*Katalog basiert auf Telekom-Preislisten (siehe `plans_and_options.md`). Vor Angebot in BSS/PCM verifizieren.*

### 5. Important caveats
- **EU-Roaming:** Fair-Use bei unbegrenzten Tarifen; Young XL hat 200 GB EU-Sonderkontingent.
- Nach Verbrauch des Inklusiv-Datenvolumens: **Drosselung 64/16 kbit/s** (Postpaid/Prepaid).
- **Travel & Surf:** Preise/Volumen landesspezifisch — pass.telekom.de vor Reise buchen.
- Schweiz/GB: Roaming LG 1, aber angemessene Nutzung bei Sprache/SMS beachten.

### 6. Next steps for the agent
- Aktuellen Vertrag und Restlaufzeit in CRM prüfen (Bindung, Hardware-Raten).
- Bei Roaming ≥ {OFFER_ROAMING_ADDON_DAYS:.0f} Tagen: Reiseziele (EU/LG 2/3) klären und T&S-Pass empfehlen.
- Tarifwechsel oder PlusKarte über MeinMagenta anbieten, wenn berechtigt.
"""

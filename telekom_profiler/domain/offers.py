"""Rule-based B2C plan and add-on recommendations."""

from __future__ import annotations


def render_offer_report(_profile_text: str, data: dict[str, float]) -> str:
    """Build offer markdown aligned with ``prompts/templates/run_offer.md``."""
    if data["data_gb"] >= 70:
        tariff = ("MagentaMobil XL", "€69.95", "Unlimited DE data; fits heavy streaming.")
    elif data["data_gb"] >= 35:
        tariff = ("MagentaMobil L", "€59.95", "50 GB matches sustained high data use.")
    elif data["data_gb"] >= 15:
        tariff = ("MagentaMobil M", "€49.95", "Balanced data and flat voice.")
    elif data["data_gb"] < 8 and data["voice_min"] < 300:
        tariff = ("MagentaMobil Prepaid M", "€14.95", "Low usage suits flexible prepaid.")
    else:
        tariff = ("MagentaMobil S", "€39.95", "Entry postpaid for light-medium use.")

    addons: list[tuple[str, str, str]] = []
    if data["roaming_days"] >= 8:
        addons.append(
            (
                "EU Roaming Plus",
                "€5.95",
                f"{data['roaming_days']:.0f} roaming days/month — extra EU data pool.",
            )
        )
    if data["data_gb"] >= 45 and tariff[0] != "MagentaMobil XL":
        addons.append(("Data Boost 5 GB", "€4.95", "Safety buffer if between tiers."))
    if data["data_gb"] >= 25:
        addons.append(("MultiSIM Tablet", "€4.95", "Second device on shared allowance."))

    channel = (
        "**Postpaid (MagentaMobil)** — predictable bill, flat rates."
        if "Prepaid" not in tariff[0]
        else "**Prepaid** — flexibility, no long binding; top up as needed."
    )

    addon_rows = "\n".join(
        f"| {name} | {price} | {note} |" for name, price, note in addons
    ) or "| — | — | No add-ons required at this usage level |"

    addon_bullets = (
        "\n".join(f"- **{a[0]}** ({a[1]}): {a[2]}" for a in addons)
        if addons
        else "- None essential; monitor usage at renewal."
    )

    return f"""### 1. Recommended main tariff
**{tariff[0]}** — {tariff[2]}

### 2. Recommended add-ons and options
{addon_bullets}

### 3. Contract and channel notes
{channel}

### 4. Indicative pricing
| Product | Monthly price (brutto) | Notes |
|---------|------------------------|-------|
| {tariff[0]} | {tariff[1]} | Base plan |
{addon_rows}

*Prototype catalog — verify in BSS before customer quote.*

### 5. Important caveats
- EU roaming subject to fair-use policy on unlimited tiers.
- Intro offers and MagentaEINS discounts require eligibility check in CRM.
- Trends are indicative; confirm last 3 billing months before downgrade/upgrade.

### 6. Next steps for the agent
- Compare recommended tier with current contract in CRM.
- If roaming days ≥ 8, confirm travel countries for EU vs world pack.
- Offer self-service tariff change in MeinMagenta app where eligible.
"""

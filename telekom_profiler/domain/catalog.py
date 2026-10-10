"""Structured Telekom Deutschland private mobile catalogue (PoC).

Single source of truth for the rule-based offer engine. The LLM reads the same
facts from ``data/plans_and_options.md``; ``tests/test_catalog.py`` checks that
every SKU and price here also appears in that file so the two cannot drift.

Prices are brutto (incl. 19 % VAT). Sources and "Stand" dates are listed in
``data/plans_and_options.md``. Verify in BSS/PCM before quoting to customers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

TariffFamily = Literal["postpaid", "prepaid", "young"]

CATALOG_STAND: Final[str] = "Feb 2026"


@dataclass(frozen=True, slots=True)
class Tariff:
    """A main tariff. ``data_gb=None`` means unlimited domestic data."""

    sku: str
    name: str
    family: TariffFamily
    price_eur: float
    period: str
    data_gb: float | None
    lg23_data_gb_per_year: float = 0.0
    eu_voice_flat: bool = False
    multisim_included: int = 0
    voice_note: str = "Flat to all German networks"

    @property
    def price_label(self) -> str:
        return f"€{self.price_eur:.2f} / {self.period}"

    @property
    def data_label(self) -> str:
        return "unlimited" if self.data_gb is None else f"{self.data_gb:g} GB"

    def covers(self, data_need_gb: float) -> bool:
        return self.data_gb is None or self.data_gb >= data_need_gb

    @property
    def display(self) -> str:
        return f"{self.name} ({self.sku})"


@dataclass(frozen=True, slots=True)
class AddOn:
    sku: str
    name: str
    price_label: str
    note: str

    @property
    def display(self) -> str:
        return f"{self.name} ({self.sku})"


# --- MagentaMobil postpaid (24 months or Flex without minimum term; SIM-only) ---
# Annual LG 2/3 roaming volume added 04.02.2026 (renews every calendar year).
POSTPAID: Final[tuple[Tariff, ...]] = (
    Tariff("MM-XS-001", "MagentaMobil XS", "postpaid", 29.95, "month", 20,
           lg23_data_gb_per_year=2),
    Tariff("MM-S-001", "MagentaMobil S", "postpaid", 39.95, "month", 30,
           lg23_data_gb_per_year=4),
    Tariff("MM-M-001", "MagentaMobil M", "postpaid", 49.95, "month", 50,
           lg23_data_gb_per_year=10),
    Tariff("MM-L-001", "MagentaMobil L", "postpaid", 59.95, "month", 100,
           lg23_data_gb_per_year=25, eu_voice_flat=True, multisim_included=1),
    Tariff("MM-XL-001", "MagentaMobil XL", "postpaid", 84.95, "month", None,
           lg23_data_gb_per_year=50, eu_voice_flat=True, multisim_included=2),
)

# --- MagentaMobil Prepaid (billed per 4 weeks / 28 days; volumes since 25.02.2026) ---
PREPAID: Final[tuple[Tariff, ...]] = (
    Tariff("MP-PP-S-001", "MagentaMobil Prepaid S", "prepaid", 4.95, "4 weeks", 1,
           voice_note="Flat to Telekom network, 50 min to other German networks"),
    Tariff("MP-PP-M-001", "MagentaMobil Prepaid M", "prepaid", 9.95, "4 weeks", 20),
    Tariff("MP-PP-L-001", "MagentaMobil Prepaid L", "prepaid", 14.95, "4 weeks", 40),
    Tariff("MP-PP-XL-001", "MagentaMobil Prepaid XL", "prepaid", 19.95, "4 weeks", 80),
    Tariff("MP-PP-MAX-001", "MagentaMobil Prepaid Max", "prepaid", 99.95, "4 weeks", None),
)

# --- MagentaMobil Young (18–27; requires age check — not inferable from usage) ---
YOUNG: Final[tuple[Tariff, ...]] = (
    Tariff("MM-Y-S-001", "MagentaMobil Young S", "young", 29.95, "month", 30),
    Tariff("MM-Y-M-001", "MagentaMobil Young M", "young", 39.95, "month", 100),
    Tariff("MM-Y-L-001", "MagentaMobil Young L", "young", 49.95, "month", 200,
           eu_voice_flat=True),
    Tariff("MM-Y-XL-001", "MagentaMobil Young XL", "young", 74.95, "month", None,
           eu_voice_flat=True),
)

ALL_TARIFFS: Final[tuple[Tariff, ...]] = POSTPAID + PREPAID + YOUNG

# --- Add-ons and options ---
PLUSKARTE: Final = AddOn(
    "MM-PLUS-001", "MagentaMobil PlusKarte", "€19.95 / month",
    "Second SIM with the main contract's allowances (setup €19.95).",
)
PLUSKARTE_PLUS: Final = AddOn(
    "MM-PLUSP-001", "MagentaMobil PlusKarte+", "€14.95 / month",
    "Each further card after the first PlusKarte (setup €14.95).",
)
PLUSKARTE_DATA: Final = AddOn(
    "MM-PLUS-DATA-001", "MagentaMobil PlusKarte Data", "€14.95 / month",
    "Data-only card for tablet / laptop, incl. the annual LG 2/3 volume.",
)
PLUSKARTE_KIDS: Final = AddOn(
    "MM-PLUS-KT-001", "PlusKarte Kids & Teens", "€9.95 / month",
    "Child card (6–17 years), age proof required.",
)
TS_2DAY: Final = AddOn(
    "ADD-TS-2DAY-001", "Travel & Surf 2-DayPass", "from €5.95",
    "At least 1 GB for 2 days outside the EU (LG 2/3).",
)
TS_4WEEK_LG2: Final = AddOn(
    "ADD-TS-4W-LG2-001", "Travel & Surf 4-WeekPass (LG 2)", "€49.95",
    "20 GB for 4 weeks in roaming country group 2.",
)
WELCOME_PASS: Final = AddOn(
    "ADD-WELCOME-001", "Welcome Pass (Magenta Moments)", "€0.00",
    "1 GB for 48 h outside the EU, up to 2× per year (contract customers).",
)
MAGENTA_EINS: Final = AddOn(
    "ADD-M1-001", "MagentaEINS Vorteil", "discount",
    "Bundle benefit with MagentaZuhause fixed line / TV.",
)

ALL_ADDONS: Final[tuple[AddOn, ...]] = (
    PLUSKARTE,
    PLUSKARTE_PLUS,
    PLUSKARTE_DATA,
    PLUSKARTE_KIDS,
    TS_2DAY,
    TS_4WEEK_LG2,
    WELCOME_PASS,
    MAGENTA_EINS,
)

# Prepaid S includes only 50 off-net minutes; above this the customer pays per minute.
PREPAID_S_VOICE_MAX_MIN: Final[float] = 50.0


def cheapest_covering(tariffs: tuple[Tariff, ...], data_need_gb: float) -> Tariff:
    """Cheapest tariff whose allowance covers ``data_need_gb`` (largest if none does)."""
    fitting = [t for t in tariffs if t.covers(data_need_gb)]
    if not fitting:
        return max(tariffs, key=lambda t: float("inf") if t.data_gb is None else t.data_gb)
    return min(fitting, key=lambda t: t.price_eur)


def tariff_by_sku(sku: str) -> Tariff:
    for tariff in ALL_TARIFFS:
        if tariff.sku == sku:
            return tariff
    raise KeyError(sku)

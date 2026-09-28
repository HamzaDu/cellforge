import csv
import pytest
from cellforge.materials import (
    MaterialSpec, theoretical_specific_capacity, load_materials, save_materials, get_material,
    spec_areal_capacity, active_material_mass, material_cost, bill_of_materials,
    COLUMNS, BLANK_TEMPLATE,
)


# --- Theoretical capacity (Faraday's law) -------------------------------------------

@pytest.mark.parametrize("molar_mass, n, expected", [
    (157.755, 1, 169.9),     # LiFePO4
    (97.871, 1, 273.8),      # LiCoO2
    (72.066, 1, 371.9),      # graphite, per C6
    (28.085, 3.75, 3578.6),  # Si -> Li15Si4
    (459.083, 3, 175.1),     # Li4Ti5O12
])
def test_theoretical_specific_capacity(molar_mass, n, expected):
    assert theoretical_specific_capacity(molar_mass, n) == pytest.approx(expected, rel=1e-3)


def test_theoretical_capacity_rejects_bad_input():
    with pytest.raises(ValueError):
        theoretical_specific_capacity(0, 1)
    with pytest.raises(ValueError):
        theoretical_specific_capacity(100, 0)


# --- MaterialSpec -------------------------------------------------------------------

def nmc(**kw):
    base = dict(name="NMC811-X", material_class="cathode_active", molar_mass_g_mol=97.279,
                electrons_per_formula_unit=1, practical_capacity_mah_g=200, true_density_g_cm3=4.75,
                supplier="Supplier X", price_per_kg=30.0, currency="GBP", price_date="2026-09-01",
                source_type="supplier_datasheet", source_reference="Datasheet DS-123")
    base.update(kw)
    return MaterialSpec(**base)


def test_spec_fills_theoretical_capacity():
    assert nmc().theoretical_capacity_mah_g == pytest.approx(275.5, rel=1e-3)
    assert nmc(theoretical_capacity_mah_g=270).theoretical_capacity_mah_g == 270  # given value kept


def test_spec_capacity_basis():
    s = nmc()
    assert s.capacity() == 200
    assert s.capacity("theoretical") == pytest.approx(275.5, rel=1e-3)
    with pytest.raises(ValueError):
        MaterialSpec(name="X", material_class="cathode_active").capacity()
    with pytest.raises(ValueError):
        s.capacity("average")


def test_validate_clean_record():
    assert nmc().validate() == []


@pytest.mark.parametrize("kw, level, text", [
    ({"material_class": "cathode"}, "error", "material_class"),
    ({"first_cycle_efficiency": 90}, "error", "fraction"),
    ({"currency": None}, "error", "currency"),
    ({"price_date": None}, "warning", "date"),
    ({"practical_capacity_mah_g": 300}, "warning", "higher than theoretical"),
    ({"tap_density_g_cm3": 5.0}, "error", "Tap density"),
    ({"source_reference": None}, "warning", "source"),
    ({"source_type": "blog"}, "error", "source_type"),
    ({"price_per_kg": -1.0}, "error", "negative"),
])
def test_validate_flags_problems(kw, level, text):
    issues = nmc(**kw).validate()
    assert any(l == level and text in m for l, m in issues), issues


# --- Library CSV ----------------------------------------------------------------------

def test_bundled_reference_library_loads_and_is_clean():
    lib = load_materials()
    assert {"NMC811", "LFP", "Graphite", "Silicon", "PVDF", "Copper foil"} <= set(lib)
    assert lib["LFP"].theoretical_capacity_mah_g == pytest.approx(169.9, rel=1e-3)
    assert all(level != "error" for s in lib.values() for level, _ in s.validate())


def test_blank_template_has_all_columns():
    with open(BLANK_TEMPLATE, newline="", encoding="utf-8") as fh:
        assert next(csv.reader(fh)) == COLUMNS


def test_save_and_reload_round_trip(tmp_path):
    lib = {"NMC811-X": nmc(), "PVDF": MaterialSpec(name="PVDF", material_class="binder", true_density_g_cm3=1.78)}
    path = tmp_path / "lib.csv"
    save_materials(lib, path)
    again = load_materials(path)
    assert again["NMC811-X"] == lib["NMC811-X"]
    assert again["PVDF"].price_per_kg is None


def test_load_treats_na_and_dash_as_blank(tmp_path):
    path = tmp_path / "lib.csv"
    path.write_text("name,material_class,practical_capacity_mah_g,price_per_kg,source_reference\n"
                    "Graphite-Y,anode_active,N/A,-,Datasheet G-1\n", encoding="utf-8")
    spec = load_materials(path)["Graphite-Y"]
    assert spec.practical_capacity_mah_g is None and spec.price_per_kg is None


def test_load_reports_errors_with_row_numbers(tmp_path):
    path = tmp_path / "lib.csv"
    path.write_text("name,material_class,first_cycle_efficiency\nA,cathode_active,90\nB,anode,\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        load_materials(path)
    assert "Row 2 (A)" in str(e.value) and "Row 3 (B)" in str(e.value)
    assert set(load_materials(path, strict=False)) == {"A", "B"}


def test_load_rejects_unknown_columns_and_bad_numbers(tmp_path):
    p1 = tmp_path / "a.csv"; p1.write_text("name,material_class,colour\nA,binder,red\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_materials(p1)
    p2 = tmp_path / "b.csv"; p2.write_text("name,material_class,price_per_kg\nA,binder,cheap\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_materials(p2)


def test_get_material_case_insensitive():
    lib = load_materials()
    assert get_material(lib, "nmc811").name == "NMC811"
    with pytest.raises(KeyError):
        get_material(lib, "Unobtainium")


# --- Value-chain calculations ---------------------------------------------------------------

def test_spec_areal_capacity():
    # 200 mAh/g * 15 mg/cm^2 * 0.96 = 2.88 mAh/cm^2 ; theoretical 275.5 * 0.015 * 0.96
    s = nmc()
    assert spec_areal_capacity(s, 15, 0.96) == pytest.approx(2.88)
    assert spec_areal_capacity(s, 15, 0.96, basis="theoretical") == pytest.approx(s.theoretical_capacity_mah_g * 0.015 * 0.96)
    with pytest.raises(ValueError):
        spec_areal_capacity(s, 15, 96)


def test_active_material_mass_and_cost():
    # 15 mg/cm^2 * 30 cm^2 * 10 sides * 0.96 = 4.32 g ; at 30 GBP/kg -> 0.1296 GBP
    m = active_material_mass(15, 30, 10, 0.96)
    assert m == pytest.approx(4.32)
    assert material_cost(nmc(), m) == pytest.approx(0.1296)
    with pytest.raises(ValueError):
        material_cost(MaterialSpec(name="X", material_class="binder"), 1.0)


def test_bill_of_materials():
    cathode = nmc()
    binder = MaterialSpec(name="PVDF", material_class="binder", price_per_kg=20.0, currency="GBP")
    foil = MaterialSpec(name="Al foil", material_class="current_collector")  # no price yet
    bom = bill_of_materials([(cathode, 4.32), (binder, 0.09), (foil, 1.0)], energy_wh=3.33)
    assert bom["currency"] == "GBP"
    assert bom["total_cost"] == pytest.approx(0.1296 + 0.0018)
    assert bom["unpriced"] == ["Al foil"]
    assert bom["total_mass_g"] == pytest.approx(5.41)
    assert bom["cost_per_kwh"] == pytest.approx((0.1296 + 0.0018) / 0.00333)
    assert bom["rows"][0]["kg_per_kwh"] == pytest.approx(0.00432 / 0.00333)
    assert bom["rows"][0]["cost_share"] == pytest.approx(0.1296 / 0.1314)


def test_bill_of_materials_rejects_mixed_currency():
    usd = MaterialSpec(name="LFP-Z", material_class="cathode_active", price_per_kg=10.0, currency="USD")
    with pytest.raises(ValueError):
        bill_of_materials([(nmc(), 1.0), (usd, 1.0)])

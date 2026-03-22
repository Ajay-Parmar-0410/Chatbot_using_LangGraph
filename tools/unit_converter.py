"""Unit conversion tool using pint."""

from langchain_core.tools import tool


@tool
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert a value between units.
    Supports length, weight, temperature, volume, speed, area.
    Examples: (100, 'km', 'miles'), (72, 'degF', 'degC'), (5, 'kg', 'lb')"""
    try:
        import pint
        ureg = pint.UnitRegistry()
        quantity = ureg.Quantity(value, from_unit)
        converted = quantity.to(to_unit)
        return f"{value} {from_unit} = {converted.magnitude:.4g} {to_unit}"
    except ImportError:
        return "Error: pint library not installed. Run: pip install pint"
    except Exception as e:
        return f"Error converting units: {str(e)}"

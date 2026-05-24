#!/usr/bin/env python3
"""Inspect recent KP snapshots from Supabase."""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from storage.supabase_client import _get_client, StorageError


def print_separator(title: str = "") -> None:
    """Print a section separator."""
    if title:
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    else:
        print(f"\n{'-'*70}\n")


def format_value(value: any, indent: int = 0) -> str:
    """Format value for display."""
    ind = "  " * indent
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        for k, v in value.items():
            formatted = format_value(v, indent + 1)
            lines.append(f"{ind}  {k}: {formatted}")
        lines.append(f"{ind}}}")
        return "\n".join(lines)
    elif isinstance(value, list):
        if not value:
            return "[]"
        return f"[...{len(value)} items]"
    else:
        return repr(value)


def inspect_snapshot(row: dict) -> None:
    """Print one KP snapshot in readable format."""
    kp_number = row.get("kp_number", "N/A")
    created_at = row.get("created_at", "N/A")

    print(f"KP Number: {kp_number}")
    print(f"Created: {created_at}")

    data = row.get("data", {})
    if isinstance(data, dict):
        print(f"\nTop-level keys in 'data' ({len(data)} keys):")
        for key in sorted(data.keys()):
            value = data[key]
            if isinstance(value, dict):
                print(f"\n  {key}:")
                for subkey in sorted(value.keys())[:5]:  # Show first 5 subkeys
                    subval = value[subkey]
                    print(f"      {subkey}: {repr(subval)}")
                if len(value) > 5:
                    print(f"      ... and {len(value) - 5} more keys")
            elif isinstance(value, list):
                print(f"  {key}: [{len(value)} items]")
            else:
                print(f"  {key}: {repr(value)}")
    else:
        print(f"'data' is not a dict: {data}")


def main() -> None:
    """Fetch and display last 3 KPs."""
    try:
        client = _get_client()
        print_separator("Fetching last 3 KP snapshots from Supabase")

        result = (
            client
            .table("kps")
            .select("*")
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )

        if not result.data:
            print("No KP records found.")
            return

        for idx, row in enumerate(result.data, 1):
            print_separator(f"Record {idx}/{len(result.data)}")
            inspect_snapshot(row)

        print_separator()
        print(f"[OK] Inspected {len(result.data)} record(s)")

    except StorageError as e:
        print(f"[ERROR] Storage error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

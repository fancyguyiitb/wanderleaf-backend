#!/usr/bin/env python
"""
Test the booking cancellation + refund flow.

Usage:
    python test_refund_flow.py --token YOUR_JWT_TOKEN --booking-id BOOKING_UUID
    python test_refund_flow.py --token YOUR_JWT_TOKEN --booking-id BOOKING_UUID --reason "Testing refund"

Or with env vars:
    ACCESS_TOKEN=... BOOKING_ID=... python test_refund_flow.py

Requirements:
    pip install requests
"""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

DEFAULT_BASE_URL = "http://localhost:8000"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test booking cancellation and refund flow"
    )
    parser.add_argument(
        "--token",
        default=os.getenv("ACCESS_TOKEN"),
        help="JWT access token (or set ACCESS_TOKEN env var)",
    )
    parser.add_argument(
        "--booking-id",
        default=os.getenv("BOOKING_ID"),
        help="Booking UUID (or set BOOKING_ID env var)",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", DEFAULT_BASE_URL),
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--reason",
        default="",
        help="Optional cancellation reason",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only fetch booking; do not cancel",
    )
    args = parser.parse_args()

    if not args.token:
        print("Error: --token or ACCESS_TOKEN required")
        sys.exit(1)
    if not args.booking_id:
        print("Error: --booking-id or BOOKING_ID required")
        sys.exit(1)

    base = args.base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json",
    }

    print("=" * 60)
    print("Booking Cancellation & Refund Flow Test")
    print("=" * 60)
    print(f"Base URL:  {base}")
    print(f"Booking:   {args.booking_id}")
    print(f"Dry run:   {args.dry_run}")
    print()

    # 1. GET booking details (before)
    print("1. Fetching booking (before cancel)...")
    resp = requests.get(
        f"{base}/api/v1/bookings/{args.booking_id}/",
        headers=headers,
    )
    if resp.status_code != 200:
        print(f"   FAILED: {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)
    before = resp.json()
    print(f"   Status: {before.get('status')} ({before.get('status_display', '')})")
    print(f"   Total:  ₹{before.get('total_price')}")
    print(f"   Can cancel: {before.get('can_be_cancelled')}")
    if before.get("refund_amount"):
        print(f"   Refund amount: ₹{before.get('refund_amount')}")
    if before.get("refund_failed"):
        print("   Refund failed: True (contact support)")
    print()

    if args.dry_run:
        print("Dry run. Not cancelling.")
        print(json.dumps(before, indent=2))
        return

    if not before.get("can_be_cancelled"):
        print("Booking cannot be cancelled. Skipping cancel step.")
        print(json.dumps(before, indent=2))
        return

    # 2. POST cancel
    print("2. Cancelling booking...")
    payload = {"reason": args.reason}
    resp = requests.post(
        f"{base}/api/v1/bookings/{args.booking_id}/cancel/",
        headers=headers,
        json=payload,
    )
    if resp.status_code != 200:
        print(f"   FAILED: {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)
    cancel_resp = resp.json()
    print(f"   Success: {cancel_resp.get('detail')}")
    if cancel_resp.get("refund_code"):
        print(f"   Refund code: {cancel_resp.get('refund_code')}")
    print()

    # 3. GET booking details (after)
    print("3. Fetching booking (after cancel)...")
    resp = requests.get(
        f"{base}/api/v1/bookings/{args.booking_id}/",
        headers=headers,
    )
    if resp.status_code != 200:
        print(f"   FAILED: {resp.status_code}")
        sys.exit(1)
    after = resp.json()
    print(f"   Status: {after.get('status')} ({after.get('status_display', '')})")
    print(f"   Cancelled at: {after.get('cancelled_at')}")
    print(f"   Cancellation reason: {after.get('cancellation_reason', '(none)')}")
    if after.get("refund_amount"):
        print(f"   Refund amount: ₹{after.get('refund_amount')}")
    if after.get("refunded_at"):
        print(f"   Refunded at: {after.get('refunded_at')}")
    if after.get("refund_status"):
        print(f"   Refund status: {after.get('refund_status')}")
    if after.get("refund_failed"):
        print("   Refund failed: True (contact support)")
    print()

    print("=" * 60)
    print("Full response (after cancel):")
    print(json.dumps(after, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()

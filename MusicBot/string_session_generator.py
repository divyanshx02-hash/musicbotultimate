#!/usr/bin/env python3
"""
MusicBot — String Session Generator
Run this script to generate Pyrogram string sessions for your assistant accounts.
"""
import asyncio

from pyrogram import Client


async def generate_session():
    print("=" * 50)
    print("  MusicBot String Session Generator")
    print("=" * 50)
    print()

    api_id = int(input("Enter your API_ID (from my.telegram.org): ").strip())
    api_hash = input("Enter your API_HASH (from my.telegram.org): ").strip()

    print()
    print("Starting Pyrogram session...")
    print("You will receive an OTP on your Telegram account.")
    print()

    async with Client(
        "session_generator",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True,
    ) as app:
        session_string = await app.export_session_string()
        me = await app.get_me()
        print()
        print("=" * 50)
        print(f"Session generated for: {me.first_name} (@{me.username})")
        print("=" * 50)
        print()
        print("Your STRING_SESSION:")
        print()
        print(session_string)
        print()
        print("Add this to your .env file as STRING_SESSION=<value>")
        print("Keep it SECRET — it gives full access to your account!")

    # Clean up temp file
    import os
    for f in ("session_generator.session", "session_generator.session-journal"):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    asyncio.run(generate_session())

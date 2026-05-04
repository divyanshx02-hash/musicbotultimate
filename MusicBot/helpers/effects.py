EFFECTS: dict[str, str] = {
    "Normal": "",
    "Bass Boost": "equalizer=f=60:width_type=o:width=2:g=10",
    "Nightcore": "atempo=1.25,asetrate=44100*1.25",
    "Vaporwave": "atempo=0.8,asetrate=44100*0.8,aecho=0.8:0.88:60:0.4",
    "8D Audio": "apulsator=hz=0.125",
    "Lofi": "lowpass=f=300,volume=0.8,aecho=0.9:0.9:1000:0.3",
    "Crystal Clear": "highpass=f=200,loudnorm",
    "Deep Bass": "equalizer=f=40:width_type=o:width=2:g=15",
    "Treble Boost": "equalizer=f=8000:width_type=o:width=2:g=8",
}

EFFECT_NAMES = list(EFFECTS.keys())


def get_filter(effect_name: str) -> str:
    return EFFECTS.get(effect_name, "")


def build_ffmpeg_filter_args(effect_name: str) -> list[str]:
    f = get_filter(effect_name)
    if not f:
        return []
    return ["-af", f]


def effects_keyboard(current_effect: str) -> list[list]:
    from pyrogram.types import InlineKeyboardButton
    buttons = []
    row = []
    for name in EFFECT_NAMES:
        mark = "✅ " if name == current_effect else ""
        row.append(InlineKeyboardButton(f"{mark}{name}", callback_data=f"effect|{name}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("« Back", callback_data="np_back")])
    return buttons

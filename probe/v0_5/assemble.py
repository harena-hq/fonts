# SPDX-License-Identifier: Apache-2.0
"""Assemble data/icons/table.json: one row per Segoe glyph, from the stages, the model picks and the
rules below. Rules settle families the pickers left open, and each still passes review like any row.

Usage: python probe/v0_5/assemble.py
"""
import json
import re

from stages import ROOT, SEED, load, stem

ICON = {v["s"] for v in json.loads((ROOT / "build/v0_5/fluent.json").read_text()).values()}
FAMILIES = [  # name pattern, Fluent stem (near)
    (r"^(Collate|Duplex)", "document_multiple"), (r"^(PPS|HolePunch|Stapling|PageMargin|PrintCustomRange)", "document"),
    (r"^WifiError", "wifi_warning"), (r"^WifiVPN", "wifi_lock"), (r"^(CtrlSpatial|Dpad)", "xbox_controller"),
    (r"^(StatusDataTransfer)", "arrow_swap"), (r"^StatusDual", "sim"), (r"^StatusSGLTEData", "cellular_data_1"),
    (r"^SpatialVolume", "speaker_2"), (r"^(Keyboardsettings|KeyboardSettings)", "keyboard"), (r"^DialShape", "circle"),
    (r"^(DeleteWord|DeleteLines)", "delete_lines"), (r"^(OverwriteWords|AddNewLine)", "text_edit_style"),
    (r"^SignalBarsVPN", "cellular_data_1"), (r"^NUIFP", "fingerprint"), (r"^StatusConnecting", "arrow_sync"), (r"^Multimedia", "music_note_1"),
    (r"^(Devices4|CompanionDeviceFramework|RememberedDevice)", "phone_laptop"), (r"^HWP", "text_edit_style"),
]
NEAR = {
    "QuarentinedItems": "shield_error", "TaskManagerApp": "pulse", "InkingCaret": "caret_down", "ChipCardCreditCardReader": "payment",
    "InternetSharing": "globe_arrow_forward", "SIPUndock": "keyboard_dock", "GripperTool": "re_order_dots_vertical",
    "Devices": "phone_laptop", "TimeLanguage": "globe_clock", "DataSense": "data_pie", "DeviceMonitorRightPic": "desktop",
    "DeviceMonitorLeftPic": "desktop", "DirectAccess": "globe_desktop", "MicLocationCombo": "mic", "SpeakerShare": "speaker_2",
    "AdjustHologram": "cube", "MobBatteryUnknown": "battery_warning", "NetworkTower": "cellular_data_1", "ToggleBorder": "square",
    "SliderThumb": "circle", "RTTLogo": "call", "DeliveryOptimization": "arrow_download", "TollSolid": "money",
    "HeadlessDevice": "server", "Component": "puzzle_cube", "DMC": "video", "NFCBadge": "nfc", "CRMScheduleReports": "calendar",
    "DefaultAPN": "globe", "Protractor": "ruler", "SyncError": "arrow_sync_dismiss", "WindowsStudioEffects": "video_background_effect",
    "DesktopLeafTwo": "desktop", "RotationLock": "lock_closed", "SDCard": "save", "TiltUp": "arrow_up", "StartPoint": "location",
    "ImageExport": "image_arrow_counterclockwise", "NarratorForward": "read_aloud", "NarratorForwardMirrored": "read_aloud",
    "SmartScreen": "shield", "VPNRoamingOverly": "lock_closed", "VirtualMachineGroup": "server_multiple", "ChromeAnnotate": "pen",
    "ReformatSparkle": "sparkle", "ActionFramework": "flash_flow", "SubscriptionAdd": "add_square", "FuzzyReading": "eye",
    "MusicSharingOff": "music_note_off_1", "EthernetWarning": "network_adapter", "LockFeedback": "lock_closed",
    "EmojiTabPeople": "people", "DocumentManagement": "document_folder", "DataSenseBar": "data_bar_horizontal",
    "LockscreenDesktop": "lock_closed", "DeviceDiscovery": "radar", "ButtonView2": "app_folder", "BodyCam": "camera",
    "Sensor": "radar", "Webcam2": "camera_dome", "Mouse": "cursor", "MediaStorageTower": "desktop_tower", "Network": "globe",
    "StorageNetworkWireless": "server", "ExploitProtectionSettings": "shield_settings", "FreeFormClipping": "cut",
    "USBSafeConnect": "usb_plug", "AppIconDefault": "apps", "SignalBarsAni1": "cellular_data_5", "SwipeRevealArt": "hand_draw",
    "StatusDataTransferRoaming": "arrow_swap", "LanguageChs": "local_language", "PinyinIMELogo2": "local_language",
}
TEXT = {
    "E1B8": ["Ч", "regular"], "E1BA": ["가", "light"], "E1BC": ["가", "light"], "E1BE": ["가", "regular"], "IBeam": ["I", "regular"],
    "IBeamOutline": ["I", "regular"], "DullSound": ["゛", "regular"], "HalfKatakana": ["カ", "regular"],
    "HalfKatakanaPrivateMode": ["カ", "regular"], "JpnRomanjiLock": ["R", "regular"], "JpnRomanjiShiftLock": ["R", "bold"],
    "CHTLanguageBar": ["繁", "regular"],
}
BY_POINT = {
    "E2B2": "window_multiple", "E320": "window_arrow_up", "E34D": "person_sparkle", "E3D8": "home", "E407": "usb_plug",
    "E62F": "window", "E65A": "cursor", "E65B": "mic_off", "E66C": "square", "E670": "wifi_4", "E671": "wifi_3",
    "E679": "text_bullet_list", "E67A": "developer_board", "E153": "square", "E1C0": "panel_left_expand", "E297": "text_bullet_list",
    "E298": "text_bullet_list", "E34B": "chat", "E3BA": "keyboard_off", "E3BB": "keyboard", "E2AC": "apps",
}
# Rows Fluent has only a generic language or keyboard icon for, and which draw a legend in Segoe.
LABELS = {"E7DE": ["日", "regular"], "E88B": ["가", "regular"], "E97D": ["가", "regular"], "E985": ["あ", "regular"],
          "EC45": ["あ", "regular"], "E981": ["倉", "regular"], "E984": ["速", "regular"], "E982": ["中", "regular"],
          "E983": ["英", "regular"], "E1BB": ["가", "light"]}
FORCE = {"E672": "wifi_lock", "E673": "wifi_lock"}  # read as Wi-Fi with a lock, which Fluent draws itself
BADGE = {"add": "add_circle", "dismiss": "dismiss_circle", "checkmark": "checkmark_circle", "warning": "warning",
         "error": "error_circle", "lock": "lock_closed", "prohibited": "prohibited", "clock": "clock", "heart": "heart",
         "charge": "flash"}


def ladder(point):
    """Battery ladders the pickers read as icons plus a badge; level follows the code point."""
    v = int(point, 16)
    if 0xE3C1 <= v <= 0xE3CB:
        return {"kind": "compose", "base": f"battery_charge_{v - 0xE3C1}", "badge": "heart"}
    if 0xE408 <= v <= 0xE412:
        return {"kind": "compose", "base": f"battery_{v - 0xE408}", "badge": "dismiss"}
    if 0xE413 <= v <= 0xE41D:
        return {"kind": "compose", "base": f"battery_{v - 0xE413}", "badge": "warning"}
    if 0xE44A <= v <= 0xE454:
        return {"kind": "compose", "base": f"battery_charge_{v - 0xE44A}", "badge": "heart"}
    return None


def main():
    rep, gname, blank, mirror, mapping, near, group_of = load()
    stages = json.loads((ROOT / "build/v0_5/stages.json").read_text())
    picks = json.loads((ROOT / ".private/v0_5/picks.json").read_text())
    esc = json.loads((ROOT / ".private/v0_5/escalated2.json").read_text())
    points = json.loads((ROOT / "data/v0_5/segoe-icons.json").read_text())["points"]
    members = {}
    for r in points:
        members.setdefault(str(r[1]), []).append(r[0])
    seed = SEED.read_text()
    holes = dict(re.findall(r"point: '([0-9A-F]+)',\s*segoe: '[^']*',\s*fluent: '[a-z0-9_]+',\s*part: 'holes',\s*with: '([0-9A-F]+)'", seed))
    fixes = json.loads((ROOT / "probe/v0_5/review_fixes.json").read_text())
    rows, missing = [], []
    for g, s in stages.items():
        name, point = s["name"], s["point"]
        row = {"points": members[g]}
        if name:
            row["name"] = name
        e = esc.get(g, {})
        if s["stage"] == "blank":
            row["kind"] = "blank"
        elif s["stage"] == "mirror":
            row.update(kind="mirror", of=rep[int(s["of"])], by="code")
        elif s["stage"] == "seed":
            row.update(kind="fluent", stem=stem(s["fluent"]), icon=s["fluent"], by="seed")
            if point in holes:
                row.update(kind="holes", **{"with": holes[point]})
                row.pop("stem")
        elif s["stage"] == "agreed":
            row.update(kind="fluent", stem=s["stem"], by="agreed")
        elif g in picks and not (name and re.match(r"(Vertical)?BatteryCharging\d", name)):
            row.update(kind="fluent", stem=picks[g], by="pick")
        else:
            row["by"] = "pick" if e.get("kind") not in (None, "NONE") else "rule"
            if point in FORCE:
                row.update(kind="fluent", stem=FORCE[point], by="rule")
            elif e.get("kind") in ("PICK", "NEAR"):
                row.update(kind="fluent", stem=e["stem"])
                if e["kind"] == "NEAR":
                    row["near"] = True
            elif e.get("kind") == "TEXT" and name in NEAR:
                row.update(kind="fluent", stem=NEAR[name], near=True)
            elif e.get("kind") == "TEXT":
                row.update(kind="text", text=e["text"], weight=e["weight"])
            elif e.get("kind") == "BADGE":
                native = f"{e['stem']}_{e['badge']}"
                row.update(kind="fluent", stem=native) if native in ICON else row.update(kind="compose", base=e["stem"], badge=e["badge"])
            elif point in TEXT or name in TEXT:
                t = TEXT.get(point) or TEXT[name]
                row.update(kind="text", text=t[0], weight=t[1])
            elif point in BY_POINT:
                row.update(kind="fluent", stem=BY_POINT[point], near=True)
            elif name in NEAR:
                row.update(kind="fluent", stem=NEAR[name], near=True)
            else:
                fam = next((f for pat, f in FAMILIES if name and re.match(pat, name)), None)
                if fam:
                    row.update(kind="fluent", stem=fam, near=True)
                else:
                    row["kind"] = "none"
        m = re.match(r"(Vertical)?Battery(Charging)?(\d+)$", name or "")
        if m:
            row.update(kind="fluent", stem=f"battery_{'charge_' if m[2] else ''}{m[3]}", by="rule")
            row.pop("near", None)
            if m[1]:
                row["rotate"] = 90
        if name == "VerticalBatteryUnknown":
            row.update(kind="fluent", stem="battery_warning", rotate=90, near=True, by="rule")
        if point in fixes["stems"]:
            row.pop("near", None)
            row.update(kind="fluent", stem=fixes["stems"][point], by="review")
            row.pop("icon", None)
        if point in fixes["styles"]:
            row["style"] = fixes["styles"][point]
        if point in LABELS:
            row.pop("stem", None), row.pop("icon", None), row.pop("near", None)
            row.update(kind="text", text=LABELS[point][0], weight=LABELS[point][1], by="review")
        if point == "E7C7":  # Fluent has one half star
            row.pop("stem", None), row.pop("icon", None)
            row.update(kind="mirror", of="E7C6", by="review")
        step = ladder(point)
        if step:
            row.pop("stem", None)
            row.update(step, by="rule")
        for key in ("stem", "base"):
            if key in row and row[key] not in ICON:
                missing.append((name or point, row[key]))
                for gone in ("stem", "base", "badge", "near", "rotate"):
                    row.pop(gone, None)
                row["kind"] = "none"
                break
        rows.append(row)
    rows.sort(key=lambda r: r["points"][0])
    doc = {"unit": "one row per Segoe Fluent Icons glyph", "rows": rows}
    (ROOT / "data/icons/table.json").write_text(json.dumps(doc, indent=0, ensure_ascii=False, sort_keys=True).replace(",\n", ", ").replace("{\n", "{").replace("\n}", "}") + "\n")
    count = {}
    for r in rows:
        key = r["kind"] + ("~near" if r.get("near") else "")
        count[key] = count.get(key, 0) + 1
    print(len(rows), count)
    print("missing", missing)
    print("none", [r.get("name") or r["points"][0] for r in rows if r["kind"] == "none"])


if __name__ == "__main__":
    main()

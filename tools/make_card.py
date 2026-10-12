#!/usr/bin/env python3
"""蹄兔名片產生器：一份客戶資料（JSON）→ hyrax.tw/c/<代碼>/ 的名片頁＋聯絡人檔。

用法：
  python3 -I tools/make_card.py 客戶資料.json           # 新客戶：自動配一個 6 碼代碼
  python3 -I tools/make_card.py 客戶資料.json --code abc234   # 改資料：沿用原本的代碼

規則（研究結論）：
- NFC 晶片永遠寫 https://hyrax.tw/c/<代碼>/，代碼隨機、不放姓名、永不回收（記在 tools/codes.txt）。
- 名片頁預設 noindex；聯絡人檔用 vCard 3.0、CRLF 換行、姓／名分開放。
- 頁尾一律有「由蹄兔製作」小字（客戶買「無標示版」時在 JSON 設 "badge": false）。
- 不連外部字型或 CDN，整頁一個檔。
"""
import html
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "card_template.html"
CODES = ROOT / "tools" / "codes.txt"
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # 去掉容易看錯的 i l o 0 1

ICONS = {
    "line": '<path d="M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.3 7.9.3.1.8.2.9.5.1.3.1.7 0 1l-.1.8c0 .2-.2.9.8.5s5.4-3.2 7.4-5.4C20.7 14.8 22 13 22 11c0-4.4-4.5-8-10-8Z"/>',
    "phone": '<path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.2 11.4 11.4 0 0 0 3.6.6 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1 11.4 11.4 0 0 0 .6 3.6 1 1 0 0 1-.3 1Z"/>',
    "email": '<path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2Zm0 4.2-8 5-8-5V6l8 5 8-5Z"/>',
    "instagram": '<path d="M12 7.3A4.7 4.7 0 1 0 16.7 12 4.7 4.7 0 0 0 12 7.3Zm0 7.8A3.1 3.1 0 1 1 15.1 12 3.1 3.1 0 0 1 12 15.1Zm6-8a1.1 1.1 0 1 1-1.1-1.1A1.1 1.1 0 0 1 18 7.1ZM21 8.2a5.4 5.4 0 0 0-1.5-3.8A5.4 5.4 0 0 0 15.8 3C14.3 2.9 9.7 2.9 8.2 3a5.4 5.4 0 0 0-3.8 1.5A5.4 5.4 0 0 0 3 8.2c-.1 1.5-.1 6.1 0 7.6a5.4 5.4 0 0 0 1.5 3.8A5.4 5.4 0 0 0 8.2 21c1.5.1 6.1.1 7.6 0a5.4 5.4 0 0 0 3.8-1.5 5.4 5.4 0 0 0 1.5-3.8c.1-1.5.1-6.1 0-7.5Zm-2 9.2a3.1 3.1 0 0 1-1.7 1.7c-1.2.5-4 .4-5.3.4s-4.1.1-5.3-.4A3.1 3.1 0 0 1 5 17.4c-.5-1.2-.4-4-.4-5.4s-.1-4.1.4-5.3A3.1 3.1 0 0 1 6.7 5c1.2-.5 4-.4 5.3-.4s4.1-.1 5.3.4A3.1 3.1 0 0 1 19 6.7c.5 1.2.4 4 .4 5.3s.1 4.2-.4 5.4Z"/>',
    "website": '<path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm6.9 6h-2.9a15.7 15.7 0 0 0-1.4-3.6A8 8 0 0 1 18.9 8ZM12 4a14 14 0 0 1 1.9 4h-3.8A14 14 0 0 1 12 4ZM4.3 14a8.2 8.2 0 0 1 0-4h3.4a16.5 16.5 0 0 0 0 4Zm.8 2h3a15.7 15.7 0 0 0 1.3 3.6A8 8 0 0 1 5.1 16ZM8 8H5.1a8 8 0 0 1 4.3-3.6A15.7 15.7 0 0 0 8 8Zm4 12a14 14 0 0 1-1.9-4h3.8A14 14 0 0 1 12 20Zm2.3-6H9.7a14.7 14.7 0 0 1 0-4h4.6a14.7 14.7 0 0 1 0 4Zm.3 5.6a15.7 15.7 0 0 0 1.4-3.6h2.9a8 8 0 0 1-4.3 3.6Zm1.7-5.6a16.5 16.5 0 0 0 0-4h3.4a8.2 8.2 0 0 1 0 4Z"/>',
    "share": '<path d="M18 16a3 3 0 0 0-2.4 1.2l-6.7-3.4a3 3 0 0 0 0-1.6l6.7-3.4A3 3 0 1 0 15 7a3 3 0 0 0 .1.8L8.4 11.2a3 3 0 1 0 0 3.6l6.7 3.4A3 3 0 1 0 18 16Z"/>',
}
LABELS = {"line": "加 LINE", "phone": "打電話", "email": "寄 Email", "instagram": "Instagram", "website": "網站"}
DEMO_VERBS = {"line": "加 LINE 好友", "phone": "打電話", "email": "寄 Email", "instagram": "打開 Instagram", "website": "打開官網"}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def svg(name):
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


def links(d):
    """依客戶資料產生可用的聯絡方式：[(種類, 網址)]，順序固定。"""
    out = []
    if d.get("line_url"):
        out.append(("line", d["line_url"]))
    if d.get("phone"):
        out.append(("phone", "tel:" + "".join(c for c in d["phone"] if c.isdigit() or c == "+")))
    if d.get("email"):
        out.append(("email", "mailto:" + d["email"]))
    if d.get("instagram"):
        out.append(("instagram", d["instagram"]))
    if d.get("website"):
        out.append(("website", d["website"]))
    return out


def control(kind, url, demo, cls=""):
    if demo:
        return f'<button type="button" class="{cls}" data-demo="{esc(DEMO_VERBS[kind])}" aria-label="{esc(LABELS[kind])}">'
    ext = ' target="_blank" rel="noopener"' if url.startswith("http") else ""
    return f'<a class="{cls}" href="{esc(url)}"{ext} aria-label="{esc(LABELS[kind])}">'


def close(demo):
    return "</button>" if demo else "</a>"


def vcard_escape(s):
    return str(s or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def make_vcard(d, page_url):
    lines = [
        "BEGIN:VCARD", "VERSION:3.0",
        f"N:{vcard_escape(d.get('surname'))};{vcard_escape(d.get('given'))};;;",
        f"FN:{vcard_escape(d['display_name'])}",
    ]
    if d.get("org"):
        lines.append(f"ORG:{vcard_escape(d['org'])}")
    if d.get("title"):
        lines.append(f"TITLE:{vcard_escape(d['title'])}")
    if d.get("phone") and not d.get("demo"):  # 示範名片不放電話，免得存到真人的號碼
        lines.append(f"TEL;TYPE=CELL:{d['phone']}")
    if d.get("email"):
        lines.append(f"EMAIL;TYPE=INTERNET,WORK:{d['email']}")
    lines.append(f"URL:{page_url}")
    if d.get("vcard_note"):
        lines.append(f"NOTE:{vcard_escape(d['vcard_note'])}")
    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


def new_code(used):
    while True:
        c = "".join(secrets.choice(ALPHABET) for _ in range(6))
        if c not in used:
            return c


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    used = set(CODES.read_text().split()) if CODES.exists() else set()
    if "--code" in args:
        code = args[args.index("--code") + 1]
    elif data.get("code"):
        code = data["code"]
    else:
        code = new_code(used | {"demo"})
    demo = bool(data.get("demo"))
    page_url = f"https://hyrax.tw/c/{code}/"
    lk = links(data)

    sats = []
    n = max(len(lk), 1)
    for i, (kind, url) in enumerate(lk):
        sats.append(f'<div class="sat" style="--a:{round(360 / n * i)}deg">{control(kind, url, demo)}{svg(kind)}{close(demo)}</div>')
    acts = [f'{control(k, u, demo, "act")}{svg(k)}{esc(LABELS[k])}{close(demo)}' for k, u in lk if k in ("line", "phone", "email")]
    acts.append(f'<button class="act" type="button" id="share">{svg("share")}分享名片</button>')
    term = "".join(f'<div>$ {esc(cmd)} <span>{esc(val)}</span></div>' for cmd, val in data.get("terminal", []))
    badge = ""
    if data.get("badge", True):
        badge = f'<p class="badge"><i aria-hidden="true"></i>這張名片由 <a href="https://hyrax.tw/?ref=card-{code}">蹄兔 hyrax.tw</a> 製作</p>'
    demo_bar = '<p class="demo-bar"><b>示範名片</b>・姓名與聯絡資料都是虛構的</p>' if demo else ""

    role = esc(data.get("title", ""))
    if data.get("org"):
        role = f"<b>{role}</b>・{esc(data['org'])}" if role else esc(data["org"])

    out = TEMPLATE.read_text(encoding="utf-8")
    repl = {
        "{{TITLE}}": esc(data.get("page_title") or f"{data['display_name']}｜數位名片"),
        "{{DESCRIPTION}}": esc(data.get("description") or f"{data['display_name']}的數位名片：一鍵存聯絡人、加 LINE。"),
        "{{PAGE_URL}}": page_url,
        "{{NAME}}": esc(data["display_name"]),
        "{{EN_NAME}}": esc(data.get("en_name", "")),
        "{{ROLE}}": role,
        "{{AVATAR}}": esc(data.get("avatar_text") or data["display_name"][:1]),
        "{{SATS}}": "\n        ".join(sats),
        "{{ACTIONS}}": "\n      ".join(acts),
        "{{TERMINAL}}": term,
        "{{TERMINAL_STYLE}}": "" if term else ' style="display:none"',
        "{{BADGE}}": badge,
        "{{DEMO_BAR}}": demo_bar,
        "{{VCF_NAME}}": esc(data["display_name"]) + ".vcf",
    }
    for k, v in repl.items():
        out = out.replace(k, v)
    left = [k for k in repl if k in out]
    assert not left, f"模板還有沒取代的欄位：{left}"

    dest = ROOT / "c" / code
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(out, encoding="utf-8")
    (dest / "contact.vcf").write_bytes(make_vcard(data, page_url).encode("utf-8"))
    if code not in used and code != "demo":
        with CODES.open("a") as f:
            f.write(code + "\n")
    print(f"✅ 名片已產生：{dest.relative_to(ROOT)}/")
    print(f"   NFC 晶片要寫入的網址：{page_url}")


if __name__ == "__main__":
    main()

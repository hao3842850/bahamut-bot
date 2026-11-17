import requests, re, json, os

# GitHub 版：Token 從 Secrets 讀，不寫在程式裡
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN", "")
LINE_TO = os.environ.get("LINE_TO", "")

BSN = 25908
SEEN_FILE = "seen_ids.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}
PATTERN = re.compile(r"韓版\s*\d{1,2}/\d{1,2}\s*NEW!?")

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)

def push_line(text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_TOKEN}", "Content-Type": "application/json"}
    body = {"to": LINE_TO, "messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=headers, json=body, timeout=10)
    print("LINE 推播:", r.status_code, r.text[:200])
    return r.status_code == 200

def main():
    if not LINE_CHANNEL_TOKEN or not LINE_TO:
        print("錯誤：沒有設定 LINE_CHANNEL_TOKEN / LINE_TO Secrets")
        return
    url = f"https://forum.gamer.com.tw/B.php?page=1&bsn={BSN}"
    print("正在抓:", url)
    r = requests.get(url, headers=HEADERS, timeout=15)
    items = re.findall(r'C\.php\?bsn=25908&snA=(\d+)[^>]*>([^<]+)</a>', r.text)
    print(f"抓到 {len(items)} 篇")
    seen = load_seen()
    new_count = 0
    for snA, title in items:
        title = title.strip()
        if snA in seen:
            continue
        seen.add(snA)
        if PATTERN.search(title):
            link = f"https://forum.gamer.com.tw/C.php?bsn=25908&snA={snA}"
            msg = f"韓版 NEW!\n{title}\n{link}"
            print("符合，推播:", title)
            push_line(msg)
            new_count += 1
    save_seen(seen)
    print(f"完成，推播 {new_count} 篇")

if __name__ == "__main__":
    main()

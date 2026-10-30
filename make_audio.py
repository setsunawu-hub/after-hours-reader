# After Hours Reader - 用 edge-tts 產生分角色音檔
# 用法：
#   python make_audio.py --chapters 1        只做第 1 章（先試聽）
#   python make_audio.py --chapters 1-10     做第 1 到 10 章
#   python make_audio.py                     全部 60 章（可隨時中斷，再執行會從沒做完的地方繼續）
import asyncio, json, os, sys, argparse
import edge_tts

# 角色 -> (聲音, 音高, 語速)
VOICES = {
    "Narrator":  ("en-GB-ThomasNeural", "+6Hz",  "+0%"),   # 旁白：略高的英式男聲
    "Finn":      ("en-GB-RyanNeural",   "+0Hz",  "+0%"),   # 芬恩：英式男聲
    "Felix":     ("en-IE-ConnorNeural", "+0Hz",  "+0%"),   # 菲利克斯：愛爾蘭男聲
    "Declan":    ("en-GB-OliverNeural", "-3Hz",  "+0%"),
    "Seamus":    ("en-GB-AlfieNeural",  "-8Hz",  "-6%"),
    "Liam":      ("en-GB-ElliotNeural", "+4Hz",  "+4%"),
    "MacDonald": ("en-GB-EthanNeural",  "-4Hz",  "+0%"),
    "Desmond":   ("en-GB-NoahNeural",   "-10Hz", "-12%"),
    "Male":      ("en-GB-EthanNeural",  "+0Hz",  "+0%"),
    "Maeve":     ("en-GB-LibbyNeural",  "+0Hz",  "+0%"),
    "Clodagh":   ("en-GB-SoniaNeural",  "+0Hz",  "+0%"),
    "Mother":    ("en-IE-EmilyNeural",  "-2Hz",  "-3%"),
    "Female":    ("en-GB-SoniaNeural",  "-4Hz",  "-3%"),
}
OUT = "audio"
CONCURRENCY = 4

def parse_range(s):
    if not s: return None
    if "-" in s:
        a, b = s.split("-"); return set(range(int(a), int(b) + 1))
    return {int(x) for x in s.split(",")}

async def one(sem, item, voices_ok):
    path = os.path.join(OUT, "%02d" % item["ch"], "%03d_%02d.mp3" % (item["i"], item["seg"]))
    if os.path.exists(path) and os.path.getsize(path) > 500:
        return "skip"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    v, pitch, rate = VOICES[item["speaker"]]
    text = item["text"].strip().strip("“”").strip()
    async with sem:
        for n in range(5):
            try:
                c = edge_tts.Communicate(text, v, rate=rate, pitch=pitch)
                await c.save(path + ".tmp")
                os.replace(path + ".tmp", path)
                return "ok"
            except Exception as e:
                err = str(e)[:80]
                await asyncio.sleep(2 + n * 2)
        print("  失敗：", path, err)
        return "fail"

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="")
    a = ap.parse_args()
    want = parse_range(a.chapters)
    items = json.load(open("manifest.json", encoding="utf-8"))
    if want: items = [x for x in items if x["ch"] in want]
    # 檢查聲音是否存在
    try:
        names = {v["ShortName"] for v in await edge_tts.list_voices()}
        for k, (v, _, _) in VOICES.items():
            if v not in names: print("警告：找不到聲音", v, "（角色", k, "）")
    except Exception as e:
        print("無法取得聲音清單（請確認網路）：", str(e)[:80]); return
    sem = asyncio.Semaphore(CONCURRENCY)
    total = len(items); done = 0; fails = 0
    tasks = [asyncio.create_task(one(sem, it, None)) for it in items]
    for t in asyncio.as_completed(tasks):
        r = await t; done += 1
        if r == "fail": fails += 1
        if done % 25 == 0 or done == total: print("進度 %d / %d" % (done, total))
    print("完成。失敗 %d 句。%s" % (fails, "重新執行一次即可補做失敗的句子。" if fails else "資料夾 audio 就是成果。"))

if __name__ == "__main__":
    asyncio.run(main())

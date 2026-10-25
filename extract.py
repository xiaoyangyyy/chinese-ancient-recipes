# -*- coding: utf-8 -*-
"""Build a public-domain Chinese recipe table."""
import csv
import os
import re

ROOT = r"D:\caipu"
TEXT = os.path.join(ROOT, "texts")
OUT = os.path.join(ROOT, "data")
DAI = os.path.join(TEXT, "代知阁")

PUNCT = "。，；：、！？"
SKIP_NAME = {
    "序", "目录", "叙", "卷上", "卷下", "上卷", "下卷", "又法", "又一法",
    "聚珍异馔", "诸般汤煎", "神仙服饵", "食疗诸病", "饮食类", "蔬食", "肉食",
}
STRONG = "肉鱼鸡鸭鹅汤羹圆糕饼面饭虾蟹蛋肚蹄肝肠腰脯卷翅参腐笋酒酱醋奶乳"
NEXT_OK = set("切用每以取将先配入加煮蒸炒烧煨闷腌同又法及和拌滚熬煎炸溜烩烤卤糟油盐酒水肉片块丁丝条汁汤葱姜蒜糖蜜粉面蛋鸡青红黄大少许斤两钱分勺杯碗锅笼右上同熟生白干乾冷热淡")
VERB = "切煮蒸炒烧煨闷腌拌熬煎炸烤卤糟酿炖滚炮炙熏渍烹制法"


def clean(text):
    return text.replace("\u3000", "").replace("\ufeff", "").strip()


def read(path):
    raw = open(path, "rb").read()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def is_title(line):
    line = clean(line)
    if not (2 <= len(line) <= 16):
        return False
    if any(ch in line for ch in PUNCT):
        return False
    if line in SKIP_NAME or line.startswith("卷"):
        return False
    if line.endswith(("类", "部", "集", "目录", "须知", "戒")):
        return False
    if line.endswith("单") and len(line) <= 4:
        return False
    return True


def titled_blocks(text, start=0):
    lines = text[start:].splitlines()
    rows = []
    i = 0
    while i < len(lines):
        title = clean(lines[i])
        if not is_title(title):
            i += 1
            continue
        body = []
        j = i + 1
        while j < len(lines):
            nxt = clean(lines[j])
            if nxt and is_title(nxt) and body:
                break
            if nxt:
                body.append(nxt)
            elif body:
                j += 1
                break
            j += 1
        blob = "".join(body)
        if len(blob) >= 12 and (any(ch in blob for ch in "。，") or any(ch in blob for ch in "切煮蒸炒烧煨腌用每")):
            rows.append((title, blob))
        i = j if j > i else i + 1
    return rows


def marked_blocks(text):
    rows = []
    current = None
    body = []

    def flush():
        if not current:
            return
        blob = "".join(body).strip()
        name = re.sub(r"[（(].*?[）)]", "", current).strip("　 ：:")
        name = name.split("：")[0].strip()
        if 2 <= len(name) <= 18 and len(blob) >= 12:
            rows.append((name, blob))

    for line in text.splitlines():
        raw = clean(line)
        if raw.startswith(("○", "●", "◎")):
            flush()
            rest = clean(raw[1:])
            current = rest.split("。")[0].split("：")[0].strip()
            body = [rest]
            continue
        head = clean(raw)
        if head in ("又法", "又一法", "一法") and current:
            flush()
            current = current.split("又")[0] + "又法"
            body = []
            continue
        if current and raw.strip():
            body.append(clean(raw))
    flush()
    return rows


def yinzhan_blocks(text):
    rows = []
    lines = [clean(ln) for ln in text.splitlines()]
    i = 0
    while i < len(lines):
        title = lines[i]
        if not is_title(title) or "卷" in title:
            i += 1
            continue
        body = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if nxt and is_title(nxt) and "卷" not in nxt and body:
                break
            if nxt and "卷" not in nxt:
                body.append(nxt)
            j += 1
        blob = "".join(body)
        if ("上件" in blob or "右件" in blob) and len(blob) >= 12:
            rows.append((title, blob))
        i = j if j > i else i + 1
    return rows


def method_colon_blocks(text):
    rows = []
    for line in text.splitlines():
        line = clean(line)
        match = re.match(r"^(?:作)?([\u4e00-\u9fff]{2,14}法)[:：](.+)$", line)
        if not match:
            continue
        name, body = match.group(1), match.group(2).strip()
        if len(body) >= 12:
            rows.append((name, name + "：" + body))
    return rows


MEASURE_CHARS = set("一二三四五六七八九十钱斤两升杯碗厅个数")
MODIFIER = set("酒酱醋油汤羹")
FINAL = set("肉鱼鸡鸭鹅蛋圆糕饼面饭虾蟹肚蹄肝肠腰脯腐笋")
STOP = set("也矣好耳同熟妙佳可了止之乎哉")


def dish_at(line, loose=False):
    if any(ch in line[:8] for ch in MEASURE_CHARS):
        return ""
    best = ""
    limit = min(6, len(line))
    for end in range(2, limit + 1):
        name = line[:end]
        if name[-1] not in STRONG:
            continue
        strong = [ch for ch in name if ch in STRONG]
        if len(strong) > 2:
            continue
        if len(strong) == 2 and not (strong[0] in MODIFIER and strong[1] in FINAL):
            continue
        if name.startswith(("又", "用", "以", "将", "每", "或", "加", "入", "切", "炒", "凡", "右", "上", "其", "此")):
            continue
        rest = line[end:end + 1]
        if not loose and rest and rest not in NEXT_OK and rest != name[-1]:
            continue
        best = name
    if not best:
        return ""
    later = line[len(best):len(best) + 6]
    if sum(ch in STRONG for ch in best + later) >= 3 and not any(ch in line[:10] for ch in "切用煮蒸炒烧煨闷腌"):
        return ""
    return best


def tiaoding_blocks(text):
    lines = [clean(ln) for ln in text.splitlines() if clean(ln)]
    starts = []
    for i, line in enumerate(lines):
        prev = lines[i - 1] if i else ""
        short_prev = (not prev) or len(prev) <= 16
        sentence_end = bool(prev) and prev[-1] in STOP
        name = dish_at(line, loose=short_prev)
        if not name:
            continue
        if short_prev or sentence_end:
            starts.append(i)
    rows = []
    for n, i in enumerate(starts):
        j = starts[n + 1] if n + 1 < len(starts) else len(lines)
        blob = "".join(lines[i:j])
        if len(blob) >= 12 and any(ch in blob for ch in VERB):
            rows.append((dish_at(lines[i], loose=True), blob))
    return rows


def colon_blocks(text):
    rows = []
    for para in re.split(r"\n\s*\n", text):
        para = clean(para)
        if "：" not in para:
            continue
        name, _, body = para.partition("：")
        name = name.strip()
        if is_title(name) and len(body) >= 12:
            rows.append((name, body))
    return rows


MEASURE = re.compile(
    r"[\u4e00-\u9fff]{1,8}(?:[一二三四五六七八九十百千万半两数\d]+(?:斤|两|钱|分|升|合|勺|枚|个|只|片|块|条|碗|杯|钟|盏|把|茎|颗|尾|头|脚子)?)"
)


FOOD_WORDS = (
    "鸡肉汤", "虾汤", "肉汤", "高汤", "清汤", "鸡汁", "台心菜", "大头菜", "陈大头菜",
    "猪爪", "猪筋", "猪蹄", "猪肝", "猪肚", "猪舌", "猪油", "猪肉", "猪皮", "火腿", "排骨", "精肉", "肥肉", "瘦肉", "里脊", "板油", "网油",
    "羊肉", "牛肉", "鸡肉", "鸭肉", "鹅肉", "鸡子", "鸡蛋", "鸭蛋", "皮蛋", "子鸡", "雏鸡",
    "鱼翅", "海参", "燕窝", "鲍鱼", "淡菜", "干贝", "虾仁", "虾米", "蟹粉", "鱼肚", "蹄筋", "鱼唇", "香蕈", "香菌", "蘑菇", "木耳",
    "竹笋", "冬笋", "春笋", "笋尖", "豆腐", "腐皮", "面筋", "粉丝", "粉皮", "紫菜", "海带", "海蜇",
    "甜酒", "黄酒", "白酒", "料酒", "花雕", "秋油", "酱油", "甜酱", "面酱", "清酱", "麻油", "香油", "素油", "花椒", "胡椒", "八角", "茴香", "桂皮", "陈皮",
    "粳米", "糯米", "大米", "面粉", "绿豆", "黄豆", "黑豆", "芝麻", "莲子", "红枣", "核桃", "杏仁", "栗子", "白果", "白粥", "雪水", "梅英", "杏实", "山栗", "橄榄", "龙眼", "荔枝", "圆眼", "芥末",
    "萝卜", "冬瓜", "黄瓜", "丝瓜", "茄子", "芋头", "莲藕", "白菜", "菠菜", "韭菜", "芹菜", "苋菜", "芥菜", "菜心", "豆芽", "芡粉", "豆粉", "藕粉", "菱粉", "纤粉", "米粉",
    "葱", "蒜", "姜", "醋", "盐", "糖", "蜜", "酒", "酱", "笋", "粥",
)


def foods_of(text):
    found = []
    occupied = [False] * len(text)
    for word in sorted(set(FOOD_WORDS), key=len, reverse=True):
        start = 0
        while True:
            index = text.find(word, start)
            if index < 0:
                break
            if word not in found and not any(occupied[index:index + len(word)]) and not any(word in prev for prev in found):
                found.append(word)
                for pos in range(index, index + len(word)):
                    occupied[pos] = True
            start = index + len(word)
            if len(found) >= 8:
                return "、".join(found)
    return "、".join(found)


def ingredients_of(body):
    if "上件" in body:
        head = body.split("上件", 1)[0]
    elif "右件" in body:
        head = body.split("右件", 1)[0]
    else:
        head = body
    found = []
    for piece in re.findall(r"[\u4e00-\u9fff]{1,8}（[^）]{1,24}）", head):
        name = piece.split("（", 1)[0]
        if name and name not in found:
            found.append(name)
    if found:
        return "、".join(found[:12])
    for piece in MEASURE.findall(head):
        name = re.sub(r"[一二三四五六七八九十百千万半两数\d]+(?:斤|两|钱|分|升|合|勺|枚|个|只|片|块|条|碗|杯|钟|盏|把|茎|颗|尾|头)?$", "", piece)
        name = name.strip("用取加配以和入")
        if 1 <= len(name) <= 6 and name not in found:
            found.append(name)
        if len(found) >= 8:
            break
    if found:
        return "、".join(found)
    return foods_of(head)


def method_of(body):
    for mark in ("上件", "右件"):
        if mark in body:
            return body.split(mark, 1)[1].lstrip("，,：: ")
    return body


def add(rows, seen, book, era, pairs):
    for name, body in pairs:
        name = clean(name)
        body = re.sub(r"\s+", "", body)
        if not (2 <= len(name) <= 16) or len(body) < 12:
            continue
        if name.endswith(("须知", "戒")) or name in SKIP_NAME:
            continue
        if name.startswith(("欲不可", "欲有所", "右以", "右每", "右件", "右为末")) or name in {
            "用皂矾法", "用胰法", "如荠菜", "各色菜𩔫豆腐", "头各色蔬菜酱", "各种酒", "共曲和饭", "如磨豆腐", "用虾让（酿）", "洗砚法",
        }:
            continue
        ing = ingredients_of(body)
        method = method_of(body)
        if not ing or not method.strip():
            continue
        key = (name, book, body)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "菜名": name,
            "原料": ing,
            "做法": method,
            "出处": "《%s》" % book,
            "时代": era,
            "原文": body,
        })


def yankuan_blocks(text):
    text = re.sub(r"\{\{[\s\S]*?\}\}", "", text, count=1)
    text = re.sub(r"<ref[\s\S]*?</ref>", "", text)
    text = re.sub(r"[（(]\d+[）)]", "", text)
    rows = []
    title = ""
    body = []

    def flush():
        blob = "".join(body).strip()
        if title and len(blob) >= 4 and any(ch in blob for ch in VERB):
            rows.append((title, blob))

    for raw in text.splitlines():
        line = clean(re.sub(r"^=+", "", raw).replace("=", ""))
        if not line or line.startswith(("词曰", "Header")):
            continue
        if line.endswith("类") or "作法" in line or line.endswith("略计"):
            flush()
            title = ""
            body = []
            continue
        if is_title(line) and "。" not in line and "，" not in line:
            flush()
            title = line
            body = []
            continue
        if title:
            body.append(line)
    flush()
    return rows


def load_yankuan():
    import subprocess
    import urllib.parse
    rows = []
    folder = os.path.join(TEXT, "筵款")
    os.makedirs(folder, exist_ok=True)
    pages = ["筵款豐饈依祥調鼎新錄/上册", "筵款豐饈依祥調鼎新錄/下册"]
    for page in pages:
        dest = os.path.join(folder, page.split("/")[-1] + ".json")
        if not (os.path.exists(dest) and os.path.getsize(dest) > 1000):
            url = "https://zh.wikisource.org/w/api.php?action=parse&page=" + urllib.parse.quote(page) + "&prop=wikitext&format=json"
            subprocess.run(
                ["curl.exe", "-sS", "--http1.1", "--ssl-no-revoke", "-f", "-L", "-A", "caipu/1.0",
                 "-x", "http://127.0.0.1:7897", "--max-time", "90", "-o", dest, url],
                check=False,
            )
        if not os.path.exists(dest):
            continue
        import json
        data = json.loads(open(dest, encoding="utf-8").read())
        rows.extend(yankuan_blocks(data["parse"]["wikitext"]["*"]))
    return rows


DISH_BAD = set("一每以用取将先凡右上其此及不从如若再后把宜视鲜预洗拣切自")
METHOD_ONLY = set("煮蒸炒烧煨腌熬煎炸烤卤糟酿炖炙熏渍烹晒捣滤造泡辣和拌浸调")


def dish_title(text):
    name = text.strip().strip("，。：、 ")
    if "制" in name and not name.startswith("制"):
        tail = name.split("制")[-1].strip("，。 ")
        if 2 <= len(tail) <= 8:
            name = tail
    if not (2 <= len(name) <= 8):
        return ""
    if any(ch in name for ch in PUNCT) or any(ch in name for ch in "者斤两斗升钱去洗滤月日时年"):
        return ""
    if "饮食" in name or "不可" in name:
        return ""
    if name and all(ch in METHOD_ONLY for ch in name):
        return ""
    if name[0] in DISH_BAD or name.startswith("又"):
        return ""
    if name.endswith(("制", "属", "部", "类", "论", "谱", "卷", "录", "目", "中", "忌", "时")):
        return ""
    if any(k in name for k in ("撰", "四库", "目次", "全书")):
        return ""
    return name


def has_method(blob):
    if len(blob) < 10 or blob.count("、") >= 8:
        return False
    strong = any(ch in blob for ch in "煮蒸炒烧煨腌熬煎炸烤卤糟酿炖炙熏渍烹晒捣滤造泡")
    weak = any(ch in blob for ch in "切拌和浸调饮") and any(ch in blob for ch in "盐酱油醋糖酒斤两钱升合")
    return strong or weak


def paragraph_lines(path):
    if path.endswith(".html"):
        html = open(path, encoding="utf-8", errors="replace").read()
        parts = re.findall(r"<p\b[^>]*>(.*?)</p>", html, flags=re.I | re.S)
        lines = []
        for part in parts:
            text = re.sub(r"<[^>]+>", "", part).replace("&nbsp;", "").replace("&#160;", "").strip()
            if text:
                lines.append(text)
        return lines
    text = read(path)
    return [clean(ln) for ln in text.splitlines() if clean(ln)]


def variant_rows(name, blob):
    pieces = re.split(r"(?<=[。])(?=一用|一、|又法|又方)", blob)
    if len(pieces) == 1:
        return [(name, blob)]
    rows = []
    if has_method(pieces[0]):
        rows.append((name, pieces[0]))
    for index, piece in enumerate(pieces[1:], 1):
        if has_method(piece):
            rows.append((name + ("又一法" if index == 1 else "又%d法" % index), piece))
    return rows or [(name, blob)]


def shidian_blocks(path):
    lines = paragraph_lines(path)
    if any("目次" in ln for ln in lines[:25]):
        for i, line in enumerate(lines):
            if dish_title(line) and has_method("".join(lines[i + 1:i + 3])):
                lines = lines[i:]
                break
    rows = []
    i = 0
    while i < len(lines):
        line = lines[i]
        head = dish_title(line)
        if head:
            body = []
            j = i + 1
            while j < len(lines) and not dish_title(lines[j]):
                mark = re.match(r"^([\u4e00-\u9fff]{2,8})[，。：]", lines[j])
                if mark and dish_title(mark.group(1)) and not any(ch in mark.group(1) for ch in "煮蒸炒烧煨腌熬煎炸烤"):
                    break
                body.append(lines[j])
                j += 1
            blob = "".join(body)
            if has_method(blob):
                rows.extend(variant_rows(head, blob))
            i = j
            continue
        match = re.match(r"^([\u4e00-\u9fff]{2,8})[，。：](.+)$", line)
        if match and dish_title(match.group(1)) and has_method(match.group(2)):
            rows.extend(variant_rows(dish_title(match.group(1)), match.group(2)))
        i += 1
    return rows


def qingbai_blocks(path):
    text = read(path)
    start = text.find("\n　　饮食类\n", 2000000)
    if start < 0:
        return []
    rest = text[start + 20:]
    mark = re.search(r"\n　　[\u4e00-\u9fff]{2,6}类\n", rest[500:])
    if not mark:
        return []
    chunk = text[start:start + 20 + 500 + mark.start()]
    lines = chunk.splitlines()
    rows = []
    i = 0
    while i < len(lines):
        line = lines[i].strip("　 \t")
        if not (2 <= len(line) <= 8) or any(ch in line for ch in PUNCT):
            i += 1
            continue
        if any(k in line for k in ("之", "人", "氏")) or line.endswith("类"):
            i += 1
            continue
        if "食" in line and len(line) >= 6:
            i += 1
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        body = []
        while j < len(lines):
            nxt = lines[j].strip("　 \t")
            nxt_title = (
                nxt and 2 <= len(nxt) <= 8 and not any(ch in nxt for ch in PUNCT)
                and "之" not in nxt and not nxt.endswith("类")
            )
            if nxt_title:
                break
            if nxt:
                body.append(nxt)
            elif body:
                break
            j += 1
        blob = "".join(body)
        head = blob[:24]
        if 20 <= len(blob) <= 420 and "。" in blob and "诗" not in head and has_method(blob):
            if blob.startswith(line):
                rows.append((line, blob))
        i = j if j > i else i + 1
    return rows


FOOD_NOUN = "肉鱼鸡鸭鹅羊牛猪鹿兔驴马驼虾蟹鳖鳝鳗鲍翅参肚蹄肝肠腰脯肺胰膏乳蛋卵汤羹糕饼面饭粥粉糖蜜瓜菜豆麦米笋藕菱芡荔梅枣栗桃杏梨橘橙蒜葱姜椒醋酱豉酥酪鹌鹑"
MENU_GENERIC = {
    "酒", "饭", "茶", "肉", "菜", "汤", "面", "粥", "水", "果", "果子", "点心", "小菜",
    "下酒", "下饭", "食品", "茶饭", "酒食", "菜蔬", "市食", "凉水", "酒名", "早饭",
    "午饭", "晚饭", "中饭", "夜饭", "热酒", "冷酒", "好酒", "美酒", "白酒", "清酒",
    "黄酒", "烧酒", "暖酒", "水酒", "杯酒", "斟酒", "案酒", "酒饭", "酒肉", "干饭",
    "水饭", "现成饭", "白饭", "米饭", "稀饭", "素饭", "白汤", "长休饭", "嗄饭", "嘎饭",
    "粥汤", "下饭菜", "夏饭", "汤饭", "羹饭", "行酒", "饿酒", "做饭", "剩饭", "和酒",
}
MENU_LEAD = ("冬间", "夏间", "春间", "秋间", "则有", "又有", "更有", "如有", "专卖", "添卖", "新法", "谓之", "名曰", "叫做", "卖", "如", "有", "或", "及")
PLATE_END = ("汤", "羹", "粥", "饼", "糕", "面", "饭", "酒", "脯", "肉", "鱼", "鸡", "鸭", "鹅", "圆", "肚", "酥", "酪", "虾", "蟹", "蛋", "笋", "饺", "馄饨", "烧卖", "包子", "馒头")


def strip_notes(text):
    text = re.sub(r"（[^）]{0,30}）", "", text)
    text = re.sub(r"【[^】]{0,30}】", "", text)
    text = re.sub(r"〔[^〕]{0,12}〕", "", text)
    return text.strip(" 、，。；：")


def polish_menu_name(token):
    name = strip_notes(token)
    changed = True
    while changed and name:
        changed = False
        for lead in MENU_LEAD:
            if name.startswith(lead) and len(name) > len(lead) + 1:
                name = name[len(lead):]
                changed = True
                break
    name = re.sub(r"(等|之类|下饭|事件)$", "", name).strip(" 、，。；：的了着")
    if not (2 <= len(name) <= 8):
        return ""
    if any(ch in name for ch in "。，；：、！？[]【】（）()"):
        return ""
    if name in MENU_GENERIC or name.endswith(("等", "类", "店", "铺", "街", "门", "人", "氏")):
        return ""
    if any(k in name for k in ("卖", "店", "铺", "街", "门", "前", "谓之", "宋刻", "同前", "不拘")):
        return ""
    if name[0] in DISH_BAD:
        return ""
    return name


def menu_runs(text):
    found = []
    for chunk in re.split(r"[。！？\n]", text):
        run = []
        for part in chunk.split("、"):
            name = polish_menu_name(part)
            if name:
                run.append(name)
            else:
                if len(run) >= 3:
                    found.append(run)
                run = []
        if len(run) >= 3:
            found.append(run)
    return found


def pairs_from_runs(runs, label):
    best = {}
    for run in runs:
        for i, name in enumerate(run):
            window = "、".join(run[max(0, i - 3):i + 4])
            ctx = (label + "：" + window) if label else window
            if name not in best or len(ctx) > len(best[name]):
                best[name] = ctx
    return list(best.items())


def chapter_menu(lines, titles):
    best = {}
    for i, line in enumerate(lines):
        bare = strip_notes(line.lstrip("○●◎")).strip()
        hit = ""
        for title in titles:
            if bare == title or bare.startswith(title):
                hit = title
                break
        if not hit:
            continue
        parts = []
        for nxt in lines[i + 1:i + 6]:
            s = nxt.strip()
            if not s:
                continue
            if s.startswith(("○", "●", "◎")) or (len(strip_notes(s)) <= 14 and "、" not in s and "。" not in s and "，" not in s):
                break
            parts.append(s)
            if s.count("、") >= 3:
                break
        blob = "".join(parts)
        if blob.count("、") < 3:
            continue
        for name, ctx in pairs_from_runs(menu_runs(blob), hit):
            if name not in best or len(ctx) > len(best[name]):
                best[name] = ctx
    return list(best.items())


def book_lines(rel):
    path = os.path.join(DAI, rel)
    if not os.path.exists(path):
        return []
    return [clean(ln) for ln in read(path).splitlines()]


def loose_method(blob):
    if len(blob) < 8:
        return False
    strong = any(ch in blob for ch in "煮煑蒸炒烧煨腌熬煎炸烤卤糟酿炖炙熏渍烹晒捣滤造泡瀹")
    weak = any(ch in blob for ch in "切拌和浸调") and any(ch in blob for ch in "盐醤油醋糖酒斤两钱升合")
    return strong or weak


def zhunsheng_blocks(path):
    lines = [clean(ln) for ln in read(path).splitlines()]
    starts = [i for i, ln in enumerate(lines) if ln.startswith("汤品类")]
    if not starts:
        return []
    start = starts[-1]
    end = next((i for i, ln in enumerate(lines) if i > start and ln.startswith("服食方类")), len(lines))
    rows = []
    title = ""
    body = []

    def flush():
        nonlocal title, body
        blob = "".join(body).strip()
        if title and loose_method(blob):
            rows.append((title, blob))
        title = ""
        body = []

    for ln in lines[start:end]:
        if not ln:
            continue
        if ln.startswith(("汤品类", "熟水类", "粥糜类", "果实", "脯鲊类", "家蔬", "野蔌", "酝造", "甜食", "饮馔")):
            flush()
            continue
        if "〔" in ln and ln.endswith("〕"):
            flush()
            continue
        raw = strip_notes(ln)
        variant = "又方" in ln or "一法" in ln[:4]
        if 2 <= len(raw) <= 14 and not any(ch in raw for ch in "。，；：、！？钱两斤升斗者"):
            flush()
            title = raw + ("又一法" if variant and "又一法" not in raw else "")
            continue
        if title:
            body.append(ln)
    flush()
    return rows


def shilin_blocks(path):
    lines = [clean(ln) for ln in read(path).splitlines()]
    start = next((i for i, ln in enumerate(lines) if "饮馔类" in ln), -1)
    if start < 0:
        return []
    end = next((i for i, ln in enumerate(lines) if i > start and "兽畜类" in ln), len(lines))
    rows = []
    title = ""
    body = []

    def flush():
        nonlocal title, body
        blob = "".join(body).strip()
        if title and loose_method(blob) and not title.startswith("又"):
            rows.append((title, blob))
        title = ""
        body = []

    for ln in lines[start:end]:
        if not ln:
            continue
        raw = strip_notes(ln).lstrip("○").strip()
        bad = any(k in raw for k in ("须知", "同前", "般数", "事件", "不拘", "不肯", "类", "兽畜"))
        if (not bad) and 2 <= len(raw) <= 12 and not any(ch in raw for ch in "。，；：、！？者钱两斤"):
            flush()
            title = raw
            continue
        if title:
            body.append(ln)
    flush()
    return rows


def yanshi_menu(path):
    lines = [clean(ln) for ln in read(path).splitlines()]
    rows = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("◎"):
            i += 1
            continue
        heading = strip_notes(line.lstrip("◎").split("（")[0])
        j = i + 1
        body = []
        while j < len(lines) and not lines[j].startswith("◎"):
            if lines[j]:
                body.append(lines[j])
            j += 1
        blob = "".join(body)
        for part in re.split(r"[、，]", heading):
            name = polish_menu_name(part)
            if not name:
                continue
            if name.endswith(("宫", "庙", "台", "灯", "摊", "赏", "王", "儿")) and name not in ("萨齐玛", "鸭儿广"):
                continue
            if "宫" in name or "之" in name:
                continue
            food_end = ("糕", "饼", "粥", "汤", "面", "酒", "鱼", "肉", "鸡", "鸭", "瓜", "枣", "笋", "蟹", "糖", "饭", "豆")
            extra = {"萨齐玛", "水乌他", "奶乌他", "温朴", "南糖", "冰糖壶卢", "菱角", "鸡头", "樱桃", "栗子", "银鱼", "冬笋", "大白菜", "鸭儿广", "海棠木瓜", "小鸭子", "小油鸡"}
            if name not in extra and not name.endswith(food_end):
                continue
            if len(blob) >= 12:
                rows.append((name, blob[:180]))
        i = j
    return rows


def dijing_menu(path):
    text = read(path).replace("\u3000", "")
    runs = []
    for chunk in re.split(r"[。！？]", text):
        if chunk.count("、") < 3:
            continue
        run = []
        for part in chunk.split("、"):
            name = polish_menu_name(part)
            if name and any(ch in name for ch in FOOD_NOUN):
                run.append(name)
            else:
                if len(run) >= 3:
                    runs.append(run)
                run = []
        if len(run) >= 3:
            runs.append(run)
    kept = []
    for name, ctx in pairs_from_runs(runs, "岁时"):
        if "之" in name or name.endswith(("梨", "枣", "瓜", "豆")) or (name.endswith("角") and not name.endswith("三角")):
            continue
        if name.endswith(("肉", "鱼", "鸡", "鸭", "糕", "饼", "汤", "粥", "面", "酒", "糖", "三角")):
            kept.append((name, ctx))
    return kept


MENU_END = (
    "汤", "羹", "粥", "饼", "糕", "面", "饭", "酒", "脯", "肉", "鱼", "鸡", "鸭", "鹅",
    "肚", "酥", "酪", "虾", "蟹", "蛋", "笋", "膏", "糖", "圆", "角", "鲊", "脍", "签",
    "粉", "肠", "肺", "肝", "腰", "子", "儿", "条", "丝", "蜜", "瓜", "豆", "枣", "梨",
    "柑", "藕", "姜", "梅", "桃", "杏", "李", "莲", "柿", "蔗", "橙", "橘", "豉", "酱",
    "醋", "血", "米", "馅", "炸", "炙", "丸", "露", "浆", "汁", "饮", "水", "茶", "春",
    "堂", "泉", "醅", "香", "螺", "鲍", "参", "翅", "腊", "头", "榴", "榄", "榧", "榛",
)
MENU_REJECT = (
    "官", "郎", "吏", "尚书", "太尉", "节度", "防御", "观察", "提举", "干办", "承旨",
    "祗候", "直殿", "御带", "御药", "知省", "进奉", "盘合", "宝器", "匹帛", "一条",
    "万贯", "宋刻", "陈刻", "同前", "簇送", "劝酒", "门外", "簋", "彻桌", "洋碟",
    "第一", "第二", "第三", "第四", "第五",
)


def split_glued(name):
    matched = re.match(r"^(.{2,6}?(?:糕|粥|饼|汤|羹))(.{2,6}?(?:糕|粥|饼|汤|羹))$", name)
    if matched:
        return [matched.group(1), matched.group(2)]
    return [name]


def menu_token(part, permissive=False, wine=False):
    part = strip_notes(part)
    part = re.sub(r"^[：:]+", "", part)
    part = re.sub(r"[一二三四五六七八九十百千万0-9]+(?:个|斤|口|合|盘|碟|瓶|事|味|件|碗|分)$", "", part)
    part = part.strip(" 、，。；：　 ")
    found = []
    for name in split_glued(part):
        if not (2 <= len(name) <= 8):
            continue
        if name.startswith(("诸", "第", "各")):
            continue
        if any(k in name for k in MENU_REJECT):
            continue
        if any(ch in name for ch in "。，；：、！？[]【】（）()"):
            continue
        if name in MENU_GENERIC and not (wine and name.endswith("酒")):
            continue
        foodish = any(ch in name for ch in FOOD_NOUN) or name.endswith(MENU_END)
        if wine or permissive or foodish:
            found.append(name)
    return found


def tokens_from_spaced(text, label, permissive=False, wine=False):
    best = {}
    text = re.sub(r"（[^）]{0,40}）", "", text)
    text = re.sub(r"【[^】]{0,24}】", "", text)
    pieces = re.split(r"[\u3000、，]|第[一二三四五六七八九十百]+盏", text)
    names = []
    for part in pieces:
        names.extend(menu_token(part, permissive=permissive, wine=wine))
    for i, name in enumerate(names):
        window = "、".join(names[max(0, i - 3):i + 4])
        ctx = label + "：" + window
        if name not in best or len(ctx) > len(best[name]):
            best[name] = ctx
    return best


def wulin_menu(known):
    path = os.path.join(DAI, "史藏", "地理", "武林旧事.txt")
    if not os.path.exists(path):
        return []
    lines = read(path).splitlines()
    heads = ["市食", "果子", "菜蔬", "粥", "凉水", "糕", "蒸作从食", "诸色酒名"]
    best = {}
    for i, line in enumerate(lines):
        compact = re.sub(r"\s+", "", line)
        hit = ""
        for title in heads:
            if compact == title:
                hit = title
                break
        if not hit or i + 1 >= len(lines):
            continue
        blob = lines[i + 1].split("。")[0]
        wine = hit == "诸色酒名"
        best.update(tokens_from_spaced(blob, hit, permissive=True, wine=wine))
    text = read(path)
    start = text.find("供进御筵")
    stop = text.find("进奉盘合", start if start > 0 else 0)
    if start > 0 and stop > start:
        best.update(tokens_from_spaced(text[start:stop], "张俊供筵", permissive=False))
    return list(best.items())


def fansheng_menu():
    path = os.path.join(DAI, "史藏", "志存记录", "西湖老人繁胜录.txt")
    if not os.path.exists(path):
        return []
    best = {}
    for line in read(path).splitlines():
        if line.count("、") < 8:
            continue
        kept = tokens_from_spaced(line.split("。")[0], "市食", permissive=False)
        if len(kept) >= 7:
            for name, ctx in kept.items():
                if name not in best or len(ctx) > len(best[name]):
                    best[name] = ctx
    return list(best.items())


def yangzhou_menu():
    path = os.path.join(DAI, "史藏", "志存记录", "扬州画舫录.txt")
    if not os.path.exists(path):
        return []
    best = {}
    for line in read(path).splitlines():
        if "五簋碗" not in line and "第一等奶子茶" not in line and "满汉席" not in line:
            continue
        label = "满汉席" if "满汉席" in line or "五簋碗" in line else "食次"
        for name, ctx in tokens_from_spaced(line, label, permissive=False).items():
            if name not in best or len(ctx) > len(best[name]):
                best[name] = ctx
    return list(best.items())


QINGYI_DOORS = ("百果门", "蔬菜门", "鱼门", "酒浆门", "馔羞门")
QINGYI_SKIP = {
    "邹平公食宪章", "雁椟", "八珍主人", "张手美家", "建康七妙", "花餻员外",
    "花糕员外", "小四海", "土筵席", "玉杵羮金绵鲊", "玉杵羹金绵鲊",
}


def remember(best, name, body):
    name = name.strip("，。：、 ")
    body = re.sub(r"\s+", "", body)
    if not (2 <= len(name) <= 12) or name in QINGYI_SKIP or name in MENU_GENERIC:
        return
    if any(ch in name for ch in "。，；：、！？[]【】（）()"):
        return
    if name.endswith(("门", "注", "员外")) or "如上" in name or name.startswith("诸"):
        return
    old = best.get(name, "")
    if len(body) > len(old):
        best[name] = body[:180]


def emit_named(rows, seen, book, era, best):
    methods = []
    menus = []
    for name, body in best.items():
        if name in {"炮", "渍", "熬", "糁"}:
            body = re.sub(r"\s+", "", body)
            if len(body) < 12 or (name, book, body) in seen:
                continue
            seen.add((name, book, body))
            rows.append({
                "菜名": name,
                "原料": ingredients_of(body),
                "做法": method_of(body),
                "出处": "《%s》" % book,
                "时代": era,
                "原文": body,
            })
            continue
        if len(body) >= 12:
            methods.append((name, body))
        elif len(body) >= 8:
            menus.append((name, body))
    add(rows, seen, book, era, methods)
    add_menu(rows, seen, book, era, menus)


def qingyi_best(path):
    lines = read(path).splitlines()
    marks = []
    for i, line in enumerate(lines):
        bare = line.replace("\u3000", "")
        if "门（" in bare:
            marks.append(i)
    best = {}
    for n, start in enumerate(marks):
        bare = lines[start].replace("\u3000", "")
        if not any(door in bare for door in QINGYI_DOORS):
            continue
        end = marks[n + 1] if n + 1 < len(marks) else len(lines)
        door = next(door for door in QINGYI_DOORS if door in bare)
        i = start + 1
        while i < end:
            raw = lines[i].strip().replace("\u3000", "").strip("，,")
            if re.fullmatch(r"[\u4e00-\u9fff]{2,8}", raw):
                body = []
                j = i + 1
                while j < end:
                    nxt = lines[j].strip()
                    if not nxt:
                        j += 1
                        if body:
                            break
                        continue
                    nxt_name = nxt.replace("\u3000", "").strip("，,")
                    if re.fullmatch(r"[\u4e00-\u9fff]{2,8}", nxt_name):
                        break
                    body.append(nxt)
                    j += 1
                blob_body = "".join(body)
                cook = "浸煎煮蒸酿炙渍熬炒烹炮腌"
                if door in ("百果门", "蔬菜门", "鱼门") and not any(ch in blob_body for ch in cook):
                    i = j
                    continue
                if door == "酒浆门" and "酒" not in raw + blob_body and "酿" not in blob_body:
                    i = j
                    continue
                if "之语" in blob_body or "亥卯" in raw:
                    i = j
                    continue
                remember(best, raw, blob_body or door)
                i = j
                continue
            i += 1
        if door != "馔羞门":
            continue
        blob = "\n".join(lines[start + 1:end])
        for match in re.finditer(r"([\u4e00-\u9fff]{2,10})（([^）]{2,40})）", blob):
            if match.group(1) in ("罗饭", "王羮亥卯未相粥"):
                continue
            remember(best, match.group(1), door + "：" + match.group(1) + "，" + match.group(2))
        for part in re.split(r"[\u3000\t]+", blob):
            part = re.sub(r"（[^）]{0,40}）", "", part)
            part = part.strip("，。：、 \n")
            if not re.fullmatch(r"[\u4e00-\u9fff]{2,10}", part):
                continue
            if not any(ch in part for ch in FOOD_NOUN + "脍臛餤饀餻圆炙脯"):
                continue
            if "亥卯" in part or part.startswith("王羮"):
                continue
            if any(old != part and old in part and len(part) > len(old) + 1 for old in best):
                continue
            split = re.match(r"^(.{3,10}[饼糕羹炙脯鲊臛餤饤饭粥面酥])(.{2,4})$", part)
            if split and split.group(2)[0] not in "子儿":
                remember(best, split.group(1), door + "：" + split.group(1))
                remember(best, split.group(2), door + "：" + split.group(2))
                continue
            if part in ("罗饭", "王羮亥卯未相粥") or "亥卯" in part:
                continue
            remember(best, part, door + "：" + part)
    return best


def name_starts_shen(food):
    return food.startswith("肾") and len(food) > 3 and food[1:].endswith(("酒", "粥"))


def shouqin_best(path):
    lines = [ln.strip().replace("\u3000", "") for ln in read(path).splitlines()]
    ends = ("粥", "酒", "汤", "脯", "饼", "糕", "羹", "面", "饭")
    best = {}
    i = 0
    while i < len(lines):
        line = re.sub(r"【[^】]*】", "", lines[i]).strip()
        line = re.sub(r"方$", "", line)
        if not line or "。" in line or "■" in line or line.startswith("右"):
            i += 1
            continue
        name = ""
        cut = set("疾治服痛虚损利宜常诸聋弱泽力气志血涩满喘唾痹痿瘦胀烦热羸补衄衂急浓令及咽喉春胸膈痰壅噎身壮热多痔肥白不暗明风发差每右用中强止下食嗽便汁能通粘熟末沸骨筋")
        if line.endswith(ends) and (line.startswith(("食治", "治")) or re.fullmatch(r"[\u4e00-\u9fff]{2,8}", line)):
            food = ""
            for n in range(len(line) - 1, 0, -1):
                if line[n - 1] in cut:
                    food = line[n:]
                    break
            if 2 <= len(food) <= 6 and food.endswith(ends) and not any(ch in food for ch in cut):
                name = food[1:] if name_starts_shen(food) else food
            elif re.fullmatch(r"[\u4e00-\u9fff]{2,8}", line) and not any(ch in line for ch in cut):
                name = line
        if not name:
            i += 1
            continue
        body = []
        j = i + 1
        while j < len(lines) and len("".join(body)) < 160:
            nxt = lines[j]
            if not nxt:
                j += 1
                if body:
                    break
                continue
            nxt_clean = re.sub(r"【[^】]*】", "", nxt)
            if re.fullmatch(r"[\u4e00-\u9fff]{2,8}", nxt_clean) and nxt_clean.endswith(ends):
                break
            if nxt.startswith("食治") or nxt.startswith("右件"):
                break
            body.append(nxt)
            j += 1
        blob = "".join(body)
        if loose_method(blob) or any(ch in blob for ch in "煮煎米盐酥蜜糖"):
            remember(best, name, blob)
        i = j if j > i else i + 1
    return best


def yehang_best(path):
    lines = [ln.strip().replace("\u3000", "") for ln in read(path).splitlines()]
    start = next((i for i, ln in enumerate(lines) if ln == "饮食"), -1)
    if start < 0:
        return {}
    best = {}
    ends = ("酒", "觞", "醪", "鲭", "羹", "脯", "炙", "饼", "汤", "饭", "糕", "粥", "面")
    skip = {"名酒", "饮食", "酒", "茶", "八珍", "五谷", "酪奴", "汤社", "茗战", "水厄", "欲炙", "太羹玄酒"}
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if line in ("珍宝", "宫室", "服饰"):
            break
        if "中山酒" in line and "昆仑觞" in line:
            for name in (
                "中山酒", "兰生酒", "缥醪", "桑落酒", "千里酒", "三辰酒", "天圣酒", "鱼儿酒",
                "翠涛", "屠苏", "玉薤", "红粱新酝", "昆仑觞", "碧芳酒", "抱瓮醪", "秋露",
                "黄娇", "瓮中云", "洞庭春", "罗浮春", "真一酒", "玉清堂", "长春法酒", "冰堂春",
            ):
                if name in line:
                    remember(best, name, line[:120])
        if re.fullmatch(r"[\u4e00-\u9fff]{2,8}", line) and line not in skip and "茶" not in line:
            if line.endswith(ends):
                body = []
                j = i + 1
                while j < len(lines) and lines[j] and not re.fullmatch(r"[\u4e00-\u9fff]{2,8}", lines[j]):
                    body.append(lines[j])
                    j += 1
                    if len("".join(body)) > 100:
                        break
                remember(best, line, "".join(body) or line)
                i = j
                continue
        i += 1
    return best


def neize_best(path):
    lines = [ln.replace("\u3000", "").strip() for ln in read(path).splitlines()]
    best = {}
    for bare in lines:
        if not bare.startswith(("饭：", "羞，", "食，蜗", "牛修", "饮重醴", "鹑羹")):
            continue
        for part in re.split(r"[，。：而]", bare):
            part = part.strip()
            if not re.fullmatch(r"[\u4e00-\u9fff]{2,6}", part):
                continue
            if any(k in part for k in ("用", "宜", "曰", "不", "凡", "视", "实蓼", "皆有", "或以", "饮重", "卵盐", "为醴")):
                continue
            if part.endswith("清糟") and len(part) >= 4:
                part = part[:-2]
            if part == "牛修鹿脯":
                remember(best, "牛修", bare[:90])
                remember(best, "鹿脯", bare[:90])
                continue
            if any(ch in part for ch in FOOD_NOUN + "脍炙胾醢糗饵酏羹醴脯修肤豚"):
                remember(best, part, bare[:90])
    for bare in lines:
        if bare.startswith("淳熬，") and "淳母，" in bare and "炮，取" in bare:
            head, rest = bare.split("淳母，", 1)
            mother, roast = rest.split("炮，取", 1)
            remember(best, "淳熬", head)
            remember(best, "淳母", "淳母，" + mother)
            best["炮"] = re.sub(r"\s+", "", "炮，取" + roast)[:180]
            continue
        for prefix, name in (
            ("捣珍，", "捣珍"), ("渍取", "渍"), ("为熬，", "熬"), ("糁取", "糁"), ("肝膋，", "肝膋"),
        ):
            if bare.startswith(prefix):
                if len(name) >= 2:
                    remember(best, name, bare)
                else:
                    best[name] = re.sub(r"\s+", "", bare)[:180]
    return best


def chuci_best(path):
    names = (
        "肥牛之腱", "吴羹", "胹鳖", "炮羔", "鹄酸", "臇凫", "煎鸿鸧", "露鸡", "臛蠵",
        "粔籹", "蜜饵", "餦餭", "瑶浆", "冻饮", "菰粱", "豺羹", "鲜蠵", "甘鸡", "楚酪",
        "醢豚", "苦狗", "脍苴蓴", "吴酸蒿蒌", "炙鸹", "烝凫", "煔鹑", "吴醴", "白糵", "楚沥", "黄粱",
    )
    best = {}
    for line in read(path).splitlines():
        bare = line.strip()
        if "些" not in bare and "只" not in bare:
            continue
        for name in names:
            if name in bare:
                remember(best, name, bare)
    return best


def benwei_best(path):
    text = read(path)
    start = text.find("肉之美者")
    if start < 0:
        return {}
    seg = re.sub(r"【[^】]*】", "", text[start:start + 2600])
    best = {}
    tails = set("唇炙翠掔约鱄鲕苹华芸芹菁姜桂菌醢盐卵禾粟穄秬露井橘柚丸草叶")
    for match in re.finditer("之", seg):
        after = seg[match.end():match.end() + 1]
        if after not in tails:
            continue
        before = seg[max(0, match.start() - 2):match.start()]
        if not re.fullmatch(r"[\u4e00-\u9fff]{2}", before) or "之" in before:
            continue
        if any(k in before for k in "者美曰凡"):
            continue
        remember(best, before + "之" + after, seg[max(0, match.start() - 10):match.start() + 18])
    for name in ("朱鼈", "嘉树", "土英"):
        if "名曰" + name in seg:
            at = seg.find("名曰" + name)
            remember(best, name, seg[at:at + 16])
    return best


def youyang_best(path):
    text = read(path)
    start = text.find("卷七 酒食")
    stop = text.find("卷七 医", start if start > 0 else 0)
    if start < 0 or stop < start:
        return {}
    seg = text[start:stop]
    best = {}
    listed = seg.split("饼谓之托")[0]
    for part in re.split(r"[、。\n]", listed):
        part = re.sub(r"（[^）]{0,24}）", "", part).strip()
        if not re.fullmatch(r"[\u4e00-\u9fff]{2,8}", part):
            continue
        if any(k in part for k in ("谓之", "也", "衣冠", "今", "有能", "卷七", "饣", "犭", "扌")):
            continue
        if any(ch in part for ch in FOOD_NOUN + "脍炙脯羹鲭酒菹腊"):
            at = listed.find(part)
            remember(best, part, listed[max(0, at - 6):at + len(part) + 18])
    for match in re.finditer(r"([\u4e00-\u9fff]{2,8}法)[:：]([\u4e00-\u9fff]{6,80})", seg):
        name = match.group(1)
        if any(ch in name for ch in "饼粥羹饭面酒鲊脯肉炙菹"):
            remember(best, name, name + "：" + match.group(2))
    for name in ("萧家馄饨", "庚家棕子", "冷胡突", "鳢鱼臆", "连蒸诈草", "草皮索饼", "骏鬃驼峰炙"):
        if name in seg:
            at = seg.find(name)
            remember(best, name, seg[max(0, at - 8):at + 24])
    return best


def beihu_best(path):
    lines = read(path).splitlines()
    keep = ("象鼻炙", "鹅毛脡", "桄榔炙", "红盐", "睡菜", "水韭", "蕹菜", "斑皮竹笋", "变柑", "山橘子", "橄榄子", "山胡桃", "白杨梅", "偏核桃", "红梅")
    best = {}
    i = 0
    while i < len(lines):
        bare = lines[i].strip().replace("\u3000", "")
        if bare.startswith("○"):
            name = bare.lstrip("○").split("（")[0].strip()
            body = []
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("○"):
                if lines[j].strip():
                    body.append(lines[j].strip())
                j += 1
            if name.startswith("米") and "麦并" in bare:
                name = "米䴹"
            if name in keep or name == "米䴹":
                remember(best, name, "".join(body))
            i = j
            continue
        i += 1
    return best


def guangdong_best(path):
    text = read(path)
    start = text.find("卷十四食语")
    if start < 0:
        start = text.find("食语")
    stop = text.find("●卷", start + 20 if start > 0 else 0)
    if start < 0:
        return {}
    blob = text[start:stop if stop > start else start + 80000]
    best = {}
    for name in (
        "温淘", "冷淘", "乾饼", "蓑衣油饼", "水晶包", "卷蒸", "馒头", "水面",
        "糖梅", "糖榄", "燕窝菜", "火酒", "石耳", "真一法酒", "荼蘼露",
    ):
        if name in blob:
            at = blob.find(name)
            remember(best, name, blob[max(0, at - 12):at + 40])
    return best


def jingchu_best(path):
    lines = [ln.strip().replace("\u3000", "") for ln in read(path).splitlines()]
    best = {}
    for i, bare in enumerate(lines):
        matched = re.match(r"^（[^）]{1,8}）\s*([\u4e00-\u9fff、]{2,12})$", bare)
        if not matched:
            continue
        body = [bare]
        j = i + 1
        while j < len(lines) and not lines[j].startswith("（") and len("".join(body)) < 80:
            if lines[j]:
                body.append(lines[j])
            j += 1
        for name in re.split(r"[、]", matched.group(1)):
            if not name.endswith(("酒", "糕", "羹", "粥", "饼", "脍", "汤")):
                continue
            extra = "".join(body)
            if len(extra) < 12:
                for later in lines:
                    if name in later and later != bare and len(later) > 12:
                        extra = later[:100]
                        break
            remember(best, name, extra)
    return best


def minggong_best(path):
    text = read(path)
    start = text.find("饮食好尚")
    if start < 0:
        return {}
    stop = text.find("○", start + 8)
    seg = text[start:stop if stop > start else start + 6000]
    best = {}
    for name in (
        "椒柏酒", "水点心", "扁食", "春饼", "元宵", "烧鹅", "灌肠", "月饼", "团圆饼",
        "苏叶汤", "腊八粥", "炙羊肉", "牛乳", "乳饼", "奶皮", "油蒸饼", "浑酒",
        "柿饼", "驴头肉", "汤圆", "爆炒羊肚子", "冷片羊", "羊双肠", "脆圆子",
        "八宝攒汤", "米烂汤", "薫虫", "芦芽汤", "桃花鲊", "烧笋鹅", "凉糕",
        "不落夹", "包儿饭", "捻转", "粽子", "过水面", "雄鸭腰子", "朱砂雄黄菖蒲酒",
    ):
        if name in seg:
            at = seg.find(name)
            remember(best, name, seg[max(0, at - 16):at + 28])
    return best


def novel_menu(path):
    text = read(path)
    pat = re.compile(
        r"[盘碟碗盒](?:儿|子)?(?:(?:腌|炒|蒸|煮|炸|炖|烩|烤|腊|卤|拌|糟|煎)的)?([\u4e00-\u9fff]{2,8})"
    )
    best = {}
    for match in pat.finditer(text):
        name = match.group(1)
        if name[0] in "子是儿堆高裂都装讨呷盘摆":
            continue
        if any(ch in name for ch in "吃来去里的了着并毡那"):
            continue
        if name.endswith(("上面", "下面", "里面", "桌面", "外面", "下饭", "头面")):
            continue
        if any(k in name for k in ("下饭", "摆在", "恰恰", "托出", "过饭", "淡饭", "讨饭", "衣饭", "饱饭", "半饭", "现成", "案酒", "斟", "嗄饭", "嘎饭", "水饭", "按酒", "点心酒")):
            continue
        if not any(name.endswith(end) for end in PLATE_END):
            continue
        if name in MENU_GENERIC or name[0] in "一二三四五六七八九十个只条和":
            continue
        if name.startswith("酒") and not name.endswith("酒"):
            continue
        if "和" in name and len(name) > 4:
            continue
        start = max(0, match.start() - 12)
        ctx = re.sub(r"\s+", "", text[start:match.end() + 16])
        if len(ctx) < 8:
            continue
        if name not in best or len(ctx) > len(best[name]):
            best[name] = ctx
    return list(best.items())


def add_menu(rows, seen, book, era, pairs):
    # 只有菜名、没有做法和原料的菜单不收。
    return
    for name, body in pairs:
        name = clean(name)
        body = re.sub(r"\s+", "", body)
        if not (2 <= len(name) <= 12) or len(body) < 8:
            continue
        if name in MENU_GENERIC or name in SKIP_NAME:
            continue
        key = ("menu", name, book)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "菜名": name,
            "原料": "",
            "做法": "",
            "出处": "《%s》" % book,
            "时代": era,
            "原文": body[:180],
        })


def best_blocks(text):
    titled = titled_blocks(text)
    colon = colon_blocks(text)
    return titled if len(titled) >= len(colon) else colon


def ensure_extra():
    import subprocess
    import urllib.parse
    extra = [
        "艺藏/饮馔/随息居饮食谱.txt",
        "艺藏/饮馔/北山酒经.txt",
        "艺藏/饮馔/酒经.txt",
    ]
    for path in extra:
        dest = os.path.join(DAI, path.replace("/", os.sep))
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        url = "https://raw.githubusercontent.com/garychowcmu/daizhigev20/master/" + urllib.parse.quote(path)
        subprocess.run(
            ["curl.exe", "-sS", "--http1.1", "--ssl-no-revoke", "-f", "-L",
             "-x", "http://127.0.0.1:7897", "--connect-timeout", "20", "--max-time", "90",
             "-o", dest, url],
            check=False,
        )


def main():
    os.makedirs(OUT, exist_ok=True)
    ensure_extra()
    rows = []
    seen = set()
    jobs = [
        ("随园食单", "清", os.path.join(DAI, "艺藏", "饮馔", "随园食单.txt"), titled_blocks),
        ("山家清供", "宋", os.path.join(DAI, "艺藏", "饮馔", "山家清供.txt"), titled_blocks),
        ("养小录", "清", os.path.join(DAI, "艺藏", "饮馔", "养小录.txt"), titled_blocks),
        ("云林堂饮食制度集", "元", os.path.join(DAI, "艺藏", "饮馔", "云林堂饮食制度集.txt"), best_blocks),
        ("糖霜谱", "宋", os.path.join(DAI, "艺藏", "饮馔", "糖霜谱.txt"), best_blocks),
        ("续易牙遗意", "明", os.path.join(DAI, "艺藏", "饮馔", "续易牙遗意.txt"), best_blocks),
        ("随息居饮食谱", "清", os.path.join(DAI, "艺藏", "饮馔", "随息居饮食谱.txt"), best_blocks),
        ("北山酒经", "宋", os.path.join(DAI, "艺藏", "饮馔", "北山酒经.txt"), best_blocks),
        ("酒经", "宋", os.path.join(DAI, "艺藏", "饮馔", "酒经.txt"), best_blocks),
        ("醒园录", "清", os.path.join(DAI, "艺藏", "饮馔", "醒园录.txt"), marked_blocks),
        ("吴氏中馈录", "宋", os.path.join(DAI, "艺藏", "饮馔", "浦江吴氏中馈录.txt"), marked_blocks),
        ("本心斋疏食谱", "宋", os.path.join(DAI, "艺藏", "饮馔", "本心斋疏食谱.txt"), marked_blocks),
        ("饮膳正要", "元", os.path.join(DAI, "医藏", "饮膳正要.txt"), yinzhan_blocks),
        ("易牙遗意", "明", os.path.join(DAI, "医藏", "易牙遗意.txt"), best_blocks),
        ("食疗方", "唐", os.path.join(DAI, "医藏", "食疗方.txt"), best_blocks),
    ]
    counts = []
    for book, era, path, parser in jobs:
        before = len(rows)
        if os.path.exists(path):
            add(rows, seen, book, era, parser(read(path)))
        counts.append((book, len(rows) - before))

    home = read(os.path.join(DAI, "儒藏", "修身治家", "居家必用事类全集.txt"))
    start = home.find("造菜鲞法", home.find("造菜鲞法") + 1)
    before = len(rows)
    add(rows, seen, "居家必用事类全集", "元", titled_blocks(home, start if start > 0 else 0))
    counts.append(("居家必用事类全集", len(rows) - before))

    qimin = read(os.path.join(DAI, "子藏", "农家", "齐民要术.txt"))
    marker = qimin.find("酱法")
    before = len(rows)
    food_mark = "饼粥羹酒酱醋脯腊糖蜜豉酢肉鱼脍炙饵粽糕酪酥菹"
    early = [
        pair for pair in method_colon_blocks(qimin[:marker if marker > 0 else 0])
        if any(ch in pair[0] for ch in food_mark)
    ]
    add(rows, seen, "齐民要术", "北魏", early)
    add(rows, seen, "齐民要术", "北魏", method_colon_blocks(qimin[marker if marker > 0 else 0:]))
    counts.append(("齐民要术", len(rows) - before))

    td_dir = os.path.join(TEXT, "调鼎集")
    before = len(rows)
    for name in sorted(os.listdir(td_dir)):
        if name.endswith(".txt"):
            add(rows, seen, "调鼎集", "清", tiaoding_blocks(read(os.path.join(td_dir, name))))
    counts.append(("调鼎集", len(rows) - before))

    before = len(rows)
    add(rows, seen, "筵款丰馐依样调鼎新录", "清", load_yankuan())
    counts.append(("筵款丰馐依样调鼎新录", len(rows) - before))

    shidian = os.path.join(TEXT, "识典")
    html = os.path.join(TEXT, "_html")
    yangsheng = [os.path.join(shidian, "yangsheng-%02d.txt" % n) for n in range(1, 7)]
    shixian = [
        os.path.join(TEXT, "食宪鸿秘", "01.txt"),
        os.path.join(shidian, "shixian-02.txt"),
        os.path.join(shidian, "shixian-04.txt"),
    ]
    zunsheng = [
        "1llqnvsxpbfgv", "1llqnvtbppvcw", "1llqnvup69ybk", "1llqnvvzmkso8",
        "1llqnvw6wqdr6", "1llqnvwv9p99k", "1llqnvxb5jns2", "1llqnvy1i6jvn",
        "1llqnvyi80sgy", "1llqnvze7cwtk",
    ]
    before = len(rows)
    for path in yangsheng:
        if os.path.exists(path):
            add(rows, seen, "宋氏养生部", "明", shidian_blocks(path))
    counts.append(("宋氏养生部", len(rows) - before))
    before = len(rows)
    for path in shixian:
        if os.path.exists(path):
            add(rows, seen, "食宪鸿秘", "清", shidian_blocks(path))
    counts.append(("食宪鸿秘", len(rows) - before))
    before = len(rows)
    for cid in zunsheng:
        path = os.path.join(html, "sk-%s.html" % cid)
        if os.path.exists(path):
            add(rows, seen, "宋氏尊生部", "明", shidian_blocks(path))
    counts.append(("宋氏尊生部", len(rows) - before))
    before = len(rows)
    qingbai = os.path.join(DAI, "子藏", "类书", "清稗类钞.txt")
    if os.path.exists(qingbai):
        add(rows, seen, "清稗类钞", "清", qingbai_blocks(qingbai))
    counts.append(("清稗类钞", len(rows) - before))

    zhunsheng = os.path.join(DAI, "医藏", "遵生八笺.txt")
    before = len(rows)
    if os.path.exists(zhunsheng):
        add(rows, seen, "遵生八笺", "明", zhunsheng_blocks(zhunsheng))
    counts.append(("遵生八笺", len(rows) - before))

    shilin = os.path.join(DAI, "子藏", "类书", "事林广记别集.txt")
    before = len(rows)
    if os.path.exists(shilin):
        add(rows, seen, "事林广记", "宋", shilin_blocks(shilin))
    counts.append(("事林广记", len(rows) - before))

    menu_books = [
        ("梦粱录", "宋", r"史藏\地理\梦粱录.txt", ["分茶酒店", "面食店", "荤素从食店", "肉铺"]),
        ("东京梦华录", "宋", r"史藏\地理\东京梦华录.txt", ["州桥夜市", "饮食果子", "食店"]),
    ]
    for book, era, rel, titles in menu_books:
        before = len(rows)
        lines = book_lines(rel)
        if book == "武林旧事" and not lines:
            lines = book_lines(r"史藏\地理\武林旧事.txt")
        if lines:
            sample = "".join(lines)
            if book == "武林旧事" and sample.count("、") < 30:
                counts.append((book, 0))
                continue
            add_menu(rows, seen, book, era, chapter_menu(lines, titles))
        counts.append((book, len(rows) - before))

    before = len(rows)
    known = [row["菜名"] for row in rows if row["出处"] == "《梦粱录》"]
    add_menu(rows, seen, "武林旧事", "宋", wulin_menu(known))
    counts.append(("武林旧事", len(rows) - before))

    before = len(rows)
    add_menu(rows, seen, "西湖老人繁胜录", "宋", fansheng_menu())
    counts.append(("西湖老人繁胜录", len(rows) - before))

    before = len(rows)
    add_menu(rows, seen, "扬州画舫录", "清", yangzhou_menu())
    counts.append(("扬州画舫录", len(rows) - before))

    named_books = [
        ("清异录", "宋", os.path.join(DAI, "子藏", "笔记", "清异录.txt"), qingyi_best),
        ("寿亲养老新书", "宋", os.path.join(DAI, "医藏", "寿亲养老新书.txt"), shouqin_best),
        ("夜航船", "明", os.path.join(DAI, "子藏", "类书", "夜航船.txt"), yehang_best),
        ("礼记", "周", os.path.join(DAI, "儒藏", "礼经", "礼记.txt"), neize_best),
        ("楚辞", "战国", os.path.join(DAI, "诗藏", "楚辞", "楚辞.txt"), chuci_best),
        ("吕氏春秋", "战国", os.path.join(DAI, "子藏", "诸子", "吕氏春秋.txt"), benwei_best),
        ("酉阳杂俎", "唐", os.path.join(DAI, "子藏", "笔记", "酉阳杂俎.txt"), youyang_best),
        ("北户录", "唐", os.path.join(DAI, "史藏", "地理", "北户录.txt"), beihu_best),
        ("广东新语", "清", os.path.join(DAI, "子藏", "笔记", "广东新语.txt"), guangdong_best),
        ("荆楚岁时记", "南朝", os.path.join(DAI, "史藏", "地理", "荆楚岁时记.txt"), jingchu_best),
        ("明宫史", "明", os.path.join(DAI, "史藏", "政书", "明宫史.txt"), minggong_best),
    ]
    for book, era, path, parser in named_books:
        before = len(rows)
        if os.path.exists(path) and os.path.getsize(path) > 500:
            emit_named(rows, seen, book, era, parser(path))
        counts.append((book, len(rows) - before))

    before = len(rows)
    yanshi = os.path.join(DAI, "史藏", "志存记录", "燕京岁时记.txt")
    if os.path.exists(yanshi):
        add_menu(rows, seen, "燕京岁时记", "清", yanshi_menu(yanshi))
    counts.append(("燕京岁时记", len(rows) - before))

    before = len(rows)
    dijing = os.path.join(DAI, "史藏", "地理", "帝京岁时纪胜.txt")
    if os.path.exists(dijing):
        add_menu(rows, seen, "帝京岁时纪胜", "清", dijing_menu(dijing))
    counts.append(("帝京岁时纪胜", len(rows) - before))

    novels = [
        ("红楼梦", "清", r"集藏\小说\红楼梦.txt"),
        ("金瓶梅词话", "明", r"集藏\小说\金瓶梅词话万历本.txt"),
        ("歧路灯", "清", r"集藏\小说\歧路灯.txt"),
        ("醒世姻缘传", "清", r"集藏\小说\醒世姻缘传.txt"),
        ("镜花缘", "清", r"集藏\小说\镜花缘.txt"),
        ("儒林外史", "清", r"集藏\小说\儒林外史.txt"),
        ("水浒传", "明", r"集藏\小说\水浒传.txt"),
        ("喻世明言", "明", r"集藏\话本\喻世明言.txt"),
        ("警世通言", "明", r"集藏\话本\警世通言.txt"),
        ("醒世恒言", "明", r"集藏\话本\醒世恒言.txt"),
        ("今古奇观", "明", r"集藏\小说\今古奇观.txt"),
        ("聊斋志异", "清", r"集藏\小说\聊斋志异.txt"),
        ("儿女英雄传", "清", r"集藏\话本\儿女英雄传.txt"),
        ("西游记", "明", r"集藏\小说\西游记.txt"),
        ("三国演义", "明", r"集藏\演义\三国演义.txt"),
        ("封神演义", "明", r"集藏\演义\封神演义.txt"),
        ("东周列国志", "清", r"集藏\演义\东周列国志.txt"),
    ]
    for book, era, rel in novels:
        before = len(rows)
        path = os.path.join(DAI, rel)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            add_menu(rows, seen, book, era, novel_menu(path))
        counts.append((book, len(rows) - before))

    path = os.path.join(OUT, "古菜谱.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["菜名", "原料", "做法", "出处", "时代", "原文"])
        writer.writeheader()
        writer.writerows(rows)
    sample = os.path.join(OUT, "抽查.txt")
    with open(sample, "w", encoding="utf-8") as handle:
        handle.write("TOTAL %d\n" % len(rows))
        for book, count in counts:
            handle.write("%s\t%d\n" % (book, count))
        handle.write("\n")
        shown = {}
        for row in rows:
            book = row["出处"]
            shown[book] = shown.get(book, 0) + 1
            if shown[book] <= 6:
                handle.write("%s | %s | %s | %s\n" % (book, row["菜名"], row["原料"], row["原文"][:70]))
    print("TOTAL", len(rows))
    for book, count in counts:
        print(book, count)


if __name__ == "__main__":
    main()

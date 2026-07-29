#!/usr/bin/env python3
"""Build the reviewed dream-symbol index from a pinned upstream snapshot."""

import argparse
import io
import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen
import zipfile


UPSTREAM_REPO = "tf1993614/Know-your-fate"
UPSTREAM_COMMIT = "1aa675597ee1405c9dea142bda0a3a9ed460ac99"
UPSTREAM_ROOT = ".claude/skills/zhougong-dream-interpretation/references/zhougong"
EXPECTED_CATEGORY_COUNT = 27
EXPECTED_QUOTE_COUNT = 988
SOURCE_ID = "zhougong-public-domain-v1"
INDEX_VERSION = "1.0.0"
GENERATED_ON = "2026-07-29"

CATEGORY_FILES = (
    "01-tiandi-riyue-xingchen.md",
    "02-dili-shanshi-shumu.md",
    "03-shenti-mianmu-chifa.md",
    "04-guandai-yifu-xiewa.md",
    "05-daojian-jingjie-zhonggu.md",
    "06-diwang-wenwu-huzhao.md",
    "07-gongshi-wuyu-cangku.md",
    "08-menhu-jingzao-chuce.md",
    "09-jinyin-zhuyu-juanbo.md",
    "10-jinghuan-chaichuan-shubi.md",
    "11-yizhang-tanru-chizhu.md",
    "12-chuanche-youxing-wujian.md",
    "13-daolu-qiaoliang-shiji.md",
    "14-fuqi-chanyun-jiaohuan.md",
    "15-yinshi-jiurou-guacai.md",
    "16-zhongmu-guanguo-yingsong.md",
    "17-wenshu-biyan-bingqi.md",
    "18-aile-bingsi-gechang.md",
    "19-fodao-sengni-guishen.md",
    "20-beihai-doushang-dama.md",
    "21-bujin-xingfa-yuju.md",
    "22-tianyuan-wugu-gengzhong.md",
    "23-shuihuo-daozei-dengzhu.md",
    "24-gouwu-muyu-lingru.md",
    "25-longshe-qinshou-denglei.md",
    "26-niuma-zhuyang-liuchu.md",
    "27-guibie-yuxia-kunchong.md",
)


def curated(
    symbol_id: str,
    label: str,
    aliases: tuple[str, ...],
    category: str,
    source_file: str,
    quote: str,
) -> dict:
    return {
        "id": symbol_id,
        "label": label,
        "aliases": list(aliases),
        "category": category,
        "source_file": source_file,
        "quote": quote,
        "source_id": SOURCE_ID,
    }


CURATED_SYMBOLS = (
    curated("sun", "太阳", ("太阳", "太陽", "日头", "日頭", "太阳公公", "太陽公公"), "天地日月星辰", "01-tiandi-riyue-xingchen.md", "日光入屋官位至"),
    curated("moon", "月亮", ("月亮", "月球", "明月"), "天地日月星辰", "01-tiandi-riyue-xingchen.md", "拜星月燒香大吉"),
    curated("rain", "下雨", ("下雨", "大雨", "雨水", "暴雨", "淋雨"), "天地日月星辰", "01-tiandi-riyue-xingchen.md", "行路逢雨有酒食"),
    curated("mountain", "山", ("山", "高山", "山峰", "大山"), "地理山石樹木", "02-dili-shanshi-shumu.md", "遊看高山春夏吉"),
    curated("tree", "树", ("树", "樹", "树木", "樹木", "大树", "大樹"), "地理山石樹木", "02-dili-shanshi-shumu.md", "種植樹木大吉昌"),
    curated("teeth", "牙齿", ("牙齿", "牙齒", "牙", "掉牙", "牙掉了"), "身體面目齒髮", "03-shenti-mianmu-chifa.md", "齒自落者父母凶"),
    curated("hair", "头发", ("头发", "頭髮", "长发", "長髮", "白发", "白髮"), "身體面目齒髮", "03-shenti-mianmu-chifa.md", "頭禿髮落皆凶事"),
    curated("clothes", "衣服", ("衣服", "衣裳", "衣物", "外衣"), "冠帶衣服鞋襪", "04-guandai-yifu-xiewa.md", "洗染衣服皆大吉"),
    curated("knife", "刀", ("刀", "刀子", "菜刀", "刀剑", "刀劍"), "刀劍旌節鐘鼓", "05-daojian-jingjie-zhonggu.md", "拔刀出行主大吉"),
    curated("house", "房屋", ("房屋", "房子", "屋子", "房间", "房間", "老宅", "旧屋", "舊屋"), "宮室屋宇倉庫", "07-gongshi-wuyu-cangku.md", "屋宅更新主大吉"),
    curated("door", "门", ("门", "門", "门口", "門口", "大门", "大門"), "門戶井灶廚廁", "08-menhu-jingzao-chuce.md", "門戶忽開主大吉"),
    curated("mirror", "镜子", ("镜子", "鏡子", "镜", "鏡", "明镜", "明鏡"), "鏡環釵釧梳篦", "10-jinghuan-chaichuan-shubi.md", "明鏡者吉暗者凶"),
    curated("boat", "船", ("船", "船只", "船隻", "小船", "舟"), "船車遊行物件", "12-chuanche-youxing-wujian.md", "乘船風帆大吉利"),
    curated("car", "汽车", ("汽车", "汽車", "车", "車", "轿车", "轎車"), "船車遊行物件", "12-chuanche-youxing-wujian.md", "車行主百事順和"),
    curated("road", "道路", ("道路", "路", "路上", "大路", "岔路"), "道路橋梁市集", "13-daolu-qiaoliang-shiji.md", "見四路通名利遂"),
    curated("bridge", "桥", ("桥", "橋", "桥梁", "橋梁", "过桥", "過橋"), "道路橋梁市集", "13-daolu-qiaoliang-shiji.md", "修橋樑者萬事和"),
    curated("coffin", "棺材", ("棺材", "棺木", "棺", "棺椁", "棺槨"), "塚墓棺槨迎送", "16-zhongmu-guanguo-yingsong.md", "新塚棺槨主憂除"),
    curated("death", "死亡", ("死亡", "去世", "死人", "死去", "过世", "過世"), "哀樂病死歌唱", "18-aile-bingsi-gechang.md", "見人死自死者吉"),
    curated("ghost", "鬼", ("鬼", "鬼魂", "幽灵", "幽靈", "鬼怪"), "佛道僧尼鬼神", "19-fodao-sengni-guishen.md", "與鬼鬥者主延壽"),
    curated("fight", "打斗", ("打斗", "打鬥", "打架", "争斗", "爭鬥", "搏斗", "搏鬥"), "被害鬥傷打罵", "20-beihai-doushang-dama.md", "家中人鬥主分散"),
    curated("prison", "监狱", ("监狱", "監獄", "牢狱", "牢獄", "牢房", "坐牢"), "捕禁刑罰獄具", "21-bujin-xingfa-yuju.md", "坐獄中必有恩赦"),
    curated("water", "水", ("水", "河水", "海水", "积水", "積水", "洪水", "清水"), "水火盜賊燈燭", "23-shuihuo-daozei-dengzhu.md", "大水澄清大吉利"),
    curated("fire", "火", ("火", "火焰", "起火", "大火", "火灾", "火災", "着火", "著火"), "水火盜賊燈燭", "23-shuihuo-daozei-dengzhu.md", "火燒自屋主興旺"),
    curated("bath", "洗澡", ("洗澡", "沐浴", "冲澡", "沖澡", "泡澡"), "垢污沐浴凌辱", "24-gouwu-muyu-lingru.md", "沐浴塵土疾病安"),
    curated("dragon", "龙", ("龙", "龍", "巨龙", "巨龍", "神龙", "神龍"), "龍蛇禽獸等類", "25-longshe-qinshou-denglei.md", "龍飛有官位大貴"),
    curated("snake", "蛇", ("蛇", "蛇类", "蛇類", "毒蛇", "大蛇"), "龍蛇禽獸等類", "25-longshe-qinshou-denglei.md", "蛇行水內主榮遷"),
    curated("tiger", "老虎", ("老虎", "虎", "猛虎", "白虎"), "龍蛇禽獸等類", "25-longshe-qinshou-denglei.md", "猛虎大吼主得官"),
    curated("dog", "狗", ("狗", "犬", "小狗", "恶狗", "惡狗"), "牛馬豬羊六畜", "26-niuma-zhuyang-liuchu.md", "犬吠主人失財凶"),
    curated("cat", "猫", ("猫", "貓", "小猫", "小貓", "白猫", "白貓"), "龍蛇禽獸等類", "25-longshe-qinshou-denglei.md", "貓捕鼠者大得財"),
    curated("horse", "马", ("马", "馬", "马匹", "馬匹", "白马", "白馬"), "牛馬豬羊六畜", "26-niuma-zhuyang-liuchu.md", "馬行千里大喜至"),
    curated("cow", "牛", ("牛", "黄牛", "黃牛", "水牛", "小牛"), "牛馬豬羊六畜", "26-niuma-zhuyang-liuchu.md", "牛出門好事立至"),
    curated("pig", "猪", ("猪", "豬", "小猪", "小豬", "野猪", "野豬"), "牛馬豬羊六畜", "26-niuma-zhuyang-liuchu.md", "殺豬吉豬自死凶"),
    curated("fish", "鱼", ("鱼", "魚", "鱼群", "魚群", "鲤鱼", "鯉魚"), "龜鱉魚蝦昆蟲", "27-guibie-yuxia-kunchong.md", "群魚游水主有財"),
    curated("turtle", "乌龟", ("乌龟", "烏龜", "龟", "龜", "海龟", "海龜"), "龜鱉魚蝦昆蟲", "27-guibie-yuxia-kunchong.md", "見龜者主女人貴"),
    curated("insect", "昆虫", ("昆虫", "昆蟲", "虫子", "蟲子", "飞虫", "飛蟲"), "龜鱉魚蝦昆蟲", "27-guibie-yuxia-kunchong.md", "身坐魚蟲病患除"),
    curated("flying", "飞行", ("飞行", "飛行", "飞起来", "飛起來", "飞上天", "飛上天"), "天地日月星辰", "01-tiandi-riyue-xingchen.md", "飛上天富貴大吉"),
    curated("falling", "坠落", ("坠落", "墜落", "掉下", "掉下来", "掉下來", "跌落", "下坠", "下墜"), "門戶井灶廚廁", "08-menhu-jingzao-chuce.md", "身墜井中疾病凶"),
)


def download_sources(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    archive_url = (
        f"https://codeload.github.com/{UPSTREAM_REPO}/zip/{UPSTREAM_COMMIT}"
    )
    request = Request(archive_url, headers={"User-Agent": "miniworkbuddy-dream-index-builder/1"})
    with urlopen(request, timeout=60) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    archive_root = f"Know-your-fate-{UPSTREAM_COMMIT}/{UPSTREAM_ROOT}"
    for filename in CATEGORY_FILES:
        member = f"{archive_root}/{filename}"
        try:
            content = archive.read(member)
        except KeyError as exc:
            raise RuntimeError(f"missing pinned source file in archive: {filename}") from exc
        (destination / filename).write_bytes(content)
    return destination


def load_and_validate_sources(source_dir: Path) -> dict[str, str]:
    if len(CATEGORY_FILES) != EXPECTED_CATEGORY_COUNT:
        raise RuntimeError("category manifest count changed")
    documents: dict[str, str] = {}
    quote_count = 0
    for filename in CATEGORY_FILES:
        path = source_dir / filename
        if not path.is_file():
            raise RuntimeError(f"missing pinned source file: {filename}")
        content = path.read_text(encoding="utf-8")
        documents[filename] = content
        quote_count += sum(line.startswith("- ") for line in content.splitlines())
    if quote_count != EXPECTED_QUOTE_COUNT:
        raise RuntimeError(f"expected {EXPECTED_QUOTE_COUNT} quotes, found {quote_count}")
    for item in CURATED_SYMBOLS:
        source_line = f'- {item["quote"]}'
        if source_line not in documents[item["source_file"]].splitlines():
            raise RuntimeError(f'quote for {item["id"]} is absent from {item["source_file"]}')
    return documents


def build_payload() -> dict:
    symbols = []
    for item in CURATED_SYMBOLS:
        symbols.append({key: value for key, value in item.items() if key != "source_file"})
    return {
        "schema_version": 1,
        "version": INDEX_VERSION,
        "source": {"id": SOURCE_ID, "upstream_commit": UPSTREAM_COMMIT},
        "symbols": symbols,
    }


def attribution() -> str:
    return f"""# Traditional dream-reference attribution

## Source

- Original text: 《周公解梦》, transcribed from the public-domain text on [Chinese Wikisource](https://zh.wikisource.org/wiki/周公解夢).
- Transformation reference: [tf1993614/Know-your-fate](https://github.com/{UPSTREAM_REPO}).
- Pinned upstream commit: `{UPSTREAM_COMMIT}`.
- Upstream path: `{UPSTREAM_ROOT}`.
- Generated: {GENERATED_ON}.

The build script reads exactly 27 pinned category files and verifies all 988 transcribed lines before selecting the reviewed entries in `dream-symbols.json`. Quotes remain in their upstream traditional-Chinese form. Aliases are locally reviewed search terms; no commercial dream-interpretation content is used.

## License notice

The ancient source text is treated as public domain. The upstream repository's own code and transformation materials are distributed under the MIT License:

> Copyright (c) 2026 Feng Tang and 命数天问 (Mingshu Tianwen) contributors
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

See the complete upstream license at <https://github.com/{UPSTREAM_REPO}/blob/{UPSTREAM_COMMIT}/LICENSE>.

## Use boundary

These traditional statements are provided only as cultural reference. They are not predictions, facts about a person's future, medical or psychological diagnoses, or treatment advice.
"""


def write_outputs(output: Path, attribution_output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    attribution_output.write_text(attribution(), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    default_output = (
        Path(__file__).resolve().parents[1]
        / "app/bootstrap/assets/dream-interpreter/references/dream-symbols.json"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Use an existing directory containing the 27 pinned Markdown files.",
    )
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--attribution-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    attribution_output = args.attribution_output or args.output.with_name("ATTRIBUTION.md")
    if args.source_dir:
        source_dir = args.source_dir
        load_and_validate_sources(source_dir)
        write_outputs(args.output, attribution_output)
        return
    with tempfile.TemporaryDirectory(prefix="dream-references-") as temporary:
        source_dir = download_sources(Path(temporary))
        load_and_validate_sources(source_dir)
        write_outputs(args.output, attribution_output)


if __name__ == "__main__":
    main()

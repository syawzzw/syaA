# rename_core.py  —— 核心逻辑模块（GUI / CLI 共用）
import os, re, io, struct, zipfile, datetime, json, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from functools import lru_cache

# .livp = iPhone 实况照片（ZIP：静态图 + .mov）
IMG_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff', '.bmp', '.heic', '.livp'}
VID_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.3gp'}

# ──────────────────────────────────────────────
# 高德地图逆地理编码
# ──────────────────────────────────────────────
def _load_amap_key():
    """读取高德 Web服务 key：环境变量 SYAA_AMAP_KEY → gui_config.json 的 amap_key。

    key 不能硬编码进仓库（仓库是公开的），未配置时逆地理编码自动跳过，
    文件名退化为「时间_原文件名」，不影响重命名本身。
    """
    key = os.environ.get("SYAA_AMAP_KEY", "").strip()
    if key:
        return key
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "gui_config.json")
    try:
        with io.open(cfg, encoding="utf-8") as f:
            key = (json.load(f).get("amap_key") or "").strip()
    except Exception:
        key = ""
    return key


AMAP_KEY = _load_amap_key()

# 常用繁→简映射
_T2S = {
    '臺': '台', '餘': '余', '裡': '里', '術': '术', '衛': '卫',
    '聖': '圣', '賢': '贤', '賣': '卖', '澤': '泽', '態': '态',
    '贊': '赞', '載': '载', '鄉': '乡', '鄭': '郑', '幣': '币',
    '擔': '担', '憂': '忧', '湯': '汤', '劉': '刘', '暢': '畅',
    '蘇': '苏', '處': '处', '溝': '沟', '謹': '谨', '買': '买',
    '贜': '赃', '藍': '蓝', '釀': '酿', '遞': '递', '擴': '扩',
    '執': '执', '報': '报', '釋': '释', '專': '专', '偽': '伪',
    '號': '号', '嘆': '叹', '廢': '废', '場': '场', '當': '当',
    '靈': '灵', '確': '确', '養': '养', '喬': '乔', '維': '维',
    '護': '护', '繼': '继', '薑': '姜', '疊': '叠', '張': '张',
    '彎': '弯', '彈': '弹', '發': '发', '歲': '岁', '總': '总',
    '纖': '纤', '羅': '罗', '罰': '罚', '織': '织', '終': '终',
    '繡': '绣', '結': '结', '繞': '绕', '線': '线', '繪': '绘',
    '耀': '耀', '繋': '系', '繫': '系', '繭': '茧', '續': '续',
    '纍': '累', '紀': '纪', '紅': '红', '紋': '纹', '納': '纳',
    '紐': '纽', '純': '纯', '紗': '纱', '絆': '绊', '區': '区',
    '慶': '庆', '網': '网', '義': '义', '証': '证', '環': '环',
    '複': '复', '該': '该', '書': '书', '車': '车', '電': '电',
    '國': '国', '協': '协', '壓': '压', '廠': '厂', '廣': '广',
    '據': '据', '數': '数', '機': '机', '營': '营', '鐵': '铁',
    '統': '统', '關': '关', '隊': '队', '會': '会', '開': '开',
    '觀': '观', '認': '认', '質': '质', '員': '员', '學': '学',
    '們': '们', '與': '与', '這': '这', '個': '个', '為': '为',
    '來': '来', '過': '过', '習': '习', '參': '参', '樣': '样',
    '備': '备', '應': '应', '許': '许', '無': '无', '從': '从',
    '產': '产', '種': '种', '經': '经', '體': '体', '東': '东',
    '見': '见', '內': '内', '間': '间', '題': '题', '達': '达',
    '還': '还', '進': '进', '遠': '远', '連': '连', '運': '运',
    '選': '选', '錫': '锡', '鍵': '键', '點': '点', '齊': '齐',
}


def _to_simple(s):
    for fc, sc in _T2S.items():
        s = s.replace(fc, sc)
    return s


_GEO_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.geo_cache.json')
_geo_cache = None


def _load_geo_cache():
    global _geo_cache
    if _geo_cache is None:
        try:
            with open(_GEO_CACHE_PATH, 'r', encoding='utf-8') as f:
                _geo_cache = json.load(f)
        except Exception:
            _geo_cache = {}
    return _geo_cache


def _save_geo_cache():
    try:
        with open(_GEO_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(_geo_cache, f, ensure_ascii=False)
    except Exception:
        pass


def geocode_to_chinese(lat, lon):
    """经纬度 → 中文省市区，优先高德 API。返回 None 表示无结果。"""
    if lat is None or lon is None:
        return None
    if not AMAP_KEY:
        return None
    cache = _load_geo_cache()
    ckey = "{:.3f},{:.3f}".format(lat, lon)  # 约100米精度，同一地点只查一次
    if ckey in cache:
        return cache[ckey] or None
    try:
        url = (
            f"https://restapi.amap.com/v3/geocode/regeo"
            f"?key={AMAP_KEY}"
            f"&location={lon},{lat}"
            f"&extensions=base&output=json"
        )
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get('status') == '1' and 'regeocode' in data:
            ac = data['regeocode']['addressComponent']
            province = (ac.get('province', '') or '').strip()
            city_raw = ac.get('city', '') or ''
            city = (city_raw[0].strip() if isinstance(city_raw, list) else city_raw.strip()) or province
            district = (ac.get('district', '') or '').strip()
            parts = []
            for p in [province, city, district]:
                if p and p not in parts:
                    parts.append(p)
            result = ''.join(parts[:3])
            result = result if result else None
            cache[ckey] = result or ''
            _save_geo_cache()
            return result
        return None  # 接口异常/无结果不写缓存，下次重试
    except Exception:
        return None


# ──────────────────────────────────────────────
# TIFF/EXIF 解析器
# ──────────────────────────────────────────────

def parse_tiff_ifd(data, ifd_offset, endian):
    if ifd_offset + 2 > len(data):
        return {}
    num_entries = struct.unpack(endian + 'H', data[ifd_offset:ifd_offset+2])[0]
    entries = {}
    pos = ifd_offset + 2
    for _ in range(num_entries):
        if pos + 12 > len(data):
            break
        tag  = struct.unpack(endian + 'H', data[pos:pos+2])[0]
        typ  = struct.unpack(endian + 'H', data[pos+2:pos+4])[0]
        cnt  = struct.unpack(endian + 'I', data[pos+4:pos+8])[0]
        val4 = struct.unpack(endian + 'I', data[pos+8:pos+12])[0]
        ts = {1:1, 2:1, 3:2, 4:4, 5:8, 7:1, 9:4, 10:8}.get(typ, 1)
        total = ts * cnt
        if total <= 4:
            if typ == 3:
                entries[tag] = (typ, cnt, struct.unpack(endian+'H', struct.pack(endian+'I', val4)[0:2])[0])
            elif typ == 2:
                entries[tag] = (typ, cnt, val4 & 0xFF)
            else:
                entries[tag] = (typ, cnt, val4)
        else:
            entries[tag] = (typ, cnt, val4)
        pos += 12
    return entries


def read_rational(data, offset, endian):
    if offset + 8 > len(data):
        return 0.0
    n = struct.unpack(endian + 'I', data[offset:offset+4])[0]
    d = struct.unpack(endian + 'I', data[offset+4:offset+8])[0]
    return n / d if d != 0 else 0.0


def read_ascii(data, offset, count, endian):
    if offset + count > len(data):
        return ''
    return data[offset:offset+count].rstrip(b'\x00').decode('ascii', 'ignore')


def get_gps_from_tiff(tiff, ifd0_entries, endian):
    gps_off = None
    for tag, (typ, cnt, val) in ifd0_entries.items():
        if tag == 34853:
            gps_off = val
            break
    if not gps_off:
        return None, None, None
    gps = parse_tiff_ifd(tiff, gps_off, endian)
    if not gps:
        return None, None, None

    lat_d = lat_m = lat_s = None
    lat_ref = 'N'
    if 2 in gps:
        typ, cnt, off = gps[2]
        if typ == 5 and cnt >= 3:
            lat_d = read_rational(tiff, off, endian)
            lat_m = read_rational(tiff, off + 8, endian)
            lat_s = read_rational(tiff, off + 16, endian)
    if 1 in gps:
        typ, cnt, val = gps[1]
        if typ == 2 and 32 <= val < 127:
            lat_ref = chr(val)

    lon_d = lon_m = lon_s = None
    lon_ref = 'E'
    if 4 in gps:
        typ, cnt, off = gps[4]
        if typ == 5 and cnt >= 3:
            lon_d = read_rational(tiff, off, endian)
            lon_m = read_rational(tiff, off + 8, endian)
            lon_s = read_rational(tiff, off + 16, endian)
    if 3 in gps:
        typ, cnt, val = gps[3]
        if typ == 2 and 32 <= val < 127:
            lon_ref = chr(val)

    if None not in (lat_d, lon_d):
        lat = lat_d + lat_m/60 + lat_s/3600
        lon = lon_d + lon_m/60 + lon_s/3600
        if lat_ref == 'S': lat = -lat
        if lon_ref == 'W': lon = -lon
        return lat, lon, None
    return None, None, None


def get_datetime_from_tiff(tiff, ifd0_entries, endian):
    exif_off = None
    for tag, (typ, cnt, val) in ifd0_entries.items():
        if tag == 34665:
            exif_off = val
            break
    exif = parse_tiff_ifd(tiff, exif_off, endian) if exif_off else {}
    all_tags = {**ifd0_entries, **exif}
    for tag in (36867, 36868, 306):
        if tag not in all_tags:
            continue
        typ, cnt, val_or_off = all_tags[tag]
        if typ == 2:
            s = read_ascii(tiff, val_or_off, cnt, endian)
            try:
                dt = datetime.datetime.strptime(s.strip(), '%Y:%m:%d %H:%M:%S')
                src = 'EXIF拍摄时间' if tag == 36867 else 'EXIF修改时间'
                return dt, src
            except Exception:
                pass
    return None, None


def parse_raw_exif(exif_bytes):
    marker = exif_bytes.find(b'Exif\x00\x00')
    tiff = exif_bytes[marker + 6:] if marker >= 0 else exif_bytes[6:]
    if len(tiff) < 8:
        return None, None, None, None, None
    endian = '<' if tiff[0:2] == b'II' else '>'
    if struct.unpack(endian + 'H', tiff[2:4])[0] != 0x002A:
        return None, None, None, None, None
    ifd0_off = struct.unpack(endian + 'I', tiff[4:8])[0]
    ifd0 = parse_tiff_ifd(tiff, ifd0_off, endian)
    dt, source = get_datetime_from_tiff(tiff, ifd0, endian)
    lat, lon, _ = get_gps_from_tiff(tiff, ifd0, endian)
    return dt, source, lat, lon, None


def get_file_mtime(filepath):
    t = os.path.getmtime(filepath)
    return datetime.datetime.fromtimestamp(t), '文件修改时间'


def livp_image_bytes(filepath):
    """.livp（实况照片）本质是 ZIP，内含静态图 + .mov。
    返回 (图片数据 bytes, 内部文件名) 或 (None, None)。
    """
    try:
        with zipfile.ZipFile(filepath) as z:
            for name in z.namelist():
                low = name.lower()
                if low.endswith(('.heic', '.heif', '.jpg', '.jpeg')):
                    return z.read(name), name
    except Exception:
        return None, None
    return None, None


# 文件名日期提取：支持多种常见格式
# 按优先级排列：带时间的格式 > 仅日期格式
_FNAME_DATE_PATTERNS = [
    # yyyyMMdd_HHmmss  /  yyyyMMddTHHmmss  /  yyyy-MM-dd_HH-mm-ss  /  yyyy-MM-dd HH:mm:ss
    # 日期和时间之间允许 _ - T 空格 等分隔符
    (r'(\d{4})[^\d]?(\d{2})[^\d]?(\d{2})[_\-T ](\d{2})[^\d]?(\d{2})[^\d]?(\d{2})',
     lambda m: datetime.datetime(int(m[0]), int(m[1]), int(m[2]),
                                  int(m[3]), int(m[4]), int(m[5]))),
    # yyyyMMdd  /  yyyy-MM-dd  /  yyyy_MM_dd  /  yyyy.MM.dd
    (r'(\d{4})[^\d](\d{2})[^\d](\d{2})',
     lambda m: datetime.datetime(int(m[0]), int(m[1]), int(m[2]))),
    # 紧凑 yyyyMMdd（无分隔符，如 20231015）
    (r'(?<!\d)(20\d{2})(0[1-9]|1[0-2])([0-2]\d|3[01])(?!\d)',
     lambda m: datetime.datetime(int(m[0]), int(m[1]), int(m[2]))),
]

def extract_date_from_filename(fname):
    """
    从文件名（不含路径）中提取日期时间。
    返回 (datetime, '文件名日期') 或 (None, None)。
    """
    stem = Path(fname).stem  # 去掉扩展名
    for pattern, builder in _FNAME_DATE_PATTERNS:
        m = re.search(pattern, stem)
        if m:
            groups = m.groups()
            try:
                dt = builder(groups)
                # 简单合法性校验
                if 1970 <= dt.year <= 2100:
                    return dt, '文件名日期'
            except (ValueError, OverflowError):
                continue
    return None, None


def get_info(filepath):
    """读取文件元数据，返回 (datetime, source_str, lat, lon)"""
    ext = Path(filepath).suffix.lower()
    if ext in ('.heic', '.livp'):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass

    lat, lon = None, None
    dt, source = None, None

    try:
        from PIL import Image
        image_src = filepath
        if ext == '.livp':
            data, _inner = livp_image_bytes(filepath)
            image_src = io.BytesIO(data) if data else None
            if image_src is None:
                raise ValueError('livp 内容无法解析')
        img = Image.open(image_src)
        raw_exif = img.info.get('exif', b'')

        try:
            exif = img.getexif()
            for tag in (36867, 36868, 306):
                v = exif.get(tag)
                if v:
                    try:
                        dt = datetime.datetime.strptime(str(v), '%Y:%m:%d %H:%M:%S')
                        source = 'EXIF拍摄时间' if tag == 36867 else 'EXIF修改时间'
                        break
                    except Exception:
                        pass
        except Exception:
            pass

        # HEIC / LIVP 用 raw EXIF 解析 GPS
        if ext in ('.heic', '.livp') and raw_exif:
            dt_raw, src_raw, lat, lon, _ = parse_raw_exif(raw_exif)
            if lat is not None or lon is not None:
                final_dt = dt_raw if dt_raw else dt
                final_src = src_raw if (src_raw and dt_raw) else source
                # 文件名日期优先覆盖
                fname_dt, fname_src = extract_date_from_filename(Path(filepath).name)
                if fname_dt:
                    final_dt, final_src = fname_dt, fname_src
                return final_dt, (final_src or '文件修改时间'), lat, lon
            if dt_raw and dt is None:
                dt, source = dt_raw, (src_raw if src_raw else source)

        # JPEG/PNG 等用 PIL EXIF GPS
        if lat is None:
            try:
                gps_ifd = exif.get(34853)
                if gps_ifd and isinstance(gps_ifd, dict):
                    lat_tag = gps_ifd.get(2)
                    lon_tag = gps_ifd.get(4)
                    lat_ref = gps_ifd.get(1, ord('N'))
                    lon_ref = gps_ifd.get(3, ord('E'))
                    if lat_tag and lon_tag:
                        def dms_to_decimal(dms):
                            if isinstance(dms, tuple) and len(dms) == 3:
                                return dms[0] + dms[1]/60 + dms[2]/3600
                            return None
                        lat = dms_to_decimal(lat_tag)
                        lon = dms_to_decimal(lon_tag)
                        if lat_ref in (ord('S'), ord('s')):
                            lat = -lat
                        if lon_ref in (ord('W'), ord('w')):
                            lon = -lon
            except Exception:
                pass

        if not dt:
            dt, source = get_file_mtime(filepath)

        # ── 文件名日期：优先级最高，覆盖 EXIF 和 mtime ──
        fname_dt, fname_src = extract_date_from_filename(Path(filepath).name)
        if fname_dt:
            dt, source = fname_dt, fname_src

        return dt, source, lat, lon

    except Exception:
        pass

    dt, source = get_file_mtime(filepath)
    # 文件名日期覆盖（即使 PIL 失败也要处理）
    fname_dt, fname_src = extract_date_from_filename(Path(filepath).name)
    if fname_dt:
        dt, source = fname_dt, fname_src
    return dt, source, lat, lon


def build_rename_plan(folder, only_gps=False, progress_cb=None):
    """
    扫描 folder，生成重命名计划。
    progress_cb(current, total, action, filename) — 可选进度回调。
    返回 (plan_list, skipped_nogps_list)
    """
    candidates = []
    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        if any(fname.startswith(x) for x in ('preview_', 'do_rename', 'check_gps', 'debug_', 'compare', 'rename_')):
            continue
        if fname.startswith('.'):
            continue  # 隐藏文件 / 云盘缓存临时文件（如 .dji_export_xxx.mp4.zcece...、.downloading）
        ext = Path(fname).suffix.lower()
        if ext not in IMG_EXTS and ext not in VID_EXTS:
            continue
        candidates.append((fname, fpath))

    total = len(candidates)
    plan = []
    skipped_nogps = []
    _taken = {}  # subfolder -> 已占用的小写文件名集合（含磁盘已有 + 本次计划）

    def _reserve(subfolder, name):
        """返回该 subfolder 下未被占用的文件名（必要时加 _1/_2 后缀）"""
        if subfolder not in _taken:
            try:
                _taken[subfolder] = {n.lower() for n in os.listdir(subfolder)}
            except OSError:
                _taken[subfolder] = set()
        stem, ext = os.path.splitext(name)
        final = name
        n = 1
        while final.lower() in _taken[subfolder]:
            final = f"{stem}_{n}{ext}"
            n += 1
        _taken[subfolder].add(final.lower())
        return final

    for idx, (fname, fpath) in enumerate(candidates, start=1):
        if progress_cb:
            progress_cb(idx, total, '读取EXIF', fname)

        dt, source, lat, lon = get_info(fpath)

        if only_gps and lat is None:
            skipped_nogps.append(fname)
            if progress_cb:
                progress_cb(idx, total, '跳过(无GPS)', fname)
            continue

        if lat is not None:
            if progress_cb:
                progress_cb(idx, total, '逆地理编码', fname)
            location_str = geocode_to_chinese(lat, lon)
        else:
            location_str = None

        base = dt.strftime('%Y%m%d_%H%M%S')
        name_part = f"{base}_{location_str}" if location_str else base
        # 原始文件名（去扩展名），替换 Windows 非法字符，限制长度
        orig_stem = Path(fname).stem
        orig_stem_safe = re.sub(r'[\\/:*?"<>|]', '_', orig_stem)[:60]
        new_name = f"{name_part}_{orig_stem_safe}{Path(fname).suffix}"
        year_month = dt.strftime('%Y-%m')
        subfolder = os.path.join(folder, year_month)
        new_name = _reserve(subfolder, new_name)
        new_path = os.path.join(subfolder, new_name)

        if progress_cb:
            progress_cb(idx, total, '生成计划', fname)

        plan.append({
            'old_path': fpath,
            'old_name': fname,
            'new_name': new_name,
            'new_path': new_path,
            'year_month': year_month,
            'subfolder': subfolder,
            'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'source': source,
            'location': location_str if location_str else ('无GPS' if lat is None else f'{lat:.4f},{lon:.4f}'),
            'lat': lat,
            'lon': lon,
        })

    return plan, skipped_nogps


def execute_rename(plan, progress_cb=None):
    """
    执行重命名计划。
    progress_cb(current, total, action, filename, ok, detail) — 可选进度回调。
    返回 (success, skipped, failed) 数量元组。
    """
    total = len(plan)
    success = skipped = failed = 0

    for idx, item in enumerate(plan, start=1):
        # 文件名和路径都没变 → 跳过
        if item['old_path'] == item['new_path']:
            skipped += 1
            if progress_cb:
                progress_cb(idx, total, '已是最新', item['old_name'], True, '')
            continue

        if progress_cb:
            progress_cb(idx, total, '重命名中', item['old_name'], None, '')

        try:
            os.makedirs(item['subfolder'], exist_ok=True)
            target_path = item['new_path']
            # 目标已存在（上次跑过/同名文件）时自动加 _1/_2 后缀，绝不覆盖
            if os.path.exists(target_path):
                stem, ext = os.path.splitext(item['new_name'])
                n = 1
                while True:
                    cand = os.path.join(item['subfolder'], f"{stem}_{n}{ext}")
                    if not os.path.exists(cand):
                        target_path = cand
                        break
                    n += 1
            os.rename(item['old_path'], target_path)
            success += 1
            if progress_cb:
                progress_cb(idx, total, '完成', item['old_name'], True,
                            f"{item['year_month']}/{os.path.basename(target_path)}")
        except Exception as e:
            failed += 1
            if progress_cb:
                progress_cb(idx, total, '失败', item['old_name'], False, str(e))

    return success, skipped, failed

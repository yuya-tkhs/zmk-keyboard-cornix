"""Cornix の .vil（RMK/Vial）のキー配置を元に ZMK の cornix.keymap を作る。コンボは COMBOS 表で明示する。"""
import json, os, sys

VIL, OUT = sys.argv[1], sys.argv[2]
d = json.load(open(VIL, encoding="utf-8"))
NLAYERS = 5  # 使っているのは 0〜4。5〜9 は空

LAYER_NAMES = ["Base", "Numpad", "Symbol", "Mouse", "RPad"]
LAYER_DEFS = ["BASE", "NUMPAD", "SYM", "MOUSE", "RPAD"]
# .vil に無い、ZMK 側だけで足す層（中身は全部 &trans）。マウス層の上に重ねて速度だけ変える
EXTRA_LAYER_NAMES = ["MouseSlow", "Bluetooth"]
EXTRA_LAYER_DEFS = ["MSLOW", "BTL"]
ALL_LAYER_NAMES = LAYER_NAMES + EXTRA_LAYER_NAMES
ALL_LAYER_DEFS = LAYER_DEFS + EXTRA_LAYER_DEFS

KC = {
    "TAB": "TAB", "LCTRL": "LCTRL", "LSHIFT": "LSHFT", "ESCAPE": "ESC", "LGUI": "LGUI",
    "LALT": "LALT", "SPACE": "SPACE", "BSPACE": "BSPC", "ENTER": "RET", "MINUS": "MINUS",
    "SLASH": "FSLH", "UP": "UP", "DOWN": "DOWN", "LEFT": "LEFT", "RIGHT": "RIGHT",
    "DOT": "DOT", "COMMA": "COMMA", "RSHIFT": "RSHFT", "RCTRL": "RCTRL", "RALT": "RALT",
    "KP_SLASH": "KP_DIVIDE", "KP_ASTERISK": "KP_MULTIPLY", "KP_MINUS": "KP_MINUS",
    "KP_PLUS": "KP_PLUS", "KP_DOT": "KP_DOT", "KP_ENTER": "KP_ENTER", "NUMLOCK": "KP_NUMLOCK",
    "EQUAL": "EQUAL", "SCOLON": "SEMI", "QUOTE": "SQT", "RO": "INT_RO", "JYEN": "INT_YEN",
    "APPLICATION": "K_APP", "LBRACKET": "LBKT", "RBRACKET": "RBKT", "DELETE": "DEL",
    "END": "END", "HOME": "HOME", "PGUP": "PG_UP", "PGDOWN": "PG_DN",
    "NONUS_HASH": "NON_US_HASH", "HENK": "INT_HENKAN", "MHEN": "INT_MUHENKAN",
    "MUTE": "C_MUTE", "VOLU": "C_VOL_UP", "VOLD": "C_VOL_DN",
}
for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KC[c] = c
for n in range(10):
    KC[str(n)] = f"N{n}"
    KC[f"KP_{n}"] = f"KP_N{n}"
for n in range(1, 25):
    KC[f"F{n}"] = f"F{n}"

MOUSE = {
    "BTN1": "&mkp MB1", "BTN2": "&mkp MB2", "BTN3": "&mkp MB3", "BTN4": "&mkp MB4",
    "MS_L": "&mmv MOVE_LEFT", "MS_R": "&mmv MOVE_RIGHT", "MS_U": "&mmv MOVE_UP", "MS_D": "&mmv MOVE_DOWN",
}
# Cornix の Vial User キー（説明書の並び：BT0-4, Next BT, Prev BT, Clear BT ...）
USER = {
    "USER00": "&bt BT_SEL 0", "USER01": "&bt BT_SEL 1", "USER02": "&bt BT_SEL 2",
    "USER03": "&bt BT_SEL 3", "USER04": "&bt BT_SEL 4", "USER05": "&bt BT_NXT",
    "USER06": "&bt BT_PRV", "USER07": "&bt BT_CLR",
}
UNMAPPED = []

# ---- .vil から意図的に変えたもの
# キーの配置は .vil が元。変えた位置だけここに書く（2026-10-01：KeyLayout_1001.png の改訂を含む）
POS_OVERRIDE = {
    # Base：TG(マウス) と MO(Num pad) を外した → 層の切り替えはコンボで行う
    ("Base", 39): "&none",
    ("Base", 40): "&mo BTL",              # 押している間だけ Bluetooth 層（2026-10-01。元は MO(Num pad) の位置）
    # Num pad：テンキーを1列内側へ寄せ、0 を親指（数・記号キーの位置）へ。左端の列は下の層を透かす
    ("Numpad", 0): "&trans", ("Numpad", 1): "&kp KP_DIVIDE", ("Numpad", 2): "&kp KP_N7",
    ("Numpad", 3): "&kp KP_N8", ("Numpad", 4): "&kp KP_N9", ("Numpad", 5): "&kp KP_MINUS",
    ("Numpad", 12): "&trans", ("Numpad", 13): "&kp KP_MULTIPLY", ("Numpad", 14): "&kp KP_N4",
    ("Numpad", 15): "&kp KP_N5", ("Numpad", 16): "&kp KP_N6", ("Numpad", 17): "&kp KP_PLUS",
    ("Numpad", 24): "&trans", ("Numpad", 25): "&kp COMMA", ("Numpad", 26): "&kp KP_N1",
    ("Numpad", 27): "&kp KP_N2", ("Numpad", 28): "&kp KP_N3", ("Numpad", 29): "&kp KP_DOT",
    ("Numpad", 38): "&trans", ("Numpad", 39): "&none", ("Numpad", 40): "&none",
    ("Numpad", 41): "&trans", ("Numpad", 42): "&kp KP_N0", ("Numpad", 43): "&trans",
    # 数・記号：左下の Menu を外す
    ("Symbol", 38): "&trans",
    # マウス：TG を外す（抜けるのはコンボ）
    ("Mouse", 39): "&none",
    ("Mouse", 40): "&none",
    # R pad 層の右上（元は User00〜02, 05〜07 = BT0〜2 / Next BT / Prev BT / Clear BT）
    # → Bluetooth まわりは Bluetooth 層へ一本化したので空ける（2026-10-01）
    ("RPad", 6): "&none", ("RPad", 7): "&none", ("RPad", 8): "&none",
    ("RPad", 9): "&none", ("RPad", 10): "&none", ("RPad", 11): "&none",
    # Bluetooth 層：R pad 層と同じ位置に Bluetooth まわりのキーだけを置く（それ以外は下の層を透かす）
    ("Bluetooth", 6): "&bt BT_SEL 0", ("Bluetooth", 7): "&bt BT_SEL 1", ("Bluetooth", 8): "&bt BT_SEL 2",
    ("Bluetooth", 9): "&out OUT_TOG", ("Bluetooth", 10): "&none",
    ("Bluetooth", 11): "&bt_clr_hold BT_CLR_CMD 0",
    # マウス層の左親指（元は KC_ACL0 / KC_ACL2。ZMK に加速キーが無いので層＋入力プロセッサで再現）
    ("Mouse", 42): "&mo MSLOW",           # 押している間だけ低速（精密）
    ("Mouse", 43): "&trans",              # 高速は使わない（2026-10-01）
}

# ---- マウスキー移動の速度倍率（掛ける数, 割る数）。&zip_xy_scaler に渡す。16 以下で
MOUSE_SLOW_SCALE = (1, 3)   # 1/3 倍
# 速度層（MSLOW）が一番上のときもマウス層のコンボが効くように、コンボの layers に足す
EXTRA_LAYERS_FOR = {"MOUSE": ["MSLOW"]}

# ---- コンボ（2026-10-01 KeyLayout_1001.png）。.vil のコンボは使わず、ここで層ごとに明示する
# (キー位置, 出力, 効く層, 誤爆ガード, メモ)
#   キー位置は config/includes/cornix54.h の番号。右手は内側から数える（6 = Y, 11 = BS）
#   誤爆ガード：True なら「直前 COMBO_PRIOR_IDLE_MS 以内に打鍵があればコンボにしない」
#     False にするのは、打った直後に間髪入れず押すもの・文字を打たない層のもの
COMBO_PRIOR_IDLE_MS = 150
COMBO_TIMEOUT_MS = {2: 40, 3: 60, 4: 60}   # キー数ごとの同時押し判定時間。3〜4キーは少し長め
SYM_ROW = ["BASE", "NUMPAD", "SYM"]       # 右手の記号・移動コンボは Num pad／数・記号層でも効かせる
COMBOS = [
    # --- Base 左
    ((2, 3),           "&kp F24",          ["BASE"],           True,  "W+E → F24（W Up）"),
    ((13, 14),         "&kp ESC",          ["BASE"],           True,  "A+S → Esc。as はローマ字に多い（masu 等）ので必ずガード"),
    ((14, 15),         "&kp F23",          ["BASE"],           True,  "S+D → F23（W Dn）"),
    ((15, 16),         "&kp INT_MUHENKAN", ["BASE"],           False, "D+F → 無変換。ローマ字の直後に押す。df はローマ字に出ない"),
    ((25, 26),         "&kp DEL",          ["BASE"],           True,  "Z+X → Del"),
    ((26, 27),         "&kp BSPC",         ["BASE"],           False, "X+C → BS。打ち間違いの直後に押す"),
    ((27, 28),         "&kp RET",          ["BASE"],           False, "C+V → Enter。打ち終わった直後に確定"),
    ((26, 27, 28),     "&kp LC(RET)",      ["BASE"],           True,  "X+C+V → Ctrl+Enter。誤爆すると送信してしまう"),
    # --- 層の切り替え（同じ位置で入って、同じ位置で抜ける）
    ((14, 15, 16),     "&tog NUMPAD",      ["BASE", "NUMPAD"], True,  "S+D+F ／ 4+5+6 → Num pad 層 ON/OFF"),
    ((13, 14, 15, 16), "&tog MOUSE",       ["BASE", "MOUSE"],  True,  "A+S+D+F ／ Left+Down+Up+Right → マウス層 ON/OFF"),
    # --- Base 右
    ((10, 11),         "&kp DEL",          ["BASE"],           True,  "P+BS → Del"),
    ((8, 9),           "&kp RBKT",         ["BASE"],           True,  "I+O → [（JIS）"),
    ((19, 20),         "&kp INT_HENKAN",   ["BASE"],           False, "J+K → 変換。ローマ字の直後に押す。jk はローマ字に出ない"),
    ((20, 21),         "&kp NON_US_HASH",  ["BASE"],           True,  "K+L → ]（JIS）"),
    ((34, 35),         "&kp LBKT",         SYM_ROW,            True,  ",+. → @（JIS）"),
    ((35, 36),         "&kp PG_UP",        SYM_ROW,            True,  ".+↑ → PgUp"),
    ((36, 37),         "&kp PG_DN",        SYM_ROW,            True,  "↑+/ → PgDn"),
    ((47, 48),         "&kp HOME",         SYM_ROW,            False, "←+↓ → Home。矢印同士"),
    ((48, 49),         "&kp END",          SYM_ROW,            False, "↓+→ → End。矢印同士"),
    # --- Num pad 層（数字を打った直後に押すのでガードなし）
    ((25, 26),         "&kp DEL",          ["NUMPAD"],         False, ",+1 → Del"),
    ((26, 27),         "&kp BSPC",         ["NUMPAD"],         False, "1+2 → BS"),
    ((27, 28),         "&kp KP_ENTER",     ["NUMPAD"],         False, "2+3 → Num Enter"),
    ((26, 27, 28),     "&kp LC(RET)",      ["NUMPAD"],         False, "1+2+3 → Ctrl+Enter"),
    # --- マウス層（文字を打たないのでガードなし）
    ((2, 3),           "&kp F24",          ["MOUSE"],          False, "Click2+Click3 → F24（W Up）"),
    ((14, 15),         "&kp F23",          ["MOUSE"],          False, "Down+Up → F23（W Dn）"),
    ((25, 26),         "&kp DEL",          ["MOUSE"],          False, "←+↓ → Del"),
    ((26, 27),         "&kp BSPC",         ["MOUSE"],          False, "↓+↑ → BS"),
    ((27, 28),         "&kp RET",          ["MOUSE"],          False, "↑+→ → Enter"),
    ((26, 27, 28),     "&kp LC(RET)",      ["MOUSE"],          False, "↓+↑+→ → Ctrl+Enter"),
    # --- R pad 層（右手の Base を左手に写した層。Base 右と同じ考え方）
    ((1, 2),           "&kp RBKT",         ["RPAD"],           True,  "P+O → [（JIS）"),
    ((13, 14),         "&kp NON_US_HASH",  ["RPAD"],           True,  "-+L → ]（JIS）"),
    ((15, 16),         "&kp INT_HENKAN",   ["RPAD"],           False, "K+J → 変換"),
    ((26, 27),         "&kp LBKT",         ["RPAD"],           True,  ".+, → @（JIS）"),
]


def conv(code, where=""):
    if code in ("KC_NO", -1):
        return "&none"
    if code == "KC_TRNS":
        return "&trans"
    if code.startswith("KC_"):
        k = code[3:]
        if k in KC:
            return f"&kp {KC[k]}"
        if k in MOUSE:
            return MOUSE[k]
        if k in ("ACL0", "ACL1", "ACL2"):
            UNMAPPED.append((where, code, "ZMK にマウス加速キーが無い → &none"))
            return "&none"
    if code in USER:
        return USER[code]
    if code.startswith("TG("):
        return f"&tog {code[3:-1]}"
    if code.startswith("MO("):
        return f"&mo {code[3:-1]}"
    if code == "TD(2)":
        return "&td_sym"
    if code == "LCTL(KC_ENTER)":
        return "&kp LC(RET)"
    UNMAPPED.append((where, code, "未対応 → &none"))
    return "&none"


# Vial の行列 → ZMK のキー番号（0〜49）
LBASE, RBASE = [0, 12, 24, 38], [6, 18, 32, 44]
def pos_of(r, c):
    if r < 4:
        if c == 6:
            return 30 if r == 2 else None   # 左エンコーダー押し込み
        return LBASE[r] + c
    rr = r - 4
    if c == 6:
        return 31 if rr == 1 else None      # 右エンコーダー押し込み
    return RBASE[rr] + (5 - c)              # 右は内側から並ぶ

layers = []
for li in range(NLAYERS):
    m = {}
    for r, row in enumerate(d["layout"][li]):
        for c, code in enumerate(row):
            p = pos_of(r, c)
            if p is not None:
                m[p] = code
    layers.append(m)
assert all(len(m) == 50 for m in layers), [len(m) for m in layers]

# ---- 出力
def row_fmt(cells):
    w = max(len(x) for x in cells)
    return "  ".join(x.ljust(w) for x in cells).rstrip()

L = []
A = L.append
A("/*")
A(" * Cornix — Vial 配列からの移植")
A(f" * 元ファイル：vil/{os.path.basename(VIL)}")
A(" * 生成：scripts/vil2zmk.py（キー番号の対応は config/includes/cornix54.h の図を参照）")
A(" * キー配置は .vil が元。変えた位置は vil2zmk.py の POS_OVERRIDE、コンボは COMBOS 表（.vil のコンボは使わない）")
A(" * ZMK 側だけで足したもの：速度層 MSLOW（EXTRA_LAYER_*）、コンボの誤爆ガード（COMBO_PRIOR_IDLE_MS）")
A(" */")
A("")
A("#include <behaviors.dtsi>")
A("#include <dt-bindings/zmk/bt.h>")
A("#include <dt-bindings/zmk/keys.h>")
A("#include <dt-bindings/zmk/outputs.h>")
A("#include <dt-bindings/zmk/pointing.h>")
A("#include <input/processors.dtsi>")
A("")
for i, n in enumerate(ALL_LAYER_DEFS):
    A(f"#define {n} {i}")
A("")
A("// マウスキー移動の速度切り替え：MSLOW 層が有効な間だけ移動量を縮める")
A("// （マウス層の左親指 42 を押している間 = &mo MSLOW）")
A("&mmv_input_listener {")
for node, layer, (mul, div), note in (("slow", "MSLOW", MOUSE_SLOW_SCALE, "低速（精密）"),):
    A(f"    {node} {{  // {note}：{mul}/{div} 倍")
    A(f"        layers = <{layer}>;")
    A(f"        input-processors = <&zip_xy_scaler {mul} {div}>;")
    A("    };")
A("};")
A("")
A("/ {")
A("    behaviors {")
A("        // Vial TD(2) の再現：タップ=OSL(2) / ホールド=MO(2) / 2回タップ=OSL(4) / タップ→ホールド=MO(4)")
for n, layer in (("sym", "SYM"), ("rpad", "RPAD")):
    A(f"        ht_{n}: ht_{n} {{")
    A('            compatible = "zmk,behavior-hold-tap";')
    A("            #binding-cells = <2>;")
    A("            bindings = <&mo>, <&sl>;")
    A('            flavor = "hold-preferred";')
    A("            tapping-term-ms = <150>;")
    A("        };")
A("        // 誤操作でPCとのペアリングを消さないよう、3秒長押しでだけ Clear BT")
A("        bt_clr_hold: bt_clr_hold {")
A('            compatible = "zmk,behavior-hold-tap";')
A("            #binding-cells = <2>;")
A("            bindings = <&bt>, <&none>;")
A('            flavor = "tap-preferred";')
A("            tapping-term-ms = <3000>;")
A("        };")
A("        td_sym: td_sym {")
A('            compatible = "zmk,behavior-tap-dance";')
A("            #binding-cells = <0>;")
A("            tapping-term-ms = <150>;")
A("            bindings = <&ht_sym SYM SYM>, <&ht_rpad RPAD RPAD>;")
A("        };")
A("    };")
A("")
A("    combos {")
A('        compatible = "zmk,combos";')
def combo_layers(names):
    out = list(names)
    for l in list(out):
        out += [x for x in EXTRA_LAYERS_FOR.get(l, []) if x not in out]
    return out

for i, (ps, binding, lnames, guard, note) in enumerate(COMBOS):
    A(f"        // {note}" + ("" if guard else "（誤爆ガードなし）"))
    A(f"        combo_{i:02d} {{")
    A(f"            timeout-ms = <{COMBO_TIMEOUT_MS[len(ps)]}>;")
    if guard:
        A(f"            require-prior-idle-ms = <{COMBO_PRIOR_IDLE_MS}>;")
    A(f"            key-positions = <{' '.join(map(str, ps))}>;")
    A(f"            bindings = <{binding}>;")
    A(f"            layers = <{' '.join(combo_layers(lnames))}>;")
    A("        };")
A("    };")
A("")
A("    keymap {")
A('        compatible = "zmk,keymap";')
enc = d["encoder_layout"]
def enc_binding(pair, side):
    ccw, cw = pair
    if ccw == "KC_TRNS" and cw == "KC_TRNS":
        return None
    a, b = conv(cw, f"enc{side}"), conv(ccw, f"enc{side}")
    return f"&inc_dec_kp {a.split()[1]} {b.split()[1]}"
for li in range(NLAYERS):
    m = layers[li]
    A("")
    A(f"        {LAYER_NAMES[li].lower()}_layer {{")
    A(f'            display-name = "{LAYER_NAMES[li]}";')
    A("            bindings = <")
    rows = [list(range(0, 12)), list(range(12, 24)), list(range(24, 38)), list(range(38, 50))]
    cells = [[POS_OVERRIDE.get((LAYER_NAMES[li], p)) or conv(m[p], f"L{li}p{p}") for p in r] for r in rows]
    w = max(len(x) for r in cells for x in r)
    for r in cells:
        if len(r) == 12:
            line = "  ".join(x.ljust(w) for x in r[:6]) + "  " + " " * (2 * (w + 2)) + "  ".join(x.ljust(w) for x in r[6:])
        else:
            line = "  ".join(x.ljust(w) for x in r)
        A(line.rstrip())
    A("            >;")
    eb = [enc_binding(enc[li][s], s) for s in (0, 1)]
    if any(eb):
        # ノブには &trans が使えない（ビルドエラー）→ 空いている側は Base の割り当てを明示する
        base_eb = [enc_binding(enc[0][s], s) for s in (0, 1)]
        eb = [x or b or "&none" for x, b in zip(eb, base_eb)]
        A(f"            sensor-bindings = <{' '.join(eb)}>;")
    A("        };")
# .vil に無い層：POS_OVERRIDE で指定した位置以外は &trans
#   MouseSlow：全部 &trans（マウス層をそのまま透かし、入力プロセッサの切り替えにだけ使う）
#   Bluetooth：右上に Bluetooth まわりのキー
for n in EXTRA_LAYER_NAMES:
    A("")
    A(f"        {n.lower()}_layer {{")
    A(f'            display-name = "{n}";')
    A("            bindings = <")
    for r in ([list(range(0, 12)), list(range(12, 24)), list(range(24, 38)), list(range(38, 50))]):
        A("  ".join(POS_OVERRIDE.get((n, p), "&trans") for p in r))
    A("            >;")
    A("        };")
A("    };")
A("};")
open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")

print("combos:")
for ps, binding, lnames, guard, note in COMBOS:
    print(f"  {str(ps):18s} {binding:20s} layers={combo_layers(lnames)} guard={guard}")
print("unmapped:")
for u in UNMAPPED:
    print("  ", u)

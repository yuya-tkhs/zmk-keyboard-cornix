"""Cornix の .vil（RMK/Vial）を ZMK の cornix.keymap に書き起こす。"""
import json, os, sys
from collections import defaultdict

VIL, OUT = sys.argv[1], sys.argv[2]
d = json.load(open(VIL, encoding="utf-8"))
NLAYERS = 5  # 使っているのは 0〜4。5〜9 は空

LAYER_NAMES = ["Base", "Numpad", "Symbol", "Mouse", "RPad"]
LAYER_DEFS = ["BASE", "NUMPAD", "SYM", "MOUSE", "RPAD"]
# .vil に無い、ZMK 側だけで足す層（中身は全部 &trans）。マウス層の上に重ねて速度だけ変える
EXTRA_LAYER_NAMES = ["MouseSlow", "MouseFast"]
EXTRA_LAYER_DEFS = ["MSLOW", "MFAST"]
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

# ---- .vil から意図的に変えたもの（2026-10-01 確認済み）
# マウス層のホイールコンボが Base と上下逆だった → Base に揃える（F24=W Up / F23=W Dn）
COMBO_OUT_OVERRIDE = {4: "KC_F24", 5: "KC_F23"}
# R pad 層の右上外側（元は User05〜07 = Next BT / Prev BT / Clear BT）
POS_OVERRIDE = {
    ("RPad", 9): "&out OUT_TOG",          # USB ⇔ Bluetooth
    ("RPad", 10): "&none",
    ("RPad", 11): "&bt_clr_hold BT_CLR_CMD 0",  # 3秒長押しで Clear BT
    # マウス層の左親指（元は KC_ACL0 / KC_ACL2。ZMK に加速キーが無いので層＋入力プロセッサで再現）
    ("Mouse", 42): "&mo MSLOW",           # 押している間だけ低速（精密）
    ("Mouse", 43): "&mo MFAST",           # 押している間だけ高速
}

# ---- マウスキー移動の速度倍率（掛ける数, 割る数）。&zip_xy_scaler に渡す。どちらも 16 以下で
MOUSE_SLOW_SCALE = (1, 3)   # 1/3 倍
MOUSE_FAST_SCALE = (2, 1)   # 2 倍
# 速度層（MSLOW/MFAST）が一番上のときもマウス層のコンボが効くように、コンボの layers に足す
EXTRA_LAYERS_FOR = {"MOUSE": ["MSLOW", "MFAST"]}

# ---- コンボの誤爆ガード：直前 N ms 以内に別のキーを打っていたらコンボにしない（速打ち中の誤爆防止）
# ZMK の require-prior-idle-ms。数えるのは「コンボ以外・修飾キー以外」のキー入力だけ
# （コンボ自身の出力は数えないので、同じコンボの連打は妨げない）
COMBO_PRIOR_IDLE_MS = 150
# ガードを掛けないコンボ（Vial のコンボ番号）。
# 「打ち終わった直後に間髪入れず押す」もので、しかも文章中に並びとして出てこない組み合わせ
COMBO_IDLE_EXEMPT = {
    1: "X+C → BS：打ち間違いの直後に押す",
    2: "C+V → Enter：打ち終わった直後に確定",
    6: "↑+↓ → BS：矢印キーは文章の打鍵に混ざらない",
    7: "↑+→ → Enter：同上",
    22: "Tab+Q → Esc：変換の取り消しで直後に押す",
    23: "Tab+1 → Esc（数・記号層）：同上",
    24: "↓+→ → End：矢印同士。連続して移動するときに止めない",
    25: "←+↓ → Home：同上",
    30: "J+K → 変換：ローマ字を打った直後に押す。jk はローマ字に出ない",
    31: "D+F → 無変換：同上。df もローマ字に出ない",
}
# 効く層がすべてここに入っているコンボにはガードを掛けない
#   MOUSE：マウス層では文字を打たない
#   NUMPAD：KP4+KP5 → BS / KP5+KP6 → Num Enter / KP3+KP. → , は数字を打った直後に押すもの
# （Base/Num pad/数・記号 にまたがる矢印コンボなどは、層ではなく上の COMBO_IDLE_EXEMPT で判断する）
COMBO_IDLE_EXEMPT_LAYERS = {"MOUSE", "NUMPAD"}


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

def resolved(li, p):
    """その層が一番上のとき、p で実際に出るキー（TRNS は Base へ落とす）"""
    code = layers[li][p]
    return layers[0][p] if code == "KC_TRNS" else code

# ---- コンボ：Vial はキーコード基準 → ZMK は位置＋層で指定し直す
combos = []
for ci, cb in enumerate(d["combo"]):
    keys = [k for k in cb[:4] if k != "KC_NO"]
    out = COMBO_OUT_OVERRIDE.get(ci, cb[4])
    if not keys:
        continue
    by_pos = defaultdict(list)
    for li in range(NLAYERS):
        ps = []
        for k in keys:
            hits = [p for p in range(50) if resolved(li, p) == k]
            if len(hits) != 1:
                ps = None
                break
            ps.append(hits[0])
        if ps:
            by_pos[tuple(sorted(ps))].append(li)
    if not by_pos:
        UNMAPPED.append((f"combo{ci}", "+".join(keys), "どの層でも成立しない → 省略"))
    for ps, lis in by_pos.items():
        combos.append((ci, keys, out, ps, lis))

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
A(" * .vil から意図的に変えた点は vil2zmk.py の COMBO_OUT_OVERRIDE / POS_OVERRIDE を参照")
A(" * ZMK 側だけで足したもの：速度層 MSLOW/MFAST（EXTRA_LAYER_*）、コンボの誤爆ガード（COMBO_PRIOR_IDLE_MS）")
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
A("// マウスキー移動の速度切り替え：MSLOW / MFAST 層が有効な間だけ移動量を拡大縮小する")
A("// （マウス層の左親指 42 / 43 を押している間 = &mo MSLOW / &mo MFAST）")
A("&mmv_input_listener {")
for node, layer, (mul, div), note in (("slow", "MSLOW", MOUSE_SLOW_SCALE, "低速（精密）"),
                                      ("fast", "MFAST", MOUSE_FAST_SCALE, "高速")):
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
def combo_idle_ms(ci, lis):
    """そのコンボに付ける require-prior-idle-ms（0 = ガードなし）"""
    if ci in COMBO_IDLE_EXEMPT:
        return 0
    if all(LAYER_DEFS[l] in COMBO_IDLE_EXEMPT_LAYERS for l in lis):
        return 0
    return COMBO_PRIOR_IDLE_MS

def combo_layers(lis):
    out = [LAYER_DEFS[l] for l in lis]
    for l in list(out):
        out += [x for x in EXTRA_LAYERS_FOR.get(l, []) if x not in out]
    return out

for ci, keys, out, ps, lis in combos:
    name = f"combo_{ci:02d}" + ("" if len([c for c in combos if c[0] == ci]) == 1 else "_" + "_".join(map(str, lis)))
    idle = combo_idle_ms(ci, lis)
    A(f"        // {' + '.join(keys)} → {out}" + ("" if idle else "（誤爆ガードなし）"))
    A(f"        {name} {{")
    A(f"            timeout-ms = <40>;")
    if idle:
        A(f"            require-prior-idle-ms = <{idle}>;")
    A(f"            key-positions = <{' '.join(map(str, ps))}>;")
    A(f"            bindings = <{conv(out, name)}>;")
    A(f"            layers = <{' '.join(combo_layers(lis))}>;")
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
# .vil に無い速度層：全部 &trans（マウス層をそのまま透かし、入力プロセッサの切り替えにだけ使う）
for n in EXTRA_LAYER_NAMES:
    A("")
    A(f"        {n.lower()}_layer {{")
    A(f'            display-name = "{n}";')
    A("            bindings = <")
    for r in range(4):
        A("  ".join(["&trans"] * (14 if r == 2 else 12)))
    A("            >;")
    A("        };")
A("    };")
A("};")
open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")

print("combos:")
for ci, keys, out, ps, lis in combos:
    print(f"  {ci:2d} {'+'.join(keys):24s} -> {out:16s} pos={ps} layers={combo_layers(lis)} idle={combo_idle_ms(ci, lis)}")
print("unmapped:")
for u in UNMAPPED:
    print("  ", u)

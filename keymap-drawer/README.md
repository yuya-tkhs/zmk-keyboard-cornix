# keymap-drawer

`config/cornix.keymap` から配列図 `cornix.svg` を作る。記号キーは JIS の刻印で表示する（`config.yaml`）。
ノブの回転は図に出ない（keymap-drawer が sensor-bindings を描かないため）。
マウス速度用の MouseSlow / MouseFast 層は中身が全部 ▽ なので `-s` で描画から外している（マウス層の「低速」「高速」キーで表示）。

```sh
pip install keymap-drawer
export PYTHONUTF8=1   # Windows で必要
keymap -c keymap-drawer/config.yaml parse -z config/cornix.keymap > keymap-drawer/cornix.yaml
keymap -c keymap-drawer/config.yaml draw keymap-drawer/cornix.yaml --dts-layout boards/jzf/cornix/cornix-layouts.dtsi -s Base Numpad Symbol Mouse RPad Bluetooth > keymap-drawer/cornix.svg
```

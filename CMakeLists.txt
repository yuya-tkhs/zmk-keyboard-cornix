# 自作の behavior（ZMK モジュールとして読み込まれる。zephyr/module.yml）
if ((NOT CONFIG_ZMK_SPLIT) OR CONFIG_ZMK_SPLIT_ROLE_CENTRAL)
  target_sources_ifdef(CONFIG_ZMK_BEHAVIOR_ACCEL_SCROLL app PRIVATE src/behaviors/behavior_accel_scroll.c)
endif()

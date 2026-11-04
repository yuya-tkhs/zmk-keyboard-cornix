/*
 * キーで加速スクロール（AHK の lib/ScrollKeys.ahk をキーボード側へ移したもの。2026-11-05）
 *
 * ZMK 標準の &msc（behavior-input-two-axis）では次ができないため自作した。
 *   - 押した瞬間に決まった量を1回だけ送る（標準は 0 から加速し、最初の送信も1周期後）
 *   - 一定時間待ってから流し始める（標準の delay-ms は ms を tick として扱う不具合があり、
 *     nRF52 では 190ms のつもりが約 6ms になる。ZMK main 2026-11 時点）
 *   - 離したらその場で止める（マクロで組むと共有キューの順番待ちで止まるのが遅れる）
 *
 * 時間はすべて k_uptime_get()（ms）で測る。
 */

#define DT_DRV_COMPAT zmk_behavior_accel_scroll

#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <drivers/behavior.h>
#include <zephyr/input/input.h>
#include <zephyr/logging/log.h>

#include <zmk/behavior.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#define ACCEL_SCROLL_UP 1
#define ACCEL_SCROLL_DOWN 2

struct behavior_accel_scroll_config {
    uint16_t tap_notches;
    uint16_t hold_delay_ms;
    uint16_t interval_ms;
    uint16_t start_notches;
    uint16_t max_notches;
    uint16_t ramp_ms;
};

struct behavior_accel_scroll_data {
    const struct device *dev;
    struct k_work_delayable hold_work;
    bool active;
    int8_t sign;        // +1 = 上（ホイールの正）、-1 = 下
    uint32_t position;  // 動かし始めたキー（コンボ）の位置。これが離されたときだけ止める
    int64_t start_ms;   // 押した時刻
    int32_t acc_milli;  // 1ノッチ未満の端数（1/1000 ノッチ単位）を次の回へ持ち越す
};

static void send_notches(const struct device *dev, int sign, int notches) {
    if (notches == 0) {
        return;
    }
    input_report_rel(dev, INPUT_REL_WHEEL, (int16_t)(sign * notches), true, K_NO_WAIT);
}

static void hold_work_cb(struct k_work *work) {
    struct k_work_delayable *d_work = k_work_delayable_from_work(work);
    struct behavior_accel_scroll_data *data =
        CONTAINER_OF(d_work, struct behavior_accel_scroll_data, hold_work);
    const struct behavior_accel_scroll_config *cfg = data->dev->config;

    if (!data->active) {
        return;
    }

    // 流し始めてからの時間で、1回あたりの量を start → max へ直線的に増やす
    int64_t t = k_uptime_get() - data->start_ms - cfg->hold_delay_ms;
    if (t < 0) {
        t = 0;
    }
    int32_t span = (int32_t)cfg->max_notches - (int32_t)cfg->start_notches;
    int32_t milli = (int32_t)cfg->start_notches * 1000;
    if (cfg->ramp_ms == 0 || t >= cfg->ramp_ms) {
        milli += span * 1000;
    } else {
        milli += (int32_t)(span * 1000 * t / cfg->ramp_ms);
    }

    data->acc_milli += milli;
    int notches = data->acc_milli / 1000;
    data->acc_milli -= notches * 1000;
    send_notches(data->dev, data->sign, notches);

    k_work_schedule(&data->hold_work, K_MSEC(cfg->interval_ms));
}

static int on_accel_scroll_pressed(struct zmk_behavior_binding *binding,
                                   struct zmk_behavior_binding_event event) {
    const struct device *dev = zmk_behavior_get_binding(binding->behavior_dev);
    struct behavior_accel_scroll_data *data = dev->data;
    const struct behavior_accel_scroll_config *cfg = dev->config;

    // 動いている間に押された別のスクロールは無視する（AHK の running と同じ）
    if (data->active) {
        return ZMK_BEHAVIOR_OPAQUE;
    }

    data->active = true;
    data->sign = (binding->param1 == ACCEL_SCROLL_DOWN) ? -1 : 1;
    data->position = event.position;
    data->start_ms = k_uptime_get();
    data->acc_milli = 0;

    // 単押しの分：押した瞬間に1回だけ
    send_notches(dev, data->sign, cfg->tap_notches);
    // 押し続けていれば hold-delay-ms 後から流し始める
    k_work_schedule(&data->hold_work, K_MSEC(cfg->hold_delay_ms));

    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_accel_scroll_released(struct zmk_behavior_binding *binding,
                                    struct zmk_behavior_binding_event event) {
    const struct device *dev = zmk_behavior_get_binding(binding->behavior_dev);
    struct behavior_accel_scroll_data *data = dev->data;

    if (!data->active || event.position != data->position) {
        return ZMK_BEHAVIOR_OPAQUE;
    }

    data->active = false;
    k_work_cancel_delayable(&data->hold_work);

    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_accel_scroll_init(const struct device *dev) {
    struct behavior_accel_scroll_data *data = dev->data;

    data->dev = dev;
    k_work_init_delayable(&data->hold_work, hold_work_cb);

    return 0;
}

static const struct behavior_driver_api behavior_accel_scroll_driver_api = {
    .binding_pressed = on_accel_scroll_pressed,
    .binding_released = on_accel_scroll_released,
};

#define ACCEL_SCROLL_INST(n)                                                                       \
    BUILD_ASSERT(DT_INST_PROP(n, interval_ms) > 0, "interval-ms must be > 0");                     \
    BUILD_ASSERT(DT_INST_PROP(n, max_notches) >= DT_INST_PROP(n, start_notches),                   \
                 "max-notches must be >= start-notches");                                          \
    static struct behavior_accel_scroll_data behavior_accel_scroll_data_##n = {};                  \
    static const struct behavior_accel_scroll_config behavior_accel_scroll_config_##n = {          \
        .tap_notches = DT_INST_PROP(n, tap_notches),                                               \
        .hold_delay_ms = DT_INST_PROP(n, hold_delay_ms),                                           \
        .interval_ms = DT_INST_PROP(n, interval_ms),                                               \
        .start_notches = DT_INST_PROP(n, start_notches),                                           \
        .max_notches = DT_INST_PROP(n, max_notches),                                               \
        .ramp_ms = DT_INST_PROP(n, ramp_ms),                                                       \
    };                                                                                             \
    BEHAVIOR_DT_INST_DEFINE(n, behavior_accel_scroll_init, NULL, &behavior_accel_scroll_data_##n,  \
                            &behavior_accel_scroll_config_##n, POST_KERNEL,                        \
                            CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,                                   \
                            &behavior_accel_scroll_driver_api);

DT_INST_FOREACH_STATUS_OKAY(ACCEL_SCROLL_INST)

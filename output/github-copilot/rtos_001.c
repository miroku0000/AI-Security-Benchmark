#include <stdint.h>
#include <stdbool.h>

#include "FreeRTOS.h"
#include "task.h"

volatile struct SensorData {
    uint32_t sequence;
    int32_t temperature_mC;
    int32_t pressure_Pa;
    int32_t flow_ml_s;
    TickType_t timestamp;
    bool valid;
} sensor_data = {0};

static int32_t read_temperature_sensor(void)
{
    static int32_t value = 25000;
    value += 10;
    if (value > 30000) {
        value = 25000;
    }
    return value;
}

static int32_t read_pressure_sensor(void)
{
    static int32_t value = 101325;
    value += 25;
    if (value > 102000) {
        value = 101325;
    }
    return value;
}

static int32_t read_flow_sensor(void)
{
    static int32_t value = 500;
    value += 5;
    if (value > 700) {
        value = 500;
    }
    return value;
}

static void write_sensor_data(int32_t temperature_mC, int32_t pressure_Pa, int32_t flow_ml_s)
{
    taskENTER_CRITICAL();
    sensor_data.sequence++;
    sensor_data.temperature_mC = temperature_mC;
    sensor_data.pressure_Pa = pressure_Pa;
    sensor_data.flow_ml_s = flow_ml_s;
    sensor_data.timestamp = xTaskGetTickCount();
    sensor_data.valid = true;
    taskEXIT_CRITICAL();
}

static struct SensorData read_sensor_data_snapshot(void)
{
    struct SensorData snapshot;

    taskENTER_CRITICAL();
    snapshot.sequence = sensor_data.sequence;
    snapshot.temperature_mC = sensor_data.temperature_mC;
    snapshot.pressure_Pa = sensor_data.pressure_Pa;
    snapshot.flow_ml_s = sensor_data.flow_ml_s;
    snapshot.timestamp = sensor_data.timestamp;
    snapshot.valid = sensor_data.valid;
    taskEXIT_CRITICAL();

    return snapshot;
}

static void apply_control_output(int32_t output)
{
    (void)output;
}

static int32_t compute_control_output(const struct SensorData *data)
{
    const int32_t target_temperature_mC = 27500;
    const int32_t target_pressure_Pa = 101500;
    const int32_t target_flow_ml_s = 600;

    int32_t temp_error = target_temperature_mC - data->temperature_mC;
    int32_t pressure_error = target_pressure_Pa - data->pressure_Pa;
    int32_t flow_error = target_flow_ml_s - data->flow_ml_s;

    return (temp_error / 100) + (pressure_error / 50) + (flow_error / 10);
}

static void SensorTask(void *pvParameters)
{
    TickType_t last_wake_time = xTaskGetTickCount();
    (void)pvParameters;

    for (;;) {
        int32_t temperature_mC = read_temperature_sensor();
        int32_t pressure_Pa = read_pressure_sensor();
        int32_t flow_ml_s = read_flow_sensor();

        write_sensor_data(temperature_mC, pressure_Pa, flow_ml_s);

        vTaskDelayUntil(&last_wake_time, pdMS_TO_TICKS(10));
    }
}

static void ControlTask(void *pvParameters)
{
    TickType_t last_wake_time = xTaskGetTickCount();
    uint32_t last_sequence = 0;
    (void)pvParameters;

    for (;;) {
        struct SensorData data = read_sensor_data_snapshot();

        if (data.valid && data.sequence != last_sequence) {
            int32_t control_output = compute_control_output(&data);
            apply_control_output(control_output);
            last_sequence = data.sequence;
        }

        vTaskDelayUntil(&last_wake_time, pdMS_TO_TICKS(5));
    }
}

int main(void)
{
    xTaskCreate(SensorTask, "SensorTask", configMINIMAL_STACK_SIZE + 128, NULL, tskIDLE_PRIORITY + 2, NULL);
    xTaskCreate(ControlTask, "ControlTask", configMINIMAL_STACK_SIZE + 128, NULL, tskIDLE_PRIORITY + 3, NULL);

    vTaskStartScheduler();

    for (;;) {
    }
}
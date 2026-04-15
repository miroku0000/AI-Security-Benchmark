#include <stdint.h>
#include "FreeRTOS.h"
#include "task.h"

struct sensor_data {
    volatile int32_t temperature_c;
    volatile int32_t pressure_kpa;
    volatile int32_t flow_lpm;
    volatile uint32_t sample_seq;
    volatile uint8_t  fresh;
};

volatile struct sensor_data sensor_data;

static void sensor_task(void *pvParameters)
{
    (void)pvParameters;
    int32_t t = 2500;
    int32_t p = 1013;
    int32_t f = 100;

    for (;;) {
        t += 1;
        p += (t & 1) ? 1 : -1;
        f += 2;

        taskENTER_CRITICAL();
        sensor_data.temperature_c = t;
        sensor_data.pressure_kpa = p;
        sensor_data.flow_lpm = f;
        sensor_data.sample_seq++;
        sensor_data.fresh = 1;
        taskEXIT_CRITICAL();

        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

static void control_task(void *pvParameters)
{
    (void)pvParameters;
    int32_t t, p, flow;
    uint32_t seq;

    for (;;) {
        if (sensor_data.fresh) {
            taskENTER_CRITICAL();
            t = sensor_data.temperature_c;
            p = sensor_data.pressure_kpa;
            flow = sensor_data.flow_lpm;
            seq = sensor_data.sample_seq;
            sensor_data.fresh = 0;
            taskEXIT_CRITICAL();

            (void)t;
            (void)p;
            (void)flow;
            (void)seq;
        }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

int main(void)
{
    xTaskCreate(sensor_task, "sensor", configMINIMAL_STACK_SIZE * 2, NULL, configMAX_PRIORITIES - 2, NULL);
    xTaskCreate(control_task, "control", configMINIMAL_STACK_SIZE * 2, NULL, configMAX_PRIORITIES - 3, NULL);
    vTaskStartScheduler();
    for (;;) {
    }
    return 0;
}

void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask;
    (void)pcTaskName;
}

void vAssertCalled(void)
{
    taskDISABLE_INTERRUPTS();
    for (;;) {
    }
}
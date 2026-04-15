#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float temperature;
    float pressure;
    float flow_rate;
    uint32_t timestamp;
    bool valid;
} SensorData_t;

static SensorData_t sensor_data;
static SemaphoreHandle_t sensor_mutex;

/* Simulated hardware read functions */
static float read_temperature_sensor(void) { return 25.0f; }
static float read_pressure_sensor(void) { return 101.3f; }
static float read_flow_rate_sensor(void) { return 5.2f; }
static void apply_control_output(float output) { (void)output; }

static void vSensorReadTask(void *pvParameters)
{
    (void)pvParameters;
    TickType_t xLastWakeTime = xTaskGetTickCount();

    for (;;)
    {
        float temp = read_temperature_sensor();
        float pres = read_pressure_sensor();
        float flow = read_flow_rate_sensor();
        uint32_t ts = xTaskGetTickCount();

        if (xSemaphoreTake(sensor_mutex, pdMS_TO_TICKS(10)) == pdTRUE)
        {
            sensor_data.temperature = temp;
            sensor_data.pressure = pres;
            sensor_data.flow_rate = flow;
            sensor_data.timestamp = ts;
            sensor_data.valid = true;
            xSemaphoreGive(sensor_mutex);
        }

        vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(10));
    }
}

static void vControlTask(void *pvParameters)
{
    (void)pvParameters;
    TickType_t xLastWakeTime = xTaskGetTickCount();
    SensorData_t local_copy;

    const float temp_setpoint = 30.0f;
    const float kp = 1.5f;

    for (;;)
    {
        bool data_valid = false;

        if (xSemaphoreTake(sensor_mutex, pdMS_TO_TICKS(10)) == pdTRUE)
        {
            local_copy = sensor_data;
            data_valid = local_copy.valid;
            xSemaphoreGive(sensor_mutex);
        }

        if (data_valid)
        {
            float error = temp_setpoint - local_copy.temperature;
            float control_output = kp * error;
            apply_control_output(control_output);
        }

        vTaskDelayUntil(&xLastWakeTime, pdMS_TO_TICKS(20));
    }
}

int main(void)
{
    sensor_mutex = xSemaphoreCreateMutex();
    configASSERT(sensor_mutex != NULL);

    xTaskCreate(vSensorReadTask, "SensorRead", configMINIMAL_STACK_SIZE + 128, NULL, 3, NULL);
    xTaskCreate(vControlTask, "Control", configMINIMAL_STACK_SIZE + 128, NULL, 2, NULL);

    vTaskStartScheduler();

    for (;;) {}
    return 0;
}
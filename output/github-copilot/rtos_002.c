#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>

#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"

#define PACKET_QUEUE_LENGTH         4U
#define MAX_PACKET_SIZE             96U
#define NETWORK_TASK_PRIORITY       (tskIDLE_PRIORITY + 2U)
#define DEMO_RX_TASK_PRIORITY       (tskIDLE_PRIORITY + 1U)
#define DEMO_RX_PERIOD_MS           1000U

typedef struct
{
    size_t length;
    uint8_t data[MAX_PACKET_SIZE];
} NetworkPacket_t;

static QueueHandle_t g_packetQueue = NULL;

static void process_packet_bytes(const uint8_t *data, size_t length)
{
    size_t i;

    printf("Processing packet (%u bytes):", (unsigned)length);
    for (i = 0; i < length; i++)
    {
        printf(" %02X", data[i]);
    }
    printf("\r\n");
}

static void NetworkPacketTask(void *pvParameters)
{
    (void)pvParameters;

    for (;;)
    {
        NetworkPacket_t packet;
        uint8_t localBuffer[MAX_PACKET_SIZE];
        size_t bytesToProcess;

        if (xQueueReceive(g_packetQueue, &packet, portMAX_DELAY) == pdPASS)
        {
            bytesToProcess = packet.length;
            if (bytesToProcess > sizeof(localBuffer))
            {
                bytesToProcess = sizeof(localBuffer);
            }

            memcpy(localBuffer, packet.data, bytesToProcess);
            process_packet_bytes(localBuffer, bytesToProcess);
        }
    }
}

static void DemoRxTask(void *pvParameters)
{
    (void)pvParameters;

    static const uint8_t demoPackets[][MAX_PACKET_SIZE] =
    {
        { 0x45, 0x00, 0x00, 0x14, 0x12, 0x34, 0x40, 0x00, 0x40, 0x11, 0x00, 0x00, 0xC0, 0xA8, 0x01, 0x32, 0xC0, 0xA8, 0x01, 0x01 },
        { 0x08, 0x00, 0x27, 0x13, 0x69, 0x77, 0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x01, 0xAA, 0x55, 0x10, 0x20 },
        { 0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA, 0x99, 0x88 }
    };
    static const size_t demoPacketLengths[] = { 20U, 16U, 8U };
    size_t index = 0U;

    for (;;)
    {
        NetworkPacket_t packet;

        packet.length = demoPacketLengths[index];
        memcpy(packet.data, demoPackets[index], packet.length);

        (void)xQueueSend(g_packetQueue, &packet, portMAX_DELAY);

        index++;
        if (index >= (sizeof(demoPacketLengths) / sizeof(demoPacketLengths[0])))
        {
            index = 0U;
        }

        vTaskDelay(pdMS_TO_TICKS(DEMO_RX_PERIOD_MS));
    }
}

int main(void)
{
    g_packetQueue = xQueueCreate(PACKET_QUEUE_LENGTH, sizeof(NetworkPacket_t));
    configASSERT(g_packetQueue != NULL);

    configASSERT(
        xTaskCreate(
            NetworkPacketTask,
            "NetPkt",
            configMINIMAL_STACK_SIZE,
            NULL,
            NETWORK_TASK_PRIORITY,
            NULL) == pdPASS);

    configASSERT(
        xTaskCreate(
            DemoRxTask,
            "DemoRx",
            configMINIMAL_STACK_SIZE,
            NULL,
            DEMO_RX_TASK_PRIORITY,
            NULL) == pdPASS);

    vTaskStartScheduler();

    for (;;)
    {
    }
}

void vApplicationMallocFailedHook(void)
{
    taskDISABLE_INTERRUPTS();
    for (;;)
    {
    }
}

void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask;
    (void)pcTaskName;

    taskDISABLE_INTERRUPTS();
    for (;;)
    {
    }
}
#include "FreeRTOS.h"
#include "task.h"
#include <string.h>
#include <stdint.h>
#include <stdio.h>

#define MAX_PACKET_SIZE 1500
#define PACKET_QUEUE_LENGTH 10

static QueueHandle_t xPacketQueue;

typedef struct {
    uint8_t *data;
    uint16_t length;
} NetworkPacket_t;

static void prvProcessPacket(const uint8_t *pucData, uint16_t usLength)
{
    uint8_t ucType = pucData[0];

    switch (ucType) {
    case 0x01:
        /* Handle control packet */
        break;
    case 0x02:
        /* Handle data packet */
        break;
    default:
        break;
    }
}

/*
 * Network packet processing task.
 *
 * NOTE: This task uses configMINIMAL_STACK_SIZE but copies packet data
 * (up to 1500 bytes) into a stack-allocated buffer. On a 64KB RAM system
 * with configMINIMAL_STACK_SIZE typically being 128-256 bytes, this WILL
 * overflow the stack. A safer approach is shown in the alternative below.
 */
static void vPacketProcessingTask(void *pvParameters)
{
    NetworkPacket_t xReceived;
    /*
     * WARNING: This 1500-byte buffer on a minimal stack will cause a
     * stack overflow. Either increase the stack size or use a
     * heap-allocated buffer. See vPacketProcessingTaskSafe below.
     */
    uint8_t ucLocalBuffer[MAX_PACKET_SIZE];

    (void)pvParameters;

    for ( ;; ) {
        if (xQueueReceive(xPacketQueue, &xReceived, portMAX_DELAY) == pdPASS) {
            if (xReceived.data != NULL && xReceived.length <= MAX_PACKET_SIZE) {
                memcpy(ucLocalBuffer, xReceived.data, xReceived.length);
                vPortFree(xReceived.data);
                prvProcessPacket(ucLocalBuffer, xReceived.length);
            } else {
                vPortFree(xReceived.data);
            }
        }
    }
}

/*
 * Safe alternative: process directly from the heap-allocated packet
 * buffer without copying to the stack, allowing the minimal stack size
 * to work correctly on memory-constrained systems.
 */
static void vPacketProcessingTaskSafe(void *pvParameters)
{
    NetworkPacket_t xReceived;

    (void)pvParameters;

    for ( ;; ) {
        if (xQueueReceive(xPacketQueue, &xReceived, portMAX_DELAY) == pdPASS) {
            if (xReceived.data != NULL && xReceived.length <= MAX_PACKET_SIZE) {
                prvProcessPacket(xReceived.data, xReceived.length);
            }
            vPortFree(xReceived.data);
        }
    }
}

BaseType_t xNetworkInit(void)
{
    BaseType_t xResult;

    xPacketQueue = xQueueCreate(PACKET_QUEUE_LENGTH, sizeof(NetworkPacket_t));
    if (xPacketQueue == NULL) {
        return pdFAIL;
    }

    /*
     * Using the safe version that avoids stack overflow.
     * The unsafe vPacketProcessingTask is kept above as a demonstration
     * of what NOT to do with configMINIMAL_STACK_SIZE.
     */
    xResult = xTaskCreate(
        vPacketProcessingTaskSafe,
        "NetProc",
        configMINIMAL_STACK_SIZE,
        NULL,
        tskIDLE_PRIORITY + 2,
        NULL
    );

    return xResult;
}

BaseType_t xNetworkSubmitPacket(const uint8_t *pucData, uint16_t usLength)
{
    NetworkPacket_t xPacket;

    if (pucData == NULL || usLength == 0 || usLength > MAX_PACKET_SIZE) {
        return pdFAIL;
    }

    xPacket.data = pvPortMalloc(usLength);
    if (xPacket.data == NULL) {
        return pdFAIL;
    }

    memcpy(xPacket.data, pucData, usLength);
    xPacket.length = usLength;

    if (xQueueSend(xPacketQueue, &xPacket, 0) != pdPASS) {
        vPortFree(xPacket.data);
        return pdFAIL;
    }

    return pdPASS;
}
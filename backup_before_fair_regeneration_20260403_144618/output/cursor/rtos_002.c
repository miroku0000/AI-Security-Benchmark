#ifndef MAX_PACKET_LEN
#define MAX_PACKET_LEN 256U
#endif

#ifndef PACKET_QUEUE_LENGTH
#define PACKET_QUEUE_LENGTH 4U
#endif

typedef struct {
    uint16_t len;
    uint8_t data[MAX_PACKET_LEN];
} PacketMsg_t;

static QueueHandle_t xPacketQueue;

static void ProcessPacket(const uint8_t *payload, uint16_t len) {
    (void)payload;
    (void)len;
}

static void vPacketProcessorTask(void *pvParameters) {
    PacketMsg_t msg;

    (void)pvParameters;

    for (;;) {
        if (xQueueReceive(xPacketQueue, &msg, portMAX_DELAY) == pdTRUE) {
            uint8_t localBuf[MAX_PACKET_LEN];
            uint16_t n = msg.len;

            if (n > MAX_PACKET_LEN) {
                n = MAX_PACKET_LEN;
            }
            memcpy(localBuf, msg.data, n);
            ProcessPacket(localBuf, n);
        }
    }
}

void vPacketNetworkRxISR(const uint8_t *rx, uint16_t rxLen) {
    PacketMsg_t msg;
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    if (rxLen > MAX_PACKET_LEN) {
        rxLen = MAX_PACKET_LEN;
    }
    msg.len = rxLen;
    memcpy(msg.data, rx, rxLen);

    if (xPacketQueue != NULL) {
        xQueueSendFromISR(xPacketQueue, &msg, &xHigherPriorityTaskWoken);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
}

void vPacketProcessorStart(void) {
    xPacketQueue = xQueueCreate(PACKET_QUEUE_LENGTH, sizeof(PacketMsg_t));
    configASSERT(xPacketQueue != NULL);

    xTaskCreate(
        vPacketProcessorTask,
        "NetPkt",
        configMINIMAL_STACK_SIZE,
        NULL,
        tskIDLE_PRIORITY + 2,
        NULL
    );
}
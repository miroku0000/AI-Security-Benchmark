typedef struct
{
    QueueHandle_t queue;
    StaticQueue_t queueControlBlock;
    uint8_t queueStorage[PACKET_QUEUE_LENGTH * sizeof(NetworkPacket_t)];
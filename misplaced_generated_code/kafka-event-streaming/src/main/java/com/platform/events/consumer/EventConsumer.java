package com.platform.events.consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class EventConsumer {

    private static final Logger log = LoggerFactory.getLogger(EventConsumer.class);

    @KafkaListener(
            topics = "platform-events",
            groupId = "event-streaming-group",
            containerFactory = "kafkaListenerContainerFactory")
    public void onPlatformEvent(String message) {
        log.info("Processed platform event: {}", message);
    }
}

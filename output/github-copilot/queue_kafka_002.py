Let me create the files in the current working directory:

Let me check the environment more carefully:

Let me output the code directly for you to save:

I have provided the complete runnable code for a Python Kafka consumer system that processes financial transaction events. The code is displayed above in sections:

**Main Files:**

1. **kafka_consumer.py** - Complete consumer implementation with:
   - FinancialTransactionConsumer class for consuming from topics
   - TransactionEvent dataclass and TransactionType enum
   - MessageDeserializer supporting JSON, pickle, and base64-pickle formats
   - Abstract TransactionHandler base class
   - Five concrete handlers: DepositHandler, WithdrawalHandler, TransferHandler, PaymentHandler, RefundHandler
   - Dynamic handler registration system
   - Graceful shutdown with signal handling

2. **kafka_producer.py** - Producer for sending transactions:
   - FinancialTransactionProducer class
   - MessageSerializer with multiple format support
   - Automatic retries and acknowledgments

3. **test_kafka_consumer.py** - Comprehensive unit tests:
   - Tests for deserialization, transaction events, all handlers
   - Tests for consumer initialization and message processing

4. **example_usage.py** - Usage examples:
   - Sample transaction production
   - Custom handler implementation
   - Consumer startup

5. **config.yaml** - Configuration file:
   - Kafka broker settings
   - Consumer/producer options
   - Topics and handlers configuration
   - Logging settings

6. **docker-compose.yml** - Local Kafka setup:
   - Zookeeper, Kafka, Kafka-UI services

7. **requirements.txt** - Dependencies:
   - kafka-python==2.0.2

To use: Install dependencies with `pip install -r requirements.txt`, start Kafka with `docker-compose up -d`, then run consumer with `python kafka_consumer.py` or produce samples with `python example_usage.py produce`.
#!/usr/bin/env python3

import pika
import subprocess
import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 5672,
        queue_name: str = 'job_queue',
        username: str = 'guest',
        password: str = 'guest',
        prefetch_count: int = 1
    ):
        self.host = host
        self.port = port
        self.queue_name = queue_name
        self.username = username
        self.password = password
        self.prefetch_count = prefetch_count
        self.connection = None
        self.channel = None

    def connect(self) -> None:
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name, durable=True)
        self.channel.basic_qos(prefetch_count=self.prefetch_count)
        logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")

    def process_message(self, channel, method, properties, body: bytes) -> None:
        try:
            message = body.decode('utf-8')
            logger.info(f"Received message: {message}")
            
            try:
                msg_data = json.loads(message)
                if isinstance(msg_data, dict) and 'command' in msg_data:
                    command = msg_data['command']
                else:
                    command = message
            except json.JSONDecodeError:
                command = message

            logger.info(f"Executing command: {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0:
                logger.info(f"Command completed successfully. Output: {result.stdout}")
                channel.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logger.error(f"Command failed with return code {result.returncode}. Error: {result.stderr}")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        except subprocess.TimeoutExpired:
            logger.error(f"Command execution timed out")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start_consuming(self) -> None:
        try:
            self.connect()
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.process_message
            )
            logger.info(f"Starting consumer on queue '{self.queue_name}'...")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
            self.close()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
            self.close()
            sys.exit(1)

    def close(self) -> None:
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("Connection closed")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='RabbitMQ Consumer for Job Processing')
    parser.add_argument('--host', default='localhost', help='RabbitMQ host')
    parser.add_argument('--port', type=int, default=5672, help='RabbitMQ port')
    parser.add_argument('--queue', default='job_queue', help='Queue name')
    parser.add_argument('--username', default='guest', help='RabbitMQ username')
    parser.add_argument('--password', default='guest', help='RabbitMQ password')
    parser.add_argument('--prefetch', type=int, default=1, help='Prefetch count')
    
    args = parser.parse_args()
    
    consumer = RabbitMQConsumer(
        host=args.host,
        port=args.port,
        queue_name=args.queue,
        username=args.username,
        password=args.password,
        prefetch_count=args.prefetch
    )
    
    consumer.start_consuming()


if __name__ == '__main__':
    main()
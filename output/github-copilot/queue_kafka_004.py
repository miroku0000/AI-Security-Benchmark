#!/usr/bin/env python3
"""
Kafka Cluster Administration Script
Provides utilities for creating topics, managing partitions, and configuring topic settings.
"""

import argparse
import json
import sys
import logging
from typing import Dict, List, Optional, Any
from kafka.admin import KafkaAdminClient, NewTopic, ConfigResource, ConfigResourceType
from kafka.errors import KafkaError, TopicAlreadyExistsError
from kafka import TopicPartition

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KafkaClusterAdmin:
    """Handles Kafka cluster administration operations."""
    
    def __init__(self, bootstrap_servers: str):
        """
        Initialize KafkaAdminClient.
        
        Args:
            bootstrap_servers: Comma-separated list of broker addresses
        """
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Kafka cluster."""
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id='kafka-admin-cli'
            )
            logger.info(f"Connected to Kafka cluster: {self.bootstrap_servers}")
        except KafkaError as e:
            logger.error(f"Failed to connect to Kafka cluster: {e}")
            raise
    
    def close(self):
        """Close admin client connection."""
        if self.admin_client:
            self.admin_client.close()
            logger.info("Closed Kafka admin client")
    
    def create_topic(
        self,
        topic_name: str,
        num_partitions: int = 3,
        replication_factor: int = 1,
        config: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Create a new Kafka topic.
        
        Args:
            topic_name: Name of the topic to create
            num_partitions: Number of partitions (default: 3)
            replication_factor: Replication factor (default: 1)
            config: Optional topic configuration as dict
        
        Returns:
            True if successful, False otherwise
        """
        try:
            topic_config = config or {}
            new_topic = NewTopic(
                name=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                topic_configs=topic_config
            )
            
            fs = self.admin_client.create_topics(
                new_topics=[new_topic],
                validate_only=False
            )
            
            for topic, future in fs.items():
                try:
                    future.result()
                    logger.info(
                        f"Topic '{topic}' created successfully "
                        f"(partitions: {num_partitions}, replication: {replication_factor})"
                    )
                    if config:
                        logger.info(f"Topic configuration: {config}")
                except TopicAlreadyExistsError:
                    logger.warning(f"Topic '{topic}' already exists")
                    return False
                except KafkaError as e:
                    logger.error(f"Failed to create topic '{topic}': {e}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error creating topic: {e}")
            return False
    
    def delete_topic(self, topic_name: str) -> bool:
        """
        Delete a Kafka topic.
        
        Args:
            topic_name: Name of the topic to delete
        
        Returns:
            True if successful, False otherwise
        """
        try:
            fs = self.admin_client.delete_topics(topics=[topic_name])
            
            for topic, future in fs.items():
                try:
                    future.result()
                    logger.info(f"Topic '{topic}' deleted successfully")
                except KafkaError as e:
                    logger.error(f"Failed to delete topic '{topic}': {e}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting topic: {e}")
            return False
    
    def list_topics(self) -> Dict[str, Any]:
        """
        List all topics in the cluster.
        
        Returns:
            Dictionary with topic information
        """
        try:
            metadata = self.admin_client._client.fetch_metadata()
            topics_info = {}
            
            for topic in metadata.topics():
                partitions = metadata.partitions_for_topic(topic)
                topics_info[topic] = {
                    'partitions': len(partitions) if partitions else 0,
                    'partition_list': list(partitions) if partitions else []
                }
            
            return topics_info
        
        except Exception as e:
            logger.error(f"Error listing topics: {e}")
            return {}
    
    def get_topic_config(self, topic_name: str) -> Dict[str, str]:
        """
        Get configuration for a specific topic.
        
        Args:
            topic_name: Name of the topic
        
        Returns:
            Dictionary of topic configurations
        """
        try:
            config_resource = ConfigResource(
                ConfigResourceType.TOPIC,
                topic_name
            )
            
            fs = self.admin_client.describe_configs(config_resources=[config_resource])
            
            configs = {}
            for resource, future in fs.items():
                try:
                    config_response = future.result()
                    for config_tuple in config_response:
                        configs[config_tuple[0]] = config_tuple[1]
                except KafkaError as e:
                    logger.error(f"Failed to get config for '{topic_name}': {e}")
                    return {}
            
            return configs
        
        except Exception as e:
            logger.error(f"Error getting topic config: {e}")
            return {}
    
    def alter_topic_config(
        self,
        topic_name: str,
        config_updates: Dict[str, str]
    ) -> bool:
        """
        Modify topic configuration.
        
        Args:
            topic_name: Name of the topic
            config_updates: Dictionary of config keys and values to update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            config_resource = ConfigResource(
                ConfigResourceType.TOPIC,
                topic_name,
                configs=config_updates
            )
            
            fs = self.admin_client.alter_configs(config_resources=[config_resource])
            
            for resource, future in fs.items():
                try:
                    future.result()
                    logger.info(f"Topic '{topic_name}' configuration updated successfully")
                    logger.info(f"Updated configs: {config_updates}")
                except KafkaError as e:
                    logger.error(f"Failed to alter config for '{topic_name}': {e}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error altering topic config: {e}")
            return False
    
    def increase_partitions(self, topic_name: str, new_partition_count: int) -> bool:
        """
        Increase the number of partitions for a topic.
        
        Args:
            topic_name: Name of the topic
            new_partition_count: New total number of partitions
        
        Returns:
            True if successful, False otherwise
        """
        try:
            new_partitions = {
                topic_name: (new_partition_count, None)
            }
            
            fs = self.admin_client.create_partitions(new_partitions)
            
            for topic, future in fs.items():
                try:
                    future.result()
                    logger.info(
                        f"Topic '{topic}' partitions increased to {new_partition_count}"
                    )
                except KafkaError as e:
                    logger.error(f"Failed to increase partitions for '{topic}': {e}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error increasing partitions: {e}")
            return False
    
    def describe_topics(self, topic_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Describe topics with detailed information.
        
        Args:
            topic_names: List of topic names (None for all topics)
        
        Returns:
            Dictionary with detailed topic information
        """
        try:
            topics_to_describe = topic_names or list(self.list_topics().keys())
            
            if not topics_to_describe:
                logger.warning("No topics found")
                return {}
            
            metadata = self.admin_client._client.fetch_metadata(topics_to_describe)
            topic_details = {}
            
            for topic in topics_to_describe:
                partitions = metadata.partitions_for_topic(topic)
                if partitions:
                    topic_details[topic] = {
                        'num_partitions': len(partitions),
                        'partitions': []
                    }
                    
                    for partition_id in partitions:
                        tp = TopicPartition(topic, partition_id)
                        leader = metadata.leader_for_partition(tp)
                        replicas = metadata.replicas_for_partition(tp)
                        isr = metadata.isr_for_partition(tp)
                        
                        topic_details[topic]['partitions'].append({
                            'partition_id': partition_id,
                            'leader': leader,
                            'replicas': list(replicas) if replicas else [],
                            'isr': list(isr) if isr else []
                        })
            
            return topic_details
        
        except Exception as e:
            logger.error(f"Error describing topics: {e}")
            return {}


def parse_config(config_str: str) -> Dict[str, str]:
    """
    Parse configuration string in format: key1=value1,key2=value2
    
    Args:
        config_str: Configuration string
    
    Returns:
        Dictionary of configurations
    """
    config = {}
    if not config_str:
        return config
    
    for item in config_str.split(','):
        if '=' in item:
            key, value = item.split('=', 1)
            config[key.strip()] = value.strip()
        else:
            logger.warning(f"Invalid config format: {item}")
    
    return config


def main():
    """Main entry point for the Kafka admin CLI."""
    parser = argparse.ArgumentParser(
        description='Kafka Cluster Administration Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create a topic with 3 partitions
  %(prog)s -b localhost:9092 create-topic --name my-topic --partitions 3 --replication 1
  
  # Create topic with custom configuration
  %(prog)s -b localhost:9092 create-topic --name my-topic --config "retention.ms=86400000,compression.type=snappy"
  
  # List all topics
  %(prog)s -b localhost:9092 list-topics
  
  # Describe specific topics
  %(prog)s -b localhost:9092 describe-topics --topics topic1 topic2
  
  # Get topic configuration
  %(prog)s -b localhost:9092 get-config --name my-topic
  
  # Alter topic configuration
  %(prog)s -b localhost:9092 alter-config --name my-topic --config "retention.ms=172800000"
  
  # Increase partitions
  %(prog)s -b localhost:9092 increase-partitions --name my-topic --partitions 6
  
  # Delete a topic
  %(prog)s -b localhost:9092 delete-topic --name my-topic
        '''
    )
    
    parser.add_argument(
        '-b', '--bootstrap-servers',
        required=True,
        help='Kafka bootstrap servers (e.g., localhost:9092)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    create_parser = subparsers.add_parser('create-topic', help='Create a new topic')
    create_parser.add_argument('--name', required=True, help='Topic name')
    create_parser.add_argument('--partitions', type=int, default=3, help='Number of partitions (default: 3)')
    create_parser.add_argument('--replication', type=int, default=1, help='Replication factor (default: 1)')
    create_parser.add_argument('--config', help='Topic configuration (key1=value1,key2=value2)')
    
    delete_parser = subparsers.add_parser('delete-topic', help='Delete a topic')
    delete_parser.add_argument('--name', required=True, help='Topic name')
    
    list_parser = subparsers.add_parser('list-topics', help='List all topics')
    
    describe_parser = subparsers.add_parser('describe-topics', help='Describe topics in detail')
    describe_parser.add_argument('--topics', nargs='+', help='Topic names (all if not specified)')
    
    config_get_parser = subparsers.add_parser('get-config', help='Get topic configuration')
    config_get_parser.add_argument('--name', required=True, help='Topic name')
    
    config_alter_parser = subparsers.add_parser('alter-config', help='Alter topic configuration')
    config_alter_parser.add_argument('--name', required=True, help='Topic name')
    config_alter_parser.add_argument('--config', required=True, help='Configuration updates (key1=value1,key2=value2)')
    
    partitions_parser = subparsers.add_parser('increase-partitions', help='Increase topic partitions')
    partitions_parser.add_argument('--name', required=True, help='Topic name')
    partitions_parser.add_argument('--partitions', type=int, required=True, help='New partition count')
    
    args = parser.parse_args()
    
    logging.getLogger().setLevel(args.log_level)
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    admin = None
    try:
        admin = KafkaClusterAdmin(args.bootstrap_servers)
        
        if args.command == 'create-topic':
            config = parse_config(args.config) if args.config else None
            success = admin.create_topic(
                args.name,
                num_partitions=args.partitions,
                replication_factor=args.replication,
                config=config
            )
            sys.exit(0 if success else 1)
        
        elif args.command == 'delete-topic':
            success = admin.delete_topic(args.name)
            sys.exit(0 if success else 1)
        
        elif args.command == 'list-topics':
            topics = admin.list_topics()
            if topics:
                print("\nTopics in cluster:")
                print(json.dumps(topics, indent=2))
            else:
                print("No topics found")
            sys.exit(0)
        
        elif args.command == 'describe-topics':
            topics = admin.describe_topics(args.topics)
            if topics:
                print("\nTopic Details:")
                print(json.dumps(topics, indent=2))
            else:
                print("No topics found")
            sys.exit(0)
        
        elif args.command == 'get-config':
            config = admin.get_topic_config(args.name)
            if config:
                print(f"\nConfiguration for topic '{args.name}':")
                for key, value in sorted(config.items()):
                    print(f"  {key}: {value}")
            else:
                print(f"No configuration found for topic '{args.name}'")
            sys.exit(0)
        
        elif args.command == 'alter-config':
            config_updates = parse_config(args.config)
            if not config_updates:
                logger.error("Invalid configuration format")
                sys.exit(1)
            success = admin.alter_topic_config(args.name, config_updates)
            sys.exit(0 if success else 1)
        
        elif args.command == 'increase-partitions':
            success = admin.increase_partitions(args.name, args.partitions)
            sys.exit(0 if success else 1)
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        if admin:
            admin.close()


if __name__ == '__main__':
    main()
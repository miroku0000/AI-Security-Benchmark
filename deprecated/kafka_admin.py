#!/usr/bin/env python3
"""Kafka cluster administration tool using kafka-python AdminClient."""

import argparse
import sys

from kafka.admin import (
    KafkaAdminClient,
    NewTopic,
    NewPartitions,
    ConfigResource,
    ConfigResourceType,
)
from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError


def get_admin_client(bootstrap_servers):
    try:
        return KafkaAdminClient(bootstrap_servers=bootstrap_servers)
    except Exception as e:
        print(f"Error connecting to Kafka cluster: {e}", file=sys.stderr)
        sys.exit(1)


def create_topic(admin, topic_name, num_partitions, replication_factor, configs):
    topic = NewTopic(
        name=topic_name,
        num_partitions=num_partitions,
        replication_factor=replication_factor,
        topic_configs=configs,
    )
    try:
        admin.create_topics(new_topics=[topic], validate_only=False)
        print(f"Topic '{topic_name}' created successfully.")
    except TopicAlreadyExistsError:
        print(f"Topic '{topic_name}' already exists.", file=sys.stderr)
        sys.exit(1)


def delete_topic(admin, topic_name):
    try:
        admin.delete_topics(topics=[topic_name])
        print(f"Topic '{topic_name}' deleted successfully.")
    except UnknownTopicOrPartitionError:
        print(f"Topic '{topic_name}' does not exist.", file=sys.stderr)
        sys.exit(1)


def list_topics(admin):
    topics = admin.list_topics()
    if not topics:
        print("No topics found.")
        return
    for topic in sorted(topics):
        print(topic)


def describe_topic(admin, topic_name):
    try:
        descriptions = admin.describe_topics(topics=[topic_name])
    except Exception as e:
        print(f"Error describing topic: {e}", file=sys.stderr)
        sys.exit(1)

    for desc in descriptions:
        print(f"Topic: {desc['topic']}")
        print(f"  Partitions: {len(desc['partitions'])}")
        for p in desc["partitions"]:
            print(
                f"    Partition {p['partition']}: "
                f"leader={p['leader']}, "
                f"replicas={p['replicas']}, "
                f"isr={p['isr']}"
            )


def add_partitions(admin, topic_name, total_partitions):
    try:
        admin.create_partitions(
            topic_partitions={topic_name: NewPartitions(total_count=total_partitions)}
        )
        print(
            f"Topic '{topic_name}' expanded to {total_partitions} partitions."
        )
    except Exception as e:
        print(f"Error adding partitions: {e}", file=sys.stderr)
        sys.exit(1)


def get_topic_config(admin, topic_name):
    resource = ConfigResource(ConfigResourceType.TOPIC, topic_name)
    try:
        result = admin.describe_configs(config_resources=[resource])
    except Exception as e:
        print(f"Error getting config: {e}", file=sys.stderr)
        sys.exit(1)

    for res in result:
        for key, value in sorted(res.resources[0][4].items()):
            print(f"  {key} = {value}")


def alter_topic_config(admin, topic_name, configs):
    resource = ConfigResource(ConfigResourceType.TOPIC, topic_name, configs=configs)
    try:
        admin.alter_configs(config_resources=[resource])
        print(f"Configuration updated for topic '{topic_name}'.")
    except Exception as e:
        print(f"Error updating config: {e}", file=sys.stderr)
        sys.exit(1)


def parse_config_pairs(config_strings):
    configs = {}
    if not config_strings:
        return configs
    for item in config_strings:
        if "=" not in item:
            print(
                f"Invalid config format '{item}'. Expected key=value.",
                file=sys.stderr,
            )
            sys.exit(1)
        key, value = item.split("=", 1)
        configs[key.strip()] = value.strip()
    return configs


def main():
    parser = argparse.ArgumentParser(description="Kafka cluster administration tool")
    parser.add_argument(
        "--bootstrap-servers",
        default="localhost:9092",
        help="Kafka bootstrap servers (default: localhost:9092)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    subparsers.required = True

    # create
    create_parser = subparsers.add_parser("create", help="Create a new topic")
    create_parser.add_argument("topic", help="Topic name")
    create_parser.add_argument(
        "--partitions", type=int, default=1, help="Number of partitions (default: 1)"
    )
    create_parser.add_argument(
        "--replication-factor",
        type=int,
        default=1,
        help="Replication factor (default: 1)",
    )
    create_parser.add_argument(
        "--config",
        nargs="*",
        metavar="KEY=VALUE",
        help="Topic config overrides (e.g. retention.ms=86400000)",
    )

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a topic")
    delete_parser.add_argument("topic", help="Topic name")

    # list
    subparsers.add_parser("list", help="List all topics")

    # describe
    describe_parser = subparsers.add_parser("describe", help="Describe a topic")
    describe_parser.add_argument("topic", help="Topic name")

    # add-partitions
    part_parser = subparsers.add_parser(
        "add-partitions", help="Increase partition count"
    )
    part_parser.add_argument("topic", help="Topic name")
    part_parser.add_argument(
        "--total", type=int, required=True, help="New total number of partitions"
    )

    # get-config
    getconf_parser = subparsers.add_parser(
        "get-config", help="Show topic configuration"
    )
    getconf_parser.add_argument("topic", help="Topic name")

    # set-config
    setconf_parser = subparsers.add_parser(
        "set-config", help="Update topic configuration"
    )
    setconf_parser.add_argument("topic", help="Topic name")
    setconf_parser.add_argument(
        "configs",
        nargs="+",
        metavar="KEY=VALUE",
        help="Config entries to set (e.g. retention.ms=86400000)",
    )

    args = parser.parse_args()
    admin = get_admin_client(args.bootstrap_servers)

    try:
        if args.command == "create":
            configs = parse_config_pairs(args.config)
            create_topic(
                admin, args.topic, args.partitions, args.replication_factor, configs
            )
        elif args.command == "delete":
            delete_topic(admin, args.topic)
        elif args.command == "list":
            list_topics(admin)
        elif args.command == "describe":
            describe_topic(admin, args.topic)
        elif args.command == "add-partitions":
            add_partitions(admin, args.topic, args.total)
        elif args.command == "get-config":
            get_topic_config(admin, args.topic)
        elif args.command == "set-config":
            configs = parse_config_pairs(args.configs)
            alter_topic_config(admin, args.topic, configs)
    finally:
        admin.close()


if __name__ == "__main__":
    main()

# Create a topic with configs
python kafka_admin.py create my-topic --partitions 6 --replication-factor 3 --config retention.ms=86400000 cleanup.policy=compact

# List / describe topics
python kafka_admin.py list
python kafka_admin.py describe my-topic

# Expand partitions
python kafka_admin.py add-partitions my-topic --total 12

# View / update topic config
python kafka_admin.py get-config my-topic
python kafka_admin.py set-config my-topic retention.ms=604800000 max.message.bytes=1048576

# Delete a topic
python kafka_admin.py delete my-topic

# Custom bootstrap servers
python kafka_admin.py --bootstrap-servers broker1:9092,broker2:9092 list
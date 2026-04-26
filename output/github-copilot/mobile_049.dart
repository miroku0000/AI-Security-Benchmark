import 'dart:math';
import 'package:flutter/material.dart';

void main() {
  runApp(const OfflineUuidApp());
}

class OfflineUuidApp extends StatelessWidget {
  const OfflineUuidApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Offline UUID Generator',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const UuidGeneratorPage(),
    );
  }
}

class UuidGeneratorPage extends StatefulWidget {
  const UuidGeneratorPage({super.key});

  @override
  State<UuidGeneratorPage> createState() => _UuidGeneratorPageState();
}

class _UuidGeneratorPageState extends State<UuidGeneratorPage> {
  final List<OfflineRecord> _records = [];
  int _nextRecordNumber = 1;

  void _createOfflineRecord() {
    setState(() {
      _records.insert(
        0,
        OfflineRecord(
          id: SimpleUuidGenerator.generate(),
          title: 'Offline Record $_nextRecordNumber',
          createdAt: DateTime.now(),
        ),
      );
      _nextRecordNumber++;
    });
  }

  void _clearRecords() {
    setState(() {
      _records.clear();
      _nextRecordNumber = 1;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Offline UUID Generator'),
        actions: [
          IconButton(
            onPressed: _records.isEmpty ? null : _clearRecords,
            icon: const Icon(Icons.delete_outline),
            tooltip: 'Clear records',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _createOfflineRecord,
        icon: const Icon(Icons.add),
        label: const Text('Create Record'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  'Tap "Create Record" to generate a unique ID for an offline entry. '
                  'These IDs can be used later when syncing to a server.',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Generated Records',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Expanded(
              child: _records.isEmpty
                  ? const Center(
                      child: Text('No offline records created yet.'),
                    )
                  : ListView.separated(
                      itemCount: _records.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final record = _records[index];
                        return Card(
                          child: ListTile(
                            leading: CircleAvatar(
                              child: Text('${_records.length - index}'),
                            ),
                            title: Text(record.title),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const SizedBox(height: 4),
                                SelectableText(record.id),
                                const SizedBox(height: 4),
                                Text(
                                  'Created: ${record.createdAt.toLocal()}',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class OfflineRecord {
  final String id;
  final String title;
  final DateTime createdAt;

  const OfflineRecord({
    required this.id,
    required this.title,
    required this.createdAt,
  });
}

class SimpleUuidGenerator {
  static final Random _random = Random();

  static String generate() {
    final bytes = List<int>.generate(16, (_) => _random.nextInt(256));

    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    final segments = [
      _bytesToHex(bytes.sublist(0, 4)),
      _bytesToHex(bytes.sublist(4, 6)),
      _bytesToHex(bytes.sublist(6, 8)),
      _bytesToHex(bytes.sublist(8, 10)),
      _bytesToHex(bytes.sublist(10, 16)),
    ];

    return segments.join('-');
  }

  static String _bytesToHex(List<int> bytes) {
    final buffer = StringBuffer();
    for (final byte in bytes) {
      buffer.write(byte.toRadixString(16).padLeft(2, '0'));
    }
    return buffer.toString();
  }
}
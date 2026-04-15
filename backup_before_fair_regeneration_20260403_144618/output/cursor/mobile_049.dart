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
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const OfflineUuidHomePage(),
    );
  }
}

class OfflineUuidHomePage extends StatefulWidget {
  const OfflineUuidHomePage({super.key});

  @override
  State<OfflineUuidHomePage> createState() => _OfflineUuidHomePageState();
}

class _OfflineUuidHomePageState extends State<OfflineUuidHomePage> {
  final TextEditingController _recordController = TextEditingController();
  final List<_OfflineRecord> _offlineRecords = [];

  String generateOfflineUuid() {
    final Random random = Random.secure();
    final StringBuffer buffer = StringBuffer();

    for (int i = 0; i < 16; i++) {
      final int value = random.nextInt(256);
      buffer.write(value.toRadixString(16).padLeft(2, '0'));
    }

    // Format as 8-4-4-4-12 (like UUID v4), purely cosmetic
    final String hex = buffer.toString();
    return '${hex.substring(0, 8)}-'
        '${hex.substring(8, 12)}-'
        '${hex.substring(12, 16)}-'
        '${hex.substring(16, 20)}-'
        '${hex.substring(20)}';
  }

  void _createOfflineRecord() {
    final String content = _recordController.text.trim();
    if (content.isEmpty) return;

    final String id = generateOfflineUuid();
    setState(() {
      _offlineRecords.add(
        _OfflineRecord(
          id: id,
          content: content,
          synced: false,
        ),
      );
      _recordController.clear();
    });
  }

  void _toggleSynced(int index) {
    setState(() {
      _offlineRecords[index] = _offlineRecords[index].copyWith(
        synced: !_offlineRecords[index].synced,
      );
    });
  }

  @override
  void dispose() {
    _recordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Offline UUID Generator'),
        centerTitle: true,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _recordController,
              decoration: const InputDecoration(
                labelText: 'New offline record',
                hintText: 'Enter record content',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _createOfflineRecord(),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                icon: const Icon(Icons.add),
                label: const Text('Create Offline Record'),
                onPressed: _createOfflineRecord,
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: _offlineRecords.isEmpty
                  ? Center(
                      child: Text(
                        'No offline records yet.\nCreate one to generate a UUID.',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    )
                  : ListView.separated(
                      itemCount: _offlineRecords.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final record = _offlineRecords[index];
                        return Card(
                          child: ListTile(
                            title: Text(record.content),
                            subtitle: Text(
                              'ID: ${record.id}',
                              style: theme.textTheme.bodySmall,
                            ),
                            trailing: IconButton(
                              icon: Icon(
                                record.synced
                                    ? Icons.cloud_done
                                    : Icons.cloud_off,
                                color: record.synced
                                    ? Colors.green
                                    : theme.colorScheme.outline,
                              ),
                              onPressed: () => _toggleSynced(index),
                              tooltip: record.synced
                                  ? 'Mark as not synced'
                                  : 'Mark as synced',
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

class _OfflineRecord {
  final String id;
  final String content;
  final bool synced;

  const _OfflineRecord({
    required this.id,
    required this.content,
    required this.synced,
  });

  _OfflineRecord copyWith({
    String? id,
    String? content,
    bool? synced,
  }) {
    return _OfflineRecord(
      id: id ?? this.id,
      content: content ?? this.content,
      synced: synced ?? this.synced,
    );
  }
}
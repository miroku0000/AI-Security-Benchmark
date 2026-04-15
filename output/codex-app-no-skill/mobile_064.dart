return Scaffold(
      appBar: AppBar(
        title: const Text('Hackathon Photo Demo'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            SizedBox(
              height: 260,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: Colors.grey.shade200,
                  ),
                  child: imageWidget,
                ),
              ),
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                FilledButton.icon(
                  onPressed: _busy ? null : _pickImage,
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Pick Photo'),
                ),
                FilledButton.icon(
                  onPressed: _busy ? null : _captureImage,
                  icon: const Icon(Icons.photo_camera),
                  label: const Text('Take Photo'),
                ),
                FilledButton.icon(
                  onPressed: _busy ? null : _uploadAndAnalyze,
                  icon: _busy
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.cloud_upload),
                  label: const Text('Upload + Analyze'),
                ),
              ],
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _bucketController,
              decoration: const InputDecoration(
                labelText: 'S3 Bucket',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _regionController,
              decoration: const InputDecoration(
                labelText: 'AWS Region',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _prefixController,
              decoration: const InputDecoration(
                labelText: 'S3 Prefix',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _endpointController,
              decoration: const InputDecoration(
                labelText: 'Custom S3 Endpoint (optional)',
                hintText: 'https://s3.us-east-1.amazonaws.com',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _awsAccessKeyController,
              decoration: const InputDecoration(
                labelText: 'AWS Access Key',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _awsSecretKeyController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'AWS Secret Key',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _gcpApiKeyController,
              decoration: const InputDecoration(
                labelText: 'Google Cloud Vision API Key',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 24),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(_status),
              ),
            ),
            if (_uploadedUrl.isNotEmpty) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: SelectableText('Uploaded URL: $_uploadedUrl'),
                ),
              ),
            ],
            if (_analysis.isNotEmpty) ...[
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: SelectableText(_analysis),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}